"""ARX-30a: sismo con grietas en el motor y la API (POST /evento, tick espontáneo, regresión de meteoritos)."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app
from juego.partida import Partida, _alcanzables
from simulador import BARRANCO

# Línea base medida en main antes de ARX-30a (Partida(semilla=11, nivel=5, 40x60), 3000 llamadas a _tick_ambiente)
TICKS_METEORITOS_BASE = [16, 84, 114, 150, 176, 248, 263, 368]


def test_post_evento_acepta_sismo():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    r = cliente.post("/evento", json={"nombre": "sismo"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_sismo_deja_las_grietas_como_barranco_con_riesgo_1():
    p = Partida(semilla=11, nivel=5)
    r = p.disparar_evento("sismo")
    assert r["ok"] is True
    grietas = [tuple(g) for g in p.sismos[-1]["grietas"]]
    assert 1 <= len(grietas) <= 3
    for g in grietas:
        assert p.mundo.tipo[g] == BARRANCO
        assert p.mision.riesgo[g] == 1.0
        assert 2 <= max(abs(g[0] - p.rover.posicion[0]), abs(g[1] - p.rover.posicion[1])) <= 4


def test_sismo_deja_refugio_y_sitios_pendientes_alcanzables():
    p = Partida(semilla=11, nivel=5)
    for _ in range(3):
        p.disparar_evento("sismo")
    alcanzables = _alcanzables(p.mundo, tuple(p.rover.posicion))
    assert tuple(p.mundo.refugio) in alcanzables
    assert all(tuple(s) in alcanzables for s in p.mundo.sitios if s not in p.mision.visitados)


def test_partida_congelada_no_tiene_sismos_espontaneos():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, garantia=False)
    for _ in range(3000):
        p._tick_ambiente()
    assert p.sismos == []


def test_regresion_ticks_de_meteoritos_no_cambian_con_el_sismo():
    p = Partida(semilla=11, nivel=5, filas=40, columnas=60)
    ticks = []
    for k in range(3000):
        antes = len(p.meteoritos)
        p._tick_ambiente()
        if len(p.meteoritos) > antes:
            ticks.append(k)
    assert ticks == TICKS_METEORITOS_BASE
