"""Logística de pedidos: entrega a domicilio o retiro en el local, y cómo se
cobra (anticipado, contra entrega con rendición en caja, o a cuenta)."""
from tests.ayudas import API, accion_envio, auth, configurar, crear_usuario, envio, producto_con_stock, stock

FONDO = 100000


def _preparar(client):
    admin = configurar(client)
    vendedor = crear_usuario(client, admin, "vende@prueba.com", "vendedor")
    deposito = crear_usuario(client, admin, "deposito@prueba.com", "deposito")
    p = producto_con_stock(client, admin, stock=50)  # precio de venta 3.000
    return admin, vendedor, deposito, p


def _pedido(client, token, producto, cantidad, **extra):
    r = client.post(f"{API}/pedidos-cliente", headers=auth(token), json={
        "cliente_nombre": "Cliente", "items": [{"producto_id": producto["id"], "cantidad": cantidad, "precio_unitario": 3000}], **extra,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _ver(client, token, ped):
    return client.get(f"{API}/pedidos-cliente/{ped['id']}", headers=auth(token)).json()


def _abrir_caja(client, token):
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(token), json={"fondo_inicial": FONDO}).status_code == 201


def _saldo_caja(client, token):
    return client.get(f"{API}/caja/turno-abierto", headers=auth(token)).json()["saldo_esperado"]


def _pagar(client, token, ped, pagos, accion="pagos"):
    return client.post(f"{API}/pedidos-cliente/{ped['id']}/{accion}", headers=auth(token), json={"pagos": pagos})


def test_contra_entrega_queda_por_rendir_y_se_rinde_en_caja(client):
    admin, vendedor, deposito, p = _preparar(client)
    ped = _pedido(client, vendedor, p, 10)  # Gs. 30.000, por defecto a domicilio y contra entrega
    assert (ped["modalidad_entrega"], ped["forma_pago"], ped["estado_pago"]) == ("ENTREGA_DOMICILIO", "CONTRA_ENTREGA", "PENDIENTE")
    assert ped["etiqueta_cobro"] == "Contra entrega" and ped["saldo"] == 30000

    # Los cobros de pedidos se registran con la caja abierta.
    r = _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 5000}])
    assert r.status_code == 409 and "caja" in r.json()["detail"]
    _abrir_caja(client, vendedor)
    r = _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 5000}])
    assert r.status_code == 201, r.text
    assert r.json()["pedido"]["estado_pago"] == "PARCIAL" and r.json()["pedido"]["etiqueta_cobro"] == "Contra entrega (con seña)"
    assert r.json()["pagos"][0]["tipo"] == "ANTICIPO"
    assert _saldo_caja(client, vendedor) == FONDO + 5000

    orden = envio(client, deposito, ped, p, 10)
    assert accion_envio(client, deposito, orden, "lista-despachar").json()["estado"] == "LISTO"
    r = accion_envio(client, deposito, orden, "despachar", {
        "numero_guia": "G-1", "transportista": "Fletes Ñandutí", "vehiculo": "Isuzu ABC 123",
        "conductor_nombre": "Pedro Gómez", "conductor_documento": "1234567", "numero_nota_remision": "001-001-0000100",
    })
    assert r.status_code == 200, r.text
    assert r.json()["conductor_nombre"] == "Pedro Gómez" and r.json()["numero_nota_remision"] == "001-001-0000100"
    hoja = client.get(f"{API}/ordenes-envio/{orden['id']}/hoja", headers=auth(vendedor)).json()
    assert hoja["cobro"]["a_cobrar_en_la_entrega"] == 25000 and hoja["items"][0]["nombre"] == "Cinta"
    assert hoja["empresa"]["nombre_comercial"] == "Ferretería de Prueba" and "001-001-0000100" in hoja["leyenda"]

    # Entregar no mueve la caja: queda por rendir.
    assert accion_envio(client, deposito, orden, "entregar").status_code == 200
    ped = _ver(client, admin, ped)
    assert ped["estado"] == "ENTREGADO" and ped["estado_pago"] == "POR_RENDIR" and ped["etiqueta_cobro"] == "Cobro por rendir"
    assert _saldo_caja(client, vendedor) == FONDO + 5000
    pendientes = client.get(f"{API}/cobros-por-rendir", headers=auth(deposito)).json()
    assert len(pendientes) == 1 and pendientes[0]["por_rendir"] == 25000
    assert pendientes[0]["conductor_nombre"] == "Pedro Gómez" and pendientes[0]["fecha_entrega"]

    # Rendición: el depósito no cobra; no se rinde más de lo que falta; puede ser en partes y mixta.
    assert _pagar(client, deposito, ped, [{"metodo": "EFECTIVO", "monto": 1000}], "rendir").status_code == 403
    r = _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 30000}], "rendir")
    assert r.status_code == 422 and "superan" in r.json()["detail"]
    r = _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 10000}], "rendir")
    assert r.status_code == 200 and r.json()["pedido"]["estado_pago"] == "POR_RENDIR" and r.json()["pedido"]["saldo"] == 15000
    assert _saldo_caja(client, vendedor) == FONDO + 15000
    r = _pagar(client, vendedor, ped, [{"metodo": "QR", "monto": 5000}, {"metodo": "TRANSFERENCIA", "monto": 10000, "referencia": "op 77"}], "rendir")
    assert r.status_code == 200, r.text
    assert r.json()["pedido"]["estado_pago"] == "PAGADO" and r.json()["pedido"]["etiqueta_cobro"] == "Entregado y pagado"
    assert [x["tipo"] for x in r.json()["pagos"]] == ["ANTICIPO", "RENDICION", "RENDICION", "RENDICION"]
    assert _saldo_caja(client, vendedor) == FONDO + 15000  # solo el efectivo entra al arqueo
    assert client.get(f"{API}/cobros-por-rendir", headers=auth(admin)).json() == []
    assert _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 1}], "rendir").status_code == 409

    # Reportes: lo cobrado por pedidos va aparte del mostrador.
    rep = client.get(f"{API}/reportes/ventas", headers=auth(admin)).json()  # mes en curso, en hora de Paraguay
    assert rep["mostrador"]["total"] == 0
    assert rep["ventas_por_pedidos"]["total"] == 30000 and rep["ventas_por_pedidos"]["cantidad_pedidos"] == 1
    assert {m["metodo_pago"]: m["total"] for m in rep["ventas_por_pedidos"]["por_metodo_pago"]} == {
        "EFECTIVO": 15000, "QR": 5000, "TRANSFERENCIA": 10000,
    }


