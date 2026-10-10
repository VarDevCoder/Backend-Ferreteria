"""Stock no vendible (averiado, abollado, vencido...) y reclamos al proveedor:
el stock vendible baja, las unidades siguen existiendo hasta resolverse y
todo queda en el kardex."""
from tests.test_empresa_y_permisos import API, _auth, _configurar, _crear_usuario


def _producto(client, token, nombre, precio_compra, stock):
    p = client.post(f"{API}/productos", headers=_auth(token), json={"nombre": nombre, "precio_compra": precio_compra}).json()
    r = client.post(f"{API}/inventario/ajustes", headers=_auth(token), json={"producto_id": p["id"], "stock_nuevo": stock, "motivo": "Inicial"})
    assert r.status_code == 201, r.text
    return p


def _proveedor(client, token, razon_social, ruc):
    r = client.post(f"{API}/proveedores", headers=_auth(token), json={
        "razon_social": razon_social, "ruc": ruc, "email": f"{ruc}@prov.com", "password": "password-123",
        "direccion": "Zona industrial", "ciudad": "Luque",
    })
    assert r.status_code == 201, r.text
    return r.json()


def _preparar(client):
    admin = _configurar(client)
    deposito = _crear_usuario(client, admin, "deposito@sj.com", "deposito")
    vendedor = _crear_usuario(client, admin, "vende@sj.com", "vendedor")
    taladro = _producto(client, admin, "Taladro", 100000, 20)
    foco = _producto(client, admin, "Foco LED", 10000, 50)
    prov = _proveedor(client, admin, "Distribuidora Central", "80011111-1")
    otro = _proveedor(client, admin, "ElectroPar", "80022222-2")
    return admin, deposito, vendedor, taladro, foco, prov, otro


def _marcar(client, token, producto, cantidad, motivo="AVERIADO", **extra):
    return client.post(f"{API}/stock-no-vendible", headers=_auth(token), json={
        "producto_id": producto["id"], "cantidad": cantidad, "motivo": motivo, **extra,
    })


def _stock(client, token, producto):
    p = client.get(f"{API}/productos/{producto['id']}", headers=_auth(token)).json()
    return p["stock_actual"], p["stock_no_vendible"], p["stock_total"]


def test_marcar_reparar_y_descartar(client):
    admin, deposito, vendedor, taladro, _, prov, _ = _preparar(client)

    r = _marcar(client, deposito, taladro, 5, "ABOLLADO", nota="Caja golpeada", proveedor_id=prov["id"])
    assert r.status_code == 201, r.text
    reg = r.json()
    assert reg["estado"] == "PENDIENTE" and reg["cantidad_pendiente"] == 5 and reg["cantidad_libre"] == 5
    assert reg["costo_unitario"] == 100000 and reg["valor_pendiente"] == 500000
    assert reg["proveedor_nombre"] == "Distribuidora Central" and reg["usuario_nombre"] == "deposito"
    assert _stock(client, admin, taladro) == (15, 5, 20)

    # La caja solo vende el stock vendible.
    assert client.post(f"{API}/caja/turnos/abrir", headers=_auth(vendedor), json={"fondo_inicial": 0}).status_code == 201
    venta = {"items": [{"producto_id": taladro["id"], "cantidad": 16}], "metodo_pago": "EFECTIVO"}
    assert client.post(f"{API}/caja/ventas", headers=_auth(vendedor), json=venta).status_code == 409
    venta["items"][0]["cantidad"] = 15
    assert client.post(f"{API}/caja/ventas", headers=_auth(vendedor), json=venta).status_code == 201
    assert _stock(client, admin, taladro) == (0, 5, 5)
    # El inventario muestra los dos.
    fila = next(p for p in client.get(f"{API}/inventario/stock", headers=_auth(vendedor)).json() if p["id"] == taladro["id"])
    assert fila["stock_actual"] == 0 and fila["stock_no_vendible"] == 5 and fila["stock_total"] == 5

    r = client.post(f"{API}/stock-no-vendible/{reg['id']}/reparar", headers=_auth(deposito), json={"cantidad": 2, "nota": "Se enderezó"})
    assert r.status_code == 200, r.text
    assert r.json()["cantidad_pendiente"] == 3 and r.json()["estado"] == "PENDIENTE"
    r = client.post(f"{API}/stock-no-vendible/{reg['id']}/descartar", headers=_auth(admin), json={"cantidad": 1})
    assert r.status_code == 200, r.text
    assert _stock(client, admin, taladro) == (2, 2, 4)

    # Sin cantidad se resuelve todo lo que queda.
    r = client.post(f"{API}/stock-no-vendible/{reg['id']}/descartar", headers=_auth(admin), json={})
    detalle = r.json()
    assert r.status_code == 200 and detalle["estado"] == "RESUELTO" and detalle["cantidad_pendiente"] == 0
    assert [(x["tipo"], x["cantidad"], x["monto"]) for x in detalle["resoluciones"]] == [
        ("REPARADO", 2, 0), ("DESCARTADO", 1, 100000), ("DESCARTADO", 2, 200000),
    ]
    assert _stock(client, admin, taladro) == (2, 0, 2)
    # Ya resuelto: no se puede volver a resolver.
    assert client.post(f"{API}/stock-no-vendible/{reg['id']}/reparar", headers=_auth(admin), json={}).status_code == 409

    # Kardex: traspaso, venta, reparación y dos bajas, con ambos stocks.
    kardex = client.get(f"{API}/inventario/kardex/{taladro['id']}", headers=_auth(admin)).json()
    movs = [(m["tipo"], m["cantidad"], m["stock_nuevo"], m["no_vendible_nuevo"]) for m in reversed(kardex)]
    assert movs == [
        ("AJUSTE", 20, 20, None), ("TRASPASO", -5, 15, 5), ("SALIDA", 15, 0, None),
        ("TRASPASO", 2, 2, 3), ("BAJA", 1, 2, 2), ("BAJA", 2, 2, 0),
    ]
    assert kardex[0]["referencia_tipo"] == "STOCK_NO_VENDIBLE" and kardex[0]["usuario_id"] is not None
    assert "abollado" in kardex[-2]["observaciones"].lower()

    listado = client.get(f"{API}/stock-no-vendible?estado=RESUELTO", headers=_auth(vendedor)).json()
    assert [x["id"] for x in listado] == [reg["id"]]


