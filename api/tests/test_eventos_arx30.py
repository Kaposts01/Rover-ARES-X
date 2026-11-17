"""ARX-30a: sismo con grietas en el motor y la API (POST /evento, tick espontáneo, regresión de meteoritos)."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app
from integracion import ESTADOS_TERMINALES
from juego.partida import PASOS_SIN_ENLACE, RUMBOS_JUGADOR, Partida, _alcanzables, _es_ganable
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
    # ARX-79: batería 84 explícita = la del nivel 5 antes del factor por tamaño; fija el generador (la lista no cambia)
    p = Partida(semilla=11, nivel=5, filas=40, columnas=60, bateria=84.0)
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
    # B3 (QA): con la sesión de la API, tras PASOS_SIN_ENLACE pasos el enlace vuelve y la orden deja de perderse
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    p = sesion.partida
    p._rng_enlace = _DadoFijo(0.0)           # mientras haya corte, toda orden se pierde
    cliente.post("/evento", json={"nombre": "baja_conectividad"})
    assert cliente.get("/estado").json()["enlace"] == {"activo": True, "restante": PASOS_SIN_ENLACE}
    for _ in range(PASOS_SIN_ENLACE):
        r = cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()
        assert r["movido"] is False and r["motivo"] == "sin enlace"
    assert cliente.get("/estado").json()["enlace"]["activo"] is False
    r = cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()
    assert r["movido"] is True               # con el dado en 0.0 una orden perdida seguiría fallando: ya no hay corte


def test_en_manual_movimiento_logrado_y_orden_perdida_avanzan_el_mismo_paso():
    # B1 (QA): ambos caminos suman un paso de misión y un turno de combate
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    p = sesion.partida
    paso0 = p.mision.paso
    assert cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()["movido"] is True
    assert p.mision.paso == paso0 + 1
    p._rng_enlace = _DadoFijo(0.0)
    cliente.post("/evento", json={"nombre": "baja_conectividad"})
    assert cliente.post("/mover", json={"rumbo": _rumbo_libre(p)}).json()["motivo"] == "sin enlace"
    assert p.mision.paso == paso0 + 2


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


# ---------- ARX-30c: señal biológica (ev3-d49 B: sitio obligatorio para ganar) ----------
def test_post_evento_acepta_senal_biologica():
    cliente = TestClient(crear_app(Sesion(semilla=11)))
    r = cliente.post("/evento", json={"nombre": "senal_biologica"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    estado = cliente.get("/estado").json()
    assert estado["senal"] == r.json()["celda"]


def test_la_senal_es_sitio_obligatorio_y_la_victoria_exige_visitarla():
    p = Partida(semilla=11, nivel=1)
    assert p.disparar_evento("senal_biologica")["ok"] is True
    celda = p.senales[0]["celda"]
    assert celda in p.mision.objetivos
    assert 3 <= max(abs(celda[0] - p.rover.posicion[0]), abs(celda[1] - p.rover.posicion[1])) <= 6
    # todos los sitios visitados y el rover en el refugio, pero la señal sin visitar: no hay EXITO
    p.mision.visitados = set(p.mundo.sitios)
    p.rover.posicion = tuple(p.mundo.refugio)
    p._actualizar_estado_tras_movimiento()
    assert p.estado != "EXITO"
    assert "señal 0/1" in p.objetivos_pendientes()
    # al pisar la celda queda visitada y deja de ser objetivo
    p.rover.posicion = tuple(celda)
    p._tick_ambiente()
    assert p.senales[0]["visitada"] is True and p.senal_activa is None
    assert celda not in p.mision.objetivos
    p.rover.posicion = tuple(p.mundo.refugio)
    p._actualizar_estado_tras_movimiento()
    assert p.estado == "EXITO"


def test_la_ia_pasa_por_la_senal_antes_de_ganar():
    p = Partida(semilla=11, nivel=1)
    for _ in range(3):
        p.avanzar_ia()
    assert p.disparar_evento("senal_biologica")["ok"] is True
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < 600:
        p.avanzar_ia()
        pasos += 1
    assert p.estado == "EXITO"
    assert p.senales[0]["visitada"] is True


def test_la_senal_no_afirma_vida_y_el_aviso_dice_no_confirma_vida():
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    cliente.post("/evento", json={"nombre": "senal_biologica"})
    ev = [e for e in cliente.get("/moviles").json()["eventos_del_paso"] if e.get("nombre") == "senal_biologica"]
    assert len(ev) == 1 and ev[0]["afirma_vida"] is False and ev[0]["efecto"] == "lectura_anomala"
    assert len(ev[0]["celdas"]) == 1
    aviso = [a for a in cliente.get("/estado").json()["avisos"] if "ñal" in a][-1]
    assert "no confirma vida" in aviso
    for texto in sesion.partida.avisos:
        assert "vida" not in texto or "no confirma vida" in texto


def test_partida_congelada_no_tiene_senales_espontaneas():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, garantia=False)
    for _ in range(3000):
        p._tick_ambiente()
    assert p.senales == []
    # la partida jugable sí las tiene desde ev3-d50 C (ver test_la_senal_cae_sola_en_los_niveles_1_a_5)


def test_arx66_con_la_senal_la_celda_es_alcanzable_y_la_partida_sigue_ganable():
    for semilla in (11, 5, 7):
        p = Partida(semilla=semilla, nivel=2)
        assert p.disparar_evento("senal_biologica")["ok"] is True
        celda = p.senales[0]["celda"]
        alcanzables = _alcanzables(p.mundo, tuple(p.rover.posicion))
        assert celda in alcanzables and tuple(p.mundo.refugio) in alcanzables
        assert all(tuple(s) in alcanzables for s in p.mundo.sitios)
        assert p._ganable_con_senal(celda)
        # la partida sigue siendo ganable en el origen (la misma comprobación de la garantía ARX-66)
        assert _es_ganable(p.mundo, p.rover.bateria, bateria_max=p.bateria_max, estaciones=p.estaciones,
                           factor=p.mision.factor_ambiente)


def test_senal_en_estado_terminal_responde_ok_false():
    p = Partida(semilla=11, nivel=1)
    p.mision.estado = "FRACASO"
    r = p.disparar_evento("senal_biologica")
    assert r["ok"] is False and p.senales == []


class _DadoSenal:
    """random() siempre 0.0 (la señal siempre cae) y el resto del generador real (permutation)."""

    def __init__(self, rng):
        self._rng = rng

    def random(self):
        return 0.0

    def permutation(self, n):
        return self._rng.permutation(n)


# ---------- ARX-30c ajuste: señal espontánea en todos los niveles (ev3-d50 C) y reglas de ev3-d51 A ----------
SEMILLA_SENAL = 11
TICKS_SENAL = 1500     # con la semilla 11 y 1500 ticks de _tick_ambiente cae al menos una señal en cada nivel


def _senales_espontaneas(nivel, garantia=True):
    p = Partida(semilla=SEMILLA_SENAL, nivel=nivel, garantia=garantia)
    bat0 = p.rover.bateria
    for _ in range(TICKS_SENAL):
        p.rover.bateria = bat0      # el rover no conduce: se repone para que la partida no termine
        p._tick_ambiente()
        if p.senal_activa is not None:      # el rover no se mueve: se libera para contar nuevas caídas
            p.senales[-1]["visitada"] = True
    return p


def test_la_senal_cae_sola_en_los_niveles_1_a_5():
    for nivel in (1, 2, 3, 4, 5):
        p = _senales_espontaneas(nivel)
        assert len(p.senales) >= 1, f"nivel {nivel}: sin señal espontánea"


def test_la_senal_no_cae_sola_sin_garantia():
    for nivel in (1, 5):
        assert _senales_espontaneas(nivel, garantia=False).senales == []


def _partida_con_un_solo_pendiente():
    p = Partida(semilla=11, nivel=1)
    p.mision.visitados = set(list(p.mundo.sitios)[:-1])
    assert len([s for s in p.mundo.sitios if s not in p.mision.visitados]) == 1
    return p


def test_la_senal_se_rechaza_si_queda_un_solo_objetivo():
    p = _partida_con_un_solo_pendiente()
    r = p.disparar_evento("senal_biologica")
    assert r["ok"] is False and "un solo objetivo" in r["detalle"] and p.senales == []
    # por la API, el mismo motivo y sin cambios
    sesion = Sesion(semilla=11)
    sesion.partida.mision.visitados = set(list(sesion.partida.mundo.sitios)[:-1])
    r = TestClient(crear_app(sesion)).post("/evento", json={"nombre": "senal_biologica"}).json()
    assert r["ok"] is False and "un solo objetivo" in r["detalle"] and sesion.partida.senales == []
    # la espontánea tampoco se crea
    p._rng_senal = _DadoSenal(p._rng_senal)
    p._tick_ambiente()
    assert p.senales == []


def test_la_senal_se_rechaza_si_la_bateria_no_alcanza():
    p = Partida(semilla=11, nivel=1)
    assert len([s for s in p.mundo.sitios if s not in p.mision.visitados]) >= 2
    p.rover.bateria = 6
    r = p.disparar_evento("senal_biologica")
    assert r["ok"] is False and "batería insuficiente" in r["detalle"] and p.senales == []
    assert p.senal_activa is None
    p._rng_senal = _DadoSenal(p._rng_senal)
    p._tick_ambiente()
    assert p.senales == []


def test_arx66_muy_facil_y_facil_con_la_senal_espontanea_siguen_ganables():
    for nivel in (1, 2):
        p = _senales_espontaneas(nivel)
        assert p.senales, f"nivel {nivel}"
        q = Partida(semilla=SEMILLA_SENAL, nivel=nivel)
        assert q.disparar_evento("senal_biologica")["ok"] is True
        assert q._ganable_con_senal(q.senales[0]["celda"])
        assert _es_ganable(q.mundo, q.rover.bateria, bateria_max=q.bateria_max, estaciones=q.estaciones,
                           factor=q.mision.factor_ambiente)


# ---------- ARX-30c (QA C1): la ganabilidad de la señal cuenta la caza de drones y el meteorito ----------
def _sesion_automatica(semilla, nivel, eventos):
    sesion = Sesion(semilla=semilla, nivel=nivel)
    app = crear_app(sesion)
    cliente = TestClient(app)
    cliente.post("/partida", json={"semilla": semilla, "nivel": nivel, "tamano": "pequeno"})
    cliente.post("/modo", json={"modo": "automatico", "veto": True})
    app.state.sesion.partida.eventos_activos = tuple(eventos)
    return app, cliente


def _jugar(app, cliente, senal_en=None):
    for n in range(700):
        if n == senal_en:
            cliente.post("/evento", json={"nombre": "senal_biologica"})
        estado = cliente.post("/paso").json().get("estado")
        if estado in ESTADOS_TERMINALES:
            return estado
    return estado


import pytest


@pytest.mark.parametrize("semilla,nivel", [(5, 3), (6, 5)])
def test_senal_con_drones_obligatorios_no_deja_sin_ganar_las_repros_de_qa(semilla, nivel):
    # Repros de QA (fracaso9): semilla 5 nivel 3 y semilla 6 nivel 5, señal forzada en el paso 3, todos los eventos
    from juego.partida import EVENTOS_SOPORTADOS
    app, cliente = _sesion_automatica(semilla, nivel, EVENTOS_SOPORTADOS)
    assert _jugar(app, cliente, None) == "EXITO"            # sin señal: se gana (línea base)
    app, cliente = _sesion_automatica(semilla, nivel, EVENTOS_SOPORTADOS)
    assert _jugar(app, cliente, 3) == "EXITO"               # con señal: se gana (la señal se acepta o se rechaza)


@pytest.mark.parametrize("nivel", [3, 5])
def test_ninguna_senal_aceptada_con_drones_deja_sin_ganar(nivel):
    from juego.partida import EVENTOS_SOPORTADOS
    for semilla in range(1, 7):
        for paso_senal in (3, 10, 20):
            app, cliente = _sesion_automatica(semilla, nivel, EVENTOS_SOPORTADOS)
            assert _jugar(app, cliente, paso_senal) == "EXITO", (semilla, nivel, paso_senal)


def _celda_alcanzable(p):
    """Una celda alcanzable a distancia Chebyshev >= 3 del rover, distinta de sitios, refugio y estaciones."""
    r = tuple(p.rover.posicion)
    for c in sorted(_alcanzables(p.mundo, r)):
        if (max(abs(c[0] - r[0]), abs(c[1] - r[1])) >= 3 and c not in p.mundo.sitios
                and c != tuple(p.mundo.refugio) and c not in p.estaciones):
            return (int(c[0]), int(c[1]))
    raise AssertionError("sin celda alcanzable")


def _bateria_minima(p, celda):
    """Batería mínima (pasos de 0,5) con la que _ganable_con_senal acepta la celda en el estado actual de p."""
    b = 1.0
    while b < 300:
        p.rover.bateria = b
        if p._ganable_con_senal(celda):
            return b
        b += 0.5
    raise AssertionError("nunca ganable")


def test_ganable_con_senal_cuenta_la_caza_de_los_drones_vivos():
    from juego.partida import MARGEN_CAZA
    app, cliente = _sesion_automatica(5, 3, ("senal_biologica",))
    p = app.state.sesion.partida
    celda = _celda_alcanzable(p)
    assert p.combate is not None and any(d.vivo for d in p.combate.drones)
    p.bateria_max = 300.0                                  # sin paradas en estaciones: solo cuenta la ruta
    p.estaciones = []
    con_drones = _bateria_minima(p, celda)
    for d in p.combate.drones:
        d.estado = "muerto"
    sin_drones = _bateria_minima(p, celda)
    assert con_drones > sin_drones            # la caza se cuenta: ruta a cada dron + MARGEN_CAZA por dron
    assert con_drones - sin_drones >= MARGEN_CAZA


def test_ganable_con_senal_reserva_el_dano_del_meteorito():
    from juego.partida import DANO_METEORITO
    app, cliente = _sesion_automatica(5, 1, ("senal_biologica",))
    p = app.state.sesion.partida
    celda = _celda_alcanzable(p)
    p.bateria_max = 300.0
    p.estaciones = []
    sin = _bateria_minima(p, celda)
    p.eventos_activos = ("senal_biologica", "meteorito")
    con = _bateria_minima(p, celda)
    assert con - sin == pytest.approx(DANO_METEORITO, abs=0.5)
