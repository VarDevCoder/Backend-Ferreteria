"""Hashing de contraseñas con PBKDF2-HMAC-SHA256 (librería estándar de Python).

Se evita deliberadamente `bcrypt`/`argon2` porque son extensiones nativas en C
y este proyecto corre sobre una versión de Python muy reciente donde esas
librerías todavía no siempre publican binarios (`wheels`) compatibles. PBKDF2
vía `hashlib` es parte del standard library, funciona en cualquier entorno y
con suficientes iteraciones es un algoritmo aceptable para este MVP.
"""
import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, hex_digest = password_hash.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(digest.hex(), hex_digest)
    except (ValueError, AttributeError):
        return False
