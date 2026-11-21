"""Uso (desde ares_x/):  python scripts/medicion_94d.py
Medición 94d (umbrales de docs/planes/ARX-94_umbrales.md): una sola corrida, sin ajustes.
Entrena v2 con la partición de 60 mapas (42 de entrenamiento, 400 muestras por mapa) y evalúa en 20 mapas no vistos (100-119).
FP = celdas libres predichas como barranco / celdas libres."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from rna import NOMBRES_RASGOS_V2, NeuralPerception, generar_dataset, particion_por_mapas
from simulador import BARRANCO, LIBRE

t = time.time()
tr, _, _ = particion_por_mapas(total_mapas=60)
te = np.arange(100, 120)
Xtr, ytr = generar_dataset(tr, muestras_por_mapa=400, perfil="v2")
Xte, yte = generar_dataset(te, muestras_por_mapa=400, perfil="v2")
res = NeuralPerception(42, nombres=NOMBRES_RASGOS_V2, perfil="v2").entrenar(Xtr, ytr).evaluar(Xte, yte)
libres = yte == LIBRE
fp = float(((res.predicciones == BARRANCO) & libres).sum() / libres.sum())
print("muestras prueba", len(yte), "barrancos", int((yte == BARRANCO).sum()))
print("matriz", res.matriz_confusion.tolist())
print("macro-F1 %.3f  recall barrancos %.3f (umbral >= 0,6)  FP %.3f %% (<= 0,2 %%)  ECE %.3f (<= 0,03)  base %.3f"
      % (res.macro_f1, res.recall_barranco, 100 * fp, res.error_calibracion, res.precision_base))
print("segundos", round(time.time() - t, 1))
