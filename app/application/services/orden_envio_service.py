"""Casos de uso de Órdenes de Envío al cliente (CU-17 generar, CU-18 despachar).

El despacho valida stock antes de descontar (RF14) y cada salida/devolución
deja su movimiento en el Kardex, igual que la recepción de compra.

Dos modalidades (las toma del pedido):
- ENTREGA_DOMICILIO: PREPARANDO → LISTO → (despachar, descuenta stock)
  EN_TRANSITO → ENTREGADO, o DEVUELTO.
- RETIRA_CLIENTE: PREPARANDO → LISTO_RETIRO → (entregar, descuenta stock)
  ENTREGADO. No se despacha.
Al entregar, el pedido registra su cobro (ver CobroPedidoService): a cuenta
se carga a la cuenta corriente; contra entrega queda POR_RENDIR.
"""
from decimal import Decimal

from app.application.validaciones import validar_items
from app.core.tiempo import hoy
from app.domain.formato import formato_cantidad
from app.domain.entities import MovimientoInventario, OrdenEnvio, OrdenEnvioItem
from app.application.services.cobro_pedido_service import CobroPedidoService
from app.domain.enums import (
    EstadoOrdenEnvio,
    EstadoPedidoCliente,
    ModalidadEntrega,
    TipoMovimientoInventario,
    TipoReferenciaMovimiento,
)
from app.domain.exceptions import (
    RecursoNoEncontrado,
    SolicitudInvalida,
    StockInsuficiente,
    StockInsuficienteParaPedido,
    TransicionDeEstadoInvalida,
)
from app.domain.repositories import (
    EmpresaRepository,
    MovimientoInventarioRepository,
    OrdenEnvioRepository,
    PedidoClienteRepository,
    ProductoRepository,
)

CAMPOS_TRASLADO = (
    "transportista", "numero_nota_remision", "transportista_ruc", "vehiculo", "conductor_nombre", "conductor_documento",
)


