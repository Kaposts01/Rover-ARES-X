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
    datos = cliente.get("/rna?proximidad=2&desnivel=-3&contraste=-0.8&vibracion=0").json()
    assert set(datos["entrada"]) == {"proximidad_frontal_m", "desnivel_frontal_m", "contraste_optico", "vibracion"}
    assert datos["modelo"] == {"perfil": "v2", "rasgos": list(datos["entrada"])}   # ARX-94d: modelo activo
    assert len(datos["activaciones"]["oculta_1"]) == 32          # MLP de 32 y 16 neuronas (§10.1)
    assert len(datos["activaciones"]["oculta_2"]) == 16
    assert all(v >= 0 for v in datos["activaciones"]["oculta_1"])  # ReLU
    assert abs(sum(datos["probabilidades"].values()) - 1.0) < 0.01  # softmax de tres clases
    assert set(datos["probabilidades"]) == {"libre", "obstáculo", "barranco"}
    assert isinstance(datos["accion"], str) and datos["accion"]


def test_rna_cambiar_la_entrada_cambia_las_probabilidades(cliente):
    a = cliente.get("/rna?proximidad=18&desnivel=0&contraste=0&vibracion=0").json()["probabilidades"]
    b = cliente.get("/rna?proximidad=2&desnivel=-3&contraste=-0.8&vibracion=0").json()["probabilidades"]
    assert a != b


def test_rna_evaluacion_da_matriz_macro_f1_y_recall_de_barrancos(cliente):
    datos = cliente.get("/rna/evaluacion").json()
    matriz = datos["matriz_confusion"]
    assert len(matriz) == 3 and all(len(f) == 3 for f in matriz)
    assert 0.0 <= datos["macro_f1"] <= 1.0
    assert 0.0 <= datos["recall_barranco"] <= 1.0
    assert 0.0 <= datos["linea_base_exactitud"] <= 1.0
    assert datos["muestras_prueba"] > 0
    assert datos["perfil"] == "v2" and datos["rasgos"][1] == "desnivel_frontal_m"   # ARX-94d: modelo activo


def test_rna_v1_sigue_disponible_por_perfil_con_sus_rasgos(cliente):
    datos = cliente.get("/rna/evaluacion?modelo=juego&perfil=v1").json()
    assert datos["perfil"] == "v1" and datos["rasgos"][1] == "borde_barranco"
    assert cliente.get("/rna/evaluacion?perfil=v9").status_code == 400


@pytest.mark.parametrize("consulta", ["proximidad=nan", "proximidad=25", "borde=2", "desnivel=99", "contraste=5", "vibracion=texto"])
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


def test_rna_red_da_forma_y_pesos_coherentes_con_las_activaciones(cliente):
    red = cliente.get("/rna/red").json()
    act = cliente.get("/rna").json()
    assert red["capas"] == [len(red["modelo"]["rasgos"]), 32, 16, 3]
    assert red["modelo"] == act["modelo"]
    assert len(red["pesos"]) == 3
    for i, W in enumerate(red["pesos"]):
        assert len(W) == red["capas"][i] and all(len(f) == red["capas"][i + 1] for f in W)
    assert set(red["clases"]) == set(act["probabilidades"])


def test_ia_del_paso_muestra_lo_que_la_ia_uso_en_ese_paso():
    # El panel en vivo usa /ia/paso: las entradas son las del paso real, no las de un laboratorio con valores por defecto
    c = TestClient(crear_app(Sesion(semilla=77, nivel=4)))
    assert c.get("/ia/paso").json()["hay_paso"] is False
    inclinaciones = set()
    for _ in range(10):
        c.post("/paso")
        d = c.get("/ia/paso").json()
        assert d["hay_paso"] is True
        # el difuso recalculado con las entradas del paso da la misma velocidad que usó el motor
        assert d["difuso"]["salida"]["velocidad"] == pytest.approx(d["difuso"]["velocidad_usada"], abs=1e-3)
        # la RNA con los rasgos del paso da las probabilidades que usó el motor
        for k, v in d["rna"]["probabilidades_usadas"].items():
            assert d["rna"]["probabilidades"][k] == pytest.approx(v, abs=2e-3)
        assert d["ag"]["celdas_restantes"] == len(d["ag"]["ruta"]) - 1
        inclinaciones.add(round(d["difuso"]["entradas"]["inclinacion"], 1))
    assert len(inclinaciones) > 1      # la inclinación real cambia con el terreno (el laboratorio la deja en 0)
    assert d["ag"]["generaciones"]     # el AG es el del plan en juego
