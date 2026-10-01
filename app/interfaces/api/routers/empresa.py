"""Datos de la empresa y configuración inicial del sistema.

`GET /empresa` y `/configuracion-inicial` son públicos: la pantalla de
ingreso necesita mostrar el nombre de la ferretería, y una instalación
nueva todavía no tiene usuarios con los que autenticarse.
"""
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.permisos import Modulo
from app.application.services.empresa_service import EmpresaService
from app.infrastructure.security.tokens import crear_token
from app.interfaces.api.deps import get_empresa_service, requiere_modulo
from app.interfaces.api.schemas.auth import SesionUsuarioResponse, TokenResponse
from app.interfaces.api.schemas.empresa import (
    ConfiguracionInicialInput,
    EmpresaResponse,
    EmpresaUpdate,
    EstadoConfiguracionResponse,
)

router = APIRouter(tags=["Empresa"])

EmpresaSvc = Annotated[EmpresaService, Depends(get_empresa_service)]


@router.get("/empresa", response_model=EmpresaResponse, summary="Datos públicos de la empresa (nombre, moneda, ticket)")
def obtener_empresa(servicio: EmpresaSvc) -> EmpresaResponse:
    return EmpresaResponse(**asdict(servicio.obtener()))


@router.put("/empresa", response_model=EmpresaResponse, dependencies=[Depends(requiere_modulo(Modulo.EMPRESA))])
def actualizar_empresa(datos: EmpresaUpdate, servicio: EmpresaSvc) -> EmpresaResponse:
    return EmpresaResponse(**asdict(servicio.actualizar(**datos.model_dump())))


@router.get("/configuracion-inicial", response_model=EstadoConfiguracionResponse)
def estado_configuracion(servicio: EmpresaSvc) -> EstadoConfiguracionResponse:
    return EstadoConfiguracionResponse(requiere_configuracion=servicio.requiere_configuracion())


@router.post(
    "/configuracion-inicial", response_model=TokenResponse, status_code=201,
    summary="Primer uso: registra la empresa y su administrador (solo funciona si no hay usuarios)",
)
def configuracion_inicial(datos: ConfiguracionInicialInput, servicio: EmpresaSvc) -> TokenResponse:
    admin = servicio.configurar_primer_uso(
        datos.empresa.model_dump(), datos.admin.name, datos.admin.email, datos.admin.password
    )
    token, expira = crear_token(admin.id)
    return TokenResponse(access_token=token, expires_in=expira, usuario=SesionUsuarioResponse.desde_entidad(admin))
