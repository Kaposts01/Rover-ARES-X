"""Paquete A: `observadas` es solo de registro. Se marca, y no cambia ninguna partida (bitácora, resultado ni rng)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import integracion  # noqa: E402
from integracion import ALCANCE_OBSERVACION, Mision  # noqa: E402
from simulador import generar_mundo  # noqa: E402


def _correr(semilla, registrar=True, monkeypatch=None):
    mundo = generar_mundo(semilla=semilla, filas=20, columnas=30, n_obstaculos=20, n_barrancos=3, n_sitios=3)
    m = Mision(mundo, semilla=semilla)
    if not registrar:
        monkeypatch.setattr(Mision, "_registrar_observacion", lambda self, *a, **k: None)
    res = m.ejecutar(max_pasos=60)
    return m, res


def test_observadas_se_marca_en_el_rover_y_en_el_rumbo():
    m, _ = _correr(5)
    assert m.observadas.shape == m.mundo.tipo.shape and m.observadas.dtype == bool
    assert m.observadas[m.mundo.inicio]
    assert m.observadas.sum() > 1
    # sin lectura de proximidad nada más que la celda propia
    m2 = Mision(generar_mundo(semilla=1), semilla=1)
    assert not m2.observadas.any()
    m2._registrar_observacion((10, 10), "N", float("nan"))
    assert m2.observadas.sum() == 1
    m2._registrar_observacion((10, 10), "E", 99.0)
    assert m2.observadas[10, 10 + ALCANCE_OBSERVACION] and not m2.observadas[10, 10 + ALCANCE_OBSERVACION + 1]
    m2._registrar_observacion((10, 10), "S", 3.2)
    assert m2.observadas[13, 10] and not m2.observadas[14, 10]


@pytest.mark.parametrize("semilla", [3, 8, 21])
def test_registrar_observadas_no_cambia_la_partida(semilla, monkeypatch):
    con, r_con = _correr(semilla)
    sin, r_sin = _correr(semilla, registrar=False, monkeypatch=monkeypatch)
    assert r_con == r_sin
    assert con.log.filas and repr(con.log.filas) == repr(sin.log.filas)
    assert con.rng.bit_generator.state == sin.rng.bit_generator.state
    assert np.array_equal(con.riesgo, sin.riesgo)
    assert not sin.observadas.any() and con.observadas.any()
