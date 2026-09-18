"""Endpoints de Caja y venta de mostrador."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.caja_service import CajaService
from app.interfaces.api.deps import RequireAnkorUser, get_caja_service
from app.interfaces.api.schemas.caja import (
    AbrirCajaInput,
    CajaTurnoResponse,
    CerrarCajaInput,
    MovimientoCajaInput,
    ResumenCajaHoyResponse,
    VentaMostradorCreate,
    VentaMostradorResponse,
)

router = APIRouter(prefix="/caja", tags=["Caja"])

CajaSvc = Annotated[CajaService, Depends(get_caja_service)]


@router.get("/turno-abierto", response_model=CajaTurnoResponse | None)
def turno_abierto(servicio: CajaSvc) -> CajaTurnoResponse | None:
    turno = servicio.turno_abierto()
    return CajaTurnoResponse.desde_entidad(turno) if turno else None


@router.get("/turnos", response_model=list[CajaTurnoResponse])
def historial_turnos(servicio: CajaSvc, limit: int = 30) -> list[CajaTurnoResponse]:
    return [CajaTurnoResponse.desde_entidad(t) for t in servicio.historial_turnos(limit)]


@router.get("/turnos/{turno_id}", response_model=CajaTurnoResponse)
def obtener_turno(turno_id: int, servicio: CajaSvc) -> CajaTurnoResponse:
    return CajaTurnoResponse.desde_entidad(servicio.obtener_turno(turno_id))


@router.post("/turnos/abrir", response_model=CajaTurnoResponse, status_code=201)
def abrir_turno(datos: AbrirCajaInput, servicio: CajaSvc, usuario: RequireAnkorUser) -> CajaTurnoResponse:
    turno = servicio.abrir_turno(usuario_id=usuario.id, fondo_inicial=datos.fondo_inicial)
    return CajaTurnoResponse.desde_entidad(turno)


@router.post("/turnos/{turno_id}/movimientos", response_model=CajaTurnoResponse)
def registrar_movimiento(
    turno_id: int, datos: MovimientoCajaInput, servicio: CajaSvc, usuario: RequireAnkorUser
) -> CajaTurnoResponse:
    turno = servicio.registrar_movimiento(
        turno_id, tipo=datos.tipo, monto=datos.monto, motivo=datos.motivo, usuario_id=usuario.id
    )
    return CajaTurnoResponse.desde_entidad(turno)


@router.post("/turnos/{turno_id}/cerrar", response_model=CajaTurnoResponse, summary="Arqueo: cierra el turno comparando conteo físico vs. saldo esperado")
def cerrar_turno(turno_id: int, datos: CerrarCajaInput, servicio: CajaSvc, _usuario: RequireAnkorUser) -> CajaTurnoResponse:
    turno = servicio.cerrar_turno(turno_id, conteo_fisico=datos.conteo_fisico, notas=datos.notas)
    return CajaTurnoResponse.desde_entidad(turno)


@router.get("/ventas", response_model=list[VentaMostradorResponse])
def listar_ventas(servicio: CajaSvc, caja_turno_id: int | None = None, limit: int = 100) -> list[VentaMostradorResponse]:
    return [VentaMostradorResponse.desde_entidad(v) for v in servicio.listar_ventas(caja_turno_id, limit)]


@router.post("/ventas", response_model=VentaMostradorResponse, status_code=201, summary="Venta de mostrador: cobro directo, descuenta stock de inmediato")
def registrar_venta(datos: VentaMostradorCreate, servicio: CajaSvc, usuario: RequireAnkorUser) -> VentaMostradorResponse:
    venta = servicio.registrar_venta(
        usuario_id=usuario.id,
        items=[i.model_dump() for i in datos.items],
        metodo_pago=datos.metodo_pago,
        cliente_id=datos.cliente_id,
        descuento=datos.descuento,
        notas=datos.notas,
    )
    return VentaMostradorResponse.desde_entidad(venta)


@router.get("/resumen-hoy", response_model=ResumenCajaHoyResponse)
def resumen_hoy(servicio: CajaSvc) -> ResumenCajaHoyResponse:
    return ResumenCajaHoyResponse(**servicio.resumen_hoy())
