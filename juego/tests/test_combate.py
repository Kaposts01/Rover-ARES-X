"""Pruebas del combate (ARX-06): munición, cooldown, impactos, máquina de estados y regla de no atravesar."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.combate import (  # noqa: E402
    COOLDOWN_TURNOS, DANO_BATERIA_ATAQUE, Combate, Dron, MUNICION_INICIAL, VIDA_DRON, distancia,
)
from simulador import LIBRE, OBSTACULO, Rover, generar_mundo  # noqa: E402


def mundo_libre(filas=30, columnas=40):
    m = generar_mundo(semilla=0, filas=filas, columnas=columnas, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    return m


def combate_con_dron(pos_rover=(15, 10), pos_dron=None, patrulla=None):
    m = mundo_libre()
    rover = Rover(posicion=pos_rover, bateria=100.0)
    c = Combate(mundo=m, rover=rover, semilla=0, n_drones=0)
    if pos_dron is not None:
        ruta = patrulla or [pos_dron, (pos_dron[0], pos_dron[1] + 1)]
        c.drones = [Dron(id=1, pos=pos_dron, ruta_patrulla=ruta)]
    return c


# ---------- munición y cooldown ----------
def test_municion_inicial_y_cooldown_en_turnos():
    c = combate_con_dron()
    assert c.municion == MUNICION_INICIAL
    c.disparar("N")
    assert c.municion == MUNICION_INICIAL - 1
    assert c.cooldown == COOLDOWN_TURNOS


def test_dos_disparos_seguidos_sin_turno_solo_produce_uno():
    c = combate_con_dron()
    c.disparar("N")
    with pytest.raises(ValueError, match="cooldown"):
        c.disparar("N")
    assert c.municion == MUNICION_INICIAL - 1


def test_el_cooldown_baja_un_turno_por_tick():
    c = combate_con_dron()
    c.disparar("N")
    c.tick()
    assert c.cooldown == COOLDOWN_TURNOS - 1
    c.tick()
    assert c.cooldown == 0
    c.disparar("N")                     # ya puede volver a disparar


def test_sin_municion_no_dispara():
    c = combate_con_dron()
    c.municion = 0
    with pytest.raises(ValueError, match="munición"):
        c.disparar("N")


def test_agotar_la_municion_con_turnos_intermedios():
    c = combate_con_dron()
    for _ in range(MUNICION_INICIAL):
        c.disparar("O")
        c.tick()
        c.tick()
    assert c.municion == 0


def test_rumbo_invalido_lanza_error():
    with pytest.raises(ValueError):
        combate_con_dron().disparar("X")


# ---------- impactos y daño ----------
def test_impacto_en_linea_recta_resta_vida():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 13))
    res = c.disparar("E")
    assert res["impacto"] is True
    assert res["npc_golpeado"] == 1
    assert c.drones[0].vida == VIDA_DRON - 1


def test_tres_impactos_destruyen_al_dron():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 12))
    for _ in range(VIDA_DRON):
        c.disparar("E")
        c.tick()
        c.tick()
    assert c.drones[0].estado == "muerto"
    assert c.bajas == 1
    assert not c.npcs()          # un dron muerto ya no aparece en la escena


def test_disparo_sin_impacto_si_no_hay_dron_en_la_linea():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(2, 2))
    res = c.disparar("N")
    assert res["impacto"] is False
    assert c.eventos and "sin impacto" in c.eventos[-1]


def test_un_obstaculo_bloquea_el_disparo():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 13))
    c.mundo.tipo[15, 11] = OBSTACULO
    res = c.disparar("E")
    assert res["impacto"] is False


def test_alcance_maximo_del_disparo():
    from juego.combate import ALCANCE_DISPARO
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 10 + ALCANCE_DISPARO + 1))
    assert c.disparar("E")["impacto"] is False


# ---------- máquina de estados ----------
def test_patrulla_pasa_a_alerta_a_seis_celdas():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 16))   # distancia 6
    c.tick()
    assert c.drones[0].estado == "alerta"


def test_alerta_pasa_a_persecucion_tras_dos_turnos():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 16))
    c.tick()                             # patrulla -> alerta
    c.tick()
    assert c.drones[0].estado == "alerta"
    c.tick()
    assert c.drones[0].estado == "persecucion"


def test_alerta_vuelve_a_patrulla_si_el_rover_se_aleja():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 16))
    c.tick()
    c.drones[0].pos = (15, 25)           # a 15 celdas
    c.tick()
    assert c.drones[0].estado == "patrulla"


def test_persecucion_se_acerca_y_pasa_a_ataque_a_una_celda():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 14))
    c.drones[0].estado = "persecucion"
    for _ in range(4):
        c.tick()
        if c.drones[0].estado == "ataque":
            break
    assert c.drones[0].estado == "ataque"
    assert distancia(c.drones[0].pos, c.rover.posicion) <= 1


def test_ataque_quita_bateria_cada_dos_turnos():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 11))
    c.drones[0].estado = "ataque"
    antes = c.rover.bateria
    c.tick()
    assert c.rover.bateria == antes          # primer turno: sin daño
    c.tick()
    assert c.rover.bateria == pytest.approx(antes - DANO_BATERIA_ATAQUE)


def test_ataque_vuelve_a_persecucion_si_el_rover_se_aleja():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 11))
    c.drones[0].estado = "ataque"
    c.rover.posicion = (15, 14)          # ya no está a 1 celda
    c.tick()
    assert c.drones[0].estado == "persecucion"


def test_persecucion_vuelve_a_patrulla_si_el_rover_queda_lejos():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 14))
    c.drones[0].estado = "persecucion"
    c.rover.posicion = (15, 30)          # a 20 celdas
    c.tick()
    assert c.drones[0].estado == "patrulla"


# ---------- reglas del terreno ----------
def test_el_dron_no_atraviesa_obstaculos():
    c = combate_con_dron(pos_rover=(15, 10), pos_dron=(15, 16))
    for f in range(10, 21):
        for col in range(8, 13):
            if (f, col) not in [(15, 10), (15, 16)]:
                c.mundo.tipo[f, col] = OBSTACULO
    c.drones[0].estado = "persecucion"
    for _ in range(10):
        c.tick()
        assert c.mundo.tipo[c.drones[0].pos] == LIBRE


def test_colocacion_inicial_de_drones_lejos_del_rover():
    m = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    rover = Rover(posicion=m.inicio, bateria=100.0)
    c = Combate(mundo=m, rover=rover, semilla=11, n_drones=2)
    assert len(c.drones) == 2
    for d in c.drones:
        assert distancia(d.pos, m.inicio) >= 8
        assert m.tipo[d.pos] == LIBRE
