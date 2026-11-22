"""R23: planificador con restricciones (ventanas de tiempo, recarga obligatoria, sitios opcionales, reparación, diversidad)."""
import numpy as np

from planificacion import (AGRestringido, Distancias, Problema, SitioPlan, mejor_heuristico, orden_2opt, orden_vecino,
                           plan_heuristico)


def _problema(sitios, bases=(), bateria=100.0, capacidad=None, factor=1.0, t0=0, filas=12, cols=30):
    mascara = np.ones((filas, cols), dtype=bool)
    return Problema((filas - 1, 0), (0, cols - 1), sitios, list(bases), bateria, capacidad or bateria,
                    Distancias(mascara), factor, t0=t0)


def _sitios(celdas, valores=None, ventanas=None, obligatorios=None):
    return [SitioPlan(i + 1, c, float((valores or {}).get(i + 1, 5)), (ventanas or {}).get(i + 1),
                      (obligatorios or {}).get(i + 1, True)) for i, c in enumerate(celdas)]


def test_distancias_bfs_ocho_direcciones():
    d = Distancias(np.ones((10, 10), dtype=bool))
    assert d.largo((0, 0), (5, 5)) == 5
    assert d.largo((0, 0), (0, 9)) == 9
    muro = np.ones((5, 5), dtype=bool)
    muro[:, 2] = False
    assert Distancias(muro).largo((0, 0), (0, 4)) is None


def test_ventana_de_tiempo_vale_cien_por_ciento_dentro_y_un_cuarto_fuera():
    sitios = _sitios([(10, 5)], ventanas={1: (0, 30)})
    p = _problema(sitios)
    dentro = p.decodificar((1,), (True,), (-1, -1))
    assert dentro.factible and dentro.ventanas_falladas == 0 and dentro.ciencia == 1.0
    fuera = _problema(_sitios([(10, 5)], ventanas={1: (80, 120)})).decodificar((1,), (True,), (-1, -1))
    assert fuera.ventanas_falladas == 1 and abs(fuera.ciencia - 0.25) < 1e-9
    assert any("fuera de su ventana" in t for t in _problema(_sitios([(10, 5)], ventanas={1: (80, 120)})).textos(fuera))


def test_el_tiempo_de_llegada_cuenta_las_paradas_de_recarga():
    base = (6, 3)
    p = _problema(_sitios([(0, 10)], ventanas={1: (0, 100)}), bases=[base], bateria=30.0, capacidad=100.0)
    sin = p.decodificar((1,), (True,), (-1, -1))
    con = p.decodificar((1,), (True,), (0, -1))
    llegada = lambda pl: [n for n in pl.nodos if n[0] == "sitio"][0][3]
    assert llegada(con) >= llegada(sin) + p.recarga_pasos


def test_recarga_obligatoria_la_reparacion_inserta_una_base_cuando_la_bateria_no_alcanza():
    # el recorrido directo cuesta 29 y la reserva final 15: con batería 38 no cabe sin recargar
    sitios = _sitios([(6, 14), (3, 25)])
    bases = [(8, 8)]
    sin_base = _problema(sitios, [], bateria=38.0).decodificar((1, 2), (True, True), (-1, -1, -1))
    assert not sin_base.factible
    p = _problema(sitios, bases, bateria=38.0, capacidad=100.0)
    plan = p.decodificar((1, 2), (True, True), (-1, -1, -1))
    assert plan.factible and plan.recargas >= 1 and plan.reparaciones >= 1
    assert any(n[0] == "base" for n in plan.nodos)
    assert 0 in plan.paradas or any(g >= 0 for g in plan.paradas)       # lamarckiano: la reparación queda en el cromosoma
    # el cromosoma reparado ya no necesita reparación
    assert p.decodificar(plan.orden, plan.sel, plan.paradas).reparaciones == 0


def test_la_ruta_del_plan_pasa_por_las_bases_y_los_sitios():
    sitios = _sitios([(6, 14), (3, 25)])
    p = _problema(sitios, [(8, 8)], bateria=38.0, capacidad=100.0)
    plan = p.decodificar((1, 2), (True, True), (-1, -1, -1))
    ruta = p.ruta(plan)
    assert ruta[0] == p.inicio and ruta[-1] == p.refugio
    assert (8, 8) in ruta and (6, 14) in ruta and (3, 25) in ruta
    assert len(ruta) - 1 == plan.pasos


