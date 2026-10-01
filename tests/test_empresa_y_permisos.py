"""Recorrido de una ferretería nueva: configuración inicial, alta de
personal, permisos por rol, carga de stock, venta y reporte."""
from datetime import date

API = "/api/v1"

EMPRESA = {
    "nombre_comercial": "Ferretería San José", "ruc": "80099999-1", "moneda_codigo": "PYG",
    "moneda_simbolo": "Gs.", "locale": "es-PY", "iva_porcentaje": 10, "margen_ganancia_defecto": 30,
}
ADMIN = {"name": "Dueña", "email": "Duena@SanJose.com", "password": "clave-segura-1"}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _configurar(client) -> str:
    r = client.post(f"{API}/configuracion-inicial", json={"empresa": EMPRESA, "admin": ADMIN})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _crear_usuario(client, token, email, rol) -> str:
    r = client.post(f"{API}/usuarios", headers=_auth(token), json={"name": rol, "email": email, "password": "password-123", "rol": rol})
    assert r.status_code == 201, r.text
    r = client.post(f"{API}/auth/login", json={"email": email, "password": "password-123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_configuracion_inicial_solo_una_vez(client):
    assert client.get(f"{API}/configuracion-inicial").json() == {"requiere_configuracion": True}
    token = _configurar(client)

    assert client.get(f"{API}/configuracion-inicial").json() == {"requiere_configuracion": False}
    assert client.get(f"{API}/empresa").json()["nombre_comercial"] == "Ferretería San José"
    me = client.get(f"{API}/auth/me", headers=_auth(token)).json()
    assert me["rol"] == "admin" and me["email"] == "duena@sanjose.com"
    assert "usuarios" in me["permisos"]

    otra = client.post(f"{API}/configuracion-inicial", json={"empresa": EMPRESA, "admin": {**ADMIN, "email": "x@y.com"}})
    assert otra.status_code == 409


def test_login_y_endpoints_protegidos(client):
    _configurar(client)
    assert client.get(f"{API}/productos").status_code == 401
    assert client.get(f"{API}/productos", headers=_auth("token-trucho")).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "mal"}).status_code == 401

    r = client.post(f"{API}/auth/login", json={"email": " duena@sanjose.com ", "password": ADMIN["password"]})
    assert r.status_code == 200
    assert client.get(f"{API}/productos", headers=_auth(r.json()["access_token"])).status_code == 200


def test_bloqueo_por_intentos_fallidos(client):
    _configurar(client)
    for _ in range(5):
        client.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "mal"})
    r = client.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
    assert r.status_code == 403


def test_permisos_por_rol(client):
    admin = _configurar(client)
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    deposito = _crear_usuario(client, admin, "depo@sj.com", "deposito")

    producto = {"nombre": "Martillo", "precio_compra": 10000, "stock_minimo": 2}
    # El vendedor consulta el catálogo pero no lo modifica; el depósito sí.
    assert client.get(f"{API}/productos", headers=_auth(vendedor)).status_code == 200
    assert client.post(f"{API}/productos", headers=_auth(vendedor), json=producto).status_code == 403
    r = client.post(f"{API}/productos", headers=_auth(deposito), json=producto)
    assert r.status_code == 201
    assert r.json()["precio_venta"] == 13000  # margen de la empresa (30 %)

    # Clientes: sí para el vendedor. Proveedores: no.
    assert client.post(f"{API}/clientes", headers=_auth(vendedor), json={"nombre": "Juan"}).status_code == 201
    proveedor = {"razon_social": "Prov", "ruc": "1-1", "email": "p@p.com", "password": "password-123"}
    assert client.post(f"{API}/proveedores", headers=_auth(vendedor), json=proveedor).status_code == 403

    # Usuarios y reportes: solo gestión.
    assert client.get(f"{API}/usuarios", headers=_auth(vendedor)).status_code == 403
    assert client.get(f"{API}/reportes/ventas", headers=_auth(deposito)).status_code == 403
    assert client.put(f"{API}/empresa", headers=_auth(vendedor), json=EMPRESA).status_code == 403


def test_usuario_desactivado_pierde_acceso(client):
    admin = _configurar(client)
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    usuarios = client.get(f"{API}/usuarios", headers=_auth(admin)).json()
    vid = next(u["id"] for u in usuarios if u["email"] == "vende@sj.com")

    r = client.put(f"{API}/usuarios/{vid}", headers=_auth(admin), json={"name": "V", "email": "vende@sj.com", "rol": "vendedor", "activo": False})
    assert r.status_code == 200
    assert client.get(f"{API}/auth/me", headers=_auth(vendedor)).status_code == 401


