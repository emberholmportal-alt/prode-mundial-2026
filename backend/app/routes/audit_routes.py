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
from ..fixtures import FIXTURE_BY_ID
from ..limiter import limiter
from ..models import Prediction, User

router = APIRouter(prefix="/audit", tags=["audit"])

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
