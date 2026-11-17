"""ARX-30a: sismo con grietas en el motor y la API (POST /evento, tick espontáneo, regresión de meteoritos)."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app
from juego.partida import PASOS_SIN_ENLACE, RUMBOS_JUGADOR, Partida, _alcanzables
from simulador import BARRANCO, LIBRE

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


# ---------- ARX-30b: baja conectividad (ev3-d48 A) ----------
class _DadoFijo:
    """Generador de pruebas: random() devuelve siempre el mismo valor (0.0 = la orden siempre se pierde)."""

    def __init__(self, valor):
        self.valor = valor

    def random(self):
        return self.valor


def _rumbo_libre(p):
    f, c = p.rover.posicion
    for rumbo, (df, dc) in RUMBOS_JUGADOR.items():
        d = (f + df, c + dc)
        if p.mundo.dentro(d) and p.mundo.tipo[d] == LIBRE:
            return rumbo
    raise AssertionError("sin rumbo libre")


def test_post_evento_acepta_baja_conectividad():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    r = cliente.post("/evento", json={"nombre": "baja_conectividad"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert cliente.get("/estado").json()["enlace"] == {"activo": True, "restante": PASOS_SIN_ENLACE}
    ev = cliente.get("/moviles").json()["eventos_del_paso"]
    assert {"nombre": "baja_conectividad", "efecto": "sin_enlace", "restante": PASOS_SIN_ENLACE} in ev


def test_con_enlace_cortado_en_manual_la_orden_se_pierde():
    # Caso fijado: el generador del enlace se sustituye por un dado que siempre da 0.0 (< PROB_ORDEN_PERDIDA)
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    p = sesion.partida
    p._rng_enlace = _DadoFijo(0.0)
    cliente.post("/evento", json={"nombre": "baja_conectividad"})
    pos = list(p.rover.posicion)
    r = cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()
    assert r["movido"] is False and r["motivo"] == "sin enlace"
    assert list(p.rover.posicion) == pos
    # con el dado en 0.99 la orden llega
    p._rng_enlace = _DadoFijo(0.99)
    assert cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()["movido"] is True


def test_con_enlace_cortado_la_ia_sigue_pero_recomendacion_e_intervencion_dan_409():
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    sesion.partida.modo_ia = "automatico"
    cliente.post("/evento", json={"nombre": "baja_conectividad"})
    assert cliente.get("/recomendacion").status_code == 409
    r = cliente.post("/intervencion", json={"tecnica": "apagar"})
    assert r.status_code == 409 and "sin enlace" in r.json()["motivo"]
    sesion.partida.avanzar_ia()      # el rover de IA sigue avanzando
    assert sesion.partida.mision.paso == 1


def test_el_enlace_vuelve_tras_los_pasos_sin_enlace():
    p = Partida(semilla=11, nivel=1, garantia=False)
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    cliente.post("/evento", json={"nombre": "baja_conectividad"})
    for _ in range(PASOS_SIN_ENLACE):
        assert cliente.get("/estado").json()["enlace"]["activo"] is True
        sesion.partida._tick_ambiente()
    assert cliente.get("/estado").json()["enlace"] == {"activo": False, "restante": 0}
    assert p.enlace_restante == 0


def test_partida_congelada_no_tiene_cortes_de_enlace_espontaneos():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, garantia=False)
    for _ in range(3000):
        p._tick_ambiente()
        assert p.enlace_restante == 0


def test_partida_jugable_tiene_cortes_espontaneos_con_generador_propio():
    # La partida termina por batería tras unos cientos de ticks (sin conducir), así que se suman varias semillas.
    vistos = 0
    for semilla in range(1, 9):
        p = Partida(semilla=semilla, nivel=5, filas=20, columnas=30)
        for _ in range(3000):
            antes = p.enlace_restante
            p._tick_ambiente()
            vistos += p.enlace_restante == PASOS_SIN_ENLACE and antes == 0
    assert vistos > 0
