"""Pruebas del menú de inicio (ARX-14) y del historial de decisiones (ARX-15) de la API."""
import csv
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.servidor import Sesion, crear_app  # noqa: E402


@pytest.fixture
def sin_partida():
    return TestClient(crear_app())


@pytest.fixture
def cliente():
    return TestClient(crear_app(Sesion(semilla=11)))


# ---------- ARX-14: menú de inicio ----------

def test_al_arrancar_no_hay_partida_y_estado_lo_indica(sin_partida):
    datos = sin_partida.get("/estado").json()
    assert datos["sin_partida"] is True


@pytest.mark.parametrize("ruta", ["/paso", "/mapa", "/paneles", "/historial"])
def test_rutas_de_juego_sin_partida_responden_409(sin_partida, ruta):
    r = sin_partida.post(ruta) if ruta == "/paso" else sin_partida.get(ruta)
    assert r.status_code == 409
    assert "POST /partida" in r.json()["motivo"]


def test_crear_partida_desde_el_menu_reemplaza_la_vacia(sin_partida):
    r = sin_partida.post("/partida", json={"semilla": 5, "nivel": 2})
    assert r.status_code == 200
    datos = sin_partida.get("/estado").json()
    assert datos["semilla"] == 5 and datos["nivel"] == 2
    assert "sin_partida" not in datos


def test_sin_semilla_el_backend_elige_una_aleatoria_y_la_devuelve(sin_partida):
    semillas = set()
    for _ in range(3):
        r = sin_partida.post("/partida", json={"semilla": None, "nivel": 1})
        assert r.status_code == 200
        semillas.add(r.json()["semilla"])
    assert all(isinstance(x, int) and 0 <= x < 10 ** 6 for x in semillas)
    assert len(semillas) >= 2          # tres sorteos sobre 10^6 valores: prácticamente siempre distintos


def test_con_semilla_se_reproduce_la_misma_partida(sin_partida):
    a = sin_partida.post("/partida", json={"semilla": 4242, "nivel": 1}).json()
    b = sin_partida.post("/partida", json={"semilla": 4242, "nivel": 1}).json()
    assert a["semilla"] == b["semilla"] == 4242
    assert a["ruta"] == b["ruta"] and a["npcs"] == b["npcs"]


@pytest.mark.parametrize("semilla", ["abc", "-1", "1.5", True, 3 * 10 ** 9, "  ", [1]])
def test_semilla_invalida_es_400_con_motivo_legible(sin_partida, semilla):
    if semilla == "  ":
        # una cadena de espacios equivale a vacío: se trata como aleatoria
        assert sin_partida.post("/partida", json={"semilla": semilla, "nivel": 1}).status_code == 200
        return
    r = sin_partida.post("/partida", json={"semilla": semilla, "nivel": 1})
    assert r.status_code == 400, r.text
    assert "inválid" in r.json()["motivo"]     # NaN llega como JSON no válido: motivo genérico pero legible


@pytest.mark.parametrize("nivel", [0, 6, "x", True])
def test_nivel_invalido_es_400_con_motivo_legible(sin_partida, nivel):
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": nivel})
    assert r.status_code == 400
    assert "nivel inválido" in r.json()["motivo"]


def test_partida_terminada_no_se_reutiliza_al_crear_otra(cliente):
    cliente.app.state.sesion.partida.mision.estado = "EXITO"
    assert cliente.get("/estado").json()["estado"] == "EXITO"
    cliente.post("/partida", json={"semilla": 11, "nivel": 1})
    assert cliente.get("/estado").json()["estado"] != "EXITO"


# ---------- ARX-15: historial de decisiones ----------

def _ultima(cliente):
    return cliente.get("/historial").json()["filas"][-1]


def test_cada_accion_deja_una_fila(cliente):
    cliente.post("/mover", json={"rumbo": "N"})
    cliente.post("/paso")
    assert len(cliente.get("/historial").json()["filas"]) == 2


