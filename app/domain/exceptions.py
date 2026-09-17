"""Errores de dominio. No dependen de FastAPI ni de SQLAlchemy: la capa de
interfaz (routers) es la que los traduce a códigos HTTP."""


class DomainError(Exception):
    """Base de todos los errores de negocio."""


class RecursoNoEncontrado(DomainError):
    def __init__(self, recurso: str, identificador: object):
        super().__init__(f"{recurso} {identificador!r} no fue encontrado")
        self.recurso = recurso
        self.identificador = identificador


class ConflictoDeUnicidad(DomainError):
    """Ej: código de producto, RUC o email duplicado."""


class TransicionDeEstadoInvalida(DomainError):
    """Se intentó mover un documento a un estado que no le corresponde desde
    su estado actual (ej. despachar una orden que no está LISTO)."""


class StockInsuficiente(DomainError):
    def __init__(self, producto_nombre: str, disponible, requerido):
        super().__init__(
            f"Stock insuficiente para {producto_nombre}. "
            f"Disponible: {disponible}, requerido: {requerido}"
        )


class CredencialesInvalidas(DomainError):
    def __init__(self):
        super().__init__("El usuario o la contraseña no son correctos")


class UsuarioInactivo(DomainError):
    def __init__(self):
        super().__init__("La cuenta fue desactivada. Contactá al administrador")


class PermisoDenegado(DomainError):
    def __init__(self, mensaje: str = "No tenés permiso para realizar esta acción"):
        super().__init__(mensaje)


class SolicitudInvalida(DomainError):
    """Error de validación de entrada que no encaja en las categorías anteriores."""
