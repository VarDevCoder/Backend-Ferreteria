"""Cobros de pedidos: señas y pagos anticipados, rendición del cobro contra
entrega y listado de cobros por rendir. Son tareas de caja (permiso del
módulo caja). Contrato: docs/api/logistica.md."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.cobro_pedido_service import CobroPedidoService
from app.interfaces.api.deps import CurrentUser, get_cobro_pedido_service
from app.interfaces.api.schemas.flujo import PedidoClienteResponse
from app.interfaces.api.schemas.logistica import (
    AnularPagoInput,
    CobroPorRendirResponse,
    CobrosPedidoResponse,
    PagoPedidoResponse,
    RegistrarPagosInput,
)

router = APIRouter(tags=["Cobros de pedidos"])

CobroSvc = Annotated[CobroPedidoService, Depends(get_cobro_pedido_service)]


def _respuesta(servicio: CobroPedidoService, pedido) -> CobrosPedidoResponse:
    return CobrosPedidoResponse(
        pedido=PedidoClienteResponse.desde_entidad(pedido),
        pagos=[PagoPedidoResponse.desde_entidad(p) for p in servicio.listar_pagos(pedido.id)],
    )


@router.get("/cobros-por-rendir", response_model=list[CobroPorRendirResponse],
            summary="Pedidos entregados contra entrega que el repartidor todavía no rindió en caja")
def cobros_por_rendir(servicio: CobroSvc) -> list[CobroPorRendirResponse]:
    return [CobroPorRendirResponse(**fila) for fila in servicio.por_rendir()]


@router.get("/pedidos-cliente/{pedido_id}/pagos", response_model=list[PagoPedidoResponse])
def listar_pagos(pedido_id: int, servicio: CobroSvc) -> list[PagoPedidoResponse]:
    return [PagoPedidoResponse.desde_entidad(p) for p in servicio.listar_pagos(pedido_id)]


@router.post("/pedidos-cliente/{pedido_id}/pagos", response_model=CobrosPedidoResponse, status_code=201,
             summary="Seña o pago anticipado (con caja abierta; el efectivo entra al arqueo)")
def registrar_anticipo(pedido_id: int, datos: RegistrarPagosInput, servicio: CobroSvc, usuario: CurrentUser) -> CobrosPedidoResponse:
    pedido = servicio.registrar_anticipo(pedido_id, [p.model_dump() for p in datos.pagos], usuario.id)
    return _respuesta(servicio, pedido)


@router.post("/pedidos-cliente/{pedido_id}/pagos/{pago_id}/anular", response_model=CobrosPedidoResponse,
             summary="Anular (devolver) una seña o pago anticipado antes de entregar")
def anular_pago(pedido_id: int, pago_id: int, datos: AnularPagoInput, servicio: CobroSvc, usuario: CurrentUser) -> CobrosPedidoResponse:
    return _respuesta(servicio, servicio.anular_pago(pedido_id, pago_id, datos.motivo, usuario.id))


@router.post("/pedidos-cliente/{pedido_id}/rendir", response_model=CobrosPedidoResponse,
             summary="Rendición del cobro contra entrega en la caja abierta (pago mixto; puede ser parcial)")
def rendir(pedido_id: int, datos: RegistrarPagosInput, servicio: CobroSvc, usuario: CurrentUser) -> CobrosPedidoResponse:
    pedido = servicio.rendir(pedido_id, [p.model_dump() for p in datos.pagos], usuario.id)
    return _respuesta(servicio, pedido)
