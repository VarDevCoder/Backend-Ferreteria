"""Configuración de la aplicación, leída desde variables de entorno.

Un único punto de verdad para todo lo configurable: URL de base de datos,
orígenes permitidos de CORS y la clave con la que se firman las sesiones.
Nada de valores mágicos repartidos por el código.
"""
import hashlib
import hmac
import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


_SECRET_KEY_DESARROLLO = "clave-de-desarrollo-no-usar-en-produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SAIL API"
    environment: str = "development"

    # Postgres (Neon en producción). Ej:
    # postgresql+pg8000://usuario:password@host/dbname?ssl_context=true
    # (usuario/base "ankor" en local: nombre heredado del entorno de desarrollo)
    database_url: str = "postgresql+pg8000://ankor:ankor@localhost:5432/ankor"

    # CORS: dominios del frontend (Netlify) autorizados a llamar la API
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # Clave para firmar los tokens de sesión (JWT). En producción hay que
    # definirla con un valor largo y aleatorio: quien la conozca puede emitir
    # sesiones válidas para cualquier usuario. Si falta, ver get_settings().
    secret_key: str = _SECRET_KEY_DESARROLLO
    # Duración de la sesión: un turno de trabajo largo.
    access_token_minutes: int = 12 * 60

    # Si es True, `seed.py` carga datos de ejemplo (productos, clientes, un
    # usuario demo). Para una empresa real dejarlo en False: el primer ingreso
    # al sistema pide crear la empresa y el usuario administrador.
    seed_demo: bool = False

    # Zona horaria de la ferretería: define qué es "hoy" (ventas del día,
    # reportes por día, numeración por año). Paraguay: UTC-3 todo el año.
    zona_horaria: str = "America/Asuncion"

    # Bloqueo de login por email + IP: tomar la IP del cliente de
    # X-Forwarded-For. Correcto detrás de Vercel (que la sobrescribe); en una
    # instalación sin proxy (por ejemplo, Windows local) poner false, porque
    # ahí el cliente podría inventar esa cabecera.
    ip_desde_x_forwarded_for: bool = True

    # Servidor único: carpeta del frontend (absoluta o relativa a la raíz del
    # backend). Si está definida, `/` muestra las pantallas y la API sigue en
    # /api/v1 en el mismo origen (sin CORS). Vacía = solo API (como en Vercel
    # con el frontend en Netlify). Ver app/interfaces/web/frontend.py.
    frontend_dir: str = ""

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
        # Sin SECRET_KEY propia no usamos la clave de desarrollo (es pública,
        # está en el repo). Derivamos una estable de DATABASE_URL: es secreta
        # y es la misma en todas las instancias de Vercel, así las sesiones
        # sirven en cualquiera. Igual conviene definir SECRET_KEY: si cambia
        # la contraseña de la base, se cerrarían todas las sesiones.
        logging.getLogger(__name__).warning(
            "SECRET_KEY no está definida: se usa una clave derivada de DATABASE_URL. Definila en las variables de entorno."
        )
        derivada = hmac.new(settings.database_url.encode(), b"ferreteria-sesiones-v1", hashlib.sha256).hexdigest()
        settings.secret_key = derivada
    return settings
