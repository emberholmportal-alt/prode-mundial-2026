from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict


TEAMS: dict[str, dict[str, str]] = {
    "MEX": {"name": "México", "iso": "mx"},
    "RSA": {"name": "Sudáfrica", "iso": "za"},
    "KOR": {"name": "Corea del Sur", "iso": "kr"},
    "CZE": {"name": "Rep. Checa", "iso": "cz"},
    "CAN": {"name": "Canadá", "iso": "ca"},
    "BIH": {"name": "Bosnia", "iso": "ba"},
    "QAT": {"name": "Catar", "iso": "qa"},
    "SUI": {"name": "Suiza", "iso": "ch"},
    "BRA": {"name": "Brasil", "iso": "br"},
    "MAR": {"name": "Marruecos", "iso": "ma"},
    "HAI": {"name": "Haití", "iso": "ht"},
    "SCO": {"name": "Escocia", "iso": "gb-sct"},
    "USA": {"name": "EE.UU.", "iso": "us"},
    "PAR": {"name": "Paraguay", "iso": "py"},
    "AUS": {"name": "Australia", "iso": "au"},
    "TUR": {"name": "Turquía", "iso": "tr"},
    "GER": {"name": "Alemania", "iso": "de"},
    "CUW": {"name": "Curazao", "iso": "cw"},
    "CIV": {"name": "Costa de Marfil", "iso": "ci"},
    "ECU": {"name": "Ecuador", "iso": "ec"},
    "NED": {"name": "Países Bajos", "iso": "nl"},
    "JPN": {"name": "Japón", "iso": "jp"},
    "SWE": {"name": "Suecia", "iso": "se"},
    "TUN": {"name": "Túnez", "iso": "tn"},
    "BEL": {"name": "Bélgica", "iso": "be"},
    "EGY": {"name": "Egipto", "iso": "eg"},
    "IRN": {"name": "Irán", "iso": "ir"},
    "NZL": {"name": "Nueva Zelanda", "iso": "nz"},
    "ESP": {"name": "España", "iso": "es"},
    "CPV": {"name": "Cabo Verde", "iso": "cv"},
    "KSA": {"name": "Arabia Saudita", "iso": "sa"},
    "URU": {"name": "Uruguay", "iso": "uy"},
    "FRA": {"name": "Francia", "iso": "fr"},
    "SEN": {"name": "Senegal", "iso": "sn"},
    "IRQ": {"name": "Irak", "iso": "iq"},
    "NOR": {"name": "Noruega", "iso": "no"},
    "ARG": {"name": "Argentina", "iso": "ar"},
    "ALG": {"name": "Argelia", "iso": "dz"},
    "AUT": {"name": "Austria", "iso": "at"},
    "JOR": {"name": "Jordania", "iso": "jo"},
    "POR": {"name": "Portugal", "iso": "pt"},
    "COD": {"name": "RD Congo", "iso": "cd"},
    "UZB": {"name": "Uzbekistán", "iso": "uz"},
    "COL": {"name": "Colombia", "iso": "co"},
    "ENG": {"name": "Inglaterra", "iso": "gb-eng"},
    "CRO": {"name": "Croacia", "iso": "hr"},
    "GHA": {"name": "Ghana", "iso": "gh"},
    "PAN": {"name": "Panamá", "iso": "pa"},
}

GROUPS: dict[str, list[str]] = {
    "A": ["MEX", "RSA", "KOR", "CZE"],
    "B": ["CAN", "BIH", "QAT", "SUI"],
    "C": ["BRA", "MAR", "HAI", "SCO"],
    "D": ["USA", "PAR", "AUS", "TUR"],
    "E": ["GER", "CUW", "CIV", "ECU"],
    "F": ["NED", "JPN", "SWE", "TUN"],
    "G": ["BEL", "EGY", "IRN", "NZL"],
    "H": ["ESP", "CPV", "KSA", "URU"],
    "I": ["FRA", "SEN", "IRQ", "NOR"],
    "J": ["ARG", "ALG", "AUT", "JOR"],
    "K": ["POR", "COD", "UZB", "COL"],
    "L": ["ENG", "CRO", "GHA", "PAN"],
}