def test_marcar_casos_invalidos(client):
    admin, deposito, vendedor, taladro, _, _, _ = _preparar(client)
    r = _marcar(client, deposito, taladro, 21)
    assert r.status_code == 409 and "Stock insuficiente" in r.json()["detail"]
    assert _marcar(client, deposito, taladro, 0).status_code == 422
    assert _marcar(client, deposito, taladro, 1, "ROTO").status_code == 422
    r = _marcar(client, deposito, taladro, 1, "OTRO")
    assert r.status_code == 422 and "nota" in r.json()["detail"]
    assert _marcar(client, deposito, taladro, 1, "OTRO", nota="Le falta una pieza").status_code == 201
    assert _marcar(client, deposito, taladro, 1, proveedor_id=999).status_code == 404
    assert _marcar(client, deposito, taladro, 1, orden_compra_id=999).status_code == 404
    assert _marcar(client, deposito, {"id": 999}, 1).status_code == 404
    assert client.get(f"{API}/stock-no-vendible?estado=NADA", headers=_auth(admin)).status_code == 422

    reg = _marcar(client, deposito, taladro, 3, "VENCIDO").json()
    r = client.post(f"{API}/stock-no-vendible/{reg['id']}/reparar", headers=_auth(deposito), json={"cantidad": 4})
    assert r.status_code == 409
    assert _stock(client, admin, taladro) == (16, 4, 20)

    # Permisos: el vendedor consulta pero no modifica.
    assert client.get(f"{API}/stock-no-vendible", headers=_auth(vendedor)).status_code == 200
    assert _marcar(client, vendedor, taladro, 1).status_code == 403
    assert client.post(f"{API}/stock-no-vendible/{reg['id']}/descartar", headers=_auth(vendedor), json={}).status_code == 403
    assert client.post(f"{API}/reclamos-proveedor", headers=_auth(vendedor), json={"proveedor_id": 1, "items": [{"registro_id": reg["id"]}]}).status_code == 403


