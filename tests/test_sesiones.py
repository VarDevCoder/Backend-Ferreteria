"""Sesiones: cambiar o restablecer la contraseña cierra las sesiones anteriores."""
from tests.ayudas import API, auth, configurar, crear_usuario


def test_cambiar_password_invalida_las_sesiones_anteriores(client):
    admin = configurar(client)
    vendedor = crear_usuario(client, admin, "vende@x.com", "vendedor")
    otra_sesion = client.post(f"{API}/auth/login", json={"email": "vende@x.com", "password": "password-123"}).json()["access_token"]

    r = client.post(f"{API}/auth/cambiar-password", headers=auth(vendedor),
                    json={"password_actual": "password-123", "password_nueva": "otra-clave-456"})
    assert r.status_code == 200, r.text
    nuevo = r.json()["access_token"]

    # Las sesiones abiertas antes del cambio (por ejemplo, en otra computadora) ya no sirven...
    assert client.get(f"{API}/auth/me", headers=auth(otra_sesion)).status_code == 401
    assert client.get(f"{API}/auth/me", headers=auth(vendedor)).status_code == 401
    # ...pero quien cambió la contraseña sigue trabajando con el token nuevo.
    assert client.get(f"{API}/auth/me", headers=auth(nuevo)).status_code == 200


def test_restablecer_password_cierra_la_sesion_del_usuario(client):
    admin = configurar(client)
    vendedor = crear_usuario(client, admin, "vende@x.com", "vendedor")
    usuario_id = client.get(f"{API}/auth/me", headers=auth(vendedor)).json()["id"]
    r = client.post(f"{API}/usuarios/{usuario_id}/restablecer-password", headers=auth(admin), json={"password_nueva": "nueva-clave-789"})
    assert r.status_code == 200, r.text
    assert client.get(f"{API}/auth/me", headers=auth(vendedor)).status_code == 401
    assert client.get(f"{API}/auth/me", headers=auth(admin)).status_code == 200
