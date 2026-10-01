"""Raíz de composición: arma repositorios y servicios a partir de la sesión de
DB de cada request, y resuelve quién es el usuario que llama.

Autenticación: cada request trae `Authorization: Bearer <token>` (lo emite
`POST /auth/login`). `get_current_user` valida el token y vuelve a leer al
usuario de la base, así un usuario desactivado pierde el acceso al instante.

Autorización: `requiere_modulo(Modulo.X)` se aplica a nivel de router en
`main.py`. Las consultas (GET) quedan abiertas a todo el personal; crear,
modificar o cambiar de estado exige un rol habilitado para ese módulo
(ver `app.application.permisos`).
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.services.caja_service import CajaService
from app.application.services.catalogo_service import CategoriaService, ProductoService
from app.application.services.contactos_service import ClienteService, ProveedorProductoService, ProveedorService
from app.application.permisos import Modulo, puede_leer, puede_modificar
from app.application.services.dashboard_service import DashboardService
from app.application.services.empresa_service import EmpresaService
from app.application.services.inventario_service import InventarioService
from app.application.services.orden_compra_service import OrdenCompraService
from app.application.services.orden_envio_service import OrdenEnvioService
from app.application.services.pedido_cliente_service import PedidoClienteService
from app.application.services.reporte_service import ReporteService
from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.application.services.usuario_service import UsuarioService
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
from app.infrastructure.db.repositories.empresa_repository import SqlAlchemyEmpresaRepository
from app.infrastructure.db.repositories.reporte_repository import SqlAlchemyReporteRepository
from app.infrastructure.db.repositories.usuario_repository import SqlAlchemyUsuarioRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.security.tokens import leer_token

DbSession = Annotated[Session, Depends(get_db)]


# --- Repositorios ---------------------------------------------------------------

def get_usuario_repo(db: DbSession) -> SqlAlchemyUsuarioRepository:
    return SqlAlchemyUsuarioRepository(db)


def get_empresa_repo(db: DbSession) -> SqlAlchemyEmpresaRepository:
    return SqlAlchemyEmpresaRepository(db)


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


def get_producto_service(
    repo: Annotated[SqlAlchemyProductoRepository, Depends(get_producto_repo)],
    empresa: Annotated[SqlAlchemyEmpresaRepository, Depends(get_empresa_repo)],
) -> ProductoService:
    return ProductoService(repo, margen_defecto=empresa.get().margen_ganancia_defecto)


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


def get_usuario_service(usuarios: Annotated[SqlAlchemyUsuarioRepository, Depends(get_usuario_repo)]) -> UsuarioService:
    return UsuarioService(usuarios)


def get_empresa_service(
    empresa: Annotated[SqlAlchemyEmpresaRepository, Depends(get_empresa_repo)],
    usuarios: Annotated[SqlAlchemyUsuarioRepository, Depends(get_usuario_repo)],
) -> EmpresaService:
    return EmpresaService(empresa, usuarios)


def get_reporte_service(db: DbSession) -> ReporteService:
    return ReporteService(SqlAlchemyReporteRepository(db))


# --- Usuario actual y permisos ---------------------------------------------------

_bearer = HTTPBearer(auto_error=False)

_NO_AUTENTICADO = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Tu sesión no es válida o venció. Volvé a ingresar",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    usuarios: Annotated[SqlAlchemyUsuarioRepository, Depends(get_usuario_repo)],
) -> Usuario:
    if credenciales is None:
        raise _NO_AUTENTICADO
    usuario_id = leer_token(credenciales.credentials)
    usuario = usuarios.get_by_id(usuario_id) if usuario_id is not None else None
    if usuario is None or not usuario.es_interno() or not usuario.activo:
        raise _NO_AUTENTICADO
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]

_METODOS_DE_LECTURA = {"GET", "HEAD", "OPTIONS"}


def requiere_modulo(modulo: Modulo) -> Callable[..., None]:
    """Dependency de router: lectura para todo el personal (salvo módulos
    sensibles), escritura solo para los roles habilitados en el módulo."""

    def verificar(request: Request, usuario: CurrentUser) -> None:
        es_lectura = request.method in _METODOS_DE_LECTURA
        permitido = puede_leer(usuario.rol, modulo) if es_lectura else puede_modificar(usuario.rol, modulo)
        if not permitido:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu rol no tiene permiso para realizar esta acción")

    return verificar


# Alias históricos que usan los routers para obtener al usuario autenticado
# (quién generó cada documento). El control de permisos lo hace
# `requiere_modulo` a nivel de router.
RequireAnkorUser = CurrentUser
RequireProveedor = CurrentUser
RequireAdmin = CurrentUser
