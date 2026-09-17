"""Modelos ORM (SQLAlchemy) — el mapeo a tablas de Postgres.

Deliberadamente "tontos": sin lógica de negocio. Las reglas viven en
`app.domain.entities`; estos modelos solo saben guardar y leer filas.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="ankor_user")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    proveedor: Mapped["ProveedorModel | None"] = relationship(back_populates="user", uselist=False)


class CategoriaModel(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class ProductoModel(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    precio_compra: Mapped[int] = mapped_column(Integer, default=0)
    precio_venta: Mapped[int] = mapped_column(Integer, default=0)
    stock_actual: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    stock_minimo: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="pz")
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    ruc: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProveedorModel(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    ruc: Mapped[str] = mapped_column(String(50), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rubros: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[UsuarioModel] = relationship(back_populates="proveedor")


class ProveedorProductoModel(Base):
    __tablename__ = "proveedor_productos"
    __table_args__ = (UniqueConstraint("proveedor_id", "producto_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="CASCADE"))
    codigo_proveedor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nombre_proveedor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precio: Mapped[int] = mapped_column(Integer, default=0)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)
    tiempo_entrega_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class PedidoClienteModel(Base):
    __tablename__ = "pedidos_cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=True)
    cliente_nombre: Mapped[str] = mapped_column(String(255))
    cliente_ruc: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cliente_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cliente_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cliente_direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_pedido: Mapped[date] = mapped_column(Date)
    fecha_entrega_solicitada: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_entrega_estimada: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="RECIBIDO", index=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    descuento: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["PedidoClienteItemModel"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )


class PedidoClienteItemModel(Base):
    __tablename__ = "pedido_cliente_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_cliente_id: Mapped[int] = mapped_column(ForeignKey("pedidos_cliente.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)

    pedido: Mapped[PedidoClienteModel] = relationship(back_populates="items")


class SolicitudPresupuestoModel(Base):
    __tablename__ = "solicitudes_presupuesto"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    pedido_cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("pedidos_cliente.id", ondelete="SET NULL"), nullable=True
    )
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id", ondelete="CASCADE"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fecha_solicitud: Mapped[date] = mapped_column(Date)
    fecha_limite_respuesta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_respuesta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="ENVIADA", index=True)
    mensaje_solicitud: Mapped[str | None] = mapped_column(Text, nullable=True)
    respuesta_proveedor: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cotizado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dias_entrega_estimados: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["SolicitudPresupuestoItemModel"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan"
    )


class SolicitudPresupuestoItemModel(Base):
    __tablename__ = "solicitud_presupuesto_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("solicitudes_presupuesto.id", ondelete="CASCADE")
    )
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad_solicitada: Mapped[float] = mapped_column(Numeric(12, 3))
    tiene_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cantidad_disponible: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    precio_unitario_cotizado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subtotal_cotizado: Mapped[int | None] = mapped_column(Integer, nullable=True)

    solicitud: Mapped[SolicitudPresupuestoModel] = relationship(back_populates="items")


class OrdenCompraModel(Base):
    __tablename__ = "ordenes_compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    pedido_cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("pedidos_cliente.id", ondelete="SET NULL"), nullable=True
    )
    proveedor_nombre: Mapped[str] = mapped_column(String(255))
    proveedor_ruc: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proveedor_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proveedor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proveedor_direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_orden: Mapped[date] = mapped_column(Date)
    fecha_entrega_esperada: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_recepcion: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", index=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    descuento: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["OrdenCompraItemModel"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


class OrdenCompraItemModel(Base):
    __tablename__ = "orden_compra_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("ordenes_compra.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad_solicitada: Mapped[float] = mapped_column(Numeric(12, 3))
    cantidad_recibida: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    precio_unitario: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)

    orden: Mapped[OrdenCompraModel] = relationship(back_populates="items")


class OrdenEnvioModel(Base):
    __tablename__ = "ordenes_envio"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    pedido_cliente_id: Mapped[int] = mapped_column(ForeignKey("pedidos_cliente.id", ondelete="CASCADE"))
    direccion_entrega: Mapped[str] = mapped_column(String(500))
    contacto_entrega: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono_entrega: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_generacion: Mapped[date] = mapped_column(Date)
    fecha_envio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="PREPARANDO", index=True)
    metodo_envio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_guia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transportista: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["OrdenEnvioItemModel"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


class OrdenEnvioItemModel(Base):
    __tablename__ = "orden_envio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_envio_id: Mapped[int] = mapped_column(ForeignKey("ordenes_envio.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3))

    orden: Mapped[OrdenEnvioModel] = relationship(back_populates="items")


class MovimientoInventarioModel(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="RESTRICT"), index=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)
    cantidad: Mapped[float] = mapped_column(Numeric(14, 3))
    stock_anterior: Mapped[float] = mapped_column(Numeric(14, 3))
    stock_nuevo: Mapped[float] = mapped_column(Numeric(14, 3))
    referencia_tipo: Mapped[str] = mapped_column(String(30))
    referencia_id: Mapped[int] = mapped_column(Integer)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
