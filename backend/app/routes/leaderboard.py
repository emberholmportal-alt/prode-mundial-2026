import threading
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deadlines import get_match_kickoff_utc
from ..fixtures import FIXTURE_BY_ID, apply_knockout_overrides
from ..limiter import limiter
from ..models import CITIES, COMPANIES, FinalPick, OfficialFinal, OfficialResult, Prediction, User
from ..scoring import calc_final_points

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

_CACHE_TTL_SECONDS = 30
# key "general" o nombre de empresa
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


def _passer_tla(home_tla: Optional[str], away_tla: Optional[str],
                h: int, a: int, pen_winner: Optional[str]) -> Optional[str]:
    """Devuelve el TLA del equipo que pasa de fase. None si no se puede determinar."""
    if h > a:
        return (home_tla or "").upper() or None
    if a > h:
        return (away_tla or "").upper() or None
    if pen_winner:
        return pen_winner.upper()
    return None


def _calc_match_points(pred, off, fixture_match) -> tuple[int, bool, bool]:
    """Devuelve (puntos, is_exact, is_result_or_passer) para un partido.

    Grupos:
      3 pts: exact h-a
      1 pt:  ganador o empate correcto
      0 pts: else
    Eliminatorias (90' + alargue):
      3 pts: marcador exacto Y, si fue empate, predijo bien quién pasa por penales
      1 pt:  predijo correctamente quién pasa de fase (sin marcador exacto)
      0 pts: else
    """
    is_knockout = fixture_match.get("phase") != "grupos"
    h_pred, a_pred = pred.home_score, pred.away_score
    h_off, a_off = off.home_score, off.away_score

    if is_knockout:
        home_tla = (fixture_match.get("home") or "").upper()
        away_tla = (fixture_match.get("away") or "").upper()
        pw_pred = (pred.penalty_winner or "").upper() or None
        pw_off = (off.penalty_winner or "").upper() or None
        is_exact = (h_pred == h_off and a_pred == a_off)
        if is_exact and h_pred == a_pred:
            # Empate exacto: requiere también acertar penalty_winner
            is_exact = (pw_pred is not None and pw_off is not None and pw_pred == pw_off)
        passer_pred = _passer_tla(home_tla, away_tla, h_pred, a_pred, pw_pred)
        passer_off = _passer_tla(home_tla, away_tla, h_off, a_off, pw_off)
        is_passer = (passer_pred is not None and passer_off is not None and passer_pred == passer_off)
        if is_exact:
            return (3, True, True)
        if is_passer:
            return (1, False, True)
        return (0, False, False)

    # Grupos
    is_exact = (h_pred == h_off and a_pred == a_off)
    is_result = (
        (h_pred > a_pred and h_off > a_off)
        or (h_pred < a_pred and h_off < a_off)
        or (h_pred == a_pred and h_off == a_off)
    )
    if is_exact:
        return (3, True, True)
    if is_result:
        return (1, False, True)
    return (0, False, False)


