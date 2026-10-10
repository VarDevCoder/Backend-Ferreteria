"""ip en intentos de login fallidos

El bloqueo de login pasa a ser por email + IP (así nadie deja afuera a otro
usuario probando contraseñas desde su propia conexión).

Revision ID: 1af74c2395d4
Revises: 4becebfe6a70
Create Date: 2026-10-10 13:05:33.209506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1af74c2395d4'
down_revision: Union[str, Sequence[str], None] = '4becebfe6a70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("intentos_login_fallidos", sa.Column("ip", sa.String(length=64), nullable=True))
    op.create_index("ix_intentos_login_fallidos_ip", "intentos_login_fallidos", ["ip"])


def downgrade() -> None:
    op.drop_index("ix_intentos_login_fallidos_ip", table_name="intentos_login_fallidos")
    op.drop_column("intentos_login_fallidos", "ip")
