"""ARX-83a: temperatura interna del rover (T_int) y aborto térmico. Modelo de docs/PLAN_PLANETAS.md (ev3-d42 B).

Todos los valores son supuestos de simulación, no cotas de diseño. El difuso lee T_int, no la temperatura ambiente:
el calor se acumula paso a paso y obliga a buscar sombra; no aborta de golpe.

Solo actúa en Partida con garantia=True. Además, el aborto y la inyección de T_int al difuso están detrás de la bandera
ABORTO_TERMICO_ACTIVO, apagada por defecto: el aborto puede terminar partidas en Mercurio de día y en Venus, y esa
decisión de juego la toma el Maestro. Para activarlo, cambiar la constante a True (o fijarla en las pruebas).
"""
from simulador import BARRANCO, OBSTACULO

ABORTO_TERMICO_ACTIVO = False       # apagada: sin ella T_int se calcula pero no cambia ninguna partida

K_CALOR = 0.08                      # fracción del salto térmico que sube por paso
K_ENFRIAMIENTO = 0.05               # fracción del exceso que baja por paso, solo a la sombra
REDUCCION_BLINDAJE = 40.0           # °C que resta el blindaje a la temperatura ambiente
GANANCIA_EXPOSICION = 15.0          # °C que suma el sol directo o el suelo caliente
T_SOMBRA = 40.0                     # °C: techo de la temperatura efectiva a la sombra o en el refugio (PLAN_PLANETAS: «unos 40 °C»)
T_INT_INICIAL = 20.0                # °C al empezar la partida
TOLERANCIA = 60.0                   # °C: por encima, el hardware está fuera de rango (igual que difuso.TEMPERATURA_TOLERANCIA)
PASOS_MAXIMOS_SOBRE_TOLERANCIA = 5  # el aborto llega al paso siguiente a cinco seguidos sobre la tolerancia

# Temperatura ambiente por planeta rover, °C (Mercurio: de día; supuesto de simulación)
T_AMB_POR_PLANETA = {"Mercurio": 430.0, "Venus": 464.0, "Tierra": 15.0, "Marte": -60.0}
PLANETA_POR_DEFECTO = "Marte"


def es_sombra(mundo, pos) -> bool:
    """Sombra: el refugio, o una celda adyacente (8 vecinas) a un barranco o un obstáculo (cráter o pared de roca)."""
    pos = (int(pos[0]), int(pos[1]))
    if pos == tuple(mundo.refugio):
        return True
    for df in (-1, 0, 1):
        for dc in (-1, 0, 1):
            vecina = (pos[0] + df, pos[1] + dc)
            if (df or dc) and mundo.dentro(vecina) and mundo.tipo[vecina] in (BARRANCO, OBSTACULO):
                return True
    return False


class Termico:
    def __init__(self, planeta: str = PLANETA_POR_DEFECTO, t_int: float = T_INT_INICIAL):
        if planeta not in T_AMB_POR_PLANETA:
            raise ValueError(f"planeta sin modelo térmico: {planeta!r} (válidos: {sorted(T_AMB_POR_PLANETA)})")
        self.planeta = planeta
        self.t_amb = T_AMB_POR_PLANETA[planeta]
        self.t_int = float(t_int)
        self.pasos_sobre_tolerancia = 0

    def paso(self, sombra: bool) -> float:
        """Un paso: actualiza T_int y el contador de pasos seguidos sobre la tolerancia; devuelve T_int."""
        if sombra:
            t_efectiva = min(self.t_amb, T_SOMBRA)
            self.t_int += (K_CALOR * max(0.0, t_efectiva - self.t_int)
                           - K_ENFRIAMIENTO * max(0.0, self.t_int - t_efectiva))
        else:
            t_efectiva = self.t_amb + GANANCIA_EXPOSICION - REDUCCION_BLINDAJE
            self.t_int += K_CALOR * max(0.0, t_efectiva - self.t_int)
        self.pasos_sobre_tolerancia = self.pasos_sobre_tolerancia + 1 if self.sobre_tolerancia else 0
        return self.t_int

    @property
    def sobre_tolerancia(self) -> bool:
        return self.t_int > TOLERANCIA

    @property
    def debe_abortar(self) -> bool:
        return self.pasos_sobre_tolerancia > PASOS_MAXIMOS_SOBRE_TOLERANCIA