@pytest.mark.parametrize("modo,tecnica", [("rna", "rna"), ("difuso", "difuso"), ("ag", "ag"),
                                          ("automatico", "supervisor")])
def test_paso_de_cada_modo_queda_con_su_tecnica(cliente, modo, tecnica):
    cliente.post("/modo", json={"modo": modo})
    cliente.post("/paso")
    fila = _ultima(cliente)
    assert fila["modo"] == modo
    assert fila["tecnica"] == tecnica


def test_movimiento_del_jugador_queda_como_humano(cliente):
    cliente.post("/mover", json={"rumbo": "N"})
    assert _ultima(cliente)["tecnica"] == "humano"


def test_disparo_del_jugador_queda_como_humano(cliente):
    cliente.post("/disparo", json={"rumbo": "N"})
    fila = _ultima(cliente)
    assert fila["tecnica"] == "humano" and fila["accion"] == "disparar"


def test_fila_de_modo_suelto_lleva_valores_de_la_rna(cliente):
    cliente.post("/modo", json={"modo": "rna"})
    cliente.post("/paso")
    fila = _ultima(cliente)
    assert fila["p_libre"] is not None and fila["p_barranco"] is not None


def test_fila_de_difuso_lleva_la_velocidad(cliente):
    cliente.post("/modo", json={"modo": "difuso"})
    cliente.post("/paso")
    assert _ultima(cliente)["velocidad"] is not None


def test_historial_se_filtra_por_modo_tecnica_y_desde(cliente):
    cliente.post("/mover", json={"rumbo": "N"})
    cliente.post("/modo", json={"modo": "rna"})
    cliente.post("/paso")
    cliente.post("/modo", json={"modo": "ag"})
    cliente.post("/paso")
    assert {f["tecnica"] for f in cliente.get("/historial?modo=rna").json()["filas"]} == {"rna"}
    assert all(f["tecnica"] == "humano" for f in cliente.get("/historial?tecnica=humano").json()["filas"])
    desde = cliente.get("/historial").json()["filas"][1]["n"]
    assert all(f["n"] >= desde for f in cliente.get("/historial?desde=%d" % desde).json()["filas"])


