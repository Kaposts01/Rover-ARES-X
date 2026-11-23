"""R23b: el laboratorio de comparación con estadística (IC y diferencias con el híbrido), escenarios rotulados y JSON con 100 semillas."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from juego import comparacion  # noqa: E402

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _fila(semilla, variante, exito, pasos=100, ciencia=0.7, puntaje=500):
    return {"semilla": semilla, "variante": variante, "exito": exito, "pasos": pasos, "colisiones": 0, "bateria_final": 30.0,
            "sitios_visitados": 8, "ciencia": ciencia, "puntaje": puntaje}


def test_una_mision_de_diferencia_con_20_semillas_es_ruido_y_con_100_no_lo_es_si_se_repite():
    # 19/20 frente a 18/20 en las mismas semillas: una misión de diferencia no se distingue del ruido
    hib = [_fila(s, "hibrido", s != 1) for s in range(20)]
    var = [_fila(s, "sin_rna", s not in (1, 2)) for s in range(20)]
    d = comparacion._diferencias_pareadas({f["semilla"]: f for f in hib}, {f["semilla"]: f for f in var})
    assert d["exito_pp"]["diferencia"] == -5.0 and d["exito_pp"]["distinguible_del_ruido"] is False
    # 20 misiones de diferencia sobre 100 semillas sí se distinguen
    hib = [_fila(s, "hibrido", True) for s in range(100)]
    var = [_fila(s, "sin_rna", s >= 20) for s in range(100)]
    d = comparacion._diferencias_pareadas({f["semilla"]: f for f in hib}, {f["semilla"]: f for f in var})
    assert d["exito_pp"]["diferencia"] == -20.0 and d["exito_pp"]["distinguible_del_ruido"] is True


def test_estadistica_cuenta_las_trayectorias_iguales_y_da_wilson():
    filas = [_fila(s, v, True) for v in ("hibrido", "sin_ag_2opt") for s in range(10)]
    e = comparacion.estadistica({"filas": filas})
    assert e["hibrido"]["ic95_exito"][1] == 100.0 and e["hibrido"]["ic95_exito"][0] < 100.0
    assert e["sin_ag_2opt"]["frente_al_hibrido"]["semillas_con_la_misma_trayectoria"] == 10
    assert e["sin_ag_2opt"]["frente_al_hibrido"]["exito_pp"]["distinguible_del_ruido"] is False


def test_los_escenarios_actuales_van_primero_y_el_congelado_es_historico():
    nombres = list(comparacion.ESCENARIOS)
    assert nombres[0] == "jugable_dificil" and nombres[-1] == "congelado"
    assert set(comparacion.INFO_ESCENARIOS) == set(nombres)
    assert comparacion.INFO_ESCENARIOS["congelado"]["historico"] is True
    assert "histórico (versión anterior del juego)" in comparacion.INFO_ESCENARIOS["congelado"]["descripcion"].lower()
    assert not any(comparacion.INFO_ESCENARIOS[n]["historico"] for n in nombres if n != "congelado")
    assert "no ejercita al ag" in comparacion.INFO_ESCENARIOS["exigente"]["descripcion"].lower()


def test_los_json_jugables_traen_100_semillas_y_la_diferencia_con_el_hibrido():
    for nombre in ("jugable_dificil", "jugable_dificil_neptuno"):
        d = json.loads((DOCS / f"COMPARACION_POLITICAS_{nombre}.json").read_text(encoding="utf-8"))
        assert len(d["semillas"]) == 100 and d["info"]["historico"] is False
        assert d["variantes"]["hibrido"]["n"] == 100 and "error_estandar" in d["variantes"]["hibrido"]["pasos"]
        dif = d["variantes"]["sin_ag_2opt"]["frente_al_hibrido"]
        assert set(dif) >= {"exito_pp", "ciencia", "puntaje", "pasos_si_ganan_las_dos"}
        assert "distinguible_del_ruido" in dif["ciencia"]
    exigente = json.loads((DOCS / "COMPARACION_POLITICAS_exigente.json").read_text(encoding="utf-8"))
    assert len(exigente["semillas"]) == 100
    assert exigente["estadistica"]["sin_ag_2opt"]["frente_al_hibrido"]["semillas_con_la_misma_trayectoria"] >= 85   # no ejercita al AG
    congelado = json.loads((DOCS / "COMPARACION_POLITICAS.json").read_text(encoding="utf-8"))
    assert congelado["info"]["historico"] is True


def test_la_api_sirve_por_defecto_el_jugable_con_su_info():
    from api.servidor import Sesion, crear_app
    c = TestClient(crear_app(Sesion(semilla=11)))
    d = c.get("/comparacion").json()
    assert d["escenario"] == "jugable_dificil" and len(d["semillas"]) == 100
    assert d["escenarios_disponibles"][0] == "jugable_dificil" and d["escenarios_disponibles"][-1] == "congelado"
    assert d["info"]["historico"] is False and d["escenarios_info"]["congelado"]["historico"] is True
