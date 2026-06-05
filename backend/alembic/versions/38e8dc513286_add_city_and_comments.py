"""add city to users and create comments table

Revision ID: 38e8dc513286
Revises: afbe2a6be66c
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '38e8dc513286'
down_revision: Union[str, None] = 'afbe2a6be66c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Borrar usuarios existentes para poder agregar city NOT NULL sin backfill.
    # En prod solo había ariel_admin de prueba; se recrea vía /api/auth/register.
    op.execute("DELETE FROM final_picks")
    op.execute("DELETE FROM predictions")
    op.execute("DELETE FROM users")

    op.add_column(
        'users',
        sa.Column('city', sa.String(length=30), nullable=False),
    )
    op.create_check_constraint(
        'ck_users_city',
        'users',
        "city IN ('isidro_casanova', 'esteban_echeverria')",
    )
    op.create_index('ix_users_city', 'users', ['city'], unique=False)

    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.String(length=500), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            'char_length(body) BETWEEN 1 AND 500',
            name='ck_comments_body_len',
        ),
    )
    op.create_index('ix_comments_created_at', 'comments', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_comments_created_at', table_name='comments')
    op.drop_table('comments')
    op.drop_index('ix_users_city', table_name='users')
    op.drop_constraint('ck_users_city', 'users', type_='check')
    op.drop_column('users', 'city')
