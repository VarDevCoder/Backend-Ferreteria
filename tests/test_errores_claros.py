"""Datos repetidos o con historial: tienen que responder 409/422 con un
mensaje claro (antes eran 500 sin cabecera CORS y la pantalla decía "No se
pudo conectar con el servidor")."""
from tests.ayudas import API, auth, configurar, producto_con_stock

ORIGEN = "http://localhost:5500"


def _post(client, token, ruta, datos):
    return client.post(f"{API}{ruta}", headers={**auth(token), "Origin": ORIGEN}, json=datos)


def test_cliente_con_ruc_o_email_repetido(client):
    admin = configurar(client)
    assert _post(client, admin, "/clientes", {"nombre": "A", "ruc": "80012345-6", "email": "a@x.com"}).status_code == 201
    r = _post(client, admin, "/clientes", {"nombre": "B", "ruc": "80012345-6"})
    assert r.status_code == 409 and "RUC" in r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") == ORIGEN
    r = _post(client, admin, "/clientes", {"nombre": "C", "email": "A@X.com"})
    assert r.status_code == 409 and "email" in r.json()["detail"]
    # Editar otro cliente para ponerle un RUC ajeno también se rechaza.
    otro = _post(client, admin, "/clientes", {"nombre": "D", "ruc": "1-1"}).json()
    r = client.put(f"{API}/clientes/{otro['id']}", headers=auth(admin), json={"nombre": "D", "ruc": "80012345-6"})
    assert r.status_code == 409
    # Un RUC vacío no cuenta como repetido.
    assert _post(client, admin, "/clientes", {"nombre": "E", "ruc": ""}).status_code == 201
    assert _post(client, admin, "/clientes", {"nombre": "F", "ruc": " "}).status_code == 201


def test_proveedor_con_ruc_repetido(client):
    admin = configurar(client)
    datos = {"razon_social": "P1", "ruc": "80099999-1", "email": "p1@p.com", "password": "password-123"}
    assert _post(client, admin, "/proveedores", datos).status_code == 201
    r = _post(client, admin, "/proveedores", {**datos, "razon_social": "P2", "email": "p2@p.com"})
    assert r.status_code == 409 and "RUC" in r.json()["detail"]


def test_categoria_con_nombre_repetido(client):
    admin = configurar(client)
    assert _post(client, admin, "/categorias", {"nombre": "Pinturas"}).status_code == 201
    r = _post(client, admin, "/categorias", {"nombre": "pinturas "})
    assert r.status_code == 409 and "categoría" in r.json()["detail"]


def test_producto_con_historial_no_se_borra(client):
    admin = configurar(client)
    p = producto_con_stock(client, admin, stock=5)
    r = client.delete(f"{API}/productos/{p['id']}", headers={**auth(admin), "Origin": ORIGEN})
    assert r.status_code == 409 and "Desactiv" in r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") == ORIGEN
    # Sin movimientos sí se puede borrar.
    nuevo = producto_con_stock(client, admin, stock=0, nombre="Nuevo")
    assert client.delete(f"{API}/productos/{nuevo['id']}", headers=auth(admin)).status_code == 200


def test_error_inesperado_lleva_cabecera_cors(client, monkeypatch):
    """Un error no previsto responde 500 en JSON y con CORS, para que la
    pantalla muestre el mensaje en vez de "No se pudo conectar"."""
    admin = configurar(client)
    from app.application.services.catalogo_service import CategoriaService

    def explota(*_a, **_k):
        raise RuntimeError("falla de prueba")

    monkeypatch.setattr(CategoriaService, "listar", explota)
    r = client.get(f"{API}/categorias", headers={**auth(admin), "Origin": ORIGEN})
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == ORIGEN
    assert "inesperado" in r.json()["detail"]


def test_conflicto_de_la_base_responde_409(client, monkeypatch):
    """Si algo se escapa de las validaciones y la base lo rechaza, igual es 409."""
    admin = configurar(client)
    from app.infrastructure.db.repositories.catalogo_repository import SqlAlchemyCategoriaRepository

    assert _post(client, admin, "/categorias", {"nombre": "Pinturas"}).status_code == 201
    monkeypatch.setattr(SqlAlchemyCategoriaRepository, "existe_nombre", lambda *_a, **_k: False)
    r = _post(client, admin, "/categorias", {"nombre": "Pinturas"})
    assert r.status_code == 409
    assert r.headers.get("access-control-allow-origin") == ORIGEN


def test_referencia_inexistente_que_llega_a_la_base_responde_422(client, monkeypatch):
    """Si un id inexistente se escapa de las validaciones, la clave foránea de
    la base responde 422 (QA-N2), no 500."""
    admin = configurar(client)
    from app.application.services.catalogo_service import ProductoService

    monkeypatch.setattr(ProductoService, "_validar_categoria", lambda *_a: None)
    r = _post(client, admin, "/productos", {"nombre": "X", "precio_compra": 1, "categoria_id": 9999})
    assert r.status_code == 422 and "no existe" in r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") == ORIGEN
