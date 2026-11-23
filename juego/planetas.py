"""R23: mecánicas propias de cada planeta (gravedad, viento, hielo) para la partida jugable.

Antes los planetas solo cambiaban de color y de temperatura. Aquí cada uno tiene un perfil con parámetros que el motor
usa de verdad en cada paso:

- **Gravedad:** coste de energía extra por moverse (más pesado = más batería) y por subir pendientes
  (proporcional a la gravedad y al desnivel subido).
- **Viento:** soplo con rumbo propio y ráfagas. Avanzar contra el viento cuesta energía (más cuanto más rápido se va) y el
  viento de costado puede desviar al rover una celda.
- **Hielo (adherencia):** parches de hielo fijos por partida. Pisar uno a velocidad de avance resbala: el rover se desliza
  una celda de más en su rumbo (o se queda donde está si no hay hueco) y gasta batería. Despacio no resbala.
- **Terreno:** `factor_pendiente` (regolito suelto o roca) encarece las subidas; `arrastre` es el coste por la atmósfera.

Todos los valores son **supuestos de simulación**, no datos de misión. La intensidad total de las mecánicas la escala el
nivel de dificultad (`juego/dificultad.py`).

Solo actúan en la partida jugable (`garantia=True`); la evaluación congelada y los escenarios de comparación existentes no
las usan (`MecanicasPlaneta.activa` es falso).

Contrato público estable (lo consume, por ejemplo, el AG que optimiza el difuso por planeta):
    juego.planetas.perfil(nombre)            -> PerfilPlaneta (dataclass inmutable)
    juego.planetas.parametros(nombre)        -> dict con los parámetros del planeta (JSON-serializable)
    Partida.parametros_planeta()             -> los mismos parámetros del planeta de la partida, más `intensidad` del nivel
    Partida.mecanicas.estado()               -> viento actual, ráfaga y contadores de la partida
"""
from dataclasses import asdict, dataclass

import numpy as np

from simulador import LIBRE, MOVIMIENTOS, _relieve_suave

PLANETA_BASE = "Marte"             # el coste base de 1 % por paso del motor está calibrado con la gravedad de Marte
G_REF = 0.38                       # gravedad (g) de referencia: sin sobrecoste por gravedad plana
COEF_GRAVEDAD_PLANA = 0.35         # % de batería extra por paso y por cada g sobre G_REF
COEF_SUBIDA = 1.0                  # % de batería extra por metro subido y por g, antes de factor_pendiente
EXTRA_MAXIMO_PASO = 2.0            # % de batería: tope de sobrecoste por paso (los gigantes no vacían la batería de golpe)
COEF_VIENTO = 1.2                  # % extra por paso con viento de cara de intensidad 1 y velocidad 0,5
AHORRO_VIENTO_COLA = 0.25          # fracción del coste de cara que se ahorra con viento de cola
RAFAGA_MULT = 2.0                  # una ráfaga multiplica la intensidad del viento
RAFAGA_PASOS = (3, 6)              # duración de una ráfaga (pasos, mínimo y máximo)
P_DESVIO_VIENTO = 0.12             # probabilidad de desvío por intensidad 1 de viento de costado
COSTO_DESLIZ = 1.0                 # % de batería que cuesta un resbalón sobre hielo
P_RESBALON_HIELO = 0.9             # prob. = P_RESBALON_HIELO * velocidad * intensidad del nivel * fragilidad_hielo
VELOCIDAD_SIN_RESBALON = 0.3       # por debajo, el avance es lento y no resbala (igual que la pendiente, ARX-28c)
VELOCIDAD_MANUAL = 0.5             # velocidad que se supone al conducir a mano o con una técnica que no fija velocidad
COSTO_TIEMPO_LENTO = 0.15          # % extra por paso a velocidad 0,25 (a 0,5 o más no hay): el consumo de base (calefactor,
                                   # instrumentos) corre más tiempo por celda cuando se avanza despacio. Sin él, ir lo más lento
                                   # posible sería siempre lo mejor (la velocidad no cuesta tiempo de partida) y el difuso no tendría
                                   # nada que decidir; con él, el mejor tope de velocidad depende del planeta (viento, hielo, pendiente)
HIELO_EQUIV_GRADOS = 18.0          # el rover detecta el hielo de la celda siguiente: el difuso lo ve como esta pendiente extra

# Direcciones del viento (hacia dónde sopla)
_UNIDAD = {r: np.array(v, dtype=float) / np.linalg.norm(v) for r, v in MOVIMIENTOS.items()}


