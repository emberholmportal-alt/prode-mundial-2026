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
from sqlalchemy import select
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
    diag = _sync_with_diagnostics(db, remote_matches)
    return diag["synced"]


def _sync_with_diagnostics(db: Session, remote_matches: list[dict]) -> dict:
    """Igual que _sync_finished_results pero devuelve detalle del por qué no
    matchearon ciertos partidos FINISHED. Útil para el endpoint admin de debug.
    """
    out: dict = {
        "synced": 0,
        "finished_total": 0,
        "already_loaded": 0,
        "unmatched": [],   # FINISHED que no encontraron pareja en el FIXTURE
    }
    if not remote_matches:
        return out
    try:
        for rm in remote_matches:
            status = (rm.get("status") or "").upper()
            if status != "FINISHED":
                continue
            out["finished_total"] += 1
            hs, as_ = rm.get("home_score"), rm.get("away_score")
            home_tla = (rm.get("home_tla") or "").upper()
            away_tla = (rm.get("away_tla") or "").upper()
            kickoff = rm.get("utc_kickoff")
            base_info = {
                "home_tla": home_tla,
                "away_tla": away_tla,
                "utc_kickoff": kickoff,
                "home_score": hs,
                "away_score": as_,
            }
            if hs is None or as_ is None:
                out["unmatched"].append({**base_info, "reason": "sin scores"})
                continue
            if not (home_tla and away_tla and kickoff):
                out["unmatched"].append({**base_info, "reason": "datos incompletos"})
                continue
            key = (home_tla, away_tla, kickoff)
            match_id = _MATCH_LOOKUP.get(key)
            if match_id is None:
                # Probamos un fallback laxo: solo por par de TLAs (cualquier kickoff)
                fallback = [mid for (h, a, _ko), mid in _MATCH_LOOKUP.items()
                            if h == home_tla and a == away_tla]
                if fallback:
                    out["unmatched"].append({
                        **base_info,
                        "reason": "kickoff no coincide",
                        "fixture_match_id_por_tla": fallback[0],
                    })
                else:
                    out["unmatched"].append({**base_info, "reason": "TLAs no matchean FIXTURE"})
                continue
            existing = db.get(OfficialResult, match_id)
            if existing is not None:
                out["already_loaded"] += 1
                continue
            db.add(OfficialResult(
                match_id=match_id,
                home_score=int(hs),
                away_score=int(as_),
                auto_loaded=True,
            ))
            out["synced"] += 1
        if out["synced"] > 0:
            db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        out["error"] = str(e)
    return out


def force_sync_now(db: Session) -> dict:
    """Limpia cache, refetcha y corre el sync. Devuelve diagnóstico completo."""
    with _lock:
        _cache["payload"] = None
        _cache["at"] = 0.0
        _cache["error"] = None
    remote = _fetch_remote()
    diag = _sync_with_diagnostics(db, remote or [])
    with _lock:
        _cache["payload"] = remote
        _cache["at"] = time.monotonic()
        last_error = _cache.get("error")
    return {
        "token_present": bool(FOOTBALL_DATA_TOKEN),
        "remote_available": remote is not None,
        "remote_count": len(remote) if remote else 0,
        "last_error": last_error,
        **diag,
    }


def sync_state_snapshot() -> dict:
    """Snapshot del estado actual sin forzar fetch (usa cache vigente)."""
    with _lock:
        cached = _cache.get("payload")
        at = _cache.get("at") or 0.0
        last_error = _cache.get("error")
    age_s = max(0.0, time.monotonic() - at) if at else None
    finished_count = 0
    if cached:
        finished_count = sum(1 for rm in cached if (rm.get("status") or "").upper() == "FINISHED")
    return {
        "token_present": bool(FOOTBALL_DATA_TOKEN),
        "remote_available": cached is not None,
        "remote_count": len(cached) if cached else 0,
        "remote_finished_count": finished_count,
        "cache_age_seconds": round(age_s, 1) if age_s is not None else None,
        "last_error": last_error,
    }


