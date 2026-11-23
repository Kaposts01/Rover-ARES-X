"""Ronda 23: comparación de dos políticas con la misma semilla y récords por semilla (api/extras.py, api/records.py)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from api import extras, records  # noqa: E402
from api.servidor import crear_app  # noqa: E402

TERMINALES = {"EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO", "LIMITE"}


@pytest.fixture()
def datos(tmp_path, monkeypatch):
    monkeypatch.setenv("ARES_DATOS_DIR", str(tmp_path / "datos"))
    return tmp_path / "datos"


@pytest.fixture()
def cli(datos):
    return TestClient(crear_app())


def _crear(c, a="hibrido", b="sin_rna", semilla=5, nivel=2):
    r = c.post("/comparar", json={"semilla": semilla, "nivel": nivel, "tamano": "pequeno", "politica_a": a, "politica_b": b})
    assert r.status_code == 200, r.text
    return r.json()


def _correr(c, ident, tope=40):
    for _ in range(tope):
        r = c.post(f"/comparar/{ident}/avanzar", json={"pasos": 30}).json()
        if all(l["terminado"] for l in r["lados"]):
            return r
    raise AssertionError("la comparación no terminó")


# ---------- comparación ----------
def test_mismas_semillas_dan_el_mismo_mapa_en_ambos_lados_y_se_corre_hasta_el_final(cli):
    d = _crear(cli)
    assert d["mapas_iguales"] is True and d["huellas"][0] == d["huellas"][1]
    assert d["mapa"]["filas"] == 20 and d["mapa"]["columnas"] == 30 and d["mapa"]["sitios"]
    assert [l["politica"] for l in d["lados"]] == ["hibrido", "sin_rna"]
    fin = _correr(cli, d["id"])
    assert fin["tabla"] is not None and fin["tabla"]["ganador"] in ("a", "b", "empate")
    claves = [f["clave"] for f in fin["tabla"]["filas"]]
    assert claves == ["resultado", "pasos", "puntaje", "ciencia_fraccion", "bateria_pct", "sitios_visitados", "vetos", "colisiones"]
    for l in fin["lados"]:
        assert l["estado"] in TERMINALES


def test_otra_semilla_cambia_el_mapa_y_la_misma_semilla_lo_repite(cli):
    a, b, c = _crear(cli, semilla=5), _crear(cli, semilla=5), _crear(cli, semilla=6)
    assert a["huellas"][0] == b["huellas"][0] != c["huellas"][0]


def test_todas_las_politicas_arrancan_y_dan_pasos(cli):
    for pol in extras.POLITICAS:
        d = _crear(cli, a="hibrido", b=pol, semilla=3, nivel=1)
        r = cli.post(f"/comparar/{d['id']}/avanzar", json={"pasos": 3}).json()
        assert len(r["lados"][1]["pasos"]) == 3, pol
        assert r["lados"][1]["pasos"][0]["n"] == 1


def test_las_fichas_traen_lo_que_pinta_el_minimapa(cli):
    d = _crear(cli)
    f = cli.post(f"/comparar/{d['id']}/avanzar", json={"pasos": 2}).json()["lados"][0]["pasos"][-1]
    for k in ("n", "posicion", "accion", "motivos", "estado", "bateria_pct", "sitios_visitados", "sitios_totales", "vetos", "colisiones", "visitados"):
        assert k in f, k


def test_una_politica_igual_a_la_otra_no_diverge_y_empata(cli):
    d = _crear(cli, a="hibrido", b="hibrido")
    fin = _correr(cli, d["id"])
    assert fin["divergencia"] is None
    assert fin["tabla"]["ganador"] == "empate"


def test_la_divergencia_marca_el_primer_paso_distinto(cli):
    d = _crear(cli, a="hibrido", b="ruta_corta", semilla=7, nivel=3)
    fin = _correr(cli, d["id"])
    dv = fin["divergencia"]
    if dv is not None:
        pa = cli.get(f"/comparar/{d['id']}").json()
        a, b = pa["lados"][0]["pasos"], pa["lados"][1]["pasos"]
        i = dv["n"] - 1
        assert (a[i]["posicion"], a[i]["accion"]) != (b[i]["posicion"], b[i]["accion"])
        for k in range(i):
            assert (a[k]["posicion"], a[k]["accion"]) == (b[k]["posicion"], b[k]["accion"])


def test_la_comparacion_no_pisa_la_partida_que_se_esta_jugando(cli):
    assert cli.post("/partida", json={"semilla": 11, "nivel": 1, "tamano": "pequeno"}).status_code == 200
    cli.post("/mover", json={"rumbo": "E"})
    antes = cli.get("/estado").json()
    n_hist = len(cli.get("/historial").json()["filas"]) if "filas" in cli.get("/historial").json() else None
    d = _crear(cli, semilla=99, nivel=4)
    _correr(cli, d["id"])
    despues = cli.get("/estado").json()
    for k in ("semilla", "nivel", "posicion", "bateria", "paso", "estado", "modo", "puntaje", "vetos"):
        assert antes[k] == despues[k], k
    assert despues["semilla"] == 11
    if n_hist is not None:
        assert len(cli.get("/historial").json()["filas"]) == n_hist


def test_sin_partida_global_la_comparacion_funciona_y_no_crea_ninguna(cli):
    d = _crear(cli)
    _correr(cli, d["id"])
    assert cli.get("/estado").json().get("sin_partida") is True


def test_limite_de_comparaciones_y_limpieza(cli):
    ids = [_crear(cli, semilla=s)["id"] for s in range(extras.MAX_COMPARACIONES + 2)]
    assert cli.get(f"/comparar/{ids[0]}").status_code == 404           # la más vieja se descartó
    assert cli.get(f"/comparar/{ids[-1]}").status_code == 200
    assert len(cli.app.state.comparaciones) == extras.MAX_COMPARACIONES
    assert cli.delete(f"/comparar/{ids[-1]}").json() == {"ok": True}
    assert cli.delete(f"/comparar/{ids[-1]}").json() == {"ok": False}
    assert cli.get(f"/comparar/{ids[-1]}").status_code == 404


def test_las_comparaciones_vencidas_se_limpian(cli, monkeypatch):
    d = _crear(cli)
    cli.app.state.comparaciones[d["id"]].usada -= extras.TTL_SEGUNDOS + 5
    assert cli.get(f"/comparar/{d['id']}").status_code == 404
    assert len(cli.app.state.comparaciones) == 0


def test_entradas_invalidas_dan_mensajes_claros(cli):
    r = cli.post("/comparar", json={"politica_a": "no_existe"})
    assert r.status_code == 400 and "política inválida" in r.json()["motivo"]
    assert cli.post("/comparar", json={"semilla": "abc"}).status_code == 400
    assert cli.post("/comparar", json={"tamano": "enorme"}).status_code == 400
    assert cli.post("/comparar", json={"planeta": "Júpiter", "modo": "rover"}).status_code == 400
    d = _crear(cli)
    assert cli.post(f"/comparar/{d['id']}/avanzar", json={"pasos": 0}).status_code == 400
    assert cli.post(f"/comparar/{d['id']}/avanzar", json={"pasos": 999}).status_code == 400
    assert cli.get("/comparar/inexistente").status_code == 404


def test_se_puede_comparar_en_otro_planeta_con_sonda(cli):
    r = cli.post("/comparar", json={"semilla": 4, "nivel": 1, "tamano": "pequeno", "planeta": "Júpiter", "modo": "sonda",
                                    "politica_a": "hibrido", "politica_b": "solo_ag"})
    assert r.status_code == 200, r.text
    assert r.json()["mapas_iguales"] is True


# ---------- récords ----------
def _jugar_hasta_el_final(c, modo="automatico", semilla=11, nivel=1):
    assert c.post("/partida", json={"semilla": semilla, "nivel": nivel, "tamano": "pequeno"}).status_code == 200
    if modo != "manual":
        c.post("/modo", json={"modo": modo})
    for _ in range(600):
        r = c.post("/paso").json()
        if r.get("estado") in TERMINALES:
            return r
    raise AssertionError("no terminó")


def test_guardar_un_record_con_todos_los_campos(cli, datos):
    _jugar_hasta_el_final(cli)
    r = cli.post("/records/registrar").json()
    rec = r["record"]
    for k in ("id", "fecha", "planeta", "nivel", "tamano", "semilla", "vehiculo", "origen", "modo", "resultado", "pasos", "puntaje", "bateria_pct"):
        assert k in rec, k
    assert rec["origen"] == "ia" and rec["tamano"] == "pequeno" and rec["semilla"] == 11 and rec["vehiculo"] == "rover"
    assert r["nuevo_record"] is (rec["resultado"] == "EXITO") and r["ya_registrado"] is False
    assert (datos / "records.json").exists()
    assert json.loads((datos / "records.json").read_text(encoding="utf-8"))["records"][0]["id"] == rec["id"]


def test_registrar_dos_veces_la_misma_partida_no_duplica(cli):
    _jugar_hasta_el_final(cli)
    a = cli.post("/records/registrar").json()
    b = cli.post("/records/registrar").json()
    assert b["ya_registrado"] is True and b["record"]["id"] == a["record"]["id"]
    assert cli.get("/records").json()["total"] == 1


def test_no_se_registra_una_mision_sin_terminar(cli):
    assert cli.post("/records/registrar").status_code == 409                       # sin partida
    cli.post("/partida", json={"semilla": 1, "nivel": 1, "tamano": "pequeno"})
    r = cli.post("/records/registrar")
    assert r.status_code == 409 and "aún no terminó" in r.json()["motivo"]


def test_origen_manual_asistida_e_ia(cli):
    # manual puro: pasos del jugador
    cli.post("/partida", json={"semilla": 2, "nivel": 1, "tamano": "pequeno"})
    cli.post("/mover", json={"rumbo": "E"})
    h = cli.get("/historial").json()
    assert records.origen_de(h["filas"]) == "manual"
    # manual con la IA conduciendo (el botón «Dejar que la IA conduzca» manda /paso en modo manual)
    cli.post("/paso")
    assert records.origen_de(cli.get("/historial").json()["filas"]) == "asistida"
    # solo manual con IA desde el principio
    cli.post("/partida", json={"semilla": 2, "nivel": 1, "tamano": "pequeno"})
    cli.post("/paso")
    assert records.origen_de(cli.get("/historial").json()["filas"]) == "asistida"


def test_origen_de_es_puro():
    assert records.origen_de([]) == "manual"
    assert records.origen_de([{"tecnica": "humano", "modo": "manual"}]) == "manual"
    assert records.origen_de([{"tecnica": "supervisor", "modo": "automatico"}]) == "ia"
    assert records.origen_de([{"tecnica": "humano", "modo": "manual"}, {"tecnica": "supervisor", "modo": "automatico"}]) == "asistida"
    assert records.origen_de([{"tecnica": "supervisor", "modo": "manual"}]) == "asistida"
    assert records.origen_de([{"tecnica": "escenario", "modo": "manual"}]) == "manual"


def _reg(**k):
    base = {"planeta": "Marte", "nivel": 1, "tamano": "pequeno", "semilla": 7, "vehiculo": "rover", "origen": "ia", "modo": "automatico",
            "resultado": "EXITO", "pasos": 50, "puntaje": 100, "bateria_pct": 60.0}
    return {**base, **k}


def test_orden_y_nuevo_record(datos):
    a = records.registrar(_reg(pasos=60, puntaje=100))
    assert a["nuevo_record"] is True and a["mejor_anterior"] is None and a["puesto"] == 1
    b = records.registrar(_reg(pasos=50, puntaje=100))                    # mismo puntaje, menos pasos: mejor
    assert b["nuevo_record"] is True and b["mejor_anterior"]["id"] == a["record"]["id"] and b["puesto"] == 1
    c = records.registrar(_reg(pasos=80, puntaje=90))
    assert c["nuevo_record"] is False and c["puesto"] == 3
    d = records.registrar(_reg(resultado="FRACASO", puntaje=500))          # un fracaso nunca es récord ni gana a un éxito
    assert d["nuevo_record"] is False and d["puesto"] is None
    m = records.consultar({})["mejores"]
    assert len(m) == 1 and m[0]["id"] == b["record"]["id"] and m[0]["intentos"] == 4 and m[0]["exitos"] == 3
    orden = [r["id"] for r in records.consultar({})["records"]]
    assert orden[:3] == [b["record"]["id"], a["record"]["id"], c["record"]["id"]] and orden[-1] == d["record"]["id"]


def test_manual_e_ia_compiten_por_separado(datos):
    records.registrar(_reg(origen="ia", puntaje=150))
    r = records.registrar(_reg(origen="manual", puntaje=80))
    assert r["nuevo_record"] is True                                     # primer récord manual de esa semilla
    assert len(records.consultar({})["mejores"]) == 2
    assert len(records.consultar({"origen": "manual"})["mejores"]) == 1


def test_filtros(datos):
    records.registrar(_reg(semilla=1, planeta="Marte"))
    records.registrar(_reg(semilla=2, planeta="Luna", nivel=3))
    assert records.consultar({"planeta": "Luna"})["filtrados"] == 1
    assert records.consultar({"semilla": "1"})["filtrados"] == 1
    assert records.consultar({"nivel": "3"})["filtrados"] == 1
    assert records.consultar({"semilla": "99"})["mejores"] == []
    assert records.consultar({})["planetas"] == ["Luna", "Marte"]


def test_archivo_corrupto_se_aparta_y_se_sigue(datos):
    datos.mkdir(parents=True)
    (datos / "records.json").write_text("{esto no es json", encoding="utf-8")
    assert records.cargar() == []
    assert (datos / "records.json.corrupto").exists()
    assert records.registrar(_reg())["nuevo_record"] is True
    assert len(records.cargar()) == 1


def test_estructura_inesperada_y_registros_rotos(datos):
    datos.mkdir(parents=True)
    (datos / "records.json").write_text('["lista suelta"]', encoding="utf-8")
    assert records.cargar() == []
    (datos / "records.json").write_text(json.dumps({"records": [{"x": 1}, _reg(id="a")]}), encoding="utf-8")
    assert [r["id"] for r in records.cargar()] == ["a"]


def test_borrar_y_sin_archivo(cli, datos):
    assert cli.get("/records").json() == {"total": 0, "filtrados": 0, "mejores": [], "records": [], "planetas": [], "niveles": []}
    records.registrar(_reg())
    records.registrar(_reg(semilla=8))
    assert cli.delete("/records").json() == {"borrados": 2}
    assert cli.get("/records").json()["total"] == 0
    assert not list(datos.glob("*.tmp"))                                  # la escritura atómica no deja temporales


def test_filtro_de_origen_invalido(cli):
    assert cli.get("/records?origen=otro").status_code == 400


def test_la_carpeta_de_datos_esta_fuera_del_control_de_versiones():
    raiz = Path(__file__).resolve().parents[2]
    assert "datos_local/" in (raiz / ".gitignore").read_text(encoding="utf-8")
