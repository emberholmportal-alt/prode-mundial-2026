"""reset puntual de password de Gabriel Garavano a 'Prode2026' (segunda vez)

Revision ID: a91ce47d2058
Revises: f3d806b9e142
Create Date: 2026-06-16 18:30:00.000000

Re-aplica el reset del password de Gabriel Garavano a 'Prode2026' y
vuelve a marcar must_change_password=TRUE.

NO destructiva. No toca otros usuarios ni pronósticos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = "a91ce47d2058"
down_revision: Union[str, None] = "f3d806b9e142"
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
    pass
