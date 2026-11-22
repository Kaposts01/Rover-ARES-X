"""Pruebas ligeras de scripts/medicion_94e.py (ARX-94e): lógica de atribución y un caso pequeño. No corre congelado ni exigente."""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

import medicion_94e as M  # noqa: E402


def _fila(pos, acc, vel, mot, bat=50.0):
    return {"posicion": pos, "accion": acc, "velocidad": vel, "motivos": mot, "bateria": bat, "reglas": ""}


def test_motivos_rna_reconoce_riesgo_y_vetos():
    filas = [_fila((1, 1), "avanzar", 0.5, "OK;RNA-RIESGO:(1, 2):0.71"), _fila((1, 1), "replanificar", 0.0, "V-RNA-BARRANCO"),
             _fila((1, 1), "avanzar", 0.5, "V-BORDE-BARRANCO")]
    assert M._motivos_rna(filas) == ["RNA-RIESGO:(1, 2):0.71", "V-RNA-BARRANCO"]
    assert M._tipo_motivo("RNA-RIESGO-2:(1, 2):0.7") == "RNA-RIESGO"
    assert M._tipo_motivo("V-RNA-OBSTACULO") == "V-RNA-OBSTACULO"


def test_divergencias_primera_directa_y_consecuencia():
    fh = {1: [_fila((1, 1), "avanzar", 0.8, "OK")], 2: [_fila((1, 2), "replanificar", 0.0, "V-RNA-BARRANCO")],
          3: [_fila((2, 2), "avanzar", 0.8, "OK", 40.0)]}
    fv = {1: [_fila((1, 1), "avanzar", 0.8, "OK")], 2: [_fila((1, 2), "avanzar", 0.5, "OK")],
          3: [_fila((2, 3), "avanzar", 0.8, "OK", 40.0)]}
    d = M.divergencias(fh, fv)
    assert [x["origen"] for x in d] == ["directa", "consecuencia"]
    assert d[0]["paso"] == 2 and "decision" in d[0]["cambio"] and "velocidad" in d[0]["cambio"]
    assert d[0]["motivos_rna"] == ["V-RNA-BARRANCO"] and d[1]["motivos_rna"] == []


def test_sin_divergencias_si_las_bitacoras_son_iguales():
    f = {1: [_fila((1, 1), "avanzar", 0.8, "OK")]}
    assert M.divergencias(f, dict(f)) == []


def test_resumir_conteo_y_criterio():
    def f(s, cuenta):
        r = {"estado": "EXITO", "exito": True, "pasos": 10, "colisiones": 0, "bateria_final": 5.0, "sitios_visitados": 3}
        return {"semilla": s, "hibrido": r, "sin_rna": r, "cuenta_para_m2": cuenta, "primera_directa": {"x": 1} if cuenta else None,
                "tipos_primera_directa": ["decision"] if cuenta else [], "motivo_atribuido": ["RNA-RIESGO"] if cuenta else [],
                "algun_paso_con_motivo_rna": cuenta}
    filas = [f(s, s <= 5) for s in range(1, 21)]
    r = M.resumir(filas, "x", list(range(1, 21)))
    assert r["m2"]["conteo"] == 5 and r["m2"]["cumple"] is True
    filas = [f(s, s <= 4) for s in range(1, 21)]
    assert M.resumir(filas, "x", list(range(1, 21)))["m2"]["cumple"] is False


def test_modo_rapido_escribe_json_y_resumen():
    import tempfile
    with tempfile.TemporaryDirectory() as salida:
        _rapido(salida)


def _rapido(salida):
    res = M.main(["--rapido", "--semillas", "1", "--salida", salida])
    assert M.ESCENARIO_RAPIDO in res
    with open(os.path.join(salida, f"medicion_94e_{M.ESCENARIO_RAPIDO}.json"), encoding="utf-8") as fh:
        datos = json.load(fh)
    assert datos["m2"]["n"] == 1 and len(datos["filas"]) == 1 and len(datos["hash_filas"]) == 64
    assert "medicion_94e.md" in os.listdir(salida)
