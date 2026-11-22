import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import integracion  # noqa: E402
from integracion import Mision, SafetySupervisor, aporte_rna  # noqa: E402
from simulador import BARRANCO, LIBRE, OBSTACULO, generar_mundo  # noqa: E402

LECTURA_OK = {"proximidad_frontal_m": 12.0, "desnivel_frontal_m": 0.0, "altimetria_m": 0.5}


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


# ---------- ARX-94c: supervisor y mapa estimado con sensores físicos ----------

def _mundo_llano(filas=5, columnas=12):
    m = generar_mundo(semilla=5, filas=filas, columnas=columnas, n_obstaculos=0, n_barrancos=0, n_sitios=0)
    m.tipo[:] = LIBRE
    m.elevacion[:] = 0.0
    m.profundidad[:] = 0.0
    m.altura[:] = 0.0
    return m


def _mision_con_barranco_adelante(profundidad, p_rna):
    """Rover en el inicio con un barranco de `profundidad` m justo en la celda siguiente de la ruta recta."""
    m = _mundo_llano()
    fila, col = m.inicio
    m.tipo[fila, col + 1] = BARRANCO
    m.elevacion[fila, col + 1] = -profundidad
    m.profundidad[fila, col + 1] = profundidad
    mision = Mision(m, semilla=5, rna=_RnaFalsa(p_rna), ruido=0.0)
    mision.riesgo[:] = 0.0                      # el mapa orbital no conoce el barranco
    mision.ruta = [m.inicio, (fila, col + 1), (fila, col + 2)]
    return mision, (fila, col + 1)


def test_supervisor_veta_por_el_desnivel_medido_y_no_por_el_tipo():
    sup = SafetySupervisor()
    d = sup.decidir({"libre": 1.0}, 0.8, dict(LECTURA_OK, desnivel_frontal_m=-3.0), 90)
    assert d.accion == "replanificar" and d.motivos == ["V-BORDE-BARRANCO"]
    # -1,5 m no alcanza el umbral de -2 m y NaN no es lectura: no hay veto duro
    for desnivel in (-1.5, float("nan")):
        d = sup.decidir({"libre": 1.0}, 0.8, dict(LECTURA_OK, desnivel_frontal_m=desnivel), 90)
        assert d.accion == "avanzar"


def test_barranco_de_3_m_contiguo_veta_por_el_sensor_aunque_la_rna_no_lo_vea():
    mision, celda = _mision_con_barranco_adelante(3.0, p_rna=0.0)
    mision.paso_mision()
    fila = mision.log.a_dataframe().iloc[-1]
    assert fila["accion"] == "replanificar" and mision.vetos == 1
    assert mision.riesgo[celda] == 1.0          # el sensor lo marcó en el mapa estimado
    assert mision.rover.posicion == mision.mundo.inicio and mision.colisiones == 0
    assert celda not in mision.ruta


def test_barranco_de_1_5_m_con_p_alta_veta_por_la_rna_y_sube_el_riesgo():
    mision, celda = _mision_con_barranco_adelante(1.5, p_rna=0.9)
    mision.paso_mision()
    motivos = mision.log.a_dataframe().iloc[-1]["motivos"]
    assert "V-RNA-BARRANCO" in motivos and f"RNA-RIESGO:{celda}:0.90" in motivos
    assert "V-BORDE-BARRANCO" not in motivos    # el sensor (σ 0,5, umbral -2 m) no lo ve a 1,5 m
    assert mision.riesgo[celda] == pytest.approx(0.9)
    assert mision.colisiones == 0 and mision.rover.posicion == mision.mundo.inicio
    assert celda not in mision.ruta


def test_barranco_de_1_5_m_con_p_baja_la_fisica_lo_rechaza_y_nunca_cae():
    mision, celda = _mision_con_barranco_adelante(1.5, p_rna=0.1)
    mision.paso_mision()
    fila = mision.log.a_dataframe().iloc[-1]
    assert "V-CELDA-BLOQUEADA" in fila["motivos"] and "V-RNA-BARRANCO" not in fila["motivos"]
    assert mision.colisiones == 1                # colisión +1 y replanificación
    assert mision.rover.posicion == mision.mundo.inicio
    assert mision.mundo.tipo[mision.rover.posicion] != BARRANCO


def test_obstaculo_en_ruta_sigue_igual_que_antes():
    m = _mundo_llano()
    fila, col = m.inicio
    m.tipo[fila, col + 3] = OBSTACULO
    mision = Mision(m, semilla=5, rna=_RnaFalsa(0.0), ruido=0.0)
    mision.riesgo[:] = 0.0
    mision.ruta = [(fila, col + k) for k in range(6)]
    mision.paso_mision()
    assert "V-OBSTACULO-EN-RUTA" in mision.log.a_dataframe().iloc[-1]["motivos"]
    assert mision.riesgo[fila, col + 3] == 1.0


