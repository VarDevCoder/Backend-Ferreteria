import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context

# Permite importar `app.*` al correr `alembic` desde la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine_args  # noqa: E402

# Identificador arbitrario (fijo) del lock de migraciones.
_LOCK_MIGRACIONES = 7_301_955

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# La URL real sale de la configuración de la app (variables de entorno / .env),
# no del alembic.ini, para no duplicar el secreto de conexión en dos lugares.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Al migrar desde la app (Vercel) no se toca el logging del servidor.
if config.config_file_name is not None and config.attributes.get("configurar_logging", True):
    fileConfig(config.config_file_name)

# Metadata de nuestros modelos: esto es lo que habilita `alembic revision --autogenerate`.
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Mismo tratamiento de SSL que la app (pg8000 necesita un SSLContext real).
    url, connect_args = engine_args(get_settings().database_url)
    connectable = create_engine(url, connect_args=connect_args, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            # En Vercel varias instancias pueden arrancar a la vez y todas
            # intentan migrar: un lock de Postgres hace que una migre y las
            # demás esperen (y después vean que no queda nada por hacer).
            # Se libera solo al terminar la transacción.
            connection.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": _LOCK_MIGRACIONES})
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
