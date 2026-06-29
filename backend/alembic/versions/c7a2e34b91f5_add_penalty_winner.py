"""add penalty_winner column to predictions and official_results

Revision ID: c7a2e34b91f5
Revises: b6e95d12fa84
Create Date: 2026-06-28 12:00:00.000000

Agrega `penalty_winner` (TLA del equipo que pasó por penales) a
predictions y official_results. Es opcional: solo aplica para partidos
de eliminatorias terminados en empate después de 90 + alargue.

NO destructiva: nullable, sin default.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7a2e34b91f5"
down_revision: Union[str, None] = "b6e95d12fa84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("penalty_winner", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "official_results",
        sa.Column("penalty_winner", sa.String(length=3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("official_results", "penalty_winner")
    op.drop_column("predictions", "penalty_winner")
