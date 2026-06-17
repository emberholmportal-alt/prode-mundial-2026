"""reset puntual de password de Cristian Pellegrino a 'Prode2026'

Revision ID: e7b251a4c83f
Revises: d4a92f8c1e57
Create Date: 2026-06-16 17:55:00.000000

Mismo flujo que el reset de Rubén Campos: setea password de
Cristian Pellegrino a 'Prode2026' y marca must_change_password=TRUE
para forzar cambio en su próximo login.

NO destructiva. No toca otros usuarios ni pronósticos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "e7b251a4c83f"
down_revision: Union[str, None] = "d4a92f8c1e57"
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
                 WHERE LOWER(TRIM(display_name)) LIKE '%cristian pellegrino%'
                    OR LOWER(TRIM(display_name)) LIKE '%cristián pellegrino%'
              ORDER BY id
                 LIMIT 1
             )
            """
        ).bindparams(h=new_hash)
    )


def downgrade() -> None:
    # No revertimos — no tenemos el password original.
    pass
