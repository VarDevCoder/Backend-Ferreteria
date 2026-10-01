"""Entrypoint para Vercel: expone la app FastAPI como función serverless.

Vercel ejecuta los archivos de `api/` como funciones; `vercel.json` reescribe
todas las rutas hacia aquí, así `/docs`, `/api/v1/...` y `/` llegan a FastAPI.

Antes de cargar la app aplica las migraciones pendientes, así un `git push`
alcanza para desplegar una versión con cambios de esquema. Se desactiva con
AUTO_MIGRATE=false (por ejemplo, para migrar a mano en una ventana de
mantenimiento).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if os.environ.get("AUTO_MIGRATE", "true").lower() != "false":
    from app.infrastructure.db.migraciones import aplicar_migraciones  # noqa: E402

    aplicar_migraciones()

from app.main import app  # noqa: E402,F401