@dataclass(frozen=True)
class PerfilPlaneta:
    nombre: str
    gravedad_g: float            # supuesto del PLAN_PLANETAS
    viento: float                # intensidad base 0..1 (0 = sin viento)
    rumbo_viento: str            # hacia dónde sopla (N, S, E, O, NE, NO, SE, SO)
    rafaga_prob: float           # probabilidad por paso de que empiece una ráfaga
    hielo_fraccion: float        # fracción del mapa cubierta de parches de hielo
    fragilidad_hielo: float      # 1,0 normal; mayor = hielo más resbaladizo
    factor_pendiente: float      # multiplica el coste de subir (regolito suelto, roca)
    arrastre: float              # % extra por paso (atmósfera densa)
    prob_tormenta_x: float       # multiplica la probabilidad de iniciar tormenta o noche (polvo)
    resumen: str                 # texto corto para la interfaz

    def como_dict(self) -> dict:
        return asdict(self)


PERFILES = {
    "Marte": PerfilPlaneta("Marte", 0.38, 0.40, "E", 0.04, 0.05, 1.0, 1.0, 0.0, 2.0,
                           "baja gravedad, viento moderado con polvo y tormentas frecuentes, algo de hielo polar"),
    "Mercurio": PerfilPlaneta("Mercurio", 0.38, 0.0, "E", 0.0, 0.0, 1.0, 1.6, 0.0, 1.0,
                              "baja gravedad, sin viento ni hielo, regolito suelto: las subidas cuestan más"),
    "Venus": PerfilPlaneta("Venus", 0.91, 0.20, "NO", 0.02, 0.0, 1.0, 1.0, 0.25, 1.0,
                           "atmósfera densa que frena (arrastre constante), viento lento, calor extremo"),
    "Tierra": PerfilPlaneta("Tierra", 1.00, 0.30, "O", 0.05, 0.08, 0.8, 1.0, 0.0, 1.0,
                            "gravedad plena, ráfagas ocasionales y barro helado en parches"),
    "Júpiter": PerfilPlaneta("Júpiter", 2.53, 0.90, "O", 0.08, 0.0, 1.0, 1.0, 0.0, 1.0,
                             "gravedad enorme y vientos muy fuertes con ráfagas"),
    "Saturno": PerfilPlaneta("Saturno", 1.07, 0.80, "NO", 0.07, 0.0, 1.0, 1.0, 0.0, 1.0,
                             "vientos zonales fuertes"),
    "Urano": PerfilPlaneta("Urano", 0.89, 0.55, "SO", 0.05, 0.30, 1.2, 1.0, 0.0, 1.0,
                           "viento medio y mucho hielo"),
    "Neptuno": PerfilPlaneta("Neptuno", 1.14, 0.85, "SO", 0.08, 0.30, 1.3, 1.0, 0.0, 1.0,
                             "viento muy fuerte con ráfagas y hielo muy resbaladizo"),
}


def perfil(nombre: str) -> PerfilPlaneta:
    """Perfil del planeta. Un nombre desconocido cae al de Marte (el escenario principal)."""
    return PERFILES.get(nombre, PERFILES[PLANETA_BASE])


# Escala cualitativa del viento (la misma para el perfil y el estado vivo; el motor la rotula, la interfaz solo la muestra).
# Umbrales sobre la intensidad NOMINAL (la del perfil, sin la escala del nivel ni la ráfaga): coinciden con las frases de
# `PERFILES` (Venus 0,20 «lento»; Marte 0,40 «moderado»; Urano 0,55 «medio»; Saturno 0,80 «fuerte»; Neptuno 0,85 «muy fuerte»).
ESCALA_VIENTO = ((0.05, "en calma"), (0.25, "suave"), (0.50, "moderado"), (0.75, "fuerte"))


def rotulo_viento(nominal: float) -> str:
    """Rótulo cualitativo del viento para una intensidad nominal (0..1)."""
    for tope, nombre in ESCALA_VIENTO:
        if nominal < tope:
            return nombre
    return "muy fuerte"


def parametros(nombre: str) -> dict:
    """Parámetros del planeta como diccionario (JSON-serializable)."""
    p = perfil(nombre)
    return {**p.como_dict(), "viento_rotulo": rotulo_viento(p.viento)}


def sobrecosto_medio(nombre: str, intensidad: float = 1.0) -> float:
    """Sobrecoste esperado de un paso (% de batería) por las mecánicas del planeta, sin contar resbalones ni ráfagas.
    Sirve para estimar cuánta batería de más pide el planeta (la garantía y la caza lo usan)."""
    p = perfil(nombre)
    plano = max(0.0, COEF_GRAVEDAD_PLANA * (p.gravedad_g - G_REF)) + p.arrastre
    subida = 0.25 * COEF_SUBIDA * p.gravedad_g * p.factor_pendiente        # desnivel medio subido por paso, ~0,25 m
    viento = 0.5 * COEF_VIENTO * p.viento * 0.35 * (0.5 + 0.5)             # de cara en ~35 % de los pasos (media)
    return float(min(EXTRA_MAXIMO_PASO, (plano + subida + viento) * intensidad))


