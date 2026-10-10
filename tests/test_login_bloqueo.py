"""Bloqueo de login por email + IP: quien prueba contraseñas desde una
conexión queda bloqueado, pero no puede dejar afuera al admin que entra
desde otra (antes el bloqueo era solo por email)."""
from tests.ayudas import API, configurar

ADMIN = {"email": "admin@prueba.com", "password": "password-123"}


def _login(client, password, ip, email=ADMIN["email"]):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password}, headers={"X-Forwarded-For": ip})


def test_atacante_no_bloquea_al_admin_desde_otra_conexion(client):
    configurar(client)
    for _ in range(5):
        assert _login(client, "mal", "203.0.113.9").status_code == 401
    # Desde la conexión del atacante, bloqueado (aunque acierte):
    r = _login(client, ADMIN["password"], "203.0.113.9")
    assert r.status_code == 403 and "intentos" in r.json()["detail"]
    # El admin, desde su conexión, entra igual.
    assert _login(client, ADMIN["password"], "198.51.100.7").status_code == 200


def test_una_conexion_que_prueba_muchos_emails_se_bloquea(client):
    configurar(client)
    for i in range(30):
        _login(client, "mal", "203.0.113.50", email=f"usuario{i}@prueba.com")
    r = _login(client, ADMIN["password"], "203.0.113.50")
    assert r.status_code == 403
    assert _login(client, ADMIN["password"], "198.51.100.7").status_code == 200


def test_la_ip_es_la_primera_de_x_forwarded_for(client):
    """Vercel pone la IP real del cliente al principio de X-Forwarded-For."""
    configurar(client)
    for _ in range(5):
        _login(client, "mal", "203.0.113.9, 10.0.0.1")
    assert _login(client, ADMIN["password"], "203.0.113.9, 10.0.0.2").status_code == 403


def test_ataque_repartido_demora_pero_no_bloquea():
    """Muchos fallos para un email desde IPs distintas: cada intento espera
    un poco más (hasta 3 s), pero el email no queda bloqueado."""
    from app.application.services.usuario_service import LimiteDeIntentos

    class Memoria:
        def __init__(self):
            self.fallos = []

        def contar_recientes(self, _ventana, email=None, ip=None):
            return sum(1 for e, i in self.fallos if (email is None or e == email) and (ip is None or i == ip))

        def registrar_fallo(self, email, ip):
            self.fallos.append((email, ip))

        def limpiar(self, *_a):
            pass

    esperas = []
    limite = LimiteDeIntentos(Memoria(), dormir=esperas.append)
    for n in range(12):
        limite.verificar("admin@x.com", f"10.0.0.{n}")  # nunca lanza: cada IP tiene un solo fallo
        limite.registrar_fallo("admin@x.com", f"10.0.0.{n}")
    assert esperas == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
