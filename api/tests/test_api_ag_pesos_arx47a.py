"""ARX-47a: /ag acepta pesos w_* en [0, 5], los guarda en la sesión y los separa en la caché."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import api.servidor as servidor  # noqa: E402
from api.servidor import Sesion, crear_app  # noqa: E402
from genetico import PESOS_POR_DEFECTO  # noqa: E402


@pytest.fixture
def cliente():
    servidor._cache_ag.clear()
    return TestClient(crear_app(Sesion(semilla=11)))


def test_sin_pesos_la_respuesta_es_la_de_siempre(cliente):
    d = cliente.get("/ag").json()
    assert d["parametros"]["pesos"] == PESOS_POR_DEFECTO


def test_pesos_pedidos_salen_en_parametros_y_cambian_el_fitness(cliente):
    base = cliente.get("/ag").json()
    d = cliente.get("/ag?w_ciencia=2&w_riesgo=0.2").json()
    assert d["parametros"]["pesos"] == {**PESOS_POR_DEFECTO, "ciencia": 2.0, "riesgo": 0.2}
    assert [c["fitness"] for c in d["candidatos"]] != [c["fitness"] for c in base["candidatos"]]


def test_los_pesos_quedan_en_la_sesion_y_se_reutilizan(cliente):
    cliente.get("/ag?w_ciencia=2")
    d = cliente.get("/ag").json()
    assert d["parametros"]["pesos"]["ciencia"] == 2.0
    d = cliente.get("/ag?w_ciencia=0").json()
    assert d["parametros"]["pesos"]["ciencia"] == 0.0


def test_la_cache_incluye_los_pesos(cliente):
    a = cliente.get("/ag").json()
    b = cliente.get("/ag?w_tiempo=5").json()
    assert a["parametros"]["pesos"] != b["parametros"]["pesos"]
    assert cliente.get("/ag?w_tiempo=5").json() == b
    assert len(servidor._cache_ag) == 2


@pytest.mark.parametrize("consulta", ["w_ciencia=-0.1", "w_riesgo=5.01", "w_tiempo=abc", "w_energia=nan",
                                      "w_distancia=inf", "w_ciencia="])
def test_pesos_invalidos_son_400_legibles(cliente, consulta):
    r = cliente.get("/ag?" + consulta)
    assert r.status_code == 400
    assert "entre 0 y 5" in str(r.json()) or "número" in str(r.json())


def test_un_peso_invalido_no_se_guarda(cliente):
    cliente.get("/ag?w_ciencia=2")
    assert cliente.get("/ag?w_riesgo=9").status_code == 400
    assert cliente.get("/ag").json()["parametros"]["pesos"] == {**PESOS_POR_DEFECTO, "ciencia": 2.0}
