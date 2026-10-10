"""Fecha y hora "de la ferretería".

La base guarda los momentos en UTC (sin zona: la sesión de Postgres se fija
en UTC al conectar, ver `infrastructure/db/session.py`). Lo que el negocio
llama "hoy" —ventas de hoy, numeración por año, reportes por día— se calcula
en la hora local de la empresa (por defecto America/Asuncion, UTC-3).
"""
from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import get_settings


@lru_cache
def zona() -> ZoneInfo:
    return ZoneInfo(get_settings().zona_horaria)


def ahora_utc() -> datetime:
    """Momento actual en UTC, sin zona (como se guarda en la base)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ahora_local() -> datetime:
    """Momento actual en la hora de la empresa, sin zona."""
    return datetime.now(zona()).replace(tzinfo=None)


def hoy() -> date:
    """La fecha de hoy para la ferretería (no la del servidor)."""
    return ahora_local().date()


def local_a_utc(momento: datetime) -> datetime:
    """Convierte una hora local (sin zona) a UTC sin zona, para guardarla."""
    return momento.replace(tzinfo=zona()).astimezone(timezone.utc).replace(tzinfo=None)
