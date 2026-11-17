"""ARX-92c: medición de 20 semillas. Criterios 1 y 4 del plan y comparación contra las líneas base.

Uso (desde ares_x/):  python scripts/medicion_92c.py SALIDA.json [semillas=20]
Tarda: criterios (1 y 4) unos minutos; comparación en los tres escenarios, más (la del exigente10 es la lenta).
Escribe un JSON con: criterio1 (semillas donde el AG iguala el óptimo de la exhaustiva con 3 sitios),
criterio4 (rutas viables por nivel, garantía activa) y comparacion (las variantes por escenario, sin ajustes).
"""
import itertools
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import numpy as np  # noqa: E402
from dataclasses import replace  # noqa: E402

from genetico import GeneticPlanner, camino_bfs  # noqa: E402
from juego import comparacion  # noqa: E402
from juego.partida import Partida, FILAS_BASE, COLUMNAS_BASE  # noqa: E402


def criterio1(semilla):
    """Con 3 sitios: el orden que elige el AG iguala el óptimo de la exhaustiva con la misma regla de desempate de 92a."""
    p = Partida(semilla=semilla, nivel=1, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
    m = p.mision
    pend = {q: v for q, v in p.mundo.sitios.items() if q not in m.visitados}
    origen, refugio = tuple(p.rover.posicion), tuple(p.mundo.refugio)
    capacidad = max(float(getattr(m, "bateria_max", None) or m.rover.bateria), 1.0)
    gp = GeneticPlanner(replace(p.mundo, inicio=origen, sitios=pend), m.riesgo, bateria=capacidad,
                        k_puntos=m.k, poblacion=30, generaciones=30, semilla=m.semilla)
    mascara = m.riesgo < 0.5
    def ruta_de(orden):
        seq = [origen] + list(orden) + [refugio]
        r = [origen]
        for a, b in zip(seq, seq[1:]):
            t = camino_bfs(a, b, mascara)
            if t is None:
                return None
            r.extend(t[1:])
        return r
    # óptimo con la misma regla de 92a: entre viables a UMBRAL_EMPATE o menos del mejor fitness, gana la más corta
    from juego.partida import UMBRAL_EMPATE
    viables = []
    for orden in itertools.permutations(list(pend)):
        r = ruta_de(orden)
        if r is not None:
            viables.append((gp.evaluar_ruta(r, capacidad).fitness, len(r), r))
    elegida = m.ruta
    if not viables or not elegida:
        return {"semilla": semilla, "cumple": None}
    fmax = max(v[0] for v in viables)
    optimo = min((v for v in viables if v[0] >= fmax - UMBRAL_EMPATE), key=lambda v: v[1])
    f_elegida = gp.evaluar_ruta(elegida, capacidad).fitness
    cumple = len(elegida) == optimo[1] and abs(f_elegida - optimo[0]) <= 1e-9
    return {"semilla": semilla, "cumple": bool(cumple), "fitness_elegida": f_elegida,
            "fitness_optimo_regla": optimo[0], "largo_elegida": len(elegida), "largo_optimo_regla": optimo[1]}


def criterio4(semilla, nivel):
    """Garantía activa: la ruta jugada termina en el refugio, es contigua, visita los sitios y cabe en la batería."""
    p = Partida(semilla=semilla, nivel=nivel, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=True)
    m = p.mision
    r = m.ruta
    ok = bool(r) and r[-1] == tuple(p.mundo.refugio) and all(
        max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1 for a, b in zip(r, r[1:]))
    ok = ok and all(c in r for c in p.mundo.sitios)
    ok = ok and (len(r) - 1) <= p.rover.bateria
    fallback = any("AG-FALLBACK-GARANTIA" in a for a in p.avisos)
    return {"semilla": semilla, "nivel": nivel, "viable": bool(ok), "fallback": fallback}


def main():
    salida = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    semillas = range(1, n + 1)
    t0 = time.perf_counter()
    res = {"inicio": time.strftime("%H:%M:%S"), "criterio1": [], "criterio4": [], "comparacion": {}}
    for s in semillas:
        res["criterio1"].append(criterio1(s))
        print("criterio1", s, res["criterio1"][-1].get("cumple"), flush=True)
    for nivel in range(1, 6):
        for s in semillas:
            res["criterio4"].append(criterio4(s, nivel))
        print("criterio4 nivel", nivel, flush=True)
    for esc in ("congelado", "exigente", "exigente10"):
        d = comparacion.comparar(semillas, esc)
        res["comparacion"][esc] = {"variantes": d["variantes"], "filas": d["filas"]}
        print("comparacion", esc, "lista", round(time.perf_counter() - t0), "s", flush=True)
    res["fin"] = time.strftime("%H:%M:%S")
    res["criterio1_resumen"] = sum(1 for x in res["criterio1"] if x.get("cumple")) / max(1, len(res["criterio1"]))
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print("escrito", salida, "fin", res["fin"], flush=True)


if __name__ == "__main__":
    main()
