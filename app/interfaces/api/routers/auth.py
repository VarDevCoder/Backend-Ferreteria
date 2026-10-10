"""Ingreso al sistema, datos de la sesión y cambio de la propia contraseña."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.services.usuario_service import UsuarioService
from app.core.config import get_settings
from app.infrastructure.security.tokens import crear_token
from app.interfaces.api.deps import CurrentUser, get_usuario_service
from app.interfaces.api.schemas.auth import CambioPasswordResponse, CambiarPasswordInput, LoginInput, SesionUsuarioResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Sesión"])

UsuarioSvc = Annotated[UsuarioService, Depends(get_usuario_service)]


def ip_del_cliente(request: Request) -> str | None:
    """En Vercel la IP real del cliente es la primera de X-Forwarded-For (Vercel
    la sobrescribe, el cliente no puede inventarla). Sin esa cabecera
    (desarrollo local), la de la conexión."""
    reenviada = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if reenviada and get_settings().ip_desde_x_forwarded_for:
        return reenviada[:64]
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse, summary="Ingresar con email y contraseña")
def login(datos: LoginInput, servicio: UsuarioSvc, request: Request) -> TokenResponse:
    usuario = servicio.autenticar(datos.email, datos.password, ip_del_cliente(request))
    token, expira = crear_token(usuario.id, usuario.version_sesion)
    return TokenResponse(access_token=token, expires_in=expira, usuario=SesionUsuarioResponse.desde_entidad(usuario))


@router.get("/me", response_model=SesionUsuarioResponse, summary="Usuario de la sesión actual y sus permisos")
def yo(usuario: CurrentUser) -> SesionUsuarioResponse:
    return SesionUsuarioResponse.desde_entidad(usuario)


@router.post("/cambiar-password", response_model=CambioPasswordResponse,
             summary="Cambia la propia contraseña: cierra las demás sesiones y devuelve un token nuevo")
def cambiar_password(datos: CambiarPasswordInput, servicio: UsuarioSvc, usuario: CurrentUser) -> CambioPasswordResponse:
    usuario = servicio.cambiar_password(usuario, datos.password_actual, datos.password_nueva)
    token, expira = crear_token(usuario.id, usuario.version_sesion)
    return CambioPasswordResponse(mensaje="Contraseña actualizada", access_token=token, expires_in=expira)
