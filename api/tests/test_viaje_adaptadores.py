"""Viaje entre planetas: pruebas del módulo JS puro (viaje_datos.js) con node; se omite si no hay node."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node no está instalado")


def _js(expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'viaje_datos.js').as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_debe_viajar():
    f = lambda p, n, a=True: _js(f"m.debeViajar({{previo:{json.dumps(p)},nuevo:{json.dumps(n)},activado:{json.dumps(a)}}})")
    assert f("Marte", "Venus") is True
    assert f("Marte", "Marte") is False
    assert f(None, "Venus") is False
    assert f("Marte", "Venus", False) is False
    assert f("Marte", "Plutón") is False


def test_duracion_ocho_segundos():
    assert _js("m.DURACION_VIAJE_S") == 8


def test_ocho_distancias_y_sin_dato():
    d = _js("m.DISTANCIA_SOL_MKM")
    assert len(d) == 8 and d["Marte"] == 228.0 and d["Neptuno"] == 4515
    t = _js("m.datosTarjeta('Marte','Venus',{})")
    assert t["titulo"] == "Viajando de Marte a Venus"
    assert t["destino"][0]["valor"] == "108,2 millones de km" and t["destino"][0]["tipo"] == "real"
    assert t["destino"][1] == {"etiqueta": "Vehículo permitido", "valor": "Sin dato", "tipo": "sin_dato"}
    assert _js("m.datosTarjeta('Marte','Pluton',null)")["destino"][0]["tipo"] == "sin_dato"
    c = _js("m.datosTarjeta('Marte','Júpiter',{planetas:[{nombre:'Júpiter',modo:'sonda'}]})")
    assert c["destino"][1]["valor"] == "sonda"
    assert len(t["avisos"]) == 2 and "Marte" in t["avisos"][1]


def test_fases_suman_exacto_y_faseactual():
    f = _js("m.fasesViaje(8)")
    assert abs(f["salida"] + f["travesia"] + f["llegada"] - 8) < 1e-9
    assert _js("m.faseActual(0, m.fasesViaje(8))") == ["salida", 0]
    assert _js("m.faseActual(8, m.fasesViaje(8))") == ["llegada", 1]
    assert _js("m.faseActual(4, m.fasesViaje(8))")[0] == "travesia"


def test_trayectoria_extremos():
    a = _js("m.trayectoria(0, 20)")
    b = _js("m.trayectoria(1, 20)")
    assert a["pos"] == [-20, 0, 0] and b["pos"] == [20, 0, 0]
    assert abs(sum(x * x for x in a["tangente"]) - 1) < 1e-9


def test_estela_acotada_y_movimiento():
    assert len(_js("(()=>{let h=[];for(let i=0;i<500;i++)h=m.actualizarEstela(h,[i,0,0],120);return h})()")) == 120
    assert _js("m.modoMovimiento(false,true)") == "animado"
    assert _js("m.modoMovimiento(true,true)") == "tarjeta"
    assert _js("m.modoMovimiento(false,false)") == "ninguno"


def test_textos_prohibidos_ausentes():
    # nombres del ejemplo armados por partes para no dejar su rastro en el repositorio
    prohibidos = ["REC" + "-BOT", "Persever" + "ance", "/ho" + "me", "herramien" + "tas/", "ESTA" + "DO.md", "http://", "https://", "cdn"]
    for nombre in ("viaje_datos.js", "viaje3d.js", "viaje_tarjeta.js"):
        ruta = ESTATICOS / nombre
        if not ruta.exists():
            continue
        txt = ruta.read_text(encoding="utf-8")
        for p in prohibidos:
            assert not re.search(re.escape(p), txt, re.I), f"{p} en {nombre}"


# ---------- Carga con cohete: el avance sigue a la carga real ----------
def _simular(listo_en, segundos=12.0, dt=1 / 60):
    """Avance mostrado a lo largo del tiempo con el motor respondiendo en listo_en (None = nunca)."""
    listo = "false" if listo_en is None else f"t>={listo_en}"
    return _js(f"(()=>{{let d=0,t=0,h=[];while(t<{segundos}){{t+={dt};const n=m.pasoCarga(d,t,{listo},{dt});h.push([t,n,n>=d]);d=n;}}return h;}})()")


def test_sin_respuesta_del_motor_el_cohete_no_llega():
    h = _simular(None)
    tope = _js("m.TOPE_ESPERA")
    assert all(d < tope for _, d, _ in h)
    assert h[-1][1] > 0.8 * tope            # pero sigue avanzando: no se ve congelado
    assert _js("m.etapaCarga(0.5)") == "crucero"


def test_al_responder_aterriza_y_nunca_retrocede():
    h = _simular(3.0)
    assert all(sube for _, _, sube in h)
    fin = next(t for t, d, _ in h if d >= 1)
    assert 3.0 < fin < 3.0 + 3.0
    assert _js("m.etapaCarga(1)") == "aterrizado"


def test_motor_inmediato_respeta_la_duracion_minima():
    h = _simular(0.0)
    fin = next(t for t, d, _ in h if d >= 1)
    assert fin >= _js("m.DURACION_MIN_CARGA_S")


def test_origen_del_vuelo():
    f = lambda p, d: _js(f"m.origenVuelo({json.dumps(p)},{json.dumps(d)})")
    assert f("Marte", "Venus") == "Marte"
    assert f(None, "Venus") == "Tierra"
    assert f("Venus", "Venus") == "Tierra"
    assert f(None, "Tierra") == "Marte"
