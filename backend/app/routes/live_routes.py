"""Live match polling + auto-sync de OfficialResult cuando un partido FINISHED.

Si FOOTBALL_DATA_TOKEN está definido en el entorno, hace polling cada 60s al
endpoint de football-data.org (`/v4/competitions/WC/matches`) y mapea los
partidos vivos. Si no, devuelve solo el estado calculado desde el FIXTURE
local (kickoff vs ahora).

Como bonus, después del fetch sincroniza con la tabla `official_results`:
para cada partido remoto con status=FINISHED que coincide con un partido
de fase de grupos de nuestro FIXTURE (matcheado por tla home/away + kickoff
UTC) y todavía no tiene OfficialResult en la DB, lo crea con auto_loaded=True.
NO sobreescribe lo que el admin ya cargó manualmente.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..fixtures import FIXTURE
from ..limiter import limiter
from ..models import OfficialResult

router = APIRouter(tags=["live"])

FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
FOOTBALL_DATA_URL = "https://api.football-data.org/v4/competitions/WC/matches"
_API_TTL = 60
_FIXTURE_LIVE_WINDOW = timedelta(hours=2)

_lock = threading.Lock()
_cache: dict[str, Any] = {"at": 0.0, "payload": None, "error": None}


def _fetch_remote() -> Optional[list[dict]]:
    if not FOOTBALL_DATA_TOKEN:
        return None
    req = urllib.request.Request(
        FOOTBALL_DATA_URL,
        headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        with _lock:
            _cache["error"] = str(e)
        return None

    matches = []
    for m in data.get("matches", []):
        status = (m.get("status") or "").upper()
        home = m.get("homeTeam") or {}
        away = m.get("awayTeam") or {}
        score = (m.get("score") or {}).get("fullTime") or {}
        matches.append({
            "remote_id": m.get("id"),
            "utc_kickoff": m.get("utcDate"),
            "status": status,
            "home_name": home.get("name"),
            "home_tla": home.get("tla"),
            "away_name": away.get("name"),
            "away_tla": away.get("tla"),
            "home_score": score.get("home"),
            "away_score": score.get("away"),
            "minute": m.get("minute"),
        })
    return matches


# Lookup (home_tla, away_tla, utc_kickoff) -> match_id, solo fase de grupos
# (los knockouts tienen equipos TBD hasta que se decidan).
def _build_match_lookup() -> dict[tuple[str, str, str], str]:
    lookup: dict[tuple[str, str, str], str] = {}
    for m in FIXTURE:
        if m.get("phase") != "grupos":
            continue
        key = (m["home"].upper(), m["away"].upper(), m["datetime_utc"])
        lookup[key] = m["id"]
    return lookup


_MATCH_LOOKUP: dict[tuple[str, str, str], str] = _build_match_lookup()


def _sync_finished_results(db: Session, remote_matches: list[dict]) -> int:
    """Sincroniza partidos FINISHED de football-data.org con OfficialResult.

    - Solo crea filas nuevas; nunca pisa lo que el admin ya cargó.
    - Solo procesa partidos de fase de grupos (los knockouts tienen TBD).
    - Devuelve la cantidad de filas nuevas insertadas.
    """
    if not remote_matches:
        return 0
    synced = 0
    try:
        for rm in remote_matches:
            status = (rm.get("status") or "").upper()
            if status != "FINISHED":
                continue
            hs, as_ = rm.get("home_score"), rm.get("away_score")
            if hs is None or as_ is None:
                continue
            home_tla = (rm.get("home_tla") or "").upper()
            away_tla = (rm.get("away_tla") or "").upper()
            kickoff = rm.get("utc_kickoff")
            if not (home_tla and away_tla and kickoff):
                continue
            key = (home_tla, away_tla, kickoff)
            match_id = _MATCH_LOOKUP.get(key)
            if match_id is None:
                continue
            # No pisar lo que ya está cargado (manual o auto)
            existing = db.get(OfficialResult, match_id)
            if existing is not None:
                continue
            db.add(OfficialResult(
                match_id=match_id,
                home_score=int(hs),
                away_score=int(as_),
                auto_loaded=True,
            ))
            synced += 1
        if synced > 0:
            db.commit()
    except Exception:
        db.rollback()
        return 0
    return synced


def _local_status(now: datetime) -> dict:
    """Encuentra partidos en curso (kickoff ≤ now ≤ kickoff + 2h) y el próximo."""
    live: list[dict] = []
    upcoming: list[dict] = []
    for m in FIXTURE:
        ko = datetime.fromisoformat(m["datetime_utc"].replace("Z", "+00:00"))
        if ko <= now <= ko + _FIXTURE_LIVE_WINDOW:
            live.append({**m, "minutes_in": int((now - ko).total_seconds() / 60)})
        elif ko > now:
            upcoming.append(m)
    upcoming.sort(key=lambda m: m["datetime_utc"])
    return {
        "live_local": live,
        "next_match": upcoming[0] if upcoming else None,
    }


@router.get("/live")
@limiter.limit("60/minute")
def live_status(request: Request, db: Session = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)
    now = time.monotonic()

    with _lock:
        cached = _cache.get("payload")
        fresh = cached and (now - _cache["at"]) < _API_TTL

    remote_matches = None
    if not fresh:
        remote_matches = _fetch_remote()
        with _lock:
            _cache["payload"] = remote_matches
            _cache["at"] = time.monotonic()
        # Auto-sync de partidos FINISHED → official_results (no pisa manuales)
        if remote_matches:
            _sync_finished_results(db, remote_matches)
    else:
        remote_matches = cached

    local = _local_status(now_utc)

    return {
        "polled_at": now_utc.isoformat().replace("+00:00", "Z"),
        "remote_available": remote_matches is not None,
        "remote_error": _cache.get("error") if remote_matches is None else None,
        "remote_matches": remote_matches or [],
        "live_local": local["live_local"],
        "next_match": local["next_match"],
    }
