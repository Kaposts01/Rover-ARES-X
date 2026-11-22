"""Cine (director de cámara y postproceso): pruebas del módulo JS puro (cine_datos.js) con node; se omite si no hay node."""
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
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'cine_datos.js').as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_seis_tomas_y_duracion_determinista():
    assert len(_js("m.TOMAS")) == 6
    assert [_js(f"m.duracionToma({i})") for i in range(6)] == [6, 7, 8, 9, 10, 6]
    assert _js("m.siguienteToma(5)") == 0


def test_destino_determinista_y_sobre_el_suelo():
    a = _js("m.destinoToma(2,{x:10,y:0,z:10},0.5,3,()=>0,{columnas:30,filas:20})")
    b = _js("m.destinoToma(2,{x:10,y:0,z:10},0.5,3,()=>0,{columnas:30,filas:20})")
    assert a == b
    for n in range(6):
        d = _js(f"m.destinoToma({n},{{x:10,y:0,z:10}},1.2,5,(x,z)=>2,{{columnas:30,filas:20}})")
        assert d["pos"]["y"] >= 2 + 0.8 - 1e-9
    d = _js("m.destinoToma(3,{x:0,y:0,z:0},0,0,()=>0,{columnas:30,filas:20})")
    assert d["pos"]["x"] >= -4 and d["pos"]["z"] >= -4


def test_cortes_suaves():
    assert _js("m.mezcla(0,5)") == 0
    k1, k2 = _js("m.mezcla(1/60,5)"), _js("m.mezcla(1/30,5)")
    assert 0 < k1 < k2 < 1
    assert abs((1 - (1 - k1) ** 2) - k2) < 1e-9   # independiente de los FPS


def test_momentos_solo_con_datos_del_paso():
    f = lambda o: _js(f"m.tipoMomento({json.dumps(o)})")
    assert f({"motivos": ["V-BARRANCO"], "eventos": []}) == "veto"
    assert f({"motivos": [], "eventos": ["dron destruido"]}) == "impacto"
    assert f({"motivos": ["ok"], "eventos": []}) is None
    assert f({"motivos": ["V-X"], "estado": "FRACASO"}) is None   # la pantalla final manda


def test_buffer_de_repeticion():
    r = _js("""(()=>{const b=m.nuevoBuffer();for(let i=0;i<100;i++)m.empujarMuestra(b,i*0.05,{x:i,y:0,z:0},0);
      const s=m.recortarRepeticion(b);return {n:b.muestras.length,s:s.length,ini:s[0].t,fin:s[s.length-1].t,
      p0:m.poseRepeticion(s,0).x,p1:m.poseRepeticion(s,1).x,pm:m.poseRepeticion(s,0.5).x}})()""")
    assert r["n"] <= 20 and r["s"] >= 2
    assert r["ini"] == 0 and r["fin"] <= 1.2 + 1e-9
    assert r["p0"] < r["pm"] < r["p1"]
    assert _js("m.recortarRepeticion(m.nuevoBuffer())") == []
    assert abs(_js("m.REPETICION.ventana_s / m.REPETICION.factor") - 3) < 1e-9 and _js("m.REPETICION.duracion_s") == 3


def test_prioridad_y_movimiento_reducido():
    base = {"activado": True, "enPartida": True}
    f = lambda **k: _js(f"m.debeActuar({json.dumps({**base, **k})})")
    assert f() is True
    for k in ("intro", "viaje", "pausa", "final", "manual"):
        assert f(**{k: True}) is False
    assert _js("m.debeActuar({activado:false,enPartida:true})") is False
    assert _js("m.modoCine(true)") == "estatico" and _js("m.modoCine(false)") == "automatico"
    assert _js("m.permiteRepeticion(true)") is False


def test_fps_mediana_p5_y_umbral():
    e = _js("m.evaluarFps([60,60,60,60,60,60,60,60,60,10])")
    assert e["mediana"] == 60 and e["p5"] == 10
    assert _js("m.decidirPostproceso({fpsCon:25,fpsSin:60})") == "apagar"
    assert _js("m.decidirPostproceso({fpsCon:40,fpsSin:60})") == "apagar"      # más de 15 % por debajo
    assert _js("m.decidirPostproceso({fpsCon:55,fpsSin:60})") == "mantener"


def test_auto_apagado_dos_ventanas_seguidas():
    r = _js("""(()=>{const mon=m.crearMonitorFps({ventana:10});const out=[];
      for(let i=0;i<20;i++)out.push(mon.empujar(50));      // 20 fps en dos ventanas
      return out})()""")
    assert "apagar" not in r[:19] and r[19] == "apagar"
    r = _js("""(()=>{const mon=m.crearMonitorFps({ventana:10});const out=[];
      for(let i=0;i<10;i++)out.push(mon.empujar(50));
      for(let i=0;i<10;i++)out.push(mon.empujar(10));      // se recupera: reinicia la cuenta
      for(let i=0;i<10;i++)out.push(mon.empujar(50));
      return out})()""")
    assert "apagar" not in r
    assert _js("m.UMBRAL_FPS") == 30 and "no rinde" in _js("m.AVISO_POST_APAGADO")


def test_teclas_con_el_cine_activo():
    assert _js("m.TECLAS_CINE") == ["h", "H", "Escape"]
    assert _js("m.teclaPermitida(' ',true)") is False
    assert _js("m.teclaPermitida('ArrowUp',true)") is False
    assert _js("m.teclaPermitida('Escape',true)") is True
    assert _js("m.teclaPermitida(' ',false)") is True


def test_textos_prohibidos_ausentes():
    # nombres del ejemplo armados por partes para no dejar su rastro en el repositorio
    prohibidos = ["REC" + "-BOT", "Persever" + "ance", "/ho" + "me", "herramien" + "tas/", "ESTA" + "DO.md",
                  "C:" + "\\Users", "Usua" + "rio", "http://", "https://", "cdn", "vista" + "3d", "Math.ran" + "dom"]
    for nombre in ("cine_datos.js", "cine3d.js", "cine_post.js", "cine_ui.js"):
        ruta = ESTATICOS / nombre
        if not ruta.exists():
            continue
        txt = ruta.read_text(encoding="utf-8")
        for p in prohibidos:
            assert not re.search(re.escape(p), txt, re.I), f"{p} en {nombre}"
