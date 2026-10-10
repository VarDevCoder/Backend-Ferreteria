"""Arranca SAIL como servidor único en una PC (instalación Windows) o en
cualquier servidor propio, sin Vercel.

En simple: lee la configuración, espera a que la base de datos esté lista,
la actualiza (migraciones) y deja el sistema andando en un puerto: las
pantallas en `/` y la API en `/api/v1`.

    python servir.py --config C:\\ProgramData\\SAIL\\config\\sail.env

Detalle técnico:
- `--config` es un archivo NOMBRE=valor (como un .env). Las variables que ya
  están en el entorno tienen prioridad (sirve para pruebas).
- Host y puerto: SAIL_HOST (por defecto 127.0.0.1) y SAIL_PORT (7245).
- Espera hasta SAIL_ESPERA_BASE segundos (120) a que Postgres acepte
  conexiones: en Windows el servicio de la base puede tardar en arrancar.
- Aplica las migraciones (alembic upgrade head) salvo AUTO_MIGRATE=false.
- uvicorn corre con proxy_headers=False: en una PC sin proxy nadie puede
  hacerse pasar por otra IP con X-Forwarded-For (ver IP_DESDE_X_FORWARDED_FOR).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

log = logging.getLogger("sail.servir")


def cargar_config(ruta: Path) -> None:
    """Carga NOMBRE=valor en el entorno (sin pisar lo que ya está definido)."""
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        os.environ.setdefault(nombre.strip(), valor.strip())


def esperar_base(segundos: float) -> None:
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings
    from app.infrastructure.db.session import engine_args

    url, connect_args = engine_args(get_settings().database_url)
    engine = create_engine(url, connect_args=connect_args)
    limite = time.monotonic() + segundos
    try:
        while True:
            try:
                with engine.connect() as conexion:
                    conexion.execute(text("SELECT 1"))
                return
            except Exception as error:  # noqa: BLE001 - se reintenta hasta el límite
                if time.monotonic() > limite:
                    raise SystemExit(f"La base de datos no responde: {type(error).__name__}: {error}")
                log.info("Esperando a la base de datos...")
                time.sleep(2)
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="SAIL: servidor único (pantallas + API)")
    parser.add_argument("--config", type=Path, help="archivo NOMBRE=valor con la configuración")
    parser.add_argument("--host", help="por defecto SAIL_HOST o 127.0.0.1")
    parser.add_argument("--port", type=int, help="por defecto SAIL_PORT o 7245")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.config:
        cargar_config(args.config)
    host = args.host or os.environ.get("SAIL_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("SAIL_PORT", "7245"))

    esperar_base(float(os.environ.get("SAIL_ESPERA_BASE", "120")))
    if os.environ.get("AUTO_MIGRATE", "true").lower() != "false":
        from app.infrastructure.db.migraciones import aplicar_migraciones

        aplicar_migraciones()

    import uvicorn

    from app.main import app

    log.info("SAIL listo en http://%s:%s", "localhost" if host in ("127.0.0.1", "0.0.0.0") else host, port)
    uvicorn.run(app, host=host, port=port, proxy_headers=False, log_level="info")


if __name__ == "__main__":
    main()
