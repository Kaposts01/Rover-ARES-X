"""ARX-30: meteorito: impacto con zona de riesgo y coste de batería, expuesto por POST /evento."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app
from juego.partida import DANO_METEORITO, Partida


def test_meteorito_marca_zona_de_riesgo_y_cuesta_bateria():
    p = Partida(semilla=11, nivel=1)
    bateria_antes = p.rover.bateria
    r = p.disparar_evento("meteorito")
    assert r["ok"] is True
    impacto = tuple(int(v) for v in r["impacto"])
    assert p.mision.riesgo[impacto] == 1.0
    assert p.rover.bateria == bateria_antes - DANO_METEORITO
    assert max(abs(impacto[0] - p.rover.posicion[0]), abs(impacto[1] - p.rover.posicion[1])) >= 2


def test_post_evento_acepta_meteorito():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    r = cliente.post("/evento", json={"nombre": "meteorito"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_partida_congelada_no_tiene_meteoritos_espontaneos():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, garantia=False)
    for _ in range(3000):
        p._tick_ambiente()
    assert p.meteoritos == []


def test_meteoritos_caen_solos_en_la_partida_jugable_de_nivel_alto():
    p = Partida(semilla=11, nivel=5, filas=40, columnas=60)
    for _ in range(3000):
        p._tick_ambiente()
    assert len(p.meteoritos) > 0
    assert all(m["zona_riesgo"][0] == m["impacto"] for m in p.meteoritos)


def test_moviles_emite_el_meteorito_con_el_formato_de_la_interfaz():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    cliente.post("/evento", json={"nombre": "meteorito"})
    datos = cliente.get("/moviles").json()
    meteoritos = [m for m in datos["moviles"] if m["tipo"] == "meteorito"]
    assert len(meteoritos) == 1
    assert meteoritos[0]["impacto"] is True
    assert 2 <= len(meteoritos[0]["trayectoria"]) <= 3
    assert meteoritos[0]["trayectoria"][-1] == meteoritos[0]["pos"]
    assert len(meteoritos[0]["zona_riesgo"]) >= 1
    eventos = [e for e in datos["eventos_del_paso"] if e.get("nombre") == "meteorito"]
    assert eventos and eventos[0]["efecto"] == "zona_riesgo" and eventos[0]["celdas"]


def test_avisos_repetidos_seguidos_no_se_apilan():
    p = Partida(semilla=11, nivel=1)
    p._avisar("Faltan drones: 1 vivo")
    p._avisar("Faltan drones: 1 vivo")
    assert p.avisos.count("Faltan drones: 1 vivo") == 1
