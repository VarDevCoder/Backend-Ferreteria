"""Órdenes de compra: recepción de mercadería."""
from tests.ayudas import API, auth, configurar, producto_con_stock, stock


def _orden_confirmada(client, token, producto, cantidad):
    r = client.post(f"{API}/ordenes-compra", headers=auth(token), json={
        "proveedor_nombre": "Proveedor SA", "items": [{"producto_id": producto["id"], "cantidad_solicitada": cantidad, "precio_unitario": 2500}],
    })
    assert r.status_code == 201, r.text
    oc = r.json()
    for accion in ("enviar", "confirmar"):
        assert client.post(f"{API}/ordenes-compra/{oc['id']}/{accion}", headers=auth(token)).status_code == 200
    return oc


def test_recepcion_parcial_y_completa_suma_stock(client):
    """Antes daba 500: sumaba la cantidad del JSON (float) a un Decimal de la base."""
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=0, nombre="Tornillo")
    oc = _orden_confirmada(client, admin, p, 5)
    item = oc["items"][0]["id"]

    r = client.post(f"{API}/ordenes-compra/{oc['id']}/recibir", headers=auth(admin), json={"cantidades": {str(item): 2.0}})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECIBIDA_PARCIAL"
    assert stock(client, admin, p) == 2

    r = client.post(f"{API}/ordenes-compra/{oc['id']}/recibir", headers=auth(admin), json={"cantidades": {str(item): 3.0}})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECIBIDA_COMPLETA"
    assert stock(client, admin, p) == 5

    kardex = client.get(f"{API}/inventario/kardex/{p['id']}", headers=auth(admin)).json()
    assert [m["referencia_tipo"] for m in kardex].count("ORDEN_COMPRA") == 2
