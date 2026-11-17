"""ARX-79c: la caza que no avanza termina con aviso y FRACASO con causa (repro QA: semilla 6, nivel 5, pequeño)."""
from fastapi.testclient import TestClient

from api.servidor import ESTADOS_TERMINALES, Sesion, crear_app
from juego.partida import EVENTOS_SOPORTADOS, PASOS_CAZA_SIN_AVANCE, Partida


def test_caza_parada_termina_con_causa(monkeypatch):
    # la señal se acepta como en b044853 (hoy la garantía la rechaza); con ella la caza queda parada en (2, 3)
    monkeypatch.setattr(Partida, "_ganable_con_senal", lambda self, celda: True)
    app = crear_app(Sesion(semilla=6, nivel=5))
    cl = TestClient(app)
    cl.post("/partida", json={"semilla": 6, "nivel": 5, "tamano": "pequeno"})
    cl.post("/modo", json={"modo": "automatico", "veto": True})
    app.state.sesion.partida.eventos_activos = tuple(EVENTOS_SOPORTADOS)
    for _ in range(3):
        cl.post("/paso")
    assert cl.post("/evento", json={"nombre": "senal_biologica"}).json()["ok"]
    estado = None
    for n in range(700):
        estado = cl.post("/paso").json().get("estado")
        if estado in ESTADOS_TERMINALES:
            break
    p = app.state.sesion.partida
    assert estado == "FRACASO" and n < 150                      # termina, no se queda repitiendo
    assert any("la caza no avanza" in a for a in p.avisos)
    assert PASOS_CAZA_SIN_AVANCE >= 6                           # deja pasar al menos dos ciclos de parada del difuso
