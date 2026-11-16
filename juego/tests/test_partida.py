import sys
from pathlib import Path

import numpy as np

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


def test_disparar_barranco_deja_celda_adyacente_y_nunca_inicio_ni_refugio():
    p = Partida(semilla=11)
    antes = int(np.sum(p.mundo.tipo == BARRANCO))
    res = p.disparar_evento("barranco")
    assert res["ok"] is True
    assert int(np.sum(p.mundo.tipo == BARRANCO)) == antes + 1
    f, c = p.rover.posicion
    adyacentes = [(f + df, c + dc) for df, dc in MOVIMIENTOS.values()]
    marcadas = [a for a in adyacentes if p.mundo.dentro(a) and p.mundo.tipo[a] == BARRANCO]
    assert len(marcadas) == 1
    assert marcadas[0] not in (p.mundo.inicio, p.mundo.refugio)


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
