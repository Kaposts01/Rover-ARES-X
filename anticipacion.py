"""ARES-X · R23: RNA con anticipación (celdas de la ruta a 2, 3 y 4 pasos).

El evaluador forzó un barranco en (7, 11) y la RNA siguió diciendo «libre 100 %» hasta tenerlo encima: la RNA original solo
clasifica la celda siguiente. Aquí una segunda red (misma arquitectura MLP 32-16) clasifica las celdas de la ruta a k = 2, 3 y 4
pasos.

**Alcance de los sensores (supuesto de simulación, declarado).** Los sensores actuales del rover (`SensorSuite.leer`) solo miden la
celda de enfrente (telémetro inclinado y cámara); no llegan a 2 a 4 celdas. Lo mínimo necesario para anticipar es ampliar su alcance
a 4 celdas con ruido creciente con la distancia: σ_k = σ_1 · (1 + 0,5 · (k − 1)) (a 4 celdas, 2,5 veces el ruido de la primera).
Con ese supuesto la red usa cuatro rasgos de la celda objetivo: desnivel medido hasta ella, desnivel medido hasta la celda anterior
de la ruta, contraste óptico de la cámara y la distancia k. No usa la vibración (es de la celda actual y no dice nada de una celda
lejana, ARX-93c) ni el tipo real de ninguna celda. La proximidad de obstáculos ya llega a 20 celdas y V-OBSTACULO-EN-RUTA la usa.

Las lecturas usan un generador propio (no consumen el azar de la misión). Una celda se marca como riesgo cuando la media de
p(barranco) de sus observaciones supera 0,5 con al menos dos observaciones (a distancias distintas, en pasos sucesivos).
"""
from functools import lru_cache

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from rna import CLASES, particion_por_mapas
from simulador import (BARRANCO, CONTRASTE_HOYO_M, CONTRASTE_ROCA, ESCALA_CAMARA, ESCALA_DESNIVEL, LIBRE, MOVIMIENTOS,
                       OBSTACULO, generar_mundo)

DISTANCIAS = (2, 3, 4)
CRECE_RUIDO_POR_CELDA = 0.5          # σ_k = σ_1 · (1 + 0,5 · (k − 1))
NOMBRES_RASGOS = ["desnivel_hasta_celda_m", "desnivel_hasta_anterior_m", "contraste_optico", "distancia_celdas"]
SEMILLA_BASE_REFUERZO = 70_000


def _sigma(base: float, ruido: float, k: int) -> float:
    return ruido * base * (1.0 + CRECE_RUIDO_POR_CELDA * (k - 1))


def rasgos_anticipacion(mundo, pos, anterior, celda, k: int, rng, ruido: float = 0.1, ambiente: str = "normal"):
    """Rasgos [desnivel hasta `celda`, desnivel hasta `anterior`, contraste de `celda`, k] medidos desde `pos`.

    `anterior` es la celda de la ruta justo antes de `celda`. Ruido gaussiano que crece con la distancia; la tormenta duplica el
    ruido y la noche y la tormenta degradan la cámara (como SensorSuite). NaN si `celda` queda fuera del mapa."""
    if not mundo.dentro(celda) or not mundo.dentro(anterior):
        return [float("nan")] * 3 + [float(k)]
    general = 2.0 if ambiente == "tormenta" else 1.0
    s_d = _sigma(ESCALA_DESNIVEL, ruido, k) * general
    s_p = _sigma(ESCALA_DESNIVEL, ruido, max(1, k - 1)) * general
    d_k = float(mundo.elevacion[celda] - mundo.elevacion[pos] + rng.normal(0, s_d))
    d_p = float(mundo.elevacion[anterior] - mundo.elevacion[pos] + rng.normal(0, s_p))
    if mundo.profundidad[celda] > 0:
        senal = -min(1.0, mundo.profundidad[celda] / CONTRASTE_HOYO_M)
    elif mundo.altura[celda] > 0:
        senal = CONTRASTE_ROCA
    else:
        senal = 0.0
    degradada = ambiente in ("noche", "tormenta")
    s_c = _sigma(ESCALA_CAMARA, ruido, k) * (2.0 if degradada else 1.0)
    contraste = float((senal * (0.5 if degradada else 1.0)) + rng.normal(0, s_c))
    return [d_k, d_p, contraste, float(k)]


