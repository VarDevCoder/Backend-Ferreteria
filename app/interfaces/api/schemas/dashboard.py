from datetime import datetime

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    solicitudes_activas: int
    solicitudes_hoy: int
    cotizaciones_pendientes: int
    cotizaciones_listas: int
    ordenes_compra_activas: int
    ordenes_envio_pendientes: int
    productos_total: int
    productos_stock_bajo: int


class ActividadRecienteResponse(BaseModel):
    tipo: str
    titulo: str
    detalle: str
    estado: str
    fecha: datetime | None
    url_recurso: str


class DashboardResponse(BaseModel):
    stats: DashboardStatsResponse
    actividad_reciente: list[ActividadRecienteResponse]
