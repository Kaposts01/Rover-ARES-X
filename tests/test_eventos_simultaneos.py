"""ARX-84 (criterio M14): eventos simultáneos con prioridad determinista.

Se disparan varios eventos en el mismo paso (antes de avanzar) y se fija el orden de vetos y avisos que resulta
del motor. Orden en el motor: los eventos se aplican en el orden de las llamadas a disparar_evento; los vetos los
decide después Mision.paso_mision (REPLAN-SISMO se anota al disparar el sismo; V-RUTA-CON-RIESGO sale en el primer
paso). Dos corridas con la misma semilla deben dar exactamente el mismo orden y los mismos avisos.
Solo pruebas: no cambia el motor.
"""
import pytest

from integracion import ESTADOS_TERMINALES
from juego.partida import BATERIA_BAJA, DANO_METEORITO, PASOS_SIN_ENLACE, Partida

TRIPLE = ["sismo", "bateria_baja", "meteorito"]
PAR = ["tormenta", "baja_conectividad"]


def _corrida(eventos, semilla, pasos, nivel=5):
    p = Partida(semilla=semilla, nivel=nivel)
    resultados = [(e, p.disparar_evento(e)["ok"]) for e in eventos]
    bateria_tras_eventos = round(float(p.rover.bateria), 2)
    avisos_tras_eventos = list(p.avisos)
    traza = []
    for _ in range(pasos):
        p.avanzar_ia()
        traza.append((int(p.mision.paso), p.estado, round(float(p.rover.bateria), 2),
                      p.ambiente, int(p.ambiente_restante), int(p.enlace_restante)))
        if p.estado in ESTADOS_TERMINALES:
            break
    return {
        "resultados": resultados,
        "bateria_tras_eventos": bateria_tras_eventos,
        "avisos_tras_eventos": avisos_tras_eventos,
        "avisos": list(p.avisos),
        "motivos": [str(m) for m in p.bitacora().motivos],
        "vetos": int(p.mision.vetos),
        "sismos": len(p.sismos),
        "meteoritos": len(p.meteoritos),
        "traza": traza,
        "estado": p.estado,
        "bateria": float(p.rover.bateria),
    }


def _consistente(r):
    assert r["bateria"] >= 0.0
    if r["bateria"] <= 0.0:
        assert r["estado"] in ESTADOS_TERMINALES


@pytest.mark.parametrize("semilla", [3, 7, 11])
def test_triple_dos_corridas_mismo_orden_y_avisos(semilla):
    a = _corrida(TRIPLE, semilla, 40)
    b = _corrida(TRIPLE, semilla, 40)
    assert a == b


@pytest.mark.parametrize("semilla", [3, 11])
def test_par_tormenta_baja_conectividad_dos_corridas_iguales(semilla):
    assert _corrida(PAR, semilla, 12) == _corrida(PAR, semilla, 12)


def test_triple_orden_de_vetos_y_avisos_fijado_semilla_3():
    r = _corrida(TRIPLE, 3, 40)
    assert r["resultados"] == [("sismo", True), ("bateria_baja", True), ("meteorito", True)]
    assert r["avisos_tras_eventos"] == ["Sismo: grietas nuevas cerca del rover",
                                        "Meteorito: impacto en una zona de riesgo cercana"]
    assert r["avisos"] == r["avisos_tras_eventos"]
    # el sismo cae en la ruta (REPLAN-SISMO) y, en el primer paso, el veto por riesgo en la ruta
    assert r["motivos"][:3] == ["REPLAN-SISMO", "V-RUTA-CON-RIESGO", "OK"]
    assert r["vetos"] == 1


def test_triple_orden_semilla_7_termina_sin_ruta_tras_el_veto():
    r = _corrida(TRIPLE, 7, 40)
    assert r["motivos"] == ["REPLAN-SISMO", "V-RUTA-CON-RIESGO"]
    assert r["vetos"] == 1
    assert r["estado"] == "SIN_RUTA"
    assert r["avisos"] == ["Sismo: grietas nuevas cerca del rover",
                           "Meteorito: impacto en una zona de riesgo cercana"]
    _consistente(r)


@pytest.mark.parametrize("semilla", [3, 7, 11])
def test_triple_ningun_evento_se_pierde_ni_se_aplica_dos_veces(semilla):
    r = _corrida(TRIPLE, semilla, 40)
    assert [ok for _, ok in r["resultados"]] == [True, True, True]
    assert r["sismos"] == 1
    assert r["meteoritos"] == 1
    # cada aviso aparece una sola vez y en el orden en que se dispararon
    assert r["avisos"].count("Sismo: grietas nuevas cerca del rover") == 1
    assert r["avisos"].count("Meteorito: impacto en una zona de riesgo cercana") == 1
    assert r["avisos"].index("Sismo: grietas nuevas cerca del rover") \
        < r["avisos"].index("Meteorito: impacto en una zona de riesgo cercana")
    # batería: bateria_baja fija el valor y el meteorito resta su daño una sola vez, sin tick intermedio
    assert r["bateria_tras_eventos"] == BATERIA_BAJA - DANO_METEORITO
    assert r["motivos"].count("REPLAN-SISMO") <= 1


def test_el_orden_de_los_eventos_importa_y_es_el_de_las_llamadas():
    """Meteorito antes de batería baja: la batería final es BATERIA_BAJA (el valor se fija, no se resta)."""
    p = Partida(semilla=3, nivel=5)
    for e in ["sismo", "meteorito", "bateria_baja"]:
        assert p.disparar_evento(e)["ok"] is True
    assert float(p.rover.bateria) == BATERIA_BAJA
    assert p.avisos == ["Sismo: grietas nuevas cerca del rover", "Meteorito: impacto en una zona de riesgo cercana"]


@pytest.mark.parametrize("semilla", [3, 7, 11])
def test_triple_estado_consistente(semilla):
    _consistente(_corrida(TRIPLE, semilla, 60))


def test_par_tormenta_baja_conectividad_orden_y_cuentas_semilla_11():
    r = _corrida(PAR, 11, 8)
    assert r["resultados"] == [("tormenta", True), ("baja_conectividad", True)]
    assert r["avisos"] == ["Baja conectividad: sin enlace con la base"]
    assert r["vetos"] == 0
    # el enlace baja un paso por tick desde PASOS_SIN_ENLACE; la tormenta dura 6 pasos y su coste se descuenta cada tick
    assert PASOS_SIN_ENLACE == 4
    assert [t[5] for t in r["traza"]] == [3, 2, 1, 0, 0, 0, 0, 0]
    assert [(t[3], t[4]) for t in r["traza"]] == [("tormenta", 5), ("tormenta", 4), ("tormenta", 3), ("tormenta", 2),
                                                  ("tormenta", 1), ("normal", 0), ("normal", 0), ("normal", 0)]
    assert [t[2] for t in r["traza"]][:5] == [82.0, 80.0, 78.0, 76.0, 74.0]
    assert r["sismos"] == 0 and r["meteoritos"] == 0
    _consistente(r)


def test_par_no_aplica_dos_veces_el_aviso_de_enlace():
    p = Partida(semilla=11, nivel=5)
    p.disparar_evento("tormenta")
    p.disparar_evento("baja_conectividad")
    p.disparar_evento("baja_conectividad")      # repetido seguido: el aviso no se apila (N6)
    assert p.avisos == ["Baja conectividad: sin enlace con la base"]
    assert p.enlace_restante == PASOS_SIN_ENLACE
