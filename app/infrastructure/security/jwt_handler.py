"""Emisión y verificación de JSON Web Tokens (autenticación stateless)."""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Lanza jwt.InvalidTokenError (o subclases) si el token es inválido o expiró."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
