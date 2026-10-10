"""Entrypoint para Vercel: expone la app FastAPI como función serverless.

Vercel ejecuta los archivos de `api/` como funciones; `vercel.json` reescribe
todas las rutas hacia aquí, así `/docs`, `/api/v1/...` y `/` llegan a FastAPI.

Antes de cargar la app aplica las migraciones pendientes, así un `git push`
alcanza para desplegar una versión con cambios de esquema. Se desactiva con
AUTO_MIGRATE=false (por ejemplo, para migrar a mano en una ventana de
mantenimiento). Con SEED_DEMO=true, además carga los datos de demostración.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if os.environ.get("AUTO_MIGRATE", "true").lower() != "false":
    from app.infrastructure.db.migraciones import aplicar_migraciones  # noqa: E402

    aplicar_migraciones()

# Base de DEMOSTRACIÓN (SEED_DEMO=true): completa los datos de ejemplo e
# historial de ventas si faltan. No hace nada si ya están. Nunca activarlo en
# la base de un cliente real (crea usuarios demo con contraseña conocida).
if os.environ.get("SEED_DEMO", "false").lower() == "true":
    import seed  # noqa: E402

    try:
        seed.main()
    except Exception:  # la demo no debe dejar la API caída por un dato de ejemplo
        import logging

        logging.getLogger(__name__).exception("No se pudieron cargar los datos de demo")

from app.main import app  # noqa: E402,F401
