"""Administración de las cuentas del personal (solo admin)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.usuario_service import UsuarioService
from app.interfaces.api.deps import CurrentUser, get_usuario_service
from app.interfaces.api.schemas.auth import RestablecerPasswordInput, UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.interfaces.api.schemas.common import Mensaje

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

UsuarioSvc = Annotated[UsuarioService, Depends(get_usuario_service)]


@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(servicio: UsuarioSvc) -> list[UsuarioResponse]:
    return [UsuarioResponse.desde_entidad(u) for u in servicio.listar()]


@router.post("", response_model=UsuarioResponse, status_code=201)
def crear_usuario(datos: UsuarioCreate, servicio: UsuarioSvc) -> UsuarioResponse:
    return UsuarioResponse.desde_entidad(servicio.crear(datos.name, datos.email, datos.password, datos.rol))


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(usuario_id: int, datos: UsuarioUpdate, servicio: UsuarioSvc, actor: CurrentUser) -> UsuarioResponse:
    usuario = servicio.actualizar(usuario_id, datos.name, datos.email, datos.rol, datos.activo, actor)
    return UsuarioResponse.desde_entidad(usuario)


@router.post("/{usuario_id}/restablecer-password", response_model=Mensaje)
def restablecer_password(usuario_id: int, datos: RestablecerPasswordInput, servicio: UsuarioSvc) -> Mensaje:
    servicio.restablecer_password(usuario_id, datos.password_nueva)
    return Mensaje(mensaje="Contraseña restablecida. Comunicásela al usuario para que la cambie al ingresar")
