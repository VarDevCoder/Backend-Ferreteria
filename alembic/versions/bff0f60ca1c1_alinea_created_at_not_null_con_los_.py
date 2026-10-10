"""alinea created_at NOT NULL con los modelos

Los modelos declaran `created_at` obligatorio (siempre lo completa
`server_default=now()`), pero el esquema inicial lo dejó admitiendo NULL en
seis tablas. `alembic check` lo marcaba como diferencia. Por las dudas se
completa con la fecha actual cualquier fila vieja sin fecha antes de exigirla.

Revision ID: bff0f60ca1c1
Revises: a1b2c3d4e5f6
Create Date: 2026-10-10 12:54:34.567646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bff0f60ca1c1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLAS = (
    "movimientos_inventario",
    "ordenes_compra",
    "ordenes_envio",
    "pedidos_cliente",
    "solicitudes_presupuesto",
    "usuarios",
)


def upgrade() -> None:
    for tabla in TABLAS:
        op.execute(sa.text(f"UPDATE {tabla} SET created_at = now() WHERE created_at IS NULL"))
        op.alter_column(tabla, "created_at", existing_type=sa.DateTime(), nullable=False, existing_server_default=sa.text("now()"))


def downgrade() -> None:
    for tabla in TABLAS:
        op.alter_column(tabla, "created_at", existing_type=sa.DateTime(), nullable=True, existing_server_default=sa.text("now()"))
