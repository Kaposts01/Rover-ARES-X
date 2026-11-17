"""ARX-89b: Partida.tiempo_computo_s acumula el tiempo de cómputo (construcción, pasos, movimientos, eventos)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import Partida  # noqa: E402


def test_tiempo_computo_incluye_la_construccion_y_crece_con_los_pasos():
    p = Partida(semilla=11)
    inicial = p.tiempo_computo_s
    assert isinstance(inicial, float) and inicial > 0.0
    p.avanzar_ia()
    p.avanzar_ia()
    assert p.tiempo_computo_s > inicial


def test_avanzar_modo_no_cuenta_dos_veces_las_llamadas_anidadas():
    p = Partida(semilla=11)
    antes = p.tiempo_computo_s
    p.avanzar_modo("ag")
    assert p._cronometro_nivel == 0
    assert 0.0 < p.tiempo_computo_s - antes < 30.0
    p.mover_jugador("N")
    p.disparar_evento("noche")
    assert p._cronometro_nivel == 0


def test_cada_partida_lleva_su_propio_acumulador():
    a, b = Partida(semilla=11), Partida(semilla=11)
    a.avanzar_ia()
    assert a.tiempo_computo_s != b.tiempo_computo_s
