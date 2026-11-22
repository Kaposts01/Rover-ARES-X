"""PLAN-SENSORES · Medición corta fuera de línea del rediseño de sensores (sin tocar el repo).

Mundo propuesto: cada barranco tiene profundidad propia U(1, 4) m. Sensores propuestos, todos físicos:
  proximidad_frontal_m  = distancia al primer OBSTÁCULO en línea (un haz no ve un hoyo), ruido como hoy;
  desnivel_frontal_m    = elevación(celda siguiente) − elevación(actual), ruido σ (telémetro inclinado);
  vibracion_actual      = IMU en la celda que se pisa (hoy todas las celdas libres son iguales: sin información).
Veto duro declarado: desnivel_frontal < −UMBRAL_BORDE. La RNA cubre la banda ambigua con probabilidad calibrada.
Se mide: (1) qué fracción de barrancos queda por debajo del veto duro (banda exclusiva de la RNA);
(2) recall/precisión de la RNA con los rasgos nuevos frente al veto por umbral solo; (3) por σ del telémetro.
Uso: python -I medir_sensores_rediseno.py <raiz_del_repo>
"""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402

import rna  # noqa: E402
from simulador import BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, generar_mundo  # noqa: E402

t0 = time.time()
PROF_MIN, PROF_MAX = 1.0, 4.0
UMBRAL_BORDE = -2.0


def mundo_v2(semilla):
    m = generar_mundo(semilla=int(semilla))
    rng = np.random.default_rng([int(semilla), 93])
    m.elevacion = m.elevacion.copy()
    for (f, c) in np.argwhere(m.tipo == BARRANCO):
        m.elevacion[f, c] -= rng.uniform(PROF_MIN, PROF_MAX)
    return m


def proximidad_obstaculo(m, pos, rumbo):
    df, dc = MOVIMIENTOS[rumbo]
    for paso in range(1, 21):
        p = (pos[0] + df * paso, pos[1] + dc * paso)
        if not m.dentro(p):
            break
        if m.tipo[p] == OBSTACULO:
            return paso
    return 20


def dataset(semillas, muestras, sigma_desnivel, ruido_prox=0.1):
    X, y = [], []
    for s in semillas:
        rng = np.random.default_rng(10_000 + int(s))
        m = mundo_v2(s)
        filas, columnas = m.forma
        for _ in range(muestras):
            pos = (int(rng.integers(1, filas - 1)), int(rng.integers(1, columnas - 1)))
            if m.tipo[pos] != LIBRE:
                continue
            rumbo = rng.choice(list(MOVIMIENTOS))
            df, dc = MOVIMIENTOS[rumbo]
            sig = (pos[0] + df, pos[1] + dc)
            prox = proximidad_obstaculo(m, pos, rumbo) + rng.normal(0, ruido_prox)
            desn = m.elevacion[sig] - m.elevacion[pos] + rng.normal(0, sigma_desnivel)
            vib = 0.2 + rng.normal(0, 0.3)          # celda actual: libre siempre → sin información
            X.append([prox, desn, vib])
            y.append(int(m.tipo[sig]))
    return np.array(X), np.array(y)


tr, _, _ = rna.particion_por_mapas(total_mapas=60)
te = np.arange(100, 120)
print(f"Mundo v2: barrancos con profundidad U({PROF_MIN:.0f}, {PROF_MAX:.0f}) m; veto duro desnivel < {UMBRAL_BORDE} m")
for sigma in (0.05, 0.5, 1.0):
    Xtr, ytr = dataset(tr, 400, sigma)
    Xte, yte = dataset(te, 400, sigma)
    red = rna.NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    r = red.evaluar(Xte, yte)
    pred = r.predicciones
    es_b = yte == BARRANCO
    veto = Xte[:, 1] < UMBRAL_BORDE
    tp_rna = int(((pred == BARRANCO) & es_b).sum())
    fp_rna = int(((pred == BARRANCO) & ~es_b).sum())
    tp_veto = int((veto & es_b).sum())
    fp_veto = int((veto & ~es_b).sum())
    solo_rna = int(((pred == BARRANCO) & es_b & ~veto).sum())
    union = int((((pred == BARRANCO) | veto) & es_b).sum())
    nb = int(es_b.sum())
    print(f"\nσ telémetro = {sigma} m · test {len(te)} mapas, n={len(yte)}, barrancos={nb}")
    print(f"  veto duro solo : recall {tp_veto / nb:.3f} ({tp_veto}/{nb}) · falsos positivos {fp_veto}")
    print(f"  RNA (3 rasgos) : recall {r.recall_barranco:.3f} ({tp_rna}/{nb}) · falsos positivos {fp_rna} · "
          f"macro-F1 {r.macro_f1:.3f} · ECE {r.error_calibracion:.3f}")
    print(f"  barrancos que SOLO la RNA ve (bajo el veto): {solo_rna} ({solo_rna / nb:.1%}) · veto ∪ RNA: {union}/{nb}")
    # obstáculos: ¿la proximidad basta?
    es_o = yte == OBSTACULO
    print(f"  obstáculos: recall RNA {((pred == OBSTACULO) & es_o).sum() / max(es_o.sum(), 1):.3f} · "
          f"con proximidad < 1,5: {((Xte[:, 0] < 1.5) & es_o).sum() / max(es_o.sum(), 1):.3f}")
print(f"\n[total] {time.time() - t0:.0f} s")
