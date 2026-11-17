"""RNA-aporte · Segunda pasada: umbral de desnivel (−1, −2, −3 m) y test más grande (20 mapas, semillas 100–119).
Uso: python -I medir_rna_aporte_2.py <raiz_del_repo>. Solo lectura del repo."""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = sys.argv[1]
sys.path.insert(0, RAIZ)

import numpy as np  # noqa: E402

import rna  # noqa: E402
import simulador  # noqa: E402
from simulador import BARRANCO  # noqa: E402

t0 = time.time()
GENERAR_ORIGINAL = simulador.generar_mundo


def mundo_con_desnivel(desnivel):
    def generar(semilla, **kw):
        m = GENERAR_ORIGINAL(semilla, **kw)
        m.elevacion = m.elevacion.copy()
        m.elevacion[m.tipo == BARRANCO] += desnivel
        return m
    return generar


tr, _, _ = rna.particion_por_mapas(total_mapas=30)
te_grande = np.arange(100, 120)
SIN_BORDE = [0, 2, 3]
for desnivel in (-1.0, -2.0, -3.0):
    simulador.generar_mundo = mundo_con_desnivel(desnivel)
    rna.generar_mundo = simulador.generar_mundo
    Xtr, ytr = rna.generar_dataset(tr, muestras_por_mapa=300)
    Xte, yte = rna.generar_dataset(te_grande, muestras_por_mapa=300)
    for nombre, cols in (("4 rasgos (con borde)", [0, 1, 2, 3]), ("sin borde_barranco", SIN_BORDE)):
        red = rna.NeuralPerception(semilla=42).entrenar(Xtr[:, cols], ytr)
        r = red.evaluar(Xte[:, cols], yte)
        nb = int((yte == BARRANCO).sum())
        tp = int(((r.predicciones == BARRANCO) & (yte == BARRANCO)).sum())
        fp = int(((r.predicciones == BARRANCO) & (yte != BARRANCO)).sum())
        print(f"desnivel={desnivel:+.0f} m · {nombre:22s} recall_barranco={r.recall_barranco:.3f} ({tp}/{nb}) "
              f"falsos_pos={fp} macroF1={r.macro_f1:.3f} ECE={r.error_calibracion:.3f} n_test={len(yte)}")
print(f"[total] {time.time() - t0:.0f} s")