def test_no_se_puede_quedar_sin_admin(client):
    admin = _configurar(client)
    yo = client.get(f"{API}/auth/me", headers=_auth(admin)).json()
    r = client.put(f"{API}/usuarios/{yo['id']}", headers=_auth(admin), json={"name": "D", "email": yo["email"], "rol": "vendedor", "activo": True})
    assert r.status_code == 422


def test_stock_inicial_venta_y_reporte(client):
    admin = _configurar(client)
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    p = client.post(f"{API}/productos", headers=_auth(admin), json={"codigo": "7790001", "nombre": "Cinta", "precio_compra": 2000, "precio_venta": 3000}).json()
    assert p["codigo"] == "7790001"
    dup = client.post(f"{API}/productos", headers=_auth(admin), json={"codigo": "7790001", "nombre": "Otra", "precio_compra": 1})
    assert dup.status_code == 409

    # Carga de inventario inicial (el vendedor no puede ajustar stock).
    ajuste = {"producto_id": p["id"], "stock_nuevo": 50, "motivo": "Inventario inicial"}
    assert client.post(f"{API}/inventario/ajustes", headers=_auth(vendedor), json=ajuste).status_code == 403
    r = client.post(f"{API}/inventario/ajustes", headers=_auth(admin), json=ajuste)
    assert r.status_code == 201 and r.json()["cantidad"] == 50

    # Venta de mostrador hecha por el vendedor.
    assert client.post(f"{API}/caja/turnos/abrir", headers=_auth(vendedor), json={"fondo_inicial": 100000}).status_code == 201
    venta = client.post(f"{API}/caja/ventas", headers=_auth(vendedor), json={"items": [{"producto_id": p["id"], "cantidad": 4}], "metodo_pago": "EFECTIVO"})
    assert venta.status_code == 201, venta.text
    assert client.get(f"{API}/productos/{p['id']}", headers=_auth(vendedor)).json()["stock_actual"] == 46

    hoy = date.today().isoformat()
    rep = client.get(f"{API}/reportes/ventas?desde={hoy}&hasta={hoy}", headers=_auth(admin)).json()
    assert rep["mostrador"] == {"cantidad_ventas": 1, "total": 12000, "ticket_promedio": 12000}
    top = rep["productos_mas_vendidos"][0]
    assert (top["cantidad"], top["total"], top["utilidad_estimada"]) == (4, 12000, 4000)


def _producto_con_stock(client, token, stock, precio_venta=3000) -> dict:
    p = client.post(f"{API}/productos", headers=_auth(token), json={"nombre": "Cinta", "precio_compra": 2000, "precio_venta": precio_venta}).json()
    client.post(f"{API}/inventario/ajustes", headers=_auth(token), json={"producto_id": p["id"], "stock_nuevo": stock, "motivo": "Inicial"})
    return p


def test_mismo_producto_en_varias_lineas_no_deja_stock_negativo(client):
    admin = _configurar(client)
    p = _producto_con_stock(client, admin, stock=5)
    client.post(f"{API}/caja/turnos/abrir", headers=_auth(admin), json={"fondo_inicial": 0})

    lineas = [{"producto_id": p["id"], "cantidad": 3}, {"producto_id": p["id"], "cantidad": 3}]
    r = client.post(f"{API}/caja/ventas", headers=_auth(admin), json={"items": lineas, "metodo_pago": "EFECTIVO"})
    assert r.status_code == 409, r.text
    assert client.get(f"{API}/productos/{p['id']}", headers=_auth(admin)).json()["stock_actual"] == 5

    lineas[1]["cantidad"] = 2  # 3 + 2 = 5: justo el stock
    assert client.post(f"{API}/caja/ventas", headers=_auth(admin), json={"items": lineas, "metodo_pago": "EFECTIVO"}).status_code == 201
    assert client.get(f"{API}/productos/{p['id']}", headers=_auth(admin)).json()["stock_actual"] == 0


def test_vendedor_no_puede_cambiar_el_precio(client):
    admin = _configurar(client)
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    p = _producto_con_stock(client, admin, stock=10, precio_venta=3000)
    client.post(f"{API}/caja/turnos/abrir", headers=_auth(admin), json={"fondo_inicial": 0})

    def vender(token, precio):
        item = {"producto_id": p["id"], "cantidad": 1}
        if precio is not None:
            item["precio_unitario"] = precio
        return client.post(f"{API}/caja/ventas", headers=_auth(token), json={"items": [item], "metodo_pago": "EFECTIVO"})

    assert vender(vendedor, 1).status_code == 403          # precio inventado: rechazado
    assert vender(vendedor, 3000).json()["total"] == 3000  # precio de lista: ok
    assert vender(vendedor, None).json()["total"] == 3000  # sin precio: usa el de lista
    assert vender(admin, 2500).json()["total"] == 2500     # el encargado/admin sí puede

    me = client.get(f"{API}/auth/me", headers=_auth(vendedor)).json()
    assert "precios_venta" not in me["permisos"]
