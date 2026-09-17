"""Endpoints de Clientes, Proveedores y catálogo por proveedor (CU-07, CU-08, CU-09)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.contactos_service import ClienteService, ProveedorProductoService, ProveedorService
from app.domain.entities import Proveedor
from app.interfaces.api.deps import (
    CurrentUser,
    RequireAnkorUser,
    get_cliente_service,
    get_proveedor_producto_service,
    get_proveedor_service,
)
from app.interfaces.api.schemas.common import Mensaje
from app.interfaces.api.schemas.contactos import (
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    ProveedorCreate,
    ProveedorProductoCreate,
    ProveedorProductoResponse,
    ProveedorProductoUpdate,
    ProveedorResponse,
    ProveedorUpdate,
)

router = APIRouter(tags=["Contactos"])

ClienteSvc = Annotated[ClienteService, Depends(get_cliente_service)]
ProveedorSvc = Annotated[ProveedorService, Depends(get_proveedor_service)]
ProveedorProductoSvc = Annotated[ProveedorProductoService, Depends(get_proveedor_producto_service)]


def _proveedor_response(p: Proveedor) -> ProveedorResponse:
    return ProveedorResponse(
        id=p.id, razon_social=p.razon_social, ruc=p.ruc, telefono=p.telefono, direccion=p.direccion,
        ciudad=p.ciudad, rubros=p.rubros, notas=p.notas, email=p.email, activo=p.usuario_activo,
    )


# --- Clientes ---------------------------------------------------------------------

@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(servicio: ClienteSvc, busqueda: str | None = None, activo: bool | None = None, ciudad: str | None = None) -> list[ClienteResponse]:
    return [ClienteResponse(**vars(c)) for c in servicio.listar(busqueda, activo, ciudad)]


@router.get("/clientes/ciudades", response_model=list[str])
def ciudades_de_clientes(servicio: ClienteSvc) -> list[str]:
    return servicio.ciudades()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, servicio: ClienteSvc) -> ClienteResponse:
    return ClienteResponse(**vars(servicio.obtener(cliente_id)))


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
def crear_cliente(datos: ClienteCreate, servicio: ClienteSvc, _usuario: RequireAnkorUser) -> ClienteResponse:
    return ClienteResponse(**vars(servicio.crear(**datos.model_dump())))


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(cliente_id: int, datos: ClienteUpdate, servicio: ClienteSvc, _usuario: RequireAnkorUser) -> ClienteResponse:
    return ClienteResponse(**vars(servicio.actualizar(cliente_id, **datos.model_dump())))


@router.delete("/clientes/{cliente_id}", response_model=Mensaje)
def eliminar_cliente(cliente_id: int, servicio: ClienteSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(cliente_id)
    return Mensaje(mensaje="Cliente eliminado exitosamente")


@router.post("/clientes/{cliente_id}/toggle-activo", response_model=ClienteResponse)
def toggle_activo_cliente(cliente_id: int, servicio: ClienteSvc, _usuario: RequireAnkorUser) -> ClienteResponse:
    return ClienteResponse(**vars(servicio.toggle_activo(cliente_id)))


# --- Proveedores ---------------------------------------------------------------------

@router.get("/proveedores", response_model=list[ProveedorResponse])
def listar_proveedores(servicio: ProveedorSvc, solo_activos: bool = False) -> list[ProveedorResponse]:
    return [_proveedor_response(p) for p in servicio.listar(solo_activos)]


@router.get("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def obtener_proveedor(proveedor_id: int, servicio: ProveedorSvc) -> ProveedorResponse:
    return _proveedor_response(servicio.obtener(proveedor_id))


@router.post("/proveedores", response_model=ProveedorResponse, status_code=201)
def crear_proveedor(datos: ProveedorCreate, servicio: ProveedorSvc, _usuario: RequireAnkorUser) -> ProveedorResponse:
    return _proveedor_response(servicio.crear(**datos.model_dump()))


@router.put("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def actualizar_proveedor(proveedor_id: int, datos: ProveedorUpdate, servicio: ProveedorSvc, _usuario: RequireAnkorUser) -> ProveedorResponse:
    return _proveedor_response(servicio.actualizar(proveedor_id, **datos.model_dump()))


@router.post("/proveedores/{proveedor_id}/toggle-activo", response_model=ProveedorResponse)
def toggle_activo_proveedor(proveedor_id: int, servicio: ProveedorSvc, _usuario: RequireAnkorUser) -> ProveedorResponse:
    return _proveedor_response(servicio.toggle_activo(proveedor_id))


# --- Catálogo por proveedor ---------------------------------------------------------------------

@router.get("/proveedor-productos", response_model=list[ProveedorProductoResponse])
def listar_catalogo_proveedor(
    servicio: ProveedorProductoSvc, proveedor_id: int | None = None, producto_id: int | None = None, disponible: bool | None = None
) -> list[ProveedorProductoResponse]:
    return [ProveedorProductoResponse(**vars(i)) for i in servicio.listar(proveedor_id, producto_id, disponible)]


@router.post("/proveedor-productos", response_model=ProveedorProductoResponse, status_code=201)
def agregar_producto_a_catalogo(datos: ProveedorProductoCreate, servicio: ProveedorProductoSvc, _usuario: CurrentUser) -> ProveedorProductoResponse:
    return ProveedorProductoResponse(**vars(servicio.crear(**datos.model_dump())))


@router.put("/proveedor-productos/{item_id}", response_model=ProveedorProductoResponse)
def actualizar_producto_de_catalogo(item_id: int, datos: ProveedorProductoUpdate, servicio: ProveedorProductoSvc, _usuario: CurrentUser) -> ProveedorProductoResponse:
    return ProveedorProductoResponse(**vars(servicio.actualizar(item_id, **datos.model_dump())))


@router.delete("/proveedor-productos/{item_id}", response_model=Mensaje)
def eliminar_producto_de_catalogo(item_id: int, servicio: ProveedorProductoSvc, _usuario: CurrentUser) -> Mensaje:
    servicio.eliminar(item_id)
    return Mensaje(mensaje="Producto quitado del catálogo")


@router.post("/proveedor-productos/{item_id}/toggle-disponible", response_model=ProveedorProductoResponse)
def toggle_disponible_producto(item_id: int, servicio: ProveedorProductoSvc, _usuario: CurrentUser) -> ProveedorProductoResponse:
    return ProveedorProductoResponse(**vars(servicio.toggle_disponible(item_id)))
