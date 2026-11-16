"""Arranque del juego ARES-X. Uso: python juego/main.py (desde la carpeta ares_x/)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from juego.partida import Partida  # noqa: E402
from juego.ui import ejecutar  # noqa: E402


if __name__ == "__main__":
    ejecutar(lambda semilla, nivel=1: Partida(semilla=semilla, nivel=nivel))
