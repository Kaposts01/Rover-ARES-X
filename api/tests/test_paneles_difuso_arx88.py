"""QA ARX-88: «usado» del difuso sale del paso mostrado, no del modo actual de la sesión."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import Sesion, crear_app  # noqa: E402


def _cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def test_tras_un_paso_en_rna_y_pasar_a_manual_el_difuso_sigue_no_usado():
    c = _cliente()
    assert c.post("/modo", json={"modo": "rna"}).status_code == 200
    assert c.post("/paso").status_code == 200
    assert c.post("/modo", json={"modo": "manual"}).status_code == 200
    d = c.get("/paneles").json()["difuso"]
    assert d["usado"] is False
    assert d["velocidad"] is None


def test_sin_pasos_el_difuso_sigue_al_modo_de_la_sesion():
    c = _cliente()
    assert c.post("/modo", json={"modo": "rna"}).status_code == 200
    assert c.get("/paneles").json()["difuso"]["usado"] is False


def test_sin_pasos_en_modo_difuso_usado_es_true_y_hay_velocidad():
    # QA/Orquestador: antes del primer paso el panel de difuso debe mostrar la sugerencia actual, no un vacío
    c = _cliente()
    assert c.post("/modo", json={"modo": "difuso"}).status_code == 200
    d = c.get("/paneles").json()["difuso"]
    assert d["usado"] is True
    assert d["velocidad"] is not None
