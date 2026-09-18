"""Entidades del dominio ANKOR.

Son `dataclasses` planas con la lógica de negocio (reglas de transición de
estado, totales, validaciones) que en el Laravel original vivía en los
modelos Eloquent. No conocen SQLAlchemy, FastAPI ni Postgres: la capa de
infraestructura las mapea desde/hacia las tablas, y la capa de interfaz las
serializa hacia JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.domain.enums import (
    EstadoCajaTurno,
    EstadoOrdenCompra,
    EstadoOrdenEnvio,
    EstadoPedidoCliente,
    EstadoSolicitudPresupuesto,
    MetodoPago,
    RolUsuario,
    TipoMovimientoCaja,
    TipoMovimientoInventario,
    TipoReferenciaMovimiento,
)


@dataclass
class Usuario:
    id: int | None
    name: str
    email: str
    password_hash: str
    rol: RolUsuario = RolUsuario.ANKOR_USER
    activo: bool = True
    created_at: datetime | None = None

    def es_admin(self) -> bool:
        return self.rol == RolUsuario.ADMIN

    def es_ankor_user(self) -> bool:
        return self.rol in (RolUsuario.ANKOR_USER, RolUsuario.ADMIN)

    def es_proveedor(self) -> bool:
        return self.rol == RolUsuario.PROVEEDOR


@dataclass
class Categoria:
    id: int | None
    nombre: str
    descripcion: str | None = None
    activo: bool = True
    orden: int = 0


@dataclass
class Producto:
    id: int | None
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int | None = None
    precio_compra: int = 0
    precio_venta: int = 0
    stock_actual: Decimal = Decimal("0")
    stock_minimo: Decimal = Decimal("0")
    unidad_medida: str = "pz"
    activo: bool = True

    def tiene_stock_bajo(self) -> bool:
        return self.stock_minimo > 0 and self.stock_actual <= self.stock_minimo

    def calcular_precio_venta(self, margen_porcentaje: Decimal = Decimal("25")) -> int:
        return int(round(self.precio_compra * (1 + margen_porcentaje / 100)))

    def margen(self) -> float:
        if self.precio_compra <= 0:
            return 0.0
        return round((self.precio_venta - self.precio_compra) / self.precio_compra * 100, 1)


@dataclass
class Cliente:
    id: int | None
    nombre: str
    ruc: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    activo: bool = True
    notas: str | None = None


@dataclass
class Proveedor:
    id: int | None
    user_id: int
    razon_social: str
    ruc: str
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    rubros: str | None = None
    notas: str | None = None
    # Datos de conveniencia, resueltos desde el usuario asociado (no persistidos aquí)
    email: str | None = None
    usuario_activo: bool = True


@dataclass
class ProveedorProducto:
    id: int | None
    proveedor_id: int
    producto_id: int
    codigo_proveedor: str | None = None
    nombre_proveedor: str | None = None
    precio: int = 0
    disponible: bool = True
    tiempo_entrega_dias: int | None = None
    notas: str | None = None


@dataclass
class PedidoClienteItem:
    id: int | None
    pedido_cliente_id: int | None
    producto_id: int
    cantidad: Decimal
    precio_unitario: int
    subtotal: int = 0

    def calcular_subtotal(self) -> int:
        self.subtotal = int(round(self.cantidad * self.precio_unitario))
        return self.subtotal


@dataclass
class PedidoCliente:
    id: int | None
    numero: str
    usuario_id: int
    cliente_id: int | None = None
    cliente_nombre: str = ""
    cliente_ruc: str | None = None
    cliente_telefono: str | None = None
    cliente_email: str | None = None
    cliente_direccion: str | None = None
    fecha_pedido: date | None = None
    fecha_entrega_solicitada: date | None = None
    fecha_entrega_estimada: date | None = None
    estado: EstadoPedidoCliente = EstadoPedidoCliente.RECIBIDO
    subtotal: int = 0
    descuento: int = 0
    total: int = 0
    notas: str | None = None
    motivo_cancelacion: str | None = None
    created_at: datetime | None = None
    items: list[PedidoClienteItem] = field(default_factory=list)

    ESTADOS_FINALES = (EstadoPedidoCliente.ENVIADO, EstadoPedidoCliente.ENTREGADO, EstadoPedidoCliente.CANCELADO)

    def calcular_totales(self) -> None:
        self.subtotal = sum(item.calcular_subtotal() for item in self.items)
        descuento_monto = int(round(self.subtotal * self.descuento / 100))
        self.total = max(0, self.subtotal - descuento_monto)

    def puede_ser_cancelado(self) -> bool:
        return self.estado not in self.ESTADOS_FINALES

    def puede_ser_editado(self) -> bool:
        return self.puede_ser_cancelado()

    def puede_generar_orden_compra(self) -> bool:
        return self.estado in (
            EstadoPedidoCliente.RECIBIDO,
            EstadoPedidoCliente.EN_PROCESO,
            EstadoPedidoCliente.PRESUPUESTADO,
        )

    def puede_generar_orden_envio(self) -> bool:
        return self.estado == EstadoPedidoCliente.MERCADERIA_RECIBIDA

    def puede_solicitar_cotizacion(self) -> bool:
        return self.estado in (
            EstadoPedidoCliente.RECIBIDO,
            EstadoPedidoCliente.EN_PROCESO,
            EstadoPedidoCliente.PRESUPUESTADO,
        )


@dataclass
class SolicitudPresupuestoItem:
    id: int | None
    solicitud_presupuesto_id: int | None
    producto_id: int
    cantidad_solicitada: Decimal
    tiene_stock: bool | None = None
    cantidad_disponible: Decimal | None = None
    precio_unitario_cotizado: int | None = None
    subtotal_cotizado: int | None = None


@dataclass
class SolicitudPresupuesto:
    id: int | None
    numero: str
    proveedor_id: int
    usuario_id: int
    pedido_cliente_id: int | None = None
    fecha_solicitud: date | None = None
    fecha_limite_respuesta: date | None = None
    fecha_respuesta: date | None = None
    estado: EstadoSolicitudPresupuesto = EstadoSolicitudPresupuesto.ENVIADA
    mensaje_solicitud: str | None = None
    respuesta_proveedor: str | None = None
    total_cotizado: int | None = None
    dias_entrega_estimados: int | None = None
    created_at: datetime | None = None
    items: list[SolicitudPresupuestoItem] = field(default_factory=list)

    ESTADOS_PENDIENTES = (EstadoSolicitudPresupuesto.ENVIADA, EstadoSolicitudPresupuesto.VISTA)

    def puede_ser_respondida(self) -> bool:
        return self.estado in self.ESTADOS_PENDIENTES

    def puede_ser_aceptada(self) -> bool:
        return self.estado == EstadoSolicitudPresupuesto.COTIZADA

    def calcular_total(self) -> None:
        self.total_cotizado = sum(
            item.subtotal_cotizado or 0 for item in self.items
        )


@dataclass
class OrdenCompraItem:
    id: int | None
    orden_compra_id: int | None
    producto_id: int
    cantidad_solicitada: Decimal
    precio_unitario: int
    cantidad_recibida: Decimal = Decimal("0")
    subtotal: int = 0

    def calcular_subtotal(self) -> int:
        self.subtotal = int(round(self.cantidad_solicitada * self.precio_unitario))
        return self.subtotal

    def recepcion_completa(self) -> bool:
        return self.cantidad_recibida >= self.cantidad_solicitada


@dataclass
class OrdenCompra:
    id: int | None
    numero: str
    usuario_id: int
    pedido_cliente_id: int | None = None
    proveedor_nombre: str = ""
    proveedor_ruc: str | None = None
    proveedor_telefono: str | None = None
    proveedor_email: str | None = None
    proveedor_direccion: str | None = None
    fecha_orden: date | None = None
    fecha_entrega_esperada: date | None = None
    fecha_recepcion: date | None = None
    estado: EstadoOrdenCompra = EstadoOrdenCompra.BORRADOR
    subtotal: int = 0
    descuento: int = 0
    total: int = 0
    notas: str | None = None
    motivo_cancelacion: str | None = None
    created_at: datetime | None = None
    items: list[OrdenCompraItem] = field(default_factory=list)

    def calcular_totales(self) -> None:
        self.subtotal = sum(item.calcular_subtotal() for item in self.items)
        descuento_monto = int(round(self.subtotal * self.descuento / 100))
        self.total = max(0, self.subtotal - descuento_monto)

    def verificar_recepcion_completa(self) -> bool:
        return all(item.recepcion_completa() for item in self.items)

    def puede_ser_enviada(self) -> bool:
        return self.estado == EstadoOrdenCompra.BORRADOR

    def puede_ser_confirmada(self) -> bool:
        return self.estado == EstadoOrdenCompra.ENVIADA

    def puede_marcarse_en_transito(self) -> bool:
        return self.estado == EstadoOrdenCompra.CONFIRMADA

    def puede_recibir_mercaderia(self) -> bool:
        return self.estado in (
            EstadoOrdenCompra.CONFIRMADA,
            EstadoOrdenCompra.EN_TRANSITO,
            EstadoOrdenCompra.RECIBIDA_PARCIAL,
        )

    def puede_ser_editada(self) -> bool:
        return self.estado == EstadoOrdenCompra.BORRADOR

    def puede_ser_cancelada(self) -> bool:
        return self.estado not in (EstadoOrdenCompra.RECIBIDA_COMPLETA, EstadoOrdenCompra.CANCELADA)

    def puede_ser_eliminada(self) -> bool:
        return self.estado in (EstadoOrdenCompra.BORRADOR, EstadoOrdenCompra.CANCELADA)


@dataclass
class OrdenEnvioItem:
    id: int | None
    orden_envio_id: int | None
    producto_id: int
    cantidad: Decimal


@dataclass
class OrdenEnvio:
    id: int | None
    numero: str
    usuario_id: int
    pedido_cliente_id: int
    direccion_entrega: str
    contacto_entrega: str | None = None
    telefono_entrega: str | None = None
    fecha_generacion: date | None = None
    fecha_envio: date | None = None
    fecha_entrega: date | None = None
    estado: EstadoOrdenEnvio = EstadoOrdenEnvio.PREPARANDO
    metodo_envio: str | None = None
    numero_guia: str | None = None
    transportista: str | None = None
    notas: str | None = None
    observaciones_entrega: str | None = None
    created_at: datetime | None = None
    items: list[OrdenEnvioItem] = field(default_factory=list)

    def puede_marcarse_lista(self) -> bool:
        return self.estado == EstadoOrdenEnvio.PREPARANDO

    def puede_ser_despachada(self) -> bool:
        return self.estado == EstadoOrdenEnvio.LISTO

    def puede_ser_entregada(self) -> bool:
        return self.estado == EstadoOrdenEnvio.EN_TRANSITO

    def puede_ser_devuelta(self) -> bool:
        return self.estado == EstadoOrdenEnvio.EN_TRANSITO

    def puede_ser_cancelada(self) -> bool:
        return self.estado not in (EstadoOrdenEnvio.ENTREGADO, EstadoOrdenEnvio.CANCELADO)

    def puede_ser_eliminada(self) -> bool:
        return self.estado in (EstadoOrdenEnvio.PREPARANDO, EstadoOrdenEnvio.CANCELADO)


@dataclass
class MovimientoInventario:
    id: int | None
    producto_id: int
    tipo: TipoMovimientoInventario
    cantidad: Decimal
    stock_anterior: Decimal
    stock_nuevo: Decimal
    referencia_tipo: TipoReferenciaMovimiento
    referencia_id: int
    usuario_id: int | None = None
    observaciones: str | None = None
    created_at: datetime | None = None


@dataclass
class MovimientoCaja:
    id: int | None
    caja_turno_id: int
    tipo: TipoMovimientoCaja
    monto: int
    motivo: str | None = None
    usuario_id: int | None = None
    created_at: datetime | None = None


@dataclass
class CajaTurno:
    id: int | None
    usuario_id: int
    fondo_inicial: int = 0
    estado: EstadoCajaTurno = EstadoCajaTurno.ABIERTO
    fecha_apertura: datetime | None = None
    fecha_cierre: datetime | None = None
    total_ventas_efectivo: int = 0
    total_ventas_tarjeta: int = 0
    total_ventas_transferencia: int = 0
    conteo_fisico: int | None = None
    diferencia: int | None = None
    notas: str | None = None
    movimientos: list[MovimientoCaja] = field(default_factory=list)

    def puede_registrar_ventas(self) -> bool:
        return self.estado == EstadoCajaTurno.ABIERTO

    def puede_cerrarse(self) -> bool:
        return self.estado == EstadoCajaTurno.ABIERTO

    def saldo_esperado(self) -> int:
        ingresos = sum(m.monto for m in self.movimientos if m.tipo == TipoMovimientoCaja.INGRESO)
        retiros = sum(m.monto for m in self.movimientos if m.tipo == TipoMovimientoCaja.RETIRO)
        return self.fondo_inicial + self.total_ventas_efectivo + ingresos - retiros

    def calcular_cierre(self, conteo_fisico: int) -> None:
        self.conteo_fisico = conteo_fisico
        self.diferencia = conteo_fisico - self.saldo_esperado()
        self.estado = EstadoCajaTurno.CERRADO


@dataclass
class VentaMostradorItem:
    id: int | None
    venta_id: int | None
    producto_id: int
    cantidad: Decimal
    precio_unitario: int
    subtotal: int = 0

    def calcular_subtotal(self) -> int:
        self.subtotal = int(round(self.cantidad * self.precio_unitario))
        return self.subtotal


@dataclass
class VentaMostrador:
    id: int | None
    numero: str
    caja_turno_id: int
    usuario_id: int
    cliente_id: int | None = None
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO
    subtotal: int = 0
    descuento: int = 0
    total: int = 0
    notas: str | None = None
    created_at: datetime | None = None
    items: list[VentaMostradorItem] = field(default_factory=list)

    def calcular_totales(self) -> None:
        self.subtotal = sum(item.calcular_subtotal() for item in self.items)
        descuento_monto = int(round(self.subtotal * self.descuento / 100))
        self.total = max(0, self.subtotal - descuento_monto)