class OrdenEnvioService:
    def __init__(
        self,
        ordenes: OrdenEnvioRepository,
        productos: ProductoRepository,
        movimientos: MovimientoInventarioRepository,
        pedidos: PedidoClienteRepository,
        cobros: CobroPedidoService,
        empresa: EmpresaRepository | None = None,
    ):
        self._ordenes = ordenes
        self._productos = productos
        self._movimientos = movimientos
        self._pedidos = pedidos
        self._cobros = cobros
        self._empresa = empresa

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
        direccion_entrega: str | None,
        items: list[dict],
        contacto_entrega: str | None = None,
        telefono_entrega: str | None = None,
        metodo_envio: str | None = None,
        transportista: str | None = None,
        notas: str | None = None,
        **traslado: str | None,
    ) -> OrdenEnvio:
        pedido = self._pedidos.get_by_id(pedido_cliente_id)
        if pedido is None:
            raise RecursoNoEncontrado("PedidoCliente", pedido_cliente_id)
        if not pedido.puede_generar_orden_envio():
            raise TransicionDeEstadoInvalida("Este pedido no puede generar orden de envío")
        validar_items(self._productos, items)
        if pedido.estado != EstadoPedidoCliente.MERCADERIA_RECIBIDA:
            self._validar_stock_para(pedido)
        direccion_entrega = (direccion_entrega or "").strip()
        if pedido.modalidad_entrega == ModalidadEntrega.RETIRA_CLIENTE:
            direccion_entrega = direccion_entrega or "Retira en el local"
        elif not direccion_entrega:
            raise SolicitudInvalida("Indicá la dirección de entrega")

        orden = OrdenEnvio(
            id=None,
            numero=self._ordenes.siguiente_numero(),
            usuario_id=usuario_id,
            pedido_cliente_id=pedido_cliente_id,
            direccion_entrega=direccion_entrega,
            contacto_entrega=contacto_entrega,
            telefono_entrega=telefono_entrega,
            fecha_generacion=hoy(),
            metodo_envio=metodo_envio,
            transportista=transportista,
            notas=notas,
            estado=EstadoOrdenEnvio.PREPARANDO,
            modalidad=pedido.modalidad_entrega,
            **self._datos_traslado(traslado, campos=CAMPOS_TRASLADO[1:]),
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
        # Una orden cancelada ya liberó su pedido al cancelarse: borrarla no
        # tiene que tocar el pedido (que puede haber seguido con otro envío).
        if orden.estado == EstadoOrdenEnvio.PREPARANDO:
            self._liberar_pedido(orden, desde=EstadoPedidoCliente.LISTO_ENVIO)

    def marcar_lista_despacho(self, orden_id: int) -> OrdenEnvio:
        """Preparado: listo para despachar (domicilio) o para que lo retire el cliente."""
        orden = self.obtener(orden_id)
        if not orden.puede_marcarse_lista():
            raise TransicionDeEstadoInvalida("La orden debe estar en preparación")
        if orden.es_retiro():
            orden.estado = EstadoOrdenEnvio.LISTO_RETIRO
            pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
            if pedido is not None and pedido.estado == EstadoPedidoCliente.LISTO_ENVIO:
                pedido.estado = EstadoPedidoCliente.LISTO_RETIRO
                self._pedidos.update(pedido)
        else:
            orden.estado = EstadoOrdenEnvio.LISTO
        return self._ordenes.update(orden)

    def actualizar_traslado(self, orden_id: int, **datos: str | None) -> OrdenEnvio:
        """Transportista, vehículo, conductor y N° de nota de remisión. Solo
        cambia los campos que se mandan."""
        orden = self.obtener(orden_id)
        if orden.estado == EstadoOrdenEnvio.CANCELADO:
            raise TransicionDeEstadoInvalida("El envío está cancelado")
        for campo, valor in self._datos_traslado(datos, solo_presentes=True).items():
            setattr(orden, campo, valor)
        return self._ordenes.update(orden)

    def hoja(self, orden_id: int) -> dict:
        """Datos para la hoja interna de entrega/remisión (la arma el frontend)."""
        orden = self.obtener(orden_id)
        pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
        productos = {i.producto_id: self._productos.get_by_id(i.producto_id) for i in orden.items}
        return {
            "empresa": self._empresa.get() if self._empresa else None,
            "orden": orden,
            "pedido": pedido,
            "productos": productos,
        }

    def despachar(self, orden_id: int, numero_guia: str | None, usuario_id: int, **traslado: str | None) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if orden.es_retiro() and orden.estado in (EstadoOrdenEnvio.LISTO_RETIRO, EstadoOrdenEnvio.PREPARANDO):
            raise TransicionDeEstadoInvalida(
                "Este pedido lo retira el cliente en el local: no se despacha, registrá la entrega cuando lo retire"
            )
        if not orden.puede_ser_despachada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser despachada")
        self._productos.bloquear(item.producto_id for item in orden.items)
        pedido = self._pedidos.bloquear(orden.pedido_cliente_id)
        if pedido is not None:
            self._cobros.validar_salida(pedido)
        self._descontar_stock(orden, usuario_id, f"Despacho orden {orden.numero}")

        orden.estado = EstadoOrdenEnvio.EN_TRANSITO
        orden.fecha_envio = hoy()
        orden.numero_guia = numero_guia
        for campo, valor in self._datos_traslado(traslado, solo_presentes=True).items():
            setattr(orden, campo, valor)
        orden = self._ordenes.update(orden)

        if pedido is not None:
            pedido.estado = EstadoPedidoCliente.ENVIADO
            self._pedidos.update(pedido)

        return orden

    def _descontar_stock(self, orden: OrdenEnvio, usuario_id: int | None, observaciones: str) -> None:
        for item in orden.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", item.producto_id)
            stock_anterior = producto.stock_actual
            stock_nuevo = stock_anterior - item.cantidad
            if stock_nuevo < 0:
                raise StockInsuficiente(producto.nombre, stock_anterior, item.cantidad, producto.unidad_medida)

            producto.stock_actual = stock_nuevo
            self._productos.update(producto)

            self._movimientos.add(
                MovimientoInventario(
                    id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.SALIDA,
                    cantidad=item.cantidad, stock_anterior=stock_anterior, stock_nuevo=stock_nuevo,
                    referencia_tipo=TipoReferenciaMovimiento.ORDEN_ENVIO, referencia_id=orden.id,
                    usuario_id=usuario_id, observaciones=observaciones,
                )
            )

    def entregar(self, orden_id: int, observaciones: str | None, usuario_id: int | None = None) -> OrdenEnvio:
        """Entregado al cliente. En un retiro en el local, recién acá sale el
        stock. El pedido registra su cobro: a cuenta se carga a la cuenta
        corriente; contra entrega queda POR_RENDIR (la caja no se mueve)."""
        orden = self.obtener(orden_id)
        if not orden.puede_ser_entregada():
            if orden.es_retiro() and orden.estado == EstadoOrdenEnvio.PREPARANDO:
                raise TransicionDeEstadoInvalida("Marcá el pedido como listo para retirar antes de entregarlo")
            raise TransicionDeEstadoInvalida("Esta orden no puede ser marcada como entregada")
        if orden.es_retiro():
            self._productos.bloquear(item.producto_id for item in orden.items)
        pedido = self._pedidos.bloquear(orden.pedido_cliente_id)
        if pedido is not None:
            self._cobros.validar_salida(pedido)
        if orden.es_retiro():
            self._descontar_stock(orden, usuario_id, f"Retiro en el local, orden {orden.numero}")
            orden.fecha_envio = hoy()
        orden.estado = EstadoOrdenEnvio.ENTREGADO
        orden.fecha_entrega = hoy()
        orden.observaciones_entrega = observaciones
        orden = self._ordenes.update(orden)

        if pedido is not None:
            self._cobros.registrar_entrega(pedido, orden, usuario_id)
        return orden

    def devolver(self, orden_id: int, observaciones: str, usuario_id: int) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if not orden.puede_ser_devuelta():
            raise TransicionDeEstadoInvalida("Solo se pueden devolver órdenes en tránsito")
        self._productos.bloquear(item.producto_id for item in orden.items)

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
        orden = self._ordenes.update(orden)
        # La mercadería volvió al depósito: el pedido se puede reenviar o cancelar.
        self._liberar_pedido(orden, desde=EstadoPedidoCliente.ENVIADO)
        return orden

    def cancelar(self, orden_id: int, observaciones: str) -> OrdenEnvio:
        orden = self.obtener(orden_id)
        if orden.estado == EstadoOrdenEnvio.EN_TRANSITO:
            raise TransicionDeEstadoInvalida(
                "El envío ya salió del depósito y descontó stock: si vuelve, registrá la devolución"
            )
        if not orden.puede_ser_cancelada():
            raise TransicionDeEstadoInvalida("Esta orden no puede ser cancelada")
        orden.estado = EstadoOrdenEnvio.CANCELADO
        orden.observaciones_entrega = observaciones
        orden = self._ordenes.update(orden)
        self._liberar_pedido(orden, desde=(EstadoPedidoCliente.LISTO_ENVIO, EstadoPedidoCliente.LISTO_RETIRO))
        return orden

    def _validar_stock_para(self, pedido) -> None:
        """Envío directo desde el depósito (sin pasar por compras): tiene que
        alcanzar el stock de todos los productos del pedido."""
        faltantes = []
        for producto_id, requerida in pedido.cantidades_por_producto().items():
            producto = self._productos.get_by_id(producto_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", producto_id)
            if producto.stock_actual < requerida:
                faltantes.append(
                    f"{producto.nombre} (hay {formato_cantidad(producto.stock_actual)} {producto.unidad_medida}, "
                    f"pide {formato_cantidad(requerida)} {producto.unidad_medida})"
                )
        if faltantes:
            raise StockInsuficienteParaPedido(faltantes)

    @staticmethod
    def _datos_traslado(datos: dict, solo_presentes: bool = False, campos: tuple = CAMPOS_TRASLADO) -> dict:
        """Limpia los datos del traslado (texto vacío = sin dato). Con
        `solo_presentes`, devuelve solo los campos que vinieron."""
        desconocidos = set(datos) - set(campos)
        if desconocidos:
            raise SolicitudInvalida(f"Campos desconocidos: {', '.join(sorted(desconocidos))}")
        return {c: (datos.get(c) or "").strip() or None for c in campos if not solo_presentes or c in datos}

    def _liberar_pedido(self, orden: OrdenEnvio, desde: EstadoPedidoCliente | tuple) -> None:
        """Vuelve el pedido a MERCADERIA_RECIBIDA (mercadería disponible para
        enviar) solo si sigue en el estado en que lo dejó este envío: así no
        se retrocede un pedido que ya avanzó con otro envío."""
        estados = desde if isinstance(desde, tuple) else (desde,)
        pedido = self._pedidos.get_by_id(orden.pedido_cliente_id)
        if pedido is not None and pedido.estado in estados:
            pedido.estado = EstadoPedidoCliente.MERCADERIA_RECIBIDA
            self._pedidos.update(pedido)
