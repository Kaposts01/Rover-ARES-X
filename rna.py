"""ARES-X · Fase 2: red neuronal de percepción (MLP 32-16, ReLU, softmax de 3 clases).

La etiqueta es el tipo REAL de la celda de enfrente (verdad del simulador).
Las características son lecturas ruidosas de los sensores, sin etiquetar con la misma variable.
Partición train/valid/test por MAPAS (semillas distintas), no por filas (sección 10.1).
"""
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from simulador import (BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, UMBRAL_DESNIVEL_BARRANCO_M, SensorSuite,
                       generar_mundo)

CLASES = {LIBRE: "libre", OBSTACULO: "obstáculo", BARRANCO: "barranco"}
NOMBRES_RASGOS = ["proximidad_frontal_m", "borde_barranco", "gradiente_altura_m", "vibracion"]
# ARX-93b (ev3-d78 A): modelo aparte, sin el rasgo de borde (que es la lectura del LIDAR del supervisor).
# El modelo actual y NOMBRES_RASGOS no cambian; /rna y el panel usan la lista del modelo activo.
NOMBRES_RASGOS_TERRENO = ["proximidad_frontal_m", "gradiente_altura_m", "vibracion"]
# ARX-93c: alerta temprana. Predice la celda a DOS pasos (con la de enfrente libre) y su altímetro frontal.
NOMBRES_RASGOS_ALERTA2 = ["proximidad_frontal_m", "desnivel_a_2_m", "gradiente_altura_m", "vibracion"]
PERFILES_RASGOS = {"actual": NOMBRES_RASGOS, "terreno": NOMBRES_RASGOS_TERRENO,
                   "alerta2": NOMBRES_RASGOS_ALERTA2}
COLUMNAS_TERRENO = [0, 2, 3]      # de un vector del perfil "actual" a los rasgos del modelo terreno

# Media de la vibración según lo que hay delante (supuesto de simulación: débil señal)
VIBRACION_MEDIA = {LIBRE: 0.2, OBSTACULO: 0.6, BARRANCO: 0.4}


def _rasgos_celda(mundo, pos, rumbo, sensor, rng):
    """Vector de rasgos para una celda observada desde pos mirando hacia rumbo."""
    lectura = sensor.leer(mundo, pos, rumbo)
    df, dc = MOVIMIENTOS[rumbo]
    delante = (pos[0] + df, pos[1] + dc)
    if mundo.dentro(delante):
        gradiente = mundo.elevacion[delante] - mundo.elevacion[pos]
        clase = mundo.tipo[delante]
    else:
        gradiente, clase = 0.0, LIBRE
    grad_ruidoso = gradiente + rng.normal(0, 0.05)
    vibracion = VIBRACION_MEDIA[clase] + rng.normal(0, 0.3)
    # ARX-94c: la lectura `borde_barranco` ya no existe; el rasgo se deriva aquí del desnivel que mide el telémetro
    # (misma semántica: 1 si < umbral, NaN si no hubo lectura). 94d lo reemplaza por los rasgos del modelo v2.
    desnivel = lectura["desnivel_frontal_m"]
    borde = float("nan") if desnivel != desnivel else float(desnivel < UMBRAL_DESNIVEL_BARRANCO_M)
    return [
        lectura["proximidad_frontal_m"],
        borde,
        grad_ruidoso,
        vibracion,
    ], int(clase)


def _rasgos_terreno(mundo, pos, rumbo, sensor, rng):
    """Como _rasgos_celda pero sin borde_barranco: la RNA solo ve proximidad, gradiente y vibración."""
    rasgos, clase = _rasgos_celda(mundo, pos, rumbo, sensor, rng)
    return [rasgos[0], rasgos[2], rasgos[3]], clase


def _rasgos_alerta2(mundo, pos, rumbo, sensor, rng):
    """Rasgos para la celda a distancia 2; None si cae fuera del mapa.

    [proximidad, desnivel a 2 (altímetro, σ 0,05), gradiente a 1, vibración de la celda a 2]; la etiqueta
    es el tipo real de la celda a 2. Misma convención de vibración que `_rasgos_celda` (ver 93d).
    """
    df, dc = MOVIMIENTOS[rumbo]
    c1 = (pos[0] + df, pos[1] + dc)
    c2 = (pos[0] + 2 * df, pos[1] + 2 * dc)
    if not mundo.dentro(c2):
        return None
    lectura = sensor.leer(mundo, pos, rumbo)
    desnivel = sensor.leer_desnivel(mundo, pos, rumbo, 2)
    gradiente = mundo.elevacion[c1] - mundo.elevacion[pos] + rng.normal(0, 0.05)
    vibracion = VIBRACION_MEDIA[mundo.tipo[c2]] + rng.normal(0, 0.3)
    return [lectura["proximidad_frontal_m"], desnivel, gradiente, vibracion], int(mundo.tipo[c2])


def _rasgos_alerta2_entrenamiento(mundo, pos, rumbo, sensor, rng):
    """Solo interesa la alerta temprana: la celda de enfrente es libre (se decide antes de sortear ruido)."""
    df, dc = MOVIMIENTOS[rumbo]
    if mundo.tipo[(pos[0] + df, pos[1] + dc)] != LIBRE:
        return None
    return _rasgos_alerta2(mundo, pos, rumbo, sensor, rng)


