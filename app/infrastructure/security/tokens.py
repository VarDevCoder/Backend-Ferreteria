"""Tokens de sesión (JWT firmado con HS256).

El token solo transporta el id del usuario: el rol y si sigue activo se
leen de la base en cada request, así que desactivar a alguien o cambiarle
el rol tiene efecto inmediato sin esperar a que venza su sesión.
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

_ALGORITMO = "HS256"


def crear_token(usuario_id: int, version_sesion: int = 0) -> tuple[str, int]:
    """Devuelve (token, segundos de validez). `version_sesion` es la del
    usuario al emitirlo: si después cambia (nueva contraseña), el token deja de valer."""
    settings = get_settings()
    duracion = timedelta(minutes=settings.access_token_minutes)
    ahora = datetime.now(timezone.utc)
    payload = {"sub": str(usuario_id), "ver": version_sesion, "iat": ahora, "exp": ahora + duracion}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITMO), int(duracion.total_seconds())


def leer_token(token: str) -> tuple[int, int] | None:
    """(id del usuario, versión de sesión) si el token es válido y no venció;
    None si no. Los tokens anteriores a la versión de sesión cuentan como 0."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[_ALGORITMO])
        return int(payload["sub"]), int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
