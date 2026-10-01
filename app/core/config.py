"""Configuración de la aplicación, leída desde variables de entorno.

Un único punto de verdad para todo lo configurable: URL de base de datos,
orígenes permitidos de CORS y la clave con la que se firman las sesiones.
Nada de valores mágicos repartidos por el código.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


_SECRET_KEY_DESARROLLO = "clave-de-desarrollo-no-usar-en-produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Ferretería API"
    environment: str = "development"

    # Postgres (Neon en producción). Ej:
    # postgresql+pg8000://usuario:password@host/dbname?ssl_context=true
    database_url: str = "postgresql+pg8000://ankor:ankor@localhost:5432/ankor"

    # CORS: dominios del frontend (Netlify) autorizados a llamar la API
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # Clave para firmar los tokens de sesión (JWT). En producción es obligatorio
    # definirla con un valor largo y aleatorio: quien la conozca puede emitir
    # sesiones válidas para cualquier usuario.
    secret_key: str = _SECRET_KEY_DESARROLLO
    # Duración de la sesión: un turno de trabajo largo.
    access_token_minutes: int = 12 * 60

    # Si es True, `seed.py` carga datos de ejemplo (productos, clientes, un
    # usuario demo). Para una empresa real dejarlo en False: el primer ingreso
    # al sistema pide crear la empresa y el usuario administrador.
    seed_demo: bool = False

    @property
    def es_produccion(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.es_produccion and settings.secret_key == _SECRET_KEY_DESARROLLO:
        raise RuntimeError(
            "Falta SECRET_KEY: en producción hay que definir una clave propia y aleatoria "
            "(ej. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`)."
        )
    return settings