def test_reclamo_completo_con_reposicion_nota_de_credito_y_rechazo(client):
    admin, deposito, vendedor, taladro, foco, prov, otro = _preparar(client)
    a = _marcar(client, deposito, taladro, 2, "DEFECTO_FABRICA", proveedor_id=prov["id"]).json()
    b = _marcar(client, deposito, foco, 10, "AVERIADO", nota="Llegaron quemados").json()  # sin proveedor
    c = _marcar(client, deposito, foco, 4, "VENCIDO", proveedor_id=prov["id"]).json()

    r = client.post(f"{API}/reclamos-proveedor", headers=_auth(deposito), json={
        "proveedor_id": prov["id"], "notas": "Mercadería de la última entrega",
        "items": [{"registro_id": a["id"]}, {"registro_id": b["id"], "cantidad": 6}, {"registro_id": c["id"]}],
    })
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["estado"] == "BORRADOR" and rec["numero"].startswith("RCL-") and rec["numero"].endswith("-0001")
    assert rec["proveedor"]["razon_social"] == "Distribuidora Central" and rec["proveedor"]["ruc"] == "80011111-1"
    assert [i["cantidad"] for i in rec["items"]] == [2, 6, 4]
    assert rec["total_reclamado"] == 2 * 100000 + 6 * 10000 + 4 * 10000
    items = {i["registro_id"]: i for i in rec["items"]}

    # Las unidades quedan reservadas y asociadas al proveedor.
    b_ahora = client.get(f"{API}/stock-no-vendible/{b['id']}", headers=_auth(admin)).json()
    assert b_ahora["proveedor_id"] == prov["id"] and b_ahora["cantidad_en_reclamo"] == 6 and b_ahora["cantidad_libre"] == 4
    assert b_ahora["estado"] == "PENDIENTE"
    assert client.get(f"{API}/stock-no-vendible/{a['id']}", headers=_auth(admin)).json()["estado"] == "EN_RECLAMO"
    # Lo reservado no se puede descartar.
    assert client.post(f"{API}/stock-no-vendible/{a['id']}/descartar", headers=_auth(admin), json={}).status_code == 409
    assert client.post(f"{API}/stock-no-vendible/{b['id']}/descartar", headers=_auth(admin), json={"cantidad": 5}).status_code == 409

    # Editar el borrador: B pasa a 7 unidades.
    r = client.put(f"{API}/reclamos-proveedor/{rec['id']}", headers=_auth(deposito), json={
        "notas": "Última entrega",
        "items": [{"registro_id": a["id"]}, {"registro_id": b["id"], "cantidad": 7}, {"registro_id": c["id"]}],
    })
    assert r.status_code == 200, r.text
    items = {i["registro_id"]: i for i in r.json()["items"]}
    assert items[b["id"]]["cantidad"] == 7

    # Antes de aceptar no se resuelven ítems.
    url = f"{API}/reclamos-proveedor/{rec['id']}"
    resolver = lambda reg, cuerpo: client.post(f"{url}/items/{items[reg['id']]['id']}/resolver", headers=_auth(deposito), json=cuerpo)
    assert resolver(a, {"resolucion": "REPOSICION"}).status_code == 409

    r = client.post(f"{url}/enviar", headers=_auth(deposito), json={"numero_nota_remision": "001-001-0000123"})
    assert r.status_code == 200 and r.json()["estado"] == "ENVIADO" and r.json()["fecha_envio"]
    assert r.json()["numero_nota_remision"] == "001-001-0000123"
    assert client.put(url, headers=_auth(deposito), json={"items": [{"registro_id": a["id"]}]}).status_code == 409
    assert client.delete(url, headers=_auth(admin)).status_code == 409
    assert client.post(f"{url}/enviar", headers=_auth(deposito), json={}).status_code == 409
    assert resolver(a, {"resolucion": "REPOSICION"}).status_code == 409

    r = client.post(f"{url}/aceptar", headers=_auth(deposito), json={"respuesta_proveedor": "Aceptan revisar"})
    assert r.status_code == 200 and r.json()["estado"] == "ACEPTADO"
    assert client.post(f"{url}/rechazar", headers=_auth(deposito), json={"motivo": "x"}).status_code == 409

    # A: reposición -> sale lo defectuoso y entra mercadería nueva.
    assert _stock(client, admin, taladro) == (18, 2, 20)
    r = resolver(a, {"resolucion": "REPOSICION", "nota": "Cambiaron los dos"})
    assert r.status_code == 200, r.text
    assert _stock(client, admin, taladro) == (20, 0, 20)
    assert r.json()["estado"] == "ACEPTADO" and r.json()["items_pendientes"] == 2
    # Resolver dos veces el mismo ítem se rechaza.
    r2 = resolver(a, {"resolucion": "NOTA_CREDITO", "monto_nota_credito": 1000})
    assert r2.status_code == 409 and "ya fue resuelto" in r2.json()["detail"]
    assert _stock(client, admin, taladro) == (20, 0, 20)

    # B: nota de crédito (el monto es obligatorio).
    assert resolver(b, {"resolucion": "NOTA_CREDITO"}).status_code == 422
    assert resolver(b, {"resolucion": "OTRA"}).status_code == 422
    r = resolver(b, {"resolucion": "NOTA_CREDITO", "monto_nota_credito": 65000, "numero_nota_credito": "001-002-0000456"})
    assert r.status_code == 200, r.text
    assert r.json()["numero_nota_credito"] == "001-002-0000456" and r.json()["total_nota_credito"] == 65000
    assert _stock(client, admin, foco) == (36, 7, 43)

    # C: el proveedor no acepta ese ítem -> las unidades siguen no vendibles.
    r = resolver(c, {"resolucion": "RECHAZADO", "nota": "Vencido por mal almacenamiento"})
    assert r.status_code == 200
    final = r.json()
    assert final["estado"] == "RESUELTO" and final["fecha_resolucion"] and final["items_pendientes"] == 0
    assert _stock(client, admin, foco) == (36, 7, 43)
    c_ahora = client.get(f"{API}/stock-no-vendible/{c['id']}", headers=_auth(admin)).json()
    assert c_ahora["estado"] == "PENDIENTE" and c_ahora["cantidad_libre"] == 4
    b_ahora = client.get(f"{API}/stock-no-vendible/{b['id']}", headers=_auth(admin)).json()
    assert b_ahora["cantidad_pendiente"] == 3 and b_ahora["estado"] == "PENDIENTE"
    assert b_ahora["resoluciones"][0]["tipo"] == "NOTA_CREDITO_PROVEEDOR" and b_ahora["resoluciones"][0]["monto"] == 65000
    a_ahora = client.get(f"{API}/stock-no-vendible/{a['id']}", headers=_auth(admin)).json()
    assert a_ahora["estado"] == "RESUELTO" and a_ahora["resoluciones"][0]["tipo"] == "REPUESTO_PROVEEDOR"
    assert resolver(c, {"resolucion": "REPOSICION"}).status_code == 409

    # Kardex del taladro: traspaso, salida al proveedor y entrada de la reposición.
    kardex = client.get(f"{API}/inventario/kardex/{taladro['id']}", headers=_auth(admin)).json()
    assert [(m["tipo"], m["referencia_tipo"], m["stock_nuevo"], m["no_vendible_nuevo"]) for m in kardex[:2]] == [
        ("ENTRADA", "RECLAMO_PROVEEDOR", 20, 0), ("SALIDA", "RECLAMO_PROVEEDOR", 18, 0),
    ]

    # Documento para imprimir.
    doc = client.get(f"{url}/documento", headers=_auth(vendedor)).json()
    assert doc["empresa"]["nombre_comercial"] == "Ferretería San José" and doc["empresa"]["ruc"] == "80099999-1"
    assert doc["reclamo"]["numero"] == rec["numero"] and "no válido como comprobante fiscal" in doc["leyenda"]
    assert {i["producto_nombre"] for i in doc["reclamo"]["items"]} == {"Taladro", "Foco LED"}
    assert next(i for i in doc["reclamo"]["items"] if i["registro_id"] == b["id"])["nota_registro"] == "Llegaron quemados"

    # Documentos editables después; solo cambia lo que se manda.
    r = client.patch(f"{url}/documentos", headers=_auth(deposito), json={"numero_nota_remision": "001-001-0000999"})
    assert r.status_code == 200
    assert r.json()["numero_nota_remision"] == "001-001-0000999" and r.json()["numero_nota_credito"] == "001-002-0000456"
    assert client.patch(f"{url}/documentos", headers=_auth(vendedor), json={}).status_code == 403

    # Listados y filtros.
    assert [x["numero"] for x in client.get(f"{API}/reclamos-proveedor?estado=RESUELTO", headers=_auth(vendedor)).json()] == [rec["numero"]]
    assert client.get(f"{API}/reclamos-proveedor?proveedor_id={otro['id']}", headers=_auth(admin)).json() == []


