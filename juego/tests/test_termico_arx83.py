"""ARX-83a: temperatura interna y aborto térmico (solo con garantia=True y con la bandera encendida)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego import termico  # noqa: E402
from juego.partida import Partida  # noqa: E402


@pytest.fixture
def bandera(monkeypatch):
    monkeypatch.setattr(termico, "ABORTO_TERMICO_ACTIVO", True)


def _al_sol(p):
    """Coloca al rover en una celda libre que no sea sombra (ni refugio ni junto a barranco u obstáculo)."""
    for f in range(p.mundo.tipo.shape[0]):
        for c in range(p.mundo.tipo.shape[1]):
            if p.mundo.tipo[f, c] == 0 and not termico.es_sombra(p.mundo, (f, c)):
                p.rover.posicion = (f, c)
                return
    raise AssertionError("no hay celda al sol")


def _quieta(planeta, **kw):
    return Partida(semilla=11, planeta=planeta, eventos_activos=(), **kw)


def test_bandera_apagada_por_defecto_y_sin_efecto():
    assert termico.ABORTO_TERMICO_ACTIVO is False
    p = _quieta("Venus")
    _al_sol(p)
    for _ in range(40):
        p._tick_ambiente()
    assert p.t_int > termico.TOLERANCIA and p.estado not in ("MODO_SEGURO",)   # T_int se calcula, nada aborta


def test_marte_se_mantiene_bajo_la_tolerancia_en_400_pasos(bandera):
    p = _quieta("Marte")
    _al_sol(p)
    for _ in range(400):
        p._tick_ambiente()
        assert p.t_int < termico.TOLERANCIA
    assert p.estado not in ("MODO_SEGURO",)


def test_venus_al_sol_aborta_al_sexto_paso_sobre_la_tolerancia(bandera):
    p = _quieta("Venus")
    _al_sol(p)
    pasos = 0
    while p.estado != "MODO_SEGURO" and pasos < 60:
        p.mision.paso += 1
        p._tick_ambiente()
        pasos += 1
    assert p.estado == "MODO_SEGURO" and p.pasos_sobre_tolerancia == 6
    assert "V-TEMPERATURA" in set(p.bitacora()["motivos"])
    assert any("Aborto térmico" in a for a in p.avisos)


def test_en_sombra_t_int_baja(bandera):
    p = _quieta("Venus")
    _al_sol(p)
    for _ in range(5):
        p._tick_ambiente()
    alta = p.t_int
    p.rover.posicion = tuple(p.mundo.refugio)          # el refugio es sombra
    p._tick_ambiente()
    assert p.t_int < alta


def test_garantia_falsa_no_usa_temperatura_y_r10_aparece_con_garantia(bandera):
    sin = Partida(semilla=11, planeta="Venus", garantia=False)
    assert "inferir" not in vars(sin.mision.difuso)            # el difuso sigue recibiendo 0,0
    _al_sol(sin)
    for _ in range(30):
        sin._tick_ambiente()
    assert sin.t_int == termico.T_INT_INICIAL and sin.estado != "MODO_SEGURO"
    con = Partida(semilla=11, planeta="Marte", eventos_activos=())
    for _ in range(3):
        con.avanzar_ia()
    assert any("R10" in str(r) for r in con.bitacora()["reglas"])      # T_int inicial 20 °C ya es «caliente» en parte


def test_determinismo_de_la_serie_t_int():
    def serie():
        p = Partida(semilla=11, planeta="Venus")
        out = []
        for _ in range(15):
            p.avanzar_ia()
            out.append(round(p.t_int, 9))
        return out
    assert serie() == serie()


@pytest.mark.parametrize("planeta", ["Saturno", "Urano", "Neptuno", "Júpiter"])
def test_planeta_sin_modelo_termico_deja_termico_inactivo(bandera, planeta):
    p = Partida(semilla=11, planeta=planeta)                  # no lanza ValueError
    assert p.termico.activo is False
    _al_sol(p)
    for _ in range(40):
        p.avanzar_ia()
    assert p.t_int == termico.T_INT_INICIAL and p.pasos_sobre_tolerancia == 0
    assert "V-TEMPERATURA" not in set(p.bitacora()["motivos"])
