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

import contextlib

import simulador
from simulador import BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, SensorSuite, generar_mundo

CLASES = {LIBRE: "libre", OBSTACULO: "obstáculo", BARRANCO: "barranco"}
# ARX-94d: modelo v2, entrenado con los sensores físicos del mundo v2. Ningún rasgo sale del tipo de celda:
# la proximidad ve solo volúmenes, el desnivel y el contraste miden geometría de la celda siguiente y la
# vibración (IMU) es de la celda ACTUAL. La etiqueta (tipo real de la celda siguiente) solo sirve para entrenar.
NOMBRES_RASGOS_V2 = ["proximidad_frontal_m", "desnivel_frontal_m", "contraste_optico", "vibracion"]
# Modelo v1 (entrega del 17/11): conservado con su dataset en el mundo v1 (`simulador.MUNDO_V1`), con el LIDAR
# exacto de borde y la vibración por clase de la celda de enfrente. Es la referencia publicada, no el del juego.
NOMBRES_RASGOS_V1 = ["proximidad_frontal_m", "borde_barranco", "gradiente_altura_m", "vibracion"]
NOMBRES_RASGOS = NOMBRES_RASGOS_V2        # modelo por defecto
# ARX-93b (ev3-d78 A): modelo aparte, sin el rasgo de borde (pista del mundo v1 con firma física).
NOMBRES_RASGOS_TERRENO = ["proximidad_frontal_m", "gradiente_altura_m", "vibracion"]
# ARX-93c (descartada): predice la celda a DOS pasos. Solo evidencia, en el mundo v1.
NOMBRES_RASGOS_ALERTA2 = ["proximidad_frontal_m", "desnivel_a_2_m", "gradiente_altura_m", "vibracion"]
PERFILES_RASGOS = {"v2": NOMBRES_RASGOS_V2, "v1": NOMBRES_RASGOS_V1, "actual": NOMBRES_RASGOS_V1,
                   "terreno": NOMBRES_RASGOS_TERRENO, "alerta2": NOMBRES_RASGOS_ALERTA2}
COLUMNAS_TERRENO = [0, 2, 3]      # de un vector del perfil v1 a los rasgos del modelo terreno

# SOLO mundo v1: media de la vibración según lo que hay delante (supuesto de simulación del modelo v1).
# El modelo v2 no la usa: su vibración es la de la celda actual.
VIBRACION_MEDIA = {LIBRE: 0.2, OBSTACULO: 0.6, BARRANCO: 0.4}


@contextlib.contextmanager
def _mundo_v1(activo: bool):
    """Fija `simulador.MUNDO_V1` mientras se genera un dataset y lo restaura."""
    anterior = simulador.MUNDO_V1
    simulador.MUNDO_V1 = bool(activo)
    try:
        yield
    finally:
        simulador.MUNDO_V1 = anterior


def _leer_v1(mundo, pos, rumbo, sensor):
    """Sensor del esquema v1 (LIDAR exacto de borde, proximidad que cuenta barrancos). Mismo consumo de azar
    que el `leer` anterior a ARX-94b: dos lecturas ruidosas (proximidad y altímetro)."""
    df, dc = MOVIMIENTOS[rumbo]
    distancia = 20
    for paso in range(1, 21):
        p = (pos[0] + df * paso, pos[1] + dc * paso)
        if not mundo.dentro(p):
            break
        if mundo.tipo[p] != LIBRE:
            distancia = paso
            break
    borde = any(mundo.dentro((pos[0] + a, pos[1] + b)) and mundo.tipo[(pos[0] + a, pos[1] + b)] == BARRANCO
                for a, b in MOVIMIENTOS.values())
    proximidad = sensor._ruidoso(distancia, 1.0)
    sensor._ruidoso(mundo.elevacion[pos], 0.5)          # altímetro: consume azar igual que antes
    return {"proximidad_frontal_m": proximidad, "borde_barranco": borde}


