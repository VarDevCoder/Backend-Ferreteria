"""Caso de uso: autenticación (CU-01 Iniciar sesión, registro de cuentas)."""
from app.domain.entities import Usuario
from app.domain.enums import RolUsuario
from app.domain.exceptions import ConflictoDeUnicidad, CredencialesInvalidas, UsuarioInactivo
from app.domain.repositories import UsuarioRepository
from app.infrastructure.security.jwt_handler import create_access_token
from app.infrastructure.security.password_hasher import hash_password, verify_password


class AuthService:
    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    def registrar(self, name: str, email: str, password: str) -> tuple[Usuario, str]:
        """Alta pública: siempre crea un usuario con rol `ankor_user`, igual que el
        registro original de Laravel. Los proveedores y admins se crean por otra vía."""
        if self._usuarios.get_by_email(email) is not None:
            raise ConflictoDeUnicidad("Ya existe una cuenta con ese email")

        usuario = Usuario(
            id=None, name=name, email=email, password_hash=hash_password(password), rol=RolUsuario.ANKOR_USER,
        )
        usuario = self._usuarios.add(usuario)
        return usuario, self._emitir_token(usuario)

    def iniciar_sesion(self, email: str, password: str) -> tuple[Usuario, str]:
        usuario = self._usuarios.get_by_email(email)
        if usuario is None or not verify_password(password, usuario.password_hash):
            raise CredencialesInvalidas()
        if not usuario.activo:
            raise UsuarioInactivo()
        return usuario, self._emitir_token(usuario)

    @staticmethod
    def _emitir_token(usuario: Usuario) -> str:
        return create_access_token(subject=str(usuario.id), extra_claims={"rol": usuario.rol.value})
