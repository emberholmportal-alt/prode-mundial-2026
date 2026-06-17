"""reset puntual de password de Gabriel Garavano a 'Prode2026'

Revision ID: f3d806b9e142
Revises: e7b251a4c83f
Create Date: 2026-06-16 18:00:00.000000

Mismo flujo que el reset de Rubén Campos y Cristian Pellegrino: setea
password de Gabriel Garavano a 'Prode2026' y marca
must_change_password=TRUE para forzar cambio en su próximo login.

NO destructiva. No toca otros usuarios ni pronósticos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "f3d806b9e142"
down_revision: Union[str, None] = "e7b251a4c83f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    new_hash = _pwd_context.hash("Prode2026")
    op.execute(
        sa.text(
            """
            UPDATE users
               SET password_hash = :h,
                   must_change_password = TRUE
             WHERE id = (
                SELECT id FROM users
                 WHERE LOWER(TRIM(display_name)) LIKE '%gabriel garavano%'
              ORDER BY id
                 LIMIT 1
             )
            """
        ).bindparams(h=new_hash)
    )


def downgrade() -> None:
    # No revertimos — no tenemos el password original.
    pass
