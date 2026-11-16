"""Combate del rover (ARX-06): disparo con munición y cooldown, y drones con máquina de estados.

Capa de juego: no modifica simulador, rna, difuso, genetico ni integracion.
Todos los valores son supuestos de simulación (ver docs/SPEC_MVP_3D.md, sección 6).

Turnos: cada acción que consume un turno (mover, paso, disparo) llama a tick(), que reduce el cooldown
y mueve a los drones según la máquina de estados:

    patrulla ──(a 6 celdas o menos)──► alerta ──(2 turnos)──► persecucion ──(a 1 celda)──► ataque
       ▲                                  │                       │  ▲                       │
       └──────(a más de 6 celdas)─────────┴───────────────────────┘  └──(a más de 1 celda)───┘

El dron no atraviesa obstáculos ni barrancos: solo se mueve sobre celdas libres.
"""
import random
from dataclasses import dataclass, field

from simulador import BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO

MUNICION_INICIAL = 10
COOLDOWN_TURNOS = 2          # unidad: turnos (ver spec, sección 6)
ALCANCE_DISPARO = 5          # celdas
DANO_IMPACTO = 1             # puntos de vida del dron por impacto
VIDA_DRON = 3
DISTANCIA_ALERTA = 6         # celdas (distancia de tablero, 8 direcciones)
DISTANCIA_ATAQUE = 1
TURNOS_ALERTA = 2
TURNOS_ENTRE_DANOS = 2       # el ataque quita batería cada 2 turnos
DANO_BATERIA_ATAQUE = 1.0    # % de batería por daño
DISTANCIA_MINIMA_INICIO = 8  # los drones aparecen lejos del rover


