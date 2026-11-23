"""ARX-79b: factor de seguridad de la garantía por tamaño y nivel, y margen de caza proporcional al mapa."""
import time

import pytest

from juego import partida as pm
from juego.partida import (AVISO_SIN_GARANTIA, MARGEN_CAZA, Partida, _es_ganable, factor_seguridad_garantia,
                           margen_caza)


def test_margen_de_caza_escala_con_el_mapa():
    assert margen_caza(20, 30) == MARGEN_CAZA == 10          # pequeño: sin cambio respecto de antes
    assert margen_caza(40, 60) == 20                         # grande: 60 / 3
    assert margen_caza(10, 10) == MARGEN_CAZA                # nunca baja del suelo
    assert margen_caza(60, 90) > margen_caza(40, 60)


@pytest.fixture
def k_plan(monkeypatch):
    monkeypatch.setattr(pm, "FACTOR_SEGURIDAD_K_ESCALA", pm.FACTOR_SEGURIDAD_PLAN[0])
    monkeypatch.setattr(pm, "FACTOR_SEGURIDAD_K_NIVEL", pm.FACTOR_SEGURIDAD_PLAN[1])


def test_factor_neutro_por_omision():
    assert factor_seguridad_garantia(40, 60, 5) == 1.0       # mientras la ficha no fije K (ver partida.py)


def test_factor_de_seguridad_por_tamano_y_nivel(k_plan):
    assert factor_seguridad_garantia(20, 30, 1) == pytest.approx(1.0)
    assert factor_seguridad_garantia(40, 60, 1) == pytest.approx(1.45)      # plan 79: Muy fácil grande ≈ 1,45
    assert factor_seguridad_garantia(20, 30, 5) == pytest.approx(1.2)
    assert factor_seguridad_garantia(40, 60, 5) > factor_seguridad_garantia(40, 60, 1)
    assert factor_seguridad_garantia(40, 60, 3) > factor_seguridad_garantia(20, 30, 3)


def test_el_factor_y_el_margen_endurecen_el_estimador(k_plan):
    p = Partida(semilla=3, nivel=3, filas=40, columnas=60, plan_restringido=False)
    p.factor_seguridad = factor_seguridad_garantia(40, 60, 3)
    m = p.mundo
    # batería mínima (por pasos de 1) con la que _es_ganable acepta el mapa elegido, con y sin las constantes nuevas
    def minima(**kw):
        b = 20.0
        while not _es_ganable(m, b, **kw):
            b += 1.0
            assert b < 3000
        return b
    from juego.partida import _drones_obligatorios
    drones = _drones_obligatorios(m, p.semilla_mundo, 3)
    base = minima(drones=drones)
    con = minima(drones=drones, factor=p.factor_seguridad, margen_caza_pasos=p.margen_caza)
    assert con > base


def test_atributos_de_la_partida_segun_tamano():
    g = Partida(semilla=1, nivel=1, filas=40, columnas=60, plan_restringido=False)
    c = Partida(semilla=1, nivel=1, plan_restringido=False)
    assert g.margen_caza == 20 and c.margen_caza == 10
    assert g.factor_seguridad == 1.0 and c.factor_seguridad == 1.0   # K neutros


@pytest.mark.parametrize("nivel", [1, 2, 3, 4, 5])
def test_el_mapa_elegido_es_ganable_con_el_estimador_nuevo_y_es_determinista(nivel):
    a = Partida(semilla=2, nivel=nivel, plan_restringido=False)
    b = Partida(semilla=2, nivel=nivel, plan_restringido=False)
    assert a.semilla_mundo == b.semilla_mundo
    assert (a.mundo.tipo == b.mundo.tipo).all()
    assert AVISO_SIN_GARANTIA not in a.avisos                # pequeño: sigue habiendo variante que pasa (R23: puede avisar AG-FALLBACK)
    drones = pm._drones_obligatorios(a.mundo, a.semilla, nivel)
    # R23: la garantía de la partida jugable cuenta con las bases de recarga y el sobrecoste medio del planeta
    assert _es_ganable(a.mundo, a.rover.bateria, drones, bateria_max=a.bateria_max, estaciones=a.estaciones,
                       factor=a.factor_seguridad * a.mision.factor_ambiente, margen_caza_pasos=a.margen_caza)


def test_pequeno_no_se_queda_sin_garantia_en_una_muestra():
    for nivel in (1, 3, 5):
        for semilla in range(1, 6):
            assert AVISO_SIN_GARANTIA not in Partida(semilla=semilla, nivel=nivel, plan_restringido=False).avisos


def test_mapa_imposible_forzado_avisa():
    p = Partida(semilla=4, nivel=2, bateria=5.0, plan_restringido=False)
    assert AVISO_SIN_GARANTIA in p.avisos
    q = Partida(semilla=4, nivel=2, bateria=5.0, garantia=False, plan_restringido=False)
    assert AVISO_SIN_GARANTIA not in q.avisos


def test_una_llamada_del_estimador_en_grande_no_pasa_de_2_s():
    # La generación completa (59 variantes de 40x60) tarda ~8 s ya en la base 5801c7d: no es del estimador (ver informe).
    p = Partida(semilla=8, nivel=3, filas=40, columnas=60, plan_restringido=False)
    drones = pm._drones_obligatorios(p.mundo, 8, 3)
    t0 = time.time()
    _es_ganable(p.mundo, p.rover.bateria, drones, factor=p.factor_seguridad, margen_caza_pasos=p.margen_caza)
    assert time.time() - t0 < 2.0
