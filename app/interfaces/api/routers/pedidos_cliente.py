"""Endpoints de Pedidos de Cliente (CU-10, CU-11, y CU-13 ★ vía /comparacion)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.catalogo_service import ProductoService
from app.application.services.contactos_service import ProveedorProductoService
from app.application.services.pedido_cliente_service import PedidoClienteService
from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.interfaces.api.deps import (
    RequireAnkorUser,
    get_pedido_cliente_service,
    get_producto_service,
    get_proveedor_producto_service,
    get_solicitud_service,
)
from app.interfaces.api.schemas.common import Mensaje, MotivoRequerido
from app.interfaces.api.schemas.flujo import (
    ComparacionPedidoResponse,
    ComparacionProducto,
    OfertaCatalogoProveedor,
    PedidoClienteCreate,
    PedidoClienteResponse,
    PedidoClienteUpdate,
    SolicitudPresupuestoResponse,
)

router = APIRouter(prefix="/pedidos-cliente", tags=["Pedidos de Cliente"])

PedidoSvc = Annotated[PedidoClienteService, Depends(get_pedido_cliente_service)]
SolicitudSvc = Annotated[SolicitudPresupuestoService, Depends(get_solicitud_service)]
CatalogoSvc = Annotated[ProveedorProductoService, Depends(get_proveedor_producto_service)]
ProductoSvc = Annotated[ProductoService, Depends(get_producto_service)]


@router.get("", response_model=list[PedidoClienteResponse])
def listar_pedidos(servicio: PedidoSvc, estado: str | None = None, buscar: str | None = None) -> list[PedidoClienteResponse]:
    return [PedidoClienteResponse.desde_entidad(p) for p in servicio.listar(estado, buscar)]


@router.get("/{pedido_id}", response_model=PedidoClienteResponse)
def obtener_pedido(pedido_id: int, servicio: PedidoSvc) -> PedidoClienteResponse:
    return PedidoClienteResponse.desde_entidad(servicio.obtener(pedido_id))


@router.post("", response_model=PedidoClienteResponse, status_code=201)
def crear_pedido(datos: PedidoClienteCreate, servicio: PedidoSvc, usuario: RequireAnkorUser) -> PedidoClienteResponse:
    pedido = servicio.crear(usuario_id=usuario.id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return PedidoClienteResponse.desde_entidad(pedido)


@router.put("/{pedido_id}", response_model=PedidoClienteResponse)
def actualizar_pedido(pedido_id: int, datos: PedidoClienteUpdate, servicio: PedidoSvc, _usuario: RequireAnkorUser) -> PedidoClienteResponse:
    pedido = servicio.actualizar(pedido_id, items=[i.model_dump() for i in datos.items], **datos.model_dump(exclude={"items"}))
    return PedidoClienteResponse.desde_entidad(pedido)


@router.delete("/{pedido_id}", response_model=Mensaje)
def eliminar_pedido(pedido_id: int, servicio: PedidoSvc, _usuario: RequireAnkorUser) -> Mensaje:
    servicio.eliminar(pedido_id)
    return Mensaje(mensaje="Solicitud eliminada exitosamente")


@router.post("/{pedido_id}/procesar", response_model=PedidoClienteResponse)
def procesar_pedido(pedido_id: int, servicio: PedidoSvc, _usuario: RequireAnkorUser) -> PedidoClienteResponse:
    return PedidoClienteResponse.desde_entidad(servicio.procesar(pedido_id))


@router.post("/{pedido_id}/cancelar", response_model=PedidoClienteResponse)
def cancelar_pedido(pedido_id: int, datos: MotivoRequerido, servicio: PedidoSvc, _usuario: RequireAnkorUser) -> PedidoClienteResponse:
    return PedidoClienteResponse.desde_entidad(servicio.cancelar(pedido_id, datos.motivo))


@router.post("/{pedido_id}/mercaderia-recibida", response_model=PedidoClienteResponse)
def marcar_mercaderia_recibida(pedido_id: int, servicio: PedidoSvc, _usuario: RequireAnkorUser) -> PedidoClienteResponse:
    return PedidoClienteResponse.desde_entidad(servicio.marcar_mercaderia_recibida(pedido_id))


@router.post("/{pedido_id}/solicitar-todos", response_model=Mensaje)
def solicitar_cotizacion_a_todos(pedido_id: int, servicio: PedidoSvc, usuario: RequireAnkorUser) -> Mensaje:
    _pedido, creadas = servicio.solicitar_cotizacion_todos(pedido_id, usuario.id)
    return Mensaje(mensaje=f"Se enviaron {creadas} solicitudes de cotización a proveedores")


@router.get("/{pedido_id}/comparacion", response_model=ComparacionPedidoResponse, summary="CU-13 ★: comparar ofertas de proveedores para este pedido")
def comparar_ofertas(
    pedido_id: int, pedidos: PedidoSvc, solicitudes: SolicitudSvc, catalogo: CatalogoSvc, productos: ProductoSvc
) -> ComparacionPedidoResponse:
    pedido = pedidos.obtener(pedido_id)
    cotizaciones = solicitudes.listar(pedido_cliente_id=pedido_id)

    comparacion: list[ComparacionProducto] = []
    for item in pedido.items:
        ofertas_catalogo = catalogo.listar(producto_id=item.producto_id, disponible=True)
        producto = productos.obtener(item.producto_id)
        comparacion.append(
            ComparacionProducto(
                producto_id=item.producto_id,
                producto_nombre=producto.nombre,
                cantidad_requerida=float(item.cantidad),
                ofertas_catalogo=[
                    OfertaCatalogoProveedor(
                        proveedor_id=o.proveedor_id, proveedor_nombre=o.nombre_proveedor or f"Proveedor #{o.proveedor_id}",
                        precio=o.precio, disponible=o.disponible, tiempo_entrega_dias=o.tiempo_entrega_dias,
                    )
                    for o in ofertas_catalogo
                ],
            )
        )

    return ComparacionPedidoResponse(
        pedido=PedidoClienteResponse.desde_entidad(pedido),
        cotizaciones=[SolicitudPresupuestoResponse.desde_entidad(s) for s in cotizaciones],
        comparacion_catalogo=comparacion,
    )
