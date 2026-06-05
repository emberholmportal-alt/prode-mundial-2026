from fastapi import APIRouter

from ..deadlines import all_match_deadlines, final_pick_deadline_utc
from ..fixtures import FIXTURE, TEAMS

router = APIRouter(tags=["fixtures"])


@router.get("/fixtures")
def list_fixtures():
    fp_dl = final_pick_deadline_utc().isoformat().replace("+00:00", "Z")
    return {
        "matches": FIXTURE,
        "match_deadlines_utc": all_match_deadlines(),
        "final_pick_deadline_utc": fp_dl,
    }


@router.get("/fixtures/teams")
def list_teams():
    return [
        {"code": code, "name": meta["name"], "iso": meta["iso"]}
        for code, meta in sorted(TEAMS.items(), key=lambda kv: kv[1]["name"])
    ]