class MecanicasPlaneta:
    """Estado y efectos de las mecánicas de un planeta en una partida."""

    def __init__(self, planeta: str, mundo, semilla: int, intensidad: float = 1.0, activa: bool = True):
        self.perfil = perfil(planeta)
        self.intensidad = float(intensidad)
        self.activa = bool(activa)
        self.mundo = mundo
        self.rafaga_restante = 0
        self.resbalones_hielo = 0
        self.desvios_viento = 0
        self.energia_extra = 0.0              # % de batería gastado por las mecánicas del planeta
        self._rng_viento = np.random.default_rng([int(semilla), 1318])
        self._rng_hielo = np.random.default_rng([int(semilla), 1319])
        self._rng_polvo = np.random.default_rng([int(semilla), 1321])      # tormentas extra de polvo (no toca el generador de ambiente)
        self.hielo = self._generar_hielo(int(semilla)) if self.activa else np.zeros(mundo.tipo.shape, dtype=bool)

    # ---------- hielo ----------
    def _generar_hielo(self, semilla: int) -> np.ndarray:
        """Parches de hielo: campo suave por encima del cuantil que da la fracción del perfil, sobre celdas libres."""
        forma = self.mundo.tipo.shape
        fraccion = self.perfil.hielo_fraccion
        if fraccion <= 0:
            return np.zeros(forma, dtype=bool)
        campo = _relieve_suave(np.random.default_rng([semilla, 1320]), forma, sigma_m=1.0, suavidad=2.0)
        libre = np.asarray(self.mundo.tipo == LIBRE)
        umbral = np.quantile(campo[libre], 1.0 - fraccion)
        hielo = (campo >= umbral) & libre
        for c in (self.mundo.inicio, self.mundo.refugio):
            hielo[tuple(c)] = False
        return hielo

    def hay_hielo(self, celda) -> bool:
        celda = (int(celda[0]), int(celda[1]))
        return bool(self.activa and self.mundo.dentro(celda) and self.hielo[celda])

    def celdas_hielo(self) -> list:
        return [[int(f), int(c)] for f, c in zip(*np.nonzero(self.hielo))]

    # ---------- viento ----------
    @property
    def viento_actual(self) -> float:
        """Intensidad del viento ahora (0..): la base del planeta, por la ráfaga si la hay, por la intensidad del nivel."""
        if not self.activa:
            return 0.0
        return self.perfil.viento * self.intensidad * (RAFAGA_MULT if self.rafaga_restante > 0 else 1.0)

    def avanzar_clima(self) -> None:
        """Un paso de clima: descuenta la ráfaga en curso o tira el dado para empezar una."""
        if not self.activa:
            return
        if self.rafaga_restante > 0:
            self.rafaga_restante -= 1
        elif self.perfil.viento > 0 and self._rng_viento.random() < self.perfil.rafaga_prob * self.intensidad:
            self.rafaga_restante = int(self._rng_viento.integers(RAFAGA_PASOS[0], RAFAGA_PASOS[1] + 1))

    def tormenta_de_polvo(self) -> bool:
        """¿Empieza una tormenta extra de polvo este paso? El perfil multiplica la probabilidad base de tormenta o noche
        (`prob_tormenta_x`); la parte que se suma a la base sale de un generador propio, así que la secuencia de meteoritos
        y de ambiente de la partida no cambia con el planeta."""
        if not self.activa or self.perfil.prob_tormenta_x <= 1.0:
            return False
        from juego.partida import PROB_AMBIENTE
        return bool(self._rng_polvo.random() < PROB_AMBIENTE * (self.perfil.prob_tormenta_x - 1.0))

    # ---------- coste ----------
    def costo_extra(self, origen, destino, velocidad: float) -> dict:
        """Sobrecoste (% de batería) de un paso de `origen` a `destino` por gravedad, pendiente, atmósfera y viento.

        Devuelve {"gravedad", "pendiente", "arrastre", "viento", "total"}; el total no pasa de EXTRA_MAXIMO_PASO.
        """
        if not self.activa:
            return {"gravedad": 0.0, "pendiente": 0.0, "arrastre": 0.0, "viento": 0.0, "lento": 0.0, "total": 0.0}
        p, k = self.perfil, self.intensidad
        origen, destino = (int(origen[0]), int(origen[1])), (int(destino[0]), int(destino[1]))
        gravedad = max(0.0, COEF_GRAVEDAD_PLANA * (p.gravedad_g - G_REF)) * k
        subida = max(0.0, float(self.mundo.elevacion[destino] - self.mundo.elevacion[origen]))
        pendiente = COEF_SUBIDA * p.gravedad_g * p.factor_pendiente * subida * k
        arrastre = p.arrastre * k
        viento = 0.0
        w = self.viento_actual
        if w > 0:
            mov = np.array([destino[0] - origen[0], destino[1] - origen[1]], dtype=float)
            norma = np.linalg.norm(mov)
            if norma > 0:
                coseno = float(np.dot(mov / norma, _UNIDAD[p.rumbo_viento]))      # >0 viento de cola, <0 de cara
                escala = COEF_VIENTO * w * (0.5 + float(velocidad))
                viento = -AHORRO_VIENTO_COLA * escala * coseno if coseno > 0 else escala * (-coseno)
                viento = float(max(-AHORRO_VIENTO_COLA * escala, viento))
        lento = COSTO_TIEMPO_LENTO * max(0.0, 0.5 / max(float(velocidad), 0.2) - 1.0) * k
        total = float(min(EXTRA_MAXIMO_PASO, max(0.0, gravedad + pendiente + arrastre + viento + lento)))
        return {"gravedad": gravedad, "pendiente": pendiente, "arrastre": arrastre, "viento": viento, "lento": lento,
                "total": total}

    # ---------- perturbaciones ----------
    def perturbar(self, origen, destino, velocidad: float, transitable) -> tuple:
        """Efecto del viento de costado y del hielo tras un avance de `origen` a `destino`.

        `transitable(celda)` dice si el rover puede ocupar una celda. Devuelve (celda_final, motivo) con motivo
        "D-VIENTO" (desvío lateral), "D-HIELO" (resbalón hacia delante) o None. Siempre consume los mismos números
        aleatorios, así que el azar de una partida no depende de qué rama se tomó.
        """
        u_viento, u_hielo = float(self._rng_viento.random()), float(self._rng_hielo.random())
        lado = 1 if float(self._rng_viento.random()) < 0.5 else -1
        if not self.activa:
            return tuple(destino), None
        origen, destino = (int(origen[0]), int(origen[1])), (int(destino[0]), int(destino[1]))
        paso = (destino[0] - origen[0], destino[1] - origen[1])
        if paso == (0, 0):
            return destino, None
        p = self.perfil
        # hielo: la celda pisada es de hielo y se avanza a velocidad de avance
        if self.hay_hielo(destino) and velocidad >= VELOCIDAD_SIN_RESBALON:
            prob = min(0.95, P_RESBALON_HIELO * velocidad * self.intensidad * p.fragilidad_hielo)
            if u_hielo < prob:
                delante = (destino[0] + paso[0], destino[1] + paso[1])
                self.resbalones_hielo += 1
                return (delante if transitable(delante) else destino), "D-HIELO"
        # viento de costado: desvía una celda perpendicular al avance
        w = self.viento_actual
        if w > 0:
            mov = np.array(paso, dtype=float)
            mov /= np.linalg.norm(mov)
            lateral = abs(float(mov[0] * _UNIDAD[p.rumbo_viento][1] - mov[1] * _UNIDAD[p.rumbo_viento][0]))   # |seno|
            if u_viento < min(0.9, P_DESVIO_VIENTO * w * lateral):
                perp = (lado * paso[1], -lado * paso[0])
                perp = (int(np.sign(perp[0])), int(np.sign(perp[1])))
                for cand in (perp, (-perp[0], -perp[1])):
                    celda = (destino[0] + cand[0], destino[1] + cand[1])
                    if cand != (0, 0) and transitable(celda):
                        self.desvios_viento += 1
                        return celda, "D-VIENTO"
        return destino, None

    # ---------- lectura ----------
    def estado(self) -> dict:
        p = self.perfil
        return {"activa": self.activa, "intensidad": round(self.intensidad, 3),
                "viento": round(self.viento_actual, 3), "rumbo_viento": p.rumbo_viento,
                # mismo rótulo que el perfil: sobre la intensidad nominal, con la ráfaga (que la duplica) y sin la escala del nivel
                "viento_rotulo": rotulo_viento(p.viento * (RAFAGA_MULT if self.rafaga_restante > 0 else 1.0) if self.activa else 0.0),
                "rafaga": self.rafaga_restante > 0, "rafaga_restante": int(self.rafaga_restante),
                "celdas_hielo": int(self.hielo.sum()),
                "resbalones_hielo": int(self.resbalones_hielo), "desvios_viento": int(self.desvios_viento),
                "energia_extra": round(float(self.energia_extra), 2)}
