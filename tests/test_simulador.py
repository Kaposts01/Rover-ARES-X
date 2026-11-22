import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulador import (  # noqa: E402
    BARRANCO, LIBRE, OBSTACULO, Rover, SensorSuite, generar_mundo,
    paso_fisico, validar_compatibilidad, MissionLogger,
)


def test_mapa_reproducible_con_misma_semilla():
    a = generar_mundo(semilla=42)
    b = generar_mundo(semilla=42)
    assert np.array_equal(a.tipo, b.tipo)
    assert a.sitios == b.sitios


def test_inicio_y_refugio_siempre_libres():
    for semilla in range(20):
        m = generar_mundo(semilla=semilla)
        assert m.tipo[m.inicio] == LIBRE
        assert m.tipo[m.refugio] == LIBRE


def test_rover_no_entra_a_barranco():
    m = generar_mundo(semilla=1)
    rover = Rover(posicion=m.inicio)
    m.marcar_barranco((m.inicio[0] - 1, m.inicio[1]))  # barranco justo al norte
    movido = paso_fisico(m, rover, "N")
    assert movido is False
    assert rover.posicion == m.inicio


def test_bateria_nunca_negativa_y_cero_no_mueve():
    m = generar_mundo(semilla=2)
    rover = Rover(posicion=m.inicio, bateria=1.0)
    paso_fisico(m, rover, "N", costo=5.0)
    assert rover.bateria == 0.0
    assert paso_fisico(m, rover, "E") is False


def test_sensor_detecta_obstaculo_en_linea():
    m = generar_mundo(semilla=3, n_obstaculos=0, n_barrancos=0)
    m.tipo[:] = LIBRE
    m.tipo[m.inicio[0] - 3, m.inicio[1]] = OBSTACULO
    sensor = SensorSuite(rng=np.random.default_rng(0), ruido=0.0)
    lectura = sensor.leer(m, m.inicio, rumbo="N")
    assert lectura["proximidad_frontal_m"] == pytest.approx(3.0)


def test_sensor_con_fallo_devuelve_nan_sin_excepcion():
    m = generar_mundo(semilla=4)
    sensor = SensorSuite(rng=np.random.default_rng(0), prob_fallo=1.0)
    lectura = sensor.leer(m, m.inicio)
    assert np.isnan(lectura["proximidad_frontal_m"])
    assert np.isnan(lectura["altimetria_m"])


def test_gigante_no_admite_rover():
    with pytest.raises(ValueError, match="sonda"):
        validar_compatibilidad("Júpiter", "rover")
    validar_compatibilidad("Júpiter", "sonda")  # no debe lanzar


def test_marte_admite_rover():
    validar_compatibilidad("Marte", "rover")


def test_mapa_sin_sitios_cientificos_no_falla():
    m = generar_mundo(semilla=6, n_sitios=0)
    assert m.sitios == {}


def test_bitacora_exporta_dataframe():
    log = MissionLogger()
    log.registrar(paso=1, accion="N", bateria=99.0)
    df = log.a_dataframe()
    assert list(df.columns) == ["paso", "accion", "bateria"]
    assert len(df) == 1


def test_firma_barranco_apagada_no_cambia_el_mundo(monkeypatch):
    import simulador
    monkeypatch.setattr(simulador, "MUNDO_V1", True)
    assert simulador.FIRMA_BARRANCO_ACTIVA is False
    a = generar_mundo(semilla=11)
    monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", False)
    b = generar_mundo(semilla=11)
    assert np.array_equal(a.tipo, b.tipo) and np.array_equal(a.elevacion, b.elevacion)


def test_firma_barranco_encendida_baja_las_celdas_barranco(monkeypatch):
    import simulador
    monkeypatch.setattr(simulador, "MUNDO_V1", True)
    apagado = generar_mundo(semilla=11)
    monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", True)
    m = generar_mundo(semilla=11)
    assert np.array_equal(m.tipo, apagado.tipo)
    es_b = m.tipo == BARRANCO
    assert es_b.any()
    assert np.allclose(m.elevacion[es_b], apagado.elevacion[es_b] - 3.0)
    assert np.array_equal(m.elevacion[~es_b], apagado.elevacion[~es_b])