class Match(TypedDict):
    id: str
    phase: str
    group: Optional[str]
    home: str
    away: str
    datetime_art: str
    datetime_utc: str
    venue: str


_GROUP_RAW: list[tuple[str, str, str, str, str, str]] = [
    ("A", "MEX", "RSA", "2026-06-11", "16:00", "Estadio Azteca, Ciudad de México"),
    ("A", "KOR", "CZE", "2026-06-11", "23:00", "Estadio Akron, Guadalajara"),
    ("B", "CAN", "BIH", "2026-06-12", "16:00", "BMO Field, Toronto"),
    ("D", "USA", "PAR", "2026-06-12", "22:00", "SoFi Stadium, Los Ángeles"),
    ("B", "QAT", "SUI", "2026-06-13", "16:00", "Levi's Stadium, San Francisco"),
    ("C", "BRA", "MAR", "2026-06-13", "19:00", "MetLife Stadium, Nueva Jersey"),
    ("C", "HAI", "SCO", "2026-06-13", "22:00", "Gillette Stadium, Boston"),
    ("D", "AUS", "TUR", "2026-06-14", "01:00", "BC Place, Vancouver"),
    ("E", "GER", "CUW", "2026-06-14", "14:00", "NRG Stadium, Houston"),
    ("F", "NED", "JPN", "2026-06-14", "17:00", "AT&T Stadium, Dallas"),
    ("E", "CIV", "ECU", "2026-06-14", "20:00", "Lincoln Financial Field, Philadelphia"),
    ("F", "SWE", "TUN", "2026-06-14", "23:00", "Estadio BBVA, Monterrey"),
    ("H", "ESP", "CPV", "2026-06-15", "13:00", "Mercedes-Benz Stadium, Atlanta"),
    ("G", "BEL", "EGY", "2026-06-15", "16:00", "Lumen Field, Seattle"),
    ("H", "KSA", "URU", "2026-06-15", "19:00", "Hard Rock Stadium, Miami"),
    ("G", "IRN", "NZL", "2026-06-15", "22:00", "SoFi Stadium, Los Ángeles"),
    ("I", "FRA", "SEN", "2026-06-16", "16:00", "MetLife Stadium, Nueva Jersey"),
    ("I", "IRQ", "NOR", "2026-06-16", "19:00", "Gillette Stadium, Boston"),
    ("J", "ARG", "ALG", "2026-06-16", "22:00", "Arrowhead Stadium, Kansas City"),
    ("J", "AUT", "JOR", "2026-06-17", "01:00", "Levi's Stadium, San Francisco"),
    ("K", "POR", "COD", "2026-06-17", "14:00", "NRG Stadium, Houston"),
    ("L", "ENG", "CRO", "2026-06-17", "17:00", "AT&T Stadium, Dallas"),
    ("L", "GHA", "PAN", "2026-06-17", "20:00", "BMO Field, Toronto"),
    ("K", "UZB", "COL", "2026-06-17", "23:00", "Estadio Azteca, Ciudad de México"),
    ("A", "CZE", "RSA", "2026-06-18", "13:00", "Mercedes-Benz Stadium, Atlanta"),
    ("B", "SUI", "BIH", "2026-06-18", "16:00", "SoFi Stadium, Los Ángeles"),
    ("B", "CAN", "QAT", "2026-06-18", "19:00", "BC Place, Vancouver"),
    ("A", "MEX", "KOR", "2026-06-18", "22:00", "Estadio Akron, Guadalajara"),
    ("D", "USA", "AUS", "2026-06-19", "16:00", "Lumen Field, Seattle"),
    ("C", "SCO", "MAR", "2026-06-19", "19:00", "Gillette Stadium, Boston"),
    ("C", "BRA", "HAI", "2026-06-19", "21:30", "Lincoln Financial Field, Philadelphia"),
    ("D", "TUR", "PAR", "2026-06-20", "00:00", "Levi's Stadium, San Francisco"),
    ("F", "NED", "SWE", "2026-06-20", "14:00", "NRG Stadium, Houston"),
    ("E", "GER", "CIV", "2026-06-20", "17:00", "BMO Field, Toronto"),
    ("E", "ECU", "CUW", "2026-06-20", "23:00", "Arrowhead Stadium, Kansas City"),
    ("F", "TUN", "JPN", "2026-06-21", "01:00", "Estadio BBVA, Monterrey"),
    ("H", "ESP", "KSA", "2026-06-21", "13:00", "Mercedes-Benz Stadium, Atlanta"),
    ("G", "BEL", "IRN", "2026-06-21", "16:00", "SoFi Stadium, Los Ángeles"),
    ("H", "URU", "CPV", "2026-06-21", "19:00", "Hard Rock Stadium, Miami"),
    ("G", "NZL", "EGY", "2026-06-21", "22:00", "BC Place, Vancouver"),
    ("J", "ARG", "AUT", "2026-06-22", "14:00", "AT&T Stadium, Dallas"),
    ("I", "FRA", "IRQ", "2026-06-22", "18:00", "Lincoln Financial Field, Philadelphia"),
    ("I", "NOR", "SEN", "2026-06-22", "21:00", "MetLife Stadium, Nueva Jersey"),
    ("J", "JOR", "ALG", "2026-06-23", "00:00", "Levi's Stadium, San Francisco"),
    ("K", "POR", "UZB", "2026-06-23", "14:00", "NRG Stadium, Houston"),
    ("L", "ENG", "GHA", "2026-06-23", "17:00", "Gillette Stadium, Boston"),
    ("L", "PAN", "CRO", "2026-06-23", "20:00", "BMO Field, Toronto"),
    ("K", "COL", "COD", "2026-06-23", "23:00", "Estadio Akron, Guadalajara"),
    ("B", "SUI", "CAN", "2026-06-24", "16:00", "BC Place, Vancouver"),
    ("B", "BIH", "QAT", "2026-06-24", "16:00", "Lumen Field, Seattle"),
    ("C", "SCO", "BRA", "2026-06-24", "19:00", "Hard Rock Stadium, Miami"),
    ("C", "MAR", "HAI", "2026-06-24", "19:00", "Mercedes-Benz Stadium, Atlanta"),
    ("A", "RSA", "KOR", "2026-06-24", "22:00", "Estadio BBVA, Monterrey"),
    ("A", "CZE", "MEX", "2026-06-24", "22:00", "Estadio Azteca, Ciudad de México"),
    ("F", "JPN", "SWE", "2026-06-25", "16:00", "AT&T Stadium, Dallas"),
    ("F", "TUN", "NED", "2026-06-25", "16:00", "NRG Stadium, Houston"),
    ("E", "CUW", "GER", "2026-06-25", "19:00", "Estadio Akron, Guadalajara"),
    ("E", "ECU", "CIV", "2026-06-25", "19:00", "Lincoln Financial Field, Philadelphia"),
    ("D", "TUR", "USA", "2026-06-25", "23:00", "SoFi Stadium, Los Ángeles"),
    ("D", "PAR", "AUS", "2026-06-25", "23:00", "Levi's Stadium, San Francisco"),
    ("I", "NOR", "FRA", "2026-06-26", "16:00", "Gillette Stadium, Boston"),
    ("I", "SEN", "IRQ", "2026-06-26", "16:00", "BMO Field, Toronto"),
    ("H", "CPV", "KSA", "2026-06-26", "20:00", "NRG Stadium, Houston"),
    ("H", "URU", "ESP", "2026-06-26", "20:00", "Estadio Akron, Guadalajara"),
    ("G", "EGY", "IRN", "2026-06-26", "23:00", "Lumen Field, Seattle"),
    ("G", "NZL", "BEL", "2026-06-26", "23:00", "BC Place, Vancouver"),
    ("L", "CRO", "ENG", "2026-06-27", "17:00", "AT&T Stadium, Dallas"),
    ("L", "PAN", "GHA", "2026-06-27", "17:00", "MetLife Stadium, Nueva Jersey"),
    ("K", "COD", "POR", "2026-06-27", "20:00", "Hard Rock Stadium, Miami"),
    ("K", "COL", "UZB", "2026-06-27", "20:00", "Mercedes-Benz Stadium, Atlanta"),
    ("J", "ALG", "AUT", "2026-06-27", "23:00", "Arrowhead Stadium, Kansas City"),
    ("J", "JOR", "ARG", "2026-06-27", "23:00", "AT&T Stadium, Dallas"),
]


