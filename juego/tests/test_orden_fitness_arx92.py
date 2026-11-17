"""ARX-92a: el envoltorio de la partida elige entre las permutaciones viables por el fitness con pesos."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from genetico import camino_bfs  # noqa: E402
from juego.partida import COLUMNAS_BASE, FILAS_BASE, METODO_ORDEN, Partida, _ag_con_todos_los_sitios  # noqa: E402

SEMILLAS = range(1, 21)


def _partida(semilla, nivel=1):
    return Partida(semilla=semilla, nivel=nivel, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)


def _ruta(p, pesos=None):
    m = p.mision
    pend = {s: v for s, v in p.mundo.sitios.items() if s not in m.visitados}
    envoltorio = _ag_con_todos_los_sitios(m, lambda o, pe: [], pesos=pesos)
    return envoltorio(tuple(p.rover.posicion), pend), list(pend)


def _largos_por_orden(p, pend):
    """Largo y riesgo medio de la ruta de cada permutación (por BFS sobre el mapa estimado)."""
    m = p.mision
    mascara = m.riesgo < 0.5
    origen, refugio = tuple(p.rover.posicion), tuple(p.mundo.refugio)
    res = []
    for orden in itertools.permutations(pend):
        ruta = [origen]
        for d in list(orden) + [refugio]:
            t = camino_bfs(ruta[-1], d, mascara)
            if t is None:
                ruta = None
                break
            ruta.extend(t[1:])
        if ruta is not None:
            res.append((len(ruta), float(np.mean([m.riesgo[c] for c in ruta])), ruta))
    return res


def test_declara_el_metodo():
    p = _partida(3)
    assert p.mision._optimizar_ag.metodo == METODO_ORDEN == "exhaustiva puntuada por el fitness"


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_pesos_solo_distancia_coincide_con_la_mas_corta(semilla):
    p = _partida(semilla)
    ruta, pend = _ruta(p, {"ciencia": 0, "distancia": 5, "energia": 0, "riesgo": 0, "tiempo": 0})
    viables = _largos_por_orden(p, pend)
    if not viables:
        pytest.skip("sin permutación viable")
    assert len(ruta) == min(v[0] for v in viables)


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_pesos_de_riesgo_no_empeoran_el_riesgo_de_la_mas_corta(semilla):
    p = _partida(semilla, nivel=5)
    ruta, pend = _ruta(p, {"ciencia": 0, "distancia": 0, "energia": 0, "riesgo": 5, "tiempo": 0})
    viables = _largos_por_orden(p, pend)
    if not viables:
        pytest.skip("sin permutación viable")
    mas_corta = min(viables, key=lambda v: v[0])
    assert float(np.mean([p.mision.riesgo[c] for c in ruta])) <= mas_corta[1] + 1e-9


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_la_ruta_elegida_es_completa_y_contigua(semilla):
    p = _partida(semilla)
    ruta, pend = _ruta(p)
    if not ruta:
        pytest.skip("sin permutación viable")
    assert ruta[0] == tuple(p.rover.posicion) and ruta[-1] == tuple(p.mundo.refugio)
    assert all(s in ruta for s in pend)
    assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1 for a, b in zip(ruta, ruta[1:]))


def test_determinista():
    p = _partida(5)
    assert _ruta(p)[0] == _ruta(p)[0]


def test_umbral_unico_fijado():
    import juego.partida as pm
    assert pm.UMBRAL_EMPATE == 0.0223


def test_caso_sin_umbral_gana_la_mas_corta(monkeypatch):
    """Mide el caso sin umbral (umbral enorme): la más corta siempre. No es el umbral de 0,0223 (ev3-d79 A)."""
    import juego.partida as pm
    monkeypatch.setattr(pm, "UMBRAL_EMPATE", 1e9)
    for semilla in (1, 9, 16):
        p = _partida(semilla, nivel=5)
        ruta, pend = _ruta(p, {"ciencia": 0, "distancia": 0, "energia": 0, "riesgo": 5, "tiempo": 0})
        viables = _largos_por_orden(p, pend)
        if viables:
            assert len(ruta) == min(v[0] for v in viables)


def test_pesos_no_triviales_cambian_el_orden_en_alguna_semilla(monkeypatch):
    """Con pesos de riesgo (×5) y sin umbral, el fitness elige una ruta distinta de la más corta en algún mapa."""
    import juego.partida as pm
    monkeypatch.setattr(pm, "UMBRAL_EMPATE", 0.0)
    cambios = 0
    for semilla in SEMILLAS:
        p = _partida(semilla, nivel=5)
        ruta, pend = _ruta(p, {"ciencia": 0, "distancia": 0, "energia": 0, "riesgo": 5, "tiempo": 0})
        viables = _largos_por_orden(p, pend)
        if viables and len(ruta) != min(v[0] for v in viables):
            cambios += 1
    assert cambios >= 1
