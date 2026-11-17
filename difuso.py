"""ARES-X · Fase 3: controlador difuso Mamdani (min–max, centroide).

Entradas: distancia al riesgo (m), batería (%), inclinación (°).
Salida: velocidad en [0, 1]. Todos los rangos y funciones son supuestos de simulación.
"""
from dataclasses import dataclass

import numpy as np


def trapecio(x, a, b, c, d):
    """Membresía trapezoidal. Con b == a o c == d se obtienen formas de hombro."""
    x = np.asarray(x, dtype=float)
    izq = np.where(b > a, (x - a) / max(b - a, 1e-12), np.where(x >= b, 1.0, 0.0))
    der = np.where(d > c, (d - x) / max(d - c, 1e-12), np.where(x <= c, 1.0, 0.0))
    mu = np.minimum(izq, der)
    return np.clip(np.where((x >= a) & (x <= d), mu, 0.0), 0.0, 1.0)


def triangulo(x, a, b, c):
    return trapecio(x, a, b, b, c)


# Universos de discurso (supuestos de simulación)
DISTANCIA_MAX, BATERIA_MAX, INCLINACION_MAX = 20.0, 100.0, 45.0
TEMPERATURA_MIN, TEMPERATURA_MAX = -80.0, 80.0
TEMPERATURA_TOLERANCIA = 60.0   # °C: por encima, §12 pide abortar o aislar (supuesto de simulación)

# Conjuntos lingüísticos por variable (RF-05: tres por variable de entrada)
CONJUNTOS = {
    "distancia": {
        "cerca": lambda x: trapecio(x, 0, 0, 3, 6),
        "media": lambda x: triangulo(x, 4, 10, 16),
        "lejos": lambda x: trapecio(x, 12, 17, 20, 20),
    },
    "bateria": {
        "critica": lambda x: trapecio(x, 0, 0, 15, 30),
        "baja": lambda x: triangulo(x, 20, 40, 60),
        "alta": lambda x: trapecio(x, 50, 70, 100, 100),
    },
    "inclinacion": {
        "plana": lambda x: trapecio(x, 0, 0, 5, 12),
        "media": lambda x: triangulo(x, 8, 18, 28),
        "fuerte": lambda x: trapecio(x, 24, 32, 45, 45),
    },
    # ev3-d40 A: temperatura exterior en °C como cuarta entrada (§2, §10.2)
    "temperatura": {
        "fria": lambda x: trapecio(x, -80, -80, -40, -20),
        "templada": lambda x: triangulo(x, -40, -5, 30),
        "caliente": lambda x: trapecio(x, 10, 35, 80, 80),
    },
}

# Conjuntos de salida (velocidad 0..1)
SALIDA = {
    "parar": lambda x: trapecio(x, 0.0, 0.0, 0.05, 0.15),
    "lenta": lambda x: triangulo(x, 0.1, 0.25, 0.4),
    "moderada": lambda x: triangulo(x, 0.35, 0.5, 0.65),
    "rapida": lambda x: trapecio(x, 0.6, 0.8, 1.0, 1.0),
}

# Reglas documentadas (RF-05: al menos ocho). Operador Y = mínimo.
REGLAS = [
    {"id": "R1", "si": [("distancia", "cerca")], "entonces": "parar",
     "motivo": "Obstáculo o barranco muy cerca: detenerse."},
    {"id": "R2", "si": [("bateria", "critica")], "entonces": "lenta",
     "motivo": "Batería crítica: avanzar lento para ahorrar energía."},
    {"id": "R3", "si": [("inclinacion", "fuerte"), ("distancia", "media")], "entonces": "lenta",
     "motivo": "Pendiente fuerte con riesgo a distancia media: cautela."},
    {"id": "R4", "si": [("bateria", "alta"), ("inclinacion", "plana"), ("distancia", "lejos")],
     "entonces": "rapida", "motivo": "Condiciones ideales: velocidad máxima."},
    {"id": "R5", "si": [("bateria", "baja"), ("distancia", "lejos")], "entonces": "moderada",
     "motivo": "Batería baja pero camino libre: velocidad media."},
    {"id": "R6", "si": [("inclinacion", "media"), ("distancia", "lejos")], "entonces": "moderada",
     "motivo": "Pendiente media con camino libre."},
    {"id": "R7", "si": [("bateria", "alta"), ("distancia", "media")], "entonces": "moderada",
     "motivo": "Energía suficiente con riesgo a distancia media."},
    {"id": "R8", "si": [("inclinacion", "fuerte")], "entonces": "lenta",
     "motivo": "Pendiente fuerte: velocidad lenta para evitar vuelco."},
    {"id": "R10", "si": [("temperatura", "caliente")], "entonces": "moderada",
     "motivo": "Temperatura alta: el sobrecalentamiento obliga a moderar la marcha."},
    {"id": "R11", "si": [("temperatura", "fria"), ("bateria", "baja")], "entonces": "lenta",
     "motivo": "Frío con batería baja: se reduce la marcha para cuidar la energía."},
    {"id": "R9", "si": [("distancia", "media"), ("inclinacion", "plana")], "entonces": "moderada",
     "motivo": "Terreno plano con riesgo a distancia media."},
]

