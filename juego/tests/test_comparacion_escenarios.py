"""ARX-28b: escenarios de evaluación del arnés de comparación (congelado y exigente)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from juego import comparacion  # noqa: E402

R_PRUEBA, P_PRUEBA = 0.3, 0.6   # valores de prueba (no son los de ARX-28a)


@pytest.fixture
def exigente_fijado(monkeypatch):
    monkeypatch.setitem(comparacion.ESCENARIOS, "exigente", {"nivel": 5, "ruido": R_PRUEBA, "p_detectar": P_PRUEBA})


def test_regresion_congelado_filas_identicas():
    # ARX-45/ev3-d64 (B2 de QA): vigila el JSON publicado. Las 4 variantes originales con 20 semillas deben dar las
    # mismas filas que docs/COMPARACION_POLITICAS.json. Si cambia el código, este test avisa antes que el informe.
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs",
                        "COMPARACION_POLITICAS.json")
    with open(ruta, encoding="utf-8") as f:
        publicado = json.load(f)
    d = comparacion.comparar(range(1, 21))
    obtenidas = [f for f in d["filas"] if f["variante"] in comparacion.VARIANTES_ABLACION]
    esperadas = [f for f in publicado["filas"] if f["variante"] in comparacion.VARIANTES_ABLACION]
    assert len(obtenidas) == 80
    assert obtenidas == esperadas
    assert d["escenario"] == "congelado"


def test_partida_variante_congelado_no_cambia():
    p_def = comparacion.partida_variante(1, "hibrido")
    p_exp = comparacion.partida_variante(1, "hibrido", "congelado")
    assert p_def.nivel == p_exp.nivel == 1
    assert p_exp.mision.sensor.ruido == 0.1
    assert (p_def.mision.riesgo == p_exp.mision.riesgo).all()
    assert p_def.mision.objetivos == p_exp.mision.objetivos


def test_exigente_pendiente_falla_con_mensaje_claro():
    if None not in (comparacion.ESCENARIOS["exigente"]["ruido"], comparacion.ESCENARIOS["exigente"]["p_detectar"]):
        pytest.skip("ARX-28a ya fijó los valores")
    with pytest.raises(ValueError, match="pendiente de ARX-28a"):
        comparacion.partida_variante(1, "hibrido", "exigente")
    with pytest.raises(ValueError, match="pendiente de ARX-28a"):
        comparacion.comparar([1], "exigente")


def test_escenario_desconocido_lanza_valueerror():
    with pytest.raises(ValueError, match="escenario desconocido"):
        comparacion.partida_variante(1, "hibrido", "otro")
    with pytest.raises(ValueError, match="escenario desconocido"):
        comparacion.comparar([1], "otro")


def test_exigente_aplica_parametros_y_es_determinista(exigente_fijado):
    p = comparacion.partida_variante(1, "hibrido", "exigente")
    assert p.nivel == 5
    assert p.mision.sensor.ruido == R_PRUEBA
    assert len(p.mision.mundo.sitios) == 4
    q = comparacion.partida_variante(1, "hibrido", "exigente")
    assert (p.mision.riesgo == q.mision.riesgo).all()
    assert p.mision.objetivos == q.mision.objetivos


def test_exigente_aplica_variante_despues_del_escenario(exigente_fijado):
    p = comparacion.partida_variante(1, "sin_rna", "exigente")
    assert p.mision.usar_rna is False and p.mision.sensor.ruido == R_PRUEBA


def test_exigente_prob_fallo_none_no_cambia_el_sensor():
    assert comparacion.ESCENARIOS["exigente"]["prob_fallo"] is None
    assert comparacion.ESCENARIOS["congelado"]["prob_fallo"] is None
    if None in (comparacion.ESCENARIOS["exigente"]["ruido"], comparacion.ESCENARIOS["exigente"]["p_detectar"]):
        pytest.skip("exigente pendiente de ARX-28a")
    p = comparacion.partida_variante(1, "hibrido", "exigente")
    assert p.mision.sensor.prob_fallo == 0.0


def test_exigente_prob_fallo_de_prueba_llega_al_sensor(monkeypatch):
    monkeypatch.setitem(comparacion.ESCENARIOS, "exigente",
                        {"nivel": 5, "ruido": R_PRUEBA, "p_detectar": P_PRUEBA, "prob_fallo": 0.2})
    p = comparacion.partida_variante(1, "hibrido", "exigente")
    assert p.mision.sensor.prob_fallo == 0.2
    assert p.mision.sensor.ruido == R_PRUEBA
    # el congelado no se ve afectado
    assert comparacion.partida_variante(1, "hibrido", "congelado").mision.sensor.prob_fallo == 0.0


def test_exigente_prob_fallo_es_determinista(monkeypatch):
    monkeypatch.setitem(comparacion.ESCENARIOS, "exigente",
                        {"nivel": 5, "ruido": R_PRUEBA, "p_detectar": P_PRUEBA, "prob_fallo": 0.2})
    a = comparacion.correr(1, "hibrido", "exigente")
    b = comparacion.correr(1, "hibrido", "exigente")
    assert a == b


def test_ruta_corta_existe_en_ambos_escenarios(exigente_fijado):
    for v in ("ruta_corta", "ag_puro"):
        assert v in comparacion.VARIANTES
        for esc in ("congelado", "exigente"):
            f = comparacion.correr(1, v, esc)
            assert f["variante"] == v and f["pasos"] > 0
            assert comparacion.correr(1, v, esc) == f      # determinista


def test_ruta_corta_planifica_sin_riesgos():
    p = comparacion.partida_variante(1, "ruta_corta")
    assert p.mision.usar_rna is False and p.mision.usar_difuso is False
    assert p.mision.riesgo.max() == 0.0


def test_resumen_dispersion_caso_pequeno():
    r = comparacion._resumen([1, 2, 3, 4])
    assert r == {"media": 2.5, "mediana": 2.5, "desviacion": 1.291, "rango_intercuartil": 1.5}
    assert comparacion._resumen([5])["desviacion"] == 0.0


def test_ag_puro_mantiene_el_mapa_de_riesgo_fijo():
    p = comparacion.partida_variante(1, "ag_puro")
    m = p.mision
    inicial = m.riesgo.copy()
    assert m.usar_rna is False and m.usar_difuso is False
    for _ in range(40):
        if p.estado in comparacion.ESTADOS_TERMINALES:
            break
        p.avanzar_ia()
        assert (m.riesgo == inicial).all()
