"""Ronda 23, cierre de defectos de interfaz (QA final): formato numérico, viento, récords, parámetros del difuso del AG, ciencia
en la comparación, textos del laboratorio genético y comprobaciones estáticas del HTML y de los módulos tocados.
Los módulos puros se ejecutan con node; sin node se omiten."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
sin_node = pytest.mark.skipif(NODE is None, reason="node no está instalado")


def _js(modulo: str, expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / modulo).as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# ---------- 6: formato numérico único ----------
def test_ningun_modulo_de_la_interfaz_formatea_a_mano_con_punto_decimal():
    """Todo número que se escribe en pantalla pasa por formato.js (coma decimal): nadie hace toFixed(...).replace(".", ",") por su cuenta."""
    sueltos = []
    for f in sorted(ESTATICOS.glob("*.js")):
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if ".toFixed(" in linea and '.replace(".", ",")' in linea and f.name != "formato.js":
                sueltos.append(f"{f.name}:{n}")
    assert sueltos == [], f"formato a mano en {sueltos}: usa coma/porcentaje/grados de formato.js"


@sin_node
def test_el_hud_y_la_ficha_de_la_sonda_formatean_con_coma_y_un_decimal():
    assert _js("formato.js", "[m.porcentaje(91.9), m.grados(18.9), m.grados(17.92), m.grados(60), m.fraccionAPorcentaje(0.5)]") == ["91,9 %", "18,9 °C", "17,9 °C", "60,0 °C", "50,0 %"]
    app = _leer("app.js")
    assert "porcentaje(e.bateria_pct ?? e.bateria)" in app and "grados(e.temperatura_interna)" in app and "grados(e.tolerancia)" in app
    assert "porcentaje(bpct)" in app and "grados(t)" in app
    assert "toFixed(1)} %" not in app


# ---------- 12: escala única del viento ----------
@sin_node
def test_la_escala_del_viento_es_la_del_motor_y_perfil_y_estado_vivo_dicen_lo_mismo():
    # Marte 0,40 moderado; Saturno 0,80 fuerte; Neptuno 0,85 y Júpiter 0,90 muy fuerte (descripciones de juego/planetas.py)
    r = _js("planeta_datos.js", "[0, 0.2, 0.3, 0.4, 0.55, 0.8, 0.85, 0.9].map(m.nombreFuerza)")
    assert r == ["en calma", "suave", "suave", "moderado", "moderado", "fuerte", "muy fuerte", "muy fuerte"]
    neptuno = {"gravedad_g": 1.14, "viento": 0.85, "rumbo_viento": "SO", "hielo_fraccion": 0.3, "fragilidad_hielo": 1.3, "factor_pendiente": 1, "arrastre": 0, "prob_tormenta_x": 1.3, "rafaga_prob": 0.08}
    marte = {"gravedad_g": 0.38, "viento": 0.4, "rumbo_viento": "E", "hielo_fraccion": 0.05, "factor_pendiente": 1, "arrastre": 0, "prob_tormenta_x": 2, "rafaga_prob": 0.04}
    for planeta, perfil, esperado in (("Neptuno", neptuno, "muy fuerte"), ("Marte", marte, "moderado")):
        # estado vivo con la intensidad del nivel (0,75) y sin ella: el rótulo no cambia, porque se rotula el perfil del planeta
        for intensidad in (1.0, 0.75):
            origen = {"planeta_mecanicas": {"perfil": perfil, "estado": {"viento": perfil["viento"] * intensidad, "rumbo_viento": perfil["rumbo_viento"], "intensidad": intensidad, "rafaga": False}}}
            filas = _js("planeta_datos.js", f"m.filasCondiciones(m.condicionesPlaneta({json.dumps(origen)}, {json.dumps(planeta)}), null)")
            viento = next(f[1] for f in filas if f[0] == "Viento")
            assert viento.startswith(esperado), (planeta, intensidad, viento)
        ficha = _js("planeta_datos.js", f"m.filasFicha({json.dumps(perfil)}, {json.dumps(planeta)})")
        assert next(f["valor"] for f in ficha if f["etiqueta"] == "Viento").startswith(esperado)


# ---------- 5: mensaje de récords unificado ----------
@sin_node
def test_el_mensaje_de_records_sigue_el_resultado_real():
    fallo = {"record": {"origen": "asistida", "semilla": 5, "resultado": "FRACASO", "puntaje": 10, "pasos": 19}, "nuevo_record": False}
    t = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps(fallo)})")
    assert t["nuevo"] is False and "guardada en los récords" not in t["titulo"].lower() and "sin récord" in t["titulo"]
    assert "solo cuentan misiones con éxito" in t["detalle"] and "fracaso" in t["detalle"]
    exito = {"record": {"origen": "ia", "semilla": 5, "resultado": "EXITO", "puntaje": 900, "pasos": 80}, "nuevo_record": False, "puesto": 2, "mejor_anterior": {"puntaje": 950, "pasos": 70}}
    t = _js("records_datos.js", f"m.textoNuevoRecord({json.dumps(exito)})")
    assert t["titulo"] == "Misión guardada en los récords" and "Puesto 2" in t["detalle"]


def test_el_paso_de_la_pantalla_final_sale_del_contador_del_motor_y_no_del_de_la_ia():
    app = _leer("app.js")
    assert "const pasoActual = () =>" in app and "estado.paso" in app
    assert "m.alFinal({ paso: pasoActual(), codigo })" in app and "m.alPaso({ paso: pasoActual()" in app
    assert "paso: ultimoPasoNumero" not in app


# ---------- 8: parámetros del difuso elegidos por el AG ----------
@sin_node
def test_los_parametros_del_difuso_incluyen_las_listas_con_nombres_claros():
    crudo = {"hay_plan": True, "sitios": [{"id": "S1", "celda": [1, 1], "valor": 3}], "generaciones": [{"n": 0, "candidatos": [{"orden": ["S1"], "fitness": 1}]}],
             "parametros_difuso": {"distancia.cerca": [0, 0, 3.116, 6.231], "salida.lenta": [0.1, 0.25, 0.4], "regla.R4": 0.8, "regla.R7": 0.0,
                                   "conduccion.v_hielo": 0.3, "conduccion.umbral_desvio": 0.22, "conduccion.factor_desvio": 1.2, "inclinacion.fuerte": [20.9, 29.8, 45, 45],
                                   "bateria.critica": [0, 0, 15.8, 29.7], "rara": [1, "x"]}}
    r = _js("ag_evolucion_datos.js", f"m.adaptarEvolucion({json.dumps(crudo)})")
    claves = [k for k, _ in r["parametrosDifuso"]]
    assert claves == ["distancia.cerca", "salida.lenta", "regla.R4", "regla.R7", "conduccion.v_hielo", "conduccion.umbral_desvio", "conduccion.factor_desvio",
                      "inclinacion.fuerte", "bateria.critica"]            # las listas de números se conservan; la lista mixta, no
    leg = {k: _js("textos.js", f"m.parametroDifusoLegible({json.dumps(k)}, {json.dumps(v)})") for k, v in r["parametrosDifuso"]}
    assert leg["distancia.cerca"] == ["Distancia · «cerca»", "función de pertenencia con puntos 0 · 0 · 3,12 · 6,23 m"]
    assert leg["salida.lenta"][0] == "Velocidad de salida · «lenta»" and leg["salida.lenta"][1].startswith("función de pertenencia con puntos 0,1 · 0,25")
    assert leg["bateria.critica"][0] == "Batería · «crítica»" and leg["bateria.critica"][1].endswith(" %")
    assert leg["regla.R4"] == ["Regla R4", "peso 0,8 (1 = el de defecto)"] and leg["regla.R7"] == ["Regla R7", "desactivada"]
    assert leg["conduccion.v_hielo"] == ["Tope de velocidad sobre hielo", "30 % de la velocidad máxima"]
    assert leg["conduccion.umbral_desvio"][1] == "22 % de la capacidad" and leg["conduccion.factor_desvio"][1] == "×1,2"
    assert not any(re.search(r"[a-z]\.[a-z]|_", n) for n, _ in leg.values())     # ningún nombre técnico en pantalla


# ---------- 10: laboratorio genético ----------
def test_el_laboratorio_genetico_ya_no_dice_70_s_ni_que_el_juego_usa_la_ruta_mas_corta():
    lab, html, textos = _leer("laboratorio.js"), _leer("index.html"), _leer("textos.js")
    assert "70 s" not in lab and "30 generaciones" not in html and "ruta más corta validada" not in lab + textos
    assert "ventanas de tiempo" in textos and "recargas obligatorias" in textos and "sitios opcionales" in textos
    assert "LAB_AG.calculando(" in lab and "datos.tiempo_s" in lab


@sin_node
def test_el_candidato_del_ag_nuevo_muestra_violaciones_paradas_y_ciencia_si_vienen():
    c = {"fitness": 0.5, "factible": False, "violaciones": ["llega fuera de la ventana de S2"], "paradas": [{"despues_de": 1, "base": [3, 4]}], "sacrificados": ["S5", "S6"], "ciencia": 0.61, "pasos": 87}
    filas = _js("textos.js", f"m.lineasExtraCandidatoAG({json.dumps(c)})")
    assert ["plan infactible", ""] in filas and ["Restricciones que incumple", "llega fuera de la ventana de S2"] in filas
    assert ["Paradas de recarga", "1"] in filas and ["Sitios opcionales descartados", "2"] in filas and ["Ciencia recogida", "0,61"] in filas and ["Pasos", "87"] in filas
    assert _js("textos.js", "m.lineasExtraCandidatoAG({fitness: 1, orden: []})") == []          # sin los campos nuevos no se muestra nada
    assert _js("textos.js", "m.lineasExtraCandidatoAG(null)") == []


# ---------- 11: ciencia recogida en la comparación ----------
@sin_node
def test_la_ciencia_se_lee_con_tolerancia_de_nombres_y_se_oculta_si_no_viene():
    def leer(o):
        return _js("comparar_datos.js", f"m.leerCiencia({json.dumps(o)})")
    assert leer({"ciencia": 0.5})["texto"] == "50,0 %" and leer({"ciencia_pct": 62.5})["texto"] == "62,5 %"
    assert leer({"ciencia_recogida": 14})["texto"] == "14,0 puntos"
    assert leer({"ciencia": {"recogida": 12.5, "maxima": 50, "fraccion": 0.25}})["texto"] == "25,0 % (12,5 de 50)"
    assert leer({"pasos": 3}) is None and leer(None) is None and leer({"ciencia": "x"}) is None
    tabla = {"filas": [{"clave": "pasos", "a": 10, "b": 12, "ganador": "a"}], "ganador": "a"}
    sin = {"politica": "a", "pasos": [{"posicion": [1, 1]}], "terminado": True}
    con_a, con_b = {**sin, "ciencia": 0.8}, {**sin, "ciencia": 0.6}
    filas = _js("comparar_datos.js", f"m.filasTabla({json.dumps(tabla)}, 'A', 'B', {json.dumps([con_a, con_b])})")
    assert [f["rotulo"] for f in filas] == ["Pasos", "Ciencia recogida"] and filas[1]["ganador"] == "a" and filas[1]["a"] == "80,0 %"
    assert len(_js("comparar_datos.js", f"m.filasTabla({json.dumps(tabla)}, 'A', 'B', {json.dumps([sin, sin])})")) == 1      # sin dato, sin fila
    # la fila que ya trae el motor con cualquiera de los tres nombres se rotula igual
    for clave in ("ciencia", "ciencia_pct", "ciencia_recogida"):
        t = {"filas": [{"clave": clave, "a": 40, "b": 55, "ganador": "b"}]}
        assert _js("comparar_datos.js", f"m.filasTabla({json.dumps(t)}, 'A', 'B')")[0]["rotulo"] == "Ciencia recogida"
    assert _js("comparar_datos.js", f"m.hayCiencia({json.dumps([sin, sin])})") is False
    assert _js("comparar_datos.js", f"m.hayCiencia({json.dumps([sin, {**sin, 'pasos': [{'ciencia_pct': 10}]}])})") is True


# ---------- comprobaciones estáticas del HTML y de app.js ----------
def test_las_misiones_seguidas_valen_una_por_defecto_y_estan_rotuladas():
    html = _leer("index.html")
    m = re.search(r'<label id="menu-misiones-fila".*?</label>', html, re.S).group(0)
    assert 'id="menu-misiones" type="number" min="1" max="20" value="1"' in m and "Misiones seguidas" in m and "semilla" in m
    assert 'document.getElementById("menu-misiones").value = "1"' in _leer("app.js")      # repetir un récord es una sola misión


def test_el_cine_no_deja_cinta_fija_y_el_atajo_va_en_el_boton_salir():
    html, ui = _leer("index.html"), _leer("cine_ui.js")
    assert "Director de cámara · H o Esc para salir" not in ui and "cn-cinta-boton" not in ui
    assert 'id="cine-salir"' in html and 'title="Salir del modo cine (H o Esc)"' in html
    assert 'cine.cinta.aviso("H o Esc para salir", 3000)' in _leer("app.js")      # 3 s y se desvanece


def test_las_peticiones_de_la_partida_no_se_lanzan_con_la_mision_terminada():
    app = _leer("app.js")
    assert "const misionAcabada = () =>" in app and "misionTerminada = false;" in app
    assert re.search(r"async function consultarRecomendacion\(\) \{.*?if \(misionAcabada\(\)\)", app, re.S)
    assert "pasoProcesando" in app and "if (misionAcabada()) {" in app
    assert re.search(r"async function mover\(rumbo\) \{.*?misionAcabada\(\)", app, re.S)


def test_la_defensa_muestra_cada_codigo_con_su_descripcion():
    d = _leer("defensa.js")
    usados = set(re.findall(r'"((?:RF|CA)-\d\d)"', d))
    definidos = set(re.findall(r'^  "((?:RF|CA)-\d\d)":', d, re.M))
    assert usados and usados <= definidos, f"sin descripción: {sorted(usados - definidos)}"
    assert "Criterios de la consigna del trabajo (RF: requisito funcional · CA: criterio de aceptación)" in d


def test_el_editor_de_reglas_tiene_el_interruptor_de_aplicar_activado_por_defecto():
    e, t = _leer("difuso_editor.js"), _leer("textos.js")
    assert "aplicarInt.checked = true" in e and "Aplicar a la partida en curso" in t
    assert "if (!aplicarInt.checked)" in e and "ESPERA_APLICAR_MS = 600" in e        # se mantiene la espera de 600 ms
