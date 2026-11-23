"""R23b: la partida en vivo (híbrido, automático) y el lado «hibrido» de /comparar con la misma configuración dan la misma trayectoria,
los mismos pasos de la misión, la misma ciencia y el mismo puntaje. Antes la tabla contaba turnos de la API (un disparo ocupa un turno sin
avanzar la misión) y decía 181 donde la pantalla final decía 175."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import app  # noqa: E402

CONFIG = {"semilla": 7, "nivel": 4, "tamano": "pequeno", "planeta": "Marte", "modo": "rover"}
TERMINALES = ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO")


def _vivo(c):
    assert c.post("/partida", json=CONFIG).status_code == 200
    c.post("/modo", json={"modo": "automatico"})
    tray = []
    for _ in range(600):
        r = c.post("/paso").json()
        e = c.get("/estado").json()
        tray.append((tuple(e["posicion"]), r["accion"]))
        if e["estado"] in TERMINALES:
            break
    return e, tray


def test_la_misma_semilla_da_la_misma_trayectoria_en_vivo_y_en_la_comparacion():
    c = TestClient(app)
    e, tray = _vivo(c)
    r = c.post("/comparar", json={**CONFIG, "politica_a": "hibrido", "politica_b": "hibrido"}).json()
    while not r["tabla"]:
        r = c.post(f"/comparar/{r['id']}/avanzar", json={"pasos": 60}).json()
    completo = c.get(f"/comparar/{r['id']}").json()
    for lado in completo["lados"]:
        # los lados traen solo desde donde se pidió: se pide todo con GET (desde 0)
        assert [(tuple(f["posicion"]), f["accion"]) for f in lado["pasos"]] == tray
        ultima = lado["pasos"][-1]
        assert ultima["paso"] == e["paso"]                              # el paso de la misión, el de la pantalla final
        assert ultima["puntaje"] == e["puntaje"]
        assert ultima["ciencia_fraccion"] == e["ciencia_fraccion"]
        assert ultima["sitios_visitados"] == e["sitios_visitados"]
    filas = {f["clave"]: f for f in r["tabla"]["filas"]}
    assert filas["pasos"]["a"] == filas["pasos"]["b"] == e["paso"]
    assert filas["puntaje"]["a"] == e["puntaje"] and filas["ciencia_fraccion"]["a"] == e["ciencia_fraccion"]
    assert filas["vetos"]["ganador"] is None and filas["vetos"]["informativa"]      # un veto no es mérito ni demérito
    assert len(tray) >= e["paso"]                                                   # los turnos pueden exceder a los pasos (disparos)


def test_sitios_visitados_y_ciencia_recogida_son_datos_distintos():
    c = TestClient(app)
    e, _ = _vivo(c)
    assert e["sitios_visitados"] == e["sitios_totales"]       # visitó todos los sitios (obligatorios y opcionales)...
    assert e["ciencia_fraccion"] < 1.0                        # ...pero parte con la ventana perdida: la ciencia vale menos
    assert abs(e["ciencia_recogida"] / e["ciencia_maxima"] - e["ciencia_fraccion"]) < 1e-3
