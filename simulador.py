"""ARES-X · Fase 1: simulador físico (sin IA).

Todos los valores numéricos son supuestos de simulación, no especificaciones de misión.
Decisión provisional ev3-d02: el mundo real (verdad) queda separado de lo que el rover observa.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Tipos de celda del mundo real
LIBRE, OBSTACULO, BARRANCO = 0, 1, 2

# ARX-93 (ev3-d78 A): pista aparte, apagada por defecto. Encendida, las celdas BARRANCO quedan
# DESNIVEL_BARRANCO_M metros bajo la elevación suave (firma física que la RNA puede aprender).
# Apagada, el mundo es idéntico al de siempre. Solo se enciende en pruebas y mediciones.
FIRMA_BARRANCO_ACTIVA = False
DESNIVEL_BARRANCO_M = 3.0

# Movimientos cardinales (fila, columna)
# Ocho direcciones (ev3-d29 B). Una diagonal se permite si la celda de destino es transitable.
MOVIMIENTOS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1),
               "NE": (-1, 1), "NO": (-1, -1), "SE": (1, 1), "SO": (1, -1)}



@dataclass(frozen=True)
class PlanetProfile:
    """Perfil de cuerpo celeste. Solo los rodantes admiten rover de ruedas."""

    nombre: str
    modo: str  # "rover" o "sonda"
    descripcion: str

    def admite_rover(self) -> bool:
        return self.modo == "rover"


PERFILES = {
    "Marte": PlanetProfile("Marte", "rover", "Rover principal: barrancos, polvo, hielo, noche (supuesto de simulación)."),
    "Mercurio": PlanetProfile("Mercurio", "rover", "Rover hipotético: radiación, sobrecalentamiento, cráteres (supuesto)."),
    "Venus": PlanetProfile("Venus", "rover", "Rover especial hipotético: temperatura, presión y corrosión (supuesto)."),
    "Tierra": PlanetProfile("Tierra", "rover", "Banco de calibración: lluvia, sismos, deslizamientos (supuesto)."),
    "Júpiter": PlanetProfile("Júpiter", "sonda", "Gigante gaseoso: sonda atmosférica, sin ruedas."),
    "Saturno": PlanetProfile("Saturno", "sonda", "Gigante gaseoso: sonda atmosférica, sin ruedas."),
    "Urano": PlanetProfile("Urano", "sonda", "Gigante helado: sonda atmosférica, sin ruedas."),
    "Neptuno": PlanetProfile("Neptuno", "sonda", "Gigante helado: sonda atmosférica, sin ruedas."),
}


def validar_compatibilidad(planeta: str, modo: str) -> None:
    """RF-01 / CA-07: bloquea un rover de ruedas en un gigante."""
    if planeta not in PERFILES:
        raise ValueError(f"Planeta desconocido: {planeta!r}")
    perfil = PERFILES[planeta]
    if modo == "rover" and not perfil.admite_rover():
        raise ValueError(
            f"{planeta} no tiene superficie sólida para un rover de ruedas. "
            "Use el modo sonda atmosférica."
        )
    if modo not in ("rover", "sonda"):
        raise ValueError(f"Modo desconocido: {modo!r}")


@dataclass
class World:
    """Mundo real: la verdad del simulador. El rover no lo consulta directamente."""

    tipo: np.ndarray            # LIBRE / OBSTACULO / BARRANCO por celda
    elevacion: np.ndarray       # metros simulados
    sitios: dict                # {(fila, col): valor científico}
    refugio: tuple
    inicio: tuple
    semilla: int

    @property
    def forma(self):
        return self.tipo.shape

    def dentro(self, pos) -> bool:
        f, c = pos
        return 0 <= f < self.tipo.shape[0] and 0 <= c < self.tipo.shape[1]

    def transitable(self, pos) -> bool:
        return self.dentro(pos) and self.tipo[pos] == LIBRE

    def marcar_barranco(self, pos) -> None:
        """Evento manual o de simulación: convierte una celda en precipicio."""
        if not self.dentro(pos):
            raise ValueError(f"Celda fuera del mapa: {pos}")
        if pos in (self.inicio, self.refugio):
            raise ValueError("No se puede poner un barranco sobre inicio o refugio.")
        if FIRMA_BARRANCO_ACTIVA and self.tipo[pos] != BARRANCO:
            self.elevacion[pos] -= DESNIVEL_BARRANCO_M
        self.tipo[pos] = BARRANCO


def generar_mundo(semilla: int, filas: int = 20, columnas: int = 30,
                  n_obstaculos: int = 40, n_barrancos: int = 6, n_sitios: int = 4) -> World:
    """Genera un mapa reproducible con la semilla dada (RF-02, RF-12)."""
    rng = np.random.default_rng(semilla)
    tipo = np.zeros((filas, columnas), dtype=int)

    inicio = (filas - 1, 0)
    refugio = (0, columnas - 1)

    def celda_libre_aleatoria():
        return (int(rng.integers(0, filas)), int(rng.integers(0, columnas)))

    for _ in range(n_obstaculos):
        p = celda_libre_aleatoria()
        if p not in (inicio, refugio):
            tipo[p] = OBSTACULO
    for _ in range(n_barrancos):
        p = celda_libre_aleatoria()
        if p not in (inicio, refugio):
            tipo[p] = BARRANCO

    # Elevación suavizada: base de altimetría (supuesto de simulación)
    elevacion = np.cumsum(rng.normal(0, 0.2, size=(filas, columnas)), axis=1)
    if FIRMA_BARRANCO_ACTIVA:
        elevacion[tipo == BARRANCO] -= DESNIVEL_BARRANCO_M

    sitios = {}
    intentos = 0
    while len(sitios) < n_sitios and intentos < 1000:
        intentos += 1
        p = celda_libre_aleatoria()
        if tipo[p] == LIBRE and p not in (inicio, refugio) and p not in sitios:
            sitios[p] = int(rng.integers(1, 10))

    return World(tipo=tipo, elevacion=elevacion, sitios=sitios,
                 refugio=refugio, inicio=inicio, semilla=semilla)


@dataclass
class SensorSuite:
    """Lecturas ruidosas del entorno inmediato. No ve el mundo completo."""

    rng: np.random.Generator
    ruido: float = 0.1          # desviación relativa del ruido gaussiano
    prob_fallo: float = 0.0     # probabilidad de lectura NaN por sensor

    def _ruidoso(self, valor: float, escala: float) -> float:
        if self.rng.random() < self.prob_fallo:
            return float("nan")
        return float(valor + self.rng.normal(0, self.ruido * escala))

    def leer(self, mundo: World, pos, rumbo: str = "N") -> dict:
        """Distancia al obstáculo o barranco más cercano en la dirección de avance."""
        df, dc = MOVIMIENTOS[rumbo]
        distancia = 20  # alcance máximo del sensor de proximidad (m)
        for paso in range(1, 21):
            p = (pos[0] + df * paso, pos[1] + dc * paso)
            if not mundo.dentro(p):
                break
            if mundo.tipo[p] != LIBRE:
                distancia = paso
                break
        altura_actual = mundo.elevacion[pos]
        celdas_barranco = self._barrancos_vecinos(mundo, pos)
        return {
            "proximidad_frontal_m": self._ruidoso(distancia, 1.0),
            "borde_barranco": len(celdas_barranco) > 0,
            "celdas_barranco": celdas_barranco,
            "altimetria_m": self._ruidoso(altura_actual, 0.5),
        }

    @staticmethod
    def _barrancos_vecinos(mundo: World, pos) -> list:
        """LIDAR de borde: celdas de precipicio en los cuatro vecinos."""
        vecinos = []
        for df, dc in MOVIMIENTOS.values():
            p = (pos[0] + df, pos[1] + dc)
            if mundo.dentro(p) and mundo.tipo[p] == BARRANCO:
                vecinos.append(p)
        return vecinos


@dataclass
class Rover:
    """Estado físico del rover."""

    posicion: tuple
    bateria: float = 100.0      # porcentaje
    rumbo: str = "N"
    distancia_recorrida: int = 0
    en_modo_seguro: bool = False
    historial: list = field(default_factory=list)

    def consumir(self, costo: float) -> None:
        # RF-13 / bordes: la batería nunca queda negativa
        self.bateria = max(0.0, self.bateria - costo)


class MissionLogger:
    """Bitácora por paso (RF-08). Exportable a CSV en la fase de entregables."""

    def __init__(self):
        self.filas = []
        self.completar = None     # ARX-80: función opcional que aporta columnas que la fila no trae

    def registrar(self, **datos) -> None:
        if self.completar is not None:
            datos = {**datos, **{k: v for k, v in self.completar(datos).items() if k not in datos}}
        self.filas.append(datos)

    def a_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.filas)


def paso_fisico(mundo: World, rover: Rover, movimiento: str, costo: float = 1.0) -> bool:
    """Intenta mover el rover una celda. Devuelve True si se movió.

    Reglas: nunca entra en obstáculo ni barranco (CA-02, sección 12); sin batería no se mueve.
    """
    if movimiento not in MOVIMIENTOS:
        raise ValueError(f"Movimiento inválido: {movimiento!r}")
    if rover.en_modo_seguro or rover.bateria <= 0:
        return False
    df, dc = MOVIMIENTOS[movimiento]
    destino = (rover.posicion[0] + df, rover.posicion[1] + dc)
    rover.rumbo = movimiento
    if not mundo.transitable(destino):
        return False
    rover.consumir(costo)
    rover.posicion = destino
    rover.distancia_recorrida += 1
    return True
