"""Raíz de composición: arma repositorios y servicios a partir de la sesión de
DB de cada request.

Este MVP es de exhibición directa al cliente: **no hay login**. Todas las
pantallas y endpoints están abiertos. El único motivo por el que sigue
existiendo un "usuario actual" es que varias tablas del dominio (pedidos,
órdenes) guardan `usuario_id` como dato de auditoría — quién generó cada
documento — así que se resuelve automáticamente contra un usuario demo
sembrado por `seed.py`, sin pedir credenciales.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.services.caja_service import CajaService
from app.application.services.catalogo_service import CategoriaService, ProductoService
from app.application.services.contactos_service import ClienteService, ProveedorProductoService, ProveedorService
from app.application.services.dashboard_service import DashboardService
from app.application.services.inventario_service import InventarioService
from app.application.services.orden_compra_service import OrdenCompraService
from app.application.services.orden_envio_service import OrdenEnvioService
from app.application.services.pedido_cliente_service import PedidoClienteService
from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.domain.entities import Usuario
from app.infrastructure.db.repositories.catalogo_repository import SqlAlchemyCategoriaRepository, SqlAlchemyProductoRepository
from app.infrastructure.db.repositories.contactos_repository import (
    SqlAlchemyClienteRepository,
    SqlAlchemyProveedorProductoRepository,
    SqlAlchemyProveedorRepository,
)
from app.infrastructure.db.repositories.flujo_repository import (
    SqlAlchemyCajaTurnoRepository,
    SqlAlchemyMovimientoInventarioRepository,
    SqlAlchemyOrdenCompraRepository,
    SqlAlchemyOrdenEnvioRepository,
    SqlAlchemyPedidoClienteRepository,
    SqlAlchemySolicitudPresupuestoRepository,
    SqlAlchemyVentaMostradorRepository,
)
from app.infrastructure.db.repositories.usuario_repository import SqlAlchemyUsuarioRepository
from app.infrastructure.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]

DEMO_USER_EMAIL = "demo@ankor.local"


# --- Repositorios ---------------------------------------------------------------

def get_usuario_repo(db: DbSession) -> SqlAlchemyUsuarioRepository:
    return SqlAlchemyUsuarioRepository(db)


def get_categoria_repo(db: DbSession) -> SqlAlchemyCategoriaRepository:
    return SqlAlchemyCategoriaRepository(db)


def get_producto_repo(db: DbSession) -> SqlAlchemyProductoRepository:
    return SqlAlchemyProductoRepository(db)


def get_cliente_repo(db: DbSession) -> SqlAlchemyClienteRepository:
    return SqlAlchemyClienteRepository(db)


def get_proveedor_repo(db: DbSession) -> SqlAlchemyProveedorRepository:
    return SqlAlchemyProveedorRepository(db)


def get_proveedor_producto_repo(db: DbSession) -> SqlAlchemyProveedorProductoRepository:
    return SqlAlchemyProveedorProductoRepository(db)


def get_pedido_cliente_repo(db: DbSession) -> SqlAlchemyPedidoClienteRepository:
    return SqlAlchemyPedidoClienteRepository(db)


def get_solicitud_repo(db: DbSession) -> SqlAlchemySolicitudPresupuestoRepository:
    return SqlAlchemySolicitudPresupuestoRepository(db)


def get_orden_compra_repo(db: DbSession) -> SqlAlchemyOrdenCompraRepository:
    return SqlAlchemyOrdenCompraRepository(db)


def get_orden_envio_repo(db: DbSession) -> SqlAlchemyOrdenEnvioRepository:
    return SqlAlchemyOrdenEnvioRepository(db)


def get_movimiento_repo(db: DbSession) -> SqlAlchemyMovimientoInventarioRepository:
    return SqlAlchemyMovimientoInventarioRepository(db)


def get_caja_turno_repo(db: DbSession) -> SqlAlchemyCajaTurnoRepository:
    return SqlAlchemyCajaTurnoRepository(db)


def get_venta_mostrador_repo(db: DbSession) -> SqlAlchemyVentaMostradorRepository:
    return SqlAlchemyVentaMostradorRepository(db)


# --- Servicios (casos de uso) ----------------------------------------------------

def get_categoria_service(repo: Annotated[SqlAlchemyCategoriaRepository, Depends(get_categoria_repo)]) -> CategoriaService:
    return CategoriaService(repo)


def get_producto_service(repo: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)]) -> ProductoService:
    return ProductoService(repo)


def get_cliente_service(repo: Annotated[SqlAlchemyClienteRepository, Depends(get_cliente_repo)]) -> ClienteService:
    return ClienteService(repo)


def get_proveedor_service(
    proveedores: Annotated[SqlAlchemyProveedorRepository, Depends(get_proveedor_repo)],
    usuarios: Annotated[SqlAlchemyUsuarioRepository, Depends(get_usuario_repo)],
) -> ProveedorService:
    return ProveedorService(proveedores, usuarios)


def get_proveedor_producto_service(
    repo: Annotated[SqlAlchemyProveedorProductoRepository, Depends(get_proveedor_producto_repo)],
) -> ProveedorProductoService:
    return ProveedorProductoService(repo)


def get_pedido_cliente_service(
    pedidos: Annotated[SqlAlchemyPedidoClienteRepository, Depends(get_pedido_cliente_repo)],
    clientes: Annotated[SqlAlchemyClienteRepository, Depends(get_cliente_repo)],
    proveedores: Annotated[SqlAlchemyProveedorRepository, Depends(get_proveedor_repo)],
    solicitudes: Annotated[SqlAlchemySolicitudPresupuestoRepository, Depends(get_solicitud_repo)],
) -> PedidoClienteService:
    return PedidoClienteService(pedidos, clientes, proveedores, solicitudes)


def get_solicitud_service(
    solicitudes: Annotated[SqlAlchemySolicitudPresupuestoRepository, Depends(get_solicitud_repo)],
    proveedores: Annotated[SqlAlchemyProveedorRepository, Depends(get_proveedor_repo)],
    pedidos: Annotated[SqlAlchemyPedidoClienteRepository, Depends(get_pedido_cliente_repo)],
    ordenes_compra: Annotated[SqlAlchemyOrdenCompraRepository, Depends(get_orden_compra_repo)],
) -> SolicitudPresupuestoService:
    return SolicitudPresupuestoService(solicitudes, proveedores, pedidos, ordenes_compra)


def get_orden_compra_service(
    ordenes: Annotated[SqlAlchemyOrdenCompraRepository, Depends(get_orden_compra_repo)],
    productos: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
    movimientos: Annotated[SqlAlchemyMovimientoInventarioRepository, Depends(get_movimiento_repo)],
    pedidos: Annotated[SqlAlchemyPedidoClienteRepository, Depends(get_pedido_cliente_repo)],
) -> OrdenCompraService:
    return OrdenCompraService(ordenes, productos, movimientos, pedidos)


def get_orden_envio_service(
    ordenes: Annotated[SqlAlchemyOrdenEnvioRepository, Depends(get_orden_envio_repo)],
    productos: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
    movimientos: Annotated[SqlAlchemyMovimientoInventarioRepository, Depends(get_movimiento_repo)],
    pedidos: Annotated[SqlAlchemyPedidoClienteRepository, Depends(get_pedido_cliente_repo)],
) -> OrdenEnvioService:
    return OrdenEnvioService(ordenes, productos, movimientos, pedidos)


def get_inventario_service(
    productos: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
    movimientos: Annotated[SqlAlchemyMovimientoInventarioRepository, Depends(get_movimiento_repo)],
) -> InventarioService:
    return InventarioService(productos, movimientos)


def get_caja_service(
    turnos: Annotated[SqlAlchemyCajaTurnoRepository, Depends(get_caja_turno_repo)],
    ventas: Annotated[SqlAlchemyVentaMostradorRepository, Depends(get_venta_mostrador_repo)],
    productos: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
    movimientos: Annotated[SqlAlchemyMovimientoInventarioRepository, Depends(get_movimiento_repo)],
) -> CajaService:
    return CajaService(turnos, ventas, productos, movimientos)


def get_dashboard_service(
    pedidos: Annotated[SqlAlchemyPedidoClienteRepository, Depends(get_pedido_cliente_repo)],
    solicitudes: Annotated[SqlAlchemySolicitudPresupuestoRepository, Depends(get_solicitud_repo)],
    ordenes_compra: Annotated[SqlAlchemyOrdenCompraRepository, Depends(get_orden_compra_repo)],
    ordenes_envio: Annotated[SqlAlchemyOrdenEnvioRepository, Depends(get_orden_envio_repo)],
    productos: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
) -> DashboardService:
    return DashboardService(pedidos, solicitudes, ordenes_compra, ordenes_envio, productos)


# --- "Usuario actual" sin login: siempre el usuario demo sembrado ---------------------

def get_current_user(usuarios: Annotated[SqlAlchemyUsuarioRepository, Depends(get_usuario_repo)]) -> Usuario:
    usuario = usuarios.get_by_email(DEMO_USER_EMAIL)
    if usuario is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Falta el usuario demo. Corré `python seed.py` para sembrar los datos de ejemplo.",
        )
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]

# El MVP no distingue permisos por rol (no hay sesión que los transporte);
# estos alias quedan solo para que los routers lean con intención ("esta
# acción normalmente la hace Compras/Depósito/Admin") sin bloquear a nadie.
RequireAnkorUser = CurrentUser
RequireProveedor = CurrentUser
RequireAdmin = CurrentUser
