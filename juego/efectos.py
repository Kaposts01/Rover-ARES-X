"""Efectos visuales de eventos y de fin de partida: título, destello, partículas, tinte de ambiente
y parpadeo de las celdas durante una falla de sensor.

Solo dibujo y temporización. No cambia la partida ni la simulación.
- titulo_de(evento): texto grande que se muestra al disparar un evento.
- Efectos: lista de efectos activos. actualizar() avanza un cuadro; dibujar() los pinta sobre el mapa.
- fijar_ambiente(nombre) y fijar_falla(activa): estado visual persistente, mientras dure el ambiente
  o la falla de sensor.
"""
import math
import random

import pygame

# Cada efecto: título, color de destello/título y duración en cuadros (30 por segundo)
CATALOGO = {
    "barranco": ("¡BARRANCO!", (230, 60, 40), 45),
    "falla_sensor": ("¡FALLA DE SENSOR!", (200, 200, 220), 45),
    "bateria_baja": ("¡BATERÍA BAJA!", (250, 200, 60), 45),
    "bloqueado": ("¡PASO BLOQUEADO!", (255, 120, 60), 25),
    "tormenta": ("¡TORMENTA DE POLVO!", (225, 165, 70), 90),
    "noche": ("¡NOCHE MARCIANA!", (120, 150, 255), 90),
    "EXITO": ("¡MISIÓN COMPLETADA!", (90, 230, 130), 150),
    "FRACASO": ("¡MISIÓN FALLIDA!", (230, 70, 70), 150),
    "MODO_SEGURO": ("¡MODO SEGURO!", (250, 160, 60), 120),
    "SIN_RUTA": ("¡SIN RUTA AL REFUGIO!", (250, 200, 80), 120),
}

# Tinte de pantalla mientras dura cada ambiente: (color, alfa 0-255)
TINTES = {
    "tormenta": ((200, 150, 60), 55),   # ocre
    "noche": ((15, 25, 110), 95),       # azul oscuro
}

COLOR_FALLA = (255, 60, 60)
ALFA_FALLA = 70
CUADROS_POR_FASE_FALLA = 6              # el parpadeo cambia cada 6 cuadros (5 veces por segundo)


def titulo_de(clave):
    """Devuelve (título, color, duración) de un evento o estado, o None si no tiene efecto."""
    return CATALOGO.get(clave)


class Efectos:
    def __init__(self, rng=None):
        self.rng = rng or random.Random(7)
        self.activos = []   # cada uno: dict(titulo, color, restante, duracion, celda, particulas)
        self.ambiente = None        # "tormenta", "noche" o None: tinte persistente
        self.falla_activa = False   # True mientras el sensor falla: celdas parpadean
        self.cuadro = 0

    def disparar(self, clave, celda=None):
        info = titulo_de(clave)
        if info is None:
            return False
        titulo, color, duracion = info
        particulas = [
            {"ang": self.rng.random() * 2 * math.pi, "vel": 1.5 + self.rng.random() * 2.5}
            for _ in range(18)
        ]
        self.activos.append({"titulo": titulo, "color": color, "restante": duracion,
                             "duracion": duracion, "celda": celda, "particulas": particulas})
        return True

    def fijar_ambiente(self, nombre):
        """Tinte de pantalla para 'tormenta' o 'noche'; cualquier otro valor lo quita."""
        self.ambiente = nombre if nombre in TINTES else None

    def fijar_falla(self, activa):
        self.falla_activa = bool(activa)

    def actualizar(self):
        self.cuadro += 1
        for efecto in self.activos:
            efecto["restante"] -= 1
        self.activos = [e for e in self.activos if e["restante"] > 0]

    def hay_activos(self):
        return bool(self.activos)

    def dibujar(self, superficie, origen_mapa, celda, ancho_mapa, fuente, alto_mapa=None):
        """Pinta tinte, parpadeo, destellos, partículas y títulos sobre el mapa.
        origen_mapa = esquina superior izquierda del mapa."""
        if alto_mapa is None:
            alto_mapa = 20 * celda
        mapa = pygame.Rect(origen_mapa[0], origen_mapa[1], ancho_mapa, alto_mapa)
        self._dibujar_tinte(superficie, mapa)
        if self.falla_activa:
            self._dibujar_parpadeo(superficie, origen_mapa, celda, ancho_mapa, alto_mapa)
        if not self.activos:
            return
        capa = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        for efecto in self.activos:
            t = efecto["restante"] / efecto["duracion"]       # 1 al inicio, 0 al final
            color = efecto["color"]
            if t > 0.6:                                        # destello al inicio
                alfa = int(90 * (t - 0.6) / 0.4)
                ancho, alto = superficie.get_size()
                capa.fill((*color, alfa), pygame.Rect(0, 0, ancho, alto))
            if efecto["celda"] is not None:
                f, c = efecto["celda"]
                cx = origen_mapa[0] + c * celda + celda // 2
                cy = origen_mapa[1] + f * celda + celda // 2
                avance = 1 - t
                for p in efecto["particulas"]:
                    r = p["vel"] * avance * celda * 1.2
                    x = cx + math.cos(p["ang"]) * r
                    y = cy + math.sin(p["ang"]) * r
                    pygame.draw.circle(capa, (*color, int(220 * t)), (int(x), int(y)), 3)
        superficie.blit(capa, (0, 0))
        # Títulos apilados en la parte superior del mapa
        for n, efecto in enumerate(self.activos):
            t = efecto["restante"] / efecto["duracion"]
            alfa = 255 if t > 0.2 else int(255 * t / 0.2)
            texto = fuente.render(efecto["titulo"], True, efecto["color"])
            fondo = pygame.Surface((texto.get_width() + 24, texto.get_height() + 12), pygame.SRCALPHA)
            pygame.draw.rect(fondo, (10, 10, 18, min(200, alfa)), fondo.get_rect(), border_radius=8)
            fondo.blit(texto, (12, 6))
            fondo.set_alpha(alfa)
            x = origen_mapa[0] + (ancho_mapa - fondo.get_width()) // 2
            y = origen_mapa[1] + 14 + n * (fondo.get_height() + 8)
            superficie.blit(fondo, (x, y))

    def _dibujar_tinte(self, superficie, mapa):
        if self.ambiente is None:
            return
        color, alfa = TINTES[self.ambiente]
        capa = pygame.Surface((mapa.width, mapa.height), pygame.SRCALPHA)
        capa.fill((*color, alfa))
        superficie.blit(capa, mapa.topleft)

    def _dibujar_parpadeo(self, superficie, origen_mapa, celda, ancho_mapa, alto_mapa):
        """Tablero de celdas alternas que se encienden y apagan mientras falla el sensor."""
        fase = (self.cuadro // CUADROS_POR_FASE_FALLA) % 2
        capa = pygame.Surface((ancho_mapa, alto_mapa), pygame.SRCALPHA)
        for f in range(alto_mapa // celda):
            for c in range(ancho_mapa // celda):
                if (f + c + fase) % 2 == 0:
                    capa.fill((*COLOR_FALLA, ALFA_FALLA), pygame.Rect(c * celda, f * celda, celda, celda))
        superficie.blit(capa, origen_mapa)
