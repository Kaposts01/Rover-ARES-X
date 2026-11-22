import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import Partida  # noqa: E402
from simulador import BARRANCO, LIBRE, MOVIMIENTOS  # noqa: E402

ESTADOS_VALIDOS = {"EXPLORACION", "ALERTA", "EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"}
TERMINALES = {"EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"}


def _instantanea(p):
    m = p.mision
    return (m.paso, p.rover.posicion, p.rover.bateria, p.estado, len(m.log.filas),
            m.rng.bit_generator.state["state"]["state"], m.riesgo.copy(), list(m.ruta))


def test_sugerencia_es_idempotente_y_no_muta_el_estado():
    p = Partida(semilla=11)
    antes = _instantanea(p)
    s1 = p.sugerencia()
    s2 = p.sugerencia()
    despues = _instantanea(p)
    assert s1 == s2
    assert antes[:5] == despues[:5]
    assert np.array_equal(antes[6], despues[6])
    assert antes[7] == despues[7]
    assert antes[5] == despues[5]


def test_sugerencia_tiene_las_claves_del_contrato():
    s = Partida(semilla=11).sugerencia()
    claves = {"rumbo", "accion", "velocidad", "p_barranco", "p_obstaculo", "p_libre",
              "reglas", "desglose", "motivos"}
    assert claves <= set(s)
    assert s["accion"] in {"avanzar", "detener", "replanificar", "modo_seguro"}
    assert 0.0 <= s["velocidad"] <= 1.0


def test_mover_jugador_a_barranco_no_mueve_ni_lanza():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    for rumbo, (df, dc) in MOVIMIENTOS.items():
        celda = (f + df, c + dc)
        if p.mundo.dentro(celda) and p.mundo.tipo[celda] == LIBRE and celda not in p.mundo.sitios:
            p.mundo.marcar_barranco(celda)
            break
    else:
        raise AssertionError("no hay celda libre adyacente para la prueba")
    bateria = p.rover.bateria
    res = p.mover_jugador(rumbo)
    assert res["movido"] is False
    assert res["posicion"] == (f, c)
    assert res["bateria"] == bateria
    assert "barranco" in res["motivo"]


def test_mover_jugador_gasta_bateria_solo_si_se_mueve():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    bateria = p.rover.bateria
    res = p.mover_jugador("N")
    if res["movido"]:
        assert res["posicion"] == (f - 1, c)
        assert res["bateria"] == bateria - 1.0
    else:
        assert res["posicion"] == (f, c)
        assert res["bateria"] == bateria


def test_disparar_barranco_cae_enfrente_sobre_la_ruta_y_nunca_inicio_ni_refugio():
    # 22/11: el barranco aparece 2 a 4 celdas por delante sobre la ruta (sin aislar refugio ni sitios); si no, adyacente
    p = Partida(semilla=11)
    p.avanzar_ia()
    ruta = [tuple(x) for x in p.mision.ruta]
    antes = int(np.sum(p.mundo.tipo == BARRANCO))
    res = p.disparar_evento("barranco")
    assert res["ok"] is True
    assert int(np.sum(p.mundo.tipo == BARRANCO)) == antes + 1
    celda = tuple(res["celdas"][0])
    assert p.mundo.tipo[celda] == BARRANCO and celda not in (p.mundo.inicio, p.mundo.refugio)
    f, c = p.rover.posicion
    adyacente = max(abs(celda[0] - f), abs(celda[1] - c)) == 1
    assert celda in ruta[2:5] or adyacente


def test_evento_desconocido_devuelve_ok_false():
    res = Partida(semilla=11).disparar_evento("volcan")
    assert res["ok"] is False


def test_bateria_baja_fija_15():
    p = Partida(semilla=11)
    res = p.disparar_evento("bateria_baja")
    assert res["ok"] is True
    assert p.rover.bateria == 15.0


def test_falla_sensor_no_lanza_al_avanzar():
    p = Partida(semilla=11)
    assert p.disparar_evento("falla_sensor")["ok"] is True
    assert p.mision.sensor.prob_fallo == 1.0
    res = p.avanzar_ia()
    assert res["estado"] in ESTADOS_VALIDOS


def test_avanzar_ia_termina_en_estado_valido_tras_400_pasos_semilla_11():
    p = Partida(semilla=11)
    for _ in range(400):
        if p.estado in TERMINALES:
            break
        res = p.avanzar_ia()
        assert res["estado"] in ESTADOS_VALIDOS
    assert p.estado in ESTADOS_VALIDOS
    assert p.estado in TERMINALES or p.resumen()["pasos"] == 400


def test_bitacora_tiene_una_fila_por_paso():
    p = Partida(semilla=11)
    for _ in range(400):
        if p.estado in TERMINALES:
            break
        p.avanzar_ia()
    assert len(p.bitacora()) == p.resumen()["pasos"]
    assert list(p.bitacora()["paso"]) == list(range(1, p.resumen()["pasos"] + 1))


def test_resumen_tiene_las_claves_de_mision():
    p = Partida(semilla=11)
    assert {"estado", "pasos", "sitios_visitados", "sitios_totales", "bateria_final",
            "vetos", "replanes", "colisiones", "barrancos_pisados"} <= set(p.resumen())


def test_pila_suma_el_diez_por_ciento_de_la_capacidad_sin_pasarse():
    # 22/11: pilas en la partida jugable; recogerla suma el 10 % de la capacidad (la batería inicial), con tope
    p = Partida(semilla=11)
    assert p.pilas and p.estaciones and p.bateria_max == p.capacidad_bateria
    celda = p.pilas[0]
    p.rover.bateria = 0.5 * p.capacidad_bateria
    p.rover.posicion = celda
    p._recoger_pila()
    assert p.rover.bateria == pytest.approx(0.6 * p.capacidad_bateria)
    assert celda not in p.pilas and p.pilas_recogidas == 1
    p.rover.bateria = 0.97 * p.capacidad_bateria
    p.rover.posicion = p.pilas[0]
    p._recoger_pila()
    assert p.rover.bateria == pytest.approx(p.capacidad_bateria)          # nunca más del 100 %


def test_las_evaluaciones_no_tienen_bases_ni_pilas():
    from juego import comparacion
    p = comparacion.partida_variante(1, "hibrido", "congelado")
    assert p.pilas == [] and p.estaciones == []
