"""corregir pronóstico de Gabriel Garavano en Sudáfrica-Canadá (16vos)

Revision ID: e8b3d5f2a9c7
Revises: d7e2c4a9f6b1
Create Date: 2026-07-07 12:30:00.000000

Al reasignarse los cruces de eliminación, el partido Sudáfrica-Canadá se
movió de slot y el pronóstico de Gabriel (1-2 = Sudáfrica 1, Canadá 2)
quedó "colgado" en el slot viejo, así que no figuraba en el partido y no
sumaba el punto que le corresponde.

Esta migración busca el slot ACTUAL de Sudáfrica-Canadá (en knockout_matches,
en cualquier orientación) y carga/actualiza el pronóstico de Gabriel con
1-2 en la orientación correcta del slot.

NO destructiva: solo upserta una fila de predictions para un usuario puntual.
Idempotente: si el usuario o el cruce no existen, no hace nada.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8b3d5f2a9c7"
down_revision: Union[str, None] = "d7e2c4a9f6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    uid = conn.execute(
        sa.text(
            "SELECT id FROM users "
            "WHERE LOWER(TRIM(display_name)) LIKE '%gabriel%garavano%' "
            "ORDER BY id LIMIT 1"
        )
    ).scalar()
    if uid is None:
        return

    row = conn.execute(
        sa.text(
            "SELECT match_id, home_tla, away_tla FROM knockout_matches "
            "WHERE (home_tla = 'RSA' AND away_tla = 'CAN') "
            "   OR (home_tla = 'CAN' AND away_tla = 'RSA') "
            "LIMIT 1"
        )
    ).fetchone()
    if row is None:
        return

    match_id, home_tla, _away_tla = row
    # Gabriel puso Sudáfrica 1, Canadá 2. Mapeamos según la orientación del slot.
    if home_tla == "RSA":
        hs, as_ = 1, 2   # local=RSA, visitante=CAN
    else:
        hs, as_ = 2, 1   # local=CAN, visitante=RSA

    existing = conn.execute(
        sa.text("SELECT id FROM predictions WHERE user_id = :u AND match_id = :m"),
        {"u": uid, "m": match_id},
    ).scalar()
    if existing is not None:
        conn.execute(
            sa.text(
                "UPDATE predictions SET home_score = :h, away_score = :a, "
                "updated_at = now() WHERE id = :id"
            ),
            {"h": hs, "a": as_, "id": existing},
        )
    else:
        conn.execute(
            sa.text(
                "INSERT INTO predictions "
                "(user_id, match_id, home_score, away_score, updated_at) "
                "VALUES (:u, :m, :h, :a, now())"
            ),
            {"u": uid, "m": match_id, "h": hs, "a": as_},
        )


def downgrade() -> None:
    pass
