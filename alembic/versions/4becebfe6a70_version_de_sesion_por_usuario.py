"""version de sesion por usuario

Cada token lleva la versión de sesión del usuario; cambiar o restablecer la
contraseña la incrementa y así invalida las sesiones abiertas antes.

Revision ID: 4becebfe6a70
Revises: bff0f60ca1c1
Create Date: 2026-10-10 13:02:52.926455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4becebfe6a70'
down_revision: Union[str, Sequence[str], None] = 'bff0f60ca1c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("version_sesion", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("usuarios", "version_sesion")
