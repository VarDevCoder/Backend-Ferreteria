"""Punto de entrada de la API. Arma la app FastAPI, registra los routers y
traduce las excepciones de dominio a respuestas HTTP — así los routers nunca
necesitan un try/except: lanzan la excepción de negocio y este módulo decide
el código de estado."""
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.permisos import Modulo
from app.core.config import get_settings
from app.domain.exceptions import (
    ConflictoDeUnicidad,
    CredencialesInvalidas,
    DomainError,
    PermisoDenegado,
    RecursoNoEncontrado,
    SolicitudInvalida,
    StockInsuficiente,
    TransicionDeEstadoInvalida,
    UsuarioInactivo,
)
from app.interfaces.api.deps import get_current_user, requiere_modulo
from app.interfaces.api.routers import (
    auth,
    caja,
    catalogo,
    contactos,
    dashboard,
    empresa,
    inventario,
    ordenes_compra,
    ordenes_envio,
    pedidos_cliente,
    reportes,
    solicitudes_presupuesto,
    usuarios,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "API del sistema de gestión para ferreterías: caja de mostrador, ciclo comercial "
        "pedido → cotización → compra → envío, inventario y reportes. "
        "Autenticación: `POST /api/v1/auth/login` devuelve un token que se envía como "
        "`Authorization: Bearer <token>` (botón *Authorize* de esta página)."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ERROR_STATUS = {
    RecursoNoEncontrado: 404,
    ConflictoDeUnicidad: 409,
    TransicionDeEstadoInvalida: 409,
    StockInsuficiente: 409,
    CredencialesInvalidas: 401,
    UsuarioInactivo: 403,
    PermisoDenegado: 403,
    SolicitudInvalida: 422,
}


@app.exception_handler(DomainError)
def manejar_error_de_dominio(_request: Request, exc: DomainError) -> JSONResponse:
    status_code = next((codigo for tipo, codigo in _ERROR_STATUS.items() if isinstance(exc, tipo)), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})




def _protegido(modulo: Modulo | None = None) -> list:
    """Todo router de negocio exige sesión; con `modulo`, además, permisos por rol."""
    return [Depends(requiere_modulo(modulo))] if modulo else [Depends(get_current_user)]


API = "/api/v1"

# Públicos (o con su propia protección por ruta)
app.include_router(auth.router, prefix=API)
app.include_router(empresa.router, prefix=API)

# Operación
app.include_router(dashboard.router, prefix=API, dependencies=_protegido())
app.include_router(caja.router, prefix=API, dependencies=_protegido(Modulo.CAJA))
app.include_router(catalogo.router, prefix=API, dependencies=_protegido(Modulo.CATALOGO))
app.include_router(contactos.router, prefix=API, dependencies=_protegido())  # permisos por ruta (clientes / proveedores)
app.include_router(pedidos_cliente.router, prefix=API, dependencies=_protegido(Modulo.PEDIDOS))
app.include_router(solicitudes_presupuesto.router, prefix=API, dependencies=_protegido(Modulo.COTIZACIONES))
app.include_router(ordenes_compra.router, prefix=API, dependencies=_protegido(Modulo.ORDENES_COMPRA))
app.include_router(ordenes_envio.router, prefix=API, dependencies=_protegido(Modulo.ORDENES_ENVIO))
app.include_router(inventario.router, prefix=API, dependencies=_protegido(Modulo.INVENTARIO))

# Gestión
app.include_router(reportes.router, prefix=API, dependencies=_protegido(Modulo.REPORTES))
app.include_router(usuarios.router, prefix=API, dependencies=_protegido(Modulo.USUARIOS))


@app.get("/", tags=["Salud"], summary="Chequeo de salud")
def salud() -> dict:
    return {"status": "ok", "app": settings.app_name}
