from datetime import datetime

from pydantic import BaseModel, Field

from app.application.permisos import modulos_modificables
from app.domain.enums import RolUsuario

_ROLES_INTERNOS = "admin | encargado | vendedor | deposito"


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class CambiarPasswordInput(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=255)


class UsuarioResponse(BaseModel):
    id: int
    name: str
    email: str
    rol: str
    activo: bool
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, u) -> "UsuarioResponse":
        return cls(id=u.id, name=u.name, email=u.email, rol=u.rol.value, activo=u.activo, created_at=u.created_at)


class SesionUsuarioResponse(UsuarioResponse):
    # Módulos que el rol puede modificar: el frontend los usa para ocultar
    # acciones no permitidas (la validación real la hace el backend).
    permisos: list[str]

    @classmethod
    def desde_entidad(cls, u) -> "SesionUsuarioResponse":
        return cls(**UsuarioResponse.desde_entidad(u).model_dump(), permisos=modulos_modificables(u.rol))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: SesionUsuarioResponse


class UsuarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    rol: RolUsuario = Field(description=_ROLES_INTERNOS)


class UsuarioUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    rol: RolUsuario = Field(description=_ROLES_INTERNOS)
    activo: bool = True


class RestablecerPasswordInput(BaseModel):
    password_nueva: str = Field(min_length=8, max_length=255)
