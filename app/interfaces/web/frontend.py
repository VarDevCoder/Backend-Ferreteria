"""Servidor único: el backend sirve también el frontend (HTML/CSS/JS sin build).

En simple: con la variable FRONTEND_DIR apuntando a la carpeta del frontend,
una sola dirección (por ejemplo http://localhost:7245 en la PC de la
ferretería, o https://cliente.sail.com.py en la nube) muestra las pantallas en
`/` y atiende la API en `/api/v1`. Como todo sale del mismo origen no hace
falta CORS.

Detalle técnico:
- Se monta un `StaticFiles` en `/` DESPUÉS de todas las rutas de la API, así
  `/api/v1/...`, `/docs` y `/redoc` siguen respondiendo igual.
- `/assets/js/env.js` se sirve con una línea agregada al final que fija
  `window.__SAIL_API_BASE__` al mismo origen. env.js es un <script> clásico
  que corre antes que los módulos, así `config.js` toma esa URL. No hace falta
  tocar el frontend: en Netlify y en local (55NN → 80NN) env.js sigue igual.
- Todo lo del frontend va con `Cache-Control: no-cache`: el navegador revalida
  con ETag (respuesta 304, liviana) y después de una actualización nadie queda
  con JavaScript viejo.
- No se sirven archivos ni carpetas ocultas (`.git`, `.github`...).
- Los tipos MIME se fijan a mano: en Windows `mimetypes` lee el registro y a
  veces devuelve `text/plain` para `.js`, y el navegador rechaza los módulos.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

log = logging.getLogger(__name__)

RUTA_ENV_JS = "assets/js/env.js"

LINEA_MISMO_ORIGEN = (
    "\n// Agregado por el servidor de SAIL (servidor único): la API está en este mismo origen.\n"
    'window.__SAIL_API_BASE__ = window.location.origin + "/api/v1";\n'
)

_TIPOS = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
}


def _registrar_tipos_mime() -> None:
    for extension, tipo in _TIPOS.items():
        mimetypes.add_type(tipo, extension)


class FrontendEstatico(StaticFiles):
    """StaticFiles con env.js generado, sin archivos ocultos y sin caché vieja."""

    def __init__(self, directorio: Path) -> None:
        super().__init__(directory=str(directorio), html=True)
        self._directorio = directorio

    async def get_response(self, path: str, scope: Scope) -> Response:
        partes = Path(path).parts
        if any(parte.startswith(".") and parte != "." for parte in partes):
            raise HTTPException(status_code=404)
        if Path(path).as_posix() == RUTA_ENV_JS and scope["method"] in ("GET", "HEAD"):
            respuesta = self._env_js()
        else:
            respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        return respuesta

    def _env_js(self) -> Response:
        archivo = self._directorio / RUTA_ENV_JS
        original = archivo.read_text(encoding="utf-8") if archivo.is_file() else ""
        return Response(original + LINEA_MISMO_ORIGEN, media_type="text/javascript")


def resolver_directorio(valor: str, raiz: Path) -> Path | None:
    """FRONTEND_DIR absoluto o relativo a la raíz del backend. None si no está definido."""
    if not valor.strip():
        return None
    directorio = Path(valor.strip())
    if not directorio.is_absolute():
        directorio = raiz / directorio
    return directorio.resolve()


def montar_frontend(app: FastAPI, directorio: Path) -> None:
    """Sirve el frontend en `/`. Llamar después de registrar todas las rutas de la API."""
    if not (directorio / "index.html").is_file():
        raise RuntimeError(
            f"FRONTEND_DIR={directorio} no tiene index.html: revisá la carpeta del frontend "
            "o borrá la variable para usar solo la API."
        )
    _registrar_tipos_mime()
    app.mount("/", FrontendEstatico(directorio), name="frontend")
    log.info("Servidor único: frontend servido desde %s", directorio)
