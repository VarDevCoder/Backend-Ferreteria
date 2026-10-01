"""Reportes de gestión (admin y encargado)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.services.reporte_service import ReporteService
from app.interfaces.api.deps import get_reporte_service
from app.interfaces.api.schemas.reportes import ReporteVentasResponse

router = APIRouter(prefix="/reportes", tags=["Reportes"])

ReporteSvc = Annotated[ReporteService, Depends(get_reporte_service)]


@router.get("/ventas", response_model=ReporteVentasResponse, summary="Ventas del período (por defecto, el mes en curso)")
def reporte_ventas(
    servicio: ReporteSvc,
    desde: date | None = None,
    hasta: date | None = None,
    limite_productos: Annotated[int, Query(ge=1, le=100)] = 10,
) -> ReporteVentasResponse:
    return ReporteVentasResponse(**servicio.ventas(desde, hasta, limite_productos))
