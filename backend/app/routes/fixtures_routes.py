from fastapi import APIRouter

from ..deadlines import all_phase_deadlines
from ..fixtures import FIXTURE, TEAMS

router = APIRouter(tags=["fixtures"])


@router.get("/fixtures")
def list_fixtures():
    return {
        "matches": FIXTURE,
        "deadlines_utc": all_phase_deadlines(),
    }


@router.get("/fixtures/teams")
def list_teams():
    return [
        {"code": code, "name": meta["name"], "iso": meta["iso"]}
        for code, meta in sorted(TEAMS.items(), key=lambda kv: kv[1]["name"])
    ]
