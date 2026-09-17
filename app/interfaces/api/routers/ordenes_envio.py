"""Endpoints de Órdenes de Envío al cliente (CU-17, CU-18)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.orden_envio_service import OrdenEnvioService
from app.interfaces.api.deps import RequireAnkorUser, get_orden_envio_service
from app.interfaces.api.schemas.common import Mensaje, ObservacionesRequeridas
from app.interfaces.api.schemas.flujo import DespacharInput, OrdenEnvioCreate, OrdenEnvioResponse

router = APIRouter(prefix="/ordenes-envio", tags=["Órdenes de Envío"])

OrdenSvc = Annotated[OrdenEnvioService, Depends(get_orden_envio_service)]


@router.get("", response_model=list[OrdenEnvioResponse])
def listar_ordenes(servicio: OrdenSvc, estado: str | None = None, buscar: str | None = None) -> list[OrdenEnvioResponse]:
    return [OrdenEnvioResponse.desde_entidad(o) for o in servicio.listar(estado, buscar)]


@router.get("/{orden_id}", response_model=OrdenEnvioResponse)
def obtener_orden(orden_id: int, servicio: OrdenSvc) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.obtener(orden_id))


@router.post("", response_model=OrdenEnvioResponse, status_code=201)
def crear_orden(datos: OrdenEnvioCreate, servicio: OrdenSvc, usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    orden = servicio.crear(usuario_id=usuario.id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return OrdenEnvioResponse.desde_entidad(orden)


@router.delete("/{orden_id}", response_model=Mensaje)
def eliminar_orden(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(orden_id)
    return Mensaje(mensaje="Orden eliminada exitosamente")


@router.post("/{orden_id}/lista-despachar", response_model=OrdenEnvioResponse)
def marcar_lista_despacho(orden_id: int, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.marcar_lista_despacho(orden_id))


@router.post("/{orden_id}/despachar", response_model=OrdenEnvioResponse, summary="CU-18: despachar (descuenta stock, valida disponibilidad)")
def despachar_orden(orden_id: int, datos: DespacharInput, servicio: OrdenSvc, usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.despachar(orden_id, datos.numero_guia, usuario.id))


@router.post("/{orden_id}/entregar", response_model=OrdenEnvioResponse)
def entregar_orden(orden_id: int, datos: ObservacionesRequeridas | None, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    observaciones = datos.observaciones if datos else None
    return OrdenEnvioResponse.desde_entidad(servicio.entregar(orden_id, observaciones))


@router.post("/{orden_id}/devolver", response_model=OrdenEnvioResponse)
def devolver_orden(orden_id: int, datos: ObservacionesRequeridas, servicio: OrdenSvc, usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.devolver(orden_id, datos.observaciones, usuario.id))


@router.post("/{orden_id}/cancelar", response_model=OrdenEnvioResponse)
def cancelar_orden(orden_id: int, datos: ObservacionesRequeridas, servicio: OrdenSvc, _usuario: RequireAnkorUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.cancelar(orden_id, datos.observaciones))
