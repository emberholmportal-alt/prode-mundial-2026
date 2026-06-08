"""add nullable avatar_config column to users

Revision ID: f24bd252cd98
Revises: 38e8dc513286
Create Date: 2026-06-08 00:00:00.000000

Migración NO destructiva: solo agrega la columna `users.avatar_config` como
Text nullable. NO borra usuarios ni datos existentes. Los usuarios sin
avatar configurado quedan con `NULL` y el frontend muestra el avatar
default de iniciales.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f24bd252cd98'
down_revision: Union[str, None] = '38e8dc513286'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('avatar_config', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'avatar_config')
