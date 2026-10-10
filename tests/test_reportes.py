"""Reporte de ventas: el ranking de productos usa lo cobrado (con el descuento de la venta)."""
from datetime import date

from tests.ayudas import API, auth, configurar, producto_con_stock


def test_ranking_descuenta_el_descuento_de_la_venta(client):
    admin = configurar(client)
    a = producto_con_stock(client, admin, stock=10, nombre="Martillo", precio_compra=2000, precio_venta=3000)
    b = producto_con_stock(client, admin, stock=10, nombre="Pinza", precio_compra=500, precio_venta=1000)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    # Subtotal 4000 (3000 + 1000) con 50 %: total 2000, repartido 1500 / 500.
    r = client.post(f"{API}/caja/ventas", headers=auth(admin), json={
        "items": [{"producto_id": a["id"], "cantidad": 1}, {"producto_id": b["id"], "cantidad": 1}], "descuento": 50,
    })
    assert r.status_code == 201 and r.json()["total"] == 2000

    hoy = date.today().isoformat()
    rep = client.get(f"{API}/reportes/ventas?desde={hoy}&hasta={hoy}", headers=auth(admin)).json()
    assert rep["mostrador"]["total"] == 2000
    filas = {f["nombre"]: f for f in rep["productos_mas_vendidos"]}
    assert (filas["Martillo"]["total"], filas["Martillo"]["utilidad_estimada"]) == (1500, -500)
    assert (filas["Pinza"]["total"], filas["Pinza"]["utilidad_estimada"]) == (500, 0)
    assert sum(f["total"] for f in rep["productos_mas_vendidos"]) == rep["mostrador"]["total"]
