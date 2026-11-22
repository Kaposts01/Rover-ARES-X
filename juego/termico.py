"""ARX-83a: temperatura interna del rover (T_int) y aborto térmico. Modelo de docs/PLAN_PLANETAS.md (ev3-d42 B).

Todos los valores son supuestos de simulación, no cotas de diseño. El difuso lee T_int, no la temperatura ambiente:
el calor se acumula paso a paso y obliga a buscar sombra; no aborta de golpe.

Solo actúa en Partida con garantia=True. Además, el aborto y la inyección de T_int al difuso están detrás de la bandera
ABORTO_TERMICO_ACTIVO, apagada por defecto: el aborto puede terminar partidas en Mercurio de día y en Venus, y esa
decisión de juego la toma el Maestro. Para activarlo, cambiar la constante a True (o fijarla en las pruebas).
"""
from simulador import BARRANCO, OBSTACULO

ABORTO_TERMICO_ACTIVO = False       # ev3-d88 B: repliegue a A (solo aviso): con el aborto no queda ninguna partida ganable (docs/planes/M13_termico_B.md)

K_CALOR = 0.01                      # fracción del salto térmico que sube por paso (ev3-d88 B: τ = 100 pasos ≈ 17 min con 10 s por paso)
K_ENFRIAMIENTO = 0.05               # fracción del exceso que baja por paso, solo a la sombra
REDUCCION_BLINDAJE = 40.0           # °C que resta el blindaje a la temperatura ambiente
GANANCIA_EXPOSICION = 15.0          # °C que suma el sol directo o el suelo caliente
T_SOMBRA = 40.0                     # °C: techo de la temperatura efectiva a la sombra o en el refugio (PLAN_PLANETAS: «unos 40 °C»)
T_INT_INICIAL = 20.0                # °C al empezar la partida
TOLERANCIA = 60.0                   # °C: por encima, el hardware está fuera de rango (igual que difuso.TEMPERATURA_TOLERANCIA)
TOLERANCIA_POR_PLANETA = {"Mercurio": 60.0, "Venus": 60.0}   # ev3-d88 B: mismo equipo en ambos planetas; tabla para otro equipo
PASOS_MAXIMOS_SOBRE_TOLERANCIA = 5  # el aborto llega al paso siguiente a cinco seguidos sobre la tolerancia

# Temperatura ambiente por planeta rover, °C (Mercurio: de día; supuesto de simulación)
# R23: los gigantes (modo sonda) también tienen modelo térmico (temperatura en las nubes, PLAN_PLANETAS). Antes no estaban en
# la tabla, el modelo quedaba inactivo y la temperatura interna se quedaba fija en 20 °C toda la partida.
T_AMB_POR_PLANETA = {"Mercurio": 430.0, "Venus": 464.0, "Tierra": 15.0, "Marte": -60.0,
                     "Júpiter": -110.0, "Saturno": -140.0, "Urano": -195.0, "Neptuno": -200.0}
# R23: planeta frío (ambiente por debajo de T_INT_INICIAL). El modelo caliente solo sube; en un planeta frío el rover pierde
# calor hacia un equilibrio: T_eq = T_INT_INICIAL + AISLAMIENTO_FRIO · (T_amb − T_INT_INICIAL) (el aislamiento y el calor propio
# retienen el 75 % del salto), y T_int lo alcanza con rapidez K_FRIO por paso. Al sol el equilibrio sube GANANCIA_SOL_FRIO.
AISLAMIENTO_FRIO = 0.25
K_FRIO = 0.02
GANANCIA_SOL_FRIO = 5.0
TOLERANCIA_FRIA = -40.0             # °C: por debajo, el hardware está fuera de rango por frío (solo informativo, sin aborto)
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
        self.planeta = planeta
        self.t_amb = T_AMB_POR_PLANETA.get(planeta)     # None: planeta sin modelo térmico (p. ej. modo sonda) -> inactivo
        self.t_int = float(t_int)
        self.pasos_sobre_tolerancia = 0

    @property
    def activo(self) -> bool:
        return self.t_amb is not None

    def paso(self, sombra: bool) -> float:
        """Un paso: actualiza T_int y el contador de pasos seguidos sobre la tolerancia; devuelve T_int.
        Sin modelo para el planeta (inactivo): no cambia nada."""
        if not self.activo:
            return self.t_int
        if self.t_amb < T_INT_INICIAL:                  # R23: planeta frío
            equilibrio = self.t_equilibrio_frio + (0.0 if sombra else GANANCIA_SOL_FRIO)
            self.t_int += K_FRIO * (equilibrio - self.t_int)
            self.pasos_sobre_tolerancia = self.pasos_sobre_tolerancia + 1 if self.sobre_tolerancia else 0
            return self.t_int
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
    def t_equilibrio_frio(self) -> float:
        """T_int a la que tiende el rover en un planeta frío (a la sombra)."""
        return T_INT_INICIAL + AISLAMIENTO_FRIO * (self.t_amb - T_INT_INICIAL)

    @property
    def bajo_tolerancia_fria(self) -> bool:
        return self.t_int < TOLERANCIA_FRIA

    @property
    def tolerancia(self) -> float:
        return TOLERANCIA_POR_PLANETA.get(self.planeta, TOLERANCIA)

    @property
    def sobre_tolerancia(self) -> bool:
        return self.t_int > self.tolerancia

    @property
    def debe_abortar(self) -> bool:
        return self.pasos_sobre_tolerancia > PASOS_MAXIMOS_SOBRE_TOLERANCIA
