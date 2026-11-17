"""ARX-91: el chequeo V-OBSTACULO-EN-RUTA es incondicional (ev3-d68 B).

Antes solo se consultaba si el supervisor decidía "detener"; la ablación sin difuso (velocidad fija 0,5)
no se detiene y nunca lo consultaba.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integracion import DISTANCIA_BLOQUEO_RUTA  # noqa: E402
from juego.partida import COLUMNAS_BASE, FILAS_BASE, Partida  # noqa: E402
from integracion import _rumbo  # noqa: E402


def _mision(usar_difuso):
    p = Partida(semilla=7, nivel=1, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)
    m = p.mision
    m.usar_difuso = usar_difuso
    return p, m


def _con_obstaculo_en_ruta(m, distancia):
    """Hace que el sensor vea un obstáculo a `distancia` celdas por el rumbo del próximo paso."""
    leer = m.sensor.leer

    def leer_falso(mundo, pos, rumbo):
        return dict(leer(mundo, pos, rumbo), proximidad_frontal_m=float(distancia))
    m.sensor.leer = leer_falso


@pytest.mark.parametrize("usar_difuso", [False, True])
@pytest.mark.parametrize("distancia", [1, 2, DISTANCIA_BLOQUEO_RUTA])
def test_obstaculo_visto_en_la_ruta_replanifica_sin_importar_la_parada(usar_difuso, distancia):
    _, m = _mision(usar_difuso)
    pos = m.rover.posicion
    rumbo = _rumbo(pos, m.ruta[1])
    _con_obstaculo_en_ruta(m, distancia)
    # solo cuenta si la celda observada cae sobre las próximas celdas de la ruta
    if not m._obstaculo_en_ruta(pos, rumbo, float(distancia)):
        pytest.skip("la ruta de esta semilla no pasa por esa celda a esa distancia")
    registros = []
    original = m._registrar
    m._registrar = lambda accion, vel, motivos, *a: (registros.append((accion, list(motivos))),
                                                    original(accion, vel, motivos, *a))[1]
    m.paso_mision()
    assert registros, "el paso no registró ninguna decisión"
    accion, motivos = registros[0]
    assert accion == "replanificar"
    assert "V-OBSTACULO-EN-RUTA" in motivos


def test_sin_difuso_distancia_uno_siempre_cae_en_la_ruta():
    """A distancia 1 la celda observada es la siguiente de la ruta: el caso sin difuso no puede saltarse el chequeo."""
    _, m = _mision(False)
    _con_obstaculo_en_ruta(m, 1)
    registros = []
    original = m._registrar
    m._registrar = lambda accion, vel, motivos, *a: (registros.append((accion, list(motivos))),
                                                    original(accion, vel, motivos, *a))[1]
    m.paso_mision()
    assert registros[0][0] == "replanificar"
    assert "V-OBSTACULO-EN-RUTA" in registros[0][1]