def test_csv_tiene_las_columnas_de_la_bitacora_y_las_nuevas(cliente):
    cliente.post("/mover", json={"rumbo": "N"})
    cliente.post("/modo", json={"modo": "rna"})
    cliente.post("/paso")
    r = cliente.get("/historial.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    filas = list(csv.DictReader(io.StringIO(r.text)))
    assert len(filas) == 2
    for col in ["paso_mision", "estado", "posicion", "bateria", "velocidad", "p_barranco", "reglas",
                "motivo", "modo", "tecnica", "fitness", "evento", "intervencion"]:
        assert col in filas[0]


def test_nan_en_la_semilla_es_400(sin_partida):
    # NaN no es JSON válido: se envía a mano para comprobar que el servidor responde 400 y no crea partida
    r = sin_partida.post("/partida", content=b'{"semilla": NaN, "nivel": 1}',
                         headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert sin_partida.get("/estado").json()["sin_partida"] is True


def test_ag_expone_generaciones_candidatos_y_operaciones(cliente):
    # ARX-22 bloque 1: CA-04 y RF-11. Historial por generación con cromosomas, fitness y operación.
    r = cliente.get("/ag")
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["parametros"]["poblacion"] >= 30 and datos["parametros"]["generaciones"] >= 30
    assert len(datos["generaciones"]) == 30
    gen = datos["generaciones"][5]
    assert len(gen["poblacion"]) == 30
    assert {"cromosoma", "fitness", "operacion"} <= set(gen["poblacion"][0])
    assert len(gen["top"]) == 3
    assert len(datos["candidatos"]) == 3
    assert {"fitness", "ciencia", "distancia", "energia", "riesgo", "tiempo", "inviabilidad"} <= set(
        datos["candidatos"][0]["desglose"])
    assert datos["cruces"] > 0 and datos["mutaciones"] > 0


def test_ag_parada_temprana_corta_las_generaciones(cliente):
    datos = cliente.get("/ag?parada_sin_mejora=1").json()
    assert datos["generaciones_ejecutadas"] < 30
    assert cliente.get("/ag?parada_sin_mejora=0").status_code == 400


@pytest.mark.parametrize("valor", ["aleatoria", "Aleatoria", "random", "", None])
def test_semilla_aleatoria_se_acepta_y_se_devuelve(sin_partida, valor):
    # ARX-23 C: "aleatoria", vacío o ausente → el backend elige la semilla y la devuelve
    r = sin_partida.post("/partida", json={"semilla": valor, "nivel": 1})
    assert r.status_code == 200, r.text
    semilla = r.json()["semilla"]
    assert isinstance(semilla, int) and 0 <= semilla < 10 ** 6
    assert sin_partida.get("/estado").json()["semilla"] == semilla


def test_jupiter_con_rover_se_bloquea_con_sugerencia_de_sonda(sin_partida):
    # CA-07 y ev3-d39 B: rover de ruedas en Júpiter → 400 con explicación y sugerencia de modo sonda
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": 1, "planeta": "Júpiter", "modo": "rover"})
    assert r.status_code == 400
    assert "sonda" in r.json()["motivo"]
    assert sin_partida.get("/estado").json()["sin_partida"] is True


def test_jupiter_en_modo_sonda_y_marte_en_rover_se_aceptan(sin_partida):
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": 1, "planeta": "Júpiter", "modo": "sonda"})
    assert r.status_code == 200
    assert r.json()["planeta"] == "Júpiter" and r.json()["modo_planeta"] == "sonda"
    assert sin_partida.post("/partida", json={"semilla": 11, "nivel": 1}).json()["planeta"] == "Marte"


def test_planetas_lista_los_ocho_y_marca_los_gigantes_como_no_viables(cliente):
    datos = cliente.get("/planetas").json()
    por_nombre = {p["nombre"]: p for p in datos["planetas"]}
    assert len(por_nombre) == 8
    assert por_nombre["Marte"]["viable"] is True
    assert por_nombre["Júpiter"]["viable"] is False and "sonda" in por_nombre["Júpiter"]["motivo"]


def test_estado_visible_emite_replanificacion_refugio_y_alerta(cliente):
    # ARX-33: /estado.estado usa ALERTA, REPLANIFICACION, REFUGIO y MODO_SEGURO además de EXPLORACION
    from juego.partida import Partida
    p = Partida(semilla=11)
    assert p.estado_visible() == "EXPLORACION"
    p.mision.estado = "ALERTA"
    assert p.estado_visible() == "ALERTA"
    p.mision.log.filas.append({"accion": "replanificar"})
    assert p.estado_visible() == "REPLANIFICACION"
    p.mision.log.filas.append({"accion": "avanzar"})
    p.mision.estado = "EXPLORACION"
    p.mision.visitados = set(p.mision.objetivos)        # sin sitios pendientes: ruta al refugio
    assert p.estado_visible() == "REFUGIO"
    p.mision.estado = "MODO_SEGURO"
    assert p.estado_visible() == "MODO_SEGURO"


def test_moviles_devuelve_drones_con_trayectoria_y_ruta_ejecutada(cliente):
    # ARX-29: drones con trayectoria por turno; ruta planificada frente a la ejecutada
    cliente.post("/mover", json={"rumbo": "N"})
    cliente.post("/paso")
    datos = cliente.get("/moviles").json()
    assert datos["moviles"], "debe haber drones"
    for m in datos["moviles"]:
        assert {"id", "tipo", "pos", "trayectoria", "estado", "vida"} <= set(m)
        assert len(m["trayectoria"]) >= 1
    assert len(datos["ruta"]["ejecutada"]) >= 2
    assert datos["obstaculos_moviles"] == []


@pytest.mark.parametrize("nombre,numero", [("muy_facil", 1), ("facil", 2), ("Medio", 3), ("dificil", 4),
                                           ("hardcore", 5), ("difícil", 4), (3, 3), ("2", 2)])
def test_nivel_por_nombre_o_numero(sin_partida, nombre, numero):
    # ARX-53: los niveles tienen nombre; los números 1 a 5 siguen siendo válidos
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": nombre})
    assert r.status_code == 200, r.text
    assert r.json()["nivel"] == numero


def test_nivel_fuera_de_nombres_y_numeros_es_400(sin_partida):
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": "epico"})
    assert r.status_code == 400 and "muy_facil" in r.json()["motivo"]


def test_recomendacion_propone_un_paso_por_modelo_sin_mover_el_rover(cliente):
    # ARX-55: cada modelo propone su paso sobre una copia; la partida real no cambia
    antes = cliente.get("/estado").json()["posicion"]
    datos = cliente.get("/recomendacion").json()
    assert [p["modelo"] for p in datos["propuestas"]] == ["hibrido", "rna", "difuso", "ag"]
    for p in datos["propuestas"]:
        assert p["accion"] and p["razon"]
    assert cliente.get("/estado").json()["posicion"] == antes


def test_objetivos_usa_el_esquema_de_diseno(cliente):
    # ARX-66: GET /objetivos con el esquema acordado (mision + condiciones con progreso real)
    datos = cliente.get("/objetivos").json()
    assert isinstance(datos["mision"], str) and datos["mision"]
    assert len(datos["condiciones"]) >= 2
    for c in datos["condiciones"]:
        assert {"nombre", "progreso", "total", "cumplido"} <= set(c)
        assert 0 <= c["progreso"] <= c["total"] or c["total"] == 1


def test_ruta_inconsistente_no_da_500_y_se_replanifica(cliente):
    # Caso reportado 14/11 (semilla 641752, hardcore, modo ag): la ruta no parte del rover y _rumbo lanzaba ValueError.
    # Reproducción sintética: ruta con un salto no adyacente. /estado debe responder 200 y el paso debe replanificar.
    sesion = cliente.app.state.sesion
    p = sesion.partida
    pos = tuple(int(x) for x in p.rover.posicion)
    p.mision.ruta = [pos, (pos[0] + 5, pos[1] + 5)]
    assert cliente.get("/estado").status_code == 200
    cliente.post("/modo", json={"modo": "ag"})
    r = cliente.post("/paso")
    assert r.status_code == 200, r.text
    assert "REPLAN-RUTA-INCONSISTENTE" in r.json().get("motivos", []) or r.json()["accion"] in ("replanificar", "avanzar")


@pytest.mark.parametrize("tamano,filas,columnas", [("pequeno", 20, 30), ("mediano", 30, 45), ("grande", 40, 60)])
def test_tamano_del_mapa_configurable(sin_partida, tamano, filas, columnas):
    # ARX-21: el mapa tiene el tamaño pedido; la evaluación congelada usa pequeno (20x30)
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": 1, "tamano": tamano})
    assert r.status_code == 200, r.text
    mapa = sin_partida.get("/mapa").json()
    assert (mapa["filas"], mapa["columnas"]) == (filas, columnas)


def test_tamano_invalido_es_400(sin_partida):
    r = sin_partida.post("/partida", json={"semilla": 11, "nivel": 1, "tamano": "gigante"})
    assert r.status_code == 400 and "pequeno" in r.json()["motivo"]


def test_llegar_al_refugio_sin_los_sitios_no_es_victoria(cliente):
    # N4 (decisión del orquestador, 14/11): llegar al refugio sin los sitios no termina la partida;
    # sigue en curso con el aviso «Faltan objetivos». Solo con todos los sitios hay victoria.
    from juego.partida import Partida
    p = Partida(semilla=11)
    p.mision.estado = "EXITO"
    p.mision.visitados = set()
    p._revisar_victoria()
    assert p.estado == "EXPLORACION"
    assert any(a.startswith("Faltan objetivos: sitios 0/") for a in p.avisos)
    p.mision.estado = "EXITO"
    p.mision.visitados = set(p.mundo.sitios)
    p._revisar_victoria()
    assert p.estado == "EXITO"


def test_sin_bateria_para_los_sitios_termina_y_no_bucla(cliente):
    # N6 (14/11): semilla 831245, Júpiter sonda, medio, grande, automático. En el refugio con sitios pendientes y
    # batería insuficiente, la partida debía replanificar en cada paso sin acabar. Ahora termina con FRACASO por batería.
    from juego.partida import Partida
    p = Partida(semilla=831245, nivel=3, filas=40, columnas=60)
    p.mision.estado = "EXITO"
    p.mision.visitados = set()
    p.rover.bateria = 22.0
    p._revisar_victoria()
    assert p.estado == "FRACASO"
    assert any("Batería insuficiente" in a for a in p.avisos)
    assert len(p.avisos) <= 20


def test_semilla_282386_automatico_termina_en_exito_o_fracaso(cliente):
    # N7 (INFORME §6): Marte, rover, Muy fácil, pequeño, automático. La acción «fin» solo puede aparecer con
    # ÉXITO o FRACASO; la partida debe terminar en uno de los dos.
    cliente.post("/partida", json={"semilla": 282386, "nivel": "muy_facil", "tamano": "pequeno",
                                   "planeta": "Marte", "modo": "rover"})
    cliente.post("/modo", json={"modo": "automatico"})
    final = None
    for _ in range(400):
        r = cliente.post("/paso").json()
        if r.get("accion") == "fin":
            assert r["estado"] in ("EXITO", "FRACASO"), r
        final = r["estado"]
        if final in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
    assert final in ("EXITO", "FRACASO"), final


@pytest.mark.parametrize("nivel,drones_obligatorios", [("muy_facil", False), ("facil", False), ("medio", True),
                                                       ("dificil", True), ("hardcore", True)])
def test_drones_obligatorios_solo_desde_medio(sin_partida, nivel, drones_obligatorios):
    # Decisión del usuario (14/11): los drones son obligatorios desde Medio; sitios y refugio siempre
    sin_partida.post("/partida", json={"semilla": 11, "nivel": nivel, "tamano": "pequeno"})
    condiciones = {c["nombre"]: c for c in sin_partida.get("/objetivos").json()["condiciones"]}
    assert condiciones["Drones destruidos"]["obligatorio"] is drones_obligatorios
    assert condiciones["Sitios científicos"]["obligatorio"] is True
    assert condiciones["Llegar al refugio"]["obligatorio"] is True


def test_en_muy_facil_los_drones_no_bloquean_la_victoria(sin_partida):
    from juego.partida import Partida
    p = Partida(semilla=11, nivel=1)
    p.mision.estado = "EXITO"
    p.mision.visitados = set(p.mundo.sitios)
    p._revisar_victoria()
    assert p.estado == "EXITO"


def test_drones_pendientes_se_cazan_y_no_fracasan_de_inmediato(cliente):
    # N12 (corrección del orquestador): en el refugio con drones pendientes, el objetivo pasa al dron
    # más cercano; FRACASO solo si no hay forma. Desde ARX-75 la caza por BFS también aplica en modo rna
    # (ya no «no dispara»): la partida sigue en EXPLORACION con el aviso de drones vivos.
    from juego.partida import Partida
    p = Partida(semilla=11, nivel=3)
    p.modo_ia = "automatico"
    from juego.combate import Combate
    p.combate = Combate(mundo=p.mundo, rover=p.rover, semilla=11)
    p.mision.estado = "EXITO"
    p.mision.visitados = set(p.mundo.sitios)
    p.modo_ia = "rna"
    p._revisar_victoria()
    assert p.estado == "EXPLORACION" and any("Faltan drones" in a for a in p.avisos)
