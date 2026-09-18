"""Motor y sesiones de SQLAlchemy."""
import ssl
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _build_engine(database_url: str):
    """pg8000 exige un ssl.SSLContext real, no el string de la URL.

    Neon requiere TLS. Si la URL trae `ssl`/`ssl_context` en la query (como en
    los ejemplos del .env), lo quitamos de ahí y lo pasamos como connect_args
    para que pg8000 reciba el objeto que realmente espera.
    """
    url = make_url(database_url)
    query = dict(url.query)
    wants_ssl = query.pop("ssl", None) or query.pop("ssl_context", None)
    connect_args = {}
    if url.drivername.startswith("postgresql+pg8000") and wants_ssl:
        connect_args["ssl_context"] = ssl.create_default_context()
    url = url.set(query=query)
    return create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)


engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI: una sesión por request, cerrada siempre al final.

    Comitea al terminar el request sin errores (los repositorios solo hacen
    `flush`, para exponer los IDs generados sin persistir todavía) y revierte
    si hubo una excepción, para no dejar cambios parciales a mitad de un caso
    de uso con varios pasos (ej. una venta que ya descontó stock de un
    producto y falla en el siguiente).
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
