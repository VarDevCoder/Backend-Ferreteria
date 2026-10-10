"""Errores QA-N1 a QA-N4 del relevamiento (docs/BACKLOG.md, sección 5)."""
from tests.ayudas import API, auth, configurar, crear_usuario, producto_con_stock, stock


def _producto(client, token, unidad, stock_inicial=10, nombre="Producto"):
    r = client.post(f"{API}/productos", headers=auth(token), json={"nombre": nombre, "precio_compra": 1000, "precio_venta": 2000, "unidad_medida": unidad})
    assert r.status_code == 201, r.text
    p = r.json()
    if stock_inicial:
        assert client.post(f"{API}/inventario/ajustes", headers=auth(token), json={"producto_id": p["id"], "stock_nuevo": stock_inicial, "motivo": "Inicial"}).status_code == 201
    return p


def _venta(client, token, producto, cantidad, **extra):
    return client.post(f"{API}/caja/ventas", headers=auth(token), json={"items": [{"producto_id": producto["id"], "cantidad": cantidad}], **extra})


# --- QA-N1: unidades enteras -------------------------------------------------------

def test_producto_por_pieza_no_se_vende_fraccionado(client):
    admin = configurar(client)
    alicate = _producto(client, admin, "pz", nombre="Alicate")
    cable = _producto(client, admin, "m", nombre="Cable")
    assert alicate["fraccionable"] is False and cable["fraccionable"] is True
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201

    r = _venta(client, admin, alicate, 0.5)
    assert r.status_code == 422 and "unidad entera" in r.json()["detail"]
    assert stock(client, admin, alicate) == 10
    assert _venta(client, admin, alicate, 2).status_code == 201
    assert _venta(client, admin, cable, 2.5).status_code == 201  # metros: se fracciona
    assert stock(client, admin, cable) == 7.5


def test_unidades_enteras_en_pedidos_envios_ajustes_y_compras(client):
    admin = configurar(client)
    caja = _producto(client, admin, "caja", nombre="Tornillos x100")
    r = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_nombre": "C", "items": [{"producto_id": caja["id"], "cantidad": 1.5, "precio_unitario": 2000}]})
    assert r.status_code == 422
    r = client.post(f"{API}/inventario/ajustes", headers=auth(admin), json={"producto_id": caja["id"], "stock_nuevo": 3.5, "motivo": "Conteo"})
    assert r.status_code == 422
    r = client.post(f"{API}/ordenes-compra", headers=auth(admin), json={
        "proveedor_nombre": "P", "items": [{"producto_id": caja["id"], "cantidad_solicitada": 0.5, "precio_unitario": 1000}]})
    assert r.status_code == 422
    ped = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_nombre": "C", "items": [{"producto_id": caja["id"], "cantidad": 2, "precio_unitario": 2000}]}).json()
    r = client.post(f"{API}/ordenes-envio", headers=auth(admin), json={
        "pedido_cliente_id": ped["id"], "direccion_entrega": "x", "items": [{"producto_id": caja["id"], "cantidad": 1.5}]})
    assert r.status_code == 422
    r = client.post(f"{API}/stock-no-vendible", headers=auth(admin), json={"producto_id": caja["id"], "cantidad": 0.5, "motivo": "AVERIADO"})
    assert r.status_code == 422, r.text


# --- QA-N2: ids que no existen --------------------------------------------------------

def test_ids_inexistentes_responden_404(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=5)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    r = _venta(client, admin, p, 1, cliente_id=9999)
    assert r.status_code == 404 and "Cliente" in r.json()["detail"]
    r = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_id": 9999, "cliente_nombre": "C", "items": [{"producto_id": p["id"], "cantidad": 1, "precio_unitario": 3000}]})
    assert r.status_code == 404
    r = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_nombre": "C", "items": [{"producto_id": 9999, "cantidad": 1, "precio_unitario": 3000}]})
    assert r.status_code == 404
    r = client.post(f"{API}/productos", headers=auth(admin), json={"nombre": "X", "precio_compra": 1, "categoria_id": 9999})
    assert r.status_code == 404 and "Categor" in r.json()["detail"]
    r = client.post(f"{API}/proveedor-productos", headers=auth(admin), json={"proveedor_id": 9999, "producto_id": p["id"], "precio": 100})
    assert r.status_code == 404
    r = client.post(f"{API}/ordenes-compra", headers=auth(admin), json={
        "proveedor_nombre": "P", "items": [{"producto_id": 9999, "cantidad_solicitada": 1, "precio_unitario": 1000}]})
    assert r.status_code in (404, 422)


# --- QA-N3: producto desactivado --------------------------------------------------------

def test_producto_desactivado_no_se_vende_ni_se_pide(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=5)
    r = client.put(f"{API}/productos/{p['id']}", headers=auth(admin), json={
        "nombre": p["nombre"], "precio_compra": p["precio_compra"], "precio_venta": p["precio_venta"],
        "stock_minimo": 0, "unidad_medida": "pz", "activo": False})
    assert r.status_code == 200
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    r = _venta(client, admin, p, 1)
    assert r.status_code == 422 and "desactivado" in r.json()["detail"]
    r = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_nombre": "C", "items": [{"producto_id": p["id"], "cantidad": 1, "precio_unitario": 3000}]})
    assert r.status_code == 422 and "desactivado" in r.json()["detail"]


# --- QA-N4: mensaje de stock insuficiente -------------------------------------------------

def test_mensaje_de_stock_insuficiente_con_formato_de_paraguay(client):
    admin = configurar(client)
    destornillador = _producto(client, admin, "pz", stock_inicial=1800, nombre="Destornillador")
    cable = _producto(client, admin, "m", stock_inicial=2.5, nombre="Cable")
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    r = _venta(client, admin, destornillador, 2000)
    assert r.status_code == 409
    assert r.json()["detail"] == "Stock insuficiente para Destornillador: hay 1.800 pz y se pidieron 2.000 pz"
    r = _venta(client, admin, cable, 3.25)
    assert r.json()["detail"] == "Stock insuficiente para Cable: hay 2,5 m y se pidieron 3,25 m"
