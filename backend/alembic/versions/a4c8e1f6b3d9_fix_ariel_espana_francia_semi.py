"""cargar pronóstico de Ariel Flores en la semifinal España-Francia

Revision ID: a4c8e1f6b3d9
Revises: e8b3d5f2a9c7
Create Date: 2026-07-14 12:00:00.000000

Ariel Flores Valdez cargó hoy 14/7 11:23 ART el pronóstico
España 2 - Francia 1 (semifinal) y no se guardó. Esta migración busca el
slot actual de España-Francia en knockout_matches (cualquier orientación)
y carga/actualiza el pronóstico de Ariel con España 2 / Francia 1, mapeado
a la orientación del slot, con la fecha/hora indicada.

NO destructiva. Idempotente: si el usuario o el cruce no existen, no hace nada.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4c8e1f6b3d9"
down_revision: Union[str, None] = "e8b3d5f2a9c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Fecha/hora indicada: 14/7 11:23 ART (UTC-3) = 14:23 UTC.
_PRED_TS_UTC = "2026-07-14 14:23:00"


def upgrade() -> None:
    conn = op.get_bind()

    uid = conn.execute(
        sa.text(
            "SELECT id FROM users "
            "WHERE LOWER(TRIM(display_name)) LIKE '%ariel%flores%' "
            "ORDER BY id LIMIT 1"
        )
    ).scalar()
    if uid is None:
        return

    row = conn.execute(
        sa.text(
            "SELECT match_id, home_tla, away_tla FROM knockout_matches "
            "WHERE (home_tla = 'ESP' AND away_tla = 'FRA') "
            "   OR (home_tla = 'FRA' AND away_tla = 'ESP') "
            "LIMIT 1"
        )
    ).fetchone()
    if row is None:
        return

    match_id, home_tla, _away_tla = row
    # Ariel puso España 2, Francia 1. Mapeamos según la orientación del slot.
    if home_tla == "ESP":
        hs, as_ = 2, 1   # local=ESP, visitante=FRA
    else:
        hs, as_ = 1, 2   # local=FRA, visitante=ESP

    existing = conn.execute(
        sa.text("SELECT id FROM predictions WHERE user_id = :u AND match_id = :m"),
        {"u": uid, "m": match_id},
    ).scalar()
    if existing is not None:
        conn.execute(
            sa.text(
                "UPDATE predictions SET home_score = :h, away_score = :a, "
                "updated_at = :ts WHERE id = :id"
            ),
            {"h": hs, "a": as_, "ts": _PRED_TS_UTC, "id": existing},
        )
    else:
        conn.execute(
            sa.text(
                "INSERT INTO predictions "
                "(user_id, match_id, home_score, away_score, updated_at) "
                "VALUES (:u, :m, :h, :a, :ts)"
            ),
            {"u": uid, "m": match_id, "h": hs, "a": as_, "ts": _PRED_TS_UTC},
        )


def downgrade() -> None:
    pass
