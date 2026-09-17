"""Configuración de la aplicación, leída desde variables de entorno.

Un único punto de verdad para todo lo configurable: URL de base de datos y
orígenes permitidos de CORS. Sin login no hay secretos que manejar. Nada de
valores mágicos repartidos por el código.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ANKOR API"
    environment: str = "development"

    # Postgres (Neon en producción). Ej:
    # postgresql+pg8000://usuario:password@host/dbname?ssl_context=true
    database_url: str = "postgresql+pg8000://ankor:ankor@localhost:5432/ankor"

    # CORS: dominios del frontend (Netlify) autorizados a llamar la API
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