# ARX-80: columnas planas de la bitácora con los grados de membresía de cada paso (M3, RF-08)
COLUMNAS_MEMBRESIA = [f"mu_{var}_{conj}" for var, conjuntos in CONJUNTOS.items() for conj in conjuntos]


def aplanar_membresias(membresias) -> dict:
    """{variable: {conjunto: grado}} -> {"mu_variable_conjunto": grado}.

    Sin datos (None o vacío) o con un grado no finito el valor es None (celda vacía en el CSV): no se inventa 0.0.
    """
    plano = {}
    for col in COLUMNAS_MEMBRESIA:
        _, var, conj = col.split("_", 2)
        g = (membresias or {}).get(var, {}).get(conj)
        plano[col] = round(float(g), 4) if g is not None and np.isfinite(g) else None
    return plano


# Valor de salida cuando ninguna regla se activa (sección 12: fallback documentado)
SALIDA_FALLBACK = 0.0


@dataclass
class ResultadoDifuso:
    velocidad: float
    membresias: dict          # {variable: {conjunto: grado}}
    reglas_activadas: list    # [(id, fuerza, motivo)]
    agregado: np.ndarray      # conjunto de salida agregado
    universo: np.ndarray      # eje x de la salida
    fallback: bool


class FuzzyController:
    def __init__(self, resolucion: int = 201):
        self.universo = np.linspace(0.0, 1.0, resolucion)

    @staticmethod
    def fusificar(distancia, bateria, inclinacion, temperatura=0.0) -> dict:
        entradas = {"distancia": distancia, "bateria": bateria, "inclinacion": inclinacion,
                    "temperatura": temperatura}
        return {
            var: {nombre: float(f(np.clip(entradas[var], _rango(var)[0], _rango(var)[1])))
                  for nombre, f in CONJUNTOS[var].items()}
            for var in CONJUNTOS
        }

    def inferir(self, distancia, bateria, inclinacion, temperatura=0.0) -> ResultadoDifuso:
        # RF-13: una entrada NaN no se propaga; se degrada a la salida fallback
        if any(np.isnan(v) for v in (distancia, bateria, inclinacion, temperatura)):
            mu = {var: {c: 0.0 for c in CONJUNTOS[var]} for var in CONJUNTOS}
            return ResultadoDifuso(velocidad=SALIDA_FALLBACK, membresias=mu, reglas_activadas=[],
                                   agregado=np.zeros_like(self.universo), universo=self.universo,
                                   fallback=True)
        mu = self.fusificar(distancia, bateria, inclinacion, temperatura)

        activaciones = {}          # conjunto de salida -> lista de fuerzas
        disparadas = []
        for regla in REGLAS:
            fuerza = min(mu[var][conj] for var, conj in regla["si"])
            if fuerza > 0:
                disparadas.append((regla["id"], float(fuerza), regla["motivo"]))
                activaciones.setdefault(regla["entonces"], []).append(fuerza)

        agregado = np.zeros_like(self.universo)
        for conjunto, fuerzas in activaciones.items():
            recortado = np.minimum(max(fuerzas), SALIDA[conjunto](self.universo))
            agregado = np.maximum(agregado, recortado)

        if agregado.sum() == 0:
            velocidad, fallback = SALIDA_FALLBACK, True
        else:
            velocidad = float(np.sum(self.universo * agregado) / np.sum(agregado))
            fallback = False

        return ResultadoDifuso(velocidad=velocidad, membresias=mu, reglas_activadas=disparadas,
                               agregado=agregado, universo=self.universo, fallback=fallback)


def _rango(var: str):
    return {
        "distancia": (0.0, DISTANCIA_MAX),
        "bateria": (0.0, BATERIA_MAX),
        "inclinacion": (0.0, INCLINACION_MAX),
        "temperatura": (TEMPERATURA_MIN, TEMPERATURA_MAX),
    }[var]
