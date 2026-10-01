"""Endpoints de Inventario y Kardex (CU-16)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.inventario_service import InventarioService
from app.interfaces.api.deps import CurrentUser, get_inventario_service
from app.interfaces.api.schemas.catalogo import ProductoResponse
from app.interfaces.api.schemas.inventario import AjusteStockInput, MovimientoInventarioResponse

router = APIRouter(prefix="/inventario", tags=["Inventario"])

InventarioSvc = Annotated[InventarioService, Depends(get_inventario_service)]


@router.get("/stock", response_model=list[ProductoResponse])
def listar_stock(servicio: InventarioSvc, solo_bajo_stock: bool = False) -> list[ProductoResponse]:
    return [ProductoResponse.desde_entidad(p) for p in servicio.listar_stock(solo_bajo_stock)]


@router.get("/movimientos", response_model=list[MovimientoInventarioResponse])
def listar_movimientos(
    servicio: InventarioSvc, producto_id: int | None = None, tipo: str | None = None, limit: int = 100
) -> list[MovimientoInventarioResponse]:
    return [MovimientoInventarioResponse.desde_entidad(m) for m in servicio.movimientos_recientes(producto_id, tipo, limit)]


@router.get("/kardex/{producto_id}", response_model=list[MovimientoInventarioResponse])
def kardex_producto(producto_id: int, servicio: InventarioSvc) -> list[MovimientoInventarioResponse]:
    return [MovimientoInventarioResponse.desde_entidad(m) for m in servicio.kardex(producto_id)]


@router.post(
    "/ajustes", response_model=MovimientoInventarioResponse, status_code=201,
    summary="Ajuste manual: fija el stock contado (inventario inicial, conteo físico, roturas)",
)
def ajustar_stock(datos: AjusteStockInput, servicio: InventarioSvc, usuario: CurrentUser) -> MovimientoInventarioResponse:
    movimiento = servicio.ajustar_stock(datos.producto_id, datos.stock_nuevo, datos.motivo, usuario.id)
    return MovimientoInventarioResponse.desde_entidad(movimiento)