def _compute_leaderboard(db: Session, company: Optional[str], city: Optional[str]) -> list[dict]:
    # Aseguramos que los overrides de knockouts estén aplicados en memoria, así
    # _calc_match_points usa home_tla/away_tla correctos para los slots K.
    apply_knockout_overrides(db)

    # Scoring en Python (más simple que CASE WHEN complejo en SQL).
    officials = {o.match_id: o for o in db.scalars(select(OfficialResult)).all()}
    all_preds = db.scalars(select(Prediction)).all()

    scored_by_user: dict[int, dict] = {}
    for p in all_preds:
        off = officials.get(p.match_id)
        if off is None:
            continue
        fx = FIXTURE_BY_ID.get(p.match_id)
        if fx is None:
            continue
        pts, is_exact, is_result = _calc_match_points(p, off, fx)
        s = scored_by_user.setdefault(
            p.user_id, {"points": 0, "correct_exact": 0, "correct_result": 0}
        )
        s["points"] += pts
        if is_exact:
            s["correct_exact"] += 1
        if is_result:
            s["correct_result"] += 1

    pred_count_stmt = (
        select(Prediction.user_id, func.count(Prediction.id))
        .group_by(Prediction.user_id)
    )
    predicted_by_user = {uid: int(n) for uid, n in db.execute(pred_count_stmt).all()}

    # Anticipación promedio por usuario: segundos entre updated_at del pronóstico
    # y el kickoff del partido. Se usa como criterio de desempate (más
    # anticipación = mejor). El kickoff vive en código (FIXTURE), no en DB,
    # así que lo calculamos en Python.
    pred_times_stmt = select(
        Prediction.user_id, Prediction.match_id, Prediction.updated_at
    )
    sum_by_user: dict[int, float] = {}
    n_by_user: dict[int, int] = {}
    for uid, match_id, updated_at in db.execute(pred_times_stmt).all():
        try:
            kickoff = get_match_kickoff_utc(match_id)
        except Exception:
            continue
        # updated_at viene del DB sin tz; lo tratamos como UTC (así está cargado).
        if updated_at.tzinfo is None:
            from datetime import timezone as _tz
            upd = updated_at.replace(tzinfo=_tz.utc)
        else:
            upd = updated_at
        delta = (kickoff - upd).total_seconds()
        # Ignorar valores negativos (edición post-kickoff por algún motivo raro).
        if delta < 0:
            continue
        sum_by_user[uid] = sum_by_user.get(uid, 0.0) + delta
        n_by_user[uid] = n_by_user.get(uid, 0) + 1
    avg_anticipation_by_user: dict[int, float] = {
        uid: sum_by_user[uid] / n_by_user[uid] for uid in sum_by_user
    }

    official_final = db.get(OfficialFinal, 1)
    final_picks_by_user: dict[int, FinalPick] = {}
    if official_final and official_final.champion:
        final_picks_by_user = {
            fp.user_id: fp for fp in db.scalars(select(FinalPick)).all()
        }

    users_stmt = select(User)
    if company:
        users_stmt = users_stmt.where(User.company == company)
    if city:
        users_stmt = users_stmt.where(User.city == city)
    users = db.scalars(users_stmt).all()

    rows: list[dict] = []
    for u in users:
        scored = scored_by_user.get(u.id, {"points": 0, "correct_exact": 0, "correct_result": 0})
        total = scored["points"]
        if official_final and official_final.champion:
            pick = final_picks_by_user.get(u.id)
            if pick:
                total += calc_final_points(
                    pick.champion,
                    pick.runner_up,
                    official_final.champion,
                    official_final.runner_up,
                )

        rows.append(
            {
                "username": u.username,
                "display_name": u.display_name,
                "company": u.company,
                "city": u.city,
                "avatar_config": u.avatar_config,
                "points": total,
                "predicted_count": predicted_by_user.get(u.id, 0),
                "correct_exact": scored["correct_exact"],
                "correct_result": scored["correct_result"],
                "avg_anticipation_seconds": avg_anticipation_by_user.get(u.id),
            }
        )

    # Orden:
    # 1) puntos DESC
    # 2) aciertos exactos DESC
    # 3) aciertos al resultado DESC
    # 4) anticipación promedio DESC (sin datos = peor)
    # 5) display_name ASC (último recurso)
    rows.sort(
        key=lambda r: (
            -r["points"],
            -r["correct_exact"],
            -r["correct_result"],
            -(r["avg_anticipation_seconds"] or 0.0),
            r["display_name"].lower(),
        )
    )
    return rows


@router.get("")
@limiter.limit("120/minute")
def leaderboard(
    request: Request,
    company: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    if company is not None and company not in COMPANIES:
        raise HTTPException(status_code=400, detail="company inválida")
    if city is not None and city not in CITIES:
        raise HTTPException(status_code=400, detail="city inválida")

    key = f"co={company or '-'}::ci={city or '-'}"
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (now - entry["at"]) < _CACHE_TTL_SECONDS:
            return entry["payload"]

    payload = _compute_leaderboard(db, company, city)

    with _cache_lock:
        _cache[key] = {"at": time.monotonic(), "payload": payload}

    return payload
