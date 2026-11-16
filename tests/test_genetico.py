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