def test_marcar_barranco_lleva_la_firma_solo_con_la_bandera(monkeypatch):
    import simulador
    monkeypatch.setattr(simulador, "MUNDO_V1", True)
    for activa, baja in ((False, 0.0), (True, 3.0)):
        monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", activa)
        m = generar_mundo(semilla=3, n_barrancos=0)
        antes = float(m.elevacion[5, 5])
        m.marcar_barranco((5, 5))
        m.marcar_barranco((5, 5))  # repetir no baja dos veces
        assert m.tipo[5, 5] == BARRANCO
        assert float(m.elevacion[5, 5]) == pytest.approx(antes - baja)


# ---- ARX-94a: mundo v2 (relieve suave, profundidad, altura) ----

# hash de tipo y elevacion de las semillas 0..19 con el generador anterior (commit a0bf109)
HASH_MUNDO_V1 = "e4c644b4284dbb184f75e0bffb4734fcae1a59a2b3d7665ba438fe44c99bc6e9"


def _hash_mundos(n=20):
    import hashlib
    h = hashlib.sha256()
    for s in range(n):
        m = generar_mundo(s)
        h.update(m.tipo.tobytes())
        h.update(m.elevacion.tobytes())
    return h.hexdigest()


def test_mundo_v1_reproduce_el_mapa_de_antes(monkeypatch):
    import simulador
    monkeypatch.setattr(simulador, "MUNDO_V1", True)
    assert _hash_mundos() == HASH_MUNDO_V1


def test_mundo_v2_es_el_defecto_y_cambia_la_elevacion():
    import simulador
    assert simulador.MUNDO_V1 is False
    assert _hash_mundos() != HASH_MUNDO_V1


def test_mundo_v2_misma_semilla_mismo_mundo():
    a, b = generar_mundo(7), generar_mundo(7)
    for campo in ("tipo", "elevacion", "profundidad", "altura"):
        assert np.array_equal(getattr(a, campo), getattr(b, campo))
    assert not np.array_equal(a.elevacion, generar_mundo(8).elevacion)


def test_relieve_v2_suave_entre_vecinos_norte_sur():
    d = np.concatenate([np.abs(np.diff(generar_mundo(s).elevacion, axis=0)).ravel() for s in range(20)])
    assert np.median(d) < 0.3
    assert np.percentile(d, 90) < 0.8


def test_barranco_v2_baja_de_1_a_4_m_bajo_sus_vecinos():
    n = 0
    for s in range(20):
        m = generar_mundo(s)
        assert np.all(m.profundidad[m.tipo != BARRANCO] == 0)
        for f, c in zip(*np.nonzero(m.tipo == BARRANCO)):
            n += 1
            assert 1.0 <= m.profundidad[f, c] <= 4.0
            vec = [m.elevacion[f + a, c + b] for a in (-1, 0, 1) for b in (-1, 0, 1)
                   if (a or b) and m.dentro((f + a, c + b)) and m.tipo[f + a, c + b] != BARRANCO]
            if vec:
                # el relieve cambia poco entre vecinos: el hoyo queda dentro de la banda +- 1 m
                assert 0.0 < np.mean(vec) - m.elevacion[f, c] < 5.0
                assert np.mean(vec) - m.elevacion[f, c] == pytest.approx(m.profundidad[f, c], abs=1.0)
    assert n > 0


def test_obstaculo_v2_tiene_altura_entre_03_y_2_m():
    m = generar_mundo(3)
    es_o = m.tipo == OBSTACULO
    assert es_o.any()
    assert np.all((m.altura[es_o] >= 0.3) & (m.altura[es_o] <= 2.0))
    assert np.all(m.altura[~es_o] == 0)


def test_marcar_barranco_v2_asigna_profundidad_con_el_generador_del_evento():
    m = generar_mundo(3, n_barrancos=0)
    antes = float(m.elevacion[5, 5])
    m.marcar_barranco((5, 5), rng=np.random.default_rng(99))
    esperado = float(np.random.default_rng(99).uniform(1.0, 4.0))
    assert m.profundidad[5, 5] == pytest.approx(esperado)
    assert m.elevacion[5, 5] == pytest.approx(antes - esperado)
    m.marcar_barranco((5, 5), rng=np.random.default_rng(1))   # repetir no baja otra vez
    assert m.elevacion[5, 5] == pytest.approx(antes - esperado)
    otra = generar_mundo(3, n_barrancos=0)
    otra.marcar_barranco((6, 6))
    assert 1.0 <= otra.profundidad[6, 6] <= 4.0


