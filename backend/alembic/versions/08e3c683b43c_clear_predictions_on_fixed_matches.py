"""delete predictions on fixed group matches (E/K/L matchday 3)

Revision ID: 08e3c683b43c
Revises: f24bd252cd98
Create Date: 2026-06-08 00:00:00.000000

Limpieza puntual: los partidos G57, G58, G67, G68, G69, G70 estaban mal
cargados (jornada 3 de los grupos E, K y L con cruces duplicados). Esta
migración borra cualquier predicción que algún usuario haya cargado contra
esos match_ids, para que vuelvan a cargar el pronóstico contra el cruce
correcto.

ALCANCE LIMITADO:
- Solo DELETE de predictions WHERE match_id IN ('G57','G58','G67','G68','G69','G70')
- NO toca users, comments, final_picks, official_results, ni predicciones
  de los otros 98 partidos.
- Idempotente (si no hay nada que borrar, no falla).
"""
from typing import Sequence, Union

from alembic import op


revision: str = '08e3c683b43c'
down_revision: Union[str, None] = 'f24bd252cd98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AFFECTED_MATCH_IDS = ('G57', 'G58', 'G67', 'G68', 'G69', 'G70')


def upgrade() -> None:
    ids_csv = ", ".join(f"'{m}'" for m in _AFFECTED_MATCH_IDS)
    op.execute(f"DELETE FROM predictions WHERE match_id IN ({ids_csv})")


def downgrade() -> None:
    # No-op: las predicciones borradas no se pueden recuperar porque
    # corresponden a cruces incorrectos del fixture.
    pass
