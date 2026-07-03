"""add comments.highlighted (destacado por admin)

Revision ID: d5b83a19e7c4
Revises: c7a2e34b91f5
Create Date: 2026-06-30 12:00:00.000000

Agrega comments.highlighted (Boolean, default false). Un admin puede
marcar/desmarcar un comentario como destacado; los destacados se muestran
con recuadro verde.

NO destructiva.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5b83a19e7c4"
down_revision: Union[str, None] = "c7a2e34b91f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column(
            "highlighted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("comments", "highlighted")
