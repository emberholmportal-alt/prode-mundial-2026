import threading
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..models import CITIES, COMPANIES, FinalPick, OfficialFinal, OfficialResult, Prediction, User
from ..scoring import calc_final_points

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

_CACHE_TTL_SECONDS = 30
# key "general" o nombre de empresa
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


def _compute_leaderboard(db: Session, company: Optional[str], city: Optional[str]) -> list[dict]:
    exact_case = case(
        (
            and_(
                Prediction.home_score == OfficialResult.home_score,
                Prediction.away_score == OfficialResult.away_score,
            ),
            1,
        ),
        else_=0,
    )

    result_case = case(
        (
            and_(
                Prediction.home_score > Prediction.away_score,
                OfficialResult.home_score > OfficialResult.away_score,
            ),
            1,
        ),
        (
            and_(
                Prediction.home_score < Prediction.away_score,
                OfficialResult.home_score < OfficialResult.away_score,
            ),
            1,
        ),
        (
            and_(
                Prediction.home_score == Prediction.away_score,
                OfficialResult.home_score == OfficialResult.away_score,
            ),
            1,
        ),
        else_=0,
    )

    points_case = case(
        (
            and_(
                Prediction.home_score == OfficialResult.home_score,
                Prediction.away_score == OfficialResult.away_score,
            ),
            3,
        ),
        (
            and_(
                Prediction.home_score > Prediction.away_score,
                OfficialResult.home_score > OfficialResult.away_score,
            ),
            1,
        ),
        (
            and_(
                Prediction.home_score < Prediction.away_score,
                OfficialResult.home_score < OfficialResult.away_score,
            ),
            1,
        ),
        (
            and_(
                Prediction.home_score == Prediction.away_score,
                OfficialResult.home_score == OfficialResult.away_score,
            ),
            1,
        ),
        else_=0,
    )

    scored_stmt = (
        select(
            Prediction.user_id.label("user_id"),
            func.coalesce(func.sum(points_case), 0).label("points"),
            func.coalesce(func.sum(exact_case), 0).label("correct_exact"),
            func.coalesce(func.sum(result_case), 0).label("correct_result"),
        )
        .join(OfficialResult, OfficialResult.match_id == Prediction.match_id)
        .group_by(Prediction.user_id)
    )
    scored_by_user = {
        row.user_id: {
            "points": int(row.points or 0),
            "correct_exact": int(row.correct_exact or 0),
            "correct_result": int(row.correct_result or 0),
        }
        for row in db.execute(scored_stmt).all()
    }

    pred_count_stmt = (
        select(Prediction.user_id, func.count(Prediction.id))
        .group_by(Prediction.user_id)
    )
    predicted_by_user = {uid: int(n) for uid, n in db.execute(pred_count_stmt).all()}

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
            }
        )

    rows.sort(key=lambda r: (-r["points"], -r["correct_exact"], r["display_name"].lower()))
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
