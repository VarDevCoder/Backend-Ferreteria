"""Medios de pago: pago mixto, venta a cuenta (fiado) con límite de crédito
por cliente, cobros posteriores y su impacto en caja y reportes."""
from datetime import date

from tests.test_empresa_y_permisos import API, _auth, _configurar, _crear_usuario


def _preparar(client):
    admin = _configurar(client)
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    p = client.post(f"{API}/productos", headers=_auth(admin), json={"nombre": "Taladro", "precio_compra": 100000, "precio_venta": 150000}).json()
    client.post(f"{API}/inventario/ajustes", headers=_auth(admin), json={"producto_id": p["id"], "stock_nuevo": 20, "motivo": "Inicial"})
    assert client.post(f"{API}/caja/turnos/abrir", headers=_auth(vendedor), json={"fondo_inicial": 100000}).status_code == 201
    return admin, vendedor, p


def _vender(client, token, producto, cantidad, pagos, cliente_id=None):
    return client.post(
        f"{API}/caja/ventas", headers=_auth(token),
        json={"items": [{"producto_id": producto["id"], "cantidad": cantidad}], "pagos": pagos, "cliente_id": cliente_id},
    )


def test_pago_mixto_suma_a_cada_medio(client):
    admin, vendedor, p = _preparar(client)
    r = _vender(client, vendedor, p, 2, [
        {"metodo": "EFECTIVO", "monto": 100000},
        {"metodo": "TARJETA_CREDITO", "monto": 150000, "referencia": "1234"},
        {"metodo": "QR", "monto": 50000},
    ])
    assert r.status_code == 201, r.text
    venta = r.json()
    assert venta["metodo_pago"] == "MIXTO" and len(venta["pagos"]) == 3

    turno = client.get(f"{API}/caja/turno-abierto", headers=_auth(vendedor)).json()
    assert turno["total_ventas_efectivo"] == 100000
    assert turno["total_ventas_tarjeta"] == 150000
    assert turno["total_ventas_transferencia"] == 50000
    assert turno["saldo_esperado"] == 200000  # fondo + solo el efectivo

    hoy = date.today().isoformat()
    rep = client.get(f"{API}/reportes/ventas?desde={hoy}&hasta={hoy}", headers=_auth(admin)).json()
    assert rep["mostrador"]["cantidad_ventas"] == 1 and rep["mostrador"]["total"] == 300000
    assert {m["metodo_pago"]: m["total"] for m in rep["por_metodo_pago"]} == {"EFECTIVO": 100000, "TARJETA_CREDITO": 150000, "QR": 50000}


def test_pagos_deben_sumar_el_total(client):
    _, vendedor, p = _preparar(client)
    r = _vender(client, vendedor, p, 1, [{"metodo": "EFECTIVO", "monto": 100000}])
    assert r.status_code == 422 and "faltan" in r.json()["detail"]
    r = _vender(client, vendedor, p, 1, [{"metodo": "NO_EXISTE", "monto": 150000}])
    assert r.status_code == 422
    # Sin `pagos`, se cobra todo con metodo_pago (compatibilidad).
    r = client.post(f"{API}/caja/ventas", headers=_auth(vendedor), json={"items": [{"producto_id": p["id"], "cantidad": 1}], "metodo_pago": "TARJETA_DEBITO"})
    assert r.status_code == 201 and r.json()["pagos"] == [{"metodo": "TARJETA_DEBITO", "monto": 150000, "referencia": None}]


def test_venta_a_cuenta_con_limite_y_cobro(client):
    admin, vendedor, p = _preparar(client)
    cliente = client.post(f"{API}/clientes", headers=_auth(vendedor), json={"nombre": "Constructora Lambaré"}).json()
    a_cuenta = [{"metodo": "EFECTIVO", "monto": 50000}, {"metodo": "CUENTA_CORRIENTE", "monto": 250000}]

    # Sin cliente, o con un cliente sin crédito habilitado, no se fía.
    assert _vender(client, vendedor, p, 2, a_cuenta).status_code == 422
    r = _vender(client, vendedor, p, 2, a_cuenta, cliente["id"])
    assert r.status_code == 422 and "crédito" in r.json()["detail"]

    # El límite lo pone un encargado/admin, no el vendedor.
    datos = {"nombre": "Constructora Lambaré", "limite_credito": 400000}
    assert client.put(f"{API}/clientes/{cliente['id']}", headers=_auth(vendedor), json=datos).status_code == 403
    r = client.put(f"{API}/clientes/{cliente['id']}", headers=_auth(admin), json=datos)
    assert r.status_code == 200 and r.json()["limite_credito"] == 400000
    # El vendedor puede editar otros datos sin tocar el límite.
    r = client.put(f"{API}/clientes/{cliente['id']}", headers=_auth(vendedor), json={"nombre": "Constructora Lambaré SA", "telefono": "0981"})
    assert r.status_code == 200 and r.json()["limite_credito"] == 400000

    # Pago parcial: entrega en efectivo y el resto a cuenta.
    r = _vender(client, vendedor, p, 2, a_cuenta, cliente["id"])
    assert r.status_code == 201, r.text
    estado = client.get(f"{API}/clientes/{cliente['id']}/cuenta-corriente", headers=_auth(vendedor)).json()
    assert estado["saldo"] == 250000 and estado["disponible"] == 150000
    assert estado["movimientos"][0]["tipo"] == "CARGO"

    # Superar el límite se rechaza.
    r = _vender(client, vendedor, p, 2, [{"metodo": "CUENTA_CORRIENTE", "monto": 300000}], cliente["id"])
    assert r.status_code == 422 and "límite" in r.json()["detail"]

    turno = client.get(f"{API}/caja/turno-abierto", headers=_auth(vendedor)).json()
    assert turno["total_ventas_a_cuenta"] == 250000 and turno["saldo_esperado"] == 150000

    # Cobro parcial en efectivo: entra a la caja.
    cobro = {"monto": 100000, "metodo": "EFECTIVO"}
    r = client.post(f"{API}/clientes/{cliente['id']}/cuenta-corriente/cobros", headers=_auth(vendedor), json=cobro)
    assert r.status_code == 201, r.text
    assert r.json()["saldo"] == 150000
    turno = client.get(f"{API}/caja/turno-abierto", headers=_auth(vendedor)).json()
    assert turno["saldo_esperado"] == 250000

    # No se cobra más de lo que debe, ni "a cuenta".
    assert client.post(f"{API}/clientes/{cliente['id']}/cuenta-corriente/cobros", headers=_auth(vendedor), json={"monto": 999999}).status_code == 422
    assert client.post(f"{API}/clientes/{cliente['id']}/cuenta-corriente/cobros", headers=_auth(vendedor), json={"monto": 1000, "metodo": "CUENTA_CORRIENTE"}).status_code == 422

    deudores = client.get(f"{API}/cuentas-corrientes/deudores", headers=_auth(vendedor)).json()
    assert len(deudores) == 1 and deudores[0]["saldo"] == 150000 and deudores[0]["hasta_30"] == 150000
    assert client.get(f"{API}/dashboard", headers=_auth(admin)).json()["stats"]["por_cobrar"] == 150000
    listado = client.get(f"{API}/clientes", headers=_auth(vendedor)).json()
    assert listado[0]["saldo"] == 150000

    # Con cuenta corriente no se borra: se desactiva.
    assert client.delete(f"{API}/clientes/{cliente['id']}", headers=_auth(admin)).status_code == 422
