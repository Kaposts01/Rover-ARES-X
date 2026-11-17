"""ARX-92c (ev3-d73 A): escenario exigente10 (10 sitios, batería de referencia) y línea base 2-opt."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego import comparacion  # noqa: E402
from juego.partida import Partida, FILAS_BASE, COLUMNAS_BASE  # noqa: E402

PAR = comparacion.ESCENARIOS["exigente10"]


def test_exigente10_tiene_diez_sitios_y_exigente_no_cambia():
    assert PAR["n_sitios"] == 10 and PAR["margen_bateria"] == 0.15
    assert "n_sitios" not in comparacion.ESCENARIOS["exigente"]
    p = comparacion.partida_variante(1, "hibrido", "exigente10")
    assert len(p.mundo.sitios) == 10


def test_bateria_de_referencia_cubre_la_ruta_voraz_con_margen():
    import math
    from integracion import MARGEN_ENERGIA
    for s in (1, 2):
        bat = comparacion._bateria_referencia(s, PAR)
        sonda = Partida(semilla=s, nivel=5, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False,
                        n_sitios=10, bateria=1e6)
        m = sonda.mision
        m.riesgo = np.zeros_like(m.riesgo); m.usar_rna = False; m.usar_difuso = False
        m._optimizar_ag = comparacion._orden_voraz(m); m.objetivos = []; m._planear()
        L = len(m.ruta) - 1
        assert bat == float(math.ceil(L * 1.15) + MARGEN_ENERGIA)
        assert L + MARGEN_ENERGIA <= bat


def test_partida_exigente10_planifica_todos_los_sitios():
    p = comparacion.partida_variante(2, "hibrido", "exigente10")
    assert all(c in p.mision.objetivos for c in p.mundo.sitios)


def test_orden_2opt_no_es_mas_largo_que_el_voraz():
    p = comparacion.partida_variante(1, "sin_ag_vecino", "exigente10")
    m = p.mision
    pend = {q: v for q, v in p.mundo.sitios.items()}
    voraz = comparacion._orden_voraz(m)(tuple(p.rover.posicion), pend)
    mejorado = comparacion._orden_2opt(m)(tuple(p.rover.posicion), pend)
    assert mejorado and voraz
    assert len(mejorado) <= len(voraz)
    assert mejorado[-1] == tuple(p.mundo.refugio) and all(c in mejorado for c in p.mundo.sitios)


def test_sin_ag_2opt_es_determinista_y_declarada():
    assert "sin_ag_2opt" in comparacion.VARIANTES_ABLACION
    f = comparacion.correr(1, "sin_ag_2opt", "exigente10")
    assert f["variante"] == "sin_ag_2opt" and f["pasos"] > 0
    assert comparacion.correr(1, "sin_ag_2opt", "exigente10") == f
