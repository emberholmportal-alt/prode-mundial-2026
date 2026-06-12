"""add auto_loaded column to official_results

Revision ID: eab040268ec8
Revises: 41831939912b
Create Date: 2026-06-08 00:00:00.000000

Migración NO destructiva: agrega `official_results.auto_loaded` boolean
con default false. Sirve para distinguir resultados cargados a mano por
el admin (False) de los importados automáticamente desde football-data.org
(True). Los resultados existentes se asumen como cargados a mano (False).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'eab040268ec8'
down_revision: Union[str, None] = '41831939912b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'official_results',
        sa.Column(
            'auto_loaded',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('official_results', 'auto_loaded')
