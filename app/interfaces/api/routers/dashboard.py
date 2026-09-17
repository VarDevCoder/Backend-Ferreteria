"""Endpoint de KPIs consolidados (CU-19)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.dashboard_service import DashboardService
from app.interfaces.api.deps import get_dashboard_service
from app.interfaces.api.schemas.dashboard import ActividadRecienteResponse, DashboardResponse, DashboardStatsResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def obtener_dashboard(servicio: Annotated[DashboardService, Depends(get_dashboard_service)]) -> DashboardResponse:
    stats = servicio.estadisticas()
    actividades = servicio.actividad_reciente()
    return DashboardResponse(
        stats=DashboardStatsResponse(**vars(stats)),
        actividad_reciente=[
            ActividadRecienteResponse(
                tipo=a.tipo, titulo=a.titulo, detalle=a.detalle, estado=a.estado, fecha=a.fecha, url_recurso=a.url_recurso
            )
            for a in actividades
        ],
    )
