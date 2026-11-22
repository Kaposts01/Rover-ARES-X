"""R23: la API expone las mecánicas del planeta, la temperatura de la sonda y el panel de IA en los modos sueltos."""
import pytest
from fastapi.testclient import TestClient

from api.servidor import crear_app


def _cliente():
    app = crear_app()
    return TestClient(app), app


def test_estado_trae_planeta_mecanicas_y_tolerancia_fria():
    c, _ = _cliente()
    e = c.post("/partida", json={"semilla": 3, "nivel": 3, "tamano": "pequeno", "planeta": "Marte"}).json()
    m = e["planeta_mecanicas"]
    assert m["perfil"]["nombre"] == "Marte" and m["perfil"]["gravedad_g"] == 0.38
    assert m["estado"]["activa"] is True and "viento" in m["estado"] and "rumbo_viento" in m["estado"]
    assert e["tolerancia_fria"] == -40.0


def test_planetas_lista_las_mecanicas_de_cada_uno():
    c, _ = _cliente()
    c.post("/partida", json={"semilla": 3, "tamano": "pequeno"})
    lista = {p["nombre"]: p for p in c.get("/planetas").json()["planetas"]}
    assert lista["Neptuno"]["mecanicas"]["viento"] > lista["Marte"]["mecanicas"]["viento"]
    assert all("hielo_fraccion" in p["mecanicas"] for p in lista.values())


def test_hielo_devuelve_celdas_para_el_mapa():
    c, _ = _cliente()
    c.post("/partida", json={"semilla": 3, "nivel": 2, "tamano": "pequeno", "planeta": "Neptuno", "modo": "sonda"})
    h = c.get("/hielo").json()
    assert h["planeta"] == "Neptuno" and len(h["celdas"]) > 20
    assert all(len(x) == 2 for x in h["celdas"])


def test_sonda_en_neptuno_la_temperatura_interna_cambia():
    c, _ = _cliente()
    c.post("/partida", json={"semilla": 3, "nivel": 2, "tamano": "pequeno", "planeta": "Neptuno", "modo": "sonda"})
    c.post("/modo", json={"modo": "automatico"})
    serie = []
    for _ in range(6):
        c.post("/paso")
        serie.append(c.get("/estado").json()["temperatura_interna"])
    assert len(set(serie)) == 6 and serie[0] < 20.0               # antes valía 20,0 en todos los pasos


@pytest.mark.parametrize("modo", ["rna", "difuso", "ag", "automatico"])
def test_ia_paso_funciona_en_todos_los_modos(modo):
    c, _ = _cliente()
    c.post("/partida", json={"semilla": 3, "nivel": 1, "tamano": "pequeno"})
    c.post("/modo", json={"modo": modo})
    for _ in range(3):
        c.post("/paso")
    r = c.get("/ia/paso").json()
    assert r["hay_paso"] is True and r["celda"] and r["paso_ia"] >= 1
