"""Prueba causal (ARX-10, ev3-d32 A). Criterio 9 de docs/SPEC_MVP_3D.md.

Sin intervención, el gancho no cambia nada: las misiones son idénticas a las de antes.
Con intervención, se mide el primer paso donde cambia la decisión (acción o velocidad).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integracion import Mision, forzar_probabilidad  # noqa: E402
from intervencion import _primer_cambio, correr_semilla, opciones_variantes  # noqa: E402
from simulador import generar_mundo  # noqa: E402


def _mision(semilla=11, **opciones):
    return Mision(generar_mundo(semilla=semilla, n_obstaculos=20, n_barrancos=4, n_sitios=3),
                  semilla=semilla, **opciones)


def test_sin_intervencion_la_mision_es_identica_a_la_de_siempre():
    # Gancho apagado por defecto: pasar None explícito o nada da exactamente el mismo registro
    a = _mision()
    b = _mision(intervencion_rna=None, intervencion_difuso=None)
    ra = a.ejecutar(max_pasos=400)
    rb = b.ejecutar(max_pasos=400)
    assert ra == rb
    assert a.log.a_dataframe().equals(b.log.a_dataframe())


def test_forzar_probabilidad_produce_distribucion_valida():
    probs = {"libre": 0.8, "obstáculo": 0.15, "barranco": 0.05}
    for clase in probs:
        p = forzar_probabilidad(clase)(probs)
        assert abs(sum(p.values()) - 1.0) < 1e-9
        assert p[clase] == max(p.values())


def test_rna_forzada_a_barranco_cambia_la_decision():
    # Criterio 9: forzar la RNA a barranco cambia acción o velocidad en algún paso
    res = correr_semilla(11, "rna_barranco", {"intervencion_rna": forzar_probabilidad("barranco")})
    assert res["paso_primer_cambio"] is not None
    assert res["paso_primer_cambio"] >= 1


def test_rna_forzada_a_libre_mide_el_efecto():
    res = correr_semilla(11, "rna_libre", {"intervencion_rna": forzar_probabilidad("libre")})
    assert isinstance(res["exito_var"], bool)
    assert res["paso_primer_cambio"] is None or res["paso_primer_cambio"] >= 1


def test_difuso_forzado_a_velocidad_minima_cambia_la_velocidad_del_primer_paso():
    m = _mision(intervencion_difuso=0.0)
    m.ejecutar(max_pasos=5)
    assert float(m.log.a_dataframe().iloc[0]["velocidad"]) == 0.0


def test_difuso_forzado_a_velocidad_maxima_cambia_la_velocidad_del_primer_paso():
    m = _mision(intervencion_difuso=1.0)
    m.ejecutar(max_pasos=5)
    assert float(m.log.a_dataframe().iloc[0]["velocidad"]) == 1.0


def test_difuso_forzado_tiene_efecto_medible_frente_a_la_base():
    base = _mision()
    base.ejecutar(max_pasos=5)
    forzada = _mision(intervencion_difuso=0.0)
    forzada.ejecutar(max_pasos=5)
    cambio = _primer_cambio(base.log.a_dataframe(), forzada.log.a_dataframe())
    assert cambio == 1


def test_variantes_definidas_son_cuatro():
    assert set(opciones_variantes()) == {"rna_barranco", "rna_libre", "difuso_min", "difuso_max"}


def test_primer_cambio_none_cuando_no_hay_diferencias():
    base = _mision()
    base.ejecutar(max_pasos=20)
    otra = _mision()
    otra.ejecutar(max_pasos=20)
    assert _primer_cambio(base.log.a_dataframe(), otra.log.a_dataframe()) is None
