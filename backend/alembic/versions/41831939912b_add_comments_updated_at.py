"""add nullable updated_at column to comments (track edits)

Revision ID: 41831939912b
Revises: 08e3c683b43c
Create Date: 2026-06-08 00:00:00.000000

Migración NO destructiva: solo agrega la columna `comments.updated_at` como
DateTime nullable. NO borra comentarios ni datos existentes. Comentarios
previos quedan con `updated_at = NULL` (= nunca editados). Cualquier edit
posterior lo setea con `datetime.utcnow()`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '41831939912b'
down_revision: Union[str, None] = '08e3c683b43c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comments',
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('comments', 'updated_at')
