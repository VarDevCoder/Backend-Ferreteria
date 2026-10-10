"""Órdenes de envío: cancelación, devolución y borrado sin perder stock ni
dejar pedidos trabados."""
from tests.ayudas import API, accion_envio, auth, configurar, envio, estado_pedido, pedido, producto_con_stock, stock


def _despachado(client, admin, cantidad=4, stock_inicial=10):
    p = producto_con_stock(client, admin, stock=stock_inicial)
    ped = pedido(client, admin, [(p["id"], cantidad)])
    orden = envio(client, admin, ped, p, cantidad)
    assert accion_envio(client, admin, orden, "lista-despachar").status_code == 200
    assert accion_envio(client, admin, orden, "despachar").status_code == 200
    return p, ped, orden


def test_envio_despachado_no_se_cancela_se_devuelve(client):
    """Antes: cancelar un envío en tránsito dejaba el stock descontado para siempre."""
    admin = configurar(client)
    p, ped, orden = _despachado(client, admin)
    assert stock(client, admin, p) == 6

    r = accion_envio(client, admin, orden, "cancelar", {"observaciones": "ya no lo quiere"})
    assert r.status_code == 409
    assert "devolución" in r.json()["detail"]
    assert stock(client, admin, p) == 6
    assert estado_pedido(client, admin, ped) == "ENVIADO"


def test_envio_devuelto_no_traba_el_pedido(client):
    """Antes: el pedido quedaba ENVIADO (estado final) y no se podía reenviar ni cancelar."""
    admin = configurar(client)
    p, ped, orden = _despachado(client, admin)

    r = accion_envio(client, admin, orden, "devolver", {"observaciones": "no había nadie"})
    assert r.status_code == 200, r.text
    assert stock(client, admin, p) == 10
    assert estado_pedido(client, admin, ped) == "MERCADERIA_RECIBIDA"

    # Se puede reenviar...
    nuevo = envio(client, admin, ped, p, 4)
    assert estado_pedido(client, admin, ped) == "LISTO_ENVIO"
    # ...o, cancelando ese envío, cancelar el pedido.
    assert accion_envio(client, admin, nuevo, "cancelar", {"observaciones": "x"}).status_code == 200
    r = client.post(f"{API}/pedidos-cliente/{ped['id']}/cancelar", headers=auth(admin), json={"motivo": "desistió"})
    assert r.status_code == 200, r.text


def test_cancelar_envio_en_preparacion_libera_el_pedido(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    ped = pedido(client, admin, [(p["id"], 2)])
    orden = envio(client, admin, ped, p, 2)
    assert accion_envio(client, admin, orden, "cancelar", {"observaciones": "cambio de dirección"}).status_code == 200
    assert estado_pedido(client, admin, ped) == "MERCADERIA_RECIBIDA"
    assert stock(client, admin, p) == 10


def test_borrar_envio_cancelado_no_retrocede_un_pedido_entregado(client):
    """Antes: borrar el envío cancelado volvía el pedido ENTREGADO a MERCADERIA_RECIBIDA."""
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    ped = pedido(client, admin, [(p["id"], 2)])
    viejo = envio(client, admin, ped, p, 2)
    assert accion_envio(client, admin, viejo, "cancelar", {"observaciones": "x"}).status_code == 200
    nuevo = envio(client, admin, ped, p, 2)
    for accion in ("lista-despachar", "despachar"):
        assert accion_envio(client, admin, nuevo, accion).status_code == 200
    assert accion_envio(client, admin, nuevo, "entregar", {"observaciones": "ok"}).status_code == 200

    assert client.delete(f"{API}/ordenes-envio/{viejo['id']}", headers=auth(admin)).status_code == 200
    assert estado_pedido(client, admin, ped) == "ENTREGADO"


def test_borrar_envio_en_preparacion_libera_el_pedido(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    ped = pedido(client, admin, [(p["id"], 2)])
    orden = envio(client, admin, ped, p, 2)
    assert client.delete(f"{API}/ordenes-envio/{orden['id']}", headers=auth(admin)).status_code == 200
    assert estado_pedido(client, admin, ped) == "MERCADERIA_RECIBIDA"
