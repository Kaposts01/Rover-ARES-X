"""ARX-28b: escenarios de evaluación del arnés de comparación (congelado y exigente)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from juego import comparacion  # noqa: E402

# Filas del escenario congelado con semillas 1-3, obtenidas ANTES de tocar el código (main, e71d0dd).
_COMUN = {1: (46, 49.0), 2: (52, 39.0), 3: (41, 62.0)}
FILAS_CONGELADO = [
    {"semilla": s, "variante": v, "estado": "EXITO", "exito": True, "pasos": _COMUN[s][0], "colisiones": 0,
     "bateria_final": _COMUN[s][1], "sitios_visitados": 3}
    for v in comparacion.VARIANTES for s in (1, 2, 3)
]

R_PRUEBA, P_PRUEBA = 0.3, 0.6   # valores de prueba (no son los de ARX-28a)


@pytest.fixture
def exigente_fijado(monkeypatch):
    monkeypatch.setitem(comparacion.ESCENARIOS, "exigente", {"nivel": 5, "ruido": R_PRUEBA, "p_detectar": P_PRUEBA})


def test_regresion_congelado_filas_identicas():
    d = comparacion.comparar(range(1, 4))
    assert d["filas"] == FILAS_CONGELADO
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
