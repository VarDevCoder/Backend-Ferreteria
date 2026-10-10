"""Endpoints de stock no vendible y reclamos al proveedor.

Permisos: módulo inventario (consultan todos; marcan, resuelven y reclaman
admin, encargado y depósito). Contrato para el frontend:
`docs/api/stock-no-vendible.md`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.stock_no_vendible_service import ReclamoProveedorService, StockNoVendibleService
from app.interfaces.api.deps import CurrentUser, get_reclamo_proveedor_service, get_stock_no_vendible_service
from app.interfaces.api.schemas.common import Mensaje
from app.interfaces.api.schemas.stock_no_vendible import (
    AceptarReclamoInput,
    DocumentoReclamoResponse,
    DocumentosReclamoInput,
    EnviarReclamoInput,
    MarcarNoVendibleInput,
    RechazarReclamoInput,
    ReclamoCreate,
    ReclamoResponse,
    ReclamoUpdate,
    ResolverItemInput,
    ResolverNoVendibleInput,
    StockNoVendibleResponse,
)

router = APIRouter(tags=["Stock no vendible y reclamos"])

NoVendibleSvc = Annotated[StockNoVendibleService, Depends(get_stock_no_vendible_service)]
ReclamoSvc = Annotated[ReclamoProveedorService, Depends(get_reclamo_proveedor_service)]


# --- Stock no vendible ----------------------------------------------------------------

@router.get("/stock-no-vendible", response_model=list[StockNoVendibleResponse])
def listar_no_vendible(
    servicio: NoVendibleSvc, estado: str | None = None, producto_id: int | None = None,
    proveedor_id: int | None = None, motivo: str | None = None,
) -> list[StockNoVendibleResponse]:
    return [StockNoVendibleResponse.desde_entidad(r) for r in servicio.listar(estado, producto_id, proveedor_id, motivo)]


@router.get("/stock-no-vendible/{registro_id}", response_model=StockNoVendibleResponse)
def obtener_no_vendible(registro_id: int, servicio: NoVendibleSvc) -> StockNoVendibleResponse:
    return StockNoVendibleResponse.desde_entidad(servicio.obtener(registro_id), con_resoluciones=True)


@router.post(
    "/stock-no-vendible", response_model=StockNoVendibleResponse, status_code=201,
    summary="Pasar unidades de vendible a no vendible (averiado, abollado, vencido...)",
)
def marcar_no_vendible(datos: MarcarNoVendibleInput, servicio: NoVendibleSvc, usuario: CurrentUser) -> StockNoVendibleResponse:
    registro = servicio.marcar(usuario_id=usuario.id, **datos.model_dump())
    return StockNoVendibleResponse.desde_entidad(registro, con_resoluciones=True)


@router.post("/stock-no-vendible/{registro_id}/reparar", response_model=StockNoVendibleResponse,
             summary="Unidades reparadas: vuelven a stock vendible")
def reparar_no_vendible(
    registro_id: int, datos: ResolverNoVendibleInput, servicio: NoVendibleSvc, usuario: CurrentUser,
) -> StockNoVendibleResponse:
    registro = servicio.reparar(registro_id, datos.cantidad, usuario.id, datos.nota)
    return StockNoVendibleResponse.desde_entidad(registro, con_resoluciones=True)


@router.post("/stock-no-vendible/{registro_id}/descartar", response_model=StockNoVendibleResponse,
             summary="Descartar unidades: baja con pérdida")
def descartar_no_vendible(
    registro_id: int, datos: ResolverNoVendibleInput, servicio: NoVendibleSvc, usuario: CurrentUser,
) -> StockNoVendibleResponse:
    registro = servicio.descartar(registro_id, datos.cantidad, usuario.id, datos.nota)
    return StockNoVendibleResponse.desde_entidad(registro, con_resoluciones=True)


# --- Reclamos al proveedor --------------------------------------------------------------

@router.get("/reclamos-proveedor", response_model=list[ReclamoResponse])
def listar_reclamos(servicio: ReclamoSvc, estado: str | None = None, proveedor_id: int | None = None) -> list[ReclamoResponse]:
    return [ReclamoResponse.desde_entidad(r) for r in servicio.listar(estado, proveedor_id)]


@router.get("/reclamos-proveedor/{reclamo_id}", response_model=ReclamoResponse)
def obtener_reclamo(reclamo_id: int, servicio: ReclamoSvc) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.obtener(reclamo_id))


@router.get("/reclamos-proveedor/{reclamo_id}/documento", response_model=DocumentoReclamoResponse,
            summary="Datos del reclamo para imprimir o enviar al proveedor")
def documento_reclamo(reclamo_id: int, servicio: ReclamoSvc) -> DocumentoReclamoResponse:
    return DocumentoReclamoResponse.desde(*servicio.documento(reclamo_id))


@router.post("/reclamos-proveedor", response_model=ReclamoResponse, status_code=201, summary="Crear reclamo (borrador)")
def crear_reclamo(datos: ReclamoCreate, servicio: ReclamoSvc, usuario: CurrentUser) -> ReclamoResponse:
    reclamo = servicio.crear(datos.proveedor_id, [i.model_dump() for i in datos.items], usuario.id, datos.notas)
    return ReclamoResponse.desde_entidad(reclamo)


@router.put("/reclamos-proveedor/{reclamo_id}", response_model=ReclamoResponse, summary="Editar un reclamo en borrador")
def actualizar_reclamo(reclamo_id: int, datos: ReclamoUpdate, servicio: ReclamoSvc, _usuario: CurrentUser) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.actualizar(reclamo_id, [i.model_dump() for i in datos.items], datos.notas))


@router.delete("/reclamos-proveedor/{reclamo_id}", response_model=Mensaje, summary="Eliminar un reclamo en borrador")
def eliminar_reclamo(reclamo_id: int, servicio: ReclamoSvc, _usuario: CurrentUser) -> Mensaje:
    servicio.eliminar(reclamo_id)
    return Mensaje(mensaje="Reclamo eliminado; las unidades vuelven a estar disponibles para resolver")


@router.post("/reclamos-proveedor/{reclamo_id}/enviar", response_model=ReclamoResponse)
def enviar_reclamo(reclamo_id: int, datos: EnviarReclamoInput, servicio: ReclamoSvc, _usuario: CurrentUser) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.enviar(reclamo_id, datos.numero_nota_remision))


@router.post("/reclamos-proveedor/{reclamo_id}/aceptar", response_model=ReclamoResponse)
def aceptar_reclamo(reclamo_id: int, datos: AceptarReclamoInput, servicio: ReclamoSvc, _usuario: CurrentUser) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.aceptar(reclamo_id, datos.respuesta_proveedor))


@router.post("/reclamos-proveedor/{reclamo_id}/rechazar", response_model=ReclamoResponse)
def rechazar_reclamo(reclamo_id: int, datos: RechazarReclamoInput, servicio: ReclamoSvc, usuario: CurrentUser) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.rechazar(reclamo_id, datos.motivo, usuario.id))


@router.post("/reclamos-proveedor/{reclamo_id}/items/{item_id}/resolver", response_model=ReclamoResponse,
             summary="Resolver un ítem: reposición, nota de crédito o rechazado")
def resolver_item_reclamo(
    reclamo_id: int, item_id: int, datos: ResolverItemInput, servicio: ReclamoSvc, usuario: CurrentUser,
) -> ReclamoResponse:
    reclamo = servicio.resolver_item(
        reclamo_id, item_id, datos.resolucion, usuario.id, datos.monto_nota_credito, datos.nota, datos.numero_nota_credito,
    )
    return ReclamoResponse.desde_entidad(reclamo)


@router.patch("/reclamos-proveedor/{reclamo_id}/documentos", response_model=ReclamoResponse,
              summary="Registrar N° de nota de crédito del proveedor y de nota de remisión")
def documentos_reclamo(
    reclamo_id: int, datos: DocumentosReclamoInput, servicio: ReclamoSvc, _usuario: CurrentUser,
) -> ReclamoResponse:
    return ReclamoResponse.desde_entidad(servicio.actualizar_documentos(reclamo_id, **datos.model_dump(exclude_unset=True)))
