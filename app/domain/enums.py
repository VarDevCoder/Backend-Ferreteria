"""Enumeraciones del dominio ANKOR.

Son la fuente de verdad de los estados de negocio. La capa de infraestructura
los persiste como texto; la capa de aplicación los usa para decidir qué
transiciones son válidas.
"""
from enum import StrEnum


class RolUsuario(StrEnum):
    ADMIN = "admin"
    ANKOR_USER = "ankor_user"
    PROVEEDOR = "proveedor"


class UnidadMedida(StrEnum):
    PIEZA = "pz"
    KILOGRAMO = "kg"
    LITRO = "lt"
    METRO = "m"
    CAJA = "caja"
    UNIDAD = "unidad"


class EstadoPedidoCliente(StrEnum):
    RECIBIDO = "RECIBIDO"
    EN_PROCESO = "EN_PROCESO"
    PRESUPUESTADO = "PRESUPUESTADO"
    ORDEN_COMPRA = "ORDEN_COMPRA"
    MERCADERIA_RECIBIDA = "MERCADERIA_RECIBIDA"
    LISTO_ENVIO = "LISTO_ENVIO"
    ENVIADO = "ENVIADO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class EstadoSolicitudPresupuesto(StrEnum):
    ENVIADA = "ENVIADA"
    VISTA = "VISTA"
    COTIZADA = "COTIZADA"
    SIN_STOCK = "SIN_STOCK"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"
    VENCIDA = "VENCIDA"


class EstadoOrdenCompra(StrEnum):
    BORRADOR = "BORRADOR"
    ENVIADA = "ENVIADA"
    CONFIRMADA = "CONFIRMADA"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDA_PARCIAL = "RECIBIDA_PARCIAL"
    RECIBIDA_COMPLETA = "RECIBIDA_COMPLETA"
    CANCELADA = "CANCELADA"


class EstadoOrdenEnvio(StrEnum):
    PREPARANDO = "PREPARANDO"
    LISTO = "LISTO"
    EN_TRANSITO = "EN_TRANSITO"
    ENTREGADO = "ENTREGADO"
    DEVUELTO = "DEVUELTO"
    CANCELADO = "CANCELADO"


class TipoMovimientoInventario(StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"


class TipoReferenciaMovimiento(StrEnum):
    """A qué documento del flujo ANKOR corresponde un movimiento de inventario."""

    ORDEN_COMPRA = "ORDEN_COMPRA"
    ORDEN_ENVIO = "ORDEN_ENVIO"
    AJUSTE_MANUAL = "AJUSTE_MANUAL"
    VENTA_MOSTRADOR = "VENTA_MOSTRADOR"


class EstadoCajaTurno(StrEnum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class MetodoPago(StrEnum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


class TipoMovimientoCaja(StrEnum):
    """Movimientos de efectivo dentro de un turno que no son una venta."""

    INGRESO = "INGRESO"
    RETIRO = "RETIRO"
