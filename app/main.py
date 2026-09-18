"""Punto de entrada de la API. Arma la app FastAPI, registra los routers y
traduce las excepciones de dominio a respuestas HTTP — así los routers nunca
necesitan un try/except: lanzan la excepción de negocio y este módulo decide
el código de estado."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.interfaces.api.routers import (
    caja,
    catalogo,
    contactos,
    dashboard,
    inventario,
    ordenes_compra,
    ordenes_envio,
    pedidos_cliente,
    solicitudes_presupuesto,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API del ERP de distribución ANKOR — ciclo comercial pedido → cotización → compra → envío.",
    version="1.0.0",
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


app.include_router(catalogo.router, prefix="/api/v1")
app.include_router(contactos.router, prefix="/api/v1")
app.include_router(pedidos_cliente.router, prefix="/api/v1")
app.include_router(solicitudes_presupuesto.router, prefix="/api/v1")
app.include_router(ordenes_compra.router, prefix="/api/v1")
app.include_router(ordenes_envio.router, prefix="/api/v1")
app.include_router(inventario.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(caja.router, prefix="/api/v1")


@app.get("/", tags=["Salud"], summary="Chequeo de salud")
def salud() -> dict:
    return {"status": "ok", "app": settings.app_name}
