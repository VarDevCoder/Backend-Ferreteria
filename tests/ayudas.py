"""Ayudas comunes para los tests de integración (alta de empresa, usuarios,
productos con stock, pedidos y envíos)."""
API = "/api/v1"

EMPRESA = {"nombre_comercial": "Ferretería de Prueba", "moneda_codigo": "PYG", "moneda_simbolo": "Gs.", "locale": "es-PY"}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def configurar(client) -> str:
    r = client.post(f"{API}/configuracion-inicial", json={
        "empresa": EMPRESA, "admin": {"name": "Admin", "email": "admin@prueba.com", "password": "password-123"},
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def crear_usuario(client, token, email, rol, password="password-123") -> str:
    r = client.post(f"{API}/usuarios", headers=auth(token), json={"name": rol, "email": email, "password": password, "rol": rol})
    assert r.status_code == 201, r.text
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def producto_con_stock(client, token, stock, nombre="Cinta", precio_compra=2000, precio_venta=3000) -> dict:
    r = client.post(f"{API}/productos", headers=auth(token), json={"nombre": nombre, "precio_compra": precio_compra, "precio_venta": precio_venta})
    assert r.status_code == 201, r.text
    p = r.json()
    if stock:
        r = client.post(f"{API}/inventario/ajustes", headers=auth(token), json={"producto_id": p["id"], "stock_nuevo": stock, "motivo": "Inicial"})
        assert r.status_code == 201, r.text
    return p


def stock(client, token, producto) -> float:
    return client.get(f"{API}/productos/{producto['id']}", headers=auth(token)).json()["stock_actual"]


def pedido(client, token, items, precio=3000) -> dict:
    r = client.post(f"{API}/pedidos-cliente", headers=auth(token), json={
        "cliente_nombre": "Cliente", "items": [{"producto_id": pid, "cantidad": c, "precio_unitario": precio} for pid, c in items],
    })
    assert r.status_code == 201, r.text
    return r.json()


def estado_pedido(client, token, ped) -> str:
    return client.get(f"{API}/pedidos-cliente/{ped['id']}", headers=auth(token)).json()["estado"]


def envio(client, token, ped, producto, cantidad) -> dict:
    r = client.post(f"{API}/ordenes-envio", headers=auth(token), json={
        "pedido_cliente_id": ped["id"], "direccion_entrega": "Ruta 1 km 20", "items": [{"producto_id": producto["id"], "cantidad": cantidad}],
    })
    assert r.status_code == 201, r.text
    return r.json()


def accion_envio(client, token, orden, accion, cuerpo=None):
    return client.post(f"{API}/ordenes-envio/{orden['id']}/{accion}", headers=auth(token), json=cuerpo or {})
