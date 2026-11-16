"""Laboratorio RNA por API (ARX-17, CA-06): entrada → normalización → activaciones → probabilidades → acción."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.servidor import Sesion, crear_app  # noqa: E402


@pytest.fixture
def cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def test_rna_expone_cada_etapa_del_flujo(cliente):
    datos = cliente.get("/rna?proximidad=2&borde=1&gradiente=0&vibracion=0").json()
    assert set(datos["entrada"]) == {"proximidad_frontal_m", "borde_barranco", "gradiente_altura_m", "vibracion"}
    assert len(datos["activaciones"]["oculta_1"]) == 32          # MLP de 32 y 16 neuronas (§10.1)
    assert len(datos["activaciones"]["oculta_2"]) == 16
    assert all(v >= 0 for v in datos["activaciones"]["oculta_1"])  # ReLU
    assert abs(sum(datos["probabilidades"].values()) - 1.0) < 0.01  # softmax de tres clases
    assert set(datos["probabilidades"]) == {"libre", "obstáculo", "barranco"}
    assert isinstance(datos["accion"], str) and datos["accion"]


def test_rna_cambiar_la_entrada_cambia_las_probabilidades(cliente):
    a = cliente.get("/rna?proximidad=18&borde=0&gradiente=0&vibracion=0").json()["probabilidades"]
    b = cliente.get("/rna?proximidad=2&borde=1&gradiente=0&vibracion=0").json()["probabilidades"]
    assert a != b


def test_rna_evaluacion_da_matriz_macro_f1_y_recall_de_barrancos(cliente):
    datos = cliente.get("/rna/evaluacion").json()
    matriz = datos["matriz_confusion"]
    assert len(matriz) == 3 and all(len(f) == 3 for f in matriz)
    assert 0.0 <= datos["macro_f1"] <= 1.0
    assert 0.0 <= datos["recall_barranco"] <= 1.0
    assert 0.0 <= datos["linea_base_exactitud"] <= 1.0
    assert datos["muestras_prueba"] > 0


@pytest.mark.parametrize("consulta", ["proximidad=nan", "proximidad=25", "borde=2", "vibracion=texto"])
def test_rna_entradas_invalidas_son_400(cliente, consulta):
    r = cliente.get("/rna?" + consulta)
    assert r.status_code == 400
    assert r.json()["motivo"]


def test_serie_por_paso_tiene_bateria_velocidad_y_accion(cliente):
    cliente.post("/modo", json={"modo": "difuso"})
    cliente.post("/paso")
    cliente.post("/paso")
    filas = cliente.get("/serie").json()["filas"]
    assert len(filas) == 2
    assert {"bateria", "velocidad", "accion", "fitness"} <= set(filas[0])
    assert filas[0]["velocidad"] is not None
