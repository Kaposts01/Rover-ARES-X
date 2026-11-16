"""Capturas automáticas de escenas clave del juego, sin ventana visible (SDL_VIDEODRIVER=dummy).

Uso (desde ares_x/):  python juego/capturas.py
Guarda PNG en juego/capturas/: inicio, barranco, falla_sensor, tormenta y llegada_refugio.
Semilla fija (11) para que las capturas sean reproducibles.
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from juego import ui  # noqa: E402
from juego.partida import Partida  # noqa: E402

CARPETA_CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas")
SEMILLA = 11
MAX_PASOS_IA = 400


def _fuentes():
    return {"cuerpo": pygame.font.Font(None, 20), "titulo": pygame.font.Font(None, 24),
            "grande": pygame.font.Font(None, 44)}


def _juego(semilla=SEMILLA):
    return ui.Juego(lambda s, nivel=1: Partida(semilla=s, nivel=nivel), semilla=semilla,
                    rng=random.Random(1))


def _capturar(juego, superficie, fuentes, nombre, cuadros_efecto=0, carpeta=CARPETA_CAPTURAS):
    """Avanza los efectos unos cuadros y guarda la vista como PNG."""
    for _ in range(cuadros_efecto):
        juego.efectos.actualizar()
    ui.dibujar_todo(superficie, fuentes, ui.construir_vista(juego))
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{nombre}.png")
    pygame.image.save(superficie, ruta)
    return ruta


def generar_capturas(semilla=SEMILLA, carpeta=CARPETA_CAPTURAS):
    """Devuelve {nombre: ruta_png} de las escenas clave. Requiere pygame-ce."""
    pygame.init()
    try:
        superficie = pygame.display.set_mode((ui.ANCHO, ui.ALTO))
        fuentes = _fuentes()
        rutas = {}

        juego = _juego(semilla)
        rutas["inicio"] = _capturar(juego, superficie, fuentes, "inicio", carpeta=carpeta)

        juego = _juego(semilla)
        juego.despachar("avanzar")
        juego.despachar("evento", "barranco")
        rutas["barranco"] = _capturar(juego, superficie, fuentes, "barranco", carpeta=carpeta, cuadros_efecto=8)

        juego = _juego(semilla)
        juego.despachar("avanzar")
        juego.despachar("evento", "falla_sensor")
        rutas["falla_sensor"] = _capturar(juego, superficie, fuentes, "falla_sensor", carpeta=carpeta, cuadros_efecto=8)

        juego = _juego(semilla)
        juego.despachar("avanzar")
        juego.despachar("evento", "tormenta")
        rutas["tormenta"] = _capturar(juego, superficie, fuentes, "tormenta", carpeta=carpeta, cuadros_efecto=8)

        juego = _juego(semilla)
        for _ in range(MAX_PASOS_IA):
            juego.despachar("avanzar")
            juego.efectos.actualizar()   # los efectos caducan con el tiempo, como en la ventana
            if juego.partida.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
                break
        rutas["llegada_refugio"] = _capturar(juego, superficie, fuentes, "llegada_refugio", carpeta=carpeta,
                                             cuadros_efecto=0)
        return rutas
    finally:
        pygame.quit()


if __name__ == "__main__":
    for nombre, ruta in generar_capturas().items():
        print(f"{nombre}: {ruta}")
