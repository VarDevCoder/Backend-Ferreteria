"""Entrypoint para Vercel: expone la app FastAPI como función serverless.

Vercel ejecuta los archivos de `api/` como funciones; `vercel.json` reescribe
todas las rutas hacia aquí, así `/docs`, `/api/v1/...` y `/` llegan a FastAPI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401
