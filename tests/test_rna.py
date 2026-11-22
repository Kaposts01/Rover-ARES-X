import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rna import (  # noqa: E402
    NOMBRES_RASGOS, NOMBRES_RASGOS_TERRENO, NOMBRES_RASGOS_V1, NOMBRES_RASGOS_V2, PERFILES_RASGOS,
    NeuralPerception, _rasgos_celda_v2, generar_dataset, particion_por_mapas,
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


def test_perfil_v1_y_terreno_quita_el_borde():
    Xa, ya = generar_dataset([0, 1], muestras_por_mapa=50, perfil="v1")
    Xt, yt = generar_dataset([0, 1], muestras_por_mapa=50, perfil="terreno")
    assert Xa.shape[1] == len(NOMBRES_RASGOS_V1) == 4
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


# ---------- ARX-94d: RNA v2 y perfiles v1 / v2 ----------

def test_rasgos_v2_son_los_cuatro_del_plan_y_el_perfil_por_defecto():
    assert NOMBRES_RASGOS_V2 == ["proximidad_frontal_m", "desnivel_frontal_m", "contraste_optico", "vibracion"]
    assert NOMBRES_RASGOS == NOMBRES_RASGOS_V2 and PERFILES_RASGOS["v2"] == NOMBRES_RASGOS_V2
    assert PERFILES_RASGOS["v1"] == NOMBRES_RASGOS_V1 and "borde_barranco" in NOMBRES_RASGOS_V1
    X, y = generar_dataset([0, 1], muestras_por_mapa=50)
    assert X.shape[1] == 4 and set(y) <= {0, 1, 2}
    assert np.array_equal(X, generar_dataset([0, 1], muestras_por_mapa=50, perfil="v2")[0])


def test_v1_se_reproduce_con_mundo_v1_igual_que_antes_de_94():
    # huella del dataset de la entrega del 17/11 (generada con el rna.py y el simulador de main, antes de ARX-94)
    X, y = generar_dataset([0, 1, 2], muestras_por_mapa=60, perfil="v1")
    assert X.shape == (164, 4)
    assert float(X.sum()) == pytest.approx(2225.445427, abs=1e-5)
    import simulador
    assert simulador.MUNDO_V1 is False          # el perfil v1 fija el mundo v1 y lo restaura
    assert np.array_equal(X, generar_dataset([0, 1, 2], muestras_por_mapa=60, perfil="actual")[0])


def test_rasgos_v2_no_dependen_del_tipo_salvo_la_proximidad_y_la_etiqueta():
    """Con la misma lectura (misma semilla del sensor), cambiar el tipo de la celda siguiente no cambia el
    desnivel, el contraste ni la vibración: salen de la geometría y de la celda actual."""
    import copy
    from simulador import BARRANCO, LIBRE, SensorSuite, generar_mundo
    mundo = generar_mundo(semilla=3)
    pos = next((f, c) for f in range(2, 18) for c in range(2, 28)
               if mundo.tipo[f, c] == LIBRE and mundo.tipo[f - 1, c] == LIBRE)
    otro = copy.deepcopy(mundo)
    otro.tipo[pos[0] - 1, pos[1]] = BARRANCO            # solo el tipo; la geometría no cambia
    a, ya = _rasgos_celda_v2(mundo, pos, "N", SensorSuite(rng=np.random.default_rng(5)))
    b, yb = _rasgos_celda_v2(otro, pos, "N", SensorSuite(rng=np.random.default_rng(5)))
    assert a == b and ya == LIBRE and yb == BARRANCO     # la etiqueta sí sale del tipo real


def test_vibracion_v2_es_de_la_celda_actual_con_sigma_03():
    X, _ = generar_dataset(range(20), muestras_por_mapa=300, perfil="v2")
    vib = X[:, 3]
    assert abs(vib.mean()) < 0.05 and vib.std() == pytest.approx(0.3, abs=0.03)


def test_modelo_v2_declara_su_perfil_y_explica_con_los_rasgos_nuevos():
    Xtr, ytr = generar_dataset(range(10), muestras_por_mapa=200)
    rna = NeuralPerception(semilla=0, nombres=NOMBRES_RASGOS_V2, perfil="v2").entrenar(Xtr, ytr)
    assert rna.perfil == "v2"
    assert list(rna.explicar(Xtr[0])["entrada"]) == NOMBRES_RASGOS_V2
    # un NaN (borde del mapa o falla de sensor) no rompe la predicción: se trata como al entrenar
    assert rna.predecir_proba([5.0, float("nan"), float("nan"), 0.0]).shape == (1, 3)


def test_rna_entrenada_por_defecto_es_v2_y_v1_se_pide_aparte():
    import simulador
    from integracion import rna_entrenada
    assert rna_entrenada().perfil == "v2" and rna_entrenada().nombres == NOMBRES_RASGOS_V2
    assert rna_entrenada(perfil="v1").nombres == NOMBRES_RASGOS_V1
    with pytest.raises(ValueError):
        rna_entrenada(perfil="v3")
    simulador.MUNDO_V1 = True
    try:
        assert rna_entrenada().perfil == "v1"           # con MUNDO_V1 el modelo del juego es el v1
    finally:
        simulador.MUNDO_V1 = False


# ---------- R23: la RNA debe ver el barranco (refuerzo de entrenamiento y regresión del barranco forzado) ----------

def test_refuerzo_barranco_no_cambia_las_muestras_naturales_y_solo_agrega_barrancos():
    X0, y0 = generar_dataset([0, 1], muestras_por_mapa=80)
    X1, y1 = generar_dataset([0, 1], muestras_por_mapa=80, refuerzo_barranco=15)
    assert len(y1) == len(y0) + 30
    assert np.array_equal(X1[:len(y0)], X0) and np.array_equal(y1[:len(y0)], y0)   # las naturales, intactas
    assert set(y1[len(y0):]) == {2}                                                  # el refuerzo es solo barranco
    Xb, yb = generar_dataset([0, 1], muestras_por_mapa=80, refuerzo_barranco=15)
    assert np.array_equal(X1, Xb) and np.array_equal(y1, yb)                         # reproducible (semilla fija)


def test_refuerzo_no_usa_mapas_de_prueba():
    from rna import SEMILLA_BASE_REFUERZO
    tr, va, te = particion_por_mapas(total_mapas=60)
    assert SEMILLA_BASE_REFUERZO > 200                  # lejos de las semillas de prueba (51-59 y 100-199)


def test_recall_de_barranco_con_refuerzo_en_los_mapas_de_prueba():
    """Mapas de prueba del laboratorio (51-59, natural): antes 19/30 = 63 %; medido ahora 25/30 = 83 %.
    En 60 mapas nunca vistos (100-159): 87-90 %. Los falsos barrancos entre celdas libres quedan en ~2 %."""
    from rna import REFUERZO_BARRANCO_POR_MAPA
    tr, _, te = particion_por_mapas(total_mapas=60)
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=400, refuerzo_barranco=REFUERZO_BARRANCO_POR_MAPA)
    rna = NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    res = rna.evaluar(*generar_dataset(te, muestras_por_mapa=400))
    m = res.matriz_confusion
    assert res.recall_barranco >= 0.80 and m[2].sum() == 30
    assert m[0, 0] / m[0].sum() >= 0.95                 # la celda libre sigue bien clasificada
    assert m[1, 1] / m[1].sum() >= 0.95                 # el obstáculo no empeora
    grande = rna.evaluar(*generar_dataset(np.arange(100, 160), muestras_por_mapa=400))
    assert grande.recall_barranco >= 0.85
    assert grande.matriz_confusion[0, 2] / grande.matriz_confusion[0].sum() <= 0.03   # falsos barrancos acotados


def test_barranco_forzado_delante_del_rover_la_rna_no_dice_libre_con_certeza():
    """Regresión R23. El evaluador forzó un barranco delante del rover y la RNA seguía en «libre 100 %».
    Los barrancos poco profundos (1,0 a 1,5 m) se confundían con la pendiente y la red, entrenada con ~1 % de
    barrancos, los daba por libres con confianza total. El barranco profundo debe marcarse siempre, y ninguno
    puede quedar en «libre» con más de 0,9 de confianza."""
    from juego.partida import Partida
    profundos = marcados = 0
    for semilla in range(1, 13):
        p = Partida(semilla=semilla, nivel=1)
        for _ in range(4):
            p.avanzar_ia()
        celda = tuple(p.mision.ruta[1])
        if celda in p.mundo.sitios or celda in (p.mundo.inicio, p.mundo.refugio):
            continue
        p.mundo.marcar_barranco(celda)                  # mismo camino que el evento: baja la elevación de la celda
        s = p.sugerencia()
        assert s["p_libre"] < 0.9, (semilla, s["p_libre"])
        if p.mundo.profundidad[celda] >= 1.5:
            profundos += 1
            marcados += s["p_barranco"] > 0.5
    assert profundos >= 5 and marcados == profundos