def audit_official_results(db: Session) -> dict:
    """Compara cada OfficialResult contra football-data.org para detectar
    discrepancias entre lo cargado (manual o auto) y lo que muestra la API.

    Solo audita partidos de fase de grupos (los knockouts no tienen TLAs
    concretos en nuestro FIXTURE hasta que se decidan, así que no podemos
    matchearlos contra football-data automáticamente).
    """
    # Refrescamos si el cache está vencido para tener data lo más nueva posible.
    with _lock:
        cached = _cache.get("payload")
        at = _cache.get("at") or 0.0
    fresh = cached and (time.monotonic() - at) < _API_TTL
    if not fresh:
        cached = _fetch_remote()
        with _lock:
            _cache["payload"] = cached
            _cache["at"] = time.monotonic()

    # Index remoto por par (home_tla, away_tla) — único en fase de grupos
    remote_by_pair: dict[tuple[str, str], dict] = {}
    for rm in cached or []:
        h = (rm.get("home_tla") or "").upper()
        a = (rm.get("away_tla") or "").upper()
        if not h or not a:
            continue
        remote_by_pair[(h, a)] = rm

    fixture_by_id = {m["id"]: m for m in FIXTURE}
    all_official = db.scalars(select(OfficialResult)).all()
    rows: list[dict] = []
    counts = {
        "ok": 0,
        "mismatch": 0,
        "remote_not_found": 0,
        "remote_unfinished": 0,
        "knockout_skipped": 0,
        "fixture_not_found": 0,
    }

    for off in all_official:
        fx = fixture_by_id.get(off.match_id)
        if fx is None:
            counts["fixture_not_found"] += 1
            rows.append({
                "match_id": off.match_id,
                "status": "fixture_not_found",
                "manual_home": off.home_score,
                "manual_away": off.away_score,
                "auto_loaded": bool(off.auto_loaded),
            })
            continue
        if fx.get("phase") != "grupos":
            counts["knockout_skipped"] += 1
            rows.append({
                "match_id": off.match_id,
                "phase": fx.get("phase"),
                "home_tla": fx["home"], "away_tla": fx["away"],
                "manual_home": off.home_score,
                "manual_away": off.away_score,
                "auto_loaded": bool(off.auto_loaded),
                "status": "knockout_skipped",
            })
            continue

        h_tla = fx["home"].upper()
        a_tla = fx["away"].upper()
        rm = remote_by_pair.get((h_tla, a_tla))
        base = {
            "match_id": off.match_id,
            "home_tla": h_tla,
            "away_tla": a_tla,
            "kickoff_utc": fx.get("datetime_utc"),
            "manual_home": off.home_score,
            "manual_away": off.away_score,
            "auto_loaded": bool(off.auto_loaded),
        }
        if rm is None:
            counts["remote_not_found"] += 1
            rows.append({**base, "status": "remote_not_found"})
            continue
        rstatus = (rm.get("status") or "").upper()
        rh, ra = rm.get("home_score"), rm.get("away_score")
        if rstatus != "FINISHED" or rh is None or ra is None:
            counts["remote_unfinished"] += 1
            rows.append({**base, "status": "remote_unfinished", "remote_status": rstatus})
            continue
        if int(rh) == int(off.home_score) and int(ra) == int(off.away_score):
            counts["ok"] += 1
            rows.append({**base, "status": "ok", "remote_home": int(rh), "remote_away": int(ra)})
        else:
            counts["mismatch"] += 1
            rows.append({
                **base,
                "status": "mismatch",
                "remote_home": int(rh),
                "remote_away": int(ra),
            })

    # Ordenar: primero mismatches, después remote_unfinished/not_found, después ok, después knockouts.
    order = {"mismatch": 0, "remote_unfinished": 1, "remote_not_found": 2, "fixture_not_found": 3, "ok": 4, "knockout_skipped": 5}
    rows.sort(key=lambda r: (order.get(r["status"], 9), r.get("match_id") or ""))

    return {
        "token_present": bool(FOOTBALL_DATA_TOKEN),
        "remote_available": cached is not None,
        "remote_count": len(cached) if cached else 0,
        "total_audited": len(rows),
        "counts": counts,
        "rows": rows,
    }


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
