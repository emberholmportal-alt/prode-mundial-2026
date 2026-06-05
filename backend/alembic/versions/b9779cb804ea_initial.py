"""initial

Revision ID: b9779cb804ea
Revises:
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9779cb804ea'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.String(length=10), nullable=False),
        sa.Column('home_score', sa.SmallInteger(), nullable=False),
        sa.Column('away_score', sa.SmallInteger(), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'match_id', name='uq_predictions_user_match'),
        sa.CheckConstraint(
            'home_score >= 0 AND home_score <= 20',
            name='ck_predictions_home_range',
        ),
        sa.CheckConstraint(
            'away_score >= 0 AND away_score <= 20',
            name='ck_predictions_away_range',
        ),
    )
    op.create_index('ix_predictions_match_id', 'predictions', ['match_id'], unique=False)

    op.create_table(
        'official_results',
        sa.Column('match_id', sa.String(length=10), nullable=False),
        sa.Column('home_score', sa.SmallInteger(), nullable=False),
        sa.Column('away_score', sa.SmallInteger(), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('match_id'),
    )

    op.create_table(
        'final_picks',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('champion', sa.String(length=3), nullable=False),
        sa.Column('runner_up', sa.String(length=3), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'official_final',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('champion', sa.String(length=3), nullable=True),
        sa.Column('runner_up', sa.String(length=3), nullable=True),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id = 1', name='ck_official_final_singleton'),
    )


def downgrade() -> None:
    op.drop_table('official_final')
    op.drop_table('final_picks')
    op.drop_table('official_results')
    op.drop_index('ix_predictions_match_id', table_name='predictions')
    op.drop_table('predictions')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
