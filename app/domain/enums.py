"""Enumeraciones del dominio.

Son la fuente de verdad de los estados de negocio. La capa de infraestructura
los persiste como texto; la capa de aplicación los usa para decidir qué
transiciones son válidas.
"""
from enum import StrEnum


class RolUsuario(StrEnum):
    """Roles del personal de la ferretería (más el de proveedor, que no entra
    al sistema interno). Qué puede hacer cada uno está en
    `app.application.permisos`."""

    ADMIN = "admin"            # dueño / gerente: todo, incluidos usuarios y configuración
    ENCARGADO = "encargado"    # encargado de sucursal: toda la operación, sin usuarios ni configuración
    VENDEDOR = "vendedor"      # mostrador: caja, pedidos y clientes
    DEPOSITO = "deposito"      # depósito: inventario, recepción de compras y envíos
    PROVEEDOR = "proveedor"

    @classmethod
    def internos(cls) -> tuple["RolUsuario", ...]:
        return (cls.ADMIN, cls.ENCARGADO, cls.VENDEDOR, cls.DEPOSITO)


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
    """Medios de pago de una venta. Una venta puede combinar varios (pago
    mixto); en ese caso la venta figura como MIXTO y el detalle está en sus
    pagos."""

    EFECTIVO = "EFECTIVO"
    TARJETA_DEBITO = "TARJETA_DEBITO"
    TARJETA_CREDITO = "TARJETA_CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    QR = "QR"                          # QR / billetera electrónica
    CHEQUE = "CHEQUE"
    CUENTA_CORRIENTE = "CUENTA_CORRIENTE"  # "a cuenta": queda como deuda del cliente
    MIXTO = "MIXTO"                    # solo como resumen de una venta con varios pagos
    TARJETA = "TARJETA"                # histórico: ventas anteriores a separar débito/crédito

    @classmethod
    def para_cobrar(cls) -> tuple["MetodoPago", ...]:
        """Medios que se pueden elegir al cobrar (excluye MIXTO y el histórico)."""
        return (cls.EFECTIVO, cls.TARJETA_DEBITO, cls.TARJETA_CREDITO, cls.TRANSFERENCIA, cls.QR, cls.CHEQUE, cls.CUENTA_CORRIENTE)

    def es_tarjeta(self) -> bool:
        return self in (MetodoPago.TARJETA, MetodoPago.TARJETA_DEBITO, MetodoPago.TARJETA_CREDITO)


class TipoMovimientoCuentaCorriente(StrEnum):
    CARGO = "CARGO"  # venta a cuenta: aumenta la deuda del cliente
    PAGO = "PAGO"    # cobro: la reduce


class TipoMovimientoCaja(StrEnum):
    """Movimientos de efectivo dentro de un turno que no son una venta."""

    INGRESO = "INGRESO"
    RETIRO = "RETIRO"
