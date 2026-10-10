"""Entrypoint para Vercel: expone la app FastAPI como función serverless.

Vercel ejecuta los archivos de `api/` como funciones; `vercel.json` reescribe
todas las rutas hacia aquí, así `/docs`, `/api/v1/...` y `/` llegan a FastAPI.

Antes de cargar la app aplica las migraciones pendientes, así un `git push`
alcanza para desplegar una versión con cambios de esquema. Se desactiva con
AUTO_MIGRATE=false (por ejemplo, para migrar a mano en una ventana de
mantenimiento). Con SEED_DEMO=true, además carga los datos de demostración.

La demo pública (el proyecto de Vercel cuyo dominio está en DOMINIOS_DEMO)
carga sus datos sola, sin configurar nada: Vercel informa el dominio en
VERCEL_PROJECT_PRODUCTION_URL. Las instancias de clientes son otros proyectos,
con otro dominio, así que no les afecta. SEED_DEMO=false la desactiva igual.
El resultado se ve en `GET /` (clave "demo").
"""
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if os.environ.get("AUTO_MIGRATE", "true").lower() != "false":
    from app.infrastructure.db.migraciones import aplicar_migraciones  # noqa: E402

    aplicar_migraciones()

# Base de DEMOSTRACIÓN: completa los datos de ejemplo e historial de ventas si
# faltan (no hace nada si ya están). Nunca en la base de un cliente real: crea
# usuarios demo con contraseña conocida.
DOMINIOS_DEMO = ("ankor-backend.vercel.app",)  # dominio histórico de la demo pública de SAIL

_seed_demo = os.environ.get("SEED_DEMO", "").strip().lower()
_es_demo_publica = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "").strip().lower() in DOMINIOS_DEMO
ESTADO_DEMO: dict = {"activa": _seed_demo == "true" or (_seed_demo != "false" and _es_demo_publica)}

if ESTADO_DEMO["activa"]:
    import seed  # noqa: E402

    inicio = time.monotonic()
    try:
        seed.main(migrar=False, forzar_demo=True)  # las migraciones ya corrieron arriba (o se manejan a mano)
        ESTADO_DEMO["resultado"] = "cargada"
    except Exception as error:  # la demo no debe dejar la API caída por un dato de ejemplo
        logging.getLogger(__name__).exception("No se pudieron cargar los datos de demo")
        ESTADO_DEMO["resultado"] = "error"
        ESTADO_DEMO["error"] = f"{type(error).__name__}: {str(error)[:200]}"
    ESTADO_DEMO["segundos"] = round(time.monotonic() - inicio, 1)

from app.main import app  # noqa: E402

app.state.demo = ESTADO_DEMO
