import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rna import (  # noqa: E402
    NOMBRES_RASGOS, NOMBRES_RASGOS_TERRENO, NeuralPerception, generar_dataset,
    particion_por_mapas,
)


def test_particion_por_mapas_sin_solapamiento():
    train, valid, test = particion_por_mapas(total_mapas=60)
    assert len(set(train) & set(valid)) == 0
    assert len(set(train) & set(test)) == 0
    assert len(set(valid) & set(test)) == 0
    assert len(train) + len(valid) + len(test) == 60


def test_dataset_reproducible_y_sin_nan():
    X1, y1 = generar_dataset([0, 1], muestras_por_mapa=50)
    X2, y2 = generar_dataset([0, 1], muestras_por_mapa=50)
    assert np.array_equal(X1, X2) and np.array_equal(y1, y2)
    assert not np.isnan(X1).any()


def test_rna_entrena_y_supera_linea_base():
    tr, va, te = particion_por_mapas(total_mapas=30)
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=300)
    Xte, yte = generar_dataset(te, muestras_por_mapa=300)
    rna = NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    res = rna.evaluar(Xte, yte)
    assert res.matriz_confusion.shape == (3, 3)
    assert 0.0 <= res.macro_f1 <= 1.0
    assert res.macro_f1 > 0.4  # mejor que azar entre 3 clases desbalanceadas
    assert 0.0 <= res.recall_barranco <= 1.0


def test_prediccion_devuelve_probabilidades_que_suman_uno():
    tr, _, _ = particion_por_mapas(total_mapas=10)
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=200)
    rna = NeuralPerception(semilla=0).entrenar(Xtr, ytr)
    p = rna.predecir_proba(Xtr[0])
    assert p.shape == (1, 3)
    assert p.sum() == pytest.approx(1.0)


def test_sin_entrenar_lanza_error_claro():
    with pytest.raises(RuntimeError, match="no está entrenada"):
        NeuralPerception().predecir_proba(np.zeros(4))


def test_explicacion_contiene_evidencia():
    tr, _, _ = particion_por_mapas(total_mapas=10)
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=200)
    rna = NeuralPerception(semilla=0).entrenar(Xtr, ytr)
    e = rna.explicar(Xtr[0])
    assert set(e) == {"entrada", "normalizada", "probabilidades", "confianza"}
    assert sum(e["probabilidades"].values()) == pytest.approx(1.0, abs=0.01)


def test_perfil_actual_no_cambia_y_terreno_quita_el_borde():
    Xa, ya = generar_dataset([0, 1], muestras_por_mapa=50)
    Xt, yt = generar_dataset([0, 1], muestras_por_mapa=50, perfil="terreno")
    assert Xa.shape[1] == len(NOMBRES_RASGOS) == 4
    assert Xt.shape[1] == len(NOMBRES_RASGOS_TERRENO) == 3
    assert np.array_equal(ya, yt)
    assert np.array_equal(Xt, Xa[:, [0, 2, 3]])
    with pytest.raises(ValueError):
        generar_dataset([0], perfil="otro")


def test_explicacion_del_modelo_terreno_tiene_tres_entradas():
    Xtr, ytr = generar_dataset(range(10), muestras_por_mapa=200, perfil="terreno")
    rna = NeuralPerception(semilla=0, nombres=NOMBRES_RASGOS_TERRENO).entrenar(Xtr, ytr)
    e = rna.explicar(Xtr[0])
    assert list(e["entrada"]) == NOMBRES_RASGOS_TERRENO
    assert "borde_barranco" not in e["normalizada"]


def test_recall_sin_borde_con_firma_fisica_en_20_mapas(monkeypatch):
    import simulador
    monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", True)
    tr, _, te = particion_por_mapas(total_mapas=60)
    assert len(te) >= 9
    te = np.arange(100, 120)  # 20 mapas de prueba distintos de los de entrenamiento
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=400, perfil="terreno")
    Xte, yte = generar_dataset(te, muestras_por_mapa=400, perfil="terreno")
    rna = NeuralPerception(semilla=42, nombres=NOMBRES_RASGOS_TERRENO).entrenar(Xtr, ytr)
    res = rna.evaluar(Xte, yte)
    assert res.recall_barranco >= 0.7  # umbral escrito antes (medido 0,842 fuera de línea)
