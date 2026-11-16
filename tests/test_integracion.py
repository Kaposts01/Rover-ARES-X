import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integracion import Mision, SafetySupervisor  # noqa: E402
from simulador import generar_mundo  # noqa: E402

LECTURA_OK = {"proximidad_frontal_m": 12.0, "borde_barranco": False,
              "celdas_barranco": [], "altimetria_m": 0.5}


def test_supervisor_veta_sensor_nan():
    lectura = dict(LECTURA_OK, proximidad_frontal_m=float("nan"))
    d = SafetySupervisor().decidir({"libre": 1.0}, 0.8, lectura, 90)
    assert d.accion == "modo_seguro"
    assert d.motivos == ["V-SENSOR-NAN"]


def test_supervisor_veta_bateria_cero():
    d = SafetySupervisor().decidir({"libre": 1.0}, 0.8, LECTURA_OK, 0)
    assert d.accion == "modo_seguro"


def test_supervisor_replanifica_si_la_rna_ve_barranco():
    d = SafetySupervisor().decidir({"barranco": 0.9, "libre": 0.1}, 0.8, LECTURA_OK, 90)
    assert d.accion == "replanificar"
    assert d.motivos == ["V-RNA-BARRANCO"]


def test_supervisor_avanza_en_camino_libre():
    d = SafetySupervisor().decidir({"libre": 0.99}, 0.8, LECTURA_OK, 90)
    assert d.accion == "avanzar"
    assert d.motivos == ["OK"]


def test_supervisor_detiene_con_velocidad_baja():
    d = SafetySupervisor().decidir({"libre": 0.99}, 0.05, LECTURA_OK, 90)
    assert d.accion == "detener"


def test_mision_nunca_pisa_barranco_ni_colisiona():
    m = generar_mundo(semilla=12, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    res = Mision(m, semilla=12).ejecutar(max_pasos=400)
    assert res["barrancos_pisados"] == 0
    assert res["colisiones"] == 0


@pytest.mark.parametrize("semilla", [11, 12, 13])
def test_mision_llega_al_refugio_en_mapas_base(semilla):
    m = generar_mundo(semilla=semilla, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    res = Mision(m, semilla=semilla).ejecutar(max_pasos=400)
    assert res["estado"] == "EXITO"
    assert res["bateria_final"] >= 0
