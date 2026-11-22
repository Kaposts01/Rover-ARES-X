"""ARX-92c: el orden de la partida lo decide un AG sobre la permutación de sitios (cruce OX, intercambio, elitismo),
con la viabilidad (batería y factor de la garantía) como restricción dura y la vía b de 92a como respaldo.

Por defecto corre pocas semillas para que la prueba sea corta; `ARX92_SEMILLAS=20` corre las 20 del criterio de HECHO."""
import itertools
import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from genetico import GeneticPlanner, camino_bfs  # noqa: E402
from integracion import camino_valido  # noqa: E402
from juego.partida import (AVISO_FALLBACK, COLUMNAS_BASE, FILAS_BASE, METODO_AG_ORDEN, NIVEL_MAX, UMBRAL_EMPATE,  # noqa: E402
                           Partida, _ag_con_todos_los_sitios)

SEMILLAS = range(1, int(os.environ.get("ARX92_SEMILLAS", "4")) + 1)


def _partida(semilla, nivel=1, garantia=False):
    return Partida(semilla=semilla, nivel=nivel, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=garantia,
                   plan_restringido=False)    # R23: estas pruebas son del envoltorio de orden (92c), no del plan con restricciones


def _referencia_exhaustiva(p):
    """Ruta que elegiría la vía b de 92a: la permutación de mayor fitness con desempate por la más corta."""
    m = p.mision
    pend = {s: v for s, v in p.mundo.sitios.items() if s not in m.visitados}
    origen, refugio = tuple(p.rover.posicion), tuple(p.mundo.refugio)
    mascara = m.riesgo < 0.5
    gp = GeneticPlanner(replace(m.mundo, inicio=origen, sitios=dict(pend)), m.riesgo,
                        bateria=max(float(m.rover.bateria), 1.0), semilla=m.semilla)
    validas = []
    for orden in itertools.permutations(list(pend)):
        ruta = [origen]
        for d in list(orden) + [refugio]:
            t = camino_bfs(ruta[-1], d, mascara)
            if t is None:
                ruta = None
                break
            ruta.extend(t[1:])
        if ruta is not None:
            validas.append((gp.evaluar_ruta(ruta).fitness, len(ruta), ruta))
    fmax = max(v[0] for v in validas)
    return fmax, min((v for v in validas if v[0] >= fmax - UMBRAL_EMPATE), key=lambda v: v[1])[2], pend


def _ag(p, **kw):
    envoltorio = _ag_con_todos_los_sitios(p.mision, lambda o, pe: [], **kw)
    pend = {s: v for s, v in p.mundo.sitios.items() if s not in p.mision.visitados}
    return envoltorio, envoltorio(tuple(p.rover.posicion), pend), pend


def test_la_partida_declara_el_ag_sobre_el_orden():
    p = _partida(3)
    assert p.mision._optimizar_ag.metodo == METODO_AG_ORDEN
    assert p.mision._optimizar_ag.fallbacks == []
    assert p.mision._optimizar_ag.ultimo.modo == "orden"


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_con_tres_sitios_el_ag_alcanza_el_optimo_de_la_exhaustiva(semilla):
    p = _partida(semilla)
    assert len(p.mundo.sitios) == 3
    fmax, ruta_ref, _ = _referencia_exhaustiva(p)
    envoltorio, ruta, _ = _ag(p)
    assert envoltorio.ultimo.viable
    assert envoltorio.ultimo.mejor_desglose.fitness >= fmax - UMBRAL_EMPATE
    assert ruta == ruta_ref                      # mismo orden que el óptimo con desempate de 92a


@pytest.mark.parametrize("semilla", SEMILLAS)
@pytest.mark.parametrize("nivel", [1, NIVEL_MAX])
def test_candidatos_son_ordenes_completos(semilla, nivel):
    p = _partida(semilla, nivel)
    envoltorio, ruta, pend = _ag(p)
    res = envoltorio.ultimo
    assert res.candidatos
    for cromosoma, _ in res.candidatos:
        assert sorted(cromosoma[0]) == sorted(pend)
    assert all(s in ruta for s in pend)


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_determinista_por_semilla(semilla):
    a, b = _partida(semilla), _partida(semilla)
    assert a.mision.ruta == b.mision.ruta
    assert a.mision._optimizar_ag.ultimo.mejor == b.mision._optimizar_ag.ultimo.mejor