def test_retiro_en_el_local_pagado_por_adelantado(client):
    admin, vendedor, deposito, p = _preparar(client)
    ped = _pedido(client, vendedor, p, 4, modalidad_entrega="RETIRA_CLIENTE", forma_pago="ANTICIPADO")  # Gs. 12.000
    assert ped["etiqueta_cobro"] == "Falta el pago anticipado"

    r = client.post(f"{API}/ordenes-envio", headers=auth(deposito), json={
        "pedido_cliente_id": ped["id"], "items": [{"producto_id": p["id"], "cantidad": 4}],
    })
    assert r.status_code == 201, r.text
    orden = r.json()
    assert orden["modalidad"] == "RETIRA_CLIENTE" and orden["direccion_entrega"] == "Retira en el local"
    r = accion_envio(client, deposito, orden, "entregar")
    assert r.status_code == 409 and "listo para retirar" in r.json()["detail"]
    assert accion_envio(client, deposito, orden, "lista-despachar").json()["estado"] == "LISTO_RETIRO"
    assert _ver(client, admin, ped)["estado"] == "LISTO_RETIRO"
    assert accion_envio(client, deposito, orden, "despachar").status_code == 409

    # Sin pagar no se entrega, y el stock no se toca.
    r = accion_envio(client, deposito, orden, "entregar")
    assert r.status_code == 409 and "pago anticipado" in r.json()["detail"]
    assert stock(client, admin, p) == 50

    _abrir_caja(client, vendedor)
    r = _pagar(client, vendedor, ped, [{"metodo": "TRANSFERENCIA", "monto": 12000}])
    assert r.status_code == 201 and r.json()["pedido"]["etiqueta_cobro"] == "Pagado a retirar"
    assert _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 1}]).status_code == 422  # ya está pagado

    r = accion_envio(client, deposito, orden, "entregar", {"observaciones": "Retiró el hijo"})
    assert r.status_code == 200 and r.json()["estado"] == "ENTREGADO"
    assert stock(client, admin, p) == 46
    ped = _ver(client, admin, ped)
    assert ped["estado"] == "ENTREGADO" and ped["estado_pago"] == "PAGADO"
    kardex = client.get(f"{API}/inventario/kardex/{p['id']}", headers=auth(admin)).json()
    assert kardex[0]["tipo"] == "SALIDA" and "Retiro en el local" in kardex[0]["observaciones"]

    # A domicilio con pago anticipado: tampoco se despacha sin pagar.
    otro = _pedido(client, vendedor, p, 2, forma_pago="ANTICIPADO")
    orden2 = envio(client, deposito, otro, p, 2)
    accion_envio(client, deposito, orden2, "lista-despachar")
    assert accion_envio(client, deposito, orden2, "despachar").status_code == 409
    _pagar(client, vendedor, otro, [{"metodo": "EFECTIVO", "monto": 6000}])
    assert _ver(client, admin, otro)["etiqueta_cobro"] == "Pagado a entregar"
    assert accion_envio(client, deposito, orden2, "despachar").status_code == 200


