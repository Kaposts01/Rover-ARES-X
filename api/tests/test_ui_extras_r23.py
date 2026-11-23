"""Ronda 23 (interfaz): récords, comparar políticas, tutorial del modo manual, aviso de la IA en manual y control del cine.
Funciones puras de los módulos con node (opcional) y comprobaciones estáticas del HTML y de los módulos JS."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.extras import puntaje_de_juego  # noqa: E402

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
sin_node = pytest.mark.skipif(NODE is None, reason="node no está instalado")
NUEVOS = ("records.js", "records_datos.js", "comparar.js", "comparar_datos.js", "tutorial.js", "tutorial_datos.js", "vx_ui.js")
JERGA = re.compile(r"§|sin_ag_|\bCA-\d|\bRF-\d|ARX-\d|ev3-d\d|\bM\d{1,2}\b")


def _js(modulo: str, expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / modulo).as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# ---------- récords ----------
@sin_node
def test_el_aviso_de_nuevo_record_distingue_primera_marca_mejora_y_no_record():
    base = {"id": "x", "semilla": 7, "puntaje": 1200, "pasos": 40, "resultado": "EXITO", "origen": "manual"}
    primero = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps({'record': base, 'nuevo_record': True, 'mejor_anterior': None})})")
    assert primero["nuevo"] is True and "Nuevo récord" in primero["titulo"] and "Primera marca manual" in primero["detalle"]
    ant = {**base, "puntaje": 1000, "pasos": 50}
    mejora = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps({'record': base, 'nuevo_record': True, 'mejor_anterior': ant})})")
    assert "Antes: 1000 puntos en 50 pasos" in mejora["detalle"]
    no = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps({'record': base, 'nuevo_record': False, 'mejor_anterior': ant, 'puesto': 2})})")
    assert no["nuevo"] is False and "Puesto 2" in no["detalle"]
    fracaso = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps({'record': {**base, 'resultado': 'FRACASO'}, 'nuevo_record': False})})")
    assert "solo cuentan misiones con éxito" in fracaso["detalle"]
    assert _js("records_datos.js", "m.textoNuevoRecord(null)") is None


@sin_node
def test_filtros_fecha_y_configuracion_para_jugar_una_semilla():
    assert _js("records_datos.js", 'm.consultaFiltros({planeta: "Marte", nivel: "", semilla: " 12 ", origen: null})') == "?planeta=Marte&semilla=12"
    assert _js("records_datos.js", "m.consultaFiltros({})") == ""
    assert _js("records_datos.js", 'm.fechaLegible("2026-11-22T14:05:09")') == "22/11/2026 14:05"
    assert _js("records_datos.js", 'm.fechaLegible("basura")') == "—"
    ia = _js("records_datos.js", 'm.configuracionDe({planeta: "Luna", vehiculo: "sonda", tamano: "pequeno", nivel: 3, semilla: 9, origen: "ia", modo: "rna"})')
    assert ia == {"planeta": "Luna", "vehiculo": "sonda", "tamano": "pequeno", "nivel": 3, "semilla": 9, "control": "rna"}
    manual = _js("records_datos.js", 'm.configuracionDe({planeta: "Marte", origen: "asistida", modo: "manual", semilla: 1, nivel: 1})')
    assert manual["control"] == "manual"          # la asistida se vuelve a jugar a mano
    assert _js("records_datos.js", '[m.rotuloOrigen("manual"), m.rotuloOrigen("asistida"), m.rotuloOrigen("ia")]') == ["Manual", "Manual con ayuda de la IA", "IA"]


def test_el_puntaje_de_los_records_lo_calcula_el_motor():
    e = {"sitios_visitados": 3, "sitios_totales": 3, "bateria_pct": 57.0, "colisiones": 0, "pasos_sobre_tolerancia": 0, "barrancos_evitados": 0}
    assert puntaje_de_juego({}) == 0
    assert puntaje_de_juego(e) >= 0


# ---------- comparar ----------
@sin_node
def test_divergencia_con_decision_y_motivo_de_cada_politica():
    div = {"n": 12, "a": {"posicion": [3, 4], "accion": "avanzar", "motivos": ["OK"]},
           "b": {"posicion": [2, 4], "accion": "replanificar", "motivos": ["V-RNA-BARRANCO"]}}
    t = _js("comparar_datos.js", f'm.textoDivergencia({json.dumps(div)}, "Híbrido", "Sin difuso")')
    assert "Primer paso distinto: el 12" in t["titulo"]
    assert "Híbrido avanzó y Sin difuso replanificó la ruta" in t["resumen"]
    assert "porque la RNA vio un barranco delante" in t["b"] and "fila 2, columna 4" in t["b"]
    assert "V-RNA" not in json.dumps(t)
    assert _js("comparar_datos.js", 'm.textoDivergencia(null, "A", "B")') is None


@sin_node
def test_tabla_final_con_nombres_claros_y_ganador_por_metrica():
    tabla = {"ganador": "a", "filas": [
        {"clave": "resultado", "a": "EXITO", "b": "FRACASO", "ganador": "a"},
        {"clave": "pasos", "a": 50, "b": 70, "ganador": None},
        {"clave": "bateria_pct", "a": 40.25, "b": 10, "ganador": "a"},
        {"clave": "vetos", "a": 0, "b": 0, "ganador": "empate"}]}
    f = _js("comparar_datos.js", f'm.filasTabla({json.dumps(tabla)}, "Híbrido", "Solo RNA")')
    assert [x["rotulo"] for x in f] == ["Resultado", "Pasos", "Batería final", "Vetos del supervisor"]
    assert f[0]["a"] == "Éxito" and f[0]["b"] == "Fracaso" and f[0]["texto"] == "Híbrido"
    assert f[1]["texto"] == "—" and f[2]["a"] == "40,3 %" and f[3]["texto"] == "empate" and f[3]["informativa"] is False
    assert _js("comparar_datos.js", f'm.veredicto({json.dumps(tabla)}, "Híbrido", "Solo RNA")') == "Gana Híbrido."
    assert _js("comparar_datos.js", 'm.veredicto({ganador: "empate", filas: []}, "A", "B")').startswith("Empate")
    assert _js("comparar_datos.js", "m.filasTabla(null, 'A', 'B')") == []


@sin_node
def test_vetos_son_informativos_y_la_nota_no_dice_que_menos_vetos_gana():
    tabla = {"ganador": "a", "filas": [{"clave": "vetos", "a": 3, "b": 9, "ganador": None}, {"clave": "choques", "a": 0, "b": 1, "ganador": "a"}]}
    f = _js("comparar_datos.js", f'm.filasTabla({json.dumps(tabla)}, "Híbrido", "Solo RNA")')
    assert f[0]["informativa"] is True and f[0]["texto"] == "informativo" and f[0]["ganador"] is None
    nota = _js("comparar_datos.js", "m.NOTA_TABLA")
    assert "menos (pasos, choques)" in nota and "vetos del supervisor son solo informativos" in nota and "pasos, vetos" not in nota


@sin_node
def test_formulario_de_comparacion_y_nombres_de_politicas():
    f = lambda **k: _js("comparar_datos.js", f"m.validarFormulario({json.dumps({'semilla': '', 'politicaA': 'hibrido', 'politicaB': 'sin_rna', **k})})")  # noqa: E731
    assert f() is None and f(semilla="42") is None
    assert "número entero" in f(semilla="4x2")
    assert "dos políticas distintas" in f(politicaB="hibrido")
    nombres = dict(_js("comparar_datos.js", "m.opcionesPoliticas()"))
    assert nombres["hibrido"] == "Híbrido" and nombres["solo_rna"] == "Solo RNA" and nombres["sin_difuso"] == "Sin difuso"
    assert all(not JERGA.search(n) and "_" not in n for n in nombres.values())
    assert len(nombres) == 11


@sin_node
def test_el_minimapa_avanza_con_el_paso_y_se_queda_en_la_ultima_ficha():
    lado = {"pasos": [{"posicion": [1, 1]}, {"posicion": [1, 2]}, {"posicion": [2, 2]}]}
    assert _js("comparar_datos.js", f"m.fichaEn({json.dumps(lado)}, 0)") is None
    assert _js("comparar_datos.js", f"m.fichaEn({json.dumps(lado)}, 2)") == {"posicion": [1, 2]}
    assert _js("comparar_datos.js", f"m.fichaEn({json.dumps(lado)}, 99)") == {"posicion": [2, 2]}
    assert _js("comparar_datos.js", f"m.rutaHasta([0, 0], {json.dumps(lado)}, 2)") == [[0, 0], [1, 1], [1, 2]]
    assert _js("comparar_datos.js", "m.tamanoCelda(20, 30, 450, 400)") == 15
    assert 3 <= _js("comparar_datos.js", "m.tamanoCelda(40, 60, 100, 100)") <= 16


# ---------- tutorial ----------
@sin_node
def test_el_tutorial_tiene_de_4_a_6_pasos_con_accion_y_recuerda_lo_visto():
    pasos = _js("tutorial_datos.js", 'm.pasosTutorial("rover")')
    assert 4 <= len(pasos) <= 6
    assert [p["accion"] for p in pasos if p["accion"]] == ["mover", "recomendacion", "evento"]
    assert all(p["titulo"] and p["texto"] and p["objetivo"] for p in pasos)
    assert "la sonda" in _js("tutorial_datos.js", 'm.pasosTutorial("sonda")')[0]["texto"]
    # el paso que habla del pad tiene un texto alternativo que no lo menciona, para cuando el pad no está a la vista
    for v in ("rover", "sonda"):
        mover = _js("tutorial_datos.js", f'm.pasosTutorial("{v}")')[0]
        assert "pad" in mover["texto"] and "pad" not in mover["textoSinObjetivo"].replace("pad de botones", "")
        assert "flechas" in mover["textoSinObjetivo"]
    # almacenamiento bloqueado o con datos: nunca lanza
    assert _js("tutorial_datos.js", "m.yaVisto({getItem() { throw new Error('bloqueado'); }})") is False
    assert _js("tutorial_datos.js", "m.marcarVisto({setItem() { throw new Error('bloqueado'); }})") is False
    assert _js("tutorial_datos.js", "(() => { const d = {}; const a = {getItem: (k) => d[k] ?? null, setItem: (k, v) => { d[k] = v; }}; const antes = m.yaVisto(a); m.marcarVisto(a); return [antes, m.yaVisto(a)]; })()") == [False, True]


# ---------- texto de las acciones ----------
@sin_node
def test_las_acciones_de_un_paso_tienen_nombre_claro():
    assert _js("textos.js", '[m.nombreAccion("avanzar"), m.nombreAccion("replanificar"), m.nombreAccion("rara_cosa")]') == ["avanzó", "replanificó la ruta", "rara cosa"]


# ---------- estáticas ----------
def test_los_modulos_nuevos_no_usan_dialogos_nativos_ni_jerga():
    for nombre in NUEVOS:
        t = _leer(nombre)
        assert not re.search(r"\b(?:confirm|alert|prompt)\(", t), nombre
        for a, b in re.findall(r'"([^"\n]{6,})"|`([^`\n]{6,})`', t):
            cadena = a or b
            if cadena.startswith(("/", "#", ".")) or " " not in cadena:
                continue
            assert not JERGA.search(cadena), (nombre, cadena)


def test_el_html_tiene_los_accesos_los_controles_del_cine_y_el_aviso_de_la_ia():
    html = re.sub(r"<!--.*?-->", "", _leer("index.html"), flags=re.S)
    for ident in ("menu-comparar", "menu-records", "menu-tutorial", "meta-records", "tutorial-abrir", "pol-comparar-vivo", "cine-play", "cine-salir", "ia-conduce", "ia-retomar"):
        assert html.count(f'id="{ident}"') == 1, ident
    assert "Retomar el control" in html and "La IA está conduciendo" in html
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))


def test_reproducir_en_manual_dice_lo_que_hace():
    app = _leer("app.js")
    assert "Dejar que la IA conduzca" in app and "Retomar el control" in app
    assert "Un paso de la IA" in app                              # el paso suelto también es de la IA
    assert '"cine-play"' in app and "alternarReproduccion" in app
    assert re.search(r'if \(ev\.key === " " && ev\.target === document\.body\) \{ ev\.preventDefault\(\); alternarReproduccion\(\)', app)


def test_el_cine_deja_salir_y_pausar_y_los_paneles_siguen_ocultos():
    css = _leer("estilos.css")
    assert "body.cine .cine-controles { display: flex; }" in css
    regla = re.search(r"body\.cine #registro[^{]*\{", css).group(0)
    assert "#dock" in regla and ".ia-conduce" not in regla      # el aviso vive dentro de #dock, que el cine oculta


def test_la_misión_manual_también_termina_al_mover_o_disparar():
    app = _leer("app.js")
    assert app.count("revisarFinManual();") >= 2 and "finAtendido" in app
    assert "registrarRecord" in app and "/records/registrar" in app