def generar_dataset(semillas, muestras_por_mapa=400, ruido=0.1, prob_fallo=0.0, perfil="actual"):
    """Muestras etiquetadas a partir de mapas con las semillas indicadas.

    perfil="actual" (por defecto) es el modelo entregable, con borde_barranco;
    perfil="terreno" es el modelo de ARX-93, sin ese rasgo (mismo flujo de azar).
    """
    if perfil not in PERFILES_RASGOS:
        raise ValueError(f"Perfil de rasgos desconocido: {perfil}")
    rasgos_de = {"actual": _rasgos_celda, "terreno": _rasgos_terreno,
                 "alerta2": _rasgos_alerta2_entrenamiento}[perfil]
    X, y = [], []
    for semilla in semillas:
        rng = np.random.default_rng(10_000 + semilla)
        mundo = generar_mundo(semilla=semilla)
        sensor = SensorSuite(rng=rng, ruido=ruido, prob_fallo=prob_fallo)
        filas, columnas = mundo.forma
        for _ in range(muestras_por_mapa):
            pos = (int(rng.integers(1, filas - 1)), int(rng.integers(1, columnas - 1)))
            if mundo.tipo[pos] != LIBRE:
                continue
            rumbo = rng.choice(list(MOVIMIENTOS))
            resultado = rasgos_de(mundo, pos, rumbo, sensor, rng)
            if resultado is None:
                continue
            rasgos, clase = resultado
            X.append(rasgos)
            y.append(clase)
    X = np.nan_to_num(np.array(X, dtype=float), nan=0.0)
    return X, np.array(y)


def particion_por_mapas(total_mapas=60, seed_base=0):
    """Reparte mapas, no muestras: 70 % entrenamiento, 15 % validación, 15 % prueba."""
    semillas = np.arange(seed_base, seed_base + total_mapas)
    n_train = int(0.70 * total_mapas)
    n_valid = int(0.15 * total_mapas)
    return semillas[:n_train], semillas[n_train:n_train + n_valid], semillas[n_train + n_valid:]


@dataclass
class ResultadoRNA:
    predicciones: np.ndarray
    matriz_confusion: np.ndarray
    macro_f1: float
    recall_barranco: float
    precision_base: float   # exactitud de predecir siempre la clase mayoritaria
    error_calibracion: float


class NeuralPerception:
    def __init__(self, semilla=42, nombres=None, columnas=None):
        self.nombres = list(nombres) if nombres is not None else list(NOMBRES_RASGOS)
        # Si el vector de entrada es el del perfil "actual" (4 rasgos, como lo arman partida y conduccion),
        # `columnas` elige los que usa este modelo; así el modelo terreno convive con esos llamadores.
        self.columnas = list(columnas) if columnas is not None else None
        self.modelo = MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu",
                                    max_iter=300, random_state=semilla,
                                    early_stopping=True, validation_fraction=0.15)
        self.escalador = StandardScaler()
        self.entrenado = False

    def entrenar(self, X, y):
        Xs = self.escalador.fit_transform(X)
        self.modelo.fit(Xs, y)
        self.entrenado = True
        return self

    def _seleccionar(self, X):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        if self.columnas is not None and X.shape[1] == len(NOMBRES_RASGOS):
            X = X[:, self.columnas]
        return X

    def predecir_proba(self, X):
        if not self.entrenado:
            raise RuntimeError("La RNA no está entrenada.")
        return self.modelo.predict_proba(self.escalador.transform(self._seleccionar(X)))

    def evaluar(self, X, y) -> ResultadoRNA:
        proba = self.predecir_proba(X)
        pred = self.modelo.classes_[proba.argmax(axis=1)]
        confianza = proba.max(axis=1)
        aciertos = (pred == y).astype(float)
        # Error de calibración esperado (ECE) con 10 contenedores
        bordes = np.linspace(0, 1, 11)
        ece = 0.0
        for lo, hi in zip(bordes[:-1], bordes[1:]):
            m = (confianza > lo) & (confianza <= hi)
            if m.any():
                ece += m.mean() * abs(confianza[m].mean() - aciertos[m].mean())
        clases = list(CLASES)
        mayoritaria = np.bincount(y, minlength=3).argmax()
        return ResultadoRNA(
            predicciones=pred,
            matriz_confusion=confusion_matrix(y, pred, labels=clases),
            macro_f1=float(f1_score(y, pred, labels=clases, average="macro", zero_division=0)),
            recall_barranco=float(((pred == BARRANCO) & (y == BARRANCO)).sum()
                                  / max((y == BARRANCO).sum(), 1)),
            precision_base=float((y == mayoritaria).mean()),
            error_calibracion=float(ece),
        )

    def explicar(self, rasgos):
        """Evidencia visible (sección 10.1): entrada → normalización → probabilidades."""
        x = self._seleccionar(rasgos)[0]
        normalizada = self.escalador.transform(x.reshape(1, -1))[0]
        proba = self.predecir_proba(x)[0]
        return {
            "entrada": dict(zip(self.nombres, x.tolist())),
            "normalizada": dict(zip(self.nombres, np.round(normalizada, 3).tolist())),
            "probabilidades": {CLASES[c]: round(float(p), 3)
                               for c, p in zip(self.modelo.classes_, proba)},
            "confianza": round(float(proba.max()), 3),
        }
