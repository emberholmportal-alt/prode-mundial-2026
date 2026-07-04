"""reset puntual de password de Valeria Analia Cufre a 'Prode2026'

Revision ID: b2d61f8e4a30
Revises: e1f4c7d9a2b6
Create Date: 2026-07-06 12:00:00.000000

Mismo flujo que los resets anteriores: setea el password de Valeria
Analia Cufre a 'Prode2026' y marca must_change_password=TRUE para
forzar el cambio en su próximo login.

NO destructiva. No toca otros usuarios ni pronósticos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "b2d61f8e4a30"
down_revision: Union[str, None] = "e1f4c7d9a2b6"
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
                 WHERE LOWER(TRIM(display_name)) LIKE '%valeria%cufr%'
              ORDER BY id
                 LIMIT 1
             )
            """
        ).bindparams(h=new_hash)
    )


def downgrade() -> None:
    pass
