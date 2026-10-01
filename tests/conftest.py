"""Los tests corren contra un Postgres real (el esquema usa tipos y funciones
de Postgres). Definí TEST_DATABASE_URL apuntando a una base descartable:
cada test la vacía y la recrea.

    TEST_DATABASE_URL=postgresql+pg8000://ankor:ankor@localhost:5432/ankor_test pytest
"""
import os

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    # Antes de importar la app: el engine se crea al importar `session.py`.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["ENVIRONMENT"] = "test"
    os.environ["SEED_DEMO"] = "false"


@pytest.fixture
def client():
    if not TEST_DATABASE_URL:
        pytest.skip("Definí TEST_DATABASE_URL para correr los tests de integración")
    from fastapi.testclient import TestClient

    from app.infrastructure.db.models import Base
    from app.infrastructure.db.session import engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
