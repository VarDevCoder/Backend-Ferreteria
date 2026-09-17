"""esquema inicial ankor

Escrita a mano (no autogenerada) para que no dependa de tener una conexión
Postgres disponible en el momento de generarla — refleja 1:1 los modelos en
`app/infrastructure/db/models.py`.

Revision ID: 4e3f668fd87f
Revises:
Create Date: 2026-09-17 20:13:36.209104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4e3f668fd87f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False, server_default="ankor_user"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(255), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "productos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("categoria_id", sa.Integer, sa.ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("precio_compra", sa.Integer, nullable=False, server_default="0"),
        sa.Column("precio_venta", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stock_actual", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("stock_minimo", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("unidad_medida", sa.String(20), nullable=False, server_default="pz"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_productos_codigo", "productos", ["codigo"])
    op.create_index("ix_productos_nombre", "productos", ["nombre"])
    op.create_index("ix_productos_activo", "productos", ["activo"])

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("ruc", sa.String(50), nullable=True, unique=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("direccion", sa.Text, nullable=True),
        sa.Column("ciudad", sa.String(100), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("notas", sa.Text, nullable=True),
    )

    op.create_table(
        "proveedores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(255), nullable=False),
        sa.Column("ruc", sa.String(50), nullable=False, unique=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("direccion", sa.Text, nullable=True),
        sa.Column("ciudad", sa.String(100), nullable=True),
        sa.Column("rubros", sa.Text, nullable=True),
        sa.Column("notas", sa.Text, nullable=True),
    )

    op.create_table(
        "proveedor_productos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("proveedor_id", sa.Integer, sa.ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo_proveedor", sa.String(100), nullable=True),
        sa.Column("nombre_proveedor", sa.String(255), nullable=True),
        sa.Column("precio", sa.Integer, nullable=False, server_default="0"),
        sa.Column("disponible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("tiempo_entrega_dias", sa.Integer, nullable=True),
        sa.Column("notas", sa.Text, nullable=True),
        sa.UniqueConstraint("proveedor_id", "producto_id"),
    )

    op.create_table(
        "pedidos_cliente",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("numero", sa.String(50), nullable=False, unique=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("cliente_nombre", sa.String(255), nullable=False),
        sa.Column("cliente_ruc", sa.String(50), nullable=True),
        sa.Column("cliente_telefono", sa.String(50), nullable=True),
        sa.Column("cliente_email", sa.String(255), nullable=True),
        sa.Column("cliente_direccion", sa.Text, nullable=True),
        sa.Column("fecha_pedido", sa.Date, nullable=False),
        sa.Column("fecha_entrega_solicitada", sa.Date, nullable=True),
        sa.Column("fecha_entrega_estimada", sa.Date, nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="RECIBIDO"),
        sa.Column("subtotal", sa.Integer, nullable=False, server_default="0"),
        sa.Column("descuento", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("motivo_cancelacion", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_pedidos_cliente_estado", "pedidos_cliente", ["estado"])

    op.create_table(
        "pedido_cliente_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pedido_cliente_id", sa.Integer, sa.ForeignKey("pedidos_cliente.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("cantidad", sa.Numeric(12, 3), nullable=False),
        sa.Column("precio_unitario", sa.Integer, nullable=False),
        sa.Column("subtotal", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "solicitudes_presupuesto",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("numero", sa.String(50), nullable=False, unique=True),
        sa.Column("pedido_cliente_id", sa.Integer, sa.ForeignKey("pedidos_cliente.id", ondelete="SET NULL"), nullable=True),
        sa.Column("proveedor_id", sa.Integer, sa.ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("fecha_solicitud", sa.Date, nullable=False),
        sa.Column("fecha_limite_respuesta", sa.Date, nullable=True),
        sa.Column("fecha_respuesta", sa.Date, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ENVIADA"),
        sa.Column("mensaje_solicitud", sa.Text, nullable=True),
        sa.Column("respuesta_proveedor", sa.Text, nullable=True),
        sa.Column("total_cotizado", sa.Integer, nullable=True),
        sa.Column("dias_entrega_estimados", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_solicitudes_presupuesto_estado", "solicitudes_presupuesto", ["estado"])

    op.create_table(
        "solicitud_presupuesto_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("solicitud_presupuesto_id", sa.Integer, sa.ForeignKey("solicitudes_presupuesto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("cantidad_solicitada", sa.Numeric(12, 3), nullable=False),
        sa.Column("tiene_stock", sa.Boolean, nullable=True),
        sa.Column("cantidad_disponible", sa.Numeric(12, 3), nullable=True),
        sa.Column("precio_unitario_cotizado", sa.Integer, nullable=True),
        sa.Column("subtotal_cotizado", sa.Integer, nullable=True),
    )

    op.create_table(
        "ordenes_compra",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("numero", sa.String(50), nullable=False, unique=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("pedido_cliente_id", sa.Integer, sa.ForeignKey("pedidos_cliente.id", ondelete="SET NULL"), nullable=True),
        sa.Column("proveedor_nombre", sa.String(255), nullable=False),
        sa.Column("proveedor_ruc", sa.String(50), nullable=True),
        sa.Column("proveedor_telefono", sa.String(50), nullable=True),
        sa.Column("proveedor_email", sa.String(255), nullable=True),
        sa.Column("proveedor_direccion", sa.Text, nullable=True),
        sa.Column("fecha_orden", sa.Date, nullable=False),
        sa.Column("fecha_entrega_esperada", sa.Date, nullable=True),
        sa.Column("fecha_recepcion", sa.Date, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
        sa.Column("subtotal", sa.Integer, nullable=False, server_default="0"),
        sa.Column("descuento", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("motivo_cancelacion", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ordenes_compra_estado", "ordenes_compra", ["estado"])

    op.create_table(
        "orden_compra_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("orden_compra_id", sa.Integer, sa.ForeignKey("ordenes_compra.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("cantidad_solicitada", sa.Numeric(12, 3), nullable=False),
        sa.Column("cantidad_recibida", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("precio_unitario", sa.Integer, nullable=False),
        sa.Column("subtotal", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "ordenes_envio",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("numero", sa.String(50), nullable=False, unique=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("pedido_cliente_id", sa.Integer, sa.ForeignKey("pedidos_cliente.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direccion_entrega", sa.String(500), nullable=False),
        sa.Column("contacto_entrega", sa.String(255), nullable=True),
        sa.Column("telefono_entrega", sa.String(50), nullable=True),
        sa.Column("fecha_generacion", sa.Date, nullable=False),
        sa.Column("fecha_envio", sa.Date, nullable=True),
        sa.Column("fecha_entrega", sa.Date, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PREPARANDO"),
        sa.Column("metodo_envio", sa.String(100), nullable=True),
        sa.Column("numero_guia", sa.String(100), nullable=True),
        sa.Column("transportista", sa.String(255), nullable=True),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("observaciones_entrega", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ordenes_envio_estado", "ordenes_envio", ["estado"])

    op.create_table(
        "orden_envio_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("orden_envio_id", sa.Integer, sa.ForeignKey("ordenes_envio.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("cantidad", sa.Numeric(12, 3), nullable=False),
    )

    op.create_table(
        "movimientos_inventario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("producto_id", sa.Integer, sa.ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("stock_anterior", sa.Numeric(14, 3), nullable=False),
        sa.Column("stock_nuevo", sa.Numeric(14, 3), nullable=False),
        sa.Column("referencia_tipo", sa.String(30), nullable=False),
        sa.Column("referencia_id", sa.Integer, nullable=False),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observaciones", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_movimientos_inventario_producto_id", "movimientos_inventario", ["producto_id"])
    op.create_index("ix_movimientos_inventario_tipo", "movimientos_inventario", ["tipo"])
    op.create_index("ix_movimientos_inventario_created_at", "movimientos_inventario", ["created_at"])
    op.create_index(
        "ix_movimientos_inventario_referencia", "movimientos_inventario", ["referencia_tipo", "referencia_id"]
    )


def downgrade() -> None:
    op.drop_table("movimientos_inventario")
    op.drop_table("orden_envio_items")
    op.drop_table("ordenes_envio")
    op.drop_table("orden_compra_items")
    op.drop_table("ordenes_compra")
    op.drop_table("solicitud_presupuesto_items")
    op.drop_table("solicitudes_presupuesto")
    op.drop_table("pedido_cliente_items")
    op.drop_table("pedidos_cliente")
    op.drop_table("proveedor_productos")
    op.drop_table("proveedores")
    op.drop_table("clientes")
    op.drop_table("productos")
    op.drop_table("categorias")
    op.drop_table("usuarios")
