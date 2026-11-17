"""ARX-86: /mapa expone el riesgo estimado y /estado las lecturas de los sensores (sin consumir su ruido)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import Sesion, crear_app  # noqa: E402


def _cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def test_mapa_devuelve_riesgo_estimado_con_la_forma_del_terreno():
    datos = _cliente().get("/mapa").json()
    riesgo, tipo = datos["riesgo_estimado"], datos["tipo"]
    assert len(riesgo) == len(tipo) and len(riesgo[0]) == len(tipo[0])
    assert all(0.0 <= v <= 1.0 for fila in riesgo for v in fila)


def test_estado_devuelve_los_sensores_con_sus_claves():
    s = _cliente().get("/estado").json()["sensores"]
    assert {"rumbo", "proximidad", "borde", "gradiente", "vibracion", "riesgo_enfrente", "falla"} <= set(s)
    assert isinstance(s["falla"], bool)
    assert s["riesgo_enfrente"] is None or 0.0 <= s["riesgo_enfrente"] <= 1.0


def test_leer_los_sensores_no_consume_el_ruido_de_la_partida():
    cliente = _cliente()
    partida = cliente.app.state.sesion.partida
    antes = partida.mision.rng.bit_generator.state
    primero = cliente.get("/estado").json()["sensores"]
    segundo = cliente.get("/estado").json()["sensores"]
    assert primero == segundo
    assert partida.mision.rng.bit_generator.state == antes
