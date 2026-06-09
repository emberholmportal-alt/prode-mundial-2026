"""Endpoint público de auditoría de actividad de usuarios.

Para que cualquier usuario pueda verificar la última fecha de modificación
de las predicciones de cualquier otro (transparencia ante el admin que
tiene acceso a la DB). Solo expone metadata (count + last_modified_at),
nunca el contenido de las predicciones."""
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..models import Prediction, User

router = APIRouter(prefix="/audit", tags=["audit"])

_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {"at": 0.0, "payload": None}
_cache_lock = threading.Lock()


def _compute_audit(db: Session) -> list[dict]:
    stmt = (
        select(
            User.username,
            User.display_name,
            func.count(Prediction.id).label("predictions_count"),
            func.max(Prediction.updated_at).label("last_modified_at"),
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .group_by(User.id, User.username, User.display_name)
    )
    rows = []
    for r in db.execute(stmt).all():
        rows.append({
            "username": r.username,
            "display_name": r.display_name,
            "predictions_count": int(r.predictions_count or 0),
            "last_modified_at": r.last_modified_at.isoformat() + "Z"
                if r.last_modified_at else None,
        })
    # Ordenar: con actividad más reciente primero; sin actividad al final por username
    rows.sort(key=lambda r: (
        r["last_modified_at"] is None,
        -(0 if r["last_modified_at"] is None
          else int(r["last_modified_at"].replace("-", "").replace(":", "").replace("T", "").replace("Z", "")[:14])),
        r["username"],
    ))
    return rows


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
