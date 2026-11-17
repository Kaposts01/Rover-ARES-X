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


def test_borde_de_barranco_detectado_por_lidar():
    m = generar_mundo(semilla=5, n_barrancos=0)
    m.tipo[:] = LIBRE
    pos = (5, 5)
    m.tipo[5, 6] = BARRANCO
    sensor = SensorSuite(rng=np.random.default_rng(0))
    assert sensor.leer(m, pos)["borde_barranco"] is True


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
    assert simulador.FIRMA_BARRANCO_ACTIVA is False
    a = generar_mundo(semilla=11)
    monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", False)
    b = generar_mundo(semilla=11)
    assert np.array_equal(a.tipo, b.tipo) and np.array_equal(a.elevacion, b.elevacion)


def test_firma_barranco_encendida_baja_las_celdas_barranco(monkeypatch):
    import simulador
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
    for activa, baja in ((False, 0.0), (True, 3.0)):
        monkeypatch.setattr(simulador, "FIRMA_BARRANCO_ACTIVA", activa)
        m = generar_mundo(semilla=3, n_barrancos=0)
        antes = float(m.elevacion[5, 5])
        m.marcar_barranco((5, 5))
        m.marcar_barranco((5, 5))  # repetir no baja dos veces
        assert m.tipo[5, 5] == BARRANCO
        assert float(m.elevacion[5, 5]) == pytest.approx(antes - baja)
