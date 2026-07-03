"""Endpoint público de auditoría de actividad de usuarios.

Para que cualquier usuario pueda verificar la última fecha de modificación
de las predicciones de cualquier otro (transparencia ante el admin que
tiene acceso a la DB). Solo expone metadata (count + last_modified_at),
nunca el contenido de las predicciones."""
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..fixtures import FIXTURE_BY_ID, TEAMS, apply_knockout_overrides
from ..limiter import limiter
from ..models import OfficialResult, Prediction, User
from .leaderboard import _calc_match_points

router = APIRouter(prefix="/audit", tags=["audit"])

_PHASE_LABELS = {
    "grupos": "Grupos", "dieciseisavos": "16vos", "octavos": "Octavos",
    "cuartos": "Cuartos", "semis": "Semis", "tercerpuesto": "3er Puesto", "final": "Final",
}

_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {"at": 0.0, "payload": None}
_cache_lock = threading.Lock()


def _compute_audit(db: Session) -> list[dict]:
    # Por usuario: cantidad total de predicciones, última modificación global,
    # y última modificación por fase (grupos / dieciseisavos / octavos / cuartos
    # / semis / tercerpuesto / final). Se agrega en Python porque la "fase" de
    # cada match no está en la DB (vive en el FIXTURE local).
    stmt = (
        select(
            User.id,
            User.username,
            User.display_name,
            Prediction.match_id,
            Prediction.updated_at,
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
    )

    per_user: dict[int, dict] = {}
    for r in db.execute(stmt).all():
        u = per_user.setdefault(r.id, {
            "username": r.username,
            "display_name": r.display_name,
            "predictions_count": 0,
            "last_modified_at": None,
            "by_phase": {},  # phase -> datetime
        })
        if r.match_id is None or r.updated_at is None:
            continue
        u["predictions_count"] += 1
        ts = r.updated_at
        if u["last_modified_at"] is None or ts > u["last_modified_at"]:
            u["last_modified_at"] = ts
        m = FIXTURE_BY_ID.get(r.match_id)
        if m is None:
            continue
        phase = m["phase"]
        cur = u["by_phase"].get(phase)
        if cur is None or ts > cur:
            u["by_phase"][phase] = ts

    def _iso(ts):
        return ts.isoformat() + "Z" if ts else None

    rows = []
    for u in per_user.values():
        rows.append({
            "username": u["username"],
            "display_name": u["display_name"],
            "predictions_count": u["predictions_count"],
            "last_modified_at": _iso(u["last_modified_at"]),
            "by_phase": {phase: _iso(ts) for phase, ts in u["by_phase"].items()},
        })

    # Ordenar: con actividad más reciente primero; sin actividad al final por username
    def _sort_key(r):
        lm = r["last_modified_at"]
        if lm is None:
            return (1, "", r["username"])
        return (0, lm, r["username"])  # mayor ISO string = más reciente
    rows.sort(key=_sort_key, reverse=False)
    # Como queremos más reciente arriba pero sin actividad al final, invertimos
    # los activos y dejamos los inactivos abajo
    actives = [r for r in rows if r["last_modified_at"] is not None]
    inactives = [r for r in rows if r["last_modified_at"] is None]
    actives.sort(key=lambda r: r["last_modified_at"], reverse=True)
    inactives.sort(key=lambda r: r["username"])
    return actives + inactives


@router.get("/users")
@limiter.limit("60/minute")
def audit_users(request: Request, db: Session = Depends(get_db)):
    now = time.monotonic()
    with _cache_lock:
        if _cache["payload"] is not None and (now - _cache["at"]) < _CACHE_TTL_SECONDS:
            return _cache["payload"]
    payload = _compute_audit(db)
    with _cache_lock:
        _cache["at"] = time.monotonic()
        _cache["payload"] = payload
    return payload


def _team_name(tla: str) -> str:
    t = TEAMS.get((tla or "").upper())
    return t["name"] if t else (tla or "?")


@router.get("/users/{username}/detail")
@limiter.limit("60/minute")
def audit_user_detail(username: str, request: Request, db: Session = Depends(get_db)):
    """Detalle transparente de un usuario: por cada partido YA FINALIZADO
    (con resultado oficial cargado), muestra qué pronosticó, cómo salió,
    cuántos puntos sumó y cuándo cargó/modificó ese pronóstico.

    Solo partidos finalizados → no se filtra info de partidos futuros.
    """
    apply_knockout_overrides(db)

    uname = (username or "").strip().lower()
    user = db.scalar(select(User).where(func.lower(User.username) == uname))
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Partidos finalizados = los que tienen OfficialResult cargado.
    officials = {o.match_id: o for o in db.scalars(select(OfficialResult)).all()}
    preds = {
        p.match_id: p
        for p in db.scalars(
            select(Prediction).where(Prediction.user_id == user.id)
        ).all()
    }

    rows = []
    total_points = 0
    for match_id, off in officials.items():
        fx = FIXTURE_BY_ID.get(match_id)
        if fx is None:
            continue
        p = preds.get(match_id)
        pts = 0
        pred_block = None
        pred_ts = None
        if p is not None:
            pts, _exact, _res = _calc_match_points(p, off, fx)
            total_points += pts
            pred_block = {
                "home": p.home_score,
                "away": p.away_score,
                "penalty_winner": p.penalty_winner,
                "penalty_winner_name": _team_name(p.penalty_winner) if p.penalty_winner else None,
            }
            pred_ts = p.updated_at.isoformat() + "Z" if p.updated_at else None

        rows.append({
            "match_id": match_id,
            "phase": fx.get("phase"),
            "phase_label": _PHASE_LABELS.get(fx.get("phase"), fx.get("phase")),
            "home_tla": fx.get("home"),
            "away_tla": fx.get("away"),
            "home_name": _team_name(fx.get("home")),
            "away_name": _team_name(fx.get("away")),
            "kickoff_utc": fx.get("datetime_utc"),
            "official": {
                "home": off.home_score,
                "away": off.away_score,
                "penalty_winner": off.penalty_winner,
                "penalty_winner_name": _team_name(off.penalty_winner) if off.penalty_winner else None,
            },
            "prediction": pred_block,
            "prediction_updated_at": pred_ts,
            "points": pts,
        })

    # Orden cronológico por kickoff.
    rows.sort(key=lambda r: r.get("kickoff_utc") or "")

    return {
        "username": user.username,
        "display_name": user.display_name,
        "company": user.company,
        "city": user.city,
        "finished_matches": len(rows),
        "predicted_count": sum(1 for r in rows if r["prediction"] is not None),
        "total_points": total_points,
        "rows": rows,
    }
