"""Servidor único (FRONTEND_DIR): el backend sirve el frontend en `/` y la API
sigue en /api/v1 en el mismo origen."""
import importlib

import pytest

from tests.ayudas import API, auth, configurar

ENV_JS_ORIGINAL = 'window.__SAIL_API_BASE__ = "https://ankor-backend.vercel.app/api/v1";\n'


@pytest.fixture
def frontend(tmp_path):
    (tmp_path / "assets" / "js").mkdir(parents=True)
    (tmp_path / "assets" / "css").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<!doctype html><title>Dashboard — SAIL</title>", encoding="utf-8")
    (tmp_path / "login.html").write_text("<!doctype html><title>Ingresar — SAIL</title>", encoding="utf-8")
    (tmp_path / "assets" / "js" / "env.js").write_text(ENV_JS_ORIGINAL, encoding="utf-8")
    (tmp_path / "assets" / "js" / "config.js").write_text("export const API_BASE_URL = window.__SAIL_API_BASE__;", encoding="utf-8")
    (tmp_path / "assets" / "css" / "styles.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client_unico(client, frontend, monkeypatch):
    """La app armada de nuevo con FRONTEND_DIR (y restaurada al terminar)."""
    from fastapi.testclient import TestClient

    import app.main
    from app.core.config import get_settings

    monkeypatch.setenv("FRONTEND_DIR", str(frontend))
    get_settings.cache_clear()
    try:
        modulo = importlib.reload(app.main)
        with TestClient(modulo.app) as c:
            yield c
    finally:
        monkeypatch.delenv("FRONTEND_DIR")
        get_settings.cache_clear()
        importlib.reload(app.main)


def test_sin_frontend_la_raiz_sigue_siendo_el_chequeo_de_salud(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert client.get(f"{API}/salud").json()["status"] == "ok"


def test_sirve_index_y_assets(client_unico):
    r = client_unico.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Dashboard — SAIL" in r.text
    assert r.headers["cache-control"] == "no-cache"

    r = client_unico.get("/login.html")
    assert r.status_code == 200 and "Ingresar" in r.text

    r = client_unico.get("/assets/js/config.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")

    r = client_unico.get("/assets/css/styles.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")

    r = client_unico.get("/manifest.webmanifest")
    assert r.headers["content-type"].startswith("application/manifest+json")


def test_revalida_con_etag(client_unico):
    r = client_unico.get("/assets/js/config.js")
    r2 = client_unico.get("/assets/js/config.js", headers={"If-None-Match": r.headers["etag"]})
    assert r2.status_code == 304


def test_env_js_apunta_al_mismo_origen(client_unico):
    r = client_unico.get("/assets/js/env.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")
    # Conserva el env.js original (tema, letra...) y al final fija la API en el mismo origen.
    assert r.text.startswith(ENV_JS_ORIGINAL)
    assert r.text.rstrip().endswith('window.__SAIL_API_BASE__ = window.location.origin + "/api/v1";')


def test_no_sirve_archivos_ocultos_ni_sale_de_la_carpeta(client_unico):
    assert client_unico.get("/.git/config").status_code == 404
    assert client_unico.get("/no-existe.html").status_code == 404
    assert client_unico.get("/assets/../../etc/passwd").status_code == 404


def test_la_api_sigue_respondiendo_en_el_mismo_origen(client_unico):
    r = client_unico.get(f"{API}/salud")
    assert r.status_code == 200 and r.json()["status"] == "ok"

    r = client_unico.get(f"{API}/configuracion-inicial")
    assert r.json() == {"requiere_configuracion": True}

    token = configurar(client_unico)
    r = client_unico.post(f"{API}/auth/login", json={"email": "admin@prueba.com", "password": "password-123"})
    assert r.status_code == 200
    assert client_unico.get(f"{API}/auth/me", headers=auth(token)).status_code == 200

    # Una ruta de API que no existe sigue respondiendo JSON, no una página.
    r = client_unico.get(f"{API}/no-existe")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}

    assert client_unico.get("/docs").status_code == 200
    assert client_unico.get("/openapi.json").status_code == 200


def test_frontend_dir_sin_index_no_arranca(tmp_path):
    from fastapi import FastAPI

    from app.interfaces.web.frontend import montar_frontend

    with pytest.raises(RuntimeError, match="index.html"):
        montar_frontend(FastAPI(), tmp_path)
