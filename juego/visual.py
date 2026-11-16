"""Dibujo realista del mapa de Marte con pygame, sin imágenes externas (todo procedural).

- El terreno, las rocas, los cráteres, los cristales y la base se dibujan UNA vez por mapa
  y se guardan en caché (preparar_terreno). Cada cuadro solo se dibujan la ruta, el rover y la flecha.
- Todo es decorativo: no cambia la simulación ni las decisiones de la IA.
"""
import math
import random

import pygame

from simulador import OBSTACULO, BARRANCO

# Paleta marciana (supuesto visual, no dato de misión)
ROJO_BASE = (196, 118, 80)
ROJO_OSCURO = (150, 84, 58)
ROJO_CLARO = (226, 152, 108)
ROCA = (110, 78, 62)
ROCA_LUZ = (168, 122, 96)
ROCA_SOMBRA = (58, 38, 30)
CRATER = (92, 34, 22)
CRATER_BORDE = (200, 110, 74)
CRISTAL = (80, 160, 255)
CRISTAL_LUZ = (210, 240, 255)
BASE_PARED = (206, 208, 216)
BASE_DETALLE = (70, 170, 110)
ROVER_CUERPO = (232, 232, 236)
ROVER_DETALLE = (244, 150, 60)
ROVER_PANEL = (28, 52, 110)
RUEDA = (30, 28, 28)

_CACHE = {}


def _ruido(f, c, semilla):
    """Ruido suave determinista en [-1, 1] para variar el color del terreno."""
    return (math.sin(f * 0.61 + semilla) * math.cos(c * 0.47 - semilla * 0.3)
            + 0.5 * math.sin((f + c) * 0.23 + semilla * 1.7)) / 1.5


def _mezclar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _sombra(superficie, centro, rx, ry, alfa=90):
    capa = pygame.Surface((int(rx * 2) + 2, int(ry * 2) + 2), pygame.SRCALPHA)
    pygame.draw.ellipse(capa, (30, 12, 6, alfa), capa.get_rect())
    superficie.blit(capa, (centro[0] - rx, centro[1] - ry))


def _roca(superficie, centro, radio, rng):
    cx, cy = centro
    _sombra(superficie, (cx + 3, cy + 4), radio * 1.05, radio * 0.6)
    puntos = []
    n = 8
    for i in range(n):
        ang = 2 * math.pi * i / n
        r = radio * (0.78 + rng.random() * 0.3)
        puntos.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.82))
    pygame.draw.polygon(superficie, ROCA, puntos)
    luz = [(x - radio * 0.18, y - radio * 0.18) for x, y in puntos[:5]]
    pygame.draw.polygon(superficie, ROCA_LUZ, luz)
    pygame.draw.polygon(superficie, ROCA_SOMBRA, puntos, 1)
    for _ in range(3):
        pygame.draw.circle(superficie, ROCA_SOMBRA,
                           (int(cx + (rng.random() - 0.5) * radio),
                            int(cy + (rng.random() - 0.5) * radio)), 1)


def _crater(superficie, centro, radio):
    cx, cy = centro
    for k in range(6, 0, -1):
        t = k / 6
        color = _mezclar(CRATER_BORDE, (18, 6, 4), 1 - t)
        pygame.draw.circle(superficie, color, (cx, cy), int(radio * t))
    pygame.draw.circle(superficie, CRATER_BORDE, (cx, cy), int(radio), 1)


def _cristal(superficie, centro, tam):
    cx, cy = centro
    halo = pygame.Surface((tam * 4, tam * 4), pygame.SRCALPHA)
    pygame.draw.circle(halo, (80, 160, 255, 60), (tam * 2, tam * 2), tam * 1.6)
    superficie.blit(halo, (cx - tam * 2, cy - tam * 2))
    puntos = [(cx, cy - tam), (cx + tam * 0.7, cy), (cx, cy + tam), (cx - tam * 0.7, cy)]
    pygame.draw.polygon(superficie, CRISTAL, puntos)
    pygame.draw.polygon(superficie, CRISTAL_LUZ, [(cx, cy - tam), (cx + tam * 0.3, cy - tam * 0.2), (cx, cy)])
    pygame.draw.polygon(superficie, (30, 70, 140), puntos, 1)