# ---- ARX-94b: sensores físicos ----

def _mundo_plano():
    m = generar_mundo(semilla=5, n_obstaculos=0, n_barrancos=0)
    m.tipo[:] = LIBRE
    m.elevacion[:] = 0.0
    m.profundidad[:] = 0.0
    m.altura[:] = 0.0
    return m


def test_lectura_trae_solo_las_lecturas_de_94b():
    m = _mundo_plano()
    lectura = SensorSuite(rng=np.random.default_rng(0)).leer(m, (5, 5))
    # ARX-94c: borde_barranco y celdas_barranco ya no existen (eran derivadas transitorias)
    assert set(lectura) == {"proximidad_frontal_m", "desnivel_frontal_m", "desniveles_vecinos",
                            "contraste_optico", "altimetria_m", "vibracion"}
    assert len(lectura["desniveles_vecinos"]) == 8


def test_proximidad_ignora_barrancos_y_ve_obstaculos():
    m = _mundo_plano()
    m.tipo[2, 5] = BARRANCO
    m.profundidad[2, 5] = 3.0
    m.elevacion[2, 5] = -3.0
    sensor = SensorSuite(rng=np.random.default_rng(0), ruido=0.0)
    assert sensor.leer(m, (5, 5), "N")["proximidad_frontal_m"] == pytest.approx(20.0)
    m.tipo[1, 5] = OBSTACULO
    assert sensor.leer(m, (5, 5), "N")["proximidad_frontal_m"] == pytest.approx(4.0)


def test_desnivel_frontal_mide_la_celda_siguiente_con_sigma_05():
    m = _mundo_plano()
    m.elevacion[4, 5] = -3.0
    exacto = SensorSuite(rng=np.random.default_rng(0), ruido=0.0)
    assert exacto.leer(m, (5, 5), "N")["desnivel_frontal_m"] == pytest.approx(-3.0)
    sensor = SensorSuite(rng=np.random.default_rng(1))
    d = np.array([sensor.leer(m, (5, 5), "N")["desnivel_frontal_m"] for _ in range(4000)])
    assert d.mean() == pytest.approx(-3.0, abs=0.05)
    assert d.std() == pytest.approx(0.5, rel=0.1)


def test_desnivel_nan_fuera_del_mapa_y_vecinos_sin_celdas_fuera():
    m = _mundo_plano()
    sensor = SensorSuite(rng=np.random.default_rng(0))
    esquina = (0, 0)
    lectura = sensor.leer(m, esquina, "N")
    assert np.isnan(lectura["desnivel_frontal_m"])
    assert np.isnan(lectura["contraste_optico"])
    assert set(lectura["desniveles_vecinos"]) == {(0, 1), (1, 0), (1, 1)}


def test_desniveles_vecinos_miden_cada_celda_con_sigma_05():
    m = _mundo_plano()
    m.elevacion[5, 6] = -2.5
    exacto = SensorSuite(rng=np.random.default_rng(0), ruido=0.0).leer(m, (5, 5))["desniveles_vecinos"]
    assert exacto[(5, 6)] == pytest.approx(-2.5)
    assert exacto[(5, 4)] == pytest.approx(0.0)
    sensor = SensorSuite(rng=np.random.default_rng(2))
    d = np.array([sensor.leer(m, (5, 5))["desniveles_vecinos"][(5, 6)] for _ in range(4000)])
    assert d.std() == pytest.approx(0.5, rel=0.1)


def test_camara_hoyo_oscuro_roca_clara_suelo_cero():
    m = _mundo_plano()
    m.tipo[4, 5] = BARRANCO
    m.profundidad[4, 5] = 4.0
    m.tipo[5, 6] = OBSTACULO
    m.altura[5, 6] = 1.0
    s = SensorSuite(rng=np.random.default_rng(0), ruido=0.0)
    assert s.leer(m, (5, 5), "N")["contraste_optico"] == pytest.approx(-1.0)
    assert s.leer(m, (5, 5), "E")["contraste_optico"] == pytest.approx(0.8)
    assert s.leer(m, (5, 5), "S")["contraste_optico"] == pytest.approx(0.0)


