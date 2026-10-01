"""Configuración de la empresa y puesta en marcha (primer uso).

Una instalación nueva arranca sin usuarios. La primera persona que abre el
sistema completa los datos de la ferretería y crea su cuenta de
administrador (`configurar_primer_uso`); a partir de ahí ese paso queda
cerrado y el resto del personal lo da de alta el admin.
"""
from dataclasses import replace

from app.domain.entities import Empresa, Usuario
from app.domain.enums import RolUsuario
from app.domain.exceptions import ConflictoDeUnicidad, SolicitudInvalida
from app.domain.repositories import EmpresaRepository, UsuarioRepository
from app.application.services.usuario_service import UsuarioService


class EmpresaService:
    def __init__(self, empresa: EmpresaRepository, usuarios: UsuarioRepository):
        self._empresa = empresa
        self._usuarios = usuarios

    def obtener(self) -> Empresa:
        return self._empresa.get()

    def actualizar(self, **datos) -> Empresa:
        empresa = replace(self._empresa.get(), **datos)
        self._validar(empresa)
        return self._empresa.save(empresa)

    def requiere_configuracion(self) -> bool:
        return self._usuarios.contar_internos() == 0

    def configurar_primer_uso(self, empresa: dict, admin_nombre: str, admin_email: str, admin_password: str) -> Usuario:
        if not self.requiere_configuracion():
            raise ConflictoDeUnicidad("El sistema ya está configurado. Ingresá con tu usuario")
        self.actualizar(**empresa)
        return UsuarioService(self._usuarios).crear(admin_nombre, admin_email, admin_password, RolUsuario.ADMIN)

    @staticmethod
    def _validar(empresa: Empresa) -> None:
        if not empresa.nombre_comercial or not empresa.nombre_comercial.strip():
            raise SolicitudInvalida("El nombre de la empresa es obligatorio")
        if not 0 <= empresa.iva_porcentaje <= 100:
            raise SolicitudInvalida("El IVA debe estar entre 0 y 100")
        if not 0 <= empresa.margen_ganancia_defecto <= 1000:
            raise SolicitudInvalida("El margen de ganancia debe estar entre 0 y 1000")
