"""Aplica las migraciones de Alembic desde la propia app.

En Vercel no hay un paso de "build" con acceso a la base ni una consola
donde correr `alembic upgrade head`: el entrypoint (`api/index.py`) llama a
esto al arrancar cada instancia. Si la base ya está al día, solo lee la
versión y sigue. `alembic/env.py` toma un lock de Postgres para que dos
instancias que arrancan juntas no migren a la vez.
"""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

_RAIZ = Path(__file__).resolve().parents[3]

log = logging.getLogger(__name__)


def aplicar_migraciones() -> None:
    config = Config(str(_RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(_RAIZ / "alembic"))
    config.attributes["configurar_logging"] = False
    log.info("Aplicando migraciones pendientes (alembic upgrade head)")
    command.upgrade(config, "head")
