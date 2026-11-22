"""ARX-82 (M8): cromosomas inviables se reparan (descarte del punto, ruta contigua) o se penalizan."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genetico import PENALIZACION_INVIABLE, GeneticPlanner  # noqa: E402
from simulador import BARRANCO, LIBRE, OBSTACULO, generar_mundo  # noqa: E402


def mundo_vacio(filas=10, columnas=12):
    m = generar_mundo(semilla=0, filas=filas, columnas=columnas, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    return m


def planificador(mundo, bateria=100.0):
    # Mapa estimado perfecto: riesgo 1.0 donde hay peligro real, 0.0 en el resto.
    riesgo = np.where(mundo.tipo != LIBRE, 1.0, 0.0)
    return GeneticPlanner(mundo, riesgo, bateria=bateria, k_puntos=3)


def es_contigua(ruta):
    return all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1 for a, b in zip(ruta, ruta[1:]))


def assert_viable(plan, ruta):
    m = plan.mundo
    assert ruta[0] == m.inicio and ruta[-1] == m.refugio
    assert es_contigua(ruta), "hay saltos entre celdas no vecinas"
    assert all(0 <= f < m.forma[0] and 0 <= c < m.forma[1] for f, c in ruta)
    assert all(m.tipo[c] == LIBRE for c in ruta), "la ruta pisa obstáculo o barranco"


def test_ruta_no_contigua_se_decodifica_contigua():
    plan = planificador(mundo_vacio())
    # Puntos de paso muy separados entre sí (saltos enormes): el decodificador los une por BFS.
    cromosoma = [(0, 0), (9, 11), (0, 5)]
    d = plan.decodificar(cromosoma)
    assert not d.inviable_sin_camino
    assert d.reparaciones == 0
    assert_viable(plan, d.ruta)
    assert plan.evaluar(cromosoma).penalizacion == 0


@pytest.mark.parametrize("tipo", [OBSTACULO, BARRANCO])
def test_punto_sobre_obstaculo_o_barranco_se_descarta(tipo):
    m = mundo_vacio()
    m.tipo[5, 5] = tipo
    plan = planificador(m)
    d = plan.decodificar([(5, 5), (3, 3)])
    assert d.reparaciones == 1
    assert (5, 5) not in d.ruta
    assert_viable(plan, d.ruta)
    assert plan.evaluar([(5, 5), (3, 3)]).penalizacion == pytest.approx(0.5 * PENALIZACION_INVIABLE)


def test_ruta_entre_puntos_rodea_muro_sin_pisarlo():
    m = mundo_vacio()
    m.tipo[:9, 6] = OBSTACULO          # muro con un único paso en la fila 9
    m.tipo[9, 6] = LIBRE
    plan = planificador(m)
    d = plan.decodificar([(2, 2), (2, 9)])
    assert_viable(plan, d.ruta)
    assert (9, 6) in d.ruta


@pytest.mark.parametrize("punto", [(-1, 3), (3, -1), (10, 3), (3, 12), (50, 50)])
def test_punto_fuera_del_mapa_se_repara(punto):
    plan = planificador(mundo_vacio())
    d = plan.decodificar([punto, (3, 3)])
    assert d.reparaciones == 1
    assert punto not in d.ruta
    assert_viable(plan, d.ruta)
    assert plan.evaluar([punto, (3, 3)]).penalizacion == pytest.approx(0.5 * PENALIZACION_INVIABLE)


def test_cromosoma_totalmente_invalido_queda_viable_con_penalizacion_proporcional():
    m = mundo_vacio()
    m.tipo[5, 5] = OBSTACULO
    m.tipo[4, 4] = BARRANCO
    plan = planificador(m)
    cromosoma = [(5, 5), (4, 4), (-3, 99)]
    d = plan.decodificar(cromosoma)
    assert d.reparaciones == 3
    assert_viable(plan, d.ruta)
    assert plan.evaluar(cromosoma).penalizacion == pytest.approx(3 * 0.5 * PENALIZACION_INVIABLE)
    assert plan.evaluar(cromosoma).fitness < plan.evaluar([(3, 3)]).fitness


def test_refugio_inalcanzable_se_marca_inviable_y_penaliza():
    m = mundo_vacio()
    m.tipo[0, 10] = OBSTACULO
    m.tipo[1, 10] = OBSTACULO
    m.tipo[1, 11] = OBSTACULO     # el refugio (0, 11) queda aislado
    plan = planificador(m)
    d = plan.decodificar([(3, 3)])
    assert d.inviable_sin_camino
    assert plan.evaluar([(3, 3)]).penalizacion >= PENALIZACION_INVIABLE


def test_mutacion_con_coordenada_invalida_se_repara():
    """Matriz §9: un gen mutado a una celda inválida no rompe la ruta decodificada."""
    m = mundo_vacio()
    m.tipo[5, 5] = OBSTACULO
    plan = planificador(m)
    original = [(2, 2), (3, 3), (4, 4)]
    for invalido in [(5, 5), (-1, -1), (99, 0)]:
        mutado = list(original)
        mutado[1] = invalido
        d = plan.decodificar(mutado)
        assert d.reparaciones == 1
        assert_viable(plan, d.ruta)


def test_obstaculo_real_no_detectado_lo_veta_el_supervisor_al_ejecutar():
    """Comportamiento de diseño (ev3-d02): el AG planifica con el mapa ESTIMADO y no ve un obstáculo real
    no detectado (riesgo < 0.5); la ruta decodificada lo pisa. La cobertura está en la ejecución: al
    detectarlo (celda de barranco en la lectura del sensor, o RNA con alta probabilidad), el supervisor veta."""
    from integracion import SafetySupervisor

    m = mundo_vacio()
    m.tipo[:, 6] = OBSTACULO
    m.tipo[4, 6] = LIBRE                       # único paso real
    riesgo = np.where(m.tipo != LIBRE, 1.0, 0.0)
    riesgo[2, 6] = 0.05                        # el rover no detectó el obstáculo en (2, 6)
    plan = GeneticPlanner(m, riesgo, k_puntos=2)
    d = plan.decodificar([(2, 2), (2, 9)])
    # El AG usa el mapa estimado: planea sobre la celda no detectada y no la repara ni la penaliza.
    assert (2, 6) in d.ruta and m.tipo[2, 6] == OBSTACULO
    assert d.reparaciones == 0 and plan.evaluar([(2, 2), (2, 9)]).penalizacion == 0
    # El veto del supervisor cubre la celda real al pisarla.
    lectura = {"proximidad_frontal_m": 1.0, "desnivel_frontal_m": -3.0, "altimetria_m": 0.5}
    dec = SafetySupervisor().decidir({"libre": 0.9}, 0.8, lectura, 90)
    assert dec.accion == "replanificar" and "V-BORDE-BARRANCO" in dec.motivos
    dec = SafetySupervisor().decidir({"obstáculo": 0.9, "libre": 0.1}, 0.8,
                                     dict(lectura, desnivel_frontal_m=0.0), 90)
    assert dec.accion == "replanificar" and "V-RNA-OBSTACULO" in dec.motivos
