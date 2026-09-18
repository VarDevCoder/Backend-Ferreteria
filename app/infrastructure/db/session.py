"""Motor y sesiones de SQLAlchemy."""
import ssl
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_SSL_PARAMS = ("ssl_context", "ssl")
_SSL_ACTIVO = {"true", "1", "require"}


def engine_args(database_url: str) -> tuple[URL, dict[str, Any]]:
    """Separa el flag SSL de la URL y lo convierte en un SSLContext real.

    pg8000 espera `ssl_context` como objeto `ssl.SSLContext`; si se deja
    `?ssl_context=true` en la URL, le llega el string "true" y la conexión a
    Neon falla con `'str' object has no attribute 'wrap_socket'`.
    """
    url = make_url(database_url)
    connect_args: dict[str, Any] = {}
    flag = next((url.query[p] for p in _SSL_PARAMS if p in url.query), None)
    if flag is not None:
        url = url.difference_update_query(_SSL_PARAMS)
        if str(flag).lower() in _SSL_ACTIVO:
            connect_args["ssl_context"] = ssl.create_default_context()
    return url, connect_args


settings = get_settings()

_url, _connect_args = engine_args(settings.database_url)
engine = create_engine(_url, connect_args=_connect_args, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI: una sesión por request, cerrada siempre al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
