from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..deadlines import ensure_final_pick_open
from ..fixtures import TEAMS
from ..limiter import limiter
from ..models import FinalPick, OfficialFinal, User
from ..schemas import FinalPickIn, FinalPickOut

router = APIRouter(prefix="/final-pick", tags=["final-pick"])


@router.get("/me", response_model=FinalPickOut | None)
@limiter.limit("60/minute")
def my_final_pick(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pick = db.scalar(select(FinalPick).where(FinalPick.user_id == user.id))
    if pick is None:
        return None
    return FinalPickOut.model_validate(pick)


@router.put("", response_model=FinalPickOut)
@limiter.limit("60/minute")
def upsert_final_pick(
    request: Request,
    payload: FinalPickIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    champion = payload.champion.upper()
    runner_up = payload.runner_up.upper()

    if champion not in TEAMS or runner_up not in TEAMS:
        raise HTTPException(status_code=400, detail="Código de selección inválido")
    if champion == runner_up:
        raise HTTPException(status_code=400, detail="Campeón y subcampeón no pueden ser iguales")

    official = db.get(OfficialFinal, 1)
    if official is not None and official.champion is not None:
        raise HTTPException(status_code=403, detail="El resultado final ya fue cargado")

    ensure_final_pick_open()

    pick = db.scalar(select(FinalPick).where(FinalPick.user_id == user.id))
    if pick is None:
        pick = FinalPick(user_id=user.id, champion=champion, runner_up=runner_up)
        db.add(pick)
    else:
        pick.champion = champion
        pick.runner_up = runner_up

    db.commit()
    db.refresh(pick)
    return FinalPickOut.model_validate(pick)
