"""ARX-92b (QA, rendimiento): la partida grande se construye y avanza dentro de un tope de tiempo.

Medido antes y después (mismo equipo): construir 31,7 s → 8 s; mediana por paso 26 ms → 5 ms. Los topes son de
margen amplio para no depender de la máquina: si vuelven a dispararse, el problema es de rendimiento, no de lógica.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import Partida  # noqa: E402

TOPE_CONSTRUIR_S = 25.0      # medido 8 s
TOPE_MEDIANA_PASO_MS = 20.0  # medido 5 ms


def test_partida_grande_se_construye_dentro_del_tope():
    inicio = time.perf_counter()
    Partida(semilla=3, nivel=5, filas=40, columnas=60)
    assert time.perf_counter() - inicio < TOPE_CONSTRUIR_S


def test_pasos_de_la_partida_grande_dentro_del_tope():
    p = Partida(semilla=3, nivel=5, filas=40, columnas=60)
    tiempos = []
    for _ in range(40):
        if p.estado in ("EXITO", "FRACASO", "SIN_RUTA"):
            break
        t0 = time.perf_counter()
        p.avanzar_ia()
        tiempos.append(time.perf_counter() - t0)
    tiempos.sort()
    assert tiempos and tiempos[len(tiempos) // 2] * 1000 < TOPE_MEDIANA_PASO_MS
