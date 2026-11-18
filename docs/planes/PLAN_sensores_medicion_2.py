"""PLAN-SENSORES · Segunda pasada: (1) cuánto varía el relieve actual entre celdas vecinas (por qué el desnivel no sirve);
(2) mundo v2 con relieve suave 2D + barrancos de profundidad U(1,4) m; sensores: telémetro inclinado (desnivel, σ_t) y
cámara (contraste óptico de la celda siguiente, función de la profundidad/altura, σ_c, degradada de noche); veto duro
desnivel < −2 m; RNA fusiona ambos. Mide recall/FP del veto, de la RNA, y la banda que SOLO la RNA cubre.
Uso: python -I medir_sensores_rediseno_2.py <raiz_del_repo>. Solo lectura del repo."""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402

import rna  # noqa: E402
from simulador import BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, generar_mundo  # noqa: E402

t0 = time.time()
UMBRAL_BORDE = -2.0

# (1) relieve actual: desnivel natural entre vecinos libres
dif_ns, dif_eo = [], []
for s in range(20):
    m = generar_mundo(s)
    e = m.elevacion
    dif_ns += list(np.abs(np.diff(e, axis=0)).ravel())
    dif_eo += list(np.abs(np.diff(e, axis=1)).ravel())
dif_ns, dif_eo = np.array(dif_ns), np.array(dif_eo)
print(f"Relieve actual (20 mapas): |desnivel| entre vecinos N-S: mediana {np.median(dif_ns):.2f} m, p90 {np.percentile(dif_ns, 90):.2f}, "
      f"máx {dif_ns.max():.2f}; E-O: mediana {np.median(dif_eo):.2f}, p90 {np.percentile(dif_eo, 90):.2f}, máx {dif_eo.max():.2f}")
print(f"  vecinos N-S con |desnivel| > 2 m: {(dif_ns > 2).mean():.1%} (un umbral de borde a −2 m los confunde con barrancos)")


def mundo_v2(semilla, amplitud=1.5, suavidad=3.0, prof=(1.0, 4.0)):
    m = generar_mundo(semilla=int(semilla))
    rng = np.random.default_rng([int(semilla), 93])
    base = gaussian_filter(rng.normal(0, 1, size=m.forma), sigma=suavidad)
    base = base / (base.std() + 1e-9) * amplitud          # relieve suave 2D, desviación `amplitud` m
    prof_celda = np.zeros(m.forma)
    for (f, c) in np.argwhere(m.tipo == BARRANCO):
        prof_celda[f, c] = rng.uniform(*prof)
    m.elevacion = base - prof_celda
    m.profundidad = prof_celda
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


def dataset(semillas, muestras, sigma_t, sigma_c, con_camara=True):
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
            prox = proximidad_obstaculo(m, pos, rumbo) + rng.normal(0, 0.1)
            desn = m.elevacion[sig] - m.elevacion[pos] + rng.normal(0, sigma_t)
            # cámara: contraste óptico de la celda siguiente. Hoyo en sombra → oscuro (proporcional a la profundidad);
            # roca → brillante; suelo libre → ~0. Ruido σ_c (supuesto de simulación, función de la geometría, no de la etiqueta).
            if m.tipo[sig] == BARRANCO:
                contraste = -min(1.0, m.profundidad[sig] / 4.0)
            elif m.tipo[sig] == OBSTACULO:
                contraste = 0.8
            else:
                contraste = 0.0
            contraste += rng.normal(0, sigma_c)
            fila = [prox, desn] + ([contraste] if con_camara else [])
            X.append(fila)
            y.append(int(m.tipo[sig]))
    return np.array(X), np.array(y)


tr, _, _ = rna.particion_por_mapas(total_mapas=60)
te = np.arange(100, 120)
print("\nMundo v2: relieve suave 2D (desv. 1,5 m, suavidad 3 celdas), barrancos U(1,4) m; veto duro desnivel < −2 m")
for sigma_t, sigma_c, cam in ((0.3, 0.4, True), (0.5, 0.4, True), (0.5, 0.6, True), (0.5, 0.0, False), (0.8, 0.6, True)):
    Xtr, ytr = dataset(tr, 400, sigma_t, sigma_c, cam)
    Xte, yte = dataset(te, 400, sigma_t, sigma_c, cam)
    red = rna.NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    r = red.evaluar(Xte, yte)
    pred = r.predicciones
    es_b = yte == BARRANCO
    veto = Xte[:, 1] < UMBRAL_BORDE
    nb = int(es_b.sum())
    tp_rna = int(((pred == BARRANCO) & es_b).sum()); fp_rna = int(((pred == BARRANCO) & ~es_b).sum())
    tp_veto = int((veto & es_b).sum()); fp_veto = int((veto & ~es_b).sum())
    solo_rna = int(((pred == BARRANCO) & es_b & ~veto).sum())
    union = int((((pred == BARRANCO) | veto) & es_b).sum())
    etiqueta = f"σ_telémetro={sigma_t} m, cámara {'σ=' + str(sigma_c) if cam else 'NO'}"
    print(f"\n{etiqueta} · test n={len(yte)}, barrancos={nb}")
    print(f"  veto duro solo : recall {tp_veto / nb:.3f} ({tp_veto}/{nb}) · FP {fp_veto}")
    print(f"  RNA            : recall {r.recall_barranco:.3f} ({tp_rna}/{nb}) · FP {fp_rna} · macro-F1 {r.macro_f1:.3f} · ECE {r.error_calibracion:.3f}")
    print(f"  SOLO la RNA (barrancos bajo el veto): {solo_rna} ({solo_rna / nb:.1%}) · veto ∪ RNA: {union}/{nb} ({union / nb:.3f})")
print(f"\n[total] {time.time() - t0:.0f} s")
