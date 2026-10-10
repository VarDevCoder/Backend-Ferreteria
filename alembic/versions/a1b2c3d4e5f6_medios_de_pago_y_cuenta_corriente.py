"""medios de pago (pago mixto) y cuenta corriente de clientes

Revision ID: a1b2c3d4e5f6
Revises: 9e3f4a5b6c7d
Create Date: 2026-10-10 12:00:00.000000

- venta_pagos: cada medio con que se cobró una venta. Las ventas existentes
  se migran con un único pago por su total y su medio.
- movimientos_cuenta_corriente: cargos (ventas "a cuenta") y pagos de cada
  cliente; el saldo es la suma de cargos menos pagos.
- clientes.limite_credito: tope de deuda (0 = no compra a cuenta).
- caja_turnos.total_ventas_a_cuenta: lo vendido a cuenta en el turno (no es
  dinero en caja, se informa aparte del arqueo).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9e3f4a5b6c7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'venta_pagos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=False),
        sa.Column('metodo', sa.String(length=20), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('referencia', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas_mostrador.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_venta_pagos_venta_id'), 'venta_pagos', ['venta_id'])
    op.execute("INSERT INTO venta_pagos (venta_id, metodo, monto) SELECT id, metodo_pago, total FROM ventas_mostrador")

    op.create_table(
        'movimientos_cuenta_corriente',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=True),
        sa.Column('metodo_pago', sa.String(length=20), nullable=True),
        sa.Column('caja_turno_id', sa.Integer(), nullable=True),
        sa.Column('referencia', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas_mostrador.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['caja_turno_id'], ['caja_turnos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_movimientos_cuenta_corriente_cliente_id'), 'movimientos_cuenta_corriente', ['cliente_id'])
    op.create_index(op.f('ix_movimientos_cuenta_corriente_created_at'), 'movimientos_cuenta_corriente', ['created_at'])

    op.add_column('clientes', sa.Column('limite_credito', sa.Integer(), server_default='0', nullable=False))
    op.add_column('caja_turnos', sa.Column('total_ventas_a_cuenta', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('caja_turnos', 'total_ventas_a_cuenta')
    op.drop_column('clientes', 'limite_credito')
    op.drop_index(op.f('ix_movimientos_cuenta_corriente_created_at'), table_name='movimientos_cuenta_corriente')
    op.drop_index(op.f('ix_movimientos_cuenta_corriente_cliente_id'), table_name='movimientos_cuenta_corriente')
    op.drop_table('movimientos_cuenta_corriente')
    op.drop_index(op.f('ix_venta_pagos_venta_id'), table_name='venta_pagos')
    op.drop_table('venta_pagos')
