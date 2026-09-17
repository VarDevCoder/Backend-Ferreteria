"""Configuración de la aplicación, leída desde variables de entorno.

Un único punto de verdad para todo lo configurable: URL de base de datos,
secretos de JWT y orígenes permitidos de CORS. Nada de valores mágicos
repartidos por el código.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ANKOR API"
    environment: str = "development"

    # Postgres (Neon en producción). Ej:
    # postgresql+pg8000://usuario:password@host/dbname?ssl=true
    database_url: str = "postgresql+pg8000://ankor:ankor@localhost:5432/ankor"

    # JWT
    secret_key: str = "change-me-in-.env-this-is-not-secure"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12 horas, cómodo para una demo

    # CORS: dominios del frontend (Netlify) autorizados a llamar la API
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
