"""Endpoints de Categorías y Productos (CU-05, CU-06)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.catalogo_service import CategoriaService, ProductoService
from app.interfaces.api.deps import RequireAnkorUser, get_categoria_service, get_producto_service
from app.interfaces.api.schemas.catalogo import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaUpdate,
    ProductoCreate,
    ProductoResponse,
    ProductoUpdate,
)
from app.interfaces.api.schemas.common import Mensaje

router = APIRouter(tags=["Catálogo"])

CategoriaSvc = Annotated[CategoriaService, Depends(get_categoria_service)]
ProductoSvc = Annotated[ProductoService, Depends(get_producto_service)]


@router.get("/categorias", response_model=list[CategoriaResponse])
def listar_categorias(servicio: CategoriaSvc, solo_activas: bool = False) -> list[CategoriaResponse]:
    return [CategoriaResponse(**vars(c)) for c in servicio.listar(solo_activas)]


@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
def crear_categoria(datos: CategoriaCreate, servicio: CategoriaSvc, _usuario: RequireAnkorUser) -> CategoriaResponse:
    categoria = servicio.crear(datos.nombre, datos.descripcion, datos.orden)
    return CategoriaResponse(**vars(categoria))


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def actualizar_categoria(categoria_id: int, datos: CategoriaUpdate, servicio: CategoriaSvc, _usuario: RequireAnkorUser) -> CategoriaResponse:
    categoria = servicio.actualizar(categoria_id, datos.nombre, datos.descripcion, datos.activo, datos.orden)
    return CategoriaResponse(**vars(categoria))


@router.delete("/categorias/{categoria_id}", response_model=Mensaje)
def eliminar_categoria(categoria_id: int, servicio: CategoriaSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(categoria_id)
    return Mensaje(mensaje="Categoría eliminada exitosamente")


@router.get("/productos", response_model=list[ProductoResponse])
def listar_productos(
    servicio: ProductoSvc, solo_activos: bool = False, categoria_id: int | None = None, buscar: str | None = None
) -> list[ProductoResponse]:
    return [ProductoResponse.desde_entidad(p) for p in servicio.listar(solo_activos, categoria_id, buscar)]


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, servicio: ProductoSvc) -> ProductoResponse:
    return ProductoResponse.desde_entidad(servicio.obtener(producto_id))


@router.post("/productos", response_model=ProductoResponse, status_code=201)
def crear_producto(datos: ProductoCreate, servicio: ProductoSvc, _usuario: RequireAnkorUser) -> ProductoResponse:
    producto = servicio.crear(
        datos.nombre, datos.descripcion, datos.categoria_id, datos.precio_compra, datos.precio_venta,
        datos.stock_minimo, datos.unidad_medida,
    )
    return ProductoResponse.desde_entidad(producto)


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(producto_id: int, datos: ProductoUpdate, servicio: ProductoSvc, _usuario: RequireAnkorUser) -> ProductoResponse:
    producto = servicio.actualizar(
        producto_id, datos.nombre, datos.descripcion, datos.categoria_id, datos.precio_compra, datos.precio_venta,
        datos.stock_minimo, datos.unidad_medida, datos.activo,
    )
    return ProductoResponse.desde_entidad(producto)


@router.delete("/productos/{producto_id}", response_model=Mensaje)
def eliminar_producto(producto_id: int, servicio: ProductoSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(producto_id)
    return Mensaje(mensaje="Producto eliminado exitosamente")
