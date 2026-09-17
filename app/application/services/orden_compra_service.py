"""Casos de uso de Órdenes de Compra a proveedor (CU-14: gestionar OC hasta
recepción). La recepción de mercadería es la operación más delicada: mueve
stock, dispara movimientos de inventario y cascada el estado del pedido."""
from datetime import date
from decimal import Decimal

from app.domain.entities import MovimientoInventario, OrdenCompra, OrdenCompraItem
from app.domain.enums import EstadoOrdenCompra, EstadoPedidoCliente, TipoMovimientoInventario, TipoReferenciaMovimiento
from app.domain.exceptions import RecursoNoEncontrado, TransicionDeEstadoInvalida
from app.domain.repositories import (
    MovimientoInventarioRepository,
    OrdenCompraRepository,
    PedidoClienteRepository,
    ProductoRepository,
)


class OrdenCompraService:
    def __init__(
        self,
        ordenes: OrdenCompraRepository,
        productos: ProductoRepository,
        movimientos: MovimientoInventarioRepository,
        pedidos: PedidoClienteRepository,
    ):
        self._ordenes = ordenes
        self._productos = productos
        self._movimientos = movimientos
        self._pedidos = pedidos

    def listar(self, estado: str | None = None, busqueda: str | None = None) -> list[OrdenCompra]:
        return self._ordenes.list(estado=estado, busqueda=busqueda)

    def obtener(self, orden_id: int) -> OrdenCompra:
        orden = self._ordenes.get_by_id(orden_id)
        if orden is None:
            raise RecursoNoEncontrado("OrdenCompra", orden_id)
        return orden

    def crear(
        self,
        usuario_id: int,
        proveedor_nombre: str,
        items: list[dict],
        pedido_cliente_id: int | None = None,
        proveedor_ruc: str | None = None,
        proveedor_telefono: str | None = None,
        proveedor_email: str | None = None,
        proveedor_direccion: str | None = None,
        fecha_entrega_esperada: date | None = None,
        descuento: int = 0,
        notas: str | None = None,
    ) -> OrdenCompra:
        orden = OrdenCompra(
            id=None,
            numero=self._ordenes.siguiente_numero(),
            usuario_id=usuario_id,
            pedido_cliente_id=pedido_cliente_id,
            proveedor_nombre=proveedor_nombre,
            proveedor_ruc=proveedor_ruc,
            proveedor_telefono=proveedor_telefono,
            proveedor_email=proveedor_email,
            proveedor_direccion=proveedor_direccion,
            fecha_orden=date.today(),
            fecha_entrega_esperada=fecha_entrega_esperada,
            estado=EstadoOrdenCompra.BORRADOR,
            descuento=descuento,
            notas=notas,
            items=[
                OrdenCompraItem(
                    id=None, orden_compra_id=None, producto_id=i["producto_id"],
                    cantidad_solicitada=Decimal(str(i["cantidad_solicitada"])),
                    precio_unitario=int(i["precio_unitario"]),
                )
                for i in items
            ],
        )
        orden.calcular_totales()
        orden = self._ordenes.add(orden)

        if pedido_cliente_id is not None:
            pedido = self._pedidos.get_by_id(pedido_cliente_id)
            if pedido is not None and pedido.puede_generar_orden_compra():
                pedido.estado = EstadoPedidoCliente.ORDEN_COMPRA
                self._pedidos.update(pedido)

        return orden

    def actualizar(
        self, orden_id: int, items: list[dict], proveedor_nombre: str, proveedor_ruc: str | None,
        proveedor_telefono: str | None, proveedor_email: str | None, proveedor_direccion: str | None,
        fecha_entrega_esperada: date | None, descuento: int, notas: str | None,
    ) -> OrdenCompra:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_editada():
            raise TransicionDeEstadoInvalida("Solo se pueden modificar órdenes en borrador")

        orden.proveedor_nombre = proveedor_nombre
        orden.proveedor_ruc = proveedor_ruc
        orden.proveedor_telefono = proveedor_telefono
        orden.proveedor_email = proveedor_email
        orden.proveedor_direccion = proveedor_direccion
        orden.fecha_entrega_esperada = fecha_entrega_esperada
        orden.descuento = descuento
        orden.notas = notas
        orden.items = [
            OrdenCompraItem(
                id=None, orden_compra_id=orden_id, producto_id=i["producto_id"],
                cantidad_solicitada=Decimal(str(i["cantidad_solicitada"])), precio_unitario=int(i["precio_unitario"]),
            )
            for i in items
        ]
        orden.calcular_totales()

        self._ordenes.replace_items(orden_id, orden.items)
        return self._ordenes.update(orden)

    def eliminar(self, orden_id: int) -> None:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_eliminada():
            raise TransicionDeEstadoInvalida("Solo se pueden eliminar órdenes en borrador o canceladas")
        self._ordenes.delete(orden_id)

    def enviar(self, orden_id: int) -> OrdenCompra:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_enviada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser enviada")
        orden.estado = EstadoOrdenCompra.ENVIADA
        return self._ordenes.update(orden)

    def confirmar(self, orden_id: int) -> OrdenCompra:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_confirmada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser confirmada")
        orden.estado = EstadoOrdenCompra.CONFIRMADA
        return self._ordenes.update(orden)

    def marcar_en_transito(self, orden_id: int) -> OrdenCompra:
        orden = self.obtener(orden_id)
        if not orden.puede_marcarse_en_transito():
            raise TransicionDeEstadoInvalida("La orden debe estar confirmada")
        orden.estado = EstadoOrdenCompra.EN_TRANSITO
        return self._ordenes.update(orden)

    def recibir_mercaderia(self, orden_id: int, usuario_id: int, cantidades_por_item: dict[int, Decimal]) -> OrdenCompra:
        """CU-15: incrementa stock por cada item recibido y deja rastro en el
        Kardex (`movimientos_inventario`). Si se completó todo lo solicitado,
        la orden pasa a RECIBIDA_COMPLETA y arrastra al pedido a MERCADERIA_RECIBIDA."""
        orden = self.obtener(orden_id)
        if not orden.puede_recibir_mercaderia():
            raise TransicionDeEstadoInvalida("No se puede recibir mercadería para esta orden")

        items_por_id = {item.id: item for item in orden.items}
        for item_id, cantidad_recibida in cantidades_por_item.items():
            item = items_por_id.get(item_id)
            if item is None or cantidad_recibida <= 0:
                continue

            item.cantidad_recibida += cantidad_recibida

            producto = self._productos.get_by_id(item.producto_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", item.producto_id)
            stock_anterior = producto.stock_actual
            producto.stock_actual = stock_anterior + cantidad_recibida
            self._productos.update(producto)

            self._movimientos.add(
                MovimientoInventario(
                    id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.ENTRADA,
                    cantidad=cantidad_recibida, stock_anterior=stock_anterior, stock_nuevo=producto.stock_actual,
                    referencia_tipo=TipoReferenciaMovimiento.ORDEN_COMPRA, referencia_id=orden.id,
                    usuario_id=usuario_id, observaciones=f"Recepción de OC {orden.numero}",
                )
            )

        orden = self._ordenes.update(orden)  # persiste cantidad_recibida de cada item

        if orden.verificar_recepcion_completa():
            orden.estado = EstadoOrdenCompra.RECIBIDA_COMPLETA
            orden.fecha_recepcion = date.today()
            if orden.pedido_cliente_id is not None:
                pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
                if pedido is not None:
                    pedido.estado = EstadoPedidoCliente.MERCADERIA_RECIBIDA
                    self._pedidos.update(pedido)
        else:
            orden.estado = EstadoOrdenCompra.RECIBIDA_PARCIAL

        return self._ordenes.update(orden)

    def cancelar(self, orden_id: int, motivo: str) -> OrdenCompra:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_cancelada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser cancelada")
        orden.estado = EstadoOrdenCompra.CANCELADA
        orden.motivo_cancelacion = motivo
        return self._ordenes.update(orden)
