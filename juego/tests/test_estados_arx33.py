"""ARX-33a: estado_visible completo (CONFIGURACION, REPLANIFICACION tras sismo, ALERTA, REFUGIO, MODO_SEGURO, EXITO)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import Partida  # noqa: E402


def _con_un_paso(semilla=11):
    p = Partida(semilla=semilla)
    p.avanzar_ia()
    return p


def test_configuracion_en_partida_nueva():
    p = Partida(semilla=11)
    assert p.mision.paso == 0 and p.estado_visible() == "CONFIGURACION"
    p.avanzar_ia()
    assert p.estado_visible() != "CONFIGURACION"


def test_alerta_con_intervencion_difuso_baja():
    p = Partida(semilla=11)
    p.mision.intervencion_difuso = 0.3
    p.avanzar_ia()
    assert p.estado == "ALERTA" and p.estado_visible() == "ALERTA"


def test_replanificacion_tras_sismo_con_grieta_en_la_ruta():
    p = _con_un_paso()
    for semilla_rng in range(60):
        ruta = {tuple(x) for x in p.mision.ruta}
        antes = len(p.sismos)
        p.disparar_evento("sismo")
        if len(p.sismos) > antes and any(tuple(g) in ruta for g in p.sismos[-1]["grietas"]):
            break
        p.avanzar_ia()
    else:
        raise AssertionError("no hubo sismo con grieta en la ruta")
    fila = p.mision.log.filas[-1]
    assert fila["accion"] == "replanificar" and fila["motivos"] in ("REPLAN-AG-SISMO", "REPLAN-SISMO")
    assert p.estado_visible() == "REPLANIFICACION"


def test_refugio_al_visitar_todos_los_sitios():
    p = _con_un_paso()
    p.mision.visitados = set(p.mundo.sitios)
    assert p.estado_visible() == "REFUGIO"


def test_modo_seguro_con_sensor_caido():
    p = _con_un_paso()
    p.mision.sensor.prob_fallo = 1.0
    for _ in range(10):
        p.mision.paso_mision()
        if p.estado == "MODO_SEGURO":
            break
    assert p.estado == "MODO_SEGURO" and p.estado_visible() == "MODO_SEGURO"


def test_exito_al_llegar_al_refugio():
    p = Partida(semilla=11, eventos_activos=())
    for _ in range(400):
        if p.estado in ("EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"):
            break
        p.avanzar_ia()
    assert p.estado == "EXITO" and p.estado_visible() == "EXITO"
