""""Hoy" es el de la ferretería (America/Asuncion, UTC-3), no el del servidor (UTC).

Las ventas se guardan en UTC. Una venta a las 22:30 de Asunción ya es el día
siguiente en UTC: antes figuraba como del día siguiente en Inicio y reportes."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import text

from app.core.tiempo import hoy, local_a_utc
from tests.ayudas import API, auth, configurar, producto_con_stock


def _vender(client, token, producto) -> dict:
    r = client.post(f"{API}/caja/ventas", headers=auth(token), json={"items": [{"producto_id": producto["id"], "cantidad": 1}]})
    assert r.status_code == 201, r.text
    return r.json()


def _mover(venta_id: int, momento_utc: datetime) -> None:
    from app.infrastructure.db.session import engine

    with engine.begin() as conexion:
        conexion.execute(text("UPDATE ventas_mostrador SET created_at = :m WHERE id = :id"), {"m": momento_utc, "id": venta_id})


def test_local_a_utc():
    assert local_a_utc(datetime(2026, 3, 9, 22, 30)) == datetime(2026, 3, 10, 1, 30)


def test_reporte_cuenta_la_venta_en_el_dia_local(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    venta = _vender(client, admin, p)
    # 9/3 a las 22:30 en Asunción = 10/3 01:30 UTC.
    _mover(venta["id"], datetime(2026, 3, 10, 1, 30))

    rep = client.get(f"{API}/reportes/ventas?desde=2026-03-09&hasta=2026-03-09", headers=auth(admin)).json()
    assert rep["mostrador"]["cantidad_ventas"] == 1
    assert rep["por_dia"] == [{"fecha": "2026-03-09", "cantidad": 1, "total": 3000}]
    assert client.get(f"{API}/reportes/ventas?desde=2026-03-10&hasta=2026-03-10", headers=auth(admin)).json()["mostrador"]["cantidad_ventas"] == 0


def test_ventas_de_hoy_en_hora_local(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    assert client.post(f"{API}/caja/turnos/abrir", headers=auth(admin), json={"fondo_inicial": 0}).status_code == 201
    de_hoy = _vender(client, admin, p)
    de_ayer = _vender(client, admin, p)
    # Hoy a las 00:10 (local) sí es de hoy; ayer a las 23:50 (local) no, aunque en UTC ya sea "hoy".
    _mover(de_hoy["id"], local_a_utc(datetime.combine(hoy(), time(0, 10))))
    _mover(de_ayer["id"], local_a_utc(datetime.combine(hoy() - timedelta(days=1), time(23, 50))))

    resumen = client.get(f"{API}/caja/resumen-hoy", headers=auth(admin)).json()
    assert resumen == {"ventas_hoy": 1, "total_hoy": 3000}


def test_fechas_de_documentos_en_hora_local(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=10)
    r = client.post(f"{API}/pedidos-cliente", headers=auth(admin), json={
        "cliente_nombre": "C", "items": [{"producto_id": p["id"], "cantidad": 1, "precio_unitario": 3000}],
    })
    assert r.json()["fecha_pedido"] == hoy().isoformat()
    assert r.json()["numero"] == f"PED-{hoy().year}-0001"
    assert isinstance(hoy(), date)
