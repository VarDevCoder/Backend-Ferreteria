"""Alta de un cliente en la nube: lo que se puede automatizar.

En simple: ayuda al dueño a crear la instancia de SAIL de un cliente nuevo
(una base en Neon + un proyecto en Vercel). Genera la clave de las sesiones,
arma la lista de variables para copiar en Vercel, prueba la conexión a la
base, corre las migraciones y verifica que la instancia publicada responda.
Paso a paso completo: docs/ALTA-CLIENTE-NUBE.md.

No pide ni guarda contraseñas de las cuentas del dueño (Neon, Vercel, GitHub).
La cadena de conexión de la base se toma de la variable DATABASE_URL o se pega
en una entrada oculta; se usa en memoria y no se escribe en ningún archivo.

Uso (desde la carpeta del backend):
    python herramientas/alta_cliente.py variables --nombre "Ferretería San José"
    python herramientas/alta_cliente.py probar-base      # necesita requirements.txt instalado
    python herramientas/alta_cliente.py migrar           # idem
    python herramientas/alta_cliente.py verificar https://ferreteria-san-jose.vercel.app

`variables` y `verificar` solo usan Python (sin dependencias).
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

OK = "  [OK]"
MAL = "  [ERROR]"
OJO = "  [ATENCIÓN]"


# ---------------------------------------------------------------- variables
def generar_secret_key() -> str:
    return secrets.token_urlsafe(48)


def variables_vercel(nombre: str, secret_key: str) -> list[tuple[str, str, str]]:
    """(variable, valor, explicación) para Vercel → Settings → Environment Variables."""
    return [
        ("DATABASE_URL", "<pegar la cadena de Neon tal cual, la del host con -pooler>",
         "Conexión a la base del cliente. No la guardes en ningún otro lado."),
        ("SECRET_KEY", secret_key, "Firma las sesiones. Generada al azar; una distinta por cliente."),
        ("ENVIRONMENT", "production", "Modo producción."),
        ("SEED_DEMO", "false", "Nunca cargar la demo en un cliente real (tiene contraseñas conocidas)."),
        ("APP_NAME", f"SAIL - {nombre}", "Nombre que muestra la API."),
        ("FRONTEND_DIR", "frontend", "Servidor único: las pantallas y la API en la misma dirección (sin CORS)."),
        ("FRONTEND_TOKEN", "<token de GitHub de solo lectura del repo del frontend>",
         "Solo mientras Frontend-Ferreteria sea privado. Si se hace público, no hace falta."),
    ]


def cmd_variables(args: argparse.Namespace) -> int:
    nombre = args.nombre.strip()
    sugerido = re.sub(r"[^a-z0-9]+", "-", nombre.lower().translate(str.maketrans("áéíóúñü", "aeiounu"))).strip("-")
    print(f"\nCliente: {nombre}")
    print(f"Nombre sugerido para el proyecto en Vercel y en Neon: sail-{sugerido}\n")
    variables = variables_vercel(nombre, generar_secret_key())
    print("Qué es cada variable:\n")
    for variable, valor, explicacion in variables:
        print(f"  {variable}: {explicacion}")
    print("\nBloque para PEGAR de una vez en Vercel (pantalla de importación → Environment Variables:")
    print("pegalo en el primer casillero 'Key' y Vercel lo separa solo). Reemplazá lo que está entre < >:\n")
    print("-" * 72)
    for variable, valor, _explicacion in variables:
        print(f"{variable}={valor}")
    print("-" * 72)
    print("\nLa SECRET_KEY se muestra una sola vez y no se guarda: copiala ahora a Vercel.")
    return 0


# ---------------------------------------------------------------- base de datos
def normalizar_url(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    if url.startswith("psql "):
        url = url[5:].strip().strip("'")
    for prefijo in ("postgresql://", "postgres://"):
        if url.startswith(prefijo):
            url = "postgresql+pg8000://" + url[len(prefijo):]
    return url


def obtener_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("Pegá la cadena de conexión de Neon (no se ve al pegar y no se guarda) y Enter:")
        url = getpass.getpass("DATABASE_URL: ")
    url = normalizar_url(url)
    if not url.startswith("postgresql+pg8000://"):
        raise SystemExit(f"{MAL} La cadena tiene que empezar con postgresql:// (copiala de Neon → Connect).")
    os.environ["DATABASE_URL"] = url
    return url


def _ocultar(url: str) -> str:
    return re.sub(r"://([^:/@]+):[^@]+@", r"://\1:****@", url)


def cmd_probar_base(_args: argparse.Namespace) -> int:
    url = obtener_database_url()
    sys.path.insert(0, str(RAIZ))
    try:
        from sqlalchemy import create_engine, text

        from app.infrastructure.db.session import engine_args
    except ImportError:
        raise SystemExit(f"{MAL} Falta instalar las dependencias: pip install -r requirements.txt")
    print(f"Probando {_ocultar(url)} ...")
    destino, connect_args = engine_args(url)
    engine = create_engine(destino, connect_args=connect_args)
    try:
        with engine.connect() as conexion:
            version = conexion.execute(text("SHOW server_version")).scalar()
            tablas = conexion.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )).scalar()
            usuarios = None
            if conexion.execute(text("SELECT to_regclass('public.usuarios')")).scalar():
                usuarios = conexion.execute(text("SELECT count(*) FROM usuarios")).scalar()
    except Exception as error:  # noqa: BLE001 - se muestra al dueño tal cual
        print(f"{MAL} No se pudo conectar: {type(error).__name__}: {error}")
        return 1
    finally:
        engine.dispose()
    print(f"{OK} Conecta. PostgreSQL {version}; {tablas} tablas.")
    if usuarios:
        print(f"{OJO} Esta base YA tiene {usuarios} usuario(s): ¿es la de otro cliente? Para un cliente nuevo, la base va vacía.")
    elif tablas:
        print(f"{OK} Esquema creado y sin usuarios: lista para la configuración inicial.")
    else:
        print(f"{OK} Base vacía: el primer arranque (o `migrar`) crea las tablas.")
    return 0


def cmd_migrar(_args: argparse.Namespace) -> int:
    obtener_database_url()
    sys.path.insert(0, str(RAIZ))
    try:
        from app.infrastructure.db.migraciones import aplicar_migraciones
    except ImportError:
        raise SystemExit(f"{MAL} Falta instalar las dependencias: pip install -r requirements.txt")
    print("Aplicando migraciones (alembic upgrade head)...")
    try:
        aplicar_migraciones()
    except Exception as error:  # noqa: BLE001
        print(f"{MAL} Falló la migración: {type(error).__name__}: {error}")
        return 1
    print(f"{OK} Base al día.")
    return 0


# ---------------------------------------------------------------- verificar
def _get(url: str, timeout: float = 60) -> tuple[int, str, str]:
    pedido = urllib.request.Request(url, headers={"User-Agent": "sail-alta-cliente"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            return r.status, r.headers.get("content-type", ""), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("content-type", ""), error.read().decode("utf-8", "replace")


def verificar(base: str) -> list[tuple[str, str]]:
    """Chequeos de una instancia publicada. Devuelve (nivel, mensaje); nivel: ok | ojo | mal."""
    base = base.rstrip("/")
    resultados: list[tuple[str, str]] = []

    def chequeo(bien: bool | str, mensaje: str) -> None:
        nivel = bien if isinstance(bien, str) else ("ok" if bien else "mal")
        resultados.append((nivel, mensaje))

    try:
        estado, tipo, cuerpo = _get(f"{base}/api/v1/salud")
    except Exception as error:  # noqa: BLE001
        chequeo(False, f"No responde {base} ({type(error).__name__}: {error}). ¿Terminó el deploy en Vercel?")
        return resultados
    if estado == 404:
        estado, tipo, cuerpo = _get(f"{base}/")  # versión anterior al servidor único
    salud = json.loads(cuerpo) if "json" in tipo else {}
    chequeo(estado == 200 and salud.get("status") == "ok", f"API en línea (salud: HTTP {estado})")
    demo = salud.get("demo") or {}
    chequeo(not demo.get("activa"), "La demo NO está activa (correcto para un cliente real)" if not demo.get("activa")
            else "¡La demo está ACTIVA! Poné SEED_DEMO=false y redeployá: tiene usuarios con contraseña conocida")

    estado, tipo, cuerpo = _get(f"{base}/")
    chequeo(estado == 200 and "text/html" in tipo,
            "Las pantallas se ven en / (servidor único)" if "text/html" in tipo
            else "En / no hay pantallas: falta FRONTEND_DIR=frontend (o FRONTEND_TOKEN) y redeployar")

    estado, _tipo, cuerpo = _get(f"{base}/assets/js/env.js")
    chequeo(estado == 200 and "window.location.origin" in cuerpo,
            "El frontend usa la API de su mismo origen" if estado == 200 else f"No se encontró env.js (HTTP {estado})")

    estado, _tipo, cuerpo = _get(f"{base}/api/v1/configuracion-inicial")
    if estado == 200:
        if json.loads(cuerpo).get("requiere_configuracion"):
            chequeo("ojo", "Falta la configuración inicial: hacela YA (mientras tanto cualquiera con la dirección podría hacerla)")
        else:
            chequeo(True, "Configuración inicial hecha: la empresa ya tiene administrador")
    else:
        chequeo(False, f"/api/v1/configuracion-inicial respondió HTTP {estado}")
    return resultados


def cmd_verificar(args: argparse.Namespace) -> int:
    print(f"Verificando {args.url} ...")
    resultados = verificar(args.url)
    etiquetas = {"ok": OK, "ojo": OJO, "mal": MAL}
    for nivel, mensaje in resultados:
        print(f"{etiquetas[nivel]} {mensaje}")
    return 1 if any(nivel == "mal" for nivel, _ in resultados) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Alta de un cliente de SAIL en la nube (ver docs/ALTA-CLIENTE-NUBE.md)")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("variables", help="genera SECRET_KEY y la lista de variables para Vercel")
    p.add_argument("--nombre", required=True, help="nombre comercial del cliente")
    p.set_defaults(funcion=cmd_variables)
    sub.add_parser("probar-base", help="prueba la conexión a la base (DATABASE_URL)").set_defaults(funcion=cmd_probar_base)
    sub.add_parser("migrar", help="crea o actualiza las tablas (alembic upgrade head)").set_defaults(funcion=cmd_migrar)
    p = sub.add_parser("verificar", help="verifica una instancia publicada")
    p.add_argument("url", help="dirección de la instancia, ej. https://sail-ferreteria-x.vercel.app")
    p.set_defaults(funcion=cmd_verificar)
    args = parser.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(main())
