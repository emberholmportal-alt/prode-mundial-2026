"""seed cruces de octavos (Round of 16) 2026 en knockout_matches

Revision ID: e1f4c7d9a2b6
Revises: d5b83a19e7c4
Create Date: 2026-07-04 12:00:00.000000

Carga los 8 cruces reales de octavos del Mundial 2026 en los slots
K17..K24 como source='manual' (fijos, el auto-sync no los pisa). Se
hace por migración porque football-data.org tardó en publicar estos
cruces con equipos concretos.

Fuente: Wikipedia / FIFA — 2026 FIFA World Cup knockout stage.

NO destructiva de datos de usuarios: solo reemplaza las filas K17..K24
de knockout_matches (asignaciones de esos slots), que es justo lo que
queremos corregir. No toca predicciones ni resultados.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f4c7d9a2b6"
down_revision: Union[str, None] = "d5b83a19e7c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (slot, home_tla, away_tla, datetime_utc, venue)
_OCTAVOS = [
    ("K17", "CAN", "MAR", "2026-07-04T20:00:00Z", "NRG Stadium, Houston"),
    ("K18", "PAR", "FRA", "2026-07-05T00:00:00Z", "Lincoln Financial Field, Philadelphia"),
    ("K19", "BRA", "NOR", "2026-07-05T21:00:00Z", "MetLife Stadium, Nueva Jersey"),
    ("K20", "MEX", "ENG", "2026-07-06T01:00:00Z", "Estadio Azteca, Ciudad de México"),
    ("K21", "POR", "ESP", "2026-07-07T01:00:00Z", "AT&T Stadium, Dallas"),
    ("K22", "USA", "BEL", "2026-07-07T03:00:00Z", "Lumen Field, Seattle"),
    ("K23", "ARG", "EGY", "2026-07-08T00:00:00Z", "Mercedes-Benz Stadium, Atlanta"),
    ("K24", "SUI", "COL", "2026-07-08T03:00:00Z", "BC Place, Vancouver"),
]


def upgrade() -> None:
    conn = op.get_bind()
    slot_ids = tuple(r[0] for r in _OCTAVOS)
    # Limpiar cualquier asignación previa (auto o duplicada) de esos slots.
    conn.execute(
        sa.text("DELETE FROM knockout_matches WHERE match_id IN :ids").bindparams(
            sa.bindparam("ids", value=slot_ids, expanding=True)
        )
    )
    # Insertar los cruces correctos como 'manual'.
    for slot, h, a, dt, venue in _OCTAVOS:
        conn.execute(
            sa.text(
                "INSERT INTO knockout_matches "
                "(match_id, home_tla, away_tla, datetime_utc, venue, source, updated_at) "
                "VALUES (:mid, :h, :a, :dt, :venue, 'manual', now())"
            ).bindparams(mid=slot, h=h, a=a, dt=dt, venue=venue)
        )


def downgrade() -> None:
    conn = op.get_bind()
    slot_ids = tuple(r[0] for r in _OCTAVOS)
    conn.execute(
        sa.text("DELETE FROM knockout_matches WHERE match_id IN :ids").bindparams(
            sa.bindparam("ids", value=slot_ids, expanding=True)
        )
    )
