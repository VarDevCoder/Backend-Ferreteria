"""Casos de uso de cuentas del personal: ingreso, cambio de contraseña y
administración de usuarios (solo admin)."""
from app.domain.entities import Usuario
from app.domain.enums import RolUsuario
from app.domain.exceptions import (
    ConflictoDeUnicidad,
    CredencialesInvalidas,
    PermisoDenegado,
    RecursoNoEncontrado,
    SolicitudInvalida,
    UsuarioInactivo,
)
from app.domain.repositories import IntentoLoginRepository, UsuarioRepository
from app.infrastructure.security.password_hasher import hash_password, verify_password

LARGO_MINIMO_PASSWORD = 8


class LimiteDeIntentos:
    """Frena la fuerza bruta: tras N contraseñas incorrectas para un mismo
    email dentro de la ventana, bloquea ese email hasta que pase el tiempo."""

    MAX_INTENTOS = 5
    VENTANA_SEGUNDOS = 5 * 60

    def __init__(self, intentos: IntentoLoginRepository):
        self._intentos = intentos

    def verificar(self, email: str) -> None:
        if self._intentos.contar_recientes(email, self.VENTANA_SEGUNDOS) >= self.MAX_INTENTOS:
            raise PermisoDenegado("Demasiados intentos fallidos. Esperá unos minutos y volvé a probar")

    def registrar_fallo(self, email: str) -> None:
        self._intentos.registrar_fallo(email)

    def limpiar(self, email: str) -> None:
        self._intentos.limpiar(email, self.VENTANA_SEGUNDOS)


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def validar_password(password: str) -> None:
    if len(password) < LARGO_MINIMO_PASSWORD:
        raise SolicitudInvalida(f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres")


class UsuarioService:
    def __init__(self, usuarios: UsuarioRepository, intentos: IntentoLoginRepository | None = None):
        self._usuarios = usuarios
        # Solo el login lo necesita; el resto de los casos de uso no.
        self._limite = LimiteDeIntentos(intentos) if intentos is not None else None

    # --- Sesión --------------------------------------------------------------

    def autenticar(self, email: str, password: str) -> Usuario:
        email = normalizar_email(email)
        if self._limite is None:
            raise RuntimeError("UsuarioService.autenticar requiere el repositorio de intentos de login")
        self._limite.verificar(email)
        usuario = self._usuarios.get_by_email(email)
        if usuario is None or not verify_password(password, usuario.password_hash):
            self._limite.registrar_fallo(email)
            raise CredencialesInvalidas()
        if not usuario.es_interno():
            # Los proveedores tienen cuenta (para un futuro portal) pero no
            # entran al sistema interno de la ferretería.
            raise PermisoDenegado("Esta cuenta no tiene acceso al sistema de gestión")
        if not usuario.activo:
            raise UsuarioInactivo()
        self._limite.limpiar(email)
        return usuario

    def cambiar_password(self, usuario: Usuario, actual: str, nueva: str) -> None:
        if not verify_password(actual, usuario.password_hash):
            raise CredencialesInvalidas()
        validar_password(nueva)
        usuario.password_hash = hash_password(nueva)
        self._usuarios.update(usuario)

    # --- Administración (admin) ----------------------------------------------

    def listar(self) -> list[Usuario]:
        return self._usuarios.list_internos()

    def obtener(self, usuario_id: int) -> Usuario:
        usuario = self._usuarios.get_by_id(usuario_id)
        if usuario is None or not usuario.es_interno():
            raise RecursoNoEncontrado("Usuario", usuario_id)
        return usuario

    def crear(self, name: str, email: str, password: str, rol: RolUsuario) -> Usuario:
        email = normalizar_email(email)
        self._validar_rol(rol)
        validar_password(password)
        if self._usuarios.get_by_email(email) is not None:
            raise ConflictoDeUnicidad(f"Ya existe un usuario con el email {email}")
        return self._usuarios.add(
            Usuario(id=None, name=name.strip(), email=email, password_hash=hash_password(password), rol=rol)
        )

    def actualizar(self, usuario_id: int, name: str, email: str, rol: RolUsuario, activo: bool, actor: Usuario) -> Usuario:
        usuario = self.obtener(usuario_id)
        email = normalizar_email(email)
        self._validar_rol(rol)
        otro = self._usuarios.get_by_email(email)
        if otro is not None and otro.id != usuario.id:
            raise ConflictoDeUnicidad(f"Ya existe un usuario con el email {email}")
        if usuario.id == actor.id and (rol != RolUsuario.ADMIN or not activo):
            raise SolicitudInvalida("No podés quitarte el rol de administrador ni desactivar tu propia cuenta")
        if usuario.es_admin() and usuario.activo and (rol != RolUsuario.ADMIN or not activo):
            self._asegurar_otro_admin_activo()

        usuario.name = name.strip()
        usuario.email = email
        usuario.rol = rol
        usuario.activo = activo
        return self._usuarios.update(usuario)

    def restablecer_password(self, usuario_id: int, nueva: str) -> Usuario:
        usuario = self.obtener(usuario_id)
        validar_password(nueva)
        usuario.password_hash = hash_password(nueva)
        return self._usuarios.update(usuario)

    def _asegurar_otro_admin_activo(self) -> None:
        if self._usuarios.contar_internos(RolUsuario.ADMIN, solo_activos=True) <= 1:
            raise SolicitudInvalida("Tiene que quedar al menos un administrador activo")

    @staticmethod
    def _validar_rol(rol: RolUsuario) -> None:
        if rol not in RolUsuario.internos():
            raise SolicitudInvalida("Rol inválido para un usuario del personal")