def _base(superficie, rect):
    x, y, w, h = rect
    halo = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
    pygame.draw.rect(halo, (70, 170, 110, 70), halo.get_rect(), border_radius=10)
    superficie.blit(halo, (x - 8, y - 8))
    pygame.draw.rect(superficie, BASE_PARED, rect, border_radius=5)
    pygame.draw.rect(superficie, (150, 150, 160), rect, 2, border_radius=5)
    franja = pygame.Rect(x + 4, y + h // 2 - 2, w - 8, 4)
    pygame.draw.rect(superficie, BASE_DETALLE, franja)
    pygame.draw.rect(superficie, ROVER_PANEL, (x + w // 2 - 5, y + 3, 10, 8))


def preparar_terreno(tipo, refugio, sitios, celda, margen, semilla=0):
    """Superficie con todo el mapa estático. Se cachea por contenido del mapa."""
    clave = (tipo.tobytes(), tuple(refugio), tuple(sorted(sitios)), celda, margen, semilla)
    if clave in _CACHE:
        return _CACHE[clave]
    filas, columnas = tipo.shape
    superficie = pygame.Surface((columnas * celda, filas * celda))
    rng = random.Random(semilla * 7919 + filas * 31 + columnas)

    for f in range(filas):
        for c in range(columnas):
            x, y = c * celda, f * celda
            base = _mezclar(ROJO_OSCURO, ROJO_CLARO, (_ruido(f, c, semilla) + 1) / 2)
            base = _mezclar(base, ROJO_BASE, 0.5)
            pygame.draw.rect(superficie, base, (x, y, celda, celda))
            for _ in range(2):
                px = x + rng.randint(2, celda - 3)
                py = y + rng.randint(2, celda - 3)
                tono = ROJO_CLARO if rng.random() < 0.5 else ROJO_OSCURO
                pygame.draw.circle(superficie, tono, (px, py), rng.choice((1, 1, 2)))

    for f in range(filas):
        for c in range(columnas):
            pos = (f, c)
            centro = (c * celda + celda // 2, f * celda + celda // 2)
            valor = int(tipo[f, c])
            if valor == OBSTACULO:
                _roca(superficie, centro, celda * 0.38, rng)
            elif valor == BARRANCO:
                _crater(superficie, centro, celda * 0.42)
    for pos in sitios:
        f, c = pos
        centro = (c * celda + celda // 2, f * celda + celda // 2)
        _cristal(superficie, centro, celda * 0.3)
    f, c = refugio
    _base(superficie, (c * celda + 3, f * celda + 5, celda - 6, celda - 10))

    _CACHE.clear()          # solo se guarda el mapa actual
    _CACHE[clave] = superficie
    return superficie


def dibujar_ruta(superficie, ruta, celda, margen):
    """Línea de puntos suave por la ruta planeada."""
    for paso, (f, c) in enumerate(ruta):
        if paso % 2:
            continue
        centro = (margen + c * celda + celda // 2, margen + f * celda + celda // 2)
        brillo = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(brillo, (255, 230, 90, 150), (6, 6), 5)
        superficie.blit(brillo, (centro[0] - 6, centro[1] - 6))


def dibujar_rover(superficie, rover, rumbo, celda, margen):
    """Rover con sombra, cuatro ruedas, panel solar, antena y faro en la dirección de avance."""
    f, c = rover
    cx = margen + c * celda + celda // 2
    cy = margen + f * celda + celda // 2
    ancho, alto = celda * 0.62, celda * 0.5
    _sombra(superficie, (cx + 3, cy + 4), ancho * 0.75, alto * 0.7, alfa=110)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        pygame.draw.circle(superficie, RUEDA, (int(cx + dx * ancho * 0.42), int(cy + dy * alto * 0.5)),
                           max(3, int(celda * 0.1)))
    cuerpo = pygame.Rect(0, 0, ancho, alto)
    cuerpo.center = (cx, cy)
    pygame.draw.rect(superficie, ROVER_CUERPO, cuerpo, border_radius=4)
    pygame.draw.rect(superficie, (90, 90, 100), cuerpo, 1, border_radius=4)
    panel = pygame.Rect(0, 0, ancho * 0.6, alto * 0.5)
    panel.center = (cx, cy)
    pygame.draw.rect(superficie, ROVER_PANEL, panel)
    for k in range(1, 3):
        pygame.draw.line(superficie, (90, 130, 200), (panel.x + k * panel.w // 3, panel.y),
                         (panel.x + k * panel.w // 3, panel.bottom))
    pygame.draw.line(superficie, (150, 150, 160), (cx, cy - alto * 0.3), (cx + 3, cy - alto * 0.9), 2)
    pygame.draw.circle(superficie, ROVER_DETALLE, (int(cx + 3), int(cy - alto * 0.9)), 3)
    vectores = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0),
                "NE": (1, -1), "NO": (-1, -1), "SE": (1, 1), "SO": (-1, 1)}
    dx, dy = vectores.get(rumbo, (0, 0))
    if dx or dy:
        faro = (int(cx + dx * ancho * 0.55), int(cy + dy * alto * 0.55))
        pygame.draw.circle(superficie, (255, 240, 170), faro, 3)
