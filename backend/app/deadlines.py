from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .fixtures import FIXTURE, FIXTURE_BY_ID


MATCH_DEADLINE_OFFSET = timedelta(hours=1)


def get_match_kickoff_utc(match_id: str) -> datetime:
    m = FIXTURE_BY_ID.get(match_id)
    if m is None:
        raise ValueError(f"match_id no existe: {match_id}")
    return datetime.fromisoformat(m["datetime_utc"].replace("Z", "+00:00"))


def match_deadline_utc(match_id: str) -> datetime:
    return get_match_kickoff_utc(match_id) - MATCH_DEADLINE_OFFSET


def is_match_locked(match_id: str) -> bool:
    return datetime.now(timezone.utc) >= match_deadline_utc(match_id)


def _compute_final_pick_deadline() -> datetime:
    # Deadline = kickoff exacto del primer partido de cuartos. Le damos a la
    # gente toda la fase de grupos + 16vos + octavos para elegir campeón
    # (evita que un usuario que se registra tarde quede lockeado del 412).
    cuartos = [m for m in FIXTURE if m["phase"] == "cuartos"]
    if not cuartos:
        raise RuntimeError("No hay partidos de cuartos en el FIXTURE")
    return min(
        datetime.fromisoformat(m["datetime_utc"].replace("Z", "+00:00"))
        for m in cuartos
    )


_FINAL_PICK_DEADLINE_UTC: datetime = _compute_final_pick_deadline()


def final_pick_deadline_utc() -> datetime:
    return _FINAL_PICK_DEADLINE_UTC


def is_final_pick_locked() -> bool:
    return datetime.now(timezone.utc) >= final_pick_deadline_utc()


def get_match_phase(match_id: str) -> str:
    m = FIXTURE_BY_ID.get(match_id)
    if m is None:
        raise ValueError(f"match_id no existe: {match_id}")
    return m["phase"]


def ensure_match_open(match_id: str) -> None:
    m = FIXTURE_BY_ID.get(match_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"match_id no existe: {match_id}")
    if is_match_locked(match_id):
        raise HTTPException(
            status_code=403,
            detail="La predicción cerró (faltaba 1h para el partido)",
        )


def ensure_final_pick_open() -> None:
    if is_final_pick_locked():
        raise HTTPException(
            status_code=403,
            detail="La elección de campeón/subcampeón ya cerró",
        )


def all_match_deadlines() -> dict[str, str]:
    out: dict[str, str] = {}
    for m in FIXTURE:
        dl = match_deadline_utc(m["id"])
        out[m["id"]] = dl.isoformat().replace("+00:00", "Z")
    return out
