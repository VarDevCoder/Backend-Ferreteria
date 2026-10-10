"""Mide la API con un catálogo de tamaño real (QA-N5 / REL-03 del backlog).

Carga 12.000 productos y 2.000 clientes de prueba (el SQL de
docs/BACKLOG.md, sección 5) en una base DE PRUEBA que ya tenga la demo, y
mide cuánto tardan y cuánto pesan las listas que usan Productos, Inventario
y Clientes. Hoy (sin paginación en el servidor) no cumple el objetivo; cuando
se haga REL-03, este script sirve para comprobarlo y para que no se vuelva a
romper.

Uso (NUNCA contra producción: inserta datos de prueba):
    DATABASE_URL=postgresql+pg8000://...base_de_prueba python herramientas/medir_catalogo_grande.py

Sale con código 1 si alguna lista supera el objetivo (2 s o 500 KB).
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

OBJETIVO_SEGUNDOS = 2.0
OBJETIVO_KB = 500
LISTAS = ["/productos", "/inventario/stock", "/clientes"]

CARGA_MASIVA = [
    """INSERT INTO productos (categoria_id,codigo,nombre,precio_compra,precio_venta,stock_actual,stock_minimo,unidad_medida,activo)
       SELECT (SELECT min(id) FROM categorias),'MASIVO-'||g,'Artículo de prueba '||g,1000+g,1250+g,10,2,'pz',true
       FROM generate_series(1,12000) g""",
    """INSERT INTO clientes (nombre,activo,limite_credito) SELECT 'Cliente prueba '||g,true,0 FROM generate_series(1,2000) g""",
]


def main() -> int:
    if "prod" in os.environ.get("DATABASE_URL", "") or os.environ.get("ENVIRONMENT") == "production":
        print("No se corre contra producción.")
        return 2
    with engine.begin() as conexion:
        if not conexion.execute(text("SELECT 1 FROM productos WHERE codigo = 'MASIVO-1'")).first():
            print("Cargando 12.000 productos y 2.000 clientes de prueba...")
            for sql in CARGA_MASIVA:
                conexion.execute(text(sql))
        productos = conexion.execute(text("SELECT count(*) FROM productos")).scalar_one()
        clientes = conexion.execute(text("SELECT count(*) FROM clientes")).scalar_one()
    print(f"Base con {productos} productos y {clientes} clientes")

    cliente = TestClient(app)
    r = cliente.post("/api/v1/auth/login", json={"email": "demo@sail.local", "password": "demo12345"})
    if r.status_code != 200:
        print("No se pudo ingresar con demo@sail.local (¿la base tiene la demo?)")
        return 2
    cabeceras = {"Authorization": f"Bearer {r.json()['access_token']}"}

    fallas = 0
    for ruta in LISTAS:
        inicio = time.perf_counter()
        respuesta = cliente.get(f"/api/v1{ruta}", headers=cabeceras)
        segundos = time.perf_counter() - inicio
        kb = len(respuesta.content) / 1024
        ok = respuesta.status_code == 200 and segundos <= OBJETIVO_SEGUNDOS and kb <= OBJETIVO_KB
        fallas += not ok
        print(f"{'OK ' if ok else 'MAL'} GET {ruta:<20} {segundos:6.2f} s  {kb:8.0f} KB  ({respuesta.status_code})")
    print(f"Objetivo por lista: {OBJETIVO_SEGUNDOS} s y {OBJETIVO_KB} KB (sin contar el dibujo en el navegador)")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
