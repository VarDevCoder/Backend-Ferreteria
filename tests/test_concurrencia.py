"""Numeración sin repetidos y operaciones simultáneas sin pisarse."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient

from app.main import app
from tests.ayudas import API, auth, configurar, pedido, producto_con_stock, stock


def test_numero_de_pedido_no_se_repite_al_borrar(client):
    """Antes: número = cantidad del año + 1. Con PED-0001..0003 y la 0002
    borrada, el siguiente volvía a ser 0003 y fallaba (número único)."""
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=5)
    pedidos = [pedido(client, admin, [(p["id"], 1)]) for _ in range(3)]
    assert client.delete(f"{API}/pedidos-cliente/{pedidos[1]['id']}", headers=auth(admin)).status_code == 200
    nuevo = pedido(client, admin, [(p["id"], 1)])
    assert nuevo["numero"].endswith("-0004")


def _en_paralelo(n, funcion):
    barrera = Barrier(n)

    def tarea(i):
        with TestClient(app) as c:
            barrera.wait()
            return funcion(c, i)

    with ThreadPoolExecutor(n) as ejecutor:
        return list(ejecutor.map(tarea, range(n)))


def test_ventas_simultaneas_no_venden_mas_que_el_stock(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201

    def vender(c, _i):
        return c.post(f"{API}/caja/ventas", headers=auth(admin), json={"items": [{"producto_id": p["id"], "cantidad": 2}]})

    respuestas = _en_paralelo(8, vender)
    exitos = [r.json() for r in respuestas if r.status_code == 201]
    assert sorted(r.status_code for r in respuestas) == [201] * 5 + [409] * 3
    assert stock(client, admin, p) == 0
    assert len({v["numero"] for v in exitos}) == 5
    turno = client.get(f"{API}/caja/turno-abierto", headers=auth(admin)).json()
    assert turno["total_ventas_efectivo"] == 5 * 6000
    kardex = client.get(f"{API}/inventario/kardex/{p['id']}", headers=auth(admin)).json()
    assert sorted(m["stock_nuevo"] for m in kardex if m["tipo"] == "SALIDA") == [0, 2, 4, 6, 8]


def test_pedidos_simultaneos_reciben_numeros_distintos(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=5)

    def crear(c, _i):
        return c.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
            "cliente_nombre": "C", "items": [{"producto_id": p["id"], "cantidad": 1, "precio_unitario": 3000}],
        })

    respuestas = _en_paralelo(6, crear)
    assert [r.status_code for r in respuestas] == [201] * 6
    assert len({r.json()["numero"] for r in respuestas}) == 6


def test_dos_aperturas_simultaneas_dejan_un_solo_turno(client):
    admin = configurar(client)
    respuestas = _en_paralelo(4, lambda c, _i: c.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}))
    assert sorted(r.status_code for r in respuestas) == [201, 409, 409, 409]


def test_ventas_a_cuenta_simultaneas_respetan_el_limite(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=50, precio_venta=10000)
    cliente = client.post(f"{API}/clientes", headers=auth(admin), json={"nombre": "Constructora", "limite_credito": 30000}).json()
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201

    def a_cuenta(c, _i):
        return c.post(f"{API}/caja/ventas", headers=auth(admin), json={
            "cliente_id": cliente["id"], "metodo_pago": "CUENTA_CORRIENTE", "items": [{"producto_id": p["id"], "cantidad": 1}],
        })

    respuestas = _en_paralelo(6, a_cuenta)
    assert sorted(r.status_code for r in respuestas) == [201] * 3 + [422] * 3
    estado = client.get(f"{API}/clientes/{cliente['id']}/cuenta-corriente", headers=auth(admin)).json()
    assert estado["saldo"] == 30000
