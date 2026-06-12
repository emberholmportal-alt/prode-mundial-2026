"""add users.must_change_password + reset puntual de password de Rubén Campos

Revision ID: c8f47a91d3e2
Revises: f9552a3cbb1b
Create Date: 2026-06-12 16:50:00.000000

Cambios:
- Agrega columna users.must_change_password (Boolean, NOT NULL, default False).
- Reset puntual: setea password de Rubén Campos a 'Prode2026' y marca
  must_change_password=True para forzar cambio en su próximo login.

NO destructiva. No toca pronósticos ni otros usuarios.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "c8f47a91d3e2"
down_revision: Union[str, None] = "f9552a3cbb1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    new_hash = _pwd_context.hash("Prode2026")
    # Reset puntual de Rubén Campos — match flexible (con/sin tilde, espacios extra).
    # Usamos LIMIT 1 para tocar exclusivamente un usuario.
    op.execute(
        sa.text(
            """
            UPDATE users
               SET password_hash = :h,
                   must_change_password = TRUE
             WHERE id = (
                SELECT id FROM users
                 WHERE LOWER(TRIM(display_name)) LIKE '%rubén campos%'
                    OR LOWER(TRIM(display_name)) LIKE '%ruben campos%'
              ORDER BY id
                 LIMIT 1
             )
            """
        ).bindparams(h=new_hash)
    )


def downgrade() -> None:
    # No restauramos el password original (no lo tenemos). Solo dropeamos la columna.
    op.drop_column("users", "must_change_password")
