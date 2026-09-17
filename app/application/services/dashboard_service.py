"""Caso de uso de KPIs consolidados (CU-19 Dashboard de gestión)."""
from dataclasses import dataclass, field

from app.domain.entities import OrdenCompra, OrdenEnvio, PedidoCliente, SolicitudPresupuesto
from app.domain.repositories import (
    OrdenCompraRepository,
    OrdenEnvioRepository,
    PedidoClienteRepository,
    ProductoRepository,
    SolicitudPresupuestoRepository,
)


@dataclass
class DashboardStats:
    solicitudes_activas: int = 0
    solicitudes_hoy: int = 0
    cotizaciones_pendientes: int = 0
    cotizaciones_listas: int = 0
    ordenes_compra_activas: int = 0
    ordenes_envio_pendientes: int = 0
    productos_total: int = 0
    productos_stock_bajo: int = 0


@dataclass
class ActividadReciente:
    tipo: str
    titulo: str
    detalle: str
    estado: str
    fecha: object
    url_recurso: str


class DashboardService:
    def __init__(
        self,
        pedidos: PedidoClienteRepository,
        solicitudes: SolicitudPresupuestoRepository,
        ordenes_compra: OrdenCompraRepository,
        ordenes_envio: OrdenEnvioRepository,
        productos: ProductoRepository,
    ):
        self._pedidos = pedidos
        self._solicitudes = solicitudes
        self._ordenes_compra = ordenes_compra
        self._ordenes_envio = ordenes_envio
        self._productos = productos

    def estadisticas(self) -> DashboardStats:
        productos_activos = self._productos.list(solo_activos=True)
        return DashboardStats(
            solicitudes_activas=self._pedidos.contar_activos(),
            solicitudes_hoy=self._pedidos.contar_creados_hoy(),
            cotizaciones_pendientes=self._solicitudes.contar_pendientes(),
            cotizaciones_listas=self._solicitudes.contar_cotizadas(),
            ordenes_compra_activas=self._ordenes_compra.contar_activas(),
            ordenes_envio_pendientes=self._ordenes_envio.contar_pendientes(),
            productos_total=len(productos_activos),
            productos_stock_bajo=sum(1 for p in productos_activos if p.tiene_stock_bajo()),
        )

    def actividad_reciente(self, limite: int = 15) -> list[ActividadReciente]:
        actividades: list[ActividadReciente] = []

        for pedido in self._pedidos.list()[:8]:
            actividades.append(
                ActividadReciente("pedido", pedido.numero, pedido.cliente_nombre, pedido.estado.value, pedido.created_at, f"/pedidos-cliente/{pedido.id}")
            )
        for solicitud in self._solicitudes.list()[:8]:
            actividades.append(
                ActividadReciente("cotizacion", solicitud.numero, f"Proveedor #{solicitud.proveedor_id}", solicitud.estado.value, solicitud.created_at, f"/solicitudes-presupuesto/{solicitud.id}")
            )
        for orden in self._ordenes_compra.list()[:8]:
            actividades.append(
                ActividadReciente("compra", orden.numero, orden.proveedor_nombre, orden.estado.value, orden.created_at, f"/ordenes-compra/{orden.id}")
            )
        for envio in self._ordenes_envio.list()[:8]:
            actividades.append(
                ActividadReciente("envio", envio.numero, envio.direccion_entrega, envio.estado.value, envio.created_at, f"/ordenes-envio/{envio.id}")
            )

        actividades.sort(key=lambda a: a.fecha or 0, reverse=True)
        return actividades[:limite]
