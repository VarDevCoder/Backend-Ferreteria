"""Endpoints de Órdenes de Envío al cliente (CU-17, CU-18)."""
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.application.services.orden_envio_service import OrdenEnvioService
from app.interfaces.api.deps import RequireSailUser, get_orden_envio_service
from app.interfaces.api.schemas.common import Mensaje, ObservacionesOpcionales, ObservacionesRequeridas
from app.interfaces.api.schemas.flujo import DespacharInput, OrdenEnvioCreate, OrdenEnvioResponse, TrasladoInput
from app.interfaces.api.schemas.logistica import HojaEnvioResponse

router = APIRouter(prefix="/ordenes-envio", tags=["Órdenes de Envío"])

OrdenSvc = Annotated[OrdenEnvioService, Depends(get_orden_envio_service)]


@router.get("", response_model=list[OrdenEnvioResponse])
def listar_ordenes(servicio: OrdenSvc, estado: str | None = None, buscar: str | None = None) -> list[OrdenEnvioResponse]:
    return [OrdenEnvioResponse.desde_entidad(o) for o in servicio.listar(estado, buscar)]


@router.get("/{orden_id}", response_model=OrdenEnvioResponse)
def obtener_orden(orden_id: int, servicio: OrdenSvc) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.obtener(orden_id))


@router.get("/{orden_id}/hoja", response_model=HojaEnvioResponse,
            summary="Datos para imprimir la hoja interna de entrega o retiro")
def hoja_envio(orden_id: int, servicio: OrdenSvc) -> HojaEnvioResponse:
    return HojaEnvioResponse.desde(servicio.hoja(orden_id))


@router.patch("/{orden_id}/traslado", response_model=OrdenEnvioResponse,
              summary="Transportista, vehículo, conductor y N° de nota de remisión (solo cambia lo que se manda)")
def actualizar_traslado(orden_id: int, datos: TrasladoInput, servicio: OrdenSvc, _usuario: RequireSailUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.actualizar_traslado(orden_id, **datos.model_dump(exclude_unset=True)))


@router.post("", response_model=OrdenEnvioResponse, status_code=201)
def crear_orden(datos: OrdenEnvioCreate, servicio: OrdenSvc, usuario: RequireSailUser) -> OrdenEnvioResponse:
    orden = servicio.crear(usuario_id=usuario.id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return OrdenEnvioResponse.desde_entidad(orden)


@router.delete("/{orden_id}", response_model=Mensaje)
def eliminar_orden(orden_id: int, servicio: OrdenSvc, _usuario: RequireSailUser) -> Mensaje:
    servicio.eliminar(orden_id)
    return Mensaje(mensaje="Orden eliminada exitosamente")


@router.post("/{orden_id}/lista-despachar", response_model=OrdenEnvioResponse)
def marcar_lista_despacho(orden_id: int, servicio: OrdenSvc, _usuario: RequireSailUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.marcar_lista_despacho(orden_id))


@router.post("/{orden_id}/despachar", response_model=OrdenEnvioResponse, summary="Despachar (descuenta stock, valida disponibilidad)")
def despachar_orden(orden_id: int, datos: DespacharInput, servicio: OrdenSvc, usuario: RequireSailUser) -> OrdenEnvioResponse:
    traslado = datos.model_dump(exclude_unset=True, exclude={"numero_guia"})
    return OrdenEnvioResponse.desde_entidad(servicio.despachar(orden_id, datos.numero_guia, usuario.id, **traslado))


@router.post("/{orden_id}/entregar", response_model=OrdenEnvioResponse)
def entregar_orden(
    orden_id: int, servicio: OrdenSvc, usuario: RequireSailUser,
    datos: Annotated[ObservacionesOpcionales | None, Body()] = None,
) -> OrdenEnvioResponse:
    """Las observaciones de la entrega son opcionales: se acepta sin cuerpo, con {} o con texto.
    En un retiro en el local, acá se descuenta el stock. El pedido registra su
    cobro: a cuenta se carga a la cuenta corriente; contra entrega queda por rendir."""
    observaciones = (datos.observaciones or "").strip() or None if datos else None
    return OrdenEnvioResponse.desde_entidad(servicio.entregar(orden_id, observaciones, usuario.id))


@router.post("/{orden_id}/devolver", response_model=OrdenEnvioResponse)
def devolver_orden(orden_id: int, datos: ObservacionesRequeridas, servicio: OrdenSvc, usuario: RequireSailUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.devolver(orden_id, datos.observaciones, usuario.id))


@router.post("/{orden_id}/cancelar", response_model=OrdenEnvioResponse)
def cancelar_orden(orden_id: int, datos: ObservacionesRequeridas, servicio: OrdenSvc, _usuario: RequireSailUser) -> OrdenEnvioResponse:
    return OrdenEnvioResponse.desde_entidad(servicio.cancelar(orden_id, datos.observaciones))
