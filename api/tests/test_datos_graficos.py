"""Datos de los gráficos por API (ARX-17): AG, difuso, barrido CA-05 y entradas inválidas."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.servidor import Sesion, crear_app  # noqa: E402


@pytest.fixture
def cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def test_ag_historial_incluye_peor_y_desglose_del_mejor(cliente):
    datos = cliente.get("/ag").json()
    gen = datos["generaciones"][0]
    assert gen["peor"] <= gen["media"] <= gen["mejor"]
    des = datos["mejor_desglose"]
    assert {"ciencia", "distancia", "energia", "riesgo", "tiempo", "inviabilidad"} <= set(des)


def test_difuso_devuelve_universos_curvas_entrada_reglas_y_salida(cliente):
    datos = cliente.get("/difuso?distancia=1&bateria=90&inclinacion=2").json()
    assert set(datos["universos"]) == {"distancia", "bateria", "inclinacion", "temperatura"}   # ev3-d40 A: cuatro entradas
    for var, curvas in datos["curvas"].items():
        assert len(curvas["x"]) == 101
        assert len(curvas["conjuntos"]) == 3                       # RF-05: tres conjuntos por variable
        for mu in curvas["conjuntos"].values():
            assert len(mu) == 101 and all(0.0 <= g <= 1.0 for g in mu)
    assert len(datos["reglas"]) >= 8                               # RF-05: al menos ocho reglas
    assert set(datos["punto_entrada"]["distancia"]) == {"cerca", "media", "lejos"}
    assert all({"id", "fuerza", "motivo"} <= set(r) for r in datos["reglas_activadas"])
    assert 0.0 <= datos["salida"]["velocidad"] <= 1.0


def test_difuso_barrido_de_10_a_1_metro_cambia_la_velocidad(cliente):
    # CA-05: al acercar el obstáculo de 10 m a 1 m, la velocidad y las reglas cambian
    datos = cliente.get("/difuso/barrido?desde=10&hasta=1&paso=1&bateria=90&inclinacion=2").json()
    assert len(datos["filas"]) == 10
    assert datos["filas"][0]["distancia"] == 10 and datos["filas"][-1]["distancia"] == 1
    lejos, cerca = datos["filas"][0]["velocidad"], datos["filas"][-1]["velocidad"]
    assert lejos != cerca
    assert datos["filas"][-1]["reglas"] != datos["filas"][0]["reglas"]


@pytest.mark.parametrize("consulta", ["distancia=nan", "distancia=-1", "distancia=25", "distancia=texto",
                                      "bateria=101", "inclinacion=46"])
def test_difuso_entradas_invalidas_son_400_con_motivo(cliente, consulta):
    r = cliente.get("/difuso?" + consulta)
    assert r.status_code == 400
    assert r.json()["motivo"]


def test_barrido_rechaza_rangos_absurdos(cliente):
    assert cliente.get("/difuso/barrido?desde=10&hasta=1&paso=0").status_code == 400
    assert cliente.get("/difuso/barrido?desde=10&hasta=1&paso=0.001").status_code == 400


def test_comparacion_tiene_cuatro_politicas_con_dispersion(cliente):
    # RF-14 y RF-15: híbrido frente a sin RNA, sin difuso y sin AG, con media, mediana y dispersión
    datos = cliente.get("/comparacion?semillas=3").json()
    # ev3-d71: ag_puro no se publica; ruta_corta (voraz) sí, rotulada en la nota
    assert set(datos["variantes"]) == {"hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_mas_corta", "sin_ag_2opt", "ag_puro", "ruta_corta"}
    for r in datos["variantes"].values():
        assert r["n"] == 3
        assert {"media", "mediana", "desviacion", "rango_intercuartil"} <= set(r["pasos"])
        assert 0.0 <= r["tasa_exito"] <= 100.0


def test_comparacion_rechaza_semillas_fuera_de_rango(cliente):
    assert cliente.get("/comparacion?semillas=0").status_code == 400
    assert cliente.get("/comparacion?semillas=41").status_code == 400


def test_temperatura_es_cuarta_entrada_con_reglas_propias(cliente):
    # ev3-d40 A: la temperatura tiene tres conjuntos y dispara sus reglas al cambiar
    fria = cliente.get("/difuso?distancia=18&bateria=30&inclinacion=2&temperatura=-60").json()
    assert set(fria["punto_entrada"]["temperatura"]) == {"fria", "templada", "caliente"}
    assert any(r["id"] == "R11" for r in fria["reglas_activadas"])
    caliente = cliente.get("/difuso?distancia=18&bateria=90&inclinacion=2&temperatura=60").json()
    assert any(r["id"] == "R10" for r in caliente["reglas_activadas"])
    barrido = cliente.get("/difuso/barrido?desde=10&hasta=1&paso=3&bateria=90&inclinacion=2&temperatura=40").json()
    assert barrido["temperatura"] == 40.0 and len(barrido["filas"]) == 4


def test_temperatura_fuera_de_rango_es_400(cliente):
    assert cliente.get("/difuso?temperatura=100").status_code == 400
    assert cliente.get("/difuso?temperatura=nan").status_code == 400


def test_aborto_por_temperatura_excesiva(cliente):
    # ev3-d40 A y §12: temperatura por encima de la tolerancia → aborto con motivo
    alta = cliente.get("/difuso?distancia=10&bateria=80&inclinacion=2&temperatura=70").json()
    assert alta["aborto"]["activo"] is True and "tolerancia" in alta["aborto"]["motivo"]
    normal = cliente.get("/difuso?distancia=10&bateria=80&inclinacion=2&temperatura=20").json()
    assert normal["aborto"]["activo"] is False
