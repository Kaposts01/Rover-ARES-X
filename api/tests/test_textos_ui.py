"""Ronda 23 (interfaz): textos y datos que ve el jugador. Funciones puras de textos.js con node (opcional), los datos del
servidor que las alimentan y comprobaciones estáticas del HTML y los módulos JS."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import Sesion, crear_app  # noqa: E402

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
sin_node = pytest.mark.skipif(NODE is None, reason="node no está instalado")


def _js(expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'textos.js').as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _cliente(**k):
    return TestClient(crear_app(Sesion(semilla=11, **k)))


def _cliente_grande():
    """Partida jugable por defecto (mapa grande): su capacidad de batería no es 100 u., así que % y unidades difieren."""
    c = TestClient(crear_app(Sesion(semilla=11)))
    assert c.post("/partida", json={"semilla": 11, "nivel": 1}).status_code == 200
    assert c.get("/estado").json()["capacidad_bateria"] > 120
    return c


def _html_sin_comentarios() -> str:
    return re.sub(r"<!--.*?-->", "", (ESTATICOS / "index.html").read_text(encoding="utf-8"), flags=re.S)


# ---------- 1. «undefined» ----------
@sin_node
def test_candidato_del_ag_no_trae_ruta_pasos_y_el_texto_no_dice_undefined():
    # forma real de /ag: cromosoma, orden, pasos, fitness y desglose (no existe «ruta_pasos»)
    c = {"cromosoma": [[1, 2], [3, 4], [5, 6]], "orden": [[1, 2], [3, 4], [5, 6]], "pasos": [None, [2, 2], None],
         "fitness": 1.5, "desglose": {}}
    t = _js(f"m.textoCandidatoAG({json.dumps(c)})")
    assert "undefined" not in t and "NaN" not in t and "Orden de 3 sitios" in t and "1 punto de paso" in t
    assert "undefined" not in _js("m.textoCandidatoAG({})") and "undefined" not in _js("m.textoCandidatoAG(null)")
    assert "Orden de 1 sitio." in _js('m.textoCandidatoAG({orden: [[1, 1]]})')


@sin_node
def test_evaluacion_de_la_rna_usa_la_configuracion_real_del_servidor():
    ev = _cliente().get("/rna/evaluacion?modelo=juego").json()
    assert "nota" not in ev and ev["configuracion"] and ev["mapas_prueba"]   # la «nota» nunca existió
    t = _js(f"m.textoEvaluacionRNA({json.dumps(ev)})")
    assert "undefined" not in t and "Mapas de prueba:" in t and ev["configuracion"] in t
    assert "undefined" not in _js("m.textoEvaluacionRNA({})")


def test_los_modulos_no_leen_campos_que_el_servidor_no_manda():
    lab = (ESTATICOS / "laboratorio.js").read_text(encoding="utf-8")
    assert "ruta_pasos" not in lab and "ev.nota" not in lab and "datos.nota" not in lab


# ---------- 2. batería del difuso ----------
def test_difuso_publica_el_porcentaje_real_igual_al_del_hud():
    c = _cliente_grande()
    estado = c.get("/estado").json()
    d = c.get("/difuso").json()["entradas"]
    assert d["bateria_pct"] == estado["bateria_pct"]                         # lo que se rotula «%» coincide con el HUD
    assert d["capacidad_bateria"] == estado["capacidad_bateria"]
    assert d["bateria"] == pytest.approx(estado["bateria"], abs=0.01)         # la entrada realmente usada, en unidades del motor
    assert d["bateria"] > 100 and d["bateria_pct"] == 100.0                   # el caso del evaluador: 145 u. no son 145 %


def test_difuso_acepta_bateria_en_porcentaje_y_la_convierte_a_unidades_del_motor():
    c = _cliente_grande()
    cap = c.get("/estado").json()["capacidad_bateria"]
    d = c.get("/difuso?bateria_pct=50").json()["entradas"]
    assert d["bateria_pct"] == 50.0 and d["bateria"] == pytest.approx(cap / 2, abs=0.01)
    assert c.get("/difuso?bateria_pct=101").status_code == 400
    assert c.get("/difuso?bateria_pct=abc").status_code == 400
    assert c.get("/difuso/barrido?bateria_pct=40").json()["bateria_pct"] == 40.0


def test_ia_paso_muestra_el_porcentaje_real_de_la_bateria_que_uso_el_difuso():
    c = _cliente_grande()
    antes = c.get("/estado").json()
    assert c.post("/modo", json={"modo": "automatico"}).status_code == 200
    assert c.post("/paso").status_code == 200
    e = c.get("/ia/paso").json()["difuso"]["entradas"]
    # el paso se decidió con la batería anterior al movimiento: el porcentaje es el de esa carga, no las unidades del motor
    assert e["bateria_pct"] == pytest.approx(antes["bateria_pct"], abs=0.2)
    assert 0.0 <= e["bateria_pct"] <= 100.0 and e["bateria"] > 100


@sin_node
def test_texto_de_la_bateria_del_difuso_no_miente_sobre_la_escala():
    t = _js('m.textoBateriaDifuso({bateria: 145, bateria_pct: 96.6, capacidad_bateria: 150})')
    assert t == "96,6 % (145 u. del motor)"
    assert "%" not in _js("m.textoBateriaDifuso({bateria: 70})")                # sin porcentaje real no inventa uno
    assert "unidades del motor" in _js("m.ETIQUETA_BATERIA_UNIVERSO") and "%" not in _js("m.ETIQUETA_BATERIA_UNIVERSO")


# ---------- 3. datos que no se limpian entre misiones ----------
def test_partida_nueva_vacia_historial_serie_y_decision_del_servidor():
    c = _cliente()
    c.post("/modo", json={"modo": "automatico"})
    for _ in range(3):
        c.post("/paso")
    assert c.get("/historial").json()["total"] >= 3
    assert c.post("/partida", json={"semilla": 5, "nivel": 1}).status_code == 200
    assert c.get("/historial").json()["total"] == 0
    assert c.get("/serie").json()["total"] == 0
    ia = c.get("/ia/paso").json()
    assert ia["hay_paso"] is False and "difuso" not in ia and "rna" not in ia


def test_el_cliente_vacia_todo_lo_derivado_al_crear_la_partida():
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    cuerpo = app[app.index("function reiniciarEstadoDerivado()"):app.index("// Tamaño del mapa (ARX-21)")]
    for pieza in ("registro", "hist-cuerpo", "tiraPasos = []", "filasGraficos = []", "rec-lista", "reiniciarLaboratorios()", "panelIA.reiniciar()"):
        assert pieza in cuerpo, pieza
    carga = app[app.index("async function cargarPartida("):app.index("// Campo vacío = semilla aleatoria real")]
    assert "reiniciarEstadoDerivado()" in carga
    panel = (ESTATICOS / "panel_ia.js").read_text(encoding="utf-8")
    assert "function reiniciar()" in panel and "hist.length = 0" in panel and "reiniciar," in panel
    assert "miEpoca !== epoca" in panel            # una respuesta de la partida anterior no repinta el historial


# ---------- 4. recomendaciones al día ----------
def test_las_recomendaciones_se_recalculan_o_se_borran_tras_cada_paso():
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    refresco = app[app.index("async function refrescarPaneles()"):app.index("// Móviles, eventos y automático continuo")]
    assert "actualizarRecomendacion()" in refresco
    assert "caja.open" in app and "epoca !== recomendacionEpoca" in app


# ---------- 5. lab Difuso: ids únicos ----------
def test_los_id_del_html_son_unicos():
    ids = re.findall(r'\bid="([^"]+)"', _html_sin_comentarios())
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert not repetidos, repetidos


def test_el_laboratorio_difuso_pinta_en_sus_propios_contenedores():
    html = _html_sin_comentarios()
    lab = (ESTATICOS / "laboratorio.js").read_text(encoding="utf-8")
    for i in ("lab-dif-reglas", "lab-dif-velocidad"):
        assert f'id="{i}"' in html and f'$("{i}")' in lab
    assert '$("dif-reglas")' not in lab and '$("dif-velocidad")' not in lab   # eran los del panel lateral


def test_difuso_entrega_reglas_para_el_cuadro_del_laboratorio():
    d = _cliente().get("/difuso?distancia=1&bateria_pct=90&inclinacion=2&temperatura=15").json()
    assert d["reglas"] and d["reglas_activadas"]
    ids = {r["id"] for r in d["reglas"]}
    assert all(r["id"] in ids for r in d["reglas_activadas"])


# ---------- 6. numeración ----------
def test_la_numeracion_de_los_pasos_es_continua():
    html = _html_sin_comentarios()
    assert "en tres pasos" in html and "cuatro pasos" not in html
    asistente = html[html.index('<div id="menu">'):]
    assert re.findall(r'<span class="num">(\d)</span>', asistente) == ["1", "2", "3"]
    panel = html[html.index('<div id="controles"'):html.index('<div id="dock"')]
    # «Simulación» pasa a la barra de control y no cuenta: los visibles son 1, 2, 3 y 4 sin saltos
    visibles = re.findall(r'titulo-seccion">(\d) · ', panel)
    assert visibles == ["1", "2", "3", "4"]


# ---------- 7. tildes, mayúsculas y siglas ----------
@sin_node
def test_nombres_visibles_de_modos_estados_y_drones():
    assert _js('[m.nombreModo("automatico"), m.nombreModo("rna"), m.nombreModo("ag"), m.nombreModo("difuso")]') == ["Híbrido", "RNA", "AG", "Difuso"]
    assert _js('[m.nombreEstado("CONFIGURACION"), m.nombreEstado("EXPLORACION"), m.nombreEstado("REPLANIFICACION")]') == ["Configuración", "Exploración", "Replanificación"]
    assert _js('m.nombreEstadoDron("persecucion")') == "persecución"
    assert _js('[m.Vehiculo("sonda"), m.Vehiculo("rover")]') == ["Sonda", "Rover"]


def test_el_html_no_muestra_siglas_en_minuscula_ni_valores_internos():
    html = _html_sin_comentarios()
    assert "(rna, difuso, ag)" not in html
    assert "Veto de seguridad (RNA, difuso, AG)" in html
    visible = re.sub(r"<[^>]+>", "\n", html)
    for malo in ("CONFIGURACION", "EXPLORACION", "REPLANIFICACION"):
        assert malo not in visible
    # el filtro del historial conserva los valores que entiende la API y muestra nombres claros
    assert '<option value="automatico">Híbrido</option>' in html and '<option value="rna">RNA</option>' in html


# ---------- 8. vehículo real ----------
def test_el_narrador_usa_el_vehiculo_de_la_partida():
    from api.narrador import narrar_fila
    fila = {"paso": 3, "accion": "avanzar", "motivos": "OK"}
    assert "El rover avanzó" in narrar_fila(fila) and "El rover avanzó" in narrar_fila(fila, "rover")
    s = narrar_fila(fila, "sonda")
    assert "La sonda avanzó" in s and "rover" not in s


def test_ia_paso_y_reporte_narran_con_el_vehiculo_real():
    c = _cliente()
    c.post("/partida", json={"semilla": 11, "nivel": 1, "planeta": "Neptuno", "modo": "sonda"})
    assert c.get("/estado").json()["modo_planeta"] == "sonda"
    c.post("/modo", json={"modo": "automatico"})
    assert c.post("/paso").status_code == 200
    n = c.get("/ia/paso").json()["narracion"]
    assert "La sonda" in n and "rover" not in n
    assert "El rover" not in c.get("/reporte.html").text


@sin_node
def test_los_avisos_del_motor_usan_el_vehiculo_y_pierden_el_codigo():
    assert _js('m.limpiarAviso("T-SOBRE-TOLERANCIA: 63 °C interna, más de 60", "rover")') == "63 °C interna, más de 60"
    assert _js('m.limpiarAviso("El rover no puede moverse", "sonda")') == "La sonda no puede moverse"
    assert _js('m.limpiarAviso("Faltan drones y el rover está detenido", "sonda")') == "Faltan drones y la sonda está detenido"
    assert _js('m.limpiarAviso("El rover no puede moverse", "rover")') == "El rover no puede moverse"


# ---------- 9, 10. «Temperatura interna» y plurales ----------
def test_temperatura_interna_en_lugar_de_calor_interno():
    todo = _html_sin_comentarios() + (ESTATICOS / "app.js").read_text(encoding="utf-8")
    assert "Calor interno" not in todo and "Temperatura interna" in todo


@sin_node
def test_singular_y_plural_de_los_contadores():
    assert _js("[m.reglasActivadas(0), m.reglasActivadas(1), m.reglasActivadas(2)]") == ["0 reglas activadas", "1 regla activada", "2 reglas activadas"]
    assert _js('[m.plural(1, "celda", "celdas"), m.plural(5, "celda", "celdas")]') == ["1 celda", "5 celdas"]


def test_el_narrador_no_usa_regla_s():
    from api.narrador import narrar_fila
    uno = narrar_fila({"paso": 1, "accion": "avanzar", "velocidad": 0.5, "reglas": "R1;R2", "motivos": "OK"})
    dos = narrar_fila({"paso": 1, "accion": "avanzar", "velocidad": 0.5, "reglas": "R1;R2;R3", "motivos": "OK"})
    assert "(s)" not in uno and "1 regla más" in uno and "2 reglas más" in dos


def test_el_selector_de_camara_no_se_corta():
    css = (ESTATICOS / "estilos.css").read_text(encoding="utf-8")
    assert ".barra-mision select { flex: 0 0 auto; min-width: 9.5em;" in css


# ---------- 11. Lanzar ----------
def test_los_eventos_se_lanzan_y_el_arma_se_dispara():
    html = _html_sin_comentarios()
    assert re.search(r'<button id="evento-disparar"[^>]*>Lanzar</button>', html)
    assert 'title="Disparar (Espacio)"' in html
    assert "Lanzar un meteorito" in (ESTATICOS / "defensa.js").read_text(encoding="utf-8")


# ---------- 12. jerga interna ----------
JERGA = re.compile(r"§|sin_ag_|\bB1 de QA\b|\bCA-\d|\bRF-\d|ARX-\d|ev3-d\d|\bM\d{1,2}\b")


def _cadenas(texto: str):
    return re.findall(r'"([^"\n]{6,})"|`([^`\n]{6,})`', texto)


def test_la_interfaz_no_muestra_codigos_internos():
    html = re.sub(r"<[^>]+>", "\n", _html_sin_comentarios())
    assert not JERGA.search(html), JERGA.search(html)
    for nombre in ("laboratorio.js", "panel_ia.js", "textos.js", "final_tarjeta.js", "final_datos.js", "holo_datos.js", "holo3d.js"):
        for a, b in _cadenas((ESTATICOS / nombre).read_text(encoding="utf-8")):
            t = a or b
            if t.startswith(("/", "#")) or " " not in t:
                continue
            assert not JERGA.search(t), (nombre, t)
    # la pantalla Defensa puede citar RF/CA, pero los explica
    defensa = (ESTATICOS / "defensa.js").read_text(encoding="utf-8")
    assert "RF: requisito funcional" in defensa and "CA: criterio de aceptación" in defensa


@sin_node
def test_las_variantes_de_la_comparacion_tienen_nombre_claro_y_ayuda():
    claves = ["hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_mas_corta", "sin_ag_2opt", "ruta_corta", "ag_puro"]
    nombres = _js(f"{json.dumps(claves)}.map(m.nombreVariante)")
    assert all("_" not in n for n in nombres) and nombres[claves.index("sin_ag_2opt")] == "Sin AG (ruta con 2-opt)"
    assert "2-opt" in _js('m.ayudaVariante("sin_ag_2opt")') and "mejora local" in _js('m.ayudaVariante("sin_ag_2opt")')
    nota = _js("m.NOTA_POLITICAS + ' ' + m.notaVariantes({sin_ag_2opt: {}, hibrido: {}})")
    assert not JERGA.search(nota) and "undefined" not in nota
    assert _js('m.nombreVariante("variante_nueva")') == "variante nueva"                 # una variante desconocida no rompe nada


def test_la_comparacion_no_muestra_la_nota_cruda_del_archivo_de_resultados():
    lab = (ESTATICOS / "laboratorio.js").read_text(encoding="utf-8")
    assert "datos.nota" not in lab and "NOTA_POLITICAS" in lab


@sin_node
def test_los_codigos_de_motivo_se_traducen_y_el_desconocido_se_deja_tal_cual():
    assert _js('m.nombreMotivo("V-RNA-BARRANCO")') == "la RNA vio un barranco delante"
    assert _js('m.nombreMotivo("RNA-RIESGO:(3, 4):0.91")') == "la RNA confirmó riesgo en la celda"
    assert _js('m.nombreMotivo("CODIGO-NUEVO")') == "CODIGO-NUEVO"
    assert "V-" not in _js('m.nombresMotivos(["V-BORDE-BARRANCO", "OK"])')


def test_el_reporte_no_muestra_codigos_de_motivo_ni_nombres_de_modo_internos():
    from api.reporte import construir_html
    log = [{"paso": 1, "motivos": "V-RNA-BARRANCO;V-BORDE-BARRANCO", "reglas": "R1", "velocidad": 0.2, "p_barranco": 0.9, "bateria": 50}]
    hist = [{"n": 1, "paso_mision": 1, "modo": "automatico", "accion": "replanificar", "tecnica": "supervisor",
             "motivo": "V-RNA-BARRANCO", "velocidad": 0.2, "p_barranco": 0.9, "bateria": 50, "reglas": "R1"}]
    est = {"modo": "automatico", "estado": "EXITO", "puntaje": 120, "paso": 7, "modo_planeta": "rover"}
    h = construir_html({"estado": est, "filas_log": log, "historial": hist})
    assert "V-RNA-BARRANCO" not in h and "V-BORDE-BARRANCO" not in h
    assert "Híbrido" in h and "Éxito" in h and "Supervisor" in h
    assert "Puntaje simple" not in h and "100 × sitios visitados" not in h     # R23b: un solo puntaje, sin bono por veto
    assert "Los vetos no suman ni restan" in h                                  # el reporte explica su cuenta


# ---------- 13. pantalla final ----------
def test_la_meta_dice_que_inicia_y_resume_pasos_puntaje_y_bateria():
    html = _html_sin_comentarios()
    boton = re.search(r'<button id="meta-confirmar"[^>]*>([^<]+)</button>', html).group(1)
    assert boton != "Confirmar" and "misión" in boton.lower()
    assert 'id="meta-resumen"' in html and 'id="meta-puntaje-ayuda"' in html


@sin_node
def test_resumen_de_la_meta_y_formula_del_puntaje_simple():
    r = _js("m.resumenMeta({paso: 42, puntaje: 133, bateria_pct: 61.25, bateria: 90})")
    assert r == [["Pasos", "42"], ["Puntaje simple", "133"], ["Batería", "61,3 %"]]
    assert _js("m.resumenMeta(null)")[0][1] == "—"
    assert "100 × sitios visitados ÷ sitios totales" in _js("m.AYUDA_PUNTAJE_SIMPLE")
    assert "No es el puntaje de la pantalla final" in _js("m.AYUDA_PUNTAJE_SIMPLE")


def test_el_puntaje_del_estado_es_el_unico_y_coincide_con_su_desglose():
    """R23b: /estado publica `puntaje` (el único), su desglose (la suma redondeada y acotada a 0 da el puntaje) y la fórmula.
    Sustituye a la prueba que comparaba el puntaje simple del HUD (JS) con el del motor: el HUD ya no tiene cuenta propia."""
    c = _cliente()
    e = c.get("/estado").json()
    assert max(0, round(sum(t["puntos"] for t in e["puntaje_desglose"]))) == e["puntaje"]
    assert all(set(t) == {"clave", "etiqueta", "valor", "peso", "puntos"} for t in e["puntaje_desglose"])
    assert e["puntaje_formula"] and "simple" not in e["puntaje_formula"].lower()
    assert 0.0 <= e["ciencia_fraccion"] <= 1.0 and e["ciencia_maxima"] > 0


# ---------- 13. eventos con señal visible y condiciones del planeta (ronda 23, interfaz) ----------
def _js_modulo(archivo: str, expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / archivo).as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@sin_node
def test_la_ubicacion_de_un_evento_dice_celda_distancia_y_rumbo():
    f = lambda c, v, veh="rover": _js(f"m.ubicacionEvento({json.dumps(c)}, {json.dumps(v)}, {json.dumps(veh)})")
    assert f([19, 2], [19, 0]) == "fila 19, columna 2 · a 2 celdas al este del rover"
    assert f([17, 4], [19, 0], "sonda") == "fila 17, columna 4 · a 4 celdas al noreste de la sonda"
    assert f([19, 0], [19, 0]).endswith("justo donde está el rover")
    assert f([3, 3], None) == "fila 3, columna 3"
    assert _js("m.direccionEntre([5, 5], [8, 5])") == "sur" and _js("m.direccionEntre([5, 5], [5, 2])") == "oeste"


@sin_node
def test_el_aviso_de_un_evento_dice_donde_pasa_y_si_no_tuvo_efecto():
    t = _js('m.avisoEvento("barranco", "barranco", {ok: true, detalle: "barranco en (19, 2)", celdas: [[19, 2]]}, [19, 0], "rover")')
    assert t == "Evento barranco: barranco en (19, 2) · a 2 celdas al este del rover"   # sin repetir fila y columna
    t = _js('m.avisoEvento("falla_sensor", "falla de sensor", {ok: true, detalle: "la IA se detiene 3 pasos"}, [19, 0], "rover")')
    assert t == "Evento falla de sensor: la IA se detiene 3 pasos"
    t = _js('m.avisoEvento("senal_biologica", "señal biológica", {ok: false, detalle: "batería insuficiente para la señal"}, [19, 0], "rover")')
    assert t == "Evento señal biológica sin efecto: batería insuficiente para la señal"
    assert _js('m.celdasDeEvento("sismo", {grietas: [[1, 2], [3, 4]]})') == [[1, 2], [3, 4]]
    assert _js('m.celdasDeEvento("meteorito", {impacto: [18, 2]})') == [[18, 2]]
    assert _js('m.celdasDeEvento("noche", {ok: true})') == []


@sin_node
def test_todo_evento_de_la_lista_tiene_marca_en_la_escena():
    html = _html_sin_comentarios()
    opciones = re.findall(r'<option value="([a-z_]+)">', html[html.index('id="evento-nombre"'):html.index('id="evento-disparar"')])
    assert set(opciones) == {"barranco", "falla_sensor", "bateria_baja", "tormenta", "noche", "meteorito", "sismo", "baja_conectividad", "senal_biologica"}
    marcas = _js("m.MARCA_EVENTO")
    for nombre in opciones:
        assert nombre in marcas and marcas[nombre]["rotulo"] and marcas[nombre]["sobre"] in ("celda", "vehiculo")


@sin_node
def test_las_condiciones_del_planeta_leen_la_forma_real_del_motor_y_toleran_su_ausencia():
    sin = _js_modulo("planeta_datos.js", 'm.condicionesPlaneta(null, "Neptuno")')
    assert sin["gravedad"]["fuente"] == "referencia" and sin["viento"]["fuente"] == "referencia" and sin["hielo"]["fuente"] == "referencia"
    assert sin["viento"]["fuerza"] > 0.8 and sin["hielo"]["nivel"] == 1
    perfil = {"gravedad_g": 0.38, "viento": 0.4, "rumbo_viento": "E", "rafaga_prob": 0.04, "hielo_fraccion": 0.05, "fragilidad_hielo": 1.0,
              "factor_pendiente": 1.0, "arrastre": 0.0, "prob_tormenta_x": 2.0, "resumen": "x", "intensidad": 1.0, "sobrecosto_medio": 0.3}
    vivo = {"activa": True, "intensidad": 1.0, "viento": 0.8, "rumbo_viento": "NO", "rafaga": True, "rafaga_restante": 3,
            "celdas_hielo": 120, "resbalones_hielo": 2, "desvios_viento": 1, "energia_extra": 1.5}
    est = {"planeta_mecanicas": {"perfil": perfil, "estado": vivo}}
    c = _js_modulo("planeta_datos.js", f'm.condicionesPlaneta({json.dumps(est)}, "Marte")')
    assert c["gravedad"] == {"g": 0.38, "fuente": "motor"}
    assert c["viento"]["fuente"] == "motor" and c["viento"]["fuerza"] == 0.8 and c["viento"]["grados"] == 315 and c["viento"]["rafaga"] is True
    assert c["viento"]["rafagaPasos"] == 3 and c["hielo"]["celdas"] == 120 and c["hielo"]["fraccion"] == 0.05
    assert c["vivo"]["resbalones"] == 2 and c["vivo"]["energiaExtra"] == 1.5 and c["sobrecostoMedio"] == 0.3
    # sin estado vivo (solo perfil): el viento es el base por la intensidad del nivel
    sv = _js_modulo("planeta_datos.js", f'm.condicionesPlaneta({json.dumps({"planeta_mecanicas": {"perfil": perfil}})}, "Marte")')
    assert sv["viento"]["fuerza"] == 0.4 and sv["viento"]["fuente"] == "motor" and sv["vivo"]["hay"] is False
    # perfil plano de /planetas
    plano = _js_modulo("planeta_datos.js", f'm.condicionesPlaneta({json.dumps(perfil)}, "Marte")')
    assert plano["gravedad"]["fuente"] == "motor"
    # claves a medias o inválidas: cada una cae a su referencia sin romper las demás
    raro = {"planeta_mecanicas": {"perfil": {"gravedad_g": "mucha", "viento": 7, "hielo_fraccion": True}, "estado": 5}}
    r = _js_modulo("planeta_datos.js", f'm.condicionesPlaneta({json.dumps(raro)}, "Tierra")')
    assert r["gravedad"]["fuente"] == "referencia" and r["viento"]["fuerza"] == 1 and r["hielo"]["fuente"] == "referencia"
    assert _js_modulo("planeta_datos.js", 'm.condicionesPlaneta({}, "Plutón").gravedad.g') == 1
    filas = _js_modulo("planeta_datos.js", 'm.filasCondiciones(m.condicionesPlaneta(null, "Mercurio"))')
    assert [f[0] for f in filas][:3] == ["Gravedad", "Viento", "Hielo"] and filas[1][1] == "en calma" and filas[2][1] == "sin hielo"


@sin_node
def test_las_filas_vivas_muestran_rafaga_resbalon_y_sobrecoste_del_paso():
    perfil = {"gravedad_g": 0.38, "viento": 0.4, "rumbo_viento": "E", "rafaga_prob": 0.04, "hielo_fraccion": 0.05, "fragilidad_hielo": 1.0,
              "factor_pendiente": 1.0, "arrastre": 0.0, "prob_tormenta_x": 2.0}
    antes = {"planeta_mecanicas": {"perfil": perfil, "estado": {"viento": 0.4, "rumbo_viento": "E", "energia_extra": 1.0, "resbalones_hielo": 0}}}
    ahora = {"planeta_mecanicas": {"perfil": perfil, "estado": {"viento": 0.8, "rumbo_viento": "E", "rafaga": True, "rafaga_restante": 2,
                                                                  "energia_extra": 1.4, "resbalones_hielo": 1}}}
    expr = (f'(() => {{ const a = m.condicionesPlaneta({json.dumps(antes)}, "Marte"), b = m.condicionesPlaneta({json.dumps(ahora)}, "Marte");'
            f' const d = m.deltaPaso(a, b); return {{ d, filas: m.filasCondiciones(b, d) }}; }})()')
    r = _js_modulo("planeta_datos.js", expr)
    assert r["d"]["resbalo"] is True and abs(r["d"]["extra"] - 0.4) < 1e-9
    textos = {f[0]: f[1] for f in r["filas"]}
    assert textos["Viento"] == "ráfaga fuerte · hacia el este (2 pasos)" and "este paso +0,40 %" in textos["Batería extra"]
    assert "¡Resbaló!" in textos and "1 resbalón" in textos["¡Resbaló!"]
    # sin lecturas vivas no hay delta ni filas vivas
    assert _js_modulo("planeta_datos.js", 'm.deltaPaso(null, null)') == {"extra": 0, "resbalo": False, "desvio": False}


@sin_node
def test_la_ficha_del_planeta_dice_que_cambia_al_jugar_con_los_datos_del_motor():
    marte = {"gravedad_g": 0.38, "viento": 0.4, "rumbo_viento": "E", "rafaga_prob": 0.04, "hielo_fraccion": 0.05, "fragilidad_hielo": 1.0,
             "factor_pendiente": 1.0, "arrastre": 0.0, "prob_tormenta_x": 2.0}
    frase = _js_modulo("planeta_datos.js", f'm.textoQueCambia({json.dumps(marte)}, "Marte")')
    assert frase.startswith("Al jugar aquí:") and "0,38 g" in frase and "hacia el este" in frase and "5 % del mapa" in frase
    venus = {"gravedad_g": 0.91, "viento": 0.2, "rumbo_viento": "NO", "rafaga_prob": 0.02, "hielo_fraccion": 0.0, "fragilidad_hielo": 1.0,
             "factor_pendiente": 1.0, "arrastre": 0.25, "prob_tormenta_x": 1.0}
    assert "atmósfera densa" in _js_modulo("planeta_datos.js", f'm.textoQueCambia({json.dumps(venus)}, "Venus")')
    filas = _js_modulo("planeta_datos.js", f'm.filasFicha({json.dumps(marte)}, "Marte")')
    assert [f["etiqueta"] for f in filas] == ["Gravedad", "Viento", "Hielo", "Al jugar aquí"]
    assert _js_modulo("planeta_datos.js", 'm.filasFicha(null, "Marte")') == [] and _js_modulo("planeta_datos.js", 'm.filasFicha({}, "Marte")') == []
    # la tarjeta de la intro suma esas filas solo si el catálogo trae `mecanicas`
    cat = {"planetas": [{"nombre": "Marte", "modo": "rover", "mecanicas": marte}]}
    con = _js_modulo("intro_datos.js", f'm.datosCuerpo("Marte", {json.dumps(cat)}).filas.map((f) => f.etiqueta)')
    assert "Al jugar aquí" in con
    sin = _js_modulo("intro_datos.js", 'm.datosCuerpo("Marte", {planetas: [{nombre: "Marte", modo: "rover"}]}).filas.map((f) => f.etiqueta)')
    assert "Al jugar aquí" not in sin


@sin_node
def test_cada_planeta_tiene_perfil_propio_sin_rocas_en_neptuno():
    perfiles = _js_modulo("planeta_datos.js", "m.PERFILES")
    assert set(perfiles) == {"Marte", "Mercurio", "Venus", "Tierra", "Saturno", "Urano", "Neptuno", "Júpiter"}
    assert len({p["firma"] for p in perfiles.values()}) == 8      # cada uno con su rasgo propio
    assert perfiles["Neptuno"]["rasgos"]["obstaculo"] == "nube_o_hielo"
    for gigante in ("Júpiter", "Saturno", "Urano", "Neptuno"):
        assert perfiles[gigante]["rasgos"]["obstaculo"] != "roca"
    assert perfiles["Neptuno"]["suelo"] != 0x3f6fd6    # ya no es el azul saturado de antes


def test_el_cine_oculta_todos_los_paneles_y_deja_un_boton_para_salir():
    css = (ESTATICOS / "estilos.css").read_text(encoding="utf-8")
    regla = re.search(r"body\.cine #registro[^{]*\{", css).group(0)
    for pieza in ("#columna", "#controles", "#dock", "#mensaje", ".fn-avisos"):
        assert pieza in regla
    assert 'id="cine-salir"' in _html_sin_comentarios()
    assert "#panel-ia" in css[css.index("body.cine #panel-ia"):][:80]


def test_la_intro_tiene_lista_de_planetas_y_zonas_de_clic_generosas():
    js = (ESTATICOS / "intro3d.js").read_text(encoding="utf-8")
    assert "in-lista" in js and "ZONA_FACTOR" in js and "velOrbital" in js
    assert "zona" in js and "intersectObjects(cuerpos.map((k) => k.zona)" in js
