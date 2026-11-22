"""R23: parámetros del difuso y de la conducción por planeta (genes, carga desde JSON, ablación por defecto, aislamiento)."""
import json

import numpy as np
import pytest

import difuso
from difuso import FuzzyController
from juego import difuso_planetas as dp
from juego.partida import Partida


def _grilla():
    return [(d, b, i) for d in (0.5, 2, 5, 9, 14, 20) for b in (5, 25, 45, 80, 100) for i in (0, 6, 15, 30, 44)]


def test_el_vector_por_defecto_reproduce_exactamente_el_difuso_original():
    base, gen = FuzzyController(), FuzzyController(params=dp.por_defecto()["difuso"])
    for d, b, i in _grilla():
        assert base.inferir(d, b, i).velocidad == pytest.approx(gen.inferir(d, b, i).velocidad, abs=1e-12)


def test_cualquier_vector_dentro_de_rango_da_un_difuso_valido():
    rng = np.random.default_rng(0)
    for _ in range(300):
        v = dp.MINIMOS + rng.random(len(dp.MINIMOS)) * (dp.MAXIMOS - dp.MINIMOS)
        c = FuzzyController(params=dp.a_parametros(v)["difuso"])
        assert 0.0 <= c.inferir(5.0, 50.0, 10.0).velocidad <= 1.0


def test_los_pesos_multiplican_la_fuerza_de_la_regla():
    c = FuzzyController(params={"reglas": [{"id": "R1", "peso": 0.5}]})
    r = c.inferir(1.0, 60.0, 5.0).reglas_activadas
    fuerza_base = dict((i, f) for i, f, _ in FuzzyController().inferir(1.0, 60.0, 5.0).reglas_activadas)["R1"]
    assert dict((i, f) for i, f, _ in r)["R1"] == pytest.approx(0.5 * fuerza_base)


def test_params_invalidos_dan_un_mensaje_claro_y_no_cambian_nada():
    c = FuzzyController()
    antes = c.como_dict()
    for malo, texto in [({"variables": {"viento": {}}}, "variable desconocida"),
                        ({"variables": {"distancia": {"etiquetas": {"cerca": [5, 3, 1, 0]}}}}, "menor a mayor"),
                        ({"variables": {"distancia": {"etiquetas": {"cerca": [0, 0, 3, 99]}}}}, "dentro del universo"),
                        ({"reglas": [{"id": "R1", "peso": 2}]}, "entre 0 y 1"),
                        ({"reglas": [{"id": "X9", "si": {"distancia": "inventada"}, "entonces": "parar"}]}, "desconocida"),
                        ({"reglas": [{"id": "R1", "activa": False}]}, "al menos una regla")]:
        with pytest.raises(ValueError, match=texto):
            c.aplicar(malo)
    assert c.como_dict() == antes


def test_la_partida_carga_los_parametros_del_planeta_desde_el_json(tmp_path, monkeypatch):
    ruta = tmp_path / "difuso_planetas.json"
    vector = dp.DEFECTO.copy()
    vector[dp.NOMBRES.index("v_hielo")] = 0.3
    vector[dp.NOMBRES.index("peso_R4")] = 0.5
    ruta.write_text(json.dumps({"version": 1, "planetas": {"Marte": dp.a_parametros(vector)}}), encoding="utf-8")
    monkeypatch.setattr(dp, "RUTA_JSON", str(ruta))
    dp._cache.clear()
    p = Partida(semilla=3, nivel=1, planeta="Marte")
    assert p.difuso_evolucionado and p.conduccion["v_hielo"] == 0.3
    assert next(r for r in p.mision.difuso.reglas if r["id"] == "R4")["peso"] == 0.5
    assert "regla.R4" in p.parametros_difuso and p.parametros_difuso["conduccion.v_hielo"] == 0.3
    otro = Partida(semilla=3, nivel=1, planeta="Tierra")             # sin parámetros en el archivo: el de defecto
    assert not otro.difuso_evolucionado and otro.conduccion == {}
    base = Partida(semilla=3, nivel=1, planeta="Marte", difuso_evolucionado=False)   # ablación: sin evolucionar
    assert not base.difuso_evolucionado and all(r["peso"] == 1.0 for r in base.mision.difuso.reglas)
    dp._cache.clear()


def test_el_tope_de_velocidad_sobre_hielo_actua_solo_con_hielo_en_la_siguiente_celda():
    vector = dp.DEFECTO.copy()
    vector[dp.NOMBRES.index("v_hielo")] = 0.25
    p = Partida(semilla=3, nivel=2, planeta="Tierra", ajustes_difuso=dp.a_parametros(vector))
    hielo = next(iter(p.mecanicas.celdas_hielo()), None)
    assert hielo is not None
    p.mision.ruta = [tuple(p.rover.posicion), tuple(hielo)]
    assert p._topes_conduccion(0.9, 0.0) == 0.25
    libre = next((int(f), int(c)) for f, c in np.argwhere(p.mundo.tipo == 0) if not p.mecanicas.hay_hielo((f, c)))
    p.mision.ruta = [tuple(p.rover.posicion), libre]
    assert p._topes_conduccion(0.9, 0.0) == 0.9 or p.mecanicas.viento_actual >= dp.UMBRAL_VIENTO


def test_reglas_editadas_en_una_partida_no_afectan_a_otras_ni_a_las_constantes():
    a, b = Partida(semilla=3, nivel=1), Partida(semilla=3, nivel=1)
    nuevo = a.mision.difuso.copia()
    nuevo.aplicar({"reglas": [{"id": "R1", "peso": 0.2}, {"id": "R4", "activa": False}]})
    a.poner_difuso(nuevo)
    assert a.mision.difuso.personalizado and not b.mision.difuso.personalizado
    assert all(r["peso"] == 1.0 and r["activa"] for r in b.mision.difuso.reglas)
    assert len(difuso.REGLAS) == 11 and "peso" not in difuso.REGLAS[0]
    a.restaurar_difuso()
    assert not a.mision.difuso.personalizado and len(a.mision.difuso.reglas) == 11
