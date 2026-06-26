from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..deadlines import get_match_kickoff_utc
from ..fixtures import FIXTURE_BY_ID, TEAMS
from ..limiter import limiter
from ..models import FinalPick, OfficialFinal, OfficialResult, Prediction, User
from .live_routes import audit_official_results, force_sync_now, sync_state_snapshot
from ..schemas import (
    AdminStats,
    OfficialFinalIn,
    OfficialFinalOut,
    OfficialResultIn,
    OfficialResultOut,
    UserPrivateOut,
    UserUpdateAdminIn,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.post("/result/{match_id}", response_model=OfficialResultOut)
@limiter.limit("30/minute")
def upsert_official_result(
    request: Request,
    match_id: str,
    payload: OfficialResultIn,
    db: Session = Depends(get_db),
):
    if match_id not in FIXTURE_BY_ID:
        raise HTTPException(status_code=404, detail=f"match_id no existe: {match_id}")

    kickoff = get_match_kickoff_utc(match_id)
    if datetime.now(timezone.utc) < kickoff:
        raise HTTPException(
            status_code=403,
            detail="No podés cargar resultado de un partido que no se jugó todavía",
        )

    existing = db.get(OfficialResult, match_id)
    if existing is None:
        existing = OfficialResult(
            match_id=match_id,
            home_score=payload.home_score,
            away_score=payload.away_score,
            auto_loaded=False,
        )
        db.add(existing)
    else:
        existing.home_score = payload.home_score
        existing.away_score = payload.away_score
        # Si lo edita el admin manualmente, deja de ser "auto"
        existing.auto_loaded = False

    db.commit()
    db.refresh(existing)
    return OfficialResultOut.model_validate(existing)


@router.delete("/result/{match_id}", status_code=204)
@limiter.limit("30/minute")
def delete_official_result(
    request: Request,
    match_id: str,
    db: Session = Depends(get_db),
):
    existing = db.get(OfficialResult, match_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resultado no cargado")
    db.delete(existing)
    db.commit()


@router.get("/final", response_model=OfficialFinalOut)
@limiter.limit("30/minute")
def get_official_final(request: Request, db: Session = Depends(get_db)):
    existing = db.get(OfficialFinal, 1)
    if existing is None:
        return OfficialFinalOut(champion=None, runner_up=None, updated_at=None)
    return OfficialFinalOut(
        champion=existing.champion,
        runner_up=existing.runner_up,
        updated_at=existing.updated_at,
    )


@router.post("/final", response_model=OfficialFinalOut)
@limiter.limit("30/minute")
def upsert_official_final(
    request: Request,
    payload: OfficialFinalIn,
    db: Session = Depends(get_db),
):
    champion = payload.champion.upper()
    runner_up = payload.runner_up.upper()
    if champion not in TEAMS or runner_up not in TEAMS:
        raise HTTPException(status_code=400, detail="Código de selección inválido")
    if champion == runner_up:
        raise HTTPException(status_code=400, detail="Campeón y subcampeón no pueden ser iguales")

    existing = db.get(OfficialFinal, 1)
    if existing is None:
        existing = OfficialFinal(id=1, champion=champion, runner_up=runner_up)
        db.add(existing)
    else:
        existing.champion = champion
        existing.runner_up = runner_up

    db.commit()
    db.refresh(existing)
    return OfficialFinalOut(
        champion=existing.champion,
        runner_up=existing.runner_up,
        updated_at=existing.updated_at,
    )


@router.delete("/final", status_code=204)
@limiter.limit("30/minute")
def delete_official_final(request: Request, db: Session = Depends(get_db)):
    existing = db.get(OfficialFinal, 1)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resultado final no cargado")
    db.delete(existing)
    db.commit()


@router.get("/sync-debug")
@limiter.limit("30/minute")
def sync_debug(request: Request, db: Session = Depends(get_db)):
    """Snapshot del estado del auto-sync con football-data.org. No fuerza fetch.

    Útil para entender por qué un partido FINISHED no se cargó solo:
    devuelve token_present, edad del cache, último error, y total de FINISHED
    actualmente vistos por la API.
    """
    snap = sync_state_snapshot()
    loaded_auto = db.scalar(
        select(func.count(OfficialResult.match_id)).where(OfficialResult.auto_loaded.is_(True))
    ) or 0
    loaded_manual = db.scalar(
        select(func.count(OfficialResult.match_id)).where(OfficialResult.auto_loaded.is_(False))
    ) or 0
    return {
        **snap,
        "official_results_auto_loaded": int(loaded_auto),
        "official_results_manual": int(loaded_manual),
    }


@router.post("/sync-now")
@limiter.limit("10/minute")
def sync_now(request: Request, db: Session = Depends(get_db)):
    """Fuerza un fetch fresh a football-data.org (ignora cache) y corre el sync.

    Devuelve diagnóstico detallado: cantidad sincronizada, total de FINISHED,
    cuáles no matchearon y por qué (TLA distinto, kickoff distinto, etc.).
    """
    return force_sync_now(db)


@router.get("/results-audit")
@limiter.limit("10/minute")
def results_audit(request: Request, db: Session = Depends(get_db)):
    """Compara cada OfficialResult cargado contra football-data.org.

    Resultado: lista con status por partido (ok/mismatch/remote_unfinished/
    remote_not_found/knockout_skipped) + contadores. Útil para auditar que
    los resultados manuales que cargaste coincidan con los oficiales.

    Knockouts no se auditan automáticamente (TLAs son TBD en el FIXTURE).
    """
    return audit_official_results(db)


@router.get("/stats", response_model=AdminStats)
@limiter.limit("30/minute")
def stats(request: Request, db: Session = Depends(get_db)):
    users_count = db.scalar(select(func.count(User.id))) or 0
    predictions_count = db.scalar(select(func.count(Prediction.id))) or 0
    results_count = db.scalar(select(func.count(OfficialResult.match_id))) or 0
    final_picks_count = db.scalar(select(func.count(FinalPick.user_id))) or 0
    official_final = db.get(OfficialFinal, 1)
    return AdminStats(
        users_count=users_count,
        predictions_count=predictions_count,
        official_results_count=results_count,
        final_picks_count=final_picks_count,
        official_final_set=bool(official_final and official_final.champion),
    )


@router.get("/users", response_model=list[UserPrivateOut])
@limiter.limit("30/minute")
def list_users(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.username)).all()
    return [UserPrivateOut.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserPrivateOut)
@limiter.limit("30/minute")
def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdateAdminIn,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.display_name = payload.display_name.strip()
    db.commit()
    db.refresh(user)
    return UserPrivateOut.model_validate(user)
