"""empresa configurable y roles del personal

Revision ID: 7c1d2e3f4a5b
Revises: 5b4211eced37
Create Date: 2026-10-01 12:00:00.000000

Agrega la tabla `empresa` (datos de la ferretería que usa el sistema) y
reemplaza el rol genérico `ankor_user` por los roles del personal:
los usuarios que lo tenían pasan a `encargado`, que conserva el mismo
alcance operativo que tenían.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1d2e3f4a5b'
down_revision: Union[str, Sequence[str], None] = '5b4211eced37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'empresa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre_comercial', sa.String(length=255), nullable=False),
        sa.Column('razon_social', sa.String(length=255), nullable=True),
        sa.Column('ruc', sa.String(length=50), nullable=True),
        sa.Column('direccion', sa.Text(), nullable=True),
        sa.Column('ciudad', sa.String(length=100), nullable=True),
        sa.Column('telefono', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('moneda_codigo', sa.String(length=3), nullable=False),
        sa.Column('moneda_simbolo', sa.String(length=10), nullable=False),
        sa.Column('locale', sa.String(length=20), nullable=False),
        sa.Column('iva_porcentaje', sa.Integer(), nullable=False),
        sa.Column('margen_ganancia_defecto', sa.Integer(), nullable=False),
        sa.Column('pie_ticket', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute("UPDATE usuarios SET rol = 'encargado' WHERE rol = 'ankor_user'")
    op.alter_column('usuarios', 'rol', server_default='vendedor')


def downgrade() -> None:
    op.alter_column('usuarios', 'rol', server_default='ankor_user')
    op.execute("UPDATE usuarios SET rol = 'ankor_user' WHERE rol IN ('encargado', 'vendedor', 'deposito')")
    op.drop_table('empresa')
