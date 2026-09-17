"""Casos de uso de Solicitudes de Presupuesto (RFQ a proveedores).

Cubre CU-11 (generar solicitud individual), CU-12 (el proveedor responde,
desde el portal) y CU-13 ★ (aceptar la cotización ganadora y emitir la Orden
de Compra en una única operación atómica) — el caso de uso central del MVP.
"""
from datetime import date

from app.domain.entities import OrdenCompra, OrdenCompraItem, SolicitudPresupuesto, SolicitudPresupuestoItem
from app.domain.enums import EstadoOrdenCompra, EstadoPedidoCliente, EstadoSolicitudPresupuesto
from app.domain.exceptions import PermisoDenegado, RecursoNoEncontrado, TransicionDeEstadoInvalida
from app.domain.repositories import (
    OrdenCompraRepository,
    PedidoClienteRepository,
    ProveedorRepository,
    SolicitudPresupuestoRepository,
)


class SolicitudPresupuestoService:
    def __init__(
        self,
        solicitudes: SolicitudPresupuestoRepository,
        proveedores: ProveedorRepository,
        pedidos: PedidoClienteRepository,
        ordenes_compra: OrdenCompraRepository,
    ):
        self._solicitudes = solicitudes
        self._proveedores = proveedores
        self._pedidos = pedidos
        self._ordenes_compra = ordenes_compra

    def listar(
        self, estado: str | None = None, proveedor_id: int | None = None, pedido_cliente_id: int | None = None
    ) -> list[SolicitudPresupuesto]:
        return self._solicitudes.list(estado=estado, proveedor_id=proveedor_id, pedido_cliente_id=pedido_cliente_id)

    def obtener(self, solicitud_id: int) -> SolicitudPresupuesto:
        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise RecursoNoEncontrado("SolicitudPresupuesto", solicitud_id)
        return solicitud

    def crear(
        self,
        proveedor_id: int,
        usuario_id: int,
        items: list[dict],
        pedido_cliente_id: int | None = None,
        fecha_limite_respuesta: date | None = None,
        mensaje_solicitud: str | None = None,
    ) -> SolicitudPresupuesto:
        solicitud = SolicitudPresupuesto(
            id=None,
            numero=self._solicitudes.siguiente_numero(),
            proveedor_id=proveedor_id,
            usuario_id=usuario_id,
            pedido_cliente_id=pedido_cliente_id,
            fecha_solicitud=date.today(),
            fecha_limite_respuesta=fecha_limite_respuesta,
            estado=EstadoSolicitudPresupuesto.ENVIADA,
            mensaje_solicitud=mensaje_solicitud,
            items=[
                SolicitudPresupuestoItem(
                    id=None, solicitud_presupuesto_id=None, producto_id=i["producto_id"],
                    cantidad_solicitada=i["cantidad_solicitada"],
                )
                for i in items
            ],
        )
        solicitud = self._solicitudes.add(solicitud)

        if pedido_cliente_id is not None:
            pedido = self._pedidos.get_by_id(pedido_cliente_id)
            if pedido is not None and pedido.estado == EstadoPedidoCliente.EN_PROCESO:
                pedido.estado = EstadoPedidoCliente.PRESUPUESTADO
                self._pedidos.update(pedido)

        return solicitud

    def eliminar(self, solicitud_id: int) -> None:
        solicitud = self.obtener(solicitud_id)
        if solicitud.estado != EstadoSolicitudPresupuesto.ENVIADA:
            raise TransicionDeEstadoInvalida("Solo se pueden eliminar solicitudes en estado enviada")
        self._solicitudes.delete(solicitud_id)

    # --- Portal proveedor (CU-12) -------------------------------------------------

    def ver_como_proveedor(self, solicitud_id: int, proveedor_id: int) -> SolicitudPresupuesto:
        solicitud = self.obtener(solicitud_id)
        self._verificar_pertenece_a_proveedor(solicitud, proveedor_id)
        if solicitud.estado == EstadoSolicitudPresupuesto.ENVIADA:
            solicitud.estado = EstadoSolicitudPresupuesto.VISTA
            solicitud = self._solicitudes.update(solicitud)
        return solicitud

    def enviar_cotizacion(
        self, solicitud_id: int, proveedor_id: int, dias_entrega_estimados: int,
        respuestas_items: list[dict], respuesta_proveedor: str | None = None,
    ) -> SolicitudPresupuesto:
        """`respuestas_items`: [{item_id, tiene_stock, cantidad_disponible, precio_unitario_cotizado}, ...]"""
        solicitud = self.obtener(solicitud_id)
        self._verificar_pertenece_a_proveedor(solicitud, proveedor_id)
        if not solicitud.puede_ser_respondida():
            raise TransicionDeEstadoInvalida("Esta solicitud ya no puede ser respondida")

        respuestas_por_id = {r["item_id"]: r for r in respuestas_items}
        todos_con_stock = True
        for item in solicitud.items:
            respuesta = respuestas_por_id.get(item.id)
            if respuesta is None:
                continue
            tiene_stock = bool(respuesta.get("tiene_stock"))
            if not tiene_stock:
                todos_con_stock = False
                item.tiene_stock = False
                item.cantidad_disponible = None
                item.precio_unitario_cotizado = None
                item.subtotal_cotizado = None
            else:
                cantidad = respuesta.get("cantidad_disponible") or 0
                precio = respuesta.get("precio_unitario_cotizado") or 0
                item.tiene_stock = True
                item.cantidad_disponible = cantidad
                item.precio_unitario_cotizado = precio
                item.subtotal_cotizado = int(round(cantidad * precio))

        solicitud.calcular_total()
        solicitud.estado = (
            EstadoSolicitudPresupuesto.COTIZADA if todos_con_stock else EstadoSolicitudPresupuesto.SIN_STOCK
        )
        solicitud.respuesta_proveedor = respuesta_proveedor
        solicitud.dias_entrega_estimados = dias_entrega_estimados
        solicitud.fecha_respuesta = date.today()
        return self._solicitudes.update(solicitud)

    def marcar_sin_stock(self, solicitud_id: int, proveedor_id: int, respuesta_proveedor: str) -> SolicitudPresupuesto:
        solicitud = self.obtener(solicitud_id)
        self._verificar_pertenece_a_proveedor(solicitud, proveedor_id)
        if not solicitud.puede_ser_respondida():
            raise TransicionDeEstadoInvalida("Esta solicitud ya no puede ser respondida")

        for item in solicitud.items:
            item.tiene_stock = False
            item.cantidad_disponible = 0

        solicitud.estado = EstadoSolicitudPresupuesto.SIN_STOCK
        solicitud.respuesta_proveedor = respuesta_proveedor
        solicitud.fecha_respuesta = date.today()
        return self._solicitudes.update(solicitud)

    # --- Decisión de Compras (CU-13 ★) ---------------------------------------------

    def aceptar(self, solicitud_id: int, usuario_id: int) -> OrdenCompra:
        """Acepta la cotización y genera la Orden de Compra en una sola operación:
        el caso de uso central del MVP (HU-09)."""
        solicitud = self.obtener(solicitud_id)
        if not solicitud.puede_ser_aceptada():
            raise TransicionDeEstadoInvalida("Esta cotización no puede ser aceptada")

        proveedor = self._proveedores.get_by_id(solicitud.proveedor_id)
        if proveedor is None:
            raise RecursoNoEncontrado("Proveedor", solicitud.proveedor_id)

        items_orden = [
            OrdenCompraItem(
                id=None, orden_compra_id=None, producto_id=item.producto_id,
                cantidad_solicitada=item.cantidad_disponible, precio_unitario=item.precio_unitario_cotizado,
            )
            for item in solicitud.items
            if item.tiene_stock and (item.cantidad_disponible or 0) > 0
        ]

        orden = OrdenCompra(
            id=None,
            numero=self._ordenes_compra.siguiente_numero(),
            usuario_id=usuario_id,
            pedido_cliente_id=solicitud.pedido_cliente_id,
            proveedor_nombre=proveedor.razon_social,
            proveedor_ruc=proveedor.ruc,
            proveedor_telefono=proveedor.telefono,
            proveedor_email=proveedor.email,
            proveedor_direccion=proveedor.direccion,
            fecha_orden=date.today(),
            estado=EstadoOrdenCompra.BORRADOR,
            items=items_orden,
        )
        orden.calcular_totales()
        orden = self._ordenes_compra.add(orden)

        solicitud.estado = EstadoSolicitudPresupuesto.ACEPTADA
        self._solicitudes.update(solicitud)

        if solicitud.pedido_cliente_id is not None:
            pedido = self._pedidos.get_by_id(solicitud.pedido_cliente_id)
            if pedido is not None:
                pedido.estado = EstadoPedidoCliente.ORDEN_COMPRA
                self._pedidos.update(pedido)

        return orden

    def rechazar(self, solicitud_id: int) -> SolicitudPresupuesto:
        solicitud = self.obtener(solicitud_id)
        if not solicitud.puede_ser_aceptada():
            raise TransicionDeEstadoInvalida("Esta cotización no puede ser rechazada")
        solicitud.estado = EstadoSolicitudPresupuesto.RECHAZADA
        return self._solicitudes.update(solicitud)

    @staticmethod
    def _verificar_pertenece_a_proveedor(solicitud: SolicitudPresupuesto, proveedor_id: int) -> None:
        if solicitud.proveedor_id != proveedor_id:
            raise PermisoDenegado("Esta solicitud no pertenece a tu cuenta de proveedor")
