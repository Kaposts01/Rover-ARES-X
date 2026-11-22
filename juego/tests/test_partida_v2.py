"""Pruebas del agente M (contrato v2): niveles, falla de sensor, ambiente, puntaje, diagonales, objetivo."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import Partida  # noqa: E402
from simulador import BARRANCO, LIBRE, OBSTACULO, generar_mundo  # noqa: E402

TERMINALES = {"EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"}
CARDINALES = ["N", "S", "E", "O"]
TODOS = CARDINALES + ["NE", "NO", "SE", "SO"]


def _mover_legal(p, rumbos=TODOS):
    """Primer movimiento válido del jugador desde la posición actual."""
    for rumbo in rumbos:
        res = p.mover_jugador(rumbo)
        if res["movido"]:
            return res
    raise AssertionError("no hay movimiento legal disponible")


def _forzar_libre(p, celda):
    p.mundo.tipo[celda] = LIBRE
    p.mundo.sitios.pop(celda, None)


# ---------- niveles (ev3-d26) ----------

@pytest.mark.parametrize("nivel", [1, 2, 3, 4, 5])
def test_nivel_genera_el_mundo_del_contrato(nivel):
    p = Partida(semilla=11, nivel=nivel)
    sitios_esperados = 3 if nivel <= 2 else 4
    # ARX-66: la garantía de ganabilidad puede usar una variante del mismo mapa (semilla_mundo != semilla);
    # el contrato se comprueba contra la semilla con que se generó el mundo realmente.
    esperado = generar_mundo(p.semilla_mundo, n_obstaculos=20 + 2 * nivel, n_barrancos=4 + nivel,
                             n_sitios=sitios_esperados)
    assert np.array_equal(p.mundo.tipo, esperado.tipo)
    assert p.mundo.sitios == esperado.sitios
    assert len(p.mundo.sitios) == sitios_esperados
    assert p.nivel == nivel


@pytest.mark.parametrize("nivel", [1, 2, 3, 4, 5])
def test_bateria_inicial_baja_4_por_nivel(nivel):
    # R23: la curva de 100 − 4·(nivel − 1) es la de la evaluación congelada (garantia=False); la partida jugable tiene la
    # suya, más exigente (juego/dificultad.py), y en Marte coincide con la tabla del nivel
    assert Partida(semilla=11, nivel=nivel, garantia=False).rover.bateria == 100.0 - 4.0 * (nivel - 1)
    jugable = Partida(semilla=11, nivel=nivel).rover.bateria
    from juego import dificultad
    assert jugable == dificultad.BATERIA_POR_NIVEL[nivel] and jugable <= 100.0 - 4.0 * (nivel - 1)


def test_bateria_explicita_gana_sobre_el_nivel():
    assert Partida(semilla=11, bateria=50.0, nivel=3).rover.bateria == 50.0


@pytest.mark.parametrize("nivel", [0, 6, -1, "2", True, 2.0])
def test_nivel_invalido_lanza_value_error(nivel):
    with pytest.raises(ValueError):
        Partida(semilla=11, nivel=nivel)


# ---------- falla de sensor (ev3-d23 B) ----------

def test_falla_sensor_detiene_tres_pasos_sin_mover_ni_modo_seguro():
    p = Partida(semilla=11)
    assert p.disparar_evento("falla_sensor")["ok"] is True
    assert p.falla_restante == 3
    pos = p.rover.posicion
    bateria = p.rover.bateria
    for _ in range(3):
        res = p.avanzar_ia()
        assert res["accion"] == "detener"
        assert res["motivos"] == ["D-FALLA-SENSOR"]
        assert res["posicion"] == pos
        assert res["bateria"] == bateria
        assert res["estado"] not in TERMINALES
    assert p.falla_restante == 0
    assert p.rover.en_modo_seguro is False


def test_falla_sensor_se_termina_y_la_ia_continua():
    p = Partida(semilla=11)
    p.disparar_evento("falla_sensor")
    for _ in range(3):
        p.avanzar_ia()
    paso = p.mision.paso
    res = p.avanzar_ia()
    assert p.mision.paso == paso + 1
    assert "D-FALLA-SENSOR" not in res["motivos"]
    assert res["accion"] != "modo_seguro"


def test_falla_sensor_restaura_la_probabilidad_del_sensor():
    p = Partida(semilla=11)
    base = p.mision.sensor.prob_fallo
    p.disparar_evento("falla_sensor")
    for _ in range(3):
        p.avanzar_ia()
    assert p.mision.sensor.prob_fallo == base


def test_falla_sensor_sugerencia_es_idempotente_durante_la_falla():
    p = Partida(semilla=11)
    p.disparar_evento("falla_sensor")
    assert p.sugerencia() == p.sugerencia()
    assert p.sugerencia()["motivos"] == ["D-FALLA-SENSOR"]
    assert p.falla_restante == 3


def test_falla_sensor_nunca_lleva_a_modo_seguro_en_400_pasos():
    p = Partida(semilla=11)
    p.disparar_evento("falla_sensor")
    for _ in range(400):
        if p.estado in TERMINALES:
            break
        res = p.avanzar_ia()
        assert res["accion"] != "modo_seguro"
    assert p.rover.en_modo_seguro is False


# ---------- ambiente (ev3-d25) ----------

def test_eventos_manuales_tormenta_y_noche_fijan_el_ambiente():
    p = Partida(semilla=11)
    assert p.disparar_evento("tormenta") == {"ok": True, "detalle": "tormenta durante 6 pasos"}
    assert (p.ambiente, p.ambiente_restante) == ("tormenta", 6)
    assert p.disparar_evento("noche")["ok"] is True
    assert (p.ambiente, p.ambiente_restante) == ("noche", 8)


def test_evento_ambiente_desactivado_devuelve_ok_false():
    p = Partida(semilla=11, eventos_activos=("barranco",))
    assert p.disparar_evento("tormenta")["ok"] is False
    assert p.ambiente == "normal"


def test_tormenta_consume_1_por_ciento_extra_por_movimiento():
    p = Partida(semilla=11)
    p.disparar_evento("tormenta")
    antes = p.rover.bateria
    res = _mover_legal(p, CARDINALES)
    assert res["bateria"] == antes - 2.0


def test_noche_consume_0_5_por_ciento_extra_por_movimiento():
    p = Partida(semilla=11)
    p.disparar_evento("noche")
    antes = p.rover.bateria
    res = _mover_legal(p, CARDINALES)
    assert res["bateria"] == antes - 1.5


def test_tormenta_dura_seis_movimientos_y_luego_normal():
    p = Partida(semilla=11)
    p.disparar_evento("tormenta")
    for _ in range(6):
        _mover_legal(p, CARDINALES)
    assert p.ambiente == "normal"
    assert p.ambiente_restante == 0


def test_ambiente_aleatorio_es_reproducible_con_la_semilla():
    def secuencia(semilla):
        p = Partida(semilla=semilla, bateria=100.0)
        vistos = []
        for _ in range(300):
            p._tick_ambiente()
            vistos.append(p.ambiente)
        return vistos

    assert secuencia(5) == secuencia(5)
    assert any(a != "normal" for a in secuencia(5))


class _RngFijo:
    """Generador de prueba: siempre saca 0.99, así nunca inicia un ambiente."""

    def random(self):
        return 0.99


def test_ambiente_normal_sin_inicio_no_consume_bateria():
    p = Partida(semilla=11)
    p._rng_ambiente = _RngFijo()
    antes = p.rover.bateria
    p._tick_ambiente()
    assert p.rover.bateria == antes
    assert p.ambiente == "normal"


def test_ambiente_usa_generador_propio_no_el_de_la_mision():
    p = Partida(semilla=11)
    assert p._rng_ambiente is not p.mision.rng


# ---------- puntaje (ev3-d24) ----------

def test_puntaje_es_entero_con_la_formula_del_contrato():
    p = Partida(semilla=11)
    total = len(p.mundo.sitios)
    esperado = round(100 * len(p.mision.visitados) / total + 0.5 * p.rover.bateria
                     + (50 if p.mision.vetos == 0 else 0))
    valor = p.puntaje()
    assert isinstance(valor, int)
    assert valor == esperado


def test_puntaje_sin_sitios_no_divide_entre_cero():
    p = Partida(semilla=11)
    p.mundo.sitios.clear()
    valor = p.puntaje()
    assert valor == round(0.5 * p.rover.bateria + (50 if p.mision.vetos == 0 else 0))


def test_resumen_incluye_nivel_y_puntaje():
    p = Partida(semilla=11, nivel=2)
    r = p.resumen()
    assert r["nivel"] == 2
    assert r["puntaje"] == p.puntaje()


# ---------- diagonales (ev3-d28) ----------

def test_diagonal_valida_mueve_y_cuesta_1_por_ciento():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    _forzar_libre(p, (f - 1, c + 1))
    bateria = p.rover.bateria
    res = p.mover_jugador("NE")
    assert res["movido"] is True
    assert res["posicion"] == (f - 1, c + 1)
    assert res["bateria"] == bateria - 1.0


@pytest.mark.parametrize("rumbo,delta", [("NE", (-1, 1)), ("NO", (-1, -1)),
                                         ("SE", (1, 1)), ("SO", (1, -1))])
def test_cada_diagonal_se_desplaza_como_se_describe(rumbo, delta):
    p = Partida(semilla=11)
    p.rover.posicion = (10, 10)  # posición de prueba, celdas centrales
    destino = (10 + delta[0], 10 + delta[1])
    _forzar_libre(p, destino)
    res = p.mover_jugador(rumbo)
    assert res["movido"] is True
    assert res["posicion"] == destino


def test_diagonal_bloqueada_por_obstaculo_no_mueve_ni_gasta():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    destino = (f - 1, c + 1)
    p.mundo.tipo[destino] = OBSTACULO
    bateria = p.rover.bateria
    res = p.mover_jugador("NE")
    assert res["movido"] is False
    assert res["posicion"] == (f, c)
    assert res["bateria"] == bateria
    assert "obstáculo" in res["motivo"]


def test_diagonal_bloqueada_por_barranco():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    p.mundo.tipo[(f - 1, c + 1)] = BARRANCO
    res = p.mover_jugador("NE")
    assert res["movido"] is False
    assert "barranco" in res["motivo"]


def test_diagonal_fuera_del_mapa_es_bloqueada():
    p = Partida(semilla=11)
    assert p.rover.posicion == p.mundo.inicio  # esquina inferior izquierda
    res = p.mover_jugador("SO")
    assert res["movido"] is False
    assert res["motivo"] == "fuera del mapa"


def test_rumbo_desconocido_sigue_siendo_invalido():
    res = Partida(semilla=11).mover_jugador("XX")
    assert res["movido"] is False
    assert "inválido" in res["motivo"]


# ---------- objetivo fijado por el jugador (ev3-d27) ----------

def test_fijar_objetivo_valido_planea_la_ruta_hacia_la_celda():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    destino = (f - 2, c)
    _forzar_libre(p, destino)
    res = p.fijar_objetivo(destino)
    assert res["ok"] is True
    assert p.objetivo == destino
    assert p.ruta[-1] == destino


def test_fijar_objetivo_la_ia_lo_alcanza_y_lo_limpia():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    destino = (f - 2, c)
    _forzar_libre(p, destino)
    assert p.fijar_objetivo(destino)["ok"] is True
    for _ in range(30):
        if p.estado in TERMINALES or p.objetivo is None:
            break
        p.avanzar_ia()
    assert p.rover.posicion == destino
    assert p.objetivo is None


def test_fijar_objetivo_en_obstaculo_falla():
    p = Partida(semilla=11)
    celda = (p.rover.posicion[0] - 1, p.rover.posicion[1])
    p.mundo.tipo[celda] = OBSTACULO
    res = p.fijar_objetivo(celda)
    assert res["ok"] is False
    assert p.objetivo is None


def test_fijar_objetivo_fuera_del_mapa_falla():
    p = Partida(semilla=11)
    assert p.fijar_objetivo((-1, 0))["ok"] is False
    assert p.fijar_objetivo((999, 999))["ok"] is False


def test_fijar_objetivo_en_la_propia_celda_falla():
    p = Partida(semilla=11)
    assert p.fijar_objetivo(p.rover.posicion)["ok"] is False


def test_fijar_objetivo_sin_camino_falla():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    destino = (f - 2, c)
    _forzar_libre(p, destino)
    # Encierra la celda destino con obstáculos en sus ocho vecinos (movimiento de ocho direcciones).
    for df, dc in [(-1, 0), (1, 0), (0, 1), (0, -1), (-1, 1), (-1, -1), (1, 1), (1, -1)]:
        vecino = (destino[0] + df, destino[1] + dc)
        if vecino != p.rover.posicion and p.mundo.dentro(vecino):
            p.mundo.tipo[vecino] = OBSTACULO
            p.mision.riesgo[vecino] = 1.0
    res = p.fijar_objetivo(destino)
    assert res["ok"] is False
    assert p.objetivo is None


def test_fijar_objetivo_none_quita_el_objetivo():
    p = Partida(semilla=11)
    f, c = p.rover.posicion
    destino = (f - 2, c)
    _forzar_libre(p, destino)
    p.fijar_objetivo(destino)
    res = p.fijar_objetivo(None)
    assert res["ok"] is True
    assert p.objetivo is None