def test_sacrificio_el_opcional_que_no_cabe_se_descarta_y_el_obligatorio_no():
    celdas = [(6, 10), (11, 28)]
    sitios = _sitios(celdas, valores={1: 9, 2: 1}, obligatorios={1: True, 2: False})
    p = _problema(sitios, [], bateria=52.0)
    assert not p.decodificar((1, 2), (True, True), (-1, -1, -1)).factible          # con los dos no cabe
    todo = p.decodificar((1, 2), (True, False), (-1, -1, -1))
    assert todo.sacrificados == (2,) and todo.factible          # sacrificando el opcional el plan sigue
    assert 1 in todo.ids_visitados and 2 not in todo.ids_visitados
    # con todos obligatorios, lo mismo es infactible
    obl = _problema(_sitios(celdas, valores={1: 9, 2: 1}), [], bateria=52.0)
    assert not obl.decodificar((1, 2), (True, True), (-1, -1, -1)).factible


def test_plan_heuristico_descarta_opcionales_de_menor_valor_hasta_que_quepa():
    celdas = [(6, 10), (11, 28), (2, 6)]
    sitios = _sitios(celdas, valores={1: 9, 2: 1, 3: 2}, obligatorios={1: True, 2: False, 3: False})
    p = _problema(sitios, [], bateria=52.0)
    plan = plan_heuristico(p, [1, 2, 3])
    assert plan.factible and 1 in plan.ids_visitados


def test_ag_mejora_a_las_heuristicas_con_ventanas_y_recargas():
    rng = np.random.default_rng(3)
    celdas = [(int(rng.integers(0, 12)), int(rng.integers(2, 28))) for _ in range(10)]
    celdas = list(dict.fromkeys(celdas))
    base = _problema(_sitios(celdas), [(5, 10), (5, 20)], bateria=70.0, capacidad=70.0, factor=1.3)
    # ventanas alrededor de los tiempos de un orden poco corto (invertido)
    ref = base.decodificar(tuple(reversed([s.id for s in base.sitios])), tuple([True] * base.n), tuple([-1] * (base.n + 1)))
    lleg = {n[2]: n[3] for n in ref.nodos if n[0] == "sitio"}
    sitios = [SitioPlan(s.id, s.celda, s.valor, (max(0, lleg[s.id] - 15), lleg[s.id] + 15) if s.id in lleg else None, True)
              for s in base.sitios]
    p = _problema(sitios, [(5, 10), (5, 20)], bateria=70.0, capacidad=70.0, factor=1.3)
    res = AGRestringido(p, semilla=1).optimizar()
    assert res.mejor.factible
    mejores_heur = max(mejor_heuristico(p, h).fitness for h in ("vecino", "2opt"))
    assert res.mejor.fitness > mejores_heur + 0.02


def test_ag_es_determinista_por_semilla():
    celdas = [(2, 5), (9, 8), (4, 20), (10, 25), (1, 14), (7, 3)]
    mk = lambda: _problema(_sitios(celdas), [(5, 12)], bateria=60.0, capacidad=60.0, factor=1.2)
    a = AGRestringido(mk(), poblacion=30, generaciones=15, semilla=7).optimizar()
    b = AGRestringido(mk(), poblacion=30, generaciones=15, semilla=7).optimizar()
    assert a.mejor.clave == b.mejor.clave and a.mejor.fitness == b.mejor.fitness


def test_diversidad_no_colapsa_en_las_primeras_generaciones_y_la_poblacion_no_tiene_duplicados():
    rng = np.random.default_rng(11)
    celdas = list(dict.fromkeys((int(rng.integers(0, 12)), int(rng.integers(2, 28))) for _ in range(11)))
    p = _problema(_sitios(celdas), [(5, 10), (5, 20)], bateria=70.0, capacidad=70.0, factor=1.3)
    res = AGRestringido(p, poblacion=40, generaciones=25, semilla=2).optimizar()
    for h in res.historial:
        assert h["distintos"] == 40                       # ningún duplicado en la población
    # el problema del evaluador: «en la generación 5 toda la población es idéntica». Aquí sigue habiendo diversidad
    assert res.historial[5]["diversidad"] > 0.1 and res.historial[-1]["diversidad"] > 0.1
    mejores = [h["mejor"] for h in res.historial]
    assert mejores == sorted(mejores)                     # elitismo: el mejor nunca baja
    assert mejores[-1] > mejores[0]                       # y hay mejora a lo largo de las generaciones


def test_pocos_sitios_no_se_cuelga_aunque_el_espacio_sea_chico():
    p = _problema(_sitios([(5, 5)]), [(3, 3)], bateria=100.0)
    res = AGRestringido(p, poblacion=30, generaciones=8, semilla=1).optimizar()
    assert res.mejor.factible
    vacio = _problema([], [(3, 3)], bateria=100.0)
    assert AGRestringido(vacio, poblacion=30, generaciones=5, semilla=1).optimizar().mejor.factible


def test_orden_vecino_y_2opt_visitan_todos_una_vez():
    celdas = [(2, 5), (9, 8), (4, 20), (10, 25)]
    p = _problema(_sitios(celdas))
    assert sorted(orden_vecino(p)) == [1, 2, 3, 4] and sorted(orden_2opt(p)) == [1, 2, 3, 4]
