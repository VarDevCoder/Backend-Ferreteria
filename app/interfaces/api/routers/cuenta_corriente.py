"""Endpoints de cuenta corriente: estado de cuenta, cobros y deudores."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.cuenta_corriente_service import CuentaCorrienteService
from app.interfaces.api.deps import RequireAnkorUser, get_cuenta_corriente_service
from app.interfaces.api.schemas.cuenta_corriente import (
    CobroInput,
    DeudorResponse,
    EstadoDeCuentaResponse,
    MovimientoCuentaResponse,
)

router = APIRouter(tags=["Cuenta corriente"])

CuentaSvc = Annotated[CuentaCorrienteService, Depends(get_cuenta_corriente_service)]


def _estado(datos: dict) -> EstadoDeCuentaResponse:
    return EstadoDeCuentaResponse(
        **{k: v for k, v in datos.items() if k != "movimientos"},
        movimientos=[_movimiento(m) for m in datos["movimientos"]],
    )


def _movimiento(m) -> MovimientoCuentaResponse:
    return MovimientoCuentaResponse(
        id=m.id, tipo=m.tipo.value, monto=m.monto, venta_id=m.venta_id,
        metodo_pago=m.metodo_pago.value if m.metodo_pago else None, referencia=m.referencia, created_at=m.created_at,
    )


@router.get("/clientes/{cliente_id}/cuenta-corriente", response_model=EstadoDeCuentaResponse,
            summary="Estado de cuenta: saldo, límite, disponible y últimos movimientos")
def estado_de_cuenta(cliente_id: int, servicio: CuentaSvc, limit: int = 100) -> EstadoDeCuentaResponse:
    return _estado(servicio.estado_de_cuenta(cliente_id, limit))


@router.post("/clientes/{cliente_id}/cuenta-corriente/cobros", response_model=EstadoDeCuentaResponse, status_code=201,
             summary="Cobra (total o parcialmente) la deuda de un cliente")
def registrar_cobro(cliente_id: int, datos: CobroInput, servicio: CuentaSvc, usuario: RequireAnkorUser) -> EstadoDeCuentaResponse:
    servicio.registrar_cobro(cliente_id, datos.monto, datos.metodo, datos.referencia, usuario.id)
    return _estado(servicio.estado_de_cuenta(cliente_id))


@router.get("/cuentas-corrientes/deudores", response_model=list[DeudorResponse],
            summary="Clientes que deben, con antigüedad de la deuda (0-30, 31-60, 61-90, +90 días)")
def deudores(servicio: CuentaSvc) -> list[DeudorResponse]:
    return [DeudorResponse(**d) for d in servicio.deudores()]
