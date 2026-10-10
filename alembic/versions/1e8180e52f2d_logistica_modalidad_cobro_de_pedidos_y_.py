"""logistica: modalidad, cobro de pedidos y nota de remision

Revision ID: 1e8180e52f2d
Revises: 1af74c2395d4
Create Date: 2026-10-10 15:07:13.740654

Logística de pedidos (entrega a domicilio o retiro en el local) y su cobro:

- pedidos_cliente: modalidad_entrega, forma_pago (ANTICIPADO, CONTRA_ENTREGA,
  CUENTA_CORRIENTE), estado_pago y lo cobrado / cargado a cuenta. Los pedidos
  ya ENTREGADOS o CANCELADOS quedan con forma_pago NULL y estado_pago
  SIN_REGISTRO (son de antes de que SAIL registrara cobros de pedidos); los
  demás pasan a CONTRA_ENTREGA, que es como se trabajaba.
- ordenes_envio: modalidad y datos del traslado (número de nota de remisión,
  RUC del transportista, vehículo, conductor).
- movimientos_cuenta_corriente.pedido_cliente_id: cargo de un pedido a cuenta.
- pedido_pagos: señas, pagos anticipados, rendiciones y cargos a cuenta.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e8180e52f2d'
down_revision: Union[str, Sequence[str], None] = '1af74c2395d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pedidos_cliente', sa.Column('modalidad_entrega', sa.String(length=20), server_default='ENTREGA_DOMICILIO', nullable=False))
    op.add_column('pedidos_cliente', sa.Column('forma_pago', sa.String(length=20), nullable=True))
    op.add_column('pedidos_cliente', sa.Column('estado_pago', sa.String(length=20), server_default='PENDIENTE', nullable=False))
    op.add_column('pedidos_cliente', sa.Column('monto_pagado', sa.Integer(), server_default='0', nullable=False))
    op.add_column('pedidos_cliente', sa.Column('monto_a_cuenta', sa.Integer(), server_default='0', nullable=False))
    op.create_index(op.f('ix_pedidos_cliente_estado_pago'), 'pedidos_cliente', ['estado_pago'])
    op.execute("UPDATE pedidos_cliente SET forma_pago = 'CONTRA_ENTREGA' WHERE estado NOT IN ('ENTREGADO', 'CANCELADO')")
    op.execute("UPDATE pedidos_cliente SET estado_pago = 'SIN_REGISTRO' WHERE estado IN ('ENTREGADO', 'CANCELADO')")

    op.add_column('ordenes_envio', sa.Column('modalidad', sa.String(length=20), server_default='ENTREGA_DOMICILIO', nullable=False))
    op.add_column('ordenes_envio', sa.Column('numero_nota_remision', sa.String(length=50), nullable=True))
    op.add_column('ordenes_envio', sa.Column('transportista_ruc', sa.String(length=50), nullable=True))
    op.add_column('ordenes_envio', sa.Column('vehiculo', sa.String(length=100), nullable=True))
    op.add_column('ordenes_envio', sa.Column('conductor_nombre', sa.String(length=255), nullable=True))
    op.add_column('ordenes_envio', sa.Column('conductor_documento', sa.String(length=50), nullable=True))

    op.add_column('movimientos_cuenta_corriente', sa.Column('pedido_cliente_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_movimientos_cuenta_corriente_pedido_cliente_id'), 'movimientos_cuenta_corriente', ['pedido_cliente_id'])
    op.create_foreign_key(
        'movimientos_cuenta_corriente_pedido_cliente_id_fkey', 'movimientos_cuenta_corriente', 'pedidos_cliente',
        ['pedido_cliente_id'], ['id'], ondelete='SET NULL',
    )

    op.create_table(
        'pedido_pagos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pedido_cliente_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('metodo', sa.String(length=20), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('referencia', sa.String(length=100), nullable=True),
        sa.Column('caja_turno_id', sa.Integer(), nullable=True),
        sa.Column('orden_envio_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('anulado', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('anulado_at', sa.DateTime(), nullable=True),
        sa.Column('anulado_por', sa.Integer(), nullable=True),
        sa.Column('motivo_anulacion', sa.Text(), nullable=True),
        sa.CheckConstraint('monto > 0', name='ck_pedido_pagos_monto'),
        sa.ForeignKeyConstraint(['pedido_cliente_id'], ['pedidos_cliente.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['caja_turno_id'], ['caja_turnos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['orden_envio_id'], ['ordenes_envio.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['anulado_por'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pedido_pagos_pedido_cliente_id'), 'pedido_pagos', ['pedido_cliente_id'])
    op.create_index(op.f('ix_pedido_pagos_created_at'), 'pedido_pagos', ['created_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_pedido_pagos_created_at'), table_name='pedido_pagos')
    op.drop_index(op.f('ix_pedido_pagos_pedido_cliente_id'), table_name='pedido_pagos')
    op.drop_table('pedido_pagos')
    op.drop_constraint('movimientos_cuenta_corriente_pedido_cliente_id_fkey', 'movimientos_cuenta_corriente', type_='foreignkey')
    op.drop_index(op.f('ix_movimientos_cuenta_corriente_pedido_cliente_id'), table_name='movimientos_cuenta_corriente')
    op.drop_column('movimientos_cuenta_corriente', 'pedido_cliente_id')
    for columna in ('conductor_documento', 'conductor_nombre', 'vehiculo', 'transportista_ruc', 'numero_nota_remision', 'modalidad'):
        op.drop_column('ordenes_envio', columna)
    op.drop_index(op.f('ix_pedidos_cliente_estado_pago'), table_name='pedidos_cliente')
    for columna in ('monto_a_cuenta', 'monto_pagado', 'estado_pago', 'forma_pago', 'modalidad_entrega'):
        op.drop_column('pedidos_cliente', columna)