_KNOCKOUT_PHASES: list[dict] = [
    {
        "key": "dieciseisavos",
        "count": 16,
        "slots": [
            ("2026-06-28", "14:00"), ("2026-06-28", "17:00"),
            ("2026-06-29", "14:00"), ("2026-06-29", "17:00"),
            ("2026-06-29", "20:00"), ("2026-06-29", "23:00"),
            ("2026-06-30", "14:00"), ("2026-06-30", "17:00"),
            ("2026-06-30", "20:00"), ("2026-06-30", "23:00"),
            ("2026-07-01", "14:00"), ("2026-07-01", "17:00"),
            ("2026-07-01", "20:00"), ("2026-07-01", "23:00"),
            ("2026-07-02", "16:00"), ("2026-07-02", "20:00"),
        ],
    },
    {
        "key": "octavos",
        "count": 8,
        "slots": [
            ("2026-07-04", "13:00"), ("2026-07-04", "17:00"),
            ("2026-07-05", "13:00"), ("2026-07-05", "17:00"),
            ("2026-07-06", "13:00"), ("2026-07-06", "17:00"),
            ("2026-07-07", "13:00"), ("2026-07-07", "17:00"),
        ],
    },
    {
        "key": "cuartos",
        "count": 4,
        "slots": [
            ("2026-07-09", "16:00"), ("2026-07-09", "20:00"),
            ("2026-07-11", "13:00"), ("2026-07-11", "17:00"),
        ],
    },
    {
        "key": "semis",
        "count": 2,
        "slots": [("2026-07-14", "16:00"), ("2026-07-15", "16:00")],
    },
    {
        "key": "tercerpuesto",
        "count": 1,
        "slots": [("2026-07-18", "16:00")],
    },
    {
        "key": "final",
        "count": 1,
        "slots": [("2026-07-19", "16:00")],
    },
]


