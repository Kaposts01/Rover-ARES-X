"""Paquete A: pruebas de los adaptadores JS puros (evolucion_datos.js, holo_datos.js).
El repo no tiene runner JS: se ejecuta node sobre el módulo, y se omite si node no existe."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node no está instalado")


def _js(modulo: str, expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / modulo).as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _ag(poblaciones):
    return {"generaciones": [
        {"generacion": i, "mejor": max(f for _, f in pob),
         "poblacion": [{"cromosoma": c, "fitness": f, "operacion": "elite"} for c, f in pob]}
        for i, pob in enumerate(poblaciones)]}


def test_evolucion_puntos_rango_y_tope():
    pob = [([[i, i + 1], [i + 2, 0]], float(i)) for i in range(12)]
    ag = _ag([pob, pob])
    r = _js("evolucion_datos.js", f"m.adaptarAG({json.dumps(ag)}, [3, 4])")
    assert r["seleccionada"] == 1
    cands = r["generaciones"][0]["candidatos"]
    assert len(cands) == 8                                   # MAX_CANDIDATOS_POR_GENERACION
    assert [c["rango"] for c in cands] == list(range(8))
    assert cands[0]["fitness"] == 11.0                       # rango 0 = mejor fitness
    assert cands[0]["puntos"][0] == [3, 4]                   # empieza en la posición del rover
    assert cands[0]["puntos"][1:] == [[11, 12], [13, 0]]     # luego el cromosoma en orden
    assert all(c["factible"] is True for c in cands)


def test_evolucion_sin_datos_y_filas_invalidas():
    assert _js("evolucion_datos.js", "m.adaptarAG({sin_sitios: true}, [0, 0])") is None
    ag = _ag([[([[1, 1]], 1.0)]])
    ag["generaciones"][0]["poblacion"].append({"cromosoma": [["x", 1]], "fitness": 5, "operacion": "mut"})
    ag["generaciones"][0]["poblacion"].append({"cromosoma": [[2, 2]], "fitness": None, "operacion": "mut"})
    r = _js("evolucion_datos.js", f"m.adaptarAG({json.dumps(ag)}, null, 3)")
    assert len(r["generaciones"][0]["candidatos"]) == 1
    assert r["generaciones"][0]["candidatos"][0]["puntos"] == [[1, 1]]   # sin posición, solo el cromosoma


def test_evolucion_coordenadas_como_la_capa_de_riesgo():
    assert _js("evolucion_datos.js", "m.celdaAEscena([2, 5])") == {"x": 5.5, "z": 2.5}
    assert _js("evolucion_datos.js", "m.celdaAEscena(null)") is None


def test_holo_tres_clases_un_medidor_y_vetos():
    rna = {"probabilidades": {"libre": 0.2, "obstáculo": 0.1, "barranco": 0.7}, "confianza": 0.7,
           "accion": "frenar", "motivos": ["V-02 borde", "otro"]}
    difuso = {"salida": {"velocidad": 0.4, "fallback": False, "cautela": 0.9}}
    ag = {"orden_en_juego": {"metodo": "AG <b>orden</b>"}, "mejor_ruta": [[1, 1], [1, 2], ["x", 3]]}
    r = _js("holo_datos.js", f"m.adaptarHolo({json.dumps({'rna': rna, 'difuso': difuso, 'ag': ag, 'estado': {'estado': 'activo', 'veto': True}})})")
    assert [c["nombre"] for c in r["clases"]] == ["libre", "obstáculo", "barranco"]
    assert r["prediccion"] == "barranco" and r["velocidad"] == 0.4
    assert "cautela" not in r and "retorno" not in r
    assert r["vetos"] == ["V-02 borde"]
    assert r["mejorRuta"] == [[1, 1], [1, 2]]
    assert "<" not in r["metodo"] and ">" not in r["metodo"]    # saneado
    assert r["estado"] == "activo" and r["vetoActivo"] is True


def test_holo_sin_datos_no_inventa():
    r = _js("holo_datos.js", "m.adaptarHolo({rna: null, difuso: null, ag: null, estado: null})")
    assert r["hayRna"] is False and r["velocidad"] is None and r["metodo"] is None
    assert r["prediccion"] is None and r["mejorRuta"] == [] and r["vetos"] == []


def _mapa_obs(riesgo, obs):
    return {"filas": len(riesgo), "columnas": len(riesgo[0]), "riesgo_estimado": riesgo, "observada": obs}


def test_incertidumbre_colores_por_estado():
    mp = _mapa_obs([[0.05, 0.05, 0.9], [0.05, 0.3, 1.0]], [[0, 1, 0], [1, 0, 1]])
    assert _js("incertidumbre_datos.js", f"m.contarEstados({json.dumps(mp)})") == {"noObservada": 1, "seguro": 2, "riesgo": 3}
    # riesgo >= 0,3 gana sobre «no observada»
    assert _js("incertidumbre_datos.js", "m.colorCeldaIncertidumbre(0.9, 0).estado") == "riesgo"
    assert _js("incertidumbre_datos.js", "m.colorCeldaIncertidumbre(0.05, 0).estado") == "noObservada"
    assert _js("incertidumbre_datos.js", "m.colorCeldaIncertidumbre(0.05, 1).estado") == "seguro"


def test_incertidumbre_modo_riesgo_no_cambia_y_rotulos():
    assert _js("incertidumbre_datos.js", "m.colorCelda('riesgo', 0.05, 0)") is None
    assert _js("incertidumbre_datos.js", "m.colorCelda('riesgo', 1, 0)") == [1, 0, 0.1]
    assert _js("incertidumbre_datos.js", "m.colorCelda('riesgo', 0.3, 0)") == [1, 0.9, 0.1]
    assert _js("incertidumbre_datos.js", "m.colorCelda('incertidumbre', 0.05, 0)") is not None
    r = _js("incertidumbre_datos.js", "m.ROTULOS")
    assert r["noObservada"] == "no observada" and "entrop" not in json.dumps(r).lower()


def test_incertidumbre_sin_observada_se_deshabilita():
    sin = {"filas": 1, "columnas": 1, "riesgo_estimado": [[0.05]]}
    assert _js("incertidumbre_datos.js", f"m.tieneObservada({json.dumps(sin)})") is False
    malo = _mapa_obs([[0.05, 0.05]], [[1]])               # dimensiones distintas
    assert _js("incertidumbre_datos.js", f"m.tieneObservada({json.dumps(malo)})") is False
    assert _js("incertidumbre_datos.js", f"m.tieneObservada({json.dumps(_mapa_obs([[0.05]], [[1]]))})") is True
    assert _js("incertidumbre_datos.js", "m.AVISO_SIN_OBSERVACION") == "sin datos de observación"