def test_pedido_a_cuenta_corriente(client):
    admin, vendedor, deposito, p = _preparar(client)
    cliente = client.post(f"{API}/clientes", headers=auth(admin), json={"nombre": "Constructora", "limite_credito": 50000}).json()
    sin_credito = client.post(f"{API}/clientes", headers=auth(admin), json={"nombre": "Contado"}).json()

    r = client.post(f"{API}/pedidos-cliente", headers=auth(vendedor), json={
        "cliente_nombre": "X", "forma_pago": "CUENTA_CORRIENTE", "items": [{"producto_id": p["id"], "cantidad": 1, "precio_unitario": 3000}],
    })
    assert r.status_code == 422  # a cuenta exige un cliente del catálogo
    contado = _pedido(client, vendedor, p, 1, cliente_id=sin_credito["id"])
    r = client.patch(f"{API}/pedidos-cliente/{contado['id']}/condiciones", headers=auth(vendedor), json={"forma_pago": "CUENTA_CORRIENTE"})
    assert r.status_code == 422 and "crédito" in r.json()["detail"]

    ped = _pedido(client, vendedor, p, 10, cliente_id=cliente["id"], forma_pago="CUENTA_CORRIENTE")  # Gs. 30.000
    assert ped["etiqueta_cobro"] == "A cuenta al entregar"
    _abrir_caja(client, vendedor)
    _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 10000}])  # entrega una seña
    orden = envio(client, deposito, ped, p, 10)
    accion_envio(client, deposito, orden, "lista-despachar")
    assert accion_envio(client, deposito, orden, "despachar").status_code == 200
    assert accion_envio(client, deposito, orden, "entregar").status_code == 200

    ped = _ver(client, admin, ped)
    assert ped["estado_pago"] == "A_CUENTA" and ped["monto_a_cuenta"] == 20000 and ped["etiqueta_cobro"] == "Entregado a cuenta"
    cuenta = client.get(f"{API}/clientes/{cliente['id']}/cuenta-corriente", headers=auth(vendedor)).json()
    assert cuenta["saldo"] == 20000 and cuenta["movimientos"][0]["referencia"] == f"Pedido {ped['numero']}"

    # Otro pedido a cuenta que supera el límite (le quedan 30.000): no sale del depósito.
    grande = _pedido(client, vendedor, p, 11, cliente_id=cliente["id"], forma_pago="CUENTA_CORRIENTE")  # 33.000
    orden = envio(client, deposito, grande, p, 11)
    accion_envio(client, deposito, orden, "lista-despachar")
    r = accion_envio(client, deposito, orden, "despachar")
    assert r.status_code == 422 and "límite" in r.json()["detail"]
    assert stock(client, admin, p) == 40

    # Contra entrega: el cliente no pagó y se carga a su cuenta al rendir.
    r = client.patch(f"{API}/pedidos-cliente/{grande['id']}/condiciones", headers=auth(vendedor), json={"forma_pago": "CONTRA_ENTREGA"})
    assert r.status_code == 200 and r.json()["etiqueta_cobro"] == "Contra entrega"
    assert accion_envio(client, deposito, orden, "despachar").status_code == 200
    assert accion_envio(client, deposito, orden, "entregar").status_code == 200
    r = _pagar(client, vendedor, grande, [{"metodo": "CUENTA_CORRIENTE", "monto": 33000}], "rendir")
    assert r.status_code == 422 and "límite" in r.json()["detail"]
    r = _pagar(client, vendedor, grande, [{"metodo": "EFECTIVO", "monto": 13000}, {"metodo": "CUENTA_CORRIENTE", "monto": 20000}], "rendir")
    assert r.status_code == 200, r.text
    assert r.json()["pedido"]["estado_pago"] == "A_CUENTA"
    assert client.get(f"{API}/clientes/{cliente['id']}/cuenta-corriente", headers=auth(vendedor)).json()["saldo"] == 40000
    # En una seña no se acepta "a cuenta".
    nuevo = _pedido(client, vendedor, p, 1, cliente_id=cliente["id"])
    assert _pagar(client, vendedor, nuevo, [{"metodo": "CUENTA_CORRIENTE", "monto": 1000}]).status_code == 422


