"""Casos de uso de Órdenes de Envío al cliente (CU-17 generar, CU-18 despachar).

El despacho valida stock antes de descontar (RF14) y cada salida/devolución
deja su movimiento en el Kardex, igual que la recepción de compra.
"""
from datetime import date
from decimal import Decimal

from app.domain.entities import MovimientoInventario, OrdenEnvio, OrdenEnvioItem
from app.domain.enums import EstadoOrdenEnvio, EstadoPedidoCliente, TipoMovimientoInventario, TipoReferenciaMovimiento
from app.domain.exceptions import RecursoNoEncontrado, StockInsuficiente, TransicionDeEstadoInvalida
from app.domain.repositories import (
    MovimientoInventarioRepository,
    OrdenEnvioRepository,
    PedidoClienteRepository,
    ProductoRepository,
)


class OrdenEnvioService:
    def __init__(
        self,
        ordenes: OrdenEnvioRepository,
        productos: ProductoRepository,
        movimientos: MovimientoInventarioRepository,
        pedidos: PedidoClienteRepository,
    ):
        self._ordenes = ordenes
        self._productos = productos
        self._movimientos = movimientos
        self._pedidos = pedidos

    def listar(self, estado: str | None = None, busqueda: str | None = None) -> list[OrdenEnvio]:
        return self._ordenes.list(estado=estado, busqueda=busqueda)

    def obtener(self, orden_id: int) -> OrdenEnvio:
        orden = self._ordenes.get_by_id(orden_id)
        if orden is None:
            raise RecursoNoEncontrado("OrdenEnvio", orden_id)
        return orden

    def crear(
        self,
        usuario_id: int,
        pedido_cliente_id: int,
        direccion_entrega: str,
        items: list[dict],
        contacto_entrega: str | None = None,
        telefono_entrega: str | None = None,
        metodo_envio: str | None = None,
        transportista: str | None = None,
        notas: str | None = None,
    ) -> OrdenEnvio:
        pedido = self._pedidos.get_by_id(pedido_cliente_id)
        if pedido is None:
            raise RecursoNoEncontrado("PedidoCliente", pedido_cliente_id)
        if not pedido.puede_generar_orden_envio():
            raise TransicionDeEstadoInvalida("Este pedido no puede generar orden de envío")

        orden = OrdenEnvio(
            id=None,
            numero=self._ordenes.siguiente_numero(),
            usuario_id=usuario_id,
            pedido_cliente_id=pedido_cliente_id,
            direccion_entrega=direccion_entrega,
            contacto_entrega=contacto_entrega,
            telefono_entrega=telefono_entrega,
            fecha_generacion=date.today(),
            metodo_envio=metodo_envio,
            transportista=transportista,
            notas=notas,
            estado=EstadoOrdenEnvio.PREPARANDO,
            items=[
                OrdenEnvioItem(
                    id=None, orden_envio_id=None, producto_id=i["producto_id"],
                    cantidad=Decimal(str(i["cantidad"])),
                )
                for i in items
            ],
        )
        orden = self._ordenes.add(orden)

        pedido.estado = EstadoPedidoCliente.LISTO_ENVIO
        self._pedidos.update(pedido)
        return orden

    def eliminar(self, orden_id: int) -> None:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_eliminada():
            raise TransicionDeEstadoInvalida("Solo se pueden eliminar órdenes en preparación o canceladas")
        self._ordenes.delete(orden_id)
        self._revertir_pedido_a_mercaderia_recibida(orden)

    def marcar_lista_despacho(self, orden_id: int) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_marcarse_lista():
            raise TransicionDeEstadoInvalida("La orden debe estar en preparación")
        orden.estado = EstadoOrdenEnvio.LISTO
        return self._ordenes.update(orden)

    def despachar(self, orden_id: int, numero_guia: str | None, usuario_id: int) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_despachada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser despachada")

        for item in orden.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", item.producto_id)
            stock_anterior = producto.stock_actual
            stock_nuevo = stock_anterior - item.cantidad
            if stock_nuevo < 0:
                raise StockInsuficiente(producto.nombre, stock_anterior, item.cantidad)

            producto.stock_actual = stock_nuevo
            self._productos.update(producto)

            self._movimientos.add(
                MovimientoInventario(
                    id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.SALIDA,
                    cantidad=item.cantidad, stock_anterior=stock_anterior, stock_nuevo=stock_nuevo,
                    referencia_tipo=TipoReferenciaMovimiento.ORDEN_ENVIO, referencia_id=orden.id,
                    usuario_id=usuario_id, observaciones=f"Despacho orden {orden.numero}",
                )
            )

        orden.estado = EstadoOrdenEnvio.EN_TRANSITO
        orden.fecha_envio = date.today()
        orden.numero_guia = numero_guia
        orden = self._ordenes.update(orden)

        pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
        if pedido is not None:
            pedido.estado = EstadoPedidoCliente.ENVIADO
            self._pedidos.update(pedido)

        return orden

    def entregar(self, orden_id: int, observaciones: str | None) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_entregada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser marcada como entregada")
        orden.estado = EstadoOrdenEnvio.ENTREGADO
        orden.fecha_entrega = date.today()
        orden.observaciones_entrega = observaciones
        orden = self._ordenes.update(orden)

        pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
        if pedido is not None:
            pedido.estado = EstadoPedidoCliente.ENTREGADO
            self._pedidos.update(pedido)
        return orden

    def devolver(self, orden_id: int, observaciones: str, usuario_id: int) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_devuelta():
            raise TransicionDeEstadoInvalida("Solo se pueden devolver órdenes en tránsito")

        for item in orden.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", item.producto_id)
            stock_anterior = producto.stock_actual
            producto.stock_actual = stock_anterior + item.cantidad
            self._productos.update(producto)

            self._movimientos.add(
                MovimientoInventario(
                    id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.ENTRADA,
                    cantidad=item.cantidad, stock_anterior=stock_anterior, stock_nuevo=producto.stock_actual,
                    referencia_tipo=TipoReferenciaMovimiento.ORDEN_ENVIO, referencia_id=orden.id,
                    usuario_id=usuario_id, observaciones=f"Devolución orden {orden.numero}: {observaciones}",
                )
            )

        orden.estado = EstadoOrdenEnvio.DEVUELTO
        orden.observaciones_entrega = observaciones
        return self._ordenes.update(orden)

    def cancelar(self, orden_id: int, observaciones: str) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_cancelada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser cancelada")
        orden.estado = EstadoOrdenEnvio.CANCELADO
        orden.observaciones_entrega = observaciones
        orden = self._ordenes.update(orden)
        self._revertir_pedido_a_mercaderia_recibida(orden)
        return orden

    def _revertir_pedido_a_mercaderia_recibida(self, orden: OrdenEnvio) -> None:
        pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
        if pedido is not None:
            pedido.estado = EstadoPedidoCliente.MERCADERIA_RECIBIDA
            self._pedidos.update(pedido)
