"""ARX-87 (ev3-d82 A): batería inicial opcional en POST /partida, entre el 50 y el 150 % del valor por defecto."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import juego.partida as pm  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import Sesion, crear_app  # noqa: E402
from juego.exportar import _configuracion  # noqa: E402
from juego.partida import Partida, bateria_por_defecto  # noqa: E402


def _cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def _partida(cliente, cuerpo):
    return cliente.post("/partida", json=cuerpo)


def test_sin_campo_la_bateria_es_la_de_por_defecto():
    r = _partida(_cliente(), {"semilla": 11, "nivel": 1, "tamano": "pequeno"})
    assert r.status_code == 200
    assert r.json()["bateria"] == bateria_por_defecto(1, 20, 30)


def test_defecto_coincide_con_la_formula_de_partida():
    for nivel, (f, c) in ((1, (20, 30)), (5, (20, 30)), (1, (40, 60)), (5, (40, 60))):
        assert bateria_por_defecto(nivel, f, c) == Partida(semilla=3, nivel=nivel, filas=f, columnas=c).mision.bateria_inicial


def test_dentro_del_rango_la_partida_y_la_exportacion_usan_la_elegida():
    cliente = _cliente()
    r = _partida(cliente, {"semilla": 11, "nivel": 1, "tamano": "pequeno", "bateria": 120})
    assert r.status_code == 200
    assert r.json()["bateria"] == 120
    partida = cliente.app.state.sesion.partida
    assert _configuracion(partida)["bateria_inicial"] == 120


def test_fuera_del_rango_bajo_o_alto_es_422_con_el_motivo():
    cliente = _cliente()
    for valor in (10, 200):
        r = _partida(cliente, {"semilla": 11, "nivel": 1, "tamano": "pequeno", "bateria": valor})
        assert r.status_code == 422
        assert "50–150 %" in r.json()["motivo"]


def test_no_numerico_es_422():
    cliente = _cliente()
    for valor in ("mucha", True, [1]):
        r = _partida(cliente, {"semilla": 11, "nivel": 1, "tamano": "pequeno", "bateria": valor})
        assert r.status_code == 422


def test_la_garantia_recibe_la_bateria_elegida(monkeypatch):
    vistas = []

    def falsa(mundo, bat0, drones, **kw):
        vistas.append(bat0)
        return False

    monkeypatch.setattr(pm, "_es_ganable", falsa)
    p = Partida(semilla=11, nivel=1, filas=20, columnas=30, bateria=120)
    assert vistas and all(b == 120 for b in vistas)
    assert p._sin_garantia and any("Mapa sin garantía" in a for a in p.avisos)
