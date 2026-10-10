"""Entidades del dominio de SAIL.

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

from app.domain.exceptions import SolicitudInvalida
from app.domain.enums import (
    EstadoCajaTurno,
    EstadoOrdenCompra,
    EstadoOrdenEnvio,
    EstadoPedidoCliente,
    EstadoReclamoProveedor,
    EstadoSolicitudPresupuesto,
    EstadoStockNoVendible,
    MetodoPago,
    MotivoNoVendible,
    ResolucionItemReclamo,
    RolUsuario,
    TipoMovimientoCaja,
    TipoMovimientoCuentaCorriente,
    TipoMovimientoInventario,
    TipoReferenciaMovimiento,
    TipoResolucionNoVendible,
)


@dataclass
class Usuario:
    id: int | None
    name: str
    email: str
    password_hash: str
    rol: RolUsuario = RolUsuario.VENDEDOR
    activo: bool = True
    created_at: datetime | None = None
    version_sesion: int = 0

    def es_admin(self) -> bool:
        return self.rol == RolUsuario.ADMIN

    def es_interno(self) -> bool:
        """Personal de la ferretería (puede entrar al sistema)."""
        return self.rol in RolUsuario.internos()

    def es_proveedor(self) -> bool:
        return self.rol == RolUsuario.PROVEEDOR


@dataclass
class Empresa:
    """Datos de la ferretería que usa el sistema: aparecen en la pantalla de
    ingreso, en el encabezado y en los tickets. Hay una sola fila."""

    nombre_comercial: str = "Mi Ferretería"
    razon_social: str | None = None
    ruc: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    telefono: str | None = None
    email: str | None = None
    # Los importes se guardan en unidades enteras de la moneda (sin centavos).
    moneda_codigo: str = "PYG"
    moneda_simbolo: str = "Gs."
    locale: str = "es-PY"
    iva_porcentaje: int = 10
    margen_ganancia_defecto: int = 25
    pie_ticket: str | None = "¡Gracias por su compra!"


@dataclass
class Categoria:
    id: int | None
    nombre: str
    descripcion: str | None = None
    activo: bool = True
    orden: int = 0


# Unidades que se venden fraccionadas (por ejemplo 2,5 m de cable o 1,25 kg
# de clavos). Cualquier otra (pz, unidad, caja, bolsa, rollo, lata...) solo
# admite cantidades enteras.
UNIDADES_FRACCIONABLES = frozenset({"m", "kg", "lt", "l"})


@dataclass
class Producto:
    id: int | None
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int | None = None
    precio_compra: int = 0
    precio_venta: int = 0
    # Stock vendible: lo único que pueden usar la caja, los pedidos y los envíos.
    stock_actual: Decimal = Decimal("0")
    stock_minimo: Decimal = Decimal("0")
    unidad_medida: str = "pz"
    activo: bool = True
    # Unidades que existen pero no se pueden vender (averiadas, vencidas...).
    # Solo las mueve el servicio de stock no vendible.
    stock_no_vendible: Decimal = Decimal("0")

    def stock_total(self) -> Decimal:
        """Unidades físicas: vendibles más no vendibles."""
        return Decimal(self.stock_actual) + Decimal(self.stock_no_vendible or 0)

    def es_fraccionable(self) -> bool:
        return (self.unidad_medida or "").strip().lower() in UNIDADES_FRACCIONABLES

    def validar_cantidad(self, cantidad) -> None:
        """Las unidades enteras (pz, caja...) no aceptan decimales."""
        valor = Decimal(str(cantidad))
        if not self.es_fraccionable() and valor != valor.to_integral_value():
            from app.domain.formato import formato_cantidad

            raise SolicitudInvalida(
                f"{self.nombre} se vende por unidad entera ({self.unidad_medida}): "
                f"no se puede usar {formato_cantidad(valor)}"
            )

    def validar_vendible(self) -> None:
        if not self.activo:
            raise SolicitudInvalida(f"{self.nombre} está desactivado: no se puede vender ni pedir")

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
    # Límite de deuda en cuenta corriente ("a cuenta"). 0 = no puede comprar a cuenta.
    limite_credito: int = 0


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
        """Con la mercadería recibida del proveedor, o antes de comprar si
        alcanza el stock del depósito (el servicio valida el stock)."""
        return self.estado in (
            EstadoPedidoCliente.RECIBIDO,
            EstadoPedidoCliente.EN_PROCESO,
            EstadoPedidoCliente.PRESUPUESTADO,
            EstadoPedidoCliente.MERCADERIA_RECIBIDA,
        )

    def cantidades_por_producto(self) -> dict[int, Decimal]:
        """Cantidad total pedida por producto (un producto puede repetirse en varias líneas)."""
        total: dict[int, Decimal] = {}
        for item in self.items:
            total[item.producto_id] = total.get(item.producto_id, Decimal("0")) + Decimal(item.cantidad)
        return total

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
        """Solo antes de salir del depósito. Un envío despachado ya descontó
        stock: si vuelve, se registra como devolución (que lo reingresa)."""
        return self.estado in (EstadoOrdenEnvio.PREPARANDO, EstadoOrdenEnvio.LISTO)

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
    # Solo en movimientos que tocan el stock no vendible (stock_anterior y
    # stock_nuevo siempre son del stock vendible).
    no_vendible_anterior: Decimal | None = None
    no_vendible_nuevo: Decimal | None = None


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
    total_ventas_a_cuenta: int = 0
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
class VentaPago:
    metodo: MetodoPago
    monto: int
    referencia: str | None = None  # ej. últimos dígitos de la tarjeta, N° de cheque o de operación
    id: int | None = None


@dataclass
class MovimientoCuentaCorriente:
    id: int | None
    cliente_id: int
    tipo: TipoMovimientoCuentaCorriente
    monto: int
    venta_id: int | None = None
    metodo_pago: MetodoPago | None = None
    caja_turno_id: int | None = None
    referencia: str | None = None
    usuario_id: int | None = None
    created_at: datetime | None = None


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
    pagos: list[VentaPago] = field(default_factory=list)

    def monto_a_cuenta(self) -> int:
        return sum(p.monto for p in self.pagos if p.metodo == MetodoPago.CUENTA_CORRIENTE)

    def calcular_totales(self) -> None:
        self.subtotal = sum(item.calcular_subtotal() for item in self.items)
        descuento_monto = int(round(self.subtotal * self.descuento / 100))
        self.total = max(0, self.subtotal - descuento_monto)


# --- Stock no vendible y reclamos al proveedor -----------------------------------

@dataclass
class ResolucionNoVendible:
    """Qué se hizo con parte (o todas) las unidades de un registro no vendible."""

    id: int | None
    registro_id: int
    tipo: TipoResolucionNoVendible
    cantidad: Decimal
    # Pérdida (descarte) o importe de la nota de crédito del proveedor.
    monto: int = 0
    reclamo_id: int | None = None
    nota: str | None = None
    usuario_id: int | None = None
    usuario_nombre: str | None = None
    created_at: datetime | None = None


@dataclass
class StockNoVendible:
    """Unidades de un producto que pasaron de vendibles a no vendibles por un
    mismo motivo. Siguen existiendo (cuentan en el stock total) hasta que se
    resuelven: reparadas, descartadas o devueltas al proveedor por un reclamo."""

    id: int | None
    producto_id: int
    cantidad: Decimal                 # unidades que se marcaron
    cantidad_pendiente: Decimal       # las que todavía no se resolvieron
    motivo: MotivoNoVendible
    nota: str | None = None
    proveedor_id: int | None = None
    orden_compra_id: int | None = None
    costo_unitario: int = 0           # precio de compra al momento de marcarlas
    estado: EstadoStockNoVendible = EstadoStockNoVendible.PENDIENTE
    usuario_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Calculados al leer (no se guardan en la fila).
    cantidad_en_reclamo: Decimal = Decimal("0")
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    unidad_medida: str | None = None
    proveedor_nombre: str | None = None
    usuario_nombre: str | None = None
    resoluciones: list[ResolucionNoVendible] = field(default_factory=list)

    def cantidad_libre(self) -> Decimal:
        """Unidades sin resolver que no están reservadas en un reclamo abierto:
        las únicas que se pueden reparar, descartar o sumar a otro reclamo."""
        return max(Decimal("0"), Decimal(self.cantidad_pendiente) - Decimal(self.cantidad_en_reclamo))

    def valor_pendiente(self) -> int:
        return int(round(Decimal(self.cantidad_pendiente) * self.costo_unitario))

    def recalcular_estado(self) -> None:
        if self.cantidad_pendiente <= 0:
            self.estado = EstadoStockNoVendible.RESUELTO
        elif self.cantidad_en_reclamo >= self.cantidad_pendiente:
            self.estado = EstadoStockNoVendible.EN_RECLAMO
        else:
            self.estado = EstadoStockNoVendible.PENDIENTE


@dataclass
class ReclamoProveedorItem:
    id: int | None
    reclamo_id: int | None
    registro_id: int
    producto_id: int
    cantidad: Decimal
    costo_unitario: int = 0
    resolucion: ResolucionItemReclamo | None = None
    monto_nota_credito: int = 0
    nota_resolucion: str | None = None
    resuelto_por: int | None = None
    resuelto_at: datetime | None = None
    # Calculados al leer.
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    unidad_medida: str | None = None
    motivo: MotivoNoVendible | None = None
    nota_registro: str | None = None

    def subtotal(self) -> int:
        return int(round(Decimal(self.cantidad) * self.costo_unitario))

    def esta_resuelto(self) -> bool:
        return self.resolucion is not None


@dataclass
class ReclamoProveedor:
    """Reclamo a un proveedor por unidades no vendibles que le corresponden.

    BORRADOR → ENVIADO → ACEPTADO → RESUELTO (cuando todos los ítems tienen
    resolución), o ENVIADO → RECHAZADO. Los datos del proveedor se copian al
    crear el reclamo (como en la orden de compra) para que el documento no
    cambie si después se edita o borra el proveedor."""

    id: int | None
    numero: str
    proveedor_id: int | None
    usuario_id: int
    proveedor_razon_social: str = ""
    proveedor_ruc: str | None = None
    proveedor_telefono: str | None = None
    proveedor_email: str | None = None
    proveedor_direccion: str | None = None
    estado: EstadoReclamoProveedor = EstadoReclamoProveedor.BORRADOR
    notas: str | None = None
    respuesta_proveedor: str | None = None
    motivo_rechazo: str | None = None
    # Números de documentos que emite el proveedor o que acompañan el traslado
    # (SAIL no genera documentos fiscales: solo los registra).
    numero_nota_credito: str | None = None
    numero_nota_remision: str | None = None
    fecha_envio: datetime | None = None
    fecha_respuesta: datetime | None = None
    fecha_resolucion: datetime | None = None
    created_at: datetime | None = None
    usuario_nombre: str | None = None
    items: list[ReclamoProveedorItem] = field(default_factory=list)

    ESTADOS_ABIERTOS = (EstadoReclamoProveedor.BORRADOR, EstadoReclamoProveedor.ENVIADO, EstadoReclamoProveedor.ACEPTADO)

    def esta_abierto(self) -> bool:
        return self.estado in self.ESTADOS_ABIERTOS

    def puede_editarse(self) -> bool:
        return self.estado == EstadoReclamoProveedor.BORRADOR

    def puede_eliminarse(self) -> bool:
        return self.estado == EstadoReclamoProveedor.BORRADOR

    def puede_enviarse(self) -> bool:
        return self.estado == EstadoReclamoProveedor.BORRADOR and bool(self.items)

    def puede_responderse(self) -> bool:
        """Aceptar o rechazar: solo un reclamo enviado."""
        return self.estado == EstadoReclamoProveedor.ENVIADO

    def puede_resolver_items(self) -> bool:
        return self.estado == EstadoReclamoProveedor.ACEPTADO

    def todos_los_items_resueltos(self) -> bool:
        return bool(self.items) and all(i.esta_resuelto() for i in self.items)

    def total_reclamado(self) -> int:
        return sum(i.subtotal() for i in self.items)

    def total_nota_credito(self) -> int:
        return sum(i.monto_nota_credito or 0 for i in self.items)
