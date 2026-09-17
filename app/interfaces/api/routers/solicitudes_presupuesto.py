"""Endpoints de Solicitudes de Presupuesto — lado Compras (CU-11, CU-13 ★)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.interfaces.api.deps import RequireAnkorUser, get_solicitud_service
from app.interfaces.api.schemas.common import Mensaje
from app.interfaces.api.schemas.flujo import (
    CotizacionInput,
    OrdenCompraResponse,
    SinStockInput,
    SolicitudPresupuestoCreate,
    SolicitudPresupuestoResponse,
    VerSolicitudInput,
)

router = APIRouter(prefix="/solicitudes-presupuesto", tags=["Solicitudes de Presupuesto"])

SolicitudSvc = Annotated[SolicitudPresupuestoService, Depends(get_solicitud_service)]


@router.get("", response_model=list[SolicitudPresupuestoResponse])
def listar_solicitudes(
    servicio: SolicitudSvc, estado: str | None = None, proveedor_id: int | None = None, pedido_cliente_id: int | None = None
) -> list[SolicitudPresupuestoResponse]:
    return [SolicitudPresupuestoResponse.desde_entidad(s) for s in servicio.listar(estado, proveedor_id, pedido_cliente_id)]


@router.get("/{solicitud_id}", response_model=SolicitudPresupuestoResponse)
def obtener_solicitud(solicitud_id: int, servicio: SolicitudSvc) -> SolicitudPresupuestoResponse:
    return SolicitudPresupuestoResponse.desde_entidad(servicio.obtener(solicitud_id))


@router.post("", response_model=SolicitudPresupuestoResponse, status_code=201)
def crear_solicitud(datos: SolicitudPresupuestoCreate, servicio: SolicitudSvc, usuario: RequireAnkorUser) -> SolicitudPresupuestoResponse:
    solicitud = servicio.crear(usuario_id=usuario.id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return SolicitudPresupuestoResponse.desde_entidad(solicitud)


@router.delete("/{solicitud_id}", response_model=Mensaje)
def eliminar_solicitud(solicitud_id: int, servicio: SolicitudSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(solicitud_id)
    return Mensaje(mensaje="Solicitud eliminada exitosamente")


@router.post("/{solicitud_id}/aceptar", response_model=OrdenCompraResponse, summary="CU-13 ★: acepta la cotización y emite la Orden de Compra")
def aceptar_cotizacion(solicitud_id: int, servicio: SolicitudSvc, usuario: RequireAnkorUser) -> OrdenCompraResponse:
    orden = servicio.aceptar(solicitud_id, usuario.id)
    return OrdenCompraResponse.desde_entidad(orden)


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudPresupuestoResponse)
def rechazar_cotizacion(solicitud_id: int, servicio: SolicitudSvc, _usuario: RequireAnkorUser) -> SolicitudPresupuestoResponse:
    return SolicitudPresupuestoResponse.desde_entidad(servicio.rechazar(solicitud_id))


# --- Portal proveedor (CU-12): sin sesión — el proveedor se identifica por proveedor_id ---------

@router.post("/{solicitud_id}/ver", response_model=SolicitudPresupuestoResponse, summary="CU-12: el proveedor abre la solicitud (marca VISTA)")
def ver_solicitud_como_proveedor(solicitud_id: int, datos: VerSolicitudInput, servicio: SolicitudSvc) -> SolicitudPresupuestoResponse:
    return SolicitudPresupuestoResponse.desde_entidad(servicio.ver_como_proveedor(solicitud_id, datos.proveedor_id))


@router.post("/{solicitud_id}/cotizar", response_model=SolicitudPresupuestoResponse, summary="CU-12: el proveedor envía su cotización")
def cotizar_solicitud(solicitud_id: int, datos: CotizacionInput, servicio: SolicitudSvc) -> SolicitudPresupuestoResponse:
    solicitud = servicio.enviar_cotizacion(
        solicitud_id, datos.proveedor_id, datos.dias_entrega_estimados,
        [i.model_dump() for i in datos.items], datos.respuesta_proveedor,
    )
    return SolicitudPresupuestoResponse.desde_entidad(solicitud)


@router.post("/{solicitud_id}/sin-stock", response_model=SolicitudPresupuestoResponse, summary="CU-12: el proveedor marca que no tiene stock")
def marcar_solicitud_sin_stock(solicitud_id: int, datos: SinStockInput, servicio: SolicitudSvc) -> SolicitudPresupuestoResponse:
    return SolicitudPresupuestoResponse.desde_entidad(
        servicio.marcar_sin_stock(solicitud_id, datos.proveedor_id, datos.respuesta_proveedor)
    )
