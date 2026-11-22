"""R23: AG que evoluciona los parámetros del difuso y de la conducción con un fitness por planeta (fuera de línea, reproducible).

Para cada planeta: un AG de codificación real (torneo, cruce BLX-α, mutación gaussiana, elitismo) busca el vector de
`juego/difuso_planetas.GENES` (puntos de las funciones de pertenencia, pesos de reglas y umbrales de conducción) que maximiza el
fitness medido SIMULANDO PARTIDAS JUGABLES en ese planeta (juego/planetas.py: gravedad, viento con ráfagas, hielo) con las semillas
de entrenamiento. Después se mide el resultado en semillas de VALIDACIÓN no vistas, contra el difuso por defecto, para detectar
sobreajuste. Guarda el resultado en `juego/difuso_planetas.json` (versionado), que la partida carga.

fitness de una partida = éxito (1) + 0,5 · ciencia recogida (fracción del valor, por la calidad de la ventana) + 0,2 · batería final
(fracción de la capacidad, solo si gana). El fitness del vector es la media sobre las semillas de entrenamiento.

Uso (desde la raíz; medición pesada, una a la vez; semilla fija):
    python scripts/evolucionar_difuso.py --planeta Marte
    python scripts/evolucionar_difuso.py --planeta Neptuno --poblacion 12 --generaciones 7
Con --salida distinta no toca el archivo versionado.
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

from integracion import ESTADOS_TERMINALES  # noqa: E402
from juego import difuso_planetas as dp  # noqa: E402
from juego.partida import Partida  # noqa: E402

MAX_PASOS = 400
SEMILLAS_ENTRENAMIENTO = list(range(301, 309))
SEMILLAS_VALIDACION = list(range(401, 421))


def jugar(vector, semilla: int, planeta: str, nivel: int, n_sitios: int) -> dict:
    """Una partida jugable con el vector dado (None = difuso por defecto, sin evolucionar)."""
    ajustes = dp.a_parametros(vector) if vector is not None else None
    p = Partida(semilla=semilla, nivel=nivel, garantia=True, planeta=planeta, n_sitios=n_sitios,
                difuso_evolucionado=False, ajustes_difuso=ajustes)
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    ciencia = p.ciencia()["fraccion"]
    exito = p.estado == "EXITO"
    bateria = float(p.rover.bateria) / max(float(p.capacidad_bateria), 1e-9)
    return {"exito": exito, "ciencia": ciencia, "bateria": bateria, "pasos": pasos,
            "fitness": (1.0 if exito else 0.0) + 0.5 * ciencia + (0.2 * bateria if exito else 0.0)}


def evaluar(vector, semillas, planeta, nivel, n_sitios) -> dict:
    filas = [jugar(vector, s, planeta, nivel, n_sitios) for s in semillas]
    return {"fitness": float(np.mean([f["fitness"] for f in filas])),
            "exito": float(np.mean([f["exito"] for f in filas])),
            "ciencia": float(np.mean([f["ciencia"] for f in filas])),
            "pasos": float(np.mean([f["pasos"] for f in filas])), "n": len(filas)}


def evolucionar(planeta, nivel, n_sitios, poblacion, generaciones, semilla, semillas_ent, log):
    rng = np.random.default_rng(semilla)
    rango = dp.MAXIMOS - dp.MINIMOS
    cache = {}

    def fit(v):
        v = dp.recortar(v)
        clave = tuple(np.round(v, 4))
        if clave not in cache:
            cache[clave] = evaluar(v, semillas_ent, planeta, nivel, n_sitios)
        return cache[clave]["fitness"]

    pob = [dp.DEFECTO.copy()]
    pob += [dp.recortar(dp.DEFECTO + rng.normal(0, 0.12, len(rango)) * rango) for _ in range(poblacion // 2)]
    while len(pob) < poblacion:
        pob.append(dp.MINIMOS + rng.random(len(rango)) * rango)
    historial = []
    for gen in range(generaciones):
        f = np.array([fit(v) for v in pob])
        orden = np.argsort(-f)
        historial.append({"generacion": gen, "mejor": float(f.max()), "media": float(f.mean()), "peor": float(f.min())})
        log(f"  gen {gen}: mejor {f.max():.4f}  media {f.mean():.4f}  peor {f.min():.4f}")
        if gen == generaciones - 1:
            break
        nueva = [pob[i].copy() for i in orden[:2]]
        sigma = 0.15 * (1.0 - 0.6 * gen / max(generaciones - 1, 1))
        while len(nueva) < poblacion:
            a, b = (pob[max(rng.choice(len(pob), 3, replace=False), key=lambda i: f[i])] for _ in range(2))
            lo, hi = np.minimum(a, b), np.maximum(a, b)
            ancho = hi - lo
            hijo = rng.uniform(lo - 0.3 * ancho, hi + 0.3 * ancho)             # BLX-0,3
            muta = rng.random(len(rango)) < 0.15
            hijo = np.where(muta, hijo + rng.normal(0, sigma, len(rango)) * rango, hijo)
            nueva.append(dp.recortar(hijo))
        pob = nueva
    f = np.array([fit(v) for v in pob])
    mejor = pob[int(np.argmax(f))]
    return dp.recortar(mejor), historial, cache


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--planeta", required=True)
    ap.add_argument("--nivel", type=int, default=4)
    ap.add_argument("--sitios", type=int, default=11)
    ap.add_argument("--poblacion", type=int, default=12)
    ap.add_argument("--generaciones", type=int, default=7)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--n-entrenamiento", type=int, default=8, help="semillas de entrenamiento (301, 302, ...)")
    ap.add_argument("--salida", default=str(dp.RUTA_JSON))
    a = ap.parse_args()
    t0 = time.perf_counter()
    log = lambda s: print(s, flush=True)
    log(f"Evolucionando el difuso de {a.planeta} (nivel {a.nivel}, {a.sitios} sitios, población {a.poblacion}, "
        f"{a.generaciones} generaciones, semilla {a.semilla})")
    entrenamiento = list(range(301, 301 + a.n_entrenamiento))
    mejor, historial, cache = evolucionar(a.planeta, a.nivel, a.sitios, a.poblacion, a.generaciones, a.semilla,
                                          entrenamiento, log)
    log("Midiendo entrenamiento y validación (defecto frente a evolucionado)...")
    res = {}
    for nombre, semillas in (("entrenamiento", entrenamiento), ("validacion", SEMILLAS_VALIDACION)):
        res[nombre] = {"semillas": [semillas[0], semillas[-1]],
                       "defecto": evaluar(None, semillas, a.planeta, a.nivel, a.sitios),
                       "evolucionado": evaluar(mejor, semillas, a.planeta, a.nivel, a.sitios)}
        log(f"  {nombre}: defecto {res[nombre]['defecto']}  evolucionado {res[nombre]['evolucionado']}")
    todo = dp.cargar_todo(a.salida) if Path(a.salida).exists() else {"planetas": {}}
    todo = {"version": 1, "planetas": dict(todo.get("planetas") or {})}
    params = dp.a_parametros(mejor)
    todo["planetas"][a.planeta] = {**params, "vector": {n: round(float(v), 4) for n, v in zip(dp.NOMBRES, mejor)},
                                   "entrenamiento": {"nivel": a.nivel, "sitios": a.sitios, "semilla": a.semilla,
                                                     "poblacion": a.poblacion, "generaciones": a.generaciones, "semillas_entrenamiento": len(entrenamiento),
                                                     "historial": historial, "evaluaciones": len(cache)},
                                   "resultados": res, "generado": date.today().isoformat()}
    dp.guardar(todo, a.salida)
    log(f"Guardado en {a.salida} ({time.perf_counter() - t0:.0f} s)")


if __name__ == "__main__":
    main()
