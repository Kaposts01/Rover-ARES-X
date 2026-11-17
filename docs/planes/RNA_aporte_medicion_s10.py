"""ARX-93 (B1 de QA): reproduce §10 de docs/planes/RNA_aporte.md (firma de barranco activa, semilla 42).

Uso (desde ares_x/):  python docs/planes/RNA_aporte_medicion_s10.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, simulador, rna
from simulador import BARRANCO
simulador.FIRMA_BARRANCO_ACTIVA = True
tr, va, te = rna.particion_por_mapas(total_mapas=60)
print("partición:", len(tr), len(va), len(te), "| firma:", simulador.FIRMA_BARRANCO_ACTIVA)
Xtr, ytr = rna.generar_dataset(tr, muestras_por_mapa=400, perfil="terreno")
Xte, yte = rna.generar_dataset(np.arange(100, 120), muestras_por_mapa=400, perfil="terreno")
red = rna.NeuralPerception(semilla=42, columnas=[0, 1, 2]).entrenar(Xtr, ytr) if "columnas" in rna.NeuralPerception.__init__.__code__.co_varnames else rna.NeuralPerception(semilla=42).entrenar(Xtr, ytr)
r = red.evaluar(Xte, yte)
clases = sorted(set(map(int, yte)) | set(map(int, r.predicciones)))
M = np.zeros((len(clases), len(clases)), int)
for a, b in zip(yte, r.predicciones): M[clases.index(int(a)), clases.index(int(b))] += 1
print("clases (real filas / predicho columnas):", clases, "| BARRANCO =", BARRANCO)
print(M)
nb = int((yte == BARRANCO).sum()); tp = int(((r.predicciones == BARRANCO) & (yte == BARRANCO)).sum())
print(f"n_test={len(yte)} macroF1={r.macro_f1:.3f} recall_barranco={r.recall_barranco:.3f} ({tp}/{nb}) | §10: 7399 muestras, macro-F1 0,933, recall 0,863 (63/73), matriz [[6890,0,2],[4,416,14],[2,8,63]]")