def test_condiciones_anulacion_de_sena_y_cancelacion(client):
    admin, vendedor, deposito, p = _preparar(client)
    ped = _pedido(client, vendedor, p, 5)  # Gs. 15.000
    r = client.patch(f"{API}/pedidos-cliente/{ped['id']}/condiciones", headers=auth(vendedor), json={"modalidad_entrega": "RETIRA_CLIENTE"})
    assert r.status_code == 200 and r.json()["modalidad_entrega"] == "RETIRA_CLIENTE" and r.json()["etiqueta_cobro"] == "Paga al retirar"
    assert client.patch(f"{API}/pedidos-cliente/{ped['id']}/condiciones", headers=auth(vendedor), json={"forma_pago": "OTRA"}).status_code == 422

    _abrir_caja(client, vendedor)
    r = _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 8000}])
    pago = r.json()["pagos"][0]
    assert _saldo_caja(client, vendedor) == FONDO + 8000

    # Con cobros: no se baja el total por debajo de lo cobrado, ni se cancela, ni se elimina.
    r = client.put(f"{API}/pedidos-cliente/{ped['id']}", headers=auth(admin), json={
        "cliente_nombre": "Cliente", "items": [{"producto_id": p["id"], "cantidad": 2, "precio_unitario": 3000}],
    })
    assert r.status_code == 422 and "cobrado" in r.json()["detail"]
    r = client.post(f"{API}/pedidos-cliente/{ped['id']}/cancelar", headers=auth(vendedor), json={"motivo": "desistió"})
    assert r.status_code == 409 and "seña" in r.json()["detail"]

    # Un envío en curso impide cambiar la modalidad.
    orden = envio(client, deposito, ped, p, 5)
    r = client.patch(f"{API}/pedidos-cliente/{ped['id']}/condiciones", headers=auth(vendedor), json={"modalidad_entrega": "ENTREGA_DOMICILIO"})
    assert r.status_code == 409
    assert accion_envio(client, deposito, orden, "lista-despachar").json()["estado"] == "LISTO_RETIRO"
    assert accion_envio(client, deposito, orden, "cancelar", {"observaciones": "no viene"}).status_code == 200
    assert _ver(client, admin, ped)["estado"] == "MERCADERIA_RECIBIDA"

    # Devolver la seña: sale de la caja.
    url = f"{API}/pedidos-cliente/{ped['id']}/pagos/{pago['id']}/anular"
    assert client.post(url, headers=auth(deposito), json={"motivo": "x"}).status_code == 403
    r = client.post(url, headers=auth(vendedor), json={"motivo": "Desistió"})
    assert r.status_code == 200, r.text
    assert r.json()["pedido"]["estado_pago"] == "PENDIENTE" and r.json()["pagos"][0]["anulado"] is True
    assert _saldo_caja(client, vendedor) == FONDO
    assert client.post(url, headers=auth(vendedor), json={"motivo": "otra vez"}).status_code == 409
    assert client.delete(f"{API}/pedidos-cliente/{ped['id']}", headers=auth(admin)).status_code == 409
    assert client.post(f"{API}/pedidos-cliente/{ped['id']}/cancelar", headers=auth(vendedor), json={"motivo": "desistió"}).status_code == 200
    assert _pagar(client, vendedor, ped, [{"metodo": "EFECTIVO", "monto": 1000}]).status_code == 409
    assert client.get(f"{API}/pedidos-cliente/999/pagos", headers=auth(admin)).status_code == 404
