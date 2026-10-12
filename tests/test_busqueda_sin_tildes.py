"""Búsquedas sin importar tildes ni mayúsculas: en el mostrador se escribe
"bulon" o "latex" y tiene que aparecer "Bulón" o "Pintura látex"."""
from tests.test_empresa_y_permisos import API, _auth, _configurar


def test_busqueda_de_productos_y_clientes_sin_tildes(client):
    admin = _configurar(client)
    for nombre in ["Bulón hexagonal 1/4", "Pintura látex interior 20L", "Caño PVC 1/2", "Tornillo 8x1"]:
        r = client.post(f"{API}/productos", headers=_auth(admin), json={"nombre": nombre, "precio_compra": 1000})
        assert r.status_code == 201, r.text
    client.post(f"{API}/clientes", headers=_auth(admin), json={"nombre": "Juan Benítez"})
    client.post(f"{API}/clientes", headers=_auth(admin), json={"nombre": "Ñandutí S.A."})

    def caja(q):
        return [p["nombre"] for p in client.get(f"{API}/productos/buscar", headers=_auth(admin), params={"q": q}).json()]

    def listado(q):
        return [p["nombre"] for p in client.get(f"{API}/productos", headers=_auth(admin), params={"buscar": q}).json()]

    assert caja("bulon") == ["Bulón hexagonal 1/4"]
    assert caja("LATEX") == ["Pintura látex interior 20L"]
    assert caja("látex 20") == ["Pintura látex interior 20L"]
    assert caja("cano pvc") == ["Caño PVC 1/2"]
    assert caja("bulón") == caja("BULON")
    assert listado("latex") == ["Pintura látex interior 20L"]
    # Los comodines de SQL se buscan como texto, no como "cualquier cosa".
    assert caja("%") == [] and caja("_") == []

    clientes = lambda q: [c["nombre"] for c in client.get(f"{API}/clientes", headers=_auth(admin), params={"busqueda": q}).json()]
    assert clientes("benitez") == ["Juan Benítez"]
    assert clientes("nandu") == ["Ñandutí S.A."]
