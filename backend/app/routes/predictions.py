from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..deadlines import ensure_match_open
from ..fixtures import FIXTURE_BY_ID
from ..limiter import limiter
from ..models import FinalPick, Prediction, User
from ..schemas import PredictionIn, PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/me", response_model=list[PredictionOut])
@limiter.limit("60/minute")
def my_predictions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Prediction).where(Prediction.user_id == user.id)
    ).all()
    return [PredictionOut.model_validate(p) for p in rows]


@router.put("/{match_id}", response_model=PredictionOut)
@limiter.limit("60/minute")
def upsert_prediction(
    request: Request,
    match_id: str,
    payload: PredictionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    final_pick = db.scalar(select(FinalPick).where(FinalPick.user_id == user.id))
    if final_pick is None:
        raise HTTPException(
            status_code=412,
            detail="Tenés que elegir campeón y subcampeón antes de cargar predicciones",
        )

    ensure_match_open(match_id)

    match = FIXTURE_BY_ID.get(match_id)
    is_knockout = match is not None and match.get("phase") != "grupos"
    pw = (payload.penalty_winner or "").upper() or None

    # Validación de penalty_winner: solo aplica para knockouts con empate.
    if pw is not None:
        if not is_knockout:
            raise HTTPException(
                status_code=400,
                detail="penalty_winner solo aplica para partidos de eliminación",
            )
        if payload.home_score != payload.away_score:
            # Si la predicción no es empate, ignoramos penalty_winner silenciosamente.
            pw = None
        else:
            valid = {(match.get("home") or "").upper(), (match.get("away") or "").upper()}
            if pw not in valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"penalty_winner debe ser uno de los equipos del partido: {sorted(valid)}",
                )

    if is_knockout and payload.home_score == payload.away_score and pw is None:
        raise HTTPException(
            status_code=400,
            detail="Para predicciones de empate en eliminación tenés que elegir quién pasa por penales",
        )

    existing = db.scalar(
        select(Prediction).where(
            Prediction.user_id == user.id,
            Prediction.match_id == match_id,
        )
    )
    if existing is None:
        existing = Prediction(
            user_id=user.id,
            match_id=match_id,
            home_score=payload.home_score,
            away_score=payload.away_score,
            penalty_winner=pw,
        )
        db.add(existing)
    else:
        existing.home_score = payload.home_score
        existing.away_score = payload.away_score
        existing.penalty_winner = pw

    db.commit()
    db.refresh(existing)
    return PredictionOut.model_validate(existing)
