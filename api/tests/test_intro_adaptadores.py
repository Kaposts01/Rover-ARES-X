"""Intro del sistema solar: pruebas del módulo JS puro (intro_datos.js) con node; se omite si no hay node."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node no está instalado")

OCHO = ["Mercurio", "Venus", "Tierra", "Marte", "Júpiter", "Saturno", "Urano", "Neptuno"]


def _js(expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'intro_datos.js').as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_solo_los_ocho_perfiles_en_orden():
    cuerpos = _js("m.CUERPOS_INTRO")
    assert [c["nombre"] for c in cuerpos] == OCHO
    dist = [c["distanciaEscena"] for c in cuerpos]
    assert dist == sorted(dist) and len(set(dist)) == 8
    assert all(c["radioEscena"] > 0 for c in cuerpos)
    for ajeno in ("Plutón", "Ceres", "Luna"):
        assert _js(f"m.esPerfilIntro({json.dumps(ajeno)})") is False


def test_debe_mostrar_intro():
    f = lambda **k: _js(f"m.debeMostrarIntro({json.dumps(k)})")
    base = dict(activada=True, reducido=False, webgl=True)
    for motivo in ("abrir", "inicio", "salir"):       # abrir la app, volver al inicio, salir de una partida
        assert f(**base, motivo=motivo) is True
        assert f(**{**base, "activada": False}, motivo=motivo) is False      # casilla apagada: directo al asistente
        assert f(**{**base, "webgl": False}, motivo=motivo) is False
        assert f(**{**base, "reducido": True}, motivo=motivo) is True        # movimiento reducido: se muestra, pero estática
    assert f(**base, motivo="repetir") is False        # «Volver a jugar» no pasa por la intro
    assert f(**{**base, "activada": False}, motivo="manual") is True         # «Ver intro» ignora la casilla
    assert f(**{**base, "webgl": False}, motivo="manual") is False
    assert f(**base) is False and _js("m.debeMostrarIntro()") is False
    assert "CLAVE_VISTA" not in (ESTATICOS / "intro_datos.js").read_text(encoding="utf-8")
    assert _js("m.modoIntro(true)") == "estatico" and _js("m.modoIntro(false)") == "animado"


def test_sin_marca_de_sesion_y_todos_los_caminos_vuelven_al_inicio():
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    assert "ares.intro.visto" not in app and "sessionStorage" not in app
    assert 'correrIntro({ motivo: "abrir" })' in app
    # los siete caminos de salida al asistente usan volverAlInicio (ninguno muestra el menú por su cuenta)
    assert len(re.findall(r'volverAlInicio\("salir"\)', app)) >= 7
    cuerpo = re.search(r"function volverAlInicio\(.*?\n\}", app, re.S).group(0)
    assert "detenerReproduccion()" in cuerpo and "cerrarAvisos()" in cuerpo and "correrIntro(" in cuerpo
    fuera = app.replace(cuerpo, "")
    assert 'getElementById("menu").classList.remove("oculto")' not in fuera
    # «Volver a jugar» (repetir) no llama a la intro
    assert re.search(r'pedido === "repetir"\) \{[^}]*nuevaDesdeMeta', app) and "motivo: \"repetir\"" not in app


def test_elegir_cuerpo():
    cat = "{planetas:[{nombre:'Saturno',modo:'sonda'},{nombre:'Marte',modo:'rover'}]}"
    assert _js(f"m.elegirCuerpo('Saturno',{cat})") == {"planeta": "Saturno", "modo": "sonda"}
    assert _js(f"m.elegirCuerpo('Marte',{cat})") == {"planeta": "Marte", "modo": "rover"}
    assert _js(f"m.elegirCuerpo('Plutón',{cat})") is None
    assert _js(f"m.elegirCuerpo('Venus',{cat})") is None      # perfil sin entrada en el catálogo
    assert _js("m.elegirCuerpo('Marte',null)") is None


def test_posicion_orbital_acotada():
    for c in _js("m.CUERPOS_INTRO"):
        for t in (0, 1, 37.5, 1e5):
            x, y, z = _js(f"m.posicionOrbital({t},{json.dumps(c)})")
            assert y == 0 and abs((x * x + z * z) ** 0.5 - c["distanciaEscena"]) < 1e-6


def test_vuelo_suma_exacta_y_paso_acotado():
    f = _js("m.fasesVuelo(1.2)")
    assert abs(f["aproximacion"] + f["asentamiento"] - 1.2) < 1e-12 and f["total"] == 1.2
    assert _js("m.DURACION_VUELO_S") == 1.2
    assert _js("[m.pasoVuelo(-1), m.pasoVuelo(0), m.pasoVuelo(0.5), m.pasoVuelo(1), m.pasoVuelo(9)]") == [0, 0, 0.5, 1, 1]


def test_tarjeta_y_avisos():
    d = _js("m.datosCuerpo('Saturno',{planetas:[{nombre:'Saturno',modo:'sonda'}]})")
    assert d["titulo"] == "Saturno"
    assert d["filas"][0]["valor"] == "1.432 millones de km" and d["filas"][0]["tipo"] == "real"
    assert d["filas"][1]["valor"] == "sonda"
    assert _js("m.datosCuerpo('Marte',null)")["filas"][1]["tipo"] == "sin_dato"
    assert "no a escala" in _js("m.ROTULO_INTRO")
    assert "Marte" in _js("m.AVISO_TERRENO_INTRO")
    assert _js("m.GUARDA_PRIMER_CUADRO_S") == 3 and _js("m.CIERRE_INACTIVIDAD_S") == 90


def test_textos_prohibidos_ausentes():
    # nombres del ejemplo armados por partes para no dejar su rastro en el repositorio
    prohibidos = ["REC" + "-BOT", "Persever" + "ance", "/ho" + "me", "herramien" + "tas/", "ESTA" + "DO.md",
                  "C:\\" + "Users", "Down" + "loads", "http://", "https://", "cdn"]
    for nombre in ("intro_datos.js", "intro3d.js", "intro_tarjeta.js"):
        ruta = ESTATICOS / nombre
        if not ruta.exists():
            continue
        txt = ruta.read_text(encoding="utf-8")
        for p in prohibidos:
            assert not re.search(re.escape(p), txt, re.I), f"{p} en {nombre}"


def test_aviso_corto_coherente_con_la_fuente_unica():
    assert "Marte" in _js("m.AVISO_TERRENO") and "Marte" in _js("m.AVISO_TERRENO_INTRO")


def test_espacio_no_llega_a_la_partida_durante_intro_y_viaje():
    # el espacio dispara en la partida: las capas modales solo dejan pasar Tab y Enter, y disparar() sale con la intro activa
    for nombre in ("intro_tarjeta.js", "viaje_tarjeta.js"):
        txt = (ESTATICOS / nombre).read_text(encoding="utf-8")
        m = re.search(r'if \(!(\[[^\]]*\])\.includes\(e\.key\)\) e\.stopPropagation\(\)', txt)
        assert m, nombre
        assert json.loads(m.group(1)) == ["Tab", "Enter"], nombre
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    m = re.search(r"async function disparar\(\) \{\s*if \(document\.body\.classList\.contains\(\"intro-activa\"\)\) return;", app)
    assert m, "falta la guarda de la intro en disparar()"
