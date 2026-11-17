"""ARX-80 (M3): la bitácora lleva el fitness del AG y las membresías difusas de cada paso."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from difuso import COLUMNAS_MEMBRESIA, aplanar_membresias  # noqa: E402
from juego.partida import Partida  # noqa: E402

COLUMNAS_VIEJAS = ["paso", "estado", "posicion", "bateria", "accion", "velocidad",
                   "p_barranco", "p_obstaculo", "reglas", "motivos"]
NUEVAS = ["fitness_ag"] + COLUMNAS_MEMBRESIA


def _escenario_corto(pasos=25):
    p = Partida(semilla=11)
    for _ in range(pasos):
        if p.estado in ("EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"):
            break
        p.avanzar_ia()
    return p.bitacora()


def test_columnas_nuevas_presentes_y_las_viejas_intactas():
    df = _escenario_corto()
    assert len(df) > 5
    assert set(NUEVAS) <= set(df.columns)
    assert list(df.columns)[:len(COLUMNAS_VIEJAS)] == COLUMNAS_VIEJAS


def test_valores_numericos_sin_nan_y_membresias_en_rango():
    df = _escenario_corto()
    nuevas = df[NUEVAS]
    assert nuevas.notna().all().all()
    assert all(np.issubdtype(t, np.number) for t in nuevas.dtypes)
    assert np.isfinite(nuevas.to_numpy(dtype=float)).all()
    assert ((df[COLUMNAS_MEMBRESIA] >= 0) & (df[COLUMNAS_MEMBRESIA] <= 1)).all().all()
    assert df["fitness_ag"].abs().sum() > 0          # el AG tuvo plan: no todo es relleno


def test_filas_con_inferencia_traen_membresias_reales():
    df = _escenario_corto()
    avance = df[df["accion"] == "avanzar"]
    assert len(avance) > 0
    assert (avance[COLUMNAS_MEMBRESIA].sum(axis=1) > 0).all()


def test_aplanar_membresias_sin_datos_da_ceros():
    assert set(aplanar_membresias(None)) == set(COLUMNAS_MEMBRESIA)
    assert all(v == 0.0 for v in aplanar_membresias({}).values())
    assert aplanar_membresias({"distancia": {"cerca": float("nan")}})["mu_distancia_cerca"] == 0.0