@pytest.mark.parametrize("semilla", SEMILLAS)
@pytest.mark.parametrize("nivel", range(1, NIVEL_MAX + 1))
def test_la_ruta_jugada_es_viable(semilla, nivel):
    p = _partida(semilla, nivel, garantia=True)
    m = p.mision
    ruta = m.ruta
    assert ruta and tuple(ruta[0]) == tuple(m.mundo.inicio) and tuple(ruta[-1]) == tuple(m.mundo.refugio)
    assert camino_valido(ruta, m.riesgo)
    if p.estaciones and not all(s in ruta for s in m.mundo.sitios):
        # R23: con la dificultad nueva la garantía cuenta con las bases de recarga, pero el planificador de orden (92c) no
        # planifica paradas: si la ruta completa no cabe sin recargar, Mision._planear descarta los sitios y va al refugio
        # (el plan con recargas es planificacion.py). Aun así la ruta es válida y cabe en la batería.
        assert (len(ruta) - 1) * m.factor_ambiente <= m.rover.bateria
        return
    assert all(s in ruta for s in m.mundo.sitios)
    o = m._optimizar_ag
    assert o.fallbacks == [] or all(a == AVISO_FALLBACK for a in o.fallbacks)
    if not m.estaciones_activas:
        assert (len(ruta) - 1) * m.factor_ambiente <= m.rover.bateria


def test_sin_orden_viable_cae_a_la_via_b_y_lo_anota(monkeypatch):
    p = _partida(5)
    m = p.mision
    avisos = []
    envoltorio = _ag_con_todos_los_sitios(m, lambda o, pe: ["original"], anotar=avisos.append)
    # El AG no encuentra ningún orden viable (la restricción dura del AG se vuelve imposible); la vía b sí enumera
    real = GeneticPlanner.optimizar_orden

    def sin_viable(self, *a, **k):
        r = real(self, *a, **k)
        r.viable, r.mejor_ruta, r.candidatos = False, [], []
        return r
    monkeypatch.setattr(GeneticPlanner, "optimizar_orden", sin_viable)
    pend = {s: v for s, v in p.mundo.sitios.items()}
    ruta = envoltorio(tuple(p.rover.posicion), pend)
    fmax, ruta_ref, _ = _referencia_exhaustiva(p)
    assert envoltorio.fallbacks == [AVISO_FALLBACK]
    assert avisos and avisos[0].startswith(AVISO_FALLBACK)
    assert ruta == ruta_ref                      # juega la permutación viable de mejor fitness (92a)


def test_si_tampoco_hay_permutacion_viable_devuelve_la_ruta_del_ag_original():
    p = _partida(5)
    m = p.mision
    m.riesgo = np.ones_like(m.riesgo)            # nada transitable: ningún orden es viable
    envoltorio = _ag_con_todos_los_sitios(m, lambda o, pe: ["original"])
    pend = {s: v for s, v in p.mundo.sitios.items()}
    assert envoltorio(tuple(p.rover.posicion), pend) == ["original"]
    assert envoltorio.fallbacks == [AVISO_FALLBACK]


def test_los_pesos_cambian_la_eleccion_del_ag():
    p = _partida(7, nivel=NIVEL_MAX)
    _, ruta_corta, _ = _ag(p, pesos={"ciencia": 0, "distancia": 5, "energia": 0, "riesgo": 0, "tiempo": 0})
    mascara = p.mision.riesgo < 0.5
    origen, refugio = tuple(p.rover.posicion), tuple(p.mundo.refugio)
    largos = []
    for orden in itertools.permutations(list(p.mundo.sitios)):
        ruta = [origen]
        for d in list(orden) + [refugio]:
            t = camino_bfs(ruta[-1], d, mascara)
            ruta = None if t is None else ruta + t[1:]
            if ruta is None:
                break
        if ruta:
            largos.append(len(ruta))
    assert len(ruta_corta) == min(largos)         # con solo distancia el AG elige la permutación más corta