def test_camara_se_degrada_de_noche_y_en_tormenta():
    m = _mundo_plano()
    m.tipo[4, 5] = BARRANCO
    m.profundidad[4, 5] = 4.0
    dia = SensorSuite(rng=np.random.default_rng(0), ruido=0.0)
    noche = SensorSuite(rng=np.random.default_rng(0), ruido=0.0, ambiente="noche")
    assert noche.leer(m, (5, 5), "N")["contraste_optico"] == pytest.approx(0.5 * dia.leer(m, (5, 5), "N")["contraste_optico"])
    sd = SensorSuite(rng=np.random.default_rng(3))
    sn = SensorSuite(rng=np.random.default_rng(3), ambiente="noche")
    d = np.array([sd.leer(m, (5, 5), "N")["contraste_optico"] for _ in range(3000)])
    n = np.array([sn.leer(m, (5, 5), "N")["contraste_optico"] for _ in range(3000)])
    assert n.std() == pytest.approx(2 * d.std(), rel=0.1)
    assert d.std() == pytest.approx(0.4, rel=0.1)
    # la noche no cambia los telémetros
    assert noche.leer(m, (5, 5), "N")["desnivel_frontal_m"] == dia.leer(m, (5, 5), "N")["desnivel_frontal_m"]


def test_tormenta_duplica_el_ruido_de_todos_los_sensores():
    m = _mundo_plano()
    normal = SensorSuite(rng=np.random.default_rng(4))
    tormenta = SensorSuite(rng=np.random.default_rng(4), ambiente="tormenta")
    for clave in ("desnivel_frontal_m", "proximidad_frontal_m", "altimetria_m", "vibracion"):
        a = np.array([normal.leer(m, (5, 5))[clave] for _ in range(3000)])
        b = np.array([tormenta.leer(m, (5, 5))[clave] for _ in range(3000)])
        assert b.std() == pytest.approx(2 * a.std(), rel=0.12), clave


def test_vibracion_es_la_imu_de_la_celda_actual_sigma_03():
    m = _mundo_plano()
    m.tipo[4, 5] = OBSTACULO     # la celda de enfrente no cambia la vibración
    sensor = SensorSuite(rng=np.random.default_rng(5))
    v = np.array([sensor.leer(m, (5, 5), "N")["vibracion"] for _ in range(4000)])
    assert v.std() == pytest.approx(0.3, rel=0.1)
    assert abs(v.mean()) < 0.03


def test_falla_de_sensor_da_nan_en_todas_las_lecturas():
    m = _mundo_plano()
    lectura = SensorSuite(rng=np.random.default_rng(0), prob_fallo=1.0).leer(m, (5, 5))
    for clave, valor in lectura.items():
        if clave == "desniveles_vecinos":
            assert all(np.isnan(v) for v in valor.values())
        else:
            assert np.isnan(valor), clave


def test_misma_semilla_mismas_lecturas():
    m = generar_mundo(9)
    a = SensorSuite(rng=np.random.default_rng(1)).leer(m, m.inicio, "N")
    b = SensorSuite(rng=np.random.default_rng(1)).leer(m, m.inicio, "N")
    assert repr(a) == repr(b)


def test_ninguna_lectura_consulta_tipo_salvo_la_proximidad_de_obstaculos():
    """Revisión de código: en SensorSuite.leer y sus auxiliares `tipo` solo aparece en el barrido de
    obstáculos (comparado con OBSTACULO)."""
    import inspect
    import re
    import simulador
    fuente = "".join(inspect.getsource(f) for f in (
        simulador.SensorSuite.leer, simulador.SensorSuite._desnivel, simulador.SensorSuite._contraste))
    usos = re.findall(r"[.]tipo.*", fuente)
    assert len(usos) == 1 and "OBSTACULO" in usos[0], usos


def test_la_lectura_ya_no_trae_borde_ni_celdas_barranco():
    """ARX-94c: las derivadas transitorias se retiraron; el barranco se decide con el desnivel medido."""
    mundo = generar_mundo(5, filas=20, columnas=30)
    mundo.elevacion[(10, 10)] = 0.0
    mundo.elevacion[(9, 10)] = -3.0
    lectura = SensorSuite(rng=np.random.default_rng(3), ruido=0.0).leer(mundo, (10, 10), "N")
    assert lectura["desnivel_frontal_m"] == pytest.approx(-3.0)
    assert "borde_barranco" not in lectura and "celdas_barranco" not in lectura
