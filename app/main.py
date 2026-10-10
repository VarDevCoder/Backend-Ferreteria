"""Punto de entrada de la API. Arma la app FastAPI, registra los routers y
traduce las excepciones de dominio a respuestas HTTP — así los routers nunca
necesitan un try/except: lanzan la excepción de negocio y este módulo decide
el código de estado."""
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.middleware.base import BaseHTTPMiddleware

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
    cuenta_corriente,
    dashboard,
    empresa,
    inventario,
    ordenes_compra,
    ordenes_envio,
    pedidos_cliente,
    reportes,
    solicitudes_presupuesto,
    stock_no_vendible,
    usuarios,
)
from app.interfaces.web.frontend import montar_frontend, resolver_directorio

settings = get_settings()
_RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

app = FastAPI(
    title=settings.app_name,
    description=(
        "API de SAIL, sistema de gestión para ferreterías: caja de mostrador, ciclo comercial "
        "pedido → cotización → compra → envío, inventario y reportes. "
        "Autenticación: `POST /api/v1/auth/login` devuelve un token que se envía como "
        "`Authorization: Bearer <token>` (botón *Authorize* de esta página)."
    ),
    version="2.0.0",
)

log = logging.getLogger(__name__)

_MENSAJE_ERROR_INESPERADO = "Ocurrió un error inesperado en el servidor. Si se repite, avisá al administrador"


async def _error_inesperado_como_json(request: Request, call_next):
    """Cualquier error no previsto responde 500 en JSON. Va *dentro* de CORS
    (se registra antes), así la respuesta lleva la cabecera CORS y la pantalla
    muestra el mensaje en vez de "No se pudo conectar con el servidor"."""
    try:
        return await call_next(request)
    except Exception:
        log.exception("Error inesperado en %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": _MENSAJE_ERROR_INESPERADO},
        )


app.add_middleware(BaseHTTPMiddleware, dispatch=_error_inesperado_como_json)
# CORS se agrega último para quedar por fuera de todo (Starlette envuelve en
# orden inverso): así también las respuestas de error llevan la cabecera.
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




def _codigo_postgres(exc: DBAPIError) -> str | None:
    detalle = getattr(exc.orig, "args", [None])[0]
    return (detalle.get("C") if isinstance(detalle, dict) else None) or getattr(exc.orig, "pgcode", None)


@app.exception_handler(DBAPIError)
def manejar_error_de_base(_request: Request, exc: DBAPIError) -> JSONResponse:
    """Red de seguridad: los servicios validan duplicados, ids y borrados con
    historial, pero si la base rechaza algo igual se responde 409/422 y no
    500. (pg8000 informa la clave foránea como ProgrammingError, por eso se
    mira el código de Postgres y no la clase.)"""
    codigo = _codigo_postgres(exc)
    if codigo == "23505":  # valor único repetido
        log.warning("Dato repetido: %s", exc.orig)
        return JSONResponse(status_code=409, content={"detail": "No se pudo guardar: el dato ya existe en otro registro"})
    if codigo in ("23503", "23502", "23514"):  # clave foránea, NOT NULL, CHECK
        log.warning("Dato inválido para la base: %s", exc.orig)
        return JSONResponse(
            status_code=422,
            content={"detail": "No se pudo guardar: algún dato hace referencia a un registro que no existe o está en uso"},
        )
    log.exception("Error de base de datos")
    return JSONResponse(status_code=500, content={"detail": _MENSAJE_ERROR_INESPERADO})


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
app.include_router(cuenta_corriente.router, prefix=API, dependencies=_protegido(Modulo.CAJA))  # cobrar deudas es tarea de caja
app.include_router(catalogo.router, prefix=API, dependencies=_protegido(Modulo.CATALOGO))
app.include_router(contactos.router, prefix=API, dependencies=_protegido())  # permisos por ruta (clientes / proveedores)
app.include_router(pedidos_cliente.router, prefix=API, dependencies=_protegido(Modulo.PEDIDOS))
app.include_router(solicitudes_presupuesto.router, prefix=API, dependencies=_protegido(Modulo.COTIZACIONES))
app.include_router(ordenes_compra.router, prefix=API, dependencies=_protegido(Modulo.ORDENES_COMPRA))
app.include_router(ordenes_envio.router, prefix=API, dependencies=_protegido(Modulo.ORDENES_ENVIO))
app.include_router(inventario.router, prefix=API, dependencies=_protegido(Modulo.INVENTARIO))
app.include_router(stock_no_vendible.router, prefix=API, dependencies=_protegido(Modulo.INVENTARIO))

# Gestión
app.include_router(reportes.router, prefix=API, dependencies=_protegido(Modulo.REPORTES))
app.include_router(usuarios.router, prefix=API, dependencies=_protegido(Modulo.USUARIOS))


def salud(request: Request) -> dict:
    respuesta = {"status": "ok", "app": settings.app_name}
    demo = getattr(request.app.state, "demo", None)  # lo deja api/index.py (Vercel)
    if demo is not None:
        respuesta["demo"] = demo
    return respuesta


# Chequeo de salud: siempre en /api/v1/salud. En `/` también, salvo en el
# servidor único (FRONTEND_DIR), donde `/` muestra las pantallas del sistema.
app.add_api_route(f"{API}/salud", salud, methods=["GET"], tags=["Salud"], summary="Chequeo de salud")

_frontend = resolver_directorio(settings.frontend_dir, _RAIZ_PROYECTO)
if _frontend is None:
    app.add_api_route("/", salud, methods=["GET"], tags=["Salud"], summary="Chequeo de salud")
else:
    montar_frontend(app, _frontend)  # va último: lo que no es API lo atiende el frontend