def generar_dataset(semillas, muestras_por_mapa: int = 500, ruido: float = 0.1, p_barranco: float = 0.30,
                    p_obstaculo: float = 0.10, base_refuerzo: int = 0):
    """Muestras (rasgos, clase de la celda objetivo) sobre mapas de las semillas dadas: una carrera recta de k celdas desde una celda
    libre con las k − 1 primeras libres (si no, el rover ya vería lo de antes). El `p_barranco` de las muestras mira a un barranco
    (refuerzo: es ~1 % de las celdas) y el `p_obstaculo`, a un obstáculo; el resto, a una celda libre al azar."""
    X, y = [], []
    for semilla in semillas:
        rng = np.random.default_rng(30_000 + int(semilla) + base_refuerzo)
        mundo = generar_mundo(semilla=int(semilla) + base_refuerzo, n_barrancos=20 if base_refuerzo else 6)
        filas, cols = mundo.forma
        barrancos = list(zip(*np.nonzero(mundo.tipo == BARRANCO)))
        obstaculos = list(zip(*np.nonzero(mundo.tipo == OBSTACULO)))
        rumbos = list(MOVIMIENTOS.values())
        hechas, intentos = 0, 0
        while hechas < muestras_por_mapa and intentos < muestras_por_mapa * 30:
            intentos += 1
            u = rng.random()
            k = int(rng.choice(DISTANCIAS))
            df, dc = rumbos[int(rng.integers(len(rumbos)))]
            if u < p_barranco and barrancos:
                objetivo = barrancos[int(rng.integers(len(barrancos)))]
            elif u < p_barranco + p_obstaculo and obstaculos:
                objetivo = obstaculos[int(rng.integers(len(obstaculos)))]
            else:
                objetivo = (int(rng.integers(filas)), int(rng.integers(cols)))
            objetivo = (int(objetivo[0]), int(objetivo[1]))
            pos = (objetivo[0] - k * df, objetivo[1] - k * dc)
            celdas = [(pos[0] + i * df, pos[1] + i * dc) for i in range(0, k + 1)]
            if not all(mundo.dentro(c) for c in celdas) or any(mundo.tipo[c] != LIBRE for c in celdas[:-1]):
                continue
            X.append(rasgos_anticipacion(mundo, pos, celdas[-2], celdas[-1], k, rng, ruido))
            y.append(int(mundo.tipo[objetivo]))
            hechas += 1
    return np.nan_to_num(np.array(X, dtype=float), nan=0.0), np.array(y)


# Proporción real de cada clase entre las celdas de una ruta del juego (mapa 20x30: ~1,5 % barrancos, ~4 % obstáculos). Las muestras de
# entrenamiento llevan muchos más barrancos (refuerzo), así que las probabilidades de la red se corrigen por el cociente de las
# proporciones (regla de Bayes): sin esa corrección el 12 a 22 % de las celdas libres salía como barranco.
PRIOR_REAL = {LIBRE: 0.945, OBSTACULO: 0.04, BARRANCO: 0.015}


class RnaAnticipacion:
    def __init__(self, semilla: int = 42):
        self.modelo = MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu", max_iter=300, random_state=semilla,
                                    early_stopping=True, validation_fraction=0.15)
        self.escalador = StandardScaler()
        self.nombres = list(NOMBRES_RASGOS)

    def entrenar(self, X, y):
        self.modelo.fit(self.escalador.fit_transform(X), y)
        y = np.asarray(y)
        self.prior_entrenamiento = {c: max(float((y == c).mean()), 1e-6) for c in self.modelo.classes_}
        return self

    def corregir(self, proba) -> np.ndarray:
        """Probabilidades con la proporción real de clases (Bayes) en vez de la del conjunto de entrenamiento."""
        w = np.array([PRIOR_REAL[c] / self.prior_entrenamiento[c] for c in self.modelo.classes_])
        q = np.asarray(proba) * w
        return q / q.sum(axis=-1, keepdims=True)

    def probabilidades(self, rasgos) -> dict:
        x = np.nan_to_num(np.atleast_2d(np.asarray(rasgos, dtype=float)), nan=0.0)
        proba = self.corregir(self.modelo.predict_proba(self.escalador.transform(x)))[0]
        return {CLASES[c]: round(float(p), 4) for c, p in zip(self.modelo.classes_, proba)}


@lru_cache(maxsize=4)
def rna_anticipacion(ruido: float = 0.1, semilla: int = 42) -> RnaAnticipacion:
    """RNA de anticipación del juego: 30 mapas de la partición de la RNA (los de entrenamiento) más mapas de refuerzo de barrancos."""
    tr, _, _ = particion_por_mapas(total_mapas=30)
    X, y = generar_dataset(tr, 500, ruido)
    Xr, yr = generar_dataset(tr, 300, ruido, p_barranco=0.9, p_obstaculo=0.0, base_refuerzo=SEMILLA_BASE_REFUERZO)
    return RnaAnticipacion(semilla).entrenar(np.vstack([X, Xr]), np.concatenate([y, yr]))


def evaluar(rna: RnaAnticipacion, semillas=range(51, 60), muestras_por_mapa: int = 400, ruido: float = 0.1) -> dict:
    """Recall de barrancos y tasa de falsos barrancos (libres marcadas como barranco), por distancia k, en mapas de prueba.
    Los datos de prueba salen sin refuerzo de barrancos de más: p_barranco = 0,30 en las muestras (se informa el recall, que no
    depende de esa proporción, y la tasa de falsos positivos sobre las celdas libres, que tampoco)."""
    X, y = generar_dataset(semillas, muestras_por_mapa, ruido)
    ks = X[:, 3].astype(int)
    proba = rna.corregir(rna.modelo.predict_proba(rna.escalador.transform(X)))
    pred = rna.modelo.classes_[proba.argmax(axis=1)]
    out = {}
    for k in DISTANCIAS:
        sel = ks == k
        bar, lib = sel & (y == BARRANCO), sel & (y == LIBRE)
        out[k] = {"recall_barranco": round(float(((pred == BARRANCO) & bar).sum() / max(bar.sum(), 1)), 3),
                  "falsos_barrancos_en_libres": round(float(((pred == BARRANCO) & lib).sum() / max(lib.sum(), 1)), 4),
                  "n_barrancos": int(bar.sum()), "n_libres": int(lib.sum())}
    return out
