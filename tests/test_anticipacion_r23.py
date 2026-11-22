"""R23: RNA con anticipación (celdas de la ruta a 2, 3 y 4 pasos) y regresión del barranco que la RNA no veía."""
import numpy as np
import pytest

import anticipacion as ant
from juego.partida import UMBRAL_ANT_PRECAUCION, Partida
from simulador import generar_mundo


@pytest.fixture(scope="module")
def red():
    return ant.rna_anticipacion()


def test_la_anticipacion_ve_barrancos_a_2_3_y_4_celdas_con_pocos_falsos(red):
    r = ant.evaluar(red, umbral=UMBRAL_ANT_PRECAUCION)
    for k in ant.DISTANCIAS:
        assert r[k]["recall_barranco"] >= 0.25, (k, r[k])          # mucho más que 0: la red original no ve nada a esa distancia
        assert r[k]["falsos_barrancos_en_libres"] <= 0.04, (k, r[k])
    assert r[2]["recall_barranco"] > r[4]["recall_barranco"]       # el ruido crece con la distancia: ver lejos cuesta más


def test_barranco_forzado_a_tres_celdas_sube_p_barranco_frente_a_una_celda_libre(red):
    mundo = generar_mundo(semilla=7, n_obstaculos=0, n_barrancos=0)
    pos, ruta_libre = (10, 2), [(10, 3), (10, 4), (10, 5)]
    mundo.marcar_barranco((10, 5))                                   # barranco forzado a 3 celdas
    rng = np.random.default_rng(1)
    con, sin = [], []
    for _ in range(300):
        con.append(red.probabilidades(ant.rasgos_anticipacion(mundo, pos, (10, 4), (10, 5), 3, rng))["barranco"])
        sin.append(red.probabilidades(ant.rasgos_anticipacion(mundo, pos, (10, 3), (10, 4), 2, rng))["barranco"])
    assert np.mean(con) > 3 * np.mean(sin)
    assert np.mean(np.array(con) >= UMBRAL_ANT_PRECAUCION) > 0.25


def test_las_lecturas_de_anticipacion_no_consumen_el_azar_de_la_mision():
    p = Partida(semilla=5, nivel=1)
    antes = p.mision.rng.bit_generator.state
    p._anticipar()
    assert p.mision.rng.bit_generator.state == antes


def test_el_tramo_clasificado_trae_celda_distancia_y_probabilidades():
    p = Partida(semilla=5, nivel=1)
    p.avanzar_ia()
    ui = p.mision.ultima_ia
    tramo = ui["tramo"]
    assert [t["distancia"] for t in tramo] == sorted(t["distancia"] for t in tramo)
    assert tramo[0]["distancia"] == 1 and tuple(tramo[0]["celda"]) == tuple(ui["celda"])
    assert len(tramo) <= 4
    for t in tramo:
        assert set(t["probabilidades"]) == {"libre", "obstáculo", "barranco"}
        assert abs(sum(t["probabilidades"].values()) - 1.0) < 0.01


def test_sin_rna_no_hay_anticipacion():
    p = Partida(semilla=5, nivel=1)
    p.mision.usar_rna = False
    p._anticipar()
    assert p._ant_ultima == [] and not p._precaucion_ant


def test_un_barranco_en_la_ruta_se_marca_antes_de_llegar():
    """Regresión: la RNA de una celda lo veía recién al tenerlo encima. Con la anticipación, la celda queda como riesgo (y la ruta la
    rodea) mientras el rover todavía está a 2 o más celdas, sin ayuda del veto del frente."""
    marcadas_antes = 0
    for semilla in (5, 6, 7, 8, 9, 10):
        p = Partida(semilla=semilla, nivel=1)
        m = p.mision
        if len(m.ruta) < 8 or m.ruta[5] in p._celdas_conocidas():
            continue
        celda = tuple(m.ruta[5])
        p.mundo.marcar_barranco(celda)                     # barranco real a 5 celdas; el rover no lo conoce
        for _ in range(4):
            if p.estado in ("EXITO", "FRACASO", "SIN_RUTA"):
                break
            lejos = max(abs(p.rover.posicion[0] - celda[0]), abs(p.rover.posicion[1] - celda[1])) >= 2
            p.avanzar_ia()
            if lejos and m.riesgo[celda] >= 0.5:
                marcadas_antes += 1
                break
    assert marcadas_antes >= 2
