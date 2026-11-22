"""R23: endpoints /ag/evolucion y /difuso/reglas y el tramo de la RNA en /ia/paso."""
from fastapi.testclient import TestClient

from api.servidor import Sesion, crear_app


def _cliente(semilla=5, nivel=3):
    return TestClient(crear_app(Sesion(semilla=semilla, nivel=nivel, filas=20, columnas=30)))


def test_ag_evolucion_trae_el_plan_inicial_con_restricciones():
    c = _cliente()
    r = c.get("/ag/evolucion")
    assert r.status_code == 200
    d = r.json()
    assert d["hay_plan"] is True and d["planeta"] == "Marte"
    assert len(d["sitios"]) >= 8 and len(d["bases"]) >= 3
    assert all({"id", "celda", "valor", "ventana"} <= set(s) for s in d["sitios"])
    assert any(s["ventana"] for s in d["sitios"]) and all(s["ventana"] is None or len(s["ventana"]) == 2 for s in d["sitios"])
    gens = d["generaciones"]
    assert len(gens) >= 30
    for g in gens:
        assert {"n", "mejor", "media", "peor", "diversidad", "candidatos"} <= set(g)
        assert 1 <= len(g["candidatos"]) <= 6
        assert all({"orden", "recargas", "camino", "fitness", "factible", "violaciones"} <= set(k) for k in g["candidatos"])
    mejor = d["mejor"]
    assert mejor["factible"] and mejor["camino"][0] == d["inicio"] and mejor["camino"][-1] == d["refugio"]
    assert all(-1 <= i < len(mejor["orden"]) for i in mejor["recargas"]) and len(mejor["paradas"]) == len(mejor["recargas"])
    assert "parametros_difuso" in d and d["tiempo_s"] < 10
    # no se recalcula en cada llamada: el mismo plan inicial aunque la partida avance
    c.post("/modo", json={"modo": "automatico"})
    for _ in range(3):
        c.post("/paso")
    assert c.get("/ag/evolucion").json()["mejor"] == mejor


def test_ag_evolucion_mejora_de_forma_sostenida_y_mantiene_la_diversidad():
    d = _cliente(semilla=4, nivel=4).get("/ag/evolucion").json()
    mejores = [g["mejor"] for g in d["generaciones"]]
    assert mejores == sorted(mejores) and mejores[-1] > mejores[0]
    assert d["generaciones"][5]["diversidad"] > 0.1 and d["generaciones"][-1]["diversidad"] > 0.1


def test_difuso_reglas_get_coincide_con_las_de_fabrica():
    d = _cliente().get("/difuso/reglas").json()
    import difuso
    assert d["personalizadas"] is False
    assert set(d["variables"]) == set(difuso.CONJUNTOS) and set(d["salida"]["etiquetas"]) == set(difuso.SALIDA)
    assert d["variables"]["distancia"]["universo"] == [0.0, 20.0]
    assert [r["id"] for r in d["reglas"]] == [r["id"] for r in difuso.REGLAS]
    r1 = d["reglas"][0]
    assert r1["si"] == {"distancia": "cerca"} and r1["entonces"] == "parar" and r1["peso"] == 1.0 and r1["activa"] and r1["texto"]


def test_difuso_reglas_put_aplica_a_la_sesion_y_delete_restaura():
    c = _cliente()
    base = c.get("/difuso", params={"distancia": 5}).json()["salida"]["velocidad"]
    reglas = c.get("/difuso/reglas").json()["reglas"]
    r = c.put("/difuso/reglas", json={"reglas": reglas, "variables": {"distancia": {"etiquetas": {"cerca": [0, 0, 5, 8]}}}})
    assert r.status_code == 200 and r.json()["personalizadas"] is True
    assert c.get("/difuso/reglas").json()["variables"]["distancia"]["etiquetas"]["cerca"] == [0.0, 0.0, 5.0, 8.0]
    cambiado = c.get("/difuso", params={"distancia": 5}).json()
    assert cambiado["salida"]["velocidad"] != base                          # el laboratorio usa las reglas editadas
    assert cambiado["personalizadas"] is True
    assert c.get("/difuso/barrido", params={"desde": 8, "hasta": 4}).status_code == 200
    d = c.delete("/difuso/reglas").json()
    assert d["personalizadas"] is False and c.get("/difuso", params={"distancia": 5}).json()["salida"]["velocidad"] == base


def test_difuso_reglas_put_invalido_da_400_con_motivo_y_no_cambia_nada():
    c = _cliente()
    for cuerpo, texto in [({"reglas": [{"id": "R1", "peso": 5}]}, "peso"), ({"reglas": []}, "al menos una"),
                          ({"variables": {"distancia": {"etiquetas": {"cerca": [3, 1]}}}}, "3 puntos"),
                          ({"reglas": [{"id": "Z", "si": {"distancia": "cerca"}, "entonces": "volar"}]}, "entonces")]:
        r = c.put("/difuso/reglas", json=cuerpo)
        assert r.status_code == 400 and texto in r.json()["motivo"]
    assert c.get("/difuso/reglas").json()["personalizadas"] is False


def test_las_reglas_editadas_valen_solo_para_la_partida_en_curso_y_no_para_la_comparacion():
    c = _cliente()
    c.put("/difuso/reglas", json={"reglas": [{"id": "R1", "peso": 0.1}]})
    assert c.get("/difuso/reglas").json()["personalizadas"] is True
    assert c.post("/partida", json={"semilla": 5, "nivel": 1, "tamano": "pequeno"}).status_code == 200
    assert c.get("/difuso/reglas").json()["personalizadas"] is False        # partida nueva: las del planeta
    from juego.comparacion import partida_variante
    assert all(r["peso"] == 1.0 for r in partida_variante(1, "hibrido", "congelado").mision.difuso.reglas)


def test_ia_paso_expone_la_clasificacion_por_celda_del_tramo():
    c = _cliente()
    c.post("/modo", json={"modo": "automatico"})
    c.post("/paso")
    d = c.get("/ia/paso").json()
    tramo = d["rna"]["tramo"]
    assert 1 <= len(tramo) <= 4 and [t["distancia"] for t in tramo] == sorted(t["distancia"] for t in tramo)
    assert tramo[0]["distancia"] == 1 and tramo[0]["celda"] == d["celda"]
    assert all(set(t["probabilidades"]) == {"libre", "obstáculo", "barranco"} for t in tramo)