def test_reclamo_casos_invalidos_y_rechazo_total(client):
    admin, deposito, _, taladro, foco, prov, otro = _preparar(client)
    a = _marcar(client, deposito, taladro, 3, proveedor_id=prov["id"]).json()
    b = _marcar(client, deposito, foco, 5, proveedor_id=otro["id"]).json()
    crear = lambda cuerpo: client.post(f"{API}/reclamos-proveedor", headers=_auth(deposito), json=cuerpo)

    assert crear({"proveedor_id": prov["id"], "items": []}).status_code == 422
    assert crear({"proveedor_id": 999, "items": [{"registro_id": a["id"]}]}).status_code == 404
    assert crear({"proveedor_id": prov["id"], "items": [{"registro_id": 999}]}).status_code == 404
    r = crear({"proveedor_id": prov["id"], "items": [{"registro_id": b["id"]}]})
    assert r.status_code == 422 and "otro proveedor" in r.json()["detail"]
    r = crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"], "cantidad": 4}]})
    assert r.status_code == 422 and "quedan 3" in r.json()["detail"]
    assert crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"]}, {"registro_id": a["id"]}]}).status_code == 422

    primero = crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"], "cantidad": 2}]}).json()
    # Solo queda 1 libre para otro reclamo.
    assert crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"], "cantidad": 2}]}).status_code == 422
    segundo = crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"]}]})
    assert segundo.status_code == 201 and segundo.json()["items"][0]["cantidad"] == 1
    assert segundo.json()["numero"].endswith("-0002")
    assert crear({"proveedor_id": prov["id"], "items": [{"registro_id": a["id"]}]}).status_code == 422
    assert client.get(f"{API}/stock-no-vendible/{a['id']}", headers=_auth(admin)).json()["estado"] == "EN_RECLAMO"

    # Borrar un borrador libera sus unidades.
    assert client.delete(f"{API}/reclamos-proveedor/{segundo.json()['id']}", headers=_auth(admin)).status_code == 200
    reg = client.get(f"{API}/stock-no-vendible/{a['id']}", headers=_auth(admin)).json()
    assert reg["estado"] == "PENDIENTE" and reg["cantidad_libre"] == 1
    assert client.get(f"{API}/reclamos-proveedor/{segundo.json()['id']}", headers=_auth(admin)).status_code == 404

    # Rechazo total: las unidades vuelven a quedar libres y el stock no cambia.
    url = f"{API}/reclamos-proveedor/{primero['id']}"
    assert client.post(f"{url}/aceptar", headers=_auth(deposito), json={}).status_code == 409  # todavía en borrador
    assert client.post(f"{url}/enviar", headers=_auth(deposito), json={}).status_code == 200
    assert client.post(f"{url}/rechazar", headers=_auth(deposito), json={"motivo": "  "}).status_code == 422
    r = client.post(f"{url}/rechazar", headers=_auth(deposito), json={"motivo": "Fuera de garantía"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECHAZADO" and r.json()["motivo_rechazo"] == "Fuera de garantía"
    assert [i["resolucion"] for i in r.json()["items"]] == ["RECHAZADO"]
    reg = client.get(f"{API}/stock-no-vendible/{a['id']}", headers=_auth(admin)).json()
    assert reg["estado"] == "PENDIENTE" and reg["cantidad_libre"] == 3 and reg["cantidad_pendiente"] == 3
    assert _stock(client, admin, taladro) == (17, 3, 20)
    assert client.post(f"{url}/aceptar", headers=_auth(deposito), json={}).status_code == 409
    item = r.json()["items"][0]["id"]
    assert client.post(f"{url}/items/{item}/resolver", headers=_auth(deposito), json={"resolucion": "REPOSICION"}).status_code == 409
    assert client.post(f"{url}/items/999/resolver", headers=_auth(deposito), json={"resolucion": "REPOSICION"}).status_code == 404

    # Rechazado el reclamo, las unidades se pueden descartar.
    r = client.post(f"{API}/stock-no-vendible/{a['id']}/descartar", headers=_auth(admin), json={"nota": "Sin garantía"})
    assert r.status_code == 200 and r.json()["estado"] == "RESUELTO"
    assert _stock(client, admin, taladro) == (17, 0, 17)