def test_rna_riesgo_no_se_anota_con_p_baja_y_sin_rna_no_toca_el_mapa():
    # ARX-94f: se prueba la escritura de la RNA en el mapa de forma aislada. Con paso_mision el rover avanza contra el
    # barranco de 1,5 m (no lo veta el desnivel) y el contacto marca la celda: eso lo cubre la prueba siguiente.
    mision, celda = _mision_con_barranco_adelante(1.5, p_rna=0.3)
    dec = integracion.Decision("avanzar", 1.0, [])
    mision._riesgo_por_rna({"barranco": 0.3}, celda, dec)
    assert not any(m.startswith("RNA-RIESGO") for m in dec.motivos)
    assert mision.riesgo[celda] == pytest.approx(0.3)      # max(riesgo, p) sin pasar de 0,5: no veta
    mision, celda = _mision_con_barranco_adelante(1.5, p_rna=0.9)
    mision.usar_rna = False
    mision._riesgo_por_rna({"barranco": 0.9}, celda, dec)
    assert mision.riesgo[celda] == 0.0


def test_el_contacto_con_una_celda_que_no_se_puede_pisar_la_marca_en_el_mapa():
    # ARX-94f: barranco de 1,5 m (sobre el umbral de -2 m: el telémetro no lo veta) y RNA que no lo ve
    mision, celda = _mision_con_barranco_adelante(1.5, p_rna=0.3)
    mision.paso_mision()
    assert mision.colisiones == 1
    assert "V-CELDA-BLOQUEADA" in mision.log.a_dataframe().iloc[-1]["motivos"]
    assert mision.riesgo[celda] == 1.0                    # el planificador ya no vuelve a mandar al rover contra ella


def _lectura_vecina(celda, d):
    return {"desniveles_vecinos": {celda: d}}


def test_desnivel_con_ruido_nominal_una_lectura_bajo_el_umbral_basta():
    mision = Mision(_mundo_llano(), semilla=5, rna=_RnaFalsa(0.0), ruido=0.1)
    assert mision._barrancos_fusionados(_lectura_vecina((1, 1), -2.5)) == {(1, 1)}


def test_desnivel_con_ruido_alto_una_lectura_suelta_no_cierra_la_celda():
    # ARX-94f: σ = 0,6 × 5 = 3 m; una celda llana cae bajo -2 m en ~25 % de las lecturas: hace falta evidencia repetida
    mision = Mision(_mundo_llano(), semilla=5, rna=_RnaFalsa(0.0), ruido=0.6)
    assert mision._barrancos_fusionados(_lectura_vecina((1, 1), -2.5)) == set()
    marcadas = set()
    for _ in range(30):                                      # lecturas de un barranco real de 3 m
        marcadas |= mision._barrancos_fusionados(_lectura_vecina((1, 1), -3.0))
    assert marcadas == {(1, 1)}
    # la consulta sin guardar no acumula lecturas
    n = int(mision._desnivel_n[1, 1])
    mision._barrancos_fusionados(_lectura_vecina((1, 1), -3.0), guardar=False)
    assert int(mision._desnivel_n[1, 1]) == n


def test_rna_con_ruido_alto_confirma_antes_de_marcar_y_con_ruido_nominal_no():
    dec = integracion.Decision("replanificar", 0.0, [])
    ruidosa = Mision(_mundo_llano(), semilla=5, rna=_RnaFalsa(0.9), ruido=0.6)
    ruidosa.riesgo[:] = 0.0
    ruidosa._riesgo_por_rna({"barranco": 0.9}, (1, 1), dec)
    assert ruidosa.riesgo[1, 1] == 0.0                       # una observación suelta no cierra la celda
    ruidosa._riesgo_por_rna({"barranco": 0.9}, (1, 1), dec)
    assert ruidosa.riesgo[1, 1] == pytest.approx(0.9)         # la segunda la confirma
    nominal = Mision(_mundo_llano(), semilla=5, rna=_RnaFalsa(0.9), ruido=0.1)
    nominal.riesgo[:] = 0.0
    nominal._riesgo_por_rna({"barranco": 0.9}, (1, 1), dec)
    assert nominal.riesgo[1, 1] == pytest.approx(0.9)         # regla de antes: basta una


def test_nada_oculto_ni_la_decision_ni_las_lecturas_consultan_el_tipo():
    """Revisión de código (regla de la meta): el supervisor y los pasos de decisión de la misión no leen
    `mundo.tipo`; los llamadores solo ven lo que mide SensorSuite. El tipo real queda para la proximidad de
    obstáculos (simulador), la física de pasos y el resumen/etiquetas."""
    import inspect
    import re
    for f in (SafetySupervisor.decidir, integracion.barrancos_medidos, integracion._bajo_umbral,
              Mision.paso_mision, Mision._riesgo_por_rna, Mision._barrancos_fusionados, Mision._actualizar_mapa_estimado,
              Mision._distancia_a_riesgo_en_ruta, Mision._obstaculo_en_ruta):
        assert not re.search(r"[.]tipo", inspect.getsource(f)), f.__qualname__
