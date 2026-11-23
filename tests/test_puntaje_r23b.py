"""R23b: el puntaje es uno solo (juego/puntaje.py): sin bono por veto, premia ciencia, batería y pasos, castiga choques y caídas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from juego import puntaje as pj  # noqa: E402

BASE = dict(ciencia=0.7, exito=True, bateria_pct=40.0, pasos=150, choques=0, caidas=0, pasos_sobre_tolerancia=0)


def _p(**cambios):
    return pj.calcular(**{**BASE, **cambios})["puntaje"]


def test_el_desglose_suma_el_puntaje_y_tiene_el_formato_del_contrato():
    r = pj.calcular(**BASE)
    assert r["puntaje"] == max(0, round(sum(t["puntos"] for t in r["desglose"])))
    assert all(set(t) == {"clave", "etiqueta", "valor", "peso", "puntos"} for t in r["desglose"])
    assert isinstance(r["puntaje"], int) and "veto" in r["formula"].lower()
    assert abs(450 * 0.7 + 300 + 125 * 0.4 + 125 * (1 - 150 / 400) - sum(t["puntos"] for t in r["desglose"])) < 0.1


def test_no_hay_ninguna_entrada_ni_termino_de_vetos():
    assert "vetos" not in {t["clave"] for t in pj.desglose(**BASE)}
    import inspect
    assert "vetos" not in inspect.signature(pj.desglose).parameters


def test_mas_ciencia_bateria_y_menos_pasos_dan_mas_puntaje():
    assert _p(ciencia=0.9) > _p() > _p(ciencia=0.5)
    assert _p(bateria_pct=80) > _p() > _p(bateria_pct=10)
    assert _p(pasos=100) > _p() > _p(pasos=300)


def test_choques_caidas_y_calor_restan():
    assert _p(choques=1) == _p() - 100
    assert _p(caidas=1) == _p() - 150
    assert _p(pasos_sobre_tolerancia=3) == _p() - 60
    assert _p(choques=50) == 0                      # nunca negativo


def test_fracasar_vale_claramente_menos_que_cumplir():
    peor_exito = _p(ciencia=0.5, bateria_pct=0.0, pasos=400)
    mejor_fracaso = _p(exito=False, ciencia=1.0, bateria_pct=100.0, pasos=10)
    assert peor_exito > mejor_fracaso
    assert mejor_fracaso <= 450


def test_valores_fuera_de_rango_se_acotan():
    assert _p(ciencia=3.0) == _p(ciencia=1.0)
    assert _p(bateria_pct=250.0) == _p(bateria_pct=100.0)
    assert _p(pasos=5000) == _p(pasos=400)
