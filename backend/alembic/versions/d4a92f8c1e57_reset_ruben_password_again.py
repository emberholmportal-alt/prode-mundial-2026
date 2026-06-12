"""reset puntual de password de Rubén Campos a 'Prode2026' (segunda vez)

Revision ID: d4a92f8c1e57
Revises: c8f47a91d3e2
Create Date: 2026-06-12 17:00:00.000000

Re-aplica el reset del password de Rubén Campos a 'Prode2026' y vuelve a
marcar must_change_password=TRUE. Idempotente: si Rubén ya no existe,
no hace nada.

NO destructiva. No toca otros usuarios ni pronósticos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "d4a92f8c1e57"
down_revision: Union[str, None] = "c8f47a91d3e2"
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
                 WHERE LOWER(TRIM(display_name)) LIKE '%rubén campos%'
                    OR LOWER(TRIM(display_name)) LIKE '%ruben campos%'
              ORDER BY id
                 LIMIT 1
             )
            """
        ).bindparams(h=new_hash)
    )


def downgrade() -> None:
    # No revertimos — no tenemos el password original.
    pass
