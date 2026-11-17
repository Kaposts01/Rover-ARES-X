"""Pruebas de la API (ARX-03) con TestClient. Criterios 1, 2, 3 y 8 de docs/SPEC_MVP_3D.md."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.servidor import Sesion, crear_app  # noqa: E402
from simulador import OBSTACULO  # noqa: E402


@pytest.fixture
def cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


def _app_con_sesion(cliente):
    return cliente.app.state.sesion


def test_estado_inicial_en_el_inicio_con_bateria_completa(cliente):
    # Criterio 1
    r = cliente.get("/estado")
    assert r.status_code == 200
    datos = r.json()
    assert datos["posicion"] == [19, 0]
    assert datos["bateria"] == 100.0
    # ARX-33a: en el paso 0 el estado visible es CONFIGURACION (antes EXPLORACION)
    assert datos["estado"] == "CONFIGURACION"


def test_post_partida_crea_nueva_y_valida_nivel(cliente):
    r = cliente.post("/partida", json={"semilla": 7, "nivel": 2})
    assert r.status_code == 200
    assert r.json()["semilla"] == 7 and r.json()["nivel"] == 2
    r = cliente.post("/partida", json={"semilla": 7, "nivel": 9})
    assert r.status_code == 400
    assert "motivo" in r.json() and "Traceback" not in r.text


def test_criterio_2_automatico_llega_a_exito_sin_colisiones(cliente):
    # Criterio 2
    assert cliente.post("/modo", json={"modo": "automatico"}).status_code == 200
    for _ in range(400):
        r = cliente.post("/paso").json()
        if r["estado"] in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
    final = cliente.get("/estado").json()
    assert final["estado"] == "EXITO"
    assert final["colisiones"] == 0
    assert final["barrancos_pisados"] == 0


def test_criterio_3_diagonal_bloqueada_devuelve_motivo(cliente):
    # Criterio 3: pone un obstáculo en la diagonal NE del rover y trata de moverse hacia allí
    sesion = _app_con_sesion(cliente)
    f, c = sesion.partida.rover.posicion
    destino = (f - 1, c + 1)
    sesion.partida.mundo.tipo[destino] = OBSTACULO
    r = cliente.post("/mover", json={"rumbo": "NE"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["movido"] is False
    assert isinstance(datos["motivo"], str) and datos["motivo"]


def test_mover_valido_cambia_la_posicion(cliente):
    antes = cliente.get("/estado").json()["posicion"]
    r = cliente.post("/mover", json={"rumbo": "N"})
    assert r.status_code == 200
    despues = cliente.get("/estado").json()["posicion"]
    assert r.json()["movido"] is True
    assert despues != antes


def test_mover_rumbo_invalido_es_400(cliente):
    r = cliente.post("/mover", json={"rumbo": "X"})
    assert r.status_code == 400
    assert "motivo" in r.json()
    assert "Traceback" not in r.text


def test_paso_devuelve_accion_y_motivos(cliente):
    r = cliente.post("/paso")
    assert r.status_code == 200
    datos = r.json()
    assert "accion" in datos and "motivos" in datos and "estado" in datos


def test_modo_invalido_es_400_y_valido_se_guarda(cliente):
    assert cliente.post("/modo", json={"modo": "volar"}).status_code == 400
    r = cliente.post("/modo", json={"modo": "rna"})
    assert r.status_code == 200
    assert r.json()["modo"] == "rna"


def test_disparo_respeta_cooldown_y_municion(cliente):
    r1 = cliente.post("/disparo", json={"rumbo": "N"})
    assert r1.status_code == 200
    assert r1.json()["municion"] == 9
    r2 = cliente.post("/disparo", json={"rumbo": "N"})
    assert r2.status_code == 409
    assert "cooldown" in r2.json()["motivo"]


def test_disparo_sin_municion_es_409(cliente):
    sesion = _app_con_sesion(cliente)
    sesion.combate.municion = 0
    r = cliente.post("/disparo", json={"rumbo": "E"})
    assert r.status_code == 409
    assert "munición" in r.json()["motivo"]


def test_disparo_rumbo_invalido_es_400(cliente):
    assert cliente.post("/disparo", json={"rumbo": "Z"}).status_code == 400


def test_evento_valido_y_desconocido(cliente):
    r = cliente.post("/evento", json={"nombre": "barranco"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    r = cliente.post("/evento", json={"nombre": "volcan"})
    assert r.status_code == 400
    assert "motivo" in r.json()


def test_paneles_devuelven_entradas_y_salidas(cliente):
    r = cliente.get("/paneles")
    assert r.status_code == 200
    datos = r.json()
    assert {"rna", "difuso", "ag", "supervisor", "intervencion", "paso"} <= set(datos)
    assert "p_barranco" in datos["rna"]
    assert "velocidad" in datos["difuso"]


def test_intervencion_rna_se_aplica_a_la_mision(cliente):
    r = cliente.post("/intervencion", json={"tecnica": "rna", "valor": "barranco"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "tecnica": "rna", "valor": "barranco"}
    assert _app_con_sesion(cliente).partida.mision.intervencion_rna is not None


def test_intervencion_difuso_acepta_0_a_1_y_rechaza_fuera_de_rango(cliente):
    assert cliente.post("/intervencion", json={"tecnica": "difuso", "valor": 0.5}).status_code == 200
    assert _app_con_sesion(cliente).partida.mision.intervencion_difuso == 0.5
    r = cliente.post("/intervencion", json={"tecnica": "difuso", "valor": 1.5})
    assert r.status_code == 400
    assert "motivo" in r.json()


def test_intervencion_entradas_invalidas_son_400(cliente):
    assert cliente.post("/intervencion", json={"tecnica": "rna", "valor": "volar"}).status_code == 400
    assert cliente.post("/intervencion", json={"tecnica": "otra", "valor": 1}).status_code == 400
    assert cliente.post("/intervencion", json={"tecnica": "difuso", "valor": True}).status_code == 400


def test_intervencion_apagar_restablece_la_mision(cliente):
    cliente.post("/intervencion", json={"tecnica": "difuso", "valor": 0.0})
    r = cliente.post("/intervencion", json={"tecnica": "apagar"})
    assert r.status_code == 200
    mision = _app_con_sesion(cliente).partida.mision
    assert mision.intervencion_rna is None and mision.intervencion_difuso is None


def test_409_cuando_la_partida_ya_termino(cliente):
    # Criterio 8: una partida terminada no acepta más pasos ni movimientos
    cliente.post("/modo", json={"modo": "automatico"})
    for _ in range(400):
        if cliente.post("/paso").json()["estado"] in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
    assert cliente.post("/paso").status_code == 409
    r = cliente.post("/mover", json={"rumbo": "N"})
    assert r.status_code == 409
    assert "motivo" in r.json()


def test_ningun_error_expone_traceback(cliente):
    casos = [
        ("post", "/mover", {"rumbo": "??"}),
        ("post", "/mover", {}),
        ("post", "/modo", {"modo": 3}),
        ("post", "/partida", {"semilla": "abc"}),
        ("post", "/evento", {"nombre": None}),
    ]
    for metodo, ruta, cuerpo in casos:
        r = getattr(cliente, metodo)(ruta, json=cuerpo)
        assert r.status_code in (400, 409, 422), (ruta, r.status_code)
        assert "Traceback" not in r.text


def test_pagina_principal_sirve_el_html_3d(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "ARES-X" in r.text
    assert "static/app.js" in r.text


def test_mapa_devuelve_terreno_de_la_partida(cliente):
    r = cliente.get("/mapa")
    assert r.status_code == 200
    datos = r.json()
    assert datos["filas"] == 20 and datos["columnas"] == 30
    assert len(datos["tipo"]) == 20 and len(datos["tipo"][0]) == 30
    assert datos["inicio"] == [19, 0]
    assert datos["refugio"] == [0, 29]
    assert all("pos" in s and "valor" in s for s in datos["sitios"])


def test_estado_incluye_drones_con_su_estado(cliente):
    datos = cliente.get("/estado").json()
    assert "npcs" in datos and isinstance(datos["npcs"], list)
    for n in datos["npcs"]:
        assert n["estado"] in ("patrulla", "alerta", "persecucion", "ataque")
        assert 0 < n["vida"] <= 3


def test_disparo_devuelve_eventos_del_combate(cliente):
    r = cliente.post("/disparo", json={"rumbo": "N"})
    assert r.status_code == 200
    assert "eventos_combate" in r.json()


def test_impacto_del_disparo_llega_en_la_respuesta(cliente):
    # Regresión ARX-09: tick() vaciaba los eventos y el impacto del disparo no llegaba a la respuesta
    sesion = _app_con_sesion(cliente)
    f, c = sesion.partida.rover.posicion
    dron = sesion.combate.drones[0]
    dron.pos = (f, c + 2)
    dron.estado = "patrulla"
    r = cliente.post("/disparo", json={"rumbo": "E"}).json()
    assert r["impacto"] is True
    assert any("impacto al dron" in e for e in r["eventos_combate"])


def test_automatico_dispara_a_un_dron_en_linea_recta(cliente):
    # Coloca un dron a 2 celdas al norte del rover, en línea recta: la IA debe disparar (D-DISPARO-DRON)
    sesion = _app_con_sesion(cliente)
    from juego.combate import Dron
    f, c = sesion.partida.rover.posicion
    sesion.partida.mundo.tipo[f - 2, c] = 0
    sesion.combate.drones = [Dron(id=9, pos=(f - 2, c), ruta_patrulla=[(f - 2, c), (f - 2, c + 1)],
                                  estado="alerta")]
    cliente.post("/modo", json={"modo": "automatico"})
    r = cliente.post("/paso").json()
    assert "D-DISPARO-DRON" in r["motivos"]
    assert r["accion"] == "disparar"


def test_modo_veto_se_valida_y_se_expone_en_estado(cliente):
    assert cliente.post("/modo", json={"modo": "rna", "veto": "si"}).status_code == 400
    r = cliente.post("/modo", json={"modo": "rna", "veto": False}).json()
    assert r["veto"] is False
    assert cliente.get("/estado").json()["veto"] is False


@pytest.mark.parametrize("modo", ["rna", "difuso", "ag"])
def test_paso_con_modo_suelto_conduce_y_no_devuelve_traceback(cliente, modo):
    cliente.post("/modo", json={"modo": modo})
    r = cliente.post("/paso")
    assert r.status_code == 200
    datos = r.json()
    assert "accion" in datos and "estado" in datos and "ultimo" in datos


@pytest.mark.parametrize("modo", ["automatico"])
def test_dron_sobre_el_rover_no_da_500(cliente, modo):
    # Regresión ARX-18.1: un dron en la celda del rover daba StopIteration (HTTP 500) en la capa de combate
    sesion = _app_con_sesion(cliente)
    cliente.post("/modo", json={"modo": modo})
    sesion.combate.drones[0].pos = tuple(int(x) for x in sesion.partida.rover.posicion)
    sesion.combate.drones[0].estado = "ataque"
    r = cliente.post("/paso")
    assert r.status_code == 200, r.text
    assert "accion" in r.json()


@pytest.mark.parametrize("modo,usado", [("rna", False), ("ag", False), ("difuso", True)])
def test_panel_difuso_marca_no_usado_en_rna_y_ag(cliente, modo, usado):
    # ARX-18.3: en rna y ag el difuso no mueve el rover; el panel no debe mostrar una velocidad 0
    cliente.post("/modo", json={"modo": modo})
    cliente.post("/paso")
    difuso = cliente.get("/paneles").json()["difuso"]
    assert difuso["usado"] is usado
    if not usado:
        assert difuso["velocidad"] is None and difuso["reglas"] is None
