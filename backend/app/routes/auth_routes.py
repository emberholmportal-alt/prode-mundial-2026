from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    is_admin_username,
    validate_username,
    verify_password,
)
from ..database import get_db
from ..limiter import limiter
from ..models import User
from ..schemas import AuthOut, LoginIn, RegisterIn, UserPrivateOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_dni(dni: str) -> str:
    return "".join(ch for ch in dni if ch.isdigit())


@router.post("/register", response_model=AuthOut)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterIn, db: Session = Depends(get_db)):
    username = validate_username(payload.username)
    dni = _normalize_dni(payload.dni)
    if not (7 <= len(dni) <= 10):
        raise HTTPException(status_code=400, detail="DNI inválido: 7 a 10 dígitos")
    email = str(payload.email).strip().lower()
    sector = payload.sector.strip()
    display_name = payload.display_name.strip()

    if db.scalar(select(User).where(User.username == username)) is not None:
        raise HTTPException(status_code=409, detail="Username ya registrado")
    if db.scalar(select(User).where(User.dni == dni)) is not None:
        raise HTTPException(status_code=409, detail="DNI ya registrado")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        display_name=display_name,
        is_admin=is_admin_username(username),
        dni=dni,
        email=email,
        sector=sector,
        company=payload.company,
        city=payload.city,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig).lower() if e.orig else ""
        if "dni" in msg:
            raise HTTPException(status_code=409, detail="DNI ya registrado")
        if "email" in msg:
            raise HTTPException(status_code=409, detail="Email ya registrado")
        if "username" in msg:
            raise HTTPException(status_code=409, detail="Username ya registrado")
        raise HTTPException(status_code=409, detail="Datos duplicados")

    db.refresh(user)
    token = create_access_token(user.id)
    return AuthOut(access_token=token, user=UserPrivateOut.model_validate(user))


@router.post("/login", response_model=AuthOut)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = create_access_token(user.id)
    return AuthOut(access_token=token, user=UserPrivateOut.model_validate(user))


@router.get("/me", response_model=UserPrivateOut)
def me(user: User = Depends(get_current_user)):
    return UserPrivateOut.model_validate(user)
