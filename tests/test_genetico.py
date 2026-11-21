import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genetico import GeneticPlanner, camino_bfs, mapa_estimado  # noqa: E402
from simulador import BARRANCO, LIBRE, OBSTACULO, generar_mundo  # noqa: E402


def mundo_vacio(filas=10, columnas=12):
    m = generar_mundo(semilla=0, filas=filas, columnas=columnas, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    return m


def test_bfs_encuentra_camino_y_respeta_muros():
    trans = np.ones((5, 5), dtype=bool)
    trans[:, 2] = False
    trans[4, 2] = True  # único paso abajo
    camino = camino_bfs((0, 0), (0, 4), trans)
    assert camino[0] == (0, 0) and camino[-1] == (0, 4)
    assert all(trans[c] for c in camino)
    assert (4, 2) in camino


def test_bfs_sin_camino_devuelve_none():
    trans = np.ones((3, 3), dtype=bool)
    trans[:, 1] = False
    assert camino_bfs((0, 0), (0, 2), trans) is None


def test_mapa_estimado_marca_detectados_y_nunca_fuera_de_rango():
    m = generar_mundo(semilla=7)
    riesgo = mapa_estimado(m, np.random.default_rng(0))
    assert riesgo.min() >= 0.0 and riesgo.max() <= 1.0
    assert riesgo.shape == m.forma


def test_requiere_poblacion_y_generaciones_minimas():
    m = mundo_vacio()
    with pytest.raises(ValueError, match="30"):
        GeneticPlanner(m, np.zeros(m.forma), poblacion=10)


def test_decodificacion_produce_ruta_contigua_y_sin_atravesar_riesgo():
    m = mundo_vacio()
    riesgo = np.zeros(m.forma)
    riesgo[5, :] = 1.0
    riesgo[5, 6] = 0.0  # hueco estrecho
    gp = GeneticPlanner(m, riesgo, k_puntos=2, semilla=0)
    d = gp.decodificar([(7, 6)])
    for a, b in zip(d.ruta, d.ruta[1:]):
        assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1   # ocho direcciones
    assert all(riesgo[c] < 0.5 for c in d.ruta)


def test_punto_inalcanzable_se_repara_descartandolo():
    m = mundo_vacio()
    riesgo = np.zeros(m.forma)
    riesgo[:, 5] = 1.0  # muro completo: el lado derecho es inalcanzable
    gp = GeneticPlanner(m, riesgo, k_puntos=2, semilla=0)
    d = gp.decodificar([(3, 8)])
    assert d.reparaciones == 1
    assert d.inviable_sin_camino is True


def test_fitness_penaliza_bateria_insuficiente():
    m = mundo_vacio()
    gp = GeneticPlanner(m, np.zeros(m.forma), bateria=5.0, k_puntos=2, semilla=0,
                        poblacion=30, generaciones=30)
    des = gp.evaluar([(0, 9), (9, 0)])
    assert des.penalizacion >= 1.0


def test_optimizacion_mejora_y_devuelve_componentes():
    m = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    rng = np.random.default_rng(11)
    riesgo = mapa_estimado(m, rng)
    gp = GeneticPlanner(m, riesgo, bateria=100, k_puntos=3, poblacion=30, generaciones=30, semilla=11)
    res = gp.optimizar()
    primera, ultima = res.historial[0]["mejor"], res.historial[-1]["mejor"]
    assert ultima >= primera - 1e-9              # elitismo: el mejor nunca empeora
    assert len(res.candidatos) >= 3              # RF-07: al menos tres rutas candidatas
    assert res.mejor_ruta[0] == m.inicio
    assert res.mejor_ruta[-1] == m.refugio


def test_mismo_seed_mismo_resultado():
    m = generar_mundo(semilla=3, n_sitios=2)
    riesgo = mapa_estimado(m, np.random.default_rng(3))
    a = GeneticPlanner(m, riesgo, semilla=5, poblacion=30, generaciones=30).optimizar()
    b = GeneticPlanner(m, riesgo, semilla=5, poblacion=30, generaciones=30).optimizar()
    assert a.mejor == b.mejor


# ---------- ARX-92b: decodificación completa y reparación (M8) ----------
def mundo_con_sitios(sitios):
    m = mundo_vacio()
    m.sitios = dict(sitios)
    return m


def test_decodificar_inserta_los_sitios_omitidos():
    m = mundo_con_sitios({(2, 3): 1.0, (7, 8): 1.0, (4, 10): 1.0})
    gp = GeneticPlanner(m, np.zeros(m.forma), k_puntos=1, semilla=0)
    d = gp.decodificar([(5, 5)])           # el cromosoma no contiene ningún sitio
    assert not d.inviable_sin_camino
    assert set(d.orden_sitios) == set(m.sitios)
    assert all(s in d.ruta for s in m.sitios)
    assert d.insertados >= 1 and d.reparaciones == d.descartes + d.insertados
    assert d.ruta[0] == m.inicio and d.ruta[-1] == m.refugio
    for a, b in zip(d.ruta, d.ruta[1:]):
        assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1


def test_sitio_ya_cubierto_por_la_ruta_no_se_inserta():
    m = mundo_vacio()
    gp0 = GeneticPlanner(m, np.zeros(m.forma), k_puntos=1, semilla=0)
    base = gp0.decodificar([]).ruta
    sitio = base[len(base) // 2]
    m.sitios = {sitio: 1.0}
    gp = GeneticPlanner(m, np.zeros(m.forma), k_puntos=1, semilla=0)
    d = gp.decodificar([])
    assert d.insertados == 0 and d.orden_sitios == [sitio]


def test_sitio_inalcanzable_deja_la_ruta_inviable():
    m = mundo_vacio()
    riesgo = np.zeros(m.forma)
    riesgo[0:3, 8:11] = 1.0
    m.sitios = {(1, 9): 1.0}               # dentro de una zona no transitable
    riesgo[1, 9] = 0.0
    riesgo[0, 8:11] = riesgo[2, 8:11] = riesgo[1, 8] = riesgo[1, 10] = 1.0
    gp = GeneticPlanner(m, riesgo, k_puntos=1, semilla=0)
    d = gp.decodificar([])
    assert d.inviable_sin_camino is True
    assert d.insertados == 0
    assert gp.evaluar([]).penalizacion >= 1.0


def test_evaluar_y_ag_exponen_contadores_y_no_devuelven_rutas_incompletas():
    m = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    riesgo = mapa_estimado(m, np.random.default_rng(11))
    gp = GeneticPlanner(m, riesgo, bateria=100, k_puntos=3, semilla=11)
    res = gp.optimizar()
    for cromosoma, des in res.candidatos:
        d = gp.decodificar(cromosoma)
        assert d.inviable_sin_camino or set(d.orden_sitios) == set(m.sitios)
        assert des.descartes + des.insertados == des.reparaciones
        assert des.insertados == d.insertados
    assert hasattr(res.mejor_desglose, "insertados")


# ---------- ARX-92c: modo «orden» (permutación de sitios) ----------
import itertools  # noqa: E402


def _mundo_orden(semilla, n_sitios=3):
    m = generar_mundo(semilla=semilla, n_obstaculos=20, n_barrancos=4, n_sitios=n_sitios)
    return m, mapa_estimado(m, np.random.default_rng(semilla))


def _gp_orden(m, riesgo, semilla=0, **kw):
    return GeneticPlanner(m, riesgo, bateria=1000.0, poblacion=30, generaciones=30, semilla=semilla, **kw)


def _optimo_exhaustivo(gp):
    """Mayor fitness entre todas las permutaciones (ruta = unión por BFS con refugio)."""
    mejor = None
    for orden in itertools.permutations(gp.mundo.sitios):
        ruta = gp._unir([gp.mundo.inicio] + list(orden) + [gp.mundo.refugio])
        if ruta is None:
            continue
        f = gp.evaluar_ruta(ruta).fitness
        mejor = f if mejor is None else max(mejor, f)
    return mejor


@pytest.mark.parametrize("semilla", range(1, 21))
def test_orden_con_tres_sitios_alcanza_el_optimo_de_la_exhaustiva(semilla):
    m, riesgo = _mundo_orden(semilla)
    gp = _gp_orden(m, riesgo, semilla)
    optimo = _optimo_exhaustivo(gp)
    if optimo is None:
        pytest.skip("sin permutación alcanzable")
    res = gp.optimizar_orden()
    assert res.viable and res.modo == "orden"
    assert res.mejor_desglose.fitness == pytest.approx(optimo, abs=1e-9)


def test_orden_candidatos_son_ordenes_completos_y_sin_repetir():
    m, riesgo = _mundo_orden(4, n_sitios=4)
    res = _gp_orden(m, riesgo, 4).optimizar_orden(con_paso=True)
    assert len(res.candidatos) >= 3
    ordenes = [tuple(c[0]) for c, _ in res.candidatos]
    assert len(set(ordenes)) == len(ordenes)
    for orden in ordenes:
        assert sorted(orden) == sorted(m.sitios)          # todos los sitios, ninguno omitido ni repetido
    for gen in res.historial:
        for ind in gen["poblacion"]:
            assert sorted(map(tuple, ind["cromosoma"])) == sorted(m.sitios)
    assert all(c in res.mejor_ruta for c in m.sitios)


def test_orden_determinista_por_semilla_y_cambia_con_otra():
    m, riesgo = _mundo_orden(6, n_sitios=4)
    a = _gp_orden(m, riesgo, 5).optimizar_orden(con_paso=True)
    b = _gp_orden(m, riesgo, 5).optimizar_orden(con_paso=True)
    assert a.mejor == b.mejor and a.mejor_ruta == b.mejor_ruta
    assert [g["mejor"] for g in a.historial] == [g["mejor"] for g in b.historial]
    c = _gp_orden(m, riesgo, 6).optimizar_orden(con_paso=True)
    assert [g["poblacion"] for g in a.historial] != [g["poblacion"] for g in c.historial]


def test_orden_elitismo_y_operadores_cuentan():
    m, riesgo = _mundo_orden(7, n_sitios=4)
    gp = _gp_orden(m, riesgo, 7)
    res = gp.optimizar_orden(con_paso=True)
    mejores = [g["mejor"] for g in res.historial]
    assert all(b >= a - 1e-12 for a, b in zip(mejores, mejores[1:]))
    assert gp.cruces > 0 and gp.mutaciones > 0
    assert len(res.historial) == 30


def test_orden_con_punto_de_paso_da_ruta_contigua_que_visita_todo():
    m, riesgo = _mundo_orden(8, n_sitios=3)
    gp = _gp_orden(m, riesgo, 8)
    res = gp.optimizar_orden(con_paso=True)
    ruta = res.mejor_ruta
    assert ruta[0] == m.inicio and ruta[-1] == m.refugio
    for a, b in zip(ruta, ruta[1:]):
        assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1
    assert all(riesgo[c] < 0.5 for c in ruta)
    assert all(s in ruta for s in m.sitios)


def test_orden_inviable_por_bateria_no_puede_ganar_y_se_declara():
    m, riesgo = _mundo_orden(9, n_sitios=3)
    gp = GeneticPlanner(m, riesgo, bateria=3.0, poblacion=30, generaciones=30, semilla=9)
    res = gp.optimizar_orden()
    assert res.viable is False and res.mejor_ruta == [] and res.candidatos == []


def test_orden_restriccion_dura_elige_el_unico_orden_viable():
    m, riesgo = _mundo_orden(10, n_sitios=3)
    gp = _gp_orden(m, riesgo, 10)
    unico = tuple(m.sitios)[::-1]

    def construir(seq):
        visitas = tuple(c for c in seq if c in m.sitios)
        return gp._unir([m.inicio] + list(seq)) if visitas == unico else None

    res = gp.optimizar_orden(construir)
    assert res.viable and tuple(map(tuple, res.mejor[0:3])) == unico


def test_orden_desempate_prefiere_la_mas_corta_dentro_del_umbral():
    m, riesgo = _mundo_orden(11, n_sitios=3)
    gp = _gp_orden(m, riesgo, 11)
    ancho = gp.optimizar_orden(umbral_empate=10.0)           # todo empata: gana la ruta más corta
    largos = [len(gp._unir([m.inicio] + list(o) + [m.refugio])) for o in itertools.permutations(m.sitios)]
    assert len(ancho.mejor_ruta) == min(largos)


# ---------- ARX-94c: mapa estimado por profundidad ----------

def test_mapa_estimado_detecta_por_profundidad_y_es_reproducible():
    import simulador
    from genetico import P_DETECTAR_SOMERO, PROFUNDIDAD_ORBITAL_M
    from simulador import BARRANCO, LIBRE, OBSTACULO
    assert (PROFUNDIDAD_ORBITAL_M, P_DETECTAR_SOMERO) == (2.0, 0.3)
    m = generar_mundo(semilla=1, filas=60, columnas=60, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    m.profundidad[:] = 0.0
    m.tipo[:, :20] = BARRANCO
    m.profundidad[:, :20] = 1.5       # somero: p 0,3
    m.tipo[:, 20:40] = BARRANCO
    m.profundidad[:, 20:40] = 3.0     # profundo: p 0,8
    m.tipo[:, 40:] = OBSTACULO        # obstáculo: p 0,8
    a = mapa_estimado(m, np.random.default_rng(4))
    assert np.array_equal(a, mapa_estimado(m, np.random.default_rng(4)))
    assert (a[:, :20] == 1.0).mean() == pytest.approx(0.3, abs=0.05)
    assert (a[:, 20:40] == 1.0).mean() == pytest.approx(0.8, abs=0.05)
    assert (a[:, 40:] == 1.0).mean() == pytest.approx(0.8, abs=0.05)


def test_mapa_estimado_con_mundo_v1_reproduce_el_mapa_anterior(monkeypatch):
    import simulador
    from simulador import LIBRE
    monkeypatch.setattr(simulador, "MUNDO_V1", True)
    m = generar_mundo(semilla=7)
    rng = np.random.default_rng(11)
    esperado = np.full(m.forma, 0.05)
    for f, c in np.argwhere(m.tipo != LIBRE):       # la definición anterior, tal cual
        if rng.random() < 0.8:
            esperado[f, c] = 1.0
    assert np.array_equal(mapa_estimado(m, np.random.default_rng(11)), esperado)
