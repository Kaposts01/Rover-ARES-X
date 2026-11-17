"""ARX-90: regla de percepción. Un sensor ruidoso no marca como riesgo un sitio pendiente, el inicio ni el refugio."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from genetico import mapa_estimado  # noqa: E402
from integracion import ESTADOS_TERMINALES  # noqa: E402
from juego import comparacion  # noqa: E402
from juego.partida import COLUMNAS_BASE, FILAS_BASE, Partida  # noqa: E402
from simulador import MOVIMIENTOS  # noqa: E402


def _exigente(semilla, variante):
    """Escenario exigente de ARX-28 (nivel 5, ruido 0,6, p_detectar 0,4) armado aquí: no depende de la rama de ARX-28."""
    p = Partida(semilla=semilla, nivel=5, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
    m = p.mision
    m.sensor.ruido = 0.6
    m.riesgo = mapa_estimado(m.mundo, m.rng, p_detectar=0.4)
    m.objetivos = []
    m._planear()
    if variante == "sin_rna":
        m.usar_rna = False
    elif variante == "sin_difuso":
        m.usar_difuso = False
    elif variante == "sin_ag":
        m._optimizar_ag = comparacion._orden_voraz(m)
        m.objetivos = []
        m._planear()
    return p


def test_regresion_semilla_7_exigente_el_hibrido_gana():
    p = _exigente(7, "hibrido")
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < comparacion.MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    assert p.estado == "EXITO"


@pytest.mark.parametrize("variante", comparacion.VARIANTES)
def test_la_regla_se_aplica_a_las_cuatro_variantes(variante):
    p = _exigente(7, variante)
    m = p.mision
    sitio = next(iter(m.mundo.sitios))
    for destino_celda in (sitio, m.mundo.inicio, m.mundo.refugio):
        # un sensor que, con ruido, ve el obstáculo justo en esa celda (rumbo norte, desde la celda de abajo)
        df, dc = MOVIMIENTOS["N"] if "N" in MOVIMIENTOS else list(MOVIMIENTOS.values())[0]
        rumbo = "N" if "N" in MOVIMIENTOS else list(MOVIMIENTOS)[0]
        pos = (destino_celda[0] - df, destino_celda[1] - dc)
        if not m.mundo.dentro(pos):
            continue
        antes = m.riesgo[destino_celda]
        m.riesgo[destino_celda] = 0.0
        m._actualizar_mapa_estimado(pos, rumbo, 1.0)
        assert m.riesgo[destino_celda] == 0.0
        m.riesgo[destino_celda] = antes


def test_una_celda_ordinaria_sigue_marcandose_y_un_sitio_visitado_tambien():
    p = _exigente(7, "hibrido")
    m = p.mision
    rumbo = list(MOVIMIENTOS)[0]
    df, dc = MOVIMIENTOS[rumbo]
    sitios = set(m.mundo.sitios) | {m.mundo.inicio, m.mundo.refugio}
    for f in range(m.mundo.tipo.shape[0]):
        for c in range(m.mundo.tipo.shape[1]):
            celda, pos = (f, c), (f - df, c - dc)
            if celda not in sitios and m.mundo.dentro(pos):
                m.riesgo[celda] = 0.0
                m._actualizar_mapa_estimado(pos, rumbo, 1.0)
                assert m.riesgo[celda] == 1.0
                break
        else:
            continue
        break
    sitio = next(iter(m.mundo.sitios))
    pos = (sitio[0] - df, sitio[1] - dc)
    if m.mundo.dentro(pos):
        m.visitados.add(sitio)
        m.riesgo[sitio] = 0.0
        m._actualizar_mapa_estimado(pos, rumbo, 1.0)
        assert m.riesgo[sitio] == 1.0


def test_la_regla_actua_sobre_su_propia_copia_y_no_toca_el_mapa_real():
    p = _exigente(7, "hibrido")
    antes = p.mision.riesgo.copy()
    p.sugerencia()
    assert np.array_equal(antes, p.mision.riesgo)
    q = copy.deepcopy(p)
    assert q.mision._actualizar_mapa_estimado.__self__ is q
