"""El commit de la sesión de base tiene que ocurrir ANTES de mandar la
respuesta: si no, la pantalla recibe "guardado" sin que lo esté, y un error
al guardar no le llega nunca (FastAPI corre después de responder el cierre
de las dependencias con scope "request")."""
import asyncio
import json

from sqlalchemy.orm import Session

from tests.test_empresa_y_permisos import ADMIN, API, _configurar


def test_el_commit_ocurre_antes_de_la_respuesta(client, monkeypatch):
    from app.main import app

    _configurar(client)
    token = client.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]}).json()["access_token"]
    eventos: list[str] = []
    commit_original = Session.commit

    def commit(self, *args, **kwargs):
        eventos.append("commit")
        return commit_original(self, *args, **kwargs)

    monkeypatch.setattr(Session, "commit", commit)
    cuerpo = json.dumps({"nombre": "Cliente nuevo"}).encode()

    async def recibir():
        return {"type": "http.request", "body": cuerpo, "more_body": False}

    async def enviar(mensaje):
        if mensaje["type"] == "http.response.start":
            eventos.append(f"respuesta {mensaje['status']}")

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": f"{API}/clientes", "raw_path": f"{API}/clientes".encode(), "query_string": b"",
        "headers": [(b"content-type", b"application/json"), (b"host", b"test"), (b"authorization", f"Bearer {token}".encode())],
        "client": ("127.0.0.1", 1), "server": ("test", 80),
    }
    asyncio.run(app(scope, recibir, enviar))
    assert eventos[-1] == "respuesta 201", eventos
    assert "commit" in eventos[:-1], eventos
