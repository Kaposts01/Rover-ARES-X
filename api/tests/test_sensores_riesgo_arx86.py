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


def test_paneles_trae_los_sensores_que_pinta_el_panel_de_supervision():
    s = _cliente().get("/paneles").json()["sensores"]
    assert {"rumbo", "proximidad", "borde", "gradiente", "vibracion", "riesgo_enfrente", "falla"} <= set(s)


def test_falla_de_sensor_responde_200_con_falla_true_en_estado_y_paneles():
    cliente = _cliente()
    r = cliente.post("/evento", json={"nombre": "falla_sensor"})
    assert r.status_code == 200
    assert cliente.get("/estado").status_code == 200
    assert cliente.get("/paneles").status_code == 200
    s = cliente.get("/estado").json()["sensores"]
    assert s["falla"] is True
    assert s["proximidad"] is None and s["borde"] is None and s["gradiente"] is None and s["vibracion"] is None


def test_borde_del_mapa_no_da_riesgo_de_enfrente_y_las_lecturas_son_finitas():
    import math
    from api.servidor import _sensores
    from juego.partida import Partida
    p = Partida(semilla=11, nivel=1, filas=20, columnas=30)
    p.rover.posicion = (0, 5)            # borde superior
    p.rover.rumbo = "N"                  # hacia fuera del mapa
    s = _sensores(p)
    assert s["riesgo_enfrente"] is None
    assert all(v is None or math.isfinite(v) for v in s.values() if isinstance(v, float))


def test_lectura_no_finita_pasa_a_none(monkeypatch):
    import numpy as np
    from api import servidor
    from juego.partida import Partida
    p = Partida(semilla=11, nivel=1, filas=20, columnas=30)
    monkeypatch.setattr(servidor.conduccion, "_observar",
                        lambda partida: {"N": {"rasgos": np.array([np.nan, 0.5, np.inf, 0.1])}})
    s = servidor._sensores(p)
    assert s["proximidad"] is None and s["gradiente"] is None and s["borde"] == 0.5 and s["vibracion"] == 0.1


def test_sin_rumbo_se_rotula_como_tal():
    from api.servidor import _sensores
    from juego.partida import Partida
    p = Partida(semilla=11, nivel=1, filas=20, columnas=30)
    p.rover.rumbo = None
    assert _sensores(p)["rumbo"] == "sin rumbo"


def test_mapa_devuelve_observada_aditiva_paquete_a():
    datos = _cliente().get("/mapa").json()
    obs, tipo = datos["observada"], datos["tipo"]
    assert len(obs) == len(tipo) and len(obs[0]) == len(tipo[0])
    assert all(v in (0, 1) for fila in obs for v in fila)
    assert sum(map(sum, obs)) <= len(tipo) * len(tipo[0])   # al inicio aún no se observó nada (se marca al avanzar)