def _rasgos_celda_v1(mundo, pos, rumbo, sensor, rng):
    """Vector v1 [proximidad, borde, gradiente, vibración] (esquema de la entrega del 17/11)."""
    lectura = _leer_v1(mundo, pos, rumbo, sensor)
    df, dc = MOVIMIENTOS[rumbo]
    delante = (pos[0] + df, pos[1] + dc)
    if mundo.dentro(delante):
        gradiente = mundo.elevacion[delante] - mundo.elevacion[pos]
        clase = mundo.tipo[delante]
    else:
        gradiente, clase = 0.0, LIBRE
    grad_ruidoso = gradiente + rng.normal(0, 0.05)
    vibracion = VIBRACION_MEDIA[clase] + rng.normal(0, 0.3)
    return [lectura["proximidad_frontal_m"], 1.0 if lectura["borde_barranco"] else 0.0,
            grad_ruidoso, vibracion], int(clase)


def _rasgos_celda_v2(mundo, pos, rumbo, sensor, rng=None):
    """Vector v2 [proximidad, desnivel frontal, contraste óptico, vibración] y la etiqueta de entrenamiento.

    Los rasgos salen solo de `sensor.leer`; el tipo real de la celda siguiente se devuelve aparte como etiqueta
    (fuera del mapa: libre, como antes). NaN (fuera del mapa o falla) se mantiene aquí; se trata al predecir.
    """
    lectura = sensor.leer(mundo, pos, rumbo)
    df, dc = MOVIMIENTOS[rumbo]
    delante = (pos[0] + df, pos[1] + dc)
    clase = mundo.tipo[delante] if mundo.dentro(delante) else LIBRE
    return [lectura["proximidad_frontal_m"], lectura["desnivel_frontal_m"],
            lectura["contraste_optico"], lectura["vibracion"]], int(clase)


def _rasgos_celda(mundo, pos, rumbo, sensor, rng=None):
    """Rasgos del modelo activo: v1 si `simulador.MUNDO_V1`, v2 si no (ver `perfil_activo`)."""
    if simulador.MUNDO_V1:
        return _rasgos_celda_v1(mundo, pos, rumbo, sensor, rng)
    return _rasgos_celda_v2(mundo, pos, rumbo, sensor, rng)


def perfil_activo() -> str:
    return "v1" if simulador.MUNDO_V1 else "v2"


def inclinacion_de_rasgos(rasgos) -> float:
    """Magnitud de la pendiente frontal (m) para el difuso: gradiente (v1) o desnivel medido (v2; NaN = 0)."""
    valor = rasgos[2] if simulador.MUNDO_V1 else rasgos[1]
    return 0.0 if valor != valor else abs(float(valor))


def _rasgos_terreno(mundo, pos, rumbo, sensor, rng):
    """Como _rasgos_celda pero sin borde_barranco: la RNA solo ve proximidad, gradiente y vibración."""
    rasgos, clase = _rasgos_celda_v1(mundo, pos, rumbo, sensor, rng)
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
    lectura = _leer_v1(mundo, pos, rumbo, sensor)
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


# R23 (RNA): el barranco es ~1 % de las celdas «de enfrente» y la red entrenada con esa proporción lo daba por libre con
# confianza del 100 % cuando era poco profundo (recall 19/30 = 63 % en los mapas de prueba). El refuerzo añade escenas
# dirigidas, con barrancos de profundidad sorteada como en el juego, mirados desde una celda libre vecina.
SEMILLA_BASE_REFUERZO = 50_000        # los mapas de refuerzo salen de semillas lejanas a las de prueba (≤ 200)
# Muestras dirigidas por mapa de entrenamiento que usa el modelo v2 con ruido nominal. Medido (R23b; 60 mapas, 400 muestras, prueba
# 51-59, argmax): refuerzo 0 -> macro-F1 0,906, barranco 19/30, 2 libres marcadas como barranco; 15 -> 0,890, 23/30 (77 %), 14;
# 100 -> 0,819, 25/30, 52 (la primera versión de R23: subía el recall pero marcaba 26 veces más celdas libres y los vetos de más).
# En 60 mapas no vistos (100-159): 0 -> 0,913 / 66 %; 15 -> 0,908 / 77 %, 0,31 % de libres marcadas; 100 -> 0,849 / 88 %, 1,3 %.
# El punto elegido (15) recupera el macro-F1 >= 0,88 con recall >= 0,75 sin cambiar el umbral de veto (0,5). Más refuerzo solo
# sube los falsos positivos: los barrancos de 1,0 a 1,5 m se confunden con la pendiente natural (límite físico del telémetro).
REFUERZO_BARRANCO_POR_MAPA = 15
BARRANCOS_MAPA_REFUERZO = 20          # barrancos por mapa de refuerzo (el juego usa 5-9 por mapa de 20x30)


