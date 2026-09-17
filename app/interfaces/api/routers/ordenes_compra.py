"""Endpoints de Órdenes de Compra a proveedor (CU-14)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.orden_compra_service import OrdenCompraService
from app.interfaces.api.deps import RequireAnkorUser, get_orden_compra_service
from app.interfaces.api.schemas.common import Mensaje, MotivoRequerido
from app.interfaces.api.schemas.flujo import OrdenCompraCreate, OrdenCompraResponse, OrdenCompraUpdate, RecepcionMercaderiaInput

router = APIRouter(prefix="/ordenes-compra", tags=["Órdenes de Compra"])

OrdenSvc = Annotated[OrdenCompraService, Depends(get_orden_compra_service)]


@router.get("", response_model=list[OrdenCompraResponse])
def listar_ordenes(servicio: OrdenSvc, estado: str | None = None, buscar: str | None = None) -> list[OrdenCompraResponse]:
    return [OrdenCompraResponse.desde_entidad(o) for o in servicio.listar(estado, buscar)]


@router.get("/{orden_id}", response_model=OrdenCompraResponse)
def obtener_orden(orden_id: int, servicio: OrdenSvc) -> OrdenCompraResponse:
    return OrdenCompraResponse.desde_entidad(servicio.obtener(orden_id))


@router.post("", response_model=OrdenCompraResponse, status_code=201)
def crear_orden(datos: OrdenCompraCreate, servicio: OrdenSvc, usuario: RequireAnkorUser) -> OrdenCompraResponse:
    orden = servicio.crear(usuario_id=usuario.id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return OrdenCompraResponse.desde_entidad(orden)


@router.put("/{orden_id}", response_model=OrdenCompraResponse)
def actualizar_orden(orden_id: int, datos: OrdenCompraUpdate, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenCompraResponse:
    orden = servicio.actualizar(orden_id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return OrdenCompraResponse.desde_entidad(orden)


@router.delete("/{orden_id}", response_model=Mensaje)
def eliminar_orden(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(orden_id)
    return Mensaje(mensaje="Orden eliminada exitosamente")


@router.post("/{orden_id}/enviar", response_model=OrdenCompraResponse)
def enviar_orden(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenCompraResponse:
    return OrdenCompraResponse.desde_entidad(servicio.enviar(orden_id))


@router.post("/{orden_id}/confirmar", response_model=OrdenCompraResponse)
def confirmar_orden(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenCompraResponse:
    return OrdenCompraResponse.desde_entidad(servicio.confirmar(orden_id))


@router.post("/{orden_id}/en-transito", response_model=OrdenCompraResponse)
def marcar_en_transito(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenCompraResponse:
    return OrdenCompraResponse.desde_entidad(servicio.marcar_en_transito(orden_id))


@router.post("/{orden_id}/recibir", response_model=OrdenCompraResponse, summary="CU-15: registrar recepción de mercadería (mueve stock)")
def recibir_mercaderia(orden_id: int, datos: RecepcionMercaderiaInput, servicio: OrdenSvc, usuario: RequireAnkorUser) -> OrdenCompraResponse:
    cantidades = {int(item_id): cantidad for item_id, cantidad in datos.cantidades.items()}
    orden = servicio.recibir_mercaderia(orden_id, usuario.id, cantidades)
    return OrdenCompraResponse.desde_entidad(orden)


@router.post("/{orden_id}/cancelar", response_model=OrdenCompraResponse)
def cancelar_orden(orden_id: int, datos: MotivoRequerido, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenCompraResponse:
    return OrdenCompraResponse.desde_entidad(servicio.cancelar(orden_id, datos.motivo))
