"""Tope de descuento por rol y control de precio en pedidos.

Decisión a confirmar con el dueño: el vendedor puede descontar hasta el 10 %
por venta o pedido (permisos.DESCUENTO_MAXIMO_SIN_PERMISO); admin y encargado,
sin tope."""
from tests.ayudas import API, auth, configurar, crear_usuario, producto_con_stock


def _venta(client, token, producto, descuento, cantidad=1):
    return client.post(f"{API}/caja/ventas", headers=auth(token), json={
        "items": [{"producto_id": producto["id"], "cantidad": cantidad}], "descuento": descuento,
    })


def test_vendedor_descuenta_hasta_10_por_ciento(client):
    admin = configurar(client)
    vendedor = crear_usuario(client, admin, "vende@x.com", "vendedor")
    encargado = crear_usuario(client, admin, "encarga@x.com", "encargado")
    p = producto_con_stock(client, admin, stock=20, precio_venta=10000)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(vendedor), json={"fondo_inicial": 0}).status_code == 201

    r = _venta(client, vendedor, p, 100)
    assert r.status_code == 403 and "10 %" in r.json()["detail"]
    r = _venta(client, vendedor, p, 10)
    assert r.status_code == 201 and r.json()["total"] == 9000
    assert _venta(client, encargado, p, 50).status_code == 201

    yo = client.get(f"{API}/auth/me", headers=auth(vendedor)).json()
    assert yo["descuento_maximo"] == 10
    assert client.get(f"{API}/auth/me", headers=auth(admin)).json()["descuento_maximo"] == 100


def _pedido(client, token, producto, precio, descuento=0):
    return client.post(f"{API}/pedidos-cliente", headers=auth(token), json={
        "cliente_nombre": "Cliente", "descuento": descuento,
        "items": [{"producto_id": producto["id"], "cantidad": 1, "precio_unitario": precio}],
    })


def test_pedido_respeta_precio_de_lista_y_descuento_del_vendedor(client):
    admin = configurar(client)
    vendedor = crear_usuario(client, admin, "vende@x.com", "vendedor")
    p = producto_con_stock(client, admin, stock=5, precio_venta=10000)

    r = _pedido(client, vendedor, p, precio=1)
    assert r.status_code == 403 and "precio" in r.json()["detail"]
    r = _pedido(client, vendedor, p, precio=10000, descuento=30)
    assert r.status_code == 403
    r = _pedido(client, vendedor, p, precio=10000, descuento=5)
    assert r.status_code == 201, r.text
    pedido = r.json()

    # Editar el pedido con otro precio tampoco.
    r = client.put(f"{API}/pedidos-cliente/{pedido['id']}", headers=auth(vendedor), json={
        "cliente_nombre": "Cliente", "descuento": 0, "items": [{"producto_id": p["id"], "cantidad": 2, "precio_unitario": 500}],
    })
    assert r.status_code == 403

    # El encargado/admin sí puede pactar otro precio.
    assert _pedido(client, admin, p, precio=8000, descuento=40).status_code == 201
