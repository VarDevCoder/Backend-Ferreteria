"""Casos de uso de Pedidos de Cliente — el punto de entrada del ciclo comercial
(CU-10 Registrar pedido, CU-11 parte "solicitar cotización a todos")."""
from datetime import date
from decimal import Decimal

from app.domain.entities import PedidoCliente, PedidoClienteItem, SolicitudPresupuesto, SolicitudPresupuestoItem
from app.domain.enums import EstadoPedidoCliente, EstadoSolicitudPresupuesto
from app.domain.exceptions import RecursoNoEncontrado, TransicionDeEstadoInvalida
from app.domain.repositories import (
    ClienteRepository,
    PedidoClienteRepository,
    ProveedorRepository,
    SolicitudPresupuestoRepository,
)


class PedidoClienteService:
    def __init__(
        self,
        pedidos: PedidoClienteRepository,
        clientes: ClienteRepository,
        proveedores: ProveedorRepository,
        solicitudes: SolicitudPresupuestoRepository,
    ):
        self._pedidos = pedidos
        self._clientes = clientes
        self._proveedores = proveedores
        self._solicitudes = solicitudes

    def listar(self, estado: str | None = None, busqueda: str | None = None) -> list[PedidoCliente]:
        return self._pedidos.list(estado=estado, busqueda=busqueda)

    def obtener(self, pedido_id: int) -> PedidoCliente:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise RecursoNoEncontrado("PedidoCliente", pedido_id)
        return pedido

    def crear(
        self,
        usuario_id: int,
        items: list[dict],
        cliente_id: int | None = None,
        cliente_nombre: str | None = None,
        cliente_ruc: str | None = None,
        cliente_telefono: str | None = None,
        cliente_email: str | None = None,
        cliente_direccion: str | None = None,
        fecha_pedido: date | None = None,
        fecha_entrega_solicitada: date | None = None,
        descuento: int = 0,
        notas: str | None = None,
    ) -> PedidoCliente:
        # Si se eligió un cliente del catálogo, tomamos su snapshot actual (igual que Laravel)
        if cliente_id is not None:
            cliente = self._clientes.get_by_id(cliente_id)
            if cliente is not None:
                cliente_nombre = cliente.nombre
                cliente_ruc = cliente.ruc
                cliente_telefono = cliente.telefono
                cliente_email = cliente.email
                cliente_direccion = cliente.direccion

        pedido = PedidoCliente(
            id=None,
            numero=self._pedidos.siguiente_numero(),
            usuario_id=usuario_id,
            cliente_id=cliente_id,
            cliente_nombre=cliente_nombre or "",
            cliente_ruc=cliente_ruc,
            cliente_telefono=cliente_telefono,
            cliente_email=cliente_email,
            cliente_direccion=cliente_direccion,
            fecha_pedido=fecha_pedido or date.today(),
            fecha_entrega_solicitada=fecha_entrega_solicitada,
            estado=EstadoPedidoCliente.RECIBIDO,
            descuento=descuento,
            notas=notas,
            items=[
                PedidoClienteItem(
                    id=None, pedido_cliente_id=None, producto_id=i["producto_id"],
                    cantidad=Decimal(str(i["cantidad"])), precio_unitario=int(i["precio_unitario"]),
                )
                for i in items
            ],
        )
        pedido.calcular_totales()
        return self._pedidos.add(pedido)

    def actualizar(
        self,
        pedido_id: int,
        items: list[dict],
        cliente_id: int | None,
        cliente_nombre: str,
        cliente_ruc: str | None,
        cliente_telefono: str | None,
        cliente_email: str | None,
        cliente_direccion: str | None,
        fecha_entrega_solicitada: date | None,
        descuento: int,
        notas: str | None,
    ) -> PedidoCliente:
        pedido = self.obtener(pedido_id)
        if not pedido.puede_ser_editado():
            raise TransicionDeEstadoInvalida("Esta solicitud no puede ser modificada")

        pedido.cliente_id = cliente_id
        pedido.cliente_nombre = cliente_nombre
        pedido.cliente_ruc = cliente_ruc
        pedido.cliente_telefono = cliente_telefono
        pedido.cliente_email = cliente_email
        pedido.cliente_direccion = cliente_direccion
        pedido.fecha_entrega_solicitada = fecha_entrega_solicitada
        pedido.descuento = descuento
        pedido.notas = notas
        pedido.items = [
            PedidoClienteItem(
                id=None, pedido_cliente_id=pedido_id, producto_id=i["producto_id"],
                cantidad=Decimal(str(i["cantidad"])), precio_unitario=int(i["precio_unitario"]),
            )
            for i in items
        ]
        pedido.calcular_totales()

        self._pedidos.replace_items(pedido_id, pedido.items)
        return self._pedidos.update(pedido)

    def eliminar(self, pedido_id: int) -> None:
        pedido = self.obtener(pedido_id)
        if not pedido.puede_ser_cancelado():
            raise TransicionDeEstadoInvalida("Esta solicitud no puede ser eliminada")
        self._pedidos.delete(pedido_id)

    def procesar(self, pedido_id: int) -> PedidoCliente:
        pedido = self.obtener(pedido_id)
        if pedido.estado != EstadoPedidoCliente.RECIBIDO:
            raise TransicionDeEstadoInvalida("Solo se pueden procesar solicitudes recién recibidas")
        pedido.estado = EstadoPedidoCliente.EN_PROCESO
        return self._pedidos.update(pedido)

    def cancelar(self, pedido_id: int, motivo: str) -> PedidoCliente:
        pedido = self.obtener(pedido_id)
        if not pedido.puede_ser_cancelado():
            raise TransicionDeEstadoInvalida("Esta solicitud no puede ser cancelada")
        pedido.estado = EstadoPedidoCliente.CANCELADO
        pedido.motivo_cancelacion = motivo
        return self._pedidos.update(pedido)

    def marcar_mercaderia_recibida(self, pedido_id: int) -> PedidoCliente:
        pedido = self.obtener(pedido_id)
        if pedido.estado != EstadoPedidoCliente.ORDEN_COMPRA:
            raise TransicionDeEstadoInvalida("La solicitud debe tener orden de compra activa")
        pedido.estado = EstadoPedidoCliente.MERCADERIA_RECIBIDA
        return self._pedidos.update(pedido)

    def solicitar_cotizacion_todos(self, pedido_id: int, usuario_id: int) -> tuple[PedidoCliente, int]:
        """CU-11 modo masivo: genera una SolicitudPresupuesto por cada proveedor activo
        que todavía no tenga una solicitud vigente para este pedido."""
        pedido = self.obtener(pedido_id)
        if not pedido.puede_solicitar_cotizacion():
            raise TransicionDeEstadoInvalida("La solicitud no está en un estado válido para cotizar")

        proveedores_activos = self._proveedores.list(solo_activos=True)
        if not proveedores_activos:
            raise TransicionDeEstadoInvalida("No hay proveedores activos en el sistema")

        creadas = 0
        for proveedor in proveedores_activos:
            if self._solicitudes.existe_activa(pedido_id, proveedor.id):
                continue

            solicitud = SolicitudPresupuesto(
                id=None,
                numero=self._solicitudes.siguiente_numero(),
                proveedor_id=proveedor.id,
                usuario_id=usuario_id,
                pedido_cliente_id=pedido_id,
                fecha_solicitud=date.today(),
                estado=EstadoSolicitudPresupuesto.ENVIADA,
                mensaje_solicitud=f"Solicitud de cotización generada automáticamente desde {pedido.numero}.",
                items=[
                    SolicitudPresupuestoItem(
                        id=None, solicitud_presupuesto_id=None, producto_id=item.producto_id,
                        cantidad_solicitada=item.cantidad,
                    )
                    for item in pedido.items
                ],
            )
            self._solicitudes.add(solicitud)
            creadas += 1

        if creadas == 0:
            raise TransicionDeEstadoInvalida("Ya existen cotizaciones activas para todos los proveedores")

        if pedido.estado == EstadoPedidoCliente.RECIBIDO:
            pedido.estado = EstadoPedidoCliente.EN_PROCESO
            pedido = self._pedidos.update(pedido)

        return pedido, creadas
