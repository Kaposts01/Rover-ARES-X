"""Mediciones de tiempo (ARX-44 y ARX-46). Solo mide: no modifica el motor ni sus resultados.

ARX-44: tiempo por paso del motor, por modo (automático = Partida.avanzar_ia; rna/difuso/ag = avanzar_modo, veto
        encendido), partida habitual 20x30 sin garantía, como en scripts/tabla_modos.py.
ARX-46: (a) entrenamiento de la RNA, por separado: generar_dataset, ajuste de la red y total
        (equivale a integracion.rna_entrenada, que se mide sin caché); (b) decisión: una llamada de
        Partida.sugerencia() por paso y una predicción suelta de la RNA.

Uso (desde ares_x/):  python scripts/medir_tiempos.py [--semillas 1 2 3] [--max-pasos 400] [--json salida.json]
Tiempos en milisegundos de reloj (time.perf_counter) y de CPU del proceso (time.process_time) para el total.
"""
import argparse
import json
import os
import statistics
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from integracion import ESTADOS_TERMINALES  # noqa: E402

MODOS = ("automatico", "rna", "difuso", "ag")


def resumen(muestras_s):
    ms = [x * 1000.0 for x in muestras_s]
    if not ms:
        return {"n": 0, "media_ms": None, "mediana_ms": None, "maximo_ms": None}
    return {"n": len(ms), "media_ms": statistics.fmean(ms), "mediana_ms": statistics.median(ms), "maximo_ms": max(ms)}


def medir_pasos(semillas, modos=MODOS, max_pasos=400):
    """ARX-44: tiempo de cada paso del motor, por modo."""
    from juego.partida import COLUMNAS_BASE, FILAS_BASE, Partida
    salida = {}
    for modo in modos:
        t = []
        for s in semillas:
            p = Partida(semilla=s, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
            pasos = 0
            while p.estado not in ESTADOS_TERMINALES and pasos < max_pasos:
                t0 = time.perf_counter()
                if modo == "automatico":
                    p.avanzar_ia()
                else:
                    p.avanzar_modo(modo, True)
                t.append(time.perf_counter() - t0)
                pasos += 1
        salida[modo] = resumen(t)
    return salida


def medir_entrenamiento():
    """ARX-46 (offline): mismos parámetros que integracion.rna_entrenada, pero sin caché."""
    from rna import NeuralPerception, generar_dataset, particion_por_mapas
    c0 = time.process_time()
    t0 = time.perf_counter()
    tr, _, _ = particion_por_mapas(total_mapas=30)
    X, y = generar_dataset(tr, muestras_por_mapa=300)
    t1 = time.perf_counter()
    red = NeuralPerception(semilla=42).entrenar(X, y)
    t2 = time.perf_counter()
    return {"muestras": int(len(y)), "generar_dataset_s": t1 - t0, "ajuste_red_s": t2 - t1,
            "total_s": t2 - t0, "cpu_total_s": time.process_time() - c0}, red


def medir_decision(semillas, red, max_pasos=400):
    """ARX-46 (online): una decisión por paso (Partida.sugerencia) y una predicción suelta de la RNA."""
    import numpy as np
    from juego.partida import COLUMNAS_BASE, FILAS_BASE, Partida
    t = []
    for s in semillas:
        p = Partida(semilla=s, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
        pasos = 0
        while p.estado not in ESTADOS_TERMINALES and pasos < max_pasos:
            t0 = time.perf_counter()
            p.sugerencia()
            t.append(time.perf_counter() - t0)
            p.avanzar_ia()
            pasos += 1
    x = np.zeros(red.escalador.n_features_in_)
    tp = []
    for _ in range(500):
        t0 = time.perf_counter()
        red.predecir_proba(x)
        tp.append(time.perf_counter() - t0)
    return {"decision_por_paso": resumen(t), "prediccion_rna_suelta": resumen(tp)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--semillas", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--max-pasos", type=int, default=400)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    c0 = time.process_time()
    res = {"semillas": a.semillas}
    entren, red = medir_entrenamiento()
    res["entrenamiento"] = entren
    res["decision"] = medir_decision(a.semillas, red, a.max_pasos)
    res["paso_por_modo"] = medir_pasos(a.semillas, max_pasos=a.max_pasos)
    res["cpu_total_s"] = time.process_time() - c0
    texto = json.dumps(res, indent=2, ensure_ascii=False)
    print(texto)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    return res


if __name__ == "__main__":
    main()
