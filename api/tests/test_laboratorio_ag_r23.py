"""R23 (correcciones tras el QA final): el laboratorio genético (GET /ag) corre el AG con restricciones sobre la partida actual;
ciencia recogida en la comparación en vivo; /ag/evolucion comprimido."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import api.servidor as servidor  # noqa: E402
from api.servidor import crear_app  # noqa: E402


@pytest.fixture
def cliente_n5():
    servidor._cache_ag.clear()
    cli = TestClient(crear_app())
    assert cli.post("/partida", json={"semilla": 7, "nivel": 5, "tamano": "pequeno", "planeta": "Marte", "modo": "rover"}).status_code == 200
    return cli


def test_el_laboratorio_devuelve_candidatos_viables_y_una_curva_que_mejora_en_nivel_5(cliente_n5):
    d = cliente_n5.get("/ag").json()
    assert d["modo"] == "restricciones" and d["viable"] is True and d["fallback"] is None
    assert len(d["candidatos"]) >= 3 and all(c["factible"] for c in d["candidatos"])
    mejor = [g["mejor"] for g in d["generaciones"]]
    assert len(mejor) == d["parametros"]["generaciones"] == 60
    assert mejor[-1] > mejor[0] + 0.02            # antes: curva plana (-2,53 → -2,52) y sin candidatos
    assert mejor == sorted(mejor)                 # el elitismo no deja bajar el mejor
    assert d["ultima_mejora"] >= 5                # no converge en la generación 1 o 2


def test_el_contrato_que_lee_la_interfaz_se_conserva(cliente_n5):
    d = cliente_n5.get("/ag").json()
    assert {"poblacion", "generaciones", "pesos", "parada_sin_mejora"} <= set(d["parametros"])
    g = d["generaciones"][3]
    assert {"generacion", "mejor", "media", "peor", "cruces", "mutaciones", "poblacion"} <= set(g)
    assert {"cromosoma", "fitness", "operacion"} <= set(g["poblacion"][0])
    assert all(len(c) == 2 for c in g["poblacion"][0]["cromosoma"])
    c = d["candidatos"][0]
    assert {"orden", "pasos", "cromosoma", "desglose", "fitness"} <= set(c)
    assert {"ciencia", "distancia", "energia", "riesgo", "tiempo", "inviabilidad"} <= set(c["desglose"])
    assert len(c["orden"]) == len(c["cromosoma"]) == len(c["pasos"]) and all(len(x) == 2 for x in c["orden"])
    assert {"mejor_ruta", "mejor_desglose", "cruces", "mutaciones", "generaciones_ejecutadas", "ordenes_evaluados", "orden_en_juego"} <= set(d)
    # campos nuevos
    assert {"tiempo_s", "sitios", "bases", "ultima_mejora", "bateria"} <= set(d)
    assert {"ids", "recargas", "paradas", "violaciones", "sacrificados", "ventanas_perdidas"} <= set(c)


def test_los_pesos_cambian_el_fitness_y_sin_tocarlos_es_el_del_juego(cliente_n5):
    base = cliente_n5.get("/ag").json()
    assert base["parametros"]["fitness"] == "el del juego"
    d = cliente_n5.get("/ag?w_ciencia=2&w_tiempo=4").json()
    assert d["parametros"]["fitness"].startswith("ponderado")
    assert d["parametros"]["pesos"]["ciencia"] == 2.0
    assert [c["fitness"] for c in d["candidatos"]] != [c["fitness"] for c in base["candidatos"]]


def test_parada_sin_mejora_corta_las_generaciones(cliente_n5):
    d = cliente_n5.get("/ag?parada_sin_mejora=3").json()
    assert d["generaciones_ejecutadas"] < 60
    assert cliente_n5.get("/ag?parada_sin_mejora=0").status_code == 400


def test_la_respuesta_es_determinista_y_se_cachea(cliente_n5):
    a = cliente_n5.get("/ag").json()
    servidor._cache_ag.clear()
    b = cliente_n5.get("/ag").json()
    assert a["candidatos"][0]["fitness"] == b["candidatos"][0]["fitness"] and a["candidatos"][0]["ids"] == b["candidatos"][0]["ids"]


def test_evolucion_se_comprime_cuando_el_cliente_acepta_gzip(cliente_n5):
    r = cliente_n5.get("/ag/evolucion", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("content-encoding") == "gzip"
    assert r.json()["hay_plan"] is True


def test_la_comparacion_en_vivo_trae_la_ciencia_recogida_por_lado():
    cli = TestClient(crear_app())
    d = cli.post("/comparar", json={"semilla": 3, "nivel": 2, "tamano": "pequeno", "politica_a": "hibrido", "politica_b": "sin_ag_vecino"}).json()
    for _ in range(40):
        d = cli.post(f"/comparar/{d['id']}/avanzar", json={"pasos": 60}).json()
        if d["tabla"] is not None:
            break
    assert d["tabla"] is not None
    for l in d["lados"]:
        f = l["pasos"][-1] if l["pasos"] else None
        assert f is None or {"ciencia_recogida", "ciencia_maxima", "ciencia_fraccion"} <= set(f)
        assert f is None or 0.0 <= f["ciencia_fraccion"] <= 1.0
    fila = next(f for f in d["tabla"]["filas"] if f["clave"] == "ciencia_fraccion")
    assert 0.0 <= fila["a"] <= 1.0 and 0.0 <= fila["b"] <= 1.0
