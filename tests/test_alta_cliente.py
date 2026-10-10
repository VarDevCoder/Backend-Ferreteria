"""Herramienta de alta de clientes en la nube y cadenas de conexión de Neon."""
import importlib.util
from pathlib import Path

from app.infrastructure.db.session import engine_args

_RUTA = Path(__file__).resolve().parent.parent / "herramientas" / "alta_cliente.py"
_spec = importlib.util.spec_from_file_location("alta_cliente", _RUTA)
alta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alta)


def test_la_cadena_de_neon_sirve_tal_cual():
    url, connect_args = engine_args("postgresql://u:p@ep-x-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    assert url.drivername == "postgresql+pg8000"
    assert "ssl_context" in connect_args
    assert "channel_binding" not in url.query and "sslmode" not in url.query
    assert engine_args("postgres://u:p@host/db")[0].drivername == "postgresql+pg8000"


def test_normalizar_url_y_ocultar_password():
    assert alta.normalizar_url("psql 'postgresql://u:p@h/db?sslmode=require'") == "postgresql+pg8000://u:p@h/db?sslmode=require"
    assert alta._ocultar("postgresql+pg8000://usuario:secreto@h/db") == "postgresql+pg8000://usuario:****@h/db"


def test_variables_para_vercel():
    clave = alta.generar_secret_key()
    assert len(clave) >= 60 and clave != alta.generar_secret_key()
    variables = {nombre: valor for nombre, valor, _ in alta.variables_vercel("Ferretería X", clave)}
    assert variables["SECRET_KEY"] == clave
    assert variables["ENVIRONMENT"] == "production"
    assert variables["SEED_DEMO"] == "false"
    assert variables["FRONTEND_DIR"] == "frontend"
    assert variables["APP_NAME"] == "SAIL - Ferretería X"
