"""extend user with dni/email/sector/company + index by company

Revision ID: afbe2a6be66c
Revises: b9779cb804ea
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'afbe2a6be66c'
down_revision: Union[str, None] = 'b9779cb804ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # El único usuario que pudo haberse creado bajo el schema viejo era el admin
    # de prueba (ariel_admin). Lo borramos para poder agregar las columnas como
    # NOT NULL sin backfill — se recrea vía /api/auth/register cuando deployemos.
    op.execute("DELETE FROM final_picks")
    op.execute("DELETE FROM predictions")
    op.execute("DELETE FROM users")

    op.add_column(
        'users',
        sa.Column('dni', sa.String(length=10), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('email', sa.String(length=200), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('sector', sa.String(length=100), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('company', sa.String(length=20), nullable=False),
    )

    op.create_unique_constraint('uq_users_dni', 'users', ['dni'])
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_check_constraint(
        'ck_users_company',
        'users',
        "company IN ('grupo_gestion', 'carrefour')",
    )
    op.create_index('ix_users_company', 'users', ['company'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_users_company', table_name='users')
    op.drop_constraint('ck_users_company', 'users', type_='check')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_constraint('uq_users_dni', 'users', type_='unique')
    op.drop_column('users', 'company')
    op.drop_column('users', 'sector')
    op.drop_column('users', 'email')
    op.drop_column('users', 'dni')
