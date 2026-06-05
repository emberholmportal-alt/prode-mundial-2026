from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..deadlines import ensure_match_open
from ..limiter import limiter
from ..models import Prediction, User
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
    ensure_match_open(match_id)

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
        )
        db.add(existing)
    else:
        existing.home_score = payload.home_score
        existing.away_score = payload.away_score

    db.commit()
    db.refresh(existing)
    return PredictionOut.model_validate(existing)