def distancia(a, b) -> int:
    """Distancia de tablero (Chebyshev): con movimiento en 8 direcciones, es el número de pasos."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


@dataclass
class Dron:
    id: int
    pos: tuple
    ruta_patrulla: list
    vida: int = VIDA_DRON
    estado: str = "patrulla"
    indice_patrulla: int = 0
    turnos_alerta: int = 0
    turnos_ataque: int = 0

    @property
    def vivo(self) -> bool:
        return self.estado != "muerto"


@dataclass
class Combate:
    mundo: object
    rover: object
    semilla: int = 0
    n_drones: int = 2
    municion: int = MUNICION_INICIAL
    cooldown: int = 0
    bajas: int = 0
    drones: list = field(default_factory=list)
    eventos: list = field(default_factory=list)   # texto de lo ocurrido en el último turno
    trayectorias: dict = field(default_factory=dict)  # ARX-29: id de dron -> posiciones por turno (últimas 50)

    def __post_init__(self):
        self.rng = random.Random(self.semilla)
        self.drones = self._colocar_drones()

    # ---------- colocación ----------
    def _celda_libre(self, pos) -> bool:
        return self.mundo.dentro(pos) and self.mundo.tipo[pos] == LIBRE

    def _colocar_drones(self) -> list:
        filas, columnas = self.mundo.tipo.shape
        candidatas = []
        for f in range(filas):
            for c in range(columnas):
                if distancia((f, c), self.rover.posicion) < DISTANCIA_MINIMA_INICIO:
                    continue
                if not self._celda_libre((f, c)):
                    continue
                for df, dc in ((0, 1), (1, 0)):          # par de patrulla cardinal
                    vecino = (f + df, c + dc)
                    if self._celda_libre(vecino):
                        candidatas.append([(f, c), vecino])
        self.rng.shuffle(candidatas)
        drones, ocupadas = [], set()
        for ruta in candidatas:
            if len(drones) >= self.n_drones:
                break
            if any(p in ocupadas for p in ruta):
                continue
            drones.append(Dron(id=len(drones) + 1, pos=ruta[0], ruta_patrulla=ruta))
            ocupadas.update(ruta)
        return drones

    # ---------- disparo ----------
    def disparar(self, rumbo: str) -> dict:
        """El rover dispara en el rumbo indicado. Lanza ValueError si no puede (cooldown o munición)."""
        if rumbo not in MOVIMIENTOS:
            raise ValueError(f"rumbo inválido: {rumbo!r}")
        if self.cooldown > 0:
            raise ValueError("disparo en cooldown")
        if self.municion <= 0:
            raise ValueError("sin munición")
        self.municion -= 1
        self.cooldown = COOLDOWN_TURNOS
        df, dc = MOVIMIENTOS[rumbo]
        f, c = self.rover.posicion
        golpeado = None
        for paso in range(1, ALCANCE_DISPARO + 1):
            celda = (f + df * paso, c + dc * paso)
            if not self.mundo.dentro(celda) or self.mundo.tipo[celda] in (OBSTACULO, BARRANCO):
                break
            dron = self._dron_en(celda)
            if dron is not None:
                dron.vida -= DANO_IMPACTO
                golpeado = dron.id
                if dron.vida <= 0:
                    dron.estado = "muerto"
                    self.bajas += 1
                    self.eventos.append(f"dron {dron.id} destruido")
                else:
                    self.eventos.append(f"impacto al dron {dron.id} (vida {dron.vida})")
                break
        if golpeado is None:
            self.eventos.append("disparo sin impacto")
        return {"impacto": golpeado is not None, "npc_golpeado": golpeado,
                "municion": self.municion, "cooldown": self.cooldown}

    # ---------- turno ----------
    def _dron_en(self, pos):
        for d in self.drones:
            if d.vivo and d.pos == pos:
                return d
        return None

    def _vecinos_libres(self, pos):
        for df, dc in MOVIMIENTOS.values():
            vecino = (pos[0] + df, pos[1] + dc)
            if self._celda_libre(vecino) and vecino != self.rover.posicion and self._dron_en(vecino) is None:
                yield vecino

    def _mover_hacia_rover(self, dron: Dron):
        mejor = None
        mejor_d = distancia(dron.pos, self.rover.posicion)
        for vecino in self._vecinos_libres(dron.pos):
            d = distancia(vecino, self.rover.posicion)
            if d < mejor_d:
                mejor, mejor_d = vecino, d
        if mejor is not None:
            dron.pos = mejor

    def _patrullar(self, dron: Dron):
        destino = dron.ruta_patrulla[(dron.indice_patrulla + 1) % len(dron.ruta_patrulla)]
        if self._celda_libre(destino) and self._dron_en(destino) is None and destino != self.rover.posicion:
            dron.pos = destino
            dron.indice_patrulla = (dron.indice_patrulla + 1) % len(dron.ruta_patrulla)

    def tick(self):
        """Un turno: reduce el cooldown y mueve a cada dron según su estado."""
        self.eventos = []
        if self.cooldown > 0:
            self.cooldown -= 1
        for dron in self.drones:
            if dron.vivo:
                self._paso_dron(dron)
            if dron.vivo:
                tray = self.trayectorias.setdefault(dron.id, [])
                tray.append([int(dron.pos[0]), int(dron.pos[1])])
                del tray[:-50]

    def _paso_dron(self, dron: Dron):
        d = distancia(dron.pos, self.rover.posicion)
        if dron.estado == "patrulla":
            if d <= DISTANCIA_ALERTA:
                dron.estado = "alerta"
                dron.turnos_alerta = TURNOS_ALERTA
                self.eventos.append(f"dron {dron.id}: alerta")
            else:
                self._patrullar(dron)
        elif dron.estado == "alerta":
            if d > DISTANCIA_ALERTA:
                dron.estado = "patrulla"
            else:
                dron.turnos_alerta -= 1
                if dron.turnos_alerta <= 0:
                    dron.estado = "persecucion"
                    self.eventos.append(f"dron {dron.id}: persecución")
        elif dron.estado == "persecucion":
            if d > DISTANCIA_ALERTA:
                dron.estado = "patrulla"
            elif d <= DISTANCIA_ATAQUE:
                dron.estado = "ataque"
                dron.turnos_ataque = 0
                self.eventos.append(f"dron {dron.id}: ataque")
            else:
                self._mover_hacia_rover(dron)
        elif dron.estado == "ataque":
            if d > DISTANCIA_ATAQUE:
                dron.estado = "persecucion"
            else:
                dron.turnos_ataque += 1
                if dron.turnos_ataque % TURNOS_ENTRE_DANOS == 0:
                    self.rover.consumir(DANO_BATERIA_ATAQUE)
                    self.eventos.append(f"dron {dron.id} daña la batería")

    # ---------- consulta ----------
    def npcs(self) -> list:
        return [{"id": d.id, "pos": [int(d.pos[0]), int(d.pos[1])], "estado": d.estado, "vida": d.vida}
                for d in self.drones if d.vivo]

    def drones_cerca(self, radio: int) -> list:
        """Drones vivos a `radio` celdas o menos del rover."""
        return [d for d in self.drones if d.vivo and distancia(d.pos, self.rover.posicion) <= radio]
