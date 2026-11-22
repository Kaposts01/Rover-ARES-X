"""ARX-31a: el AG vuelve a planificar solo ante eventos graves que tocan la ruta, como máximo una vez por paso."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.partida import EVENTOS_GRAVES, Partida  # noqa: E402
from simulador import BARRANCO, LIBRE, MOVIMIENTOS  # noqa: E402


def _filas_ag(p):
    return [f for f in p.mision.log.filas if str(f.get("motivos", "")).startswith("REPLAN-AG-")]


def _ruta(p):
    return {tuple(x) for x in p.mision.ruta}


def _partida(semilla=11, nivel=1):
    p = Partida(semilla=semilla, nivel=nivel)
    p.avanzar_ia()
    return p


def _celda_barranco(p):
    """La celda que elegirá _evento_barranco (misma regla: primera adyacente libre que no sea sitio, inicio ni refugio)."""
    f, c = p.rover.posicion
    for df, dc in MOVIMIENTOS.values():
        celda = (f + df, c + dc)
        if (p.mundo.dentro(celda) and p.mundo.tipo[celda] == LIBRE and celda not in p.mundo.sitios
                and celda not in (p.mundo.inicio, p.mundo.refugio)):
            return celda
    return None


def test_eventos_graves_declarados():
    assert set(EVENTOS_GRAVES) == {"sismo", "senal_biologica"}


def test_bateria_baja_no_replanea_con_ag():
    p = _partida()
    p.disparar_evento("bateria_baja")
    assert _filas_ag(p) == []                         # Mision._planear descarta los sitios igual: no se gasta el AG


def test_sismo_con_grieta_en_la_ruta_replanea_con_ag():
    # ARX-94f: semilla 3 (con el mundo v2 la 11 no deja ninguna grieta sobre la ruta en los intentos; con MUNDO_V1 la 11 sí)
    p = _partida(semilla=3)
    for _ in range(80):
        ruta, antes, replanes = _ruta(p), len(p.sismos), p.mision.replanes
        p.disparar_evento("sismo")
        if len(p.sismos) > antes and any(tuple(g) in ruta for g in p.sismos[-1]["grietas"]):
            break
        p.avanzar_ia()
    else:
        raise AssertionError("no hubo sismo con grieta en la ruta")
    assert p.mision.replanes > replanes
    assert p.mision.log.filas[-1]["motivos"] == "REPLAN-AG-SISMO"
    assert p.mision.objetivos and p.mision.objetivos[-1] == p.mundo.refugio   # objetivos recomputados por el AG
    assert p.estado_visible() == "REPLANIFICACION"


def test_meteorito_lejos_de_la_ruta_no_replanea_con_ag():
    p = _partida()
    for _ in range(80):
        ruta, antes = _ruta(p), len(p.meteoritos)
        p.disparar_evento("meteorito")
        if len(p.meteoritos) > antes and not any(tuple(z) in ruta for z in p.meteoritos[-1]["zona_riesgo"]):
            assert _filas_ag(p) == []
            return
        p.avanzar_ia()
    raise AssertionError("no hubo meteorito fuera de la ruta")


def test_meteorito_sobre_la_ruta_no_usa_el_ag_sino_bfs():
    p = _partida()
    for _ in range(120):
        ruta, antes = _ruta(p), len(p.meteoritos)
        p.disparar_evento("meteorito")
        if len(p.meteoritos) > antes and any(tuple(z) in ruta for z in p.meteoritos[-1]["zona_riesgo"]):
            assert _filas_ag(p) == []          # el replanteo es el BFS del motor, no el AG
            return
        p.avanzar_ia()
    raise AssertionError("no hubo meteorito sobre la ruta")


def test_barranco_sobre_la_ruta_no_usa_el_ag_sino_bfs():
    p = _partida()
    for _ in range(80):
        celda = _celda_barranco(p)
        if celda is not None and celda in _ruta(p):
            p.disparar_evento("barranco")
            assert _filas_ag(p) == []          # el replanteo es el BFS del motor, no el AG
            assert p.mundo.tipo[celda] == BARRANCO
            return
        p.avanzar_ia()
    raise AssertionError("no hubo barranco sobre la ruta")


def test_dos_replanteos_en_el_mismo_paso_comparten_uno():
    p = _partida()
    assert p._replanear_ag("senal") is True
    assert p._replanear_ag("sismo") is False
    assert len(_filas_ag(p)) == 1
    p.avanzar_ia()
    assert p._replanear_ag("sismo") is True           # paso nuevo: otro replanteo
    assert len(_filas_ag(p)) == 2


def test_replanteo_del_ag_reinicia_paros_seguidos():
    p = _partida()
    p.mision.paros_seguidos = 2
    p._replanear_ag("senal")
    assert p.mision.paros_seguidos == 0


def test_sin_eventos_no_hay_replanteo_del_ag_en_el_escenario_congelado(monkeypatch):
    p = Partida(semilla=11, garantia=False, eventos_activos=())
    for _ in range(60):
        p.avanzar_ia()
    assert _filas_ag(p) == []

    def _prohibido(self, motivo):
        raise AssertionError("el escenario congelado no debe replantear con el AG")
    monkeypatch.setattr(Partida, "_replanear_ag", _prohibido)
    from juego.comparacion import comparar
    assert len(comparar(range(1, 4))["filas"]) > 0
