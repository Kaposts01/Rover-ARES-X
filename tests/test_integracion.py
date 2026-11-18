import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import integracion  # noqa: E402
from integracion import Mision, SafetySupervisor, aporte_rna  # noqa: E402
from simulador import BARRANCO, LIBRE, generar_mundo  # noqa: E402

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


class _RnaFalsa:
    """RNA de prueba: devuelve siempre la misma distribución de probabilidades."""

    def __init__(self, p_barranco):
        self.p = p_barranco

    def explicar(self, rasgos):
        return {"probabilidades": {"libre": 1 - self.p, "obstáculo": 0.0, "barranco": self.p}}


def _mundo_con_barranco_a_dos(columnas=12):
    """Fila libre de ancho `columnas` salvo un barranco a dos celdas del rover, sobre la ruta recta."""
    m = generar_mundo(semilla=5, filas=3, columnas=columnas, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    return m


def test_aporte_apagado_no_marca_alerta_ni_entrena_el_modelo_nuevo():
    assert integracion.RNA_APORTE_ACTIVA is False
    mision = Mision(generar_mundo(semilla=7), semilla=7)
    mision.ejecutar(max_pasos=60)
    assert mision.aporte_rna is False and mision.alerta_rna_2 is False and mision._rna_alerta2 is None
    assert not any("RNA-RIESGO-2" in m for m in mision.log.a_dataframe()["motivos"])


def test_alerta_a_dos_celdas_marca_riesgo_sin_veto_y_la_ruta_lo_evita(monkeypatch):
    monkeypatch.setattr(integracion, "ALERTA_RNA_2_ACTIVA", True)
    # La RNA falsa ve un barranco a dos celdas que el mapa estimado no conoce y que el sensor de proximidad
    # no marca (la celda real es libre): lo que se prueba es el mecanismo de marca y replanificación.
    with aporte_rna(True):
        mundo = generar_mundo(semilla=5, filas=5, columnas=12, n_obstaculos=0, n_barrancos=0, n_sitios=0)
        mundo.tipo[:] = LIBRE
        mision = Mision(mundo, semilla=5, rna=_RnaFalsa(0.0), rna_alerta2=_RnaFalsa(0.9))
    mision.riesgo[:] = 0.0
    fila, col = mundo.inicio
    mision._planear()
    assert (fila, col + 2) in mision.ruta
    mision.paso_mision()
    assert mision.riesgo[fila, col + 2] == pytest.approx(0.9)
    bitacora = mision.log.a_dataframe()
    assert any("RNA-RIESGO-2:" in str(m) for m in bitacora["motivos"])
    assert not any("V-" in str(m) for m in bitacora["motivos"])     # sin veto nuevo
    assert (fila, col + 2) not in mision.ruta   # la ruta ya lo evita
    assert mision.colisiones == 0 and mision.vetos == 0


def test_alerta_no_marca_donde_el_mapa_ya_conocia_el_riesgo(monkeypatch):
    monkeypatch.setattr(integracion, "ALERTA_RNA_2_ACTIVA", True)
    with aporte_rna(True):
        mundo = generar_mundo(semilla=5, filas=5, columnas=12, n_obstaculos=0, n_barrancos=0, n_sitios=0)
        mundo.tipo[:] = LIBRE
        mision = Mision(mundo, semilla=5, rna=_RnaFalsa(0.0), rna_alerta2=_RnaFalsa(0.9))
    fila, col = mundo.inicio
    mision.riesgo[:] = 0.0
    mision.riesgo[fila, col + 2] = 1.0
    mision._planear()
    mision.paso_mision()
    assert not any("RNA-RIESGO-2" in str(m) for m in mision.log.a_dataframe()["motivos"])


def test_con_el_borde_encendido_los_vetos_no_cambian():
    with aporte_rna(True):
        mundo = generar_mundo(semilla=5, filas=5, columnas=12, n_obstaculos=0, n_barrancos=0, n_sitios=0)
        mundo.tipo[:] = LIBRE
        mision = Mision(mundo, semilla=5, rna=_RnaFalsa(0.0), rna_alerta2=_RnaFalsa(0.0))
    fila, col = mundo.inicio
    mision.riesgo[:] = 0.0
    mundo.tipo[fila, col + 1] = BARRANCO       # barranco de enfrente: el LIDAR sigue vetando primero
    mundo.elevacion[fila, col] = 0.0           # ARX-94b: el sensor mide la geometría (desnivel de 3 m)
    mundo.elevacion[fila, col + 1] = -3.0
    mundo.profundidad[fila, col + 1] = 3.0
    mision.ruta = [mundo.inicio, (fila, col + 1), (fila, col + 2)]
    mision.paso_mision()
    assert "V-RUTA-CON-RIESGO" in mision.log.a_dataframe()["motivos"].iloc[-1] or         mision.log.a_dataframe()["accion"].iloc[-1] == "replanificar"


def test_aporte_encendido_deja_la_alerta_a_dos_celdas_apagada():
    with aporte_rna(True):
        mundo = generar_mundo(semilla=5, filas=5, columnas=12, n_obstaculos=0, n_barrancos=0, n_sitios=0)
        mision = Mision(mundo, semilla=5, rna=_RnaFalsa(0.0), rna_alerta2=_RnaFalsa(0.9))
    assert mision.aporte_rna is True and mision.alerta_rna_2 is False
    mision.paso_mision()
    assert not any("RNA-RIESGO-2" in str(m) for m in mision.log.a_dataframe()["motivos"])
