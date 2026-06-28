"""add knockout_matches table

Revision ID: b6e95d12fa84
Revises: a91ce47d2058
Create Date: 2026-06-27 22:00:00.000000

Crea la tabla knockout_matches que guarda las asignaciones de equipos
para los slots K1..K30 del FIXTURE. Se popula automáticamente desde
football-data.org cuando FIFA define los cruces (16vos, octavos, etc).

NO destructiva. No toca FIXTURE ni pronósticos. Las filas se insertan
solo cuando hay datos remotos que las soportan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b6e95d12fa84"
down_revision: Union[str, None] = "a91ce47d2058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knockout_matches",
        sa.Column("match_id", sa.String(length=10), primary_key=True),
        sa.Column("home_tla", sa.String(length=3), nullable=False),
        sa.Column("away_tla", sa.String(length=3), nullable=False),
        sa.Column("datetime_utc", sa.String(length=40), nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column(
            "source",
            sa.String(length=10),
            nullable=False,
            server_default="auto",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("knockout_matches")
