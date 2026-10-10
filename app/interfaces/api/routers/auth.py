"""Ingreso al sistema, datos de la sesión y cambio de la propia contraseña."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.usuario_service import UsuarioService
from app.infrastructure.security.tokens import crear_token
from app.interfaces.api.deps import CurrentUser, get_usuario_service
from app.interfaces.api.schemas.auth import CambioPasswordResponse, CambiarPasswordInput, LoginInput, SesionUsuarioResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Sesión"])

UsuarioSvc = Annotated[UsuarioService, Depends(get_usuario_service)]


@router.post("/login", response_model=TokenResponse, summary="Ingresar con email y contraseña")
def login(datos: LoginInput, servicio: UsuarioSvc) -> TokenResponse:
    usuario = servicio.autenticar(datos.email, datos.password)
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
