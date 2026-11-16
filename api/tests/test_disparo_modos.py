"""ARX-75: los modos sueltos (rna, difuso, ag) disparan a un dron en línea y en alcance."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app
from simulador import LIBRE, MOVIMIENTOS


def _cliente_con_dron_en_linea(modo):
    sesion = Sesion(semilla=11)
    cliente = TestClient(crear_app(sesion))
    assert cliente.post("/modo", json={"modo": modo}).status_code == 200
    p = sesion.partida
    f, c = p.rover.posicion
    for df, dc in MOVIMIENTOS.values():
        vecino = (f + df, c + dc)
        if p.mundo.dentro(vecino) and p.mundo.tipo[vecino] == LIBRE:
            sesion.combate.drones[0].pos = vecino
            sesion.combate.drones[0].estado = "patrulla"
            break
    sesion.combate.cooldown = 0
    sesion.combate.municion = 5
    return cliente, sesion


def test_rna_difuso_ag_disparan_con_dron_en_linea():
    for modo in ("rna", "difuso", "ag"):
        cliente, sesion = _cliente_con_dron_en_linea(modo)
        municion_antes = sesion.combate.municion
        datos = cliente.post("/paso").json()
        assert datos["accion"] == "disparar", modo
        assert "D-DISPARO-DRON" in datos["motivos"], modo
        assert sesion.combate.municion == municion_antes - 1, modo


def test_veto_bloquea_disparo_en_riesgo_y_queda_anotado():
    for modo in ("rna", "difuso", "ag"):
        cliente, sesion = _cliente_con_dron_en_linea(modo)
        f, c = sesion.partida.rover.posicion
        sesion.partida.mision.riesgo[(f, c)] = 0.9
        datos = cliente.post("/paso").json()
        assert datos["accion"] != "disparar", modo
        assert "V-DISPARO-RIESGO" in datos["motivos"], modo
        assert sesion.combate.municion == 5, modo


def test_sin_veto_dispara_aunque_la_celda_sea_de_riesgo():
    for modo in ("rna", "difuso", "ag"):
        cliente, sesion = _cliente_con_dron_en_linea(modo)
        sesion.veto = False
        f, c = sesion.partida.rover.posicion
        sesion.partida.mision.riesgo[(f, c)] = 0.9
        datos = cliente.post("/paso").json()
        assert datos["accion"] == "disparar", modo


def test_veto_bloquea_disparo_con_bateria_critica():
    cliente, sesion = _cliente_con_dron_en_linea("rna")
    sesion.partida.rover.bateria = 5.0
    datos = cliente.post("/paso").json()
    assert datos["accion"] != "disparar"
    assert "V-DISPARO-BATERIA-CRITICA" in datos["motivos"]


def test_disparo_devuelve_ultimo_con_el_formato_de_un_movimiento():
    cliente, sesion = _cliente_con_dron_en_linea("rna")
    datos = cliente.post("/paso").json()
    assert datos["accion"] == "disparar"
    ultimo = datos["ultimo"]
    assert ultimo, "un disparo debe traer el último paso"
    assert isinstance(ultimo["paso"], int)
    assert ultimo["accion"] == "disparar"
    assert "D-DISPARO-DRON" in ultimo["motivos"]
    for clave in ("velocidad", "p_barranco", "p_obstaculo", "p_libre", "reglas"):
        assert clave in ultimo
    assert ultimo["objetivo"] == sesion.combate.drones[0].id
    assert ultimo["rumbo"] in MOVIMIENTOS
