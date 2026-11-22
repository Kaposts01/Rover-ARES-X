"""ARX-79c: la caza que no avanza termina con aviso y FRACASO con causa (repro QA: semilla 6, nivel 5, pequeño)."""
from fastapi.testclient import TestClient

from api.servidor import ESTADOS_TERMINALES, Sesion, crear_app
from juego.partida import PASOS_CAZA_SIN_AVANCE


def test_caza_parada_termina_con_causa():
    # ARX-94f: el repro de QA (semilla 6, señal aceptada) dependía del mapa v1; con el mundo v2 ninguna semilla 1-59
    # deja la caza atascada sola. Se provoca la misma causa sin depender del mapa: sitios ya visitados (empieza la
    # caza) y el difuso forzado a velocidad 0 (el rover no sale de su celda y el BFS vuelve a trazar la misma ruta).
    app = crear_app(Sesion(semilla=6, nivel=5))
    cl = TestClient(app)
    cl.post("/partida", json={"semilla": 6, "nivel": 5, "tamano": "pequeno"})
    cl.post("/modo", json={"modo": "automatico", "veto": True})
    p = app.state.sesion.partida
    assert p.drones_obligatorios() and any(d.vivo for d in p.combate.drones)
    p.mision.visitados = {tuple(s) for s in p.mundo.sitios}
    p.mision.intervencion_difuso = 0.0
    estado = None
    for n in range(700):
        estado = cl.post("/paso").json().get("estado")
        if estado in ESTADOS_TERMINALES:
            break
    assert estado == "FRACASO" and n < 150                      # termina, no se queda repitiendo
    assert any("la caza no avanza" in a for a in p.avisos)
    assert PASOS_CAZA_SIN_AVANCE >= 6                           # deja pasar al menos dos ciclos de parada del difuso
