from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deadlines import all_match_deadlines, final_pick_deadline_utc
from ..fixtures import FIXTURE, TEAMS
from ..models import KnockoutMatch

router = APIRouter(tags=["fixtures"])


@router.get("/fixtures")
def list_fixtures(db: Session = Depends(get_db)):
    fp_dl = final_pick_deadline_utc().isoformat().replace("+00:00", "Z")
    assignments = {
        km.match_id: {
            "home": km.home_tla,
            "away": km.away_tla,
            "datetime_utc": km.datetime_utc,
            "venue": km.venue,
            "source": km.source,
        }
        for km in db.scalars(select(KnockoutMatch)).all()
    }
    return {
        "matches": FIXTURE,
        "match_deadlines_utc": all_match_deadlines(),
        "final_pick_deadline_utc": fp_dl,
        "knockout_assignments": assignments,
    }


@router.get("/fixtures/teams")
def list_teams():
    return [
        {"code": code, "name": meta["name"], "iso": meta["iso"]}
        for code, meta in sorted(TEAMS.items(), key=lambda kv: kv[1]["name"])
    ]
