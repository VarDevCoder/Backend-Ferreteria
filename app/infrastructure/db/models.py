"""Modelos ORM (SQLAlchemy) — el mapeo a tablas de Postgres.

Deliberadamente "tontos": sin lógica de negocio. Las reglas viven en
`app.domain.entities`; estos modelos solo saben guardar y leer filas.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
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
    # Como lo crea la migración inicial: restricción UNIQUE más un índice aparte.
    __table_args__ = (Index("ix_usuarios_email", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="vendedor")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Va dentro del token: al cambiar o restablecer la contraseña se incrementa
    # y las sesiones emitidas antes dejan de valer.
    version_sesion: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    proveedor: Mapped["ProveedorModel | None"] = relationship(back_populates="user", uselist=False)


class IntentoLoginFallidoModel(Base):
    """Contraseñas incorrectas recientes por email, para frenar la fuerza
    bruta. Vive en la base (y no en memoria) porque en Vercel cada request
    puede caer en una instancia distinta."""

    __tablename__ = "intentos_login_fallidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    # IP del cliente: el bloqueo es por email + IP, así nadie deja afuera a otro.
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class EmpresaModel(Base):
    """Configuración de la ferretería. Siempre una única fila con id=1."""

    __tablename__ = "empresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_comercial: Mapped[str] = mapped_column(String(255))
    razon_social: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ruc: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moneda_codigo: Mapped[str] = mapped_column(String(3), default="PYG")
    moneda_simbolo: Mapped[str] = mapped_column(String(10), default="Gs.")
    locale: Mapped[str] = mapped_column(String(20), default="es-PY")
    iva_porcentaje: Mapped[int] = mapped_column(Integer, default=10)
    margen_ganancia_defecto: Mapped[int] = mapped_column(Integer, default=25)
    pie_ticket: Mapped[str | None] = mapped_column(Text, nullable=True)


class CategoriaModel(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class ProductoModel(Base):
    __tablename__ = "productos"
    # Como lo crea la migración inicial: restricción UNIQUE más un índice aparte.
    __table_args__ = (Index("ix_productos_codigo", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    precio_compra: Mapped[int] = mapped_column(Integer, default=0)
    precio_venta: Mapped[int] = mapped_column(Integer, default=0)
    stock_actual: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    stock_minimo: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="pz")
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Unidades que existen pero no se pueden vender (ver StockNoVendibleModel).
    stock_no_vendible: Mapped[float] = mapped_column(Numeric(14, 3), default=0, server_default="0")


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
    limite_credito: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


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
    __table_args__ = (Index("ix_movimientos_inventario_referencia", "referencia_tipo", "referencia_id"),)

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
    # Solo en movimientos que tocan el stock no vendible.
    no_vendible_anterior: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    no_vendible_nuevo: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)


class CajaTurnoModel(Base):
    __tablename__ = "caja_turnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fondo_inicial: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO", index=True)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_ventas_efectivo: Mapped[int] = mapped_column(Integer, default=0)
    total_ventas_tarjeta: Mapped[int] = mapped_column(Integer, default=0)
    total_ventas_transferencia: Mapped[int] = mapped_column(Integer, default=0)
    total_ventas_a_cuenta: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    conteo_fisico: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diferencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    movimientos: Mapped[list["MovimientoCajaModel"]] = relationship(
        back_populates="turno", cascade="all, delete-orphan"
    )


class MovimientoCajaModel(Base):
    __tablename__ = "movimientos_caja"

    id: Mapped[int] = mapped_column(primary_key=True)
    caja_turno_id: Mapped[int] = mapped_column(ForeignKey("caja_turnos.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))
    monto: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    turno: Mapped[CajaTurnoModel] = relationship(back_populates="movimientos")


class VentaMostradorModel(Base):
    __tablename__ = "ventas_mostrador"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    caja_turno_id: Mapped[int] = mapped_column(ForeignKey("caja_turnos.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True)
    metodo_pago: Mapped[str] = mapped_column(String(20), default="EFECTIVO")
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    descuento: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    items: Mapped[list["VentaMostradorItemModel"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )
    pagos: Mapped[list["VentaPagoModel"]] = relationship(back_populates="venta", cascade="all, delete-orphan")


class VentaPagoModel(Base):
    """Cada medio con que se cobró una venta (una venta mixta tiene varios)."""

    __tablename__ = "venta_pagos"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_mostrador.id", ondelete="CASCADE"), index=True)
    metodo: Mapped[str] = mapped_column(String(20))
    monto: Mapped[int] = mapped_column(Integer)
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)

    venta: Mapped["VentaMostradorModel"] = relationship(back_populates="pagos")


class MovimientoCuentaCorrienteModel(Base):
    """Libro de la cuenta corriente de un cliente: cargos (ventas a cuenta) y pagos."""

    __tablename__ = "movimientos_cuenta_corriente"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))
    monto: Mapped[int] = mapped_column(Integer)
    venta_id: Mapped[int | None] = mapped_column(ForeignKey("ventas_mostrador.id", ondelete="SET NULL"), nullable=True)
    metodo_pago: Mapped[str | None] = mapped_column(String(20), nullable=True)
    caja_turno_id: Mapped[int | None] = mapped_column(ForeignKey("caja_turnos.id", ondelete="SET NULL"), nullable=True)
    referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class VentaMostradorItemModel(Base):
    __tablename__ = "venta_mostrador_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_mostrador.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)

    venta: Mapped[VentaMostradorModel] = relationship(back_populates="items")


class StockNoVendibleModel(Base):
    """Unidades de un producto separadas del stock vendible por un motivo
    (averiado, vencido...), con lo que falta resolver."""

    __tablename__ = "stock_no_vendible"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_stock_no_vendible_cantidad"),
        CheckConstraint("cantidad_pendiente >= 0 AND cantidad_pendiente <= cantidad", name="ck_stock_no_vendible_pendiente"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="RESTRICT"), index=True)
    cantidad: Mapped[float] = mapped_column(Numeric(14, 3))
    cantidad_pendiente: Mapped[float] = mapped_column(Numeric(14, 3))
    motivo: Mapped[str] = mapped_column(String(20))
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedores.id", ondelete="SET NULL"), nullable=True, index=True)
    orden_compra_id: Mapped[int | None] = mapped_column(ForeignKey("ordenes_compra.id", ondelete="SET NULL"), nullable=True)
    costo_unitario: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    resoluciones: Mapped[list["ResolucionNoVendibleModel"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan", order_by="ResolucionNoVendibleModel.id"
    )


class ResolucionNoVendibleModel(Base):
    """Cada resolución (total o parcial) de un registro no vendible."""

    __tablename__ = "stock_no_vendible_resoluciones"
    __table_args__ = (CheckConstraint("cantidad > 0", name="ck_resolucion_no_vendible_cantidad"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registro_id: Mapped[int] = mapped_column(ForeignKey("stock_no_vendible.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    cantidad: Mapped[float] = mapped_column(Numeric(14, 3))
    monto: Mapped[int] = mapped_column(Integer, default=0)
    reclamo_id: Mapped[int | None] = mapped_column(ForeignKey("reclamos_proveedor.id", ondelete="SET NULL"), nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    registro: Mapped[StockNoVendibleModel] = relationship(back_populates="resoluciones")


class ReclamoProveedorModel(Base):
    __tablename__ = "reclamos_proveedor"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedores.id", ondelete="SET NULL"), nullable=True, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    proveedor_razon_social: Mapped[str] = mapped_column(String(255))
    proveedor_ruc: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proveedor_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proveedor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proveedor_direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", index=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    respuesta_proveedor: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_nota_credito: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numero_nota_remision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    items: Mapped[list["ReclamoProveedorItemModel"]] = relationship(
        back_populates="reclamo", cascade="all, delete-orphan", order_by="ReclamoProveedorItemModel.id"
    )


class ReclamoProveedorItemModel(Base):
    __tablename__ = "reclamo_proveedor_items"
    __table_args__ = (
        UniqueConstraint("reclamo_id", "registro_id"),
        CheckConstraint("cantidad > 0", name="ck_reclamo_item_cantidad"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reclamo_id: Mapped[int] = mapped_column(ForeignKey("reclamos_proveedor.id", ondelete="CASCADE"), index=True)
    registro_id: Mapped[int] = mapped_column(ForeignKey("stock_no_vendible.id", ondelete="RESTRICT"), index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="RESTRICT"))
    cantidad: Mapped[float] = mapped_column(Numeric(14, 3))
    costo_unitario: Mapped[int] = mapped_column(Integer, default=0)
    resolucion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    monto_nota_credito: Mapped[int] = mapped_column(Integer, default=0)
    nota_resolucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    resuelto_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    resuelto_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    reclamo: Mapped[ReclamoProveedorModel] = relationship(back_populates="items")
