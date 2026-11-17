"""RNA-aporte · Medición corta fuera de línea: ¿puede la RNA detectar barrancos sin `borde_barranco`
si el barranco tiene una firma física (desnivel) en el mundo?

Uso: python -I medir_rna_aporte.py <raiz_del_repo>
Solo lectura del repo (parchea generar_mundo en memoria; no escribe nada). Salida por consola.
Mismo tamaño de entrenamiento que rna_entrenada(): 30 mapas, partición por mapas 70/15/15, 300 muestras/mapa.
"""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = sys.argv[1]
sys.path.insert(0, RAIZ)

import numpy as np  # noqa: E402

import rna  # noqa: E402
import simulador  # noqa: E402
from simulador import BARRANCO, LIBRE, MOVIMIENTOS, SensorSuite  # noqa: E402

t0 = time.time()
GENERAR_ORIGINAL = simulador.generar_mundo


def mundo_con_desnivel(desnivel):
    """Devuelve un generar_mundo que baja la elevación `desnivel` m en las celdas BARRANCO."""
    def generar(semilla, **kw):
        m = GENERAR_ORIGINAL(semilla, **kw)
        if desnivel:
            m.elevacion = m.elevacion.copy()
            m.elevacion[m.tipo == BARRANCO] += desnivel
        return m
    return generar


def dataset_horizonte2(semillas, muestras_por_mapa, generar, ruido_grad=0.05):
    """Rasgos para la celda a distancia 2: [proximidad, desnivel a 2 (ruidoso), gradiente a 1 (ruidoso), vibración(celda+2)]."""
    X, y = [], []
    for semilla in semillas:
        rng = np.random.default_rng(10_000 + int(semilla))
        mundo = generar(semilla=int(semilla))
        sensor = SensorSuite(rng=rng, ruido=0.1)
        filas, columnas = mundo.forma
        for _ in range(muestras_por_mapa):
            pos = (int(rng.integers(1, filas - 1)), int(rng.integers(1, columnas - 1)))
            if mundo.tipo[pos] != LIBRE:
                continue
            rumbo = rng.choice(list(MOVIMIENTOS))
            df, dc = MOVIMIENTOS[rumbo]
            c1 = (pos[0] + df, pos[1] + dc)
            c2 = (pos[0] + 2 * df, pos[1] + 2 * dc)
            if not mundo.dentro(c2) or mundo.tipo[c1] != LIBRE:
                continue  # solo interesa la alerta temprana: la celda de enfrente es libre
            lectura = sensor.leer(mundo, pos, rumbo)
            des2 = mundo.elevacion[c2] - mundo.elevacion[pos] + rng.normal(0, ruido_grad)
            grad1 = mundo.elevacion[c1] - mundo.elevacion[pos] + rng.normal(0, 0.05)
            vib = rna.VIBRACION_MEDIA[mundo.tipo[c2]] + rng.normal(0, 0.3)
            X.append([lectura["proximidad_frontal_m"], des2, grad1, vib])
            y.append(int(mundo.tipo[c2]))
    return np.nan_to_num(np.array(X, dtype=float), nan=0.0), np.array(y)


def evaluar(nombre, Xtr, ytr, Xte, yte):
    red = rna.NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    r = red.evaluar(Xte, yte)
    nb = int((yte == BARRANCO).sum())
    pred_b = int((r.predicciones == BARRANCO).sum())
    fp_b = int(((r.predicciones == BARRANCO) & (yte != BARRANCO)).sum())
    print(f"{nombre:58s} recall_barranco={r.recall_barranco:.3f} macroF1={r.macro_f1:.3f} "
          f"ECE={r.error_calibracion:.3f} base={r.precision_base:.3f} | test: barrancos={nb} "
          f"pred_barranco={pred_b} falsos_pos={fp_b} n={len(yte)}")
    return r


tr, va, te = rna.particion_por_mapas(total_mapas=30)
SIN_BORDE = [0, 2, 3]  # columnas: proximidad, gradiente, vibración

print("== Horizonte 1 (celda de enfrente), 30 mapas, 300 muestras/mapa, partición por mapas")
for desnivel in (0.0, -1.0, -3.0):
    simulador.generar_mundo = mundo_con_desnivel(desnivel)
    rna.generar_mundo = simulador.generar_mundo
    Xtr, ytr = rna.generar_dataset(tr, muestras_por_mapa=300)
    Xte, yte = rna.generar_dataset(te, muestras_por_mapa=300)
    evaluar(f"A desnivel={desnivel:+.0f} m · 4 rasgos (con borde)", Xtr, ytr, Xte, yte)
    evaluar(f"B desnivel={desnivel:+.0f} m · sin borde_barranco", Xtr[:, SIN_BORDE], ytr, Xte[:, SIN_BORDE], yte)
    if desnivel:
        # robustez: ruido del gradiente 10 veces mayor (σ 0,5) sobre el mismo desnivel
        rng = np.random.default_rng(7)
        Xtr2, Xte2 = Xtr.copy(), Xte.copy()
        Xtr2[:, 2] += rng.normal(0, 0.5, len(Xtr2))
        Xte2[:, 2] += rng.normal(0, 0.5, len(Xte2))
        evaluar(f"B' desnivel={desnivel:+.0f} m · sin borde, ruido grad σ 0,5", Xtr2[:, SIN_BORDE], ytr, Xte2[:, SIN_BORDE], yte)
print(f"[horizonte 1] {time.time() - t0:.0f} s")

print("\n== Horizonte 2 (celda a distancia 2, con la de enfrente libre): alerta temprana")
for desnivel in (0.0, -3.0):
    gen = mundo_con_desnivel(desnivel)
    Xtr, ytr = dataset_horizonte2(tr, 300, gen)
    Xte, yte = dataset_horizonte2(te, 300, gen)
    evaluar(f"C desnivel={desnivel:+.0f} m · horizonte 2 (sin borde)", Xtr, ytr, Xte, yte)
gen = mundo_con_desnivel(-3.0)
Xtr, ytr = dataset_horizonte2(tr, 300, gen, ruido_grad=0.5)
Xte, yte = dataset_horizonte2(te, 300, gen, ruido_grad=0.5)
evaluar("C' desnivel=-3 m · horizonte 2, ruido desnivel σ 0,5", Xtr, ytr, Xte, yte)

# Celdas vecinas a un barranco que son LIBRE: ¿cuántas hay en los mapas de test? (efecto del desnivel en el difuso)
simulador.generar_mundo = GENERAR_ORIGINAL
vecinas = 0
for s in te:
    m = GENERAR_ORIGINAL(int(s))
    for (f, c), t in np.ndenumerate(m.tipo):
        if t == LIBRE and any(m.dentro((f + df, c + dc)) and m.tipo[f + df, c + dc] == BARRANCO for df, dc in MOVIMIENTOS.values()):
            vecinas += 1
print(f"\nCeldas LIBRE vecinas a un barranco en los {len(te)} mapas de test: {vecinas} (de {len(te) * 600})")
print(f"[total] {time.time() - t0:.0f} s")
