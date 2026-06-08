"""Endpoints del usuario logueado para su propio perfil/preferencias."""
import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..limiter import limiter
from ..models import User
from ..schemas import AvatarConfigIn, AvatarConfigOut, UserOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/avatar", response_model=AvatarConfigOut)
@limiter.limit("60/minute")
def get_my_avatar(request: Request, user: User = Depends(get_current_user)):
    return AvatarConfigOut(avatar_config=user.avatar_config)


@router.put("/avatar", response_model=UserOut)
@limiter.limit("30/minute")
def update_my_avatar(
    request: Request,
    payload: AvatarConfigIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Guardamos el dict serializado a JSON; quita None para mantener el blob
    # liviano y dejar al frontend usar defaults de DiceBear.
    data = payload.model_dump(exclude_none=True)
    user.avatar_config = json.dumps(data, ensure_ascii=False, sort_keys=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
