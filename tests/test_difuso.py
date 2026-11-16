import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from difuso import CONJUNTOS, REGLAS, FuzzyController, trapecio  # noqa: E402


def test_hay_al_menos_ocho_reglas_y_tres_conjuntos_por_variable():
    assert len(REGLAS) >= 8
    for var, conjuntos in CONJUNTOS.items():
        assert len(conjuntos) >= 3, var


def test_membresias_en_rango_cero_uno():
    ctrl = FuzzyController()
    for d in np.linspace(0, 20, 21):
        mu = ctrl.fusificar(d, 50, 20)
        for var in mu:
            for grado in mu[var].values():
                assert 0.0 <= grado <= 1.0


def test_trapecio_forma_basica():
    assert trapecio(7, 0, 0, 3, 6) == pytest.approx(0.0)
    assert trapecio(1, 0, 0, 3, 6) == pytest.approx(1.0)
    assert trapecio(4.5, 0, 0, 3, 6) == pytest.approx(0.5)
    assert trapecio(5, 0, 0, 3, 6) == pytest.approx(1 / 3)


def test_obstaculo_cerca_implica_parar():
    r = FuzzyController().inferir(distancia=1.0, bateria=90, inclinacion=5)
    assert r.velocidad < 0.15
    assert any(rid == "R1" for rid, _, _ in r.reglas_activadas)


def test_camino_libre_bateria_alta_implica_rapida():
    r = FuzzyController().inferir(distancia=18, bateria=90, inclinacion=2)
    assert r.velocidad > 0.7
    assert any(rid == "R4" for rid, _, _ in r.reglas_activadas)


def test_bateria_critica_limita_velocidad():
    r = FuzzyController().inferir(distancia=18, bateria=5, inclinacion=2)
    assert r.velocidad < 0.45


def test_velocidad_cambia_al_acercar_obstaculo():
    ctrl = FuzzyController()
    lejos = ctrl.inferir(distancia=10, bateria=80, inclinacion=3).velocidad
    cerca = ctrl.inferir(distancia=1, bateria=80, inclinacion=3).velocidad
    assert cerca < lejos


def test_caso_con_multiples_reglas_activas():
    r = FuzzyController().inferir(distancia=8, bateria=30, inclinacion=25)
    assert len(r.reglas_activadas) >= 2
    assert 0.0 <= r.velocidad <= 1.0


def test_salida_en_rango_y_sin_fallback_en_caso_normal():
    r = FuzzyController().inferir(distancia=10, bateria=60, inclinacion=15)
    assert 0.0 <= r.velocidad <= 1.0
    assert r.fallback is False


def test_entrada_nan_degrada_a_fallback_sin_excepcion():
    r = FuzzyController().inferir(distancia=float("nan"), bateria=60, inclinacion=15)
    assert r.fallback is True
    assert r.velocidad == 0.0