PHASES_ORDER = [
    "grupos",
    "dieciseisavos",
    "octavos",
    "cuartos",
    "semis",
    "tercerpuesto",
    "final",
]


def _art_to_utc_iso(date_str: str, time_str: str) -> tuple[str, str]:
    art_naive = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    utc = art_naive + timedelta(hours=3)
    return (
        art_naive.isoformat(),
        utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def _build_fixture() -> list[Match]:
    matches: list[Match] = []
    for idx, (group, home, away, date_str, time_str, venue) in enumerate(_GROUP_RAW, start=1):
        art_iso, utc_iso = _art_to_utc_iso(date_str, time_str)
        matches.append(
            Match(
                id=f"G{idx}",
                phase="grupos",
                group=group,
                home=home,
                away=away,
                datetime_art=art_iso,
                datetime_utc=utc_iso,
                venue=venue,
            )
        )

    kid = 1
    for phase in _KNOCKOUT_PHASES:
        slots = phase["slots"]
        for i in range(phase["count"]):
            date_str, time_str = slots[i] if i < len(slots) else slots[-1]
            art_iso, utc_iso = _art_to_utc_iso(date_str, time_str)
            matches.append(
                Match(
                    id=f"K{kid}",
                    phase=phase["key"],
                    group=None,
                    home="TBD",
                    away="TBD",
                    datetime_art=art_iso,
                    datetime_utc=utc_iso,
                    venue="Por confirmar",
                )
            )
            kid += 1
    return matches


FIXTURE: list[Match] = _build_fixture()
FIXTURE_BY_ID: dict[str, Match] = {m["id"]: m for m in FIXTURE}


def get_match(match_id: str) -> Optional[Match]:
    return FIXTURE_BY_ID.get(match_id)
