"""ARX-28d: /comparacion acepta escenario, con caché por escenario y 400 legible."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import api.servidor as servidor  # noqa: E402
from api.servidor import Sesion, crear_app  # noqa: E402


@pytest.fixture
def cliente():
    servidor._cache_comparacion.clear()
    return TestClient(crear_app(Sesion(semilla=11)))


@pytest.fixture
def motor_falso(monkeypatch):
    """Motor de comparación simulado: cuenta llamadas y registra el escenario pedido."""
    from juego import comparacion as motor
    llamadas = []

    def comparar(semillas, escenario="congelado"):
        llamadas.append((len(list(semillas)), escenario))
        return {"semillas": [1], "variantes": {}, "filas": [], "nota": "x"}
    monkeypatch.setattr(motor, "comparar", comparar)
    monkeypatch.setattr(motor, "ESCENARIOS", {"congelado": {}, "exigente": {}}, raising=False)
    return llamadas


def test_sin_escenario_es_congelado_y_trae_el_campo(cliente, motor_falso):
    datos = cliente.get("/comparacion?semillas=3").json()
    assert datos["escenario"] == "congelado"
    assert motor_falso == [(3, "congelado")]


def test_escenario_exigente_se_calcula_y_se_etiqueta(cliente, motor_falso):
    datos = cliente.get("/comparacion?semillas=3&escenario=exigente").json()
    assert datos["escenario"] == "exigente"
    assert motor_falso == [(3, "exigente")]


@pytest.mark.parametrize("valor", ["otro", "", "EXIGENTE", "1"])
def test_escenario_desconocido_es_400_legible(cliente, motor_falso, valor):
    r = cliente.get("/comparacion", params={"semillas": 3, "escenario": valor})
    assert r.status_code == 400
    assert "congelado" in str(r.json()) and "exigente" in str(r.json())
    assert motor_falso == []


def test_la_cache_distingue_escenarios(cliente, motor_falso):
    cliente.get("/comparacion?semillas=3")
    cliente.get("/comparacion?semillas=3&escenario=exigente")
    cliente.get("/comparacion?semillas=3&escenario=exigente")
    cliente.get("/comparacion?semillas=3")
    assert motor_falso == [(3, "congelado"), (3, "exigente")]


def test_con_20_semillas_sirve_el_json_del_escenario(cliente, motor_falso, tmp_path, monkeypatch):
    import json
    base = tmp_path / "COMPARACION_POLITICAS.json"
    base.write_text(json.dumps({"semillas": [1], "variantes": {}, "filas": [], "marca": "c"}), encoding="utf-8")
    (tmp_path / "COMPARACION_POLITICAS_exigente.json").write_text(
        json.dumps({"semillas": [1], "variantes": {}, "filas": [], "marca": "e"}), encoding="utf-8")
    monkeypatch.setattr(servidor, "COMPARACION_JSON", str(base))
    assert cliente.get("/comparacion").json()["marca"] == "c"
    d = cliente.get("/comparacion?escenario=exigente").json()
    assert d["marca"] == "e" and d["escenario"] == "exigente"
    assert motor_falso == []
