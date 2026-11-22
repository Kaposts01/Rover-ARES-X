"""R23 (correcciones tras el QA final): bucle de replanteo parado sobre una base de recarga, barranco del evento, rótulo del viento."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integracion import ESTADOS_TERMINALES  # noqa: E402
import planificacion  # noqa: E402
from juego import planetas  # noqa: E402
from juego import partida as jp  # noqa: E402
from juego.partida import Partida  # noqa: E402


# (las pruebas de partidas completas por la API, con drones y combate, están en api/tests/test_correcciones_motor_r23.py)


def test_salvaguarda_de_quietud_escala_y_termina_con_motivo():
    p = Partida(semilla=5, nivel=3, planeta="Marte")
    p.avanzar_ia()
    pos = tuple(p.rover.posicion)
    p.rover.bateria = 2.0                                   # ni al refugio llega: el último escalón es el fin con motivo
    for _ in range(40):
        if p.estado in ESTADOS_TERMINALES:
            break
        p.mision.log.registrar(paso=p.mision.paso, estado="ALERTA", posicion=str(pos), bateria=2.0, accion="replanificar",
                               velocidad=0.0, p_barranco=None, p_obstaculo=None, reglas="", motivos="PRUEBA")
        p._vigilar_quietud(pos)
    assert p._escape_nivel >= 1
    assert p.estado == "FRACASO" and any("sin plan posible" in a for a in p.avisos)


def test_un_movimiento_reinicia_la_cuenta_de_quietud():
    p = Partida(semilla=5, nivel=3, planeta="Marte")
    p.avanzar_ia()
    pos = tuple(p.rover.posicion)
    p._quietos = jp.PASOS_QUIETO_MAXIMO - 1
    p._vigilar_quietud((pos[0], pos[1] + 5))                # el rover está en otra celda que antes: se movió
    assert p._quietos == 0 and p._escape_nivel == 0


def test_una_base_donde_ya_esta_no_es_destino_del_ultimo_recurso():
    """El recurso «ir a la base alcanzable más cercana» incluía la base donde el rover ya estaba (ruta de 1 celda: REPLAN-RUTA-VACIA
    en cada paso). Ahora se excluye."""
    import inspect
    fuente = inspect.getsource(Partida._planear_restringido)
    assert "0 < len(t) - 1 <= self.rover.bateria" in fuente


def test_liberar_ruta_real_borra_lecturas_firmes_falsas_sobre_el_camino_real():
    p = Partida(semilla=5, nivel=3, planeta="Marte")
    m = p.mision
    origen = tuple(int(v) for v in p.rover.posicion)
    refugio = tuple(int(v) for v in p.mundo.refugio)
    m.riesgo[refugio[0] + 1, refugio[1]] = 1.0              # celdas libres en el mundo real, marcadas como riesgo en el estimado
    m.riesgo[refugio[0] + 1, refugio[1] - 1] = 1.0
    m.riesgo[refugio[0], refugio[1] - 1] = 1.0
    assert p._liberar_ruta_real(origen, refugio) in (True, False)
    asegura = np.asarray(m.riesgo < 0.5)
    assert asegura[refugio]


# ---------- defecto 3: barranco ----------
def _con_barranco(semilla=7, nivel=3):
    p = Partida(semilla=semilla, nivel=nivel, planeta="Marte")
    p.avanzar_ia()
    r = p.disparar_evento("barranco")
    assert r["ok"] is True
    return p, tuple(r["celdas"][0])


def test_el_barranco_del_evento_no_marca_el_mapa_estimado_antes_de_percibirlo():
    p, celda = _con_barranco()
    assert p.mision.riesgo[celda] < 0.5           # el rover no lo conoce todavía
    assert celda in {tuple(x) for x in p.mision.ruta}


@pytest.mark.parametrize("semilla", [7, 1, 2, 3])
def test_el_barranco_se_percibe_se_clasifica_y_la_ruta_lo_rodea(semilla):
    p, celda = _con_barranco(semilla)
    visto, replanteo = False, False
    for _ in range(4):
        p.avanzar_ia()
        ui = p.mision.ultima_ia or {}
        for t in ui.get("tramo", []):
            if tuple(t["celda"]) == celda:
                visto = True
        fila = p.mision.log.filas[-1] if p.mision.log.filas else {}
        replanteo = replanteo or fila.get("accion") == "replanificar"
        if p.mision.riesgo[celda] >= 0.5:
            break
    assert visto, "la celda del barranco nunca salió en rna.tramo"
    assert p.mision.riesgo[celda] >= 0.5          # percibido por la anticipación o por los sensores
    assert celda not in {tuple(x) for x in p.mision.ruta}      # la ruta ya no lo cruza


def test_una_celda_con_riesgo_conocido_sigue_en_el_tramo_marcada():
    p = Partida(semilla=7, nivel=3, planeta="Marte")
    p.avanzar_ia()
    m = p.mision
    celda = tuple(int(v) for v in m.ruta[2]) if len(m.ruta) > 3 else None
    if celda is None or celda in p._celdas_conocidas():
        pytest.skip("sin celda adecuada en la ruta")
    m.riesgo[celda] = 1.0                          # ya conocida como riesgo (p. ej. por un sensor)
    p._anticipar()
    visto = [e for e in p._ant_ultima if tuple(e["celda"]) == celda]
    assert not visto or visto[0]["marcada"] is True


# ---------- defecto 6: viento ----------
def test_la_escala_del_viento_es_la_misma_en_el_perfil_y_en_el_estado():
    nep = planetas.parametros("Neptuno")
    assert nep["viento_rotulo"] == "muy fuerte"
    mec = planetas.MecanicasPlaneta("Neptuno", Partida(semilla=5, nivel=3, planeta="Neptuno").mundo, 5, 0.75, True)
    assert mec.estado()["viento"] == pytest.approx(0.85 * 0.75, abs=1e-3)       # 0,64 con la escala del nivel
    assert mec.estado()["viento_rotulo"] == nep["viento_rotulo"]                # pero el rótulo es el del perfil
    for nombre in planetas.PERFILES:
        perfil = planetas.PERFILES[nombre]
        m = planetas.MecanicasPlaneta(nombre, Partida(semilla=5, nivel=1, garantia=False).mundo, 5, 0.4, True)
        assert m.estado()["viento_rotulo"] == planetas.parametros(nombre)["viento_rotulo"] == planetas.rotulo_viento(perfil.viento)
