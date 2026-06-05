from datetime import datetime, timezone

from fastapi import HTTPException

from .fixtures import FIXTURE, FIXTURE_BY_ID, PHASES_ORDER


def _compute_phase_deadlines() -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for phase in PHASES_ORDER:
        matches_in_phase = [m for m in FIXTURE if m["phase"] == phase]
        if not matches_in_phase:
            continue
        first_dt = min(
            datetime.fromisoformat(m["datetime_utc"].replace("Z", "+00:00"))
            for m in matches_in_phase
        )
        result[phase] = first_dt
    return result


_PHASE_DEADLINES_UTC: dict[str, datetime] = _compute_phase_deadlines()


def phase_deadline_utc(phase: str) -> datetime:
    if phase not in _PHASE_DEADLINES_UTC:
        raise ValueError(f"Fase desconocida: {phase}")
    return _PHASE_DEADLINES_UTC[phase]


def is_phase_locked(phase: str) -> bool:
    return datetime.now(timezone.utc) >= phase_deadline_utc(phase)


def get_match_phase(match_id: str) -> str:
    m = FIXTURE_BY_ID.get(match_id)
    if m is None:
        raise ValueError(f"match_id no existe: {match_id}")
    return m["phase"]


def ensure_match_open(match_id: str) -> None:
    m = FIXTURE_BY_ID.get(match_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"match_id no existe: {match_id}")
    if is_phase_locked(m["phase"]):
        raise HTTPException(status_code=403, detail="La fase ya cerró")


def ensure_final_pick_open() -> None:
    if is_phase_locked("semis"):
        raise HTTPException(status_code=403, detail="La fase ya cerró")


def all_phase_deadlines() -> dict[str, str]:
    return {
        phase: dt.isoformat().replace("+00:00", "Z")
        for phase, dt in _PHASE_DEADLINES_UTC.items()
    }