def generar_dataset(semillas, muestras_por_mapa=400, ruido=0.1, prob_fallo=0.0, perfil="v2", refuerzo_barranco=0):
    """Muestras etiquetadas a partir de mapas con las semillas indicadas.

    `refuerzo_barranco`: muestras dirigidas ADICIONALES por semilla, tomadas de un mapa de refuerzo propio (semilla
    `SEMILLA_BASE_REFUERZO + semilla`, con muchos barrancos) y siempre mirando a un barranco desde una celda libre
    vecina. Solo para entrenar: no altera el azar de las muestras naturales (van al final) y los datos de prueba se
    generan sin él (con 0 el resultado es idéntico al de antes).

    perfil="v2" (por defecto): sensores físicos sobre el mundo v2 (ARX-94d). perfil="v1" (alias "actual"):
    el modelo de la entrega del 17/11, con su dataset en el mundo v1. "terreno" y "alerta2" son las pistas de
    ARX-93 (mundo v1, mismo flujo de azar que entonces). Cada perfil fija el mundo que usa y lo restaura.
    """
    if perfil not in PERFILES_RASGOS:
        raise ValueError(f"Perfil de rasgos desconocido: {perfil}")
    rasgos_de = {"v2": _rasgos_celda_v2, "v1": _rasgos_celda_v1, "actual": _rasgos_celda_v1,
                 "terreno": _rasgos_terreno, "alerta2": _rasgos_alerta2_entrenamiento}[perfil]
    with _mundo_v1(perfil != "v2"):
        return _dataset(semillas, muestras_por_mapa, ruido, prob_fallo, rasgos_de, refuerzo_barranco)


def _refuerzo_barranco(semilla, cantidad, ruido, prob_fallo, rasgos_de, X, y):
    """Agrega `cantidad` muestras de barranco: celda libre cardinal vecina de un barranco, mirando hacia él."""
    rng = np.random.default_rng(20_000 + semilla)
    mundo = generar_mundo(semilla=SEMILLA_BASE_REFUERZO + semilla, n_barrancos=BARRANCOS_MAPA_REFUERZO)
    sensor = SensorSuite(rng=rng, ruido=ruido, prob_fallo=prob_fallo)
    posibles = []
    for celda in zip(*np.nonzero(mundo.tipo == BARRANCO)):
        for rumbo, (df, dc) in MOVIMIENTOS.items():
            pos = (int(celda[0]) - df, int(celda[1]) - dc)      # desde `pos` con ese rumbo se mira a `celda`
            if mundo.dentro(pos) and mundo.tipo[pos] == LIBRE:
                posibles.append((pos, rumbo))
    for _ in range(cantidad if posibles else 0):
        pos, rumbo = posibles[int(rng.integers(len(posibles)))]
        resultado = rasgos_de(mundo, pos, rumbo, sensor, rng)
        if resultado is not None:
            X.append(resultado[0])
            y.append(resultado[1])


def _dataset(semillas, muestras_por_mapa, ruido, prob_fallo, rasgos_de, refuerzo_barranco=0):
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
    if refuerzo_barranco:
        for semilla in semillas:
            _refuerzo_barranco(int(semilla), int(refuerzo_barranco), ruido, prob_fallo, rasgos_de, X, y)
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
    def __init__(self, semilla=42, nombres=None, columnas=None, perfil=None):
        self.nombres = list(nombres) if nombres is not None else list(NOMBRES_RASGOS)
        self.perfil = perfil          # "v1", "v2" u otro; solo informa qué modelo es
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
        X = np.nan_to_num(np.atleast_2d(np.asarray(X, dtype=float)), nan=0.0)   # igual que al entrenar
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
