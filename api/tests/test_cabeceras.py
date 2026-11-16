"""O11: la interfaz se sirve con Cache-Control: no-cache para que el navegador no use módulos JS viejos."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app


def test_raiz_y_estaticos_llevan_no_cache():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    assert cliente.get("/").headers["cache-control"] == "no-cache"
    assert cliente.get("/static/app.js").headers["cache-control"] == "no-cache"


def test_api_no_cambia_su_cabecera():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    assert "no-cache" not in cliente.get("/estado").headers.get("cache-control", "")
