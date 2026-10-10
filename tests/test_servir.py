"""servir.py: arranque del servidor único fuera de Vercel (instalación Windows)."""
import servir


def test_cargar_config_respeta_el_entorno_y_tolera_bom(tmp_path, monkeypatch):
    archivo = tmp_path / "sail.env"
    archivo.write_bytes(
        "﻿# comentario\nSAIL_PRUEBA_A=uno\nSAIL_PRUEBA_B = dos=con-igual \n\nlinea-sin-igual\nSAIL_PRUEBA_C=del-archivo\n".encode("utf-8")
    )
    monkeypatch.delenv("SAIL_PRUEBA_A", raising=False)
    monkeypatch.delenv("SAIL_PRUEBA_B", raising=False)
    monkeypatch.setenv("SAIL_PRUEBA_C", "del-entorno")
    servir.cargar_config(archivo)
    import os

    assert os.environ["SAIL_PRUEBA_A"] == "uno"
    assert os.environ["SAIL_PRUEBA_B"] == "dos=con-igual"
    assert os.environ["SAIL_PRUEBA_C"] == "del-entorno"  # lo del entorno tiene prioridad
    for nombre in ("SAIL_PRUEBA_A", "SAIL_PRUEBA_B"):
        monkeypatch.delenv(nombre)
