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
    assert df["fitness_ag"].notna().all() and np.isfinite(df["fitness_ag"].to_numpy(dtype=float)).all()
    assert df["fitness_ag"].abs().sum() > 0          # el AG tuvo plan: no todo es relleno
    inferidas = df[df["accion"] == "avanzar"]        # filas donde el difuso corrió en avanzar_ia
    assert len(inferidas) > 0
    mu = inferidas[COLUMNAS_MEMBRESIA]
    assert mu.notna().all().all()
    assert np.isfinite(mu.to_numpy(dtype=float)).all()
    assert ((mu >= 0) & (mu <= 1)).all().all()


def test_filas_con_inferencia_traen_membresias_reales():
    df = _escenario_corto()
    avance = df[df["accion"] == "avanzar"]
    assert len(avance) > 0
    assert (avance[COLUMNAS_MEMBRESIA].sum(axis=1) > 0).all()


def test_modo_difuso_suelto_registra_las_membresias_reales():
    p = Partida(semilla=11)
    for _ in range(15):
        p.avanzar_modo("difuso")
    df = p.bitacora()
    con_difuso = df[df["motivos"].str.contains("D-VELOCIDAD")]      # filas donde el difuso corrió
    assert len(con_difuso) > 0
    assert (con_difuso[COLUMNAS_MEMBRESIA].sum(axis=1) > 0).all()
    assert df["fitness_ag"].notna().all()


def test_modo_rna_deja_vacias_las_membresias_no_cero_falso():
    p = Partida(semilla=11)
    for _ in range(8):
        p.avanzar_modo("rna")
    df = p.bitacora()
    assert df[COLUMNAS_MEMBRESIA].isna().all().all()


def test_aplanar_membresias_sin_datos_da_vacio():
    assert set(aplanar_membresias(None)) == set(COLUMNAS_MEMBRESIA)
    assert all(v is None for v in aplanar_membresias({}).values())
    assert aplanar_membresias({"distancia": {"cerca": float("nan")}})["mu_distancia_cerca"] is None
    assert aplanar_membresias({"distancia": {"cerca": 0.0}})["mu_distancia_cerca"] == 0.0
