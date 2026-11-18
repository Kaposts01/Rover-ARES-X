"""ARX-92 B (§16): penalización graduada de la inviabilidad, cota del fitness viable y siembra del vecino más cercano."""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from genetico import GeneticPlanner, cota_viable  # noqa: E402
from juego.partida import COLUMNAS_BASE, FILAS_BASE, Partida  # noqa: E402


def _planificador(semilla=3, pesos=None):
    p = Partida(semilla=semilla, nivel=1, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
    m = p.mision
    pend = {q: v for q, v in p.mundo.sitios.items() if q not in m.visitados}
    origen = tuple(p.rover.posicion)
    gp = GeneticPlanner(replace(p.mundo, inicio=origen, sitios=pend), m.riesgo, bateria=100.0,
                        poblacion=30, generaciones=30, semilla=7, pesos=pesos)
    return gp, origen, list(pend)


def test_cota_con_todos_los_pesos_en_5():
    # ARX-92 B (QA): con TODOS los pesos en 5, un cromosoma inviable queda por debajo de la cota de cualquier viable
    pesos = {k: 5.0 for k in ("ciencia", "distancia", "energia", "riesgo", "tiempo")}
    gp, _, _ = _planificador(pesos=pesos)
    cota = cota_viable(gp.pesos, gp.pasos_maximos, gp.bateria)
    viable = gp.optimizar_orden()
    assert viable.viable and viable.mejor_desglose.fitness >= cota
    inviable = gp.optimizar_orden(construir=lambda seq: ("inviable", seq, 5.0))
    assert not inviable.viable and inviable.mejor_desglose.fitness < cota


def test_con_mas_exceso_menos_fitness():
    gp, _, _ = _planificador()
    poco = gp.optimizar_orden(construir=lambda seq: ("inviable", seq, 1.0))
    mucho = gp.optimizar_orden(construir=lambda seq: ("inviable", seq, 50.0))
    assert mucho.mejor_desglose.fitness < poco.mejor_desglose.fitness


@pytest.mark.parametrize("peso", [0.0, 1.0, 5.0])
def test_una_ruta_viable_siempre_gana_a_una_inviable(peso):
    pesos = {"ciencia": 1.0, "distancia": peso, "energia": peso, "riesgo": peso, "tiempo": peso}
    gp, origen, sitios = _planificador(pesos=pesos)
    primero = sitios[0]

    def construir(seq):
        ruta = gp._unir([origen] + list(seq))
        if ruta is None:
            return None
        return ruta if seq[0] == primero else ("inviable", ruta, 50.0)

    res = gp.optimizar_orden(construir, umbral_empate=0.0)
    assert res.viable
    assert tuple(res.mejor[0]) == tuple(primero)


def test_sin_rutas_viables_el_resultado_no_es_viable():
    gp, origen, sitios = _planificador()

    def construir(seq):
        ruta = gp._unir([origen] + list(seq))
        return None if ruta is None else ("inviable", ruta, 5.0)

    assert gp.optimizar_orden(construir, umbral_empate=0.0).viable is False


def test_la_siembra_del_vecino_aparece_en_la_generacion_0():
    gp, origen, sitios = _planificador()

    def construir(seq):
        return gp._unir([origen] + list(seq))

    res = gp.optimizar_orden(construir, umbral_empate=0.0)
    # vecino más cercano por longitud de camino, desde el inicio, sin 2-opt
    cur, pend, orden = origen, list(sitios), []
    while pend:
        nxt = min(pend, key=lambda q: (gp._largo(cur, q) if gp._largo(cur, q) is not None else np.inf, sitios.index(q)))
        orden.append(nxt)
        pend.remove(nxt)
        cur = nxt
    sembrado = res.historial[0]["poblacion"][-1]["cromosoma"]
    assert [tuple(x) for x in sembrado] == orden


def test_es_determinista():
    gp, origen, sitios = _planificador()

    def construir(seq):
        return gp._unir([origen] + list(seq))

    a = gp.optimizar_orden(construir, umbral_empate=0.0)
    gp2, _, _ = _planificador()
    b = gp2.optimizar_orden(lambda seq: gp2._unir([origen] + list(seq)), umbral_empate=0.0)
    assert a.mejor == b.mejor and a.mejor_ruta == b.mejor_ruta
