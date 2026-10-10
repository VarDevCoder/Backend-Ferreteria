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
    LISTO_RETIRO = "LISTO_RETIRO"  # preparado: el cliente lo retira en el local
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
    LISTO = "LISTO"                # listo para despachar (entrega a domicilio)
    LISTO_RETIRO = "LISTO_RETIRO"  # listo para que el cliente lo retire en el local
    EN_TRANSITO = "EN_TRANSITO"
    ENTREGADO = "ENTREGADO"
    DEVUELTO = "DEVUELTO"
    CANCELADO = "CANCELADO"


class TipoMovimientoInventario(StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    # Paso entre stock vendible y no vendible (el total físico no cambia).
    TRASPASO = "TRASPASO"
    # Baja con pérdida de unidades no vendibles (descarte).
    BAJA = "BAJA"


class TipoReferenciaMovimiento(StrEnum):
    """A qué documento del flujo comercial corresponde un movimiento de inventario."""

    ORDEN_COMPRA = "ORDEN_COMPRA"
    ORDEN_ENVIO = "ORDEN_ENVIO"
    AJUSTE_MANUAL = "AJUSTE_MANUAL"
    VENTA_MOSTRADOR = "VENTA_MOSTRADOR"
    STOCK_NO_VENDIBLE = "STOCK_NO_VENDIBLE"    # registro de unidades no vendibles
    RECLAMO_PROVEEDOR = "RECLAMO_PROVEEDOR"    # resolución de un reclamo al proveedor


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


class MotivoNoVendible(StrEnum):
    """Por qué unas unidades dejan de poder venderse."""

    AVERIADO = "AVERIADO"
    ABOLLADO = "ABOLLADO"
    VENCIDO = "VENCIDO"
    DEFECTO_FABRICA = "DEFECTO_FABRICA"
    OTRO = "OTRO"  # exige una nota que explique el motivo


class EstadoStockNoVendible(StrEnum):
    """Estado de un registro de unidades no vendibles.

    PENDIENTE: hay unidades sin resolver que no están en ningún reclamo abierto.
    EN_RECLAMO: todas las unidades sin resolver están en un reclamo abierto.
    RESUELTO: ya no quedan unidades sin resolver.
    """

    PENDIENTE = "PENDIENTE"
    EN_RECLAMO = "EN_RECLAMO"
    RESUELTO = "RESUELTO"


class TipoResolucionNoVendible(StrEnum):
    """Cómo se resolvieron unidades no vendibles."""

    REPARADO = "REPARADO"                              # vuelven a stock vendible
    DESCARTADO = "DESCARTADO"                          # baja con pérdida
    REPUESTO_PROVEEDOR = "REPUESTO_PROVEEDOR"          # el proveedor se las llevó y entregó mercadería nueva
    NOTA_CREDITO_PROVEEDOR = "NOTA_CREDITO_PROVEEDOR"  # el proveedor se las llevó y emitió nota de crédito


class EstadoReclamoProveedor(StrEnum):
    BORRADOR = "BORRADOR"
    ENVIADO = "ENVIADO"
    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"
    RESUELTO = "RESUELTO"


class ResolucionItemReclamo(StrEnum):
    """Respuesta del proveedor para cada ítem de un reclamo aceptado."""

    REPOSICION = "REPOSICION"      # repone la mercadería
    NOTA_CREDITO = "NOTA_CREDITO"  # emite una nota de crédito por un monto
    RECHAZADO = "RECHAZADO"        # no acepta ese ítem: las unidades siguen no vendibles


class ModalidadEntrega(StrEnum):
    """Cómo recibe el cliente un pedido."""

    ENTREGA_DOMICILIO = "ENTREGA_DOMICILIO"  # se le lleva (orden de envío con despacho)
    RETIRA_CLIENTE = "RETIRA_CLIENTE"        # pasa a buscarlo por el local


class FormaPagoPedido(StrEnum):
    """Cómo se acordó cobrar un pedido."""

    ANTICIPADO = "ANTICIPADO"              # se paga todo antes de entregar ("pagado a retirar / a entregar")
    CONTRA_ENTREGA = "CONTRA_ENTREGA"      # se cobra al entregar; el repartidor rinde después en caja
    CUENTA_CORRIENTE = "CUENTA_CORRIENTE"  # al entregar se carga a la cuenta corriente del cliente


class EstadoPagoPedido(StrEnum):
    """Situación del cobro de un pedido (la calcula el backend)."""

    PENDIENTE = "PENDIENTE"          # no se cobró nada
    PARCIAL = "PARCIAL"              # tiene una seña o pago parcial
    PAGADO = "PAGADO"                # cobrado por completo
    A_CUENTA = "A_CUENTA"            # cubierto, con una parte cargada a la cuenta corriente
    POR_RENDIR = "POR_RENDIR"        # entregado contra entrega: falta que el repartidor rinda en caja
    SIN_REGISTRO = "SIN_REGISTRO"    # pedido anterior a que SAIL registrara cobros de pedidos


class TipoPagoPedido(StrEnum):
    ANTICIPO = "ANTICIPO"                  # seña o pago anticipado, antes de entregar
    RENDICION = "RENDICION"                # cobro contra entrega rendido en caja
    CARGO_CUENTA = "CARGO_CUENTA"          # saldo cargado a la cuenta corriente al entregar
