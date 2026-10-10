"""stock no vendible y reclamos al proveedor

Revision ID: efcd5ab831ef
Revises: a1b2c3d4e5f6
Create Date: 2026-10-10 12:51:15.431408

- productos.stock_no_vendible: unidades que existen pero no se pueden vender
  (stock_actual sigue siendo el stock vendible, el único que usan la caja,
  los pedidos y los envíos).
- movimientos_inventario.no_vendible_anterior / no_vendible_nuevo: el kardex
  registra también cómo cambia el stock no vendible.
- stock_no_vendible: unidades marcadas como no vendibles (motivo, quién,
  cuándo, proveedor y lo que falta resolver).
- stock_no_vendible_resoluciones: cada resolución (reparado, descartado,
  repuesto o con nota de crédito del proveedor).
- reclamos_proveedor y reclamo_proveedor_items: reclamos con número
  correlativo (RCL-AAAA-NNNN), estados y resolución por ítem.

Solo agrega tablas y columnas (con valor por defecto): no toca datos existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efcd5ab831ef'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('productos', sa.Column('stock_no_vendible', sa.Numeric(14, 3), server_default='0', nullable=False))
    op.add_column('movimientos_inventario', sa.Column('no_vendible_anterior', sa.Numeric(14, 3), nullable=True))
    op.add_column('movimientos_inventario', sa.Column('no_vendible_nuevo', sa.Numeric(14, 3), nullable=True))

    op.create_table(
        'stock_no_vendible',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Numeric(14, 3), nullable=False),
        sa.Column('cantidad_pendiente', sa.Numeric(14, 3), nullable=False),
        sa.Column('motivo', sa.String(length=20), nullable=False),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('proveedor_id', sa.Integer(), nullable=True),
        sa.Column('orden_compra_id', sa.Integer(), nullable=True),
        sa.Column('costo_unitario', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('cantidad > 0', name='ck_stock_no_vendible_cantidad'),
        sa.CheckConstraint('cantidad_pendiente >= 0 AND cantidad_pendiente <= cantidad', name='ck_stock_no_vendible_pendiente'),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['orden_compra_id'], ['ordenes_compra.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_stock_no_vendible_producto_id'), 'stock_no_vendible', ['producto_id'])
    op.create_index(op.f('ix_stock_no_vendible_proveedor_id'), 'stock_no_vendible', ['proveedor_id'])
    op.create_index(op.f('ix_stock_no_vendible_estado'), 'stock_no_vendible', ['estado'])
    op.create_index(op.f('ix_stock_no_vendible_created_at'), 'stock_no_vendible', ['created_at'])

    op.create_table(
        'reclamos_proveedor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(length=50), nullable=False),
        sa.Column('proveedor_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('proveedor_razon_social', sa.String(length=255), nullable=False),
        sa.Column('proveedor_ruc', sa.String(length=50), nullable=True),
        sa.Column('proveedor_telefono', sa.String(length=50), nullable=True),
        sa.Column('proveedor_email', sa.String(length=255), nullable=True),
        sa.Column('proveedor_direccion', sa.Text(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('respuesta_proveedor', sa.Text(), nullable=True),
        sa.Column('motivo_rechazo', sa.Text(), nullable=True),
        sa.Column('numero_nota_credito', sa.String(length=50), nullable=True),
        sa.Column('numero_nota_remision', sa.String(length=50), nullable=True),
        sa.Column('fecha_envio', sa.DateTime(), nullable=True),
        sa.Column('fecha_respuesta', sa.DateTime(), nullable=True),
        sa.Column('fecha_resolucion', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero'),
    )
    op.create_index(op.f('ix_reclamos_proveedor_proveedor_id'), 'reclamos_proveedor', ['proveedor_id'])
    op.create_index(op.f('ix_reclamos_proveedor_estado'), 'reclamos_proveedor', ['estado'])
    op.create_index(op.f('ix_reclamos_proveedor_created_at'), 'reclamos_proveedor', ['created_at'])

    op.create_table(
        'reclamo_proveedor_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reclamo_id', sa.Integer(), nullable=False),
        sa.Column('registro_id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Numeric(14, 3), nullable=False),
        sa.Column('costo_unitario', sa.Integer(), nullable=False),
        sa.Column('resolucion', sa.String(length=20), nullable=True),
        sa.Column('monto_nota_credito', sa.Integer(), nullable=False),
        sa.Column('nota_resolucion', sa.Text(), nullable=True),
        sa.Column('resuelto_por', sa.Integer(), nullable=True),
        sa.Column('resuelto_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('cantidad > 0', name='ck_reclamo_item_cantidad'),
        sa.ForeignKeyConstraint(['reclamo_id'], ['reclamos_proveedor.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registro_id'], ['stock_no_vendible.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['resuelto_por'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reclamo_id', 'registro_id'),
    )
    op.create_index(op.f('ix_reclamo_proveedor_items_reclamo_id'), 'reclamo_proveedor_items', ['reclamo_id'])
    op.create_index(op.f('ix_reclamo_proveedor_items_registro_id'), 'reclamo_proveedor_items', ['registro_id'])

    op.create_table(
        'stock_no_vendible_resoluciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registro_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('cantidad', sa.Numeric(14, 3), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('reclamo_id', sa.Integer(), nullable=True),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('cantidad > 0', name='ck_resolucion_no_vendible_cantidad'),
        sa.ForeignKeyConstraint(['registro_id'], ['stock_no_vendible.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reclamo_id'], ['reclamos_proveedor.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_stock_no_vendible_resoluciones_registro_id'), 'stock_no_vendible_resoluciones', ['registro_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_stock_no_vendible_resoluciones_registro_id'), table_name='stock_no_vendible_resoluciones')
    op.drop_table('stock_no_vendible_resoluciones')
    op.drop_index(op.f('ix_reclamo_proveedor_items_registro_id'), table_name='reclamo_proveedor_items')
    op.drop_index(op.f('ix_reclamo_proveedor_items_reclamo_id'), table_name='reclamo_proveedor_items')
    op.drop_table('reclamo_proveedor_items')
    op.drop_index(op.f('ix_reclamos_proveedor_created_at'), table_name='reclamos_proveedor')
    op.drop_index(op.f('ix_reclamos_proveedor_estado'), table_name='reclamos_proveedor')
    op.drop_index(op.f('ix_reclamos_proveedor_proveedor_id'), table_name='reclamos_proveedor')
    op.drop_table('reclamos_proveedor')
    op.drop_index(op.f('ix_stock_no_vendible_created_at'), table_name='stock_no_vendible')
    op.drop_index(op.f('ix_stock_no_vendible_estado'), table_name='stock_no_vendible')
    op.drop_index(op.f('ix_stock_no_vendible_proveedor_id'), table_name='stock_no_vendible')
    op.drop_index(op.f('ix_stock_no_vendible_producto_id'), table_name='stock_no_vendible')
    op.drop_table('stock_no_vendible')
    op.drop_column('movimientos_inventario', 'no_vendible_nuevo')
    op.drop_column('movimientos_inventario', 'no_vendible_anterior')
    op.drop_column('productos', 'stock_no_vendible')
