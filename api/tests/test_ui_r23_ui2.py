"""Ronda 23 (interfaz, segunda tanda): adaptadores puros del tramo de la RNA, de la evolución del AG y de la edición de reglas
difusas (con node), paridad del motor difuso local con difuso.py y comprobaciones estáticas del HTML y de los módulos nuevos."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
sin_node = pytest.mark.skipif(NODE is None, reason="node no está instalado")
NUEVOS = ("rna_tramo_datos.js", "ag_evolucion_datos.js", "ag_evolucion_simulacro.js", "evolucion3d.js", "evolucion_ui.js",
          "difuso_reglas_datos.js", "difuso_editor.js")
JERGA = re.compile(r"§|sin_ag_|\bCA-\d|\bRF-\d|ARX-\d|ev3-d\d|\bM\d{1,2}\b")


def _js(modulo: str, expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / modulo).as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# ---------- tramo de la RNA ----------
PROBS = {"libre": 0.98, "obstáculo": 0.01, "barranco": 0.01}


@sin_node
def test_sin_tramo_el_panel_muestra_la_celda_de_enfrente_con_su_coordenada():
    d = {"posicion": [19, 0], "celda": [18, 0], "rumbo": "N", "rna": {"probabilidades": PROBS, "probabilidades_usadas": PROBS}}
    r = _js("rna_tramo_datos.js", f"m.adaptarTramoRNA({json.dumps(d)})")
    assert r["real"] is False and len(r["filas"]) == 1
    f = r["filas"][0]
    assert f["celda"] == [18, 0] and f["distancia"] == 1 and f["clase"] == "libre" and "a 1 celda al norte del rover" in f["lugar"]
    assert _js("rna_tramo_datos.js", f"m.titularRNA(m.adaptarTramoRNA({json.dumps(d)}).filas[0])") == "libre 98,0 % · celda (18, 0)"


@sin_node
def test_con_tramo_hay_una_fila_por_celda_ordenada_y_marca_las_de_riesgo():
    barranco = {"libre": 0.02, "obstaculo": 0.08, "barranco": 0.9}      # clave sin tilde, como puede mandarla el motor
    d = {"posicion": [10, 10], "celda": [9, 10], "rna": {"probabilidades": PROBS, "tramo": [
        {"celda": [7, 10], "probabilidades": barranco, "distancia": 3}, {"celda": [9, 10], "probabilidades": PROBS, "distancia": 1},
        {"celda": [8, 10], "probabilidades": PROBS, "distancia": 2}, {"celda": "mal", "probabilidades": PROBS}, {"celda": [1, 1]}]}}
    r = _js("rna_tramo_datos.js", f"m.adaptarTramoRNA({json.dumps(d)})")
    assert r["real"] is True and [f["distancia"] for f in r["filas"]] == [1, 2, 3]
    assert r["filas"][2]["clase"] == "barranco" and r["filas"][2]["probabilidades"]["obstáculo"] == 0.08
    marcas = _js("rna_tramo_datos.js", f"m.celdasAMarcar(m.adaptarTramoRNA({json.dumps(d)}))")
    assert [x["riesgo"] for x in marcas] == [False, False, True]


@sin_node
def test_el_tramo_tolera_campos_ausentes_y_topa_en_cuatro_celdas():
    assert _js("rna_tramo_datos.js", "m.adaptarTramoRNA(null)") is None
    assert _js("rna_tramo_datos.js", "m.adaptarTramoRNA({})") is None
    assert _js("rna_tramo_datos.js", 'm.adaptarTramoRNA({rna: {tramo: []}, celda: [1, 1]})') is None
    muchas = {"rna": {"tramo": [{"celda": [i, 0], "probs": PROBS} for i in range(8)]}}
    assert len(_js("rna_tramo_datos.js", f"m.adaptarTramoRNA({json.dumps(muchas)}).filas")) == 4


# ---------- evolución del AG ----------
def _evolucion(**cambios):
    d = {"planeta": "Marte", "inicio": [19, 0], "refugio": [0, 29],
         "sitios": [{"id": "S1", "celda": [14, 16], "valor": 1, "ventana": [0, 40]}, {"id": "S2", "celda": [15, 3], "valor": 4, "ventana": None},
                    {"id": "S3", "celda": [8, 7], "valor": 8, "ventana": [10, 60]}],
         "bases": [[16, 7]],
         "generaciones": [
             {"n": 0, "mejor": 5.0, "media": 3.0, "peor": 1.0, "diversidad": 0.9, "candidatos": [
                 {"orden": ["S2", "S1", "S3"], "recargas": [2], "camino": None, "fitness": 5.0, "factible": False, "violaciones": ["llega tarde a S3"]},
                 {"orden": ["S1", "S2", "S3"], "recargas": [], "camino": None, "fitness": 4.0, "factible": True, "violaciones": []},
                 {"orden": ["S1", "S2", "S3"], "recargas": [], "camino": None, "fitness": 3.5, "factible": True, "violaciones": []}]},
             {"n": 1, "candidatos": [{"orden": ["S3", "S2", "S1"], "fitness": 7.5, "factible": True, "camino": [[19, 0], [16, 7], [8, 7]]}]}],
         "mejor": {"orden": ["S3", "S2", "S1"], "fitness": 7.5, "factible": True},
         "parametros_difuso": {"umbral_cerca_m": 3}, "tiempo_s": 1.25}
    d.update(cambios)
    return d


@sin_node
def test_la_evolucion_adapta_el_contrato_con_ventanas_recargas_y_lineas_rectas():
    r = _js("ag_evolucion_datos.js", f"m.adaptarEvolucion({json.dumps(_evolucion())})")
    assert r["estado"] == "ok" and r["fuente"] == "motor" and r["seleccionada"] == 1 and r["hayVentanas"] and r["hayRecargas"]
    g0 = r["generaciones"][0]
    # los dos órdenes idénticos se dibujan una sola vez y se cuenta cuántos eran
    assert [c["fitness"] for c in g0["candidatos"]] == [5.0, 4.0] and g0["candidatos"][1]["copias"] == 2
    c = g0["candidatos"][0]
    # sin `camino`: inicio → S2 → S1 → (base de recarga antes de S3) → S3 → refugio, con segmentos rectos
    assert c["rectas"] is True and c["puntos"] == [[19, 0], [15, 3], [14, 16], [16, 7], [8, 7], [0, 29]]
    assert c["paradas"] == [{"indice": 2, "celda": [16, 7]}] and c["factible"] is False and c["violaciones"] == ["llega tarde a S3"]
    # con `camino` se usa tal cual y las bases usadas son las que pisa
    c1 = r["generaciones"][1]["candidatos"][0]
    assert c1["rectas"] is False and c1["puntos"] == [[19, 0], [16, 7], [8, 7]] and c1["basesUsadas"] == [[16, 7]]
    # media, peor y diversidad que faltan se calculan; el `mejor` viene del motor
    g1 = r["generaciones"][1]
    assert g1["mejor"] == 7.5 and g1["media"] == 7.5 and g1["diversidad"] is None
    assert r["tiempoS"] == 1.25 and r["parametrosDifuso"] == [["umbral_cerca_m", 3]]


@sin_node
def test_la_evolucion_vacia_o_rota_da_un_estado_vacio_con_motivo_claro():
    for crudo in ("null", "{hay_plan: false}", "{sin_sitios: true}", "{sitios: [], generaciones: []}", f"{{...{json.dumps(_evolucion())}, generaciones: []}}"):
        r = _js("ag_evolucion_datos.js", f"m.adaptarEvolucion({crudo})")
        assert r["estado"] == "vacio" and r["motivo"] and not JERGA.search(r["motivo"]), crudo
    # ids desconocidos y celdas rotas se ignoran sin romper
    raro = _evolucion(generaciones=[{"n": 0, "candidatos": [{"orden": ["S9", "S1"], "fitness": "x"}, {"orden": ["S1"], "fitness": 2, "factible": "si"}, None]}])
    r = _js("ag_evolucion_datos.js", f"m.adaptarEvolucion({json.dumps(raro)})")
    c = r["generaciones"][0]["candidatos"]
    # el orden con id desconocido queda en [S1] y se junta con el otro, igual: una sola ruta con la mejor cifra
    assert len(c) == 1 and c[0]["fitness"] == 2 and c[0]["factible"] is None and c[0]["orden"] == ["S1"] and c[0]["copias"] == 2


@sin_node
def test_el_respaldo_convierte_la_poblacion_del_laboratorio_genetico():
    ag = {"generaciones": [{"generacion": 0, "mejor": 1.0, "media": 0.5, "peor": 0.1, "poblacion": [
        {"cromosoma": [[14, 16], [15, 3]], "fitness": 1.0, "operacion": "cruce"}, {"cromosoma": [[15, 3], [14, 16]], "fitness": 0.5, "operacion": "mutacion"}]}],
        "candidatos": [{"cromosoma": [[14, 16], [15, 3]], "fitness": 1.0, "desglose": {"inviabilidad": 0}}]}
    ctx = {"inicio": [19, 0], "refugio": [0, 29], "sitios": [{"pos": [14, 16], "valor": 1}, {"pos": [15, 3], "valor": 4}, {"pos": [8, 7], "valor": 8}], "bases": [[16, 7]]}
    r = _js("ag_evolucion_datos.js", f"m.desdeLaboratorio({json.dumps(ag)}, {json.dumps(ctx)})")
    assert r["estado"] == "ok" and r["fuente"] == "laboratorio" and not r["hayVentanas"]
    assert [s["id"] for s in r["sitios"]] == ["S1", "S2"]            # el sitio que ninguna ruta visita (ya visitado) no se dibuja
    assert r["generaciones"][0]["candidatos"][0]["orden"] == ["S1", "S2"] and r["generaciones"][0]["diversidad"] == 1
    assert r["mejor"]["factible"] is True
    assert _js("ag_evolucion_datos.js", 'm.desdeLaboratorio({sin_sitios: true}, {})["estado"]') == "vacio"


@sin_node
def test_la_lectura_del_candidato_dice_orden_recargas_fitness_y_restriccion():
    expr = (f"(() => {{ const e = m.adaptarEvolucion({json.dumps(_evolucion())}); const g = e.generaciones[0];"
            f" return m.lecturaCandidato(g.candidatos[0], e, g); }})()")
    r = _js("ag_evolucion_datos.js", expr)
    filas = {f["clave"]: f for f in r["lineas"]}
    assert filas["Orden"]["valor"] == "S2 → S1 → recarga → S3" and filas["Recargas"]["valor"] == "antes de S3"
    assert "5,00" in filas["Fitness"]["valor"] and filas["Factible"]["valor"] == "no" and filas["Restricción que viola"]["valor"] == "llega tarde a S3"
    assert filas["Ventanas"]["valor"] == "S1 0–40 · S3 10–60" and "Candidato 1" in r["titulo"] and "Generación 0" in r["titulo"]
    assert _js("ag_evolucion_datos.js", "m.lecturaCandidato(null, {}, null)") is None


@sin_node
def test_el_simulacro_cumple_el_contrato_y_el_adaptador_lo_acepta():
    ctx = {"planeta": "Marte", "inicio": [19, 0], "refugio": [0, 29], "bases": [[16, 7]],
           "sitios": [{"pos": [14, 16], "valor": 1}, {"pos": [15, 3], "valor": 4}, {"pos": [8, 7], "valor": 8}, {"pos": [3, 20], "valor": 5}]}
    expr = (f"(() => {{ const s = m.simularEvolucion({json.dumps(ctx)}, {{autonomia: 16}}); return {{ s, n: s.generaciones.length }}; }})()")
    s = _js("ag_evolucion_simulacro.js", expr)
    assert s["n"] == 24 and all(g["candidatos"] for g in s["s"]["generaciones"]) and s["s"]["sitios"][0]["ventana"]
    assert _js("ag_evolucion_simulacro.js", f"m.simularEvolucion({json.dumps(ctx)}) === null") is False
    adaptado = _js("ag_evolucion_datos.js", f"m.adaptarEvolucion({json.dumps(s['s'])})")
    assert adaptado["estado"] == "ok" and adaptado["hayVentanas"]
    mejor = [g["mejor"] for g in adaptado["generaciones"]]
    assert mejor[-1] >= mejor[0]                                     # el AG mejora (o al menos no empeora) con las generaciones
    assert _js("ag_evolucion_simulacro.js", 'm.simularEvolucion({sitios: []})') == {"hay_plan": False}


# ---------- reglas difusas ----------
@sin_node
def test_el_motor_difuso_local_da_lo_mismo_que_difuso_py():
    from difuso import FuzzyController
    casos = [(1, 90, 2, 15), (10, 50, 20, -10), (19, 25, 30, 40), (5, 10, 40, 60), (8, 55, 5, 0), (0, 100, 0, -70), (14, 30, 10, 20), (3, 5, 0, -50)]
    c = FuzzyController()
    esperado = []
    for d, b, i, t in casos:
        r = c.inferir(d, b, i, t)
        esperado.append([round(float(r.velocidad), 6), sorted(x[0] for x in r.reglas_activadas)])
    expr = (f"(() => {{ const mod = m.modeloDeFabrica(); return {json.dumps(casos)}.map(([d, b, i, t]) => {{ const r = m.inferir(mod, {{distancia: d, bateria: b, inclinacion: i, temperatura: t}});"
            f" return [Math.round(r.velocidad * 1e6) / 1e6, r.reglas.filter((x) => x.fuerza > 0).map((x) => x.id).sort()]; }}); }})()")
    assert _js("difuso_reglas_datos.js", expr) == esperado


@sin_node
def test_las_reglas_de_fabrica_coinciden_con_las_del_motor():
    from difuso import CONJUNTOS, REGLAS
    m = _js("difuso_reglas_datos.js", "m.modeloDeFabrica()")
    assert {r["id"] for r in m["reglas"]} == {r["id"] for r in REGLAS}
    for r in REGLAS:
        mine = next(x for x in m["reglas"] if x["id"] == r["id"])
        assert mine["si"] == [list(par) for par in r["si"]] and mine["entonces"] == r["entonces"]
    assert set(m["variables"]) == set(CONJUNTOS)


@sin_node
def test_apagar_cambiar_o_pesar_una_regla_cambia_la_salida_y_se_valida():
    expr = ("(() => { const base = m.modeloDeFabrica(); const e = {distancia: 1, bateria: 90, inclinacion: 2, temperatura: 15};"
            " const antes = m.inferir(base, e); const mod = m.clonar(base); mod.reglas.find((r) => r.id === 'R1').activa = false;"
            " const sin = m.inferir(mod, e); const mod2 = m.clonar(base); mod2.reglas.find((r) => r.id === 'R1').peso = 0.5; const medio = m.inferir(mod2, e);"
            " return { antes: antes.velocidad, sin: sin.velocidad, medio: medio.velocidad, fuerzaMedia: medio.reglas.find((r) => r.id === 'R1').fuerza, dif: m.diferencias(base, mod), put: m.cuerpoPUT(mod, base) }; })()")
    r = _js("difuso_reglas_datos.js", expr)
    assert r["sin"] > r["medio"] > r["antes"] and r["fuerzaMedia"] == 0.5          # sin la regla de parar, el vehículo va más rápido
    assert r["dif"]["reglas"] == ["R1"] and r["dif"]["total"] == 1
    assert r["put"]["reglas"][0] == {"id": "R1", "si": {"distancia": "cerca"}, "entonces": "parar", "peso": 1, "activa": False} and "variables" not in r["put"]


@sin_node
def test_la_validacion_de_reglas_da_mensajes_claros():
    def validar(cambio: str):
        return _js("difuso_reglas_datos.js", f"(() => {{ const mod = m.modeloDeFabrica(); {cambio}; return m.validar(mod); }})()")
    assert validar("") == []
    r = validar("mod.reglas[0].peso = 1.5")
    assert any(x["tipo"] == "error" and x["texto"] == "R1: el peso debe estar entre 0 y 1." for x in r)
    r = validar("mod.variables.distancia.etiquetas.cerca = [0, 5, 3, 6]")
    assert any(x["tipo"] == "error" and "deben ir de menor a mayor" in x["texto"] and "«cerca» de distancia" in x["texto"] for x in r)
    r = validar("mod.variables.bateria.etiquetas.alta = [200, 210, 220, 230]")
    assert any("fuera del universo" in x["texto"] for x in r)
    r = validar("mod.variables.distancia.etiquetas.media = [5, 5, 5]")
    assert any("no pueden ser todos iguales" in x["texto"] for x in r)
    r = validar("mod.reglas.forEach((x) => { x.activa = false; })")
    assert any(x["tipo"] == "error" and x["donde"] == "reglas" for x in r)
    r = validar("mod.reglas[0].entonces = 'volar'")
    assert any("la velocidad «volar» no existe" in x["texto"] for x in r)
    # un hueco entre etiquetas es un aviso (no bloquea), y una regla que nunca se activa también
    r = validar("mod.variables.distancia.etiquetas.media = [4, 5, 6]; mod.variables.distancia.etiquetas.lejos = [15, 17, 20, 20]; mod.variables.distancia.etiquetas.cerca = [0, 0, 3, 4]")
    assert any(x["tipo"] == "aviso" and "ninguna etiqueta cubre" in x["texto"] for x in r) and not any(x["tipo"] == "error" for x in r)
    r = validar("mod.reglas[0].si = [['distancia', 'cerca'], ['distancia', 'lejos']]")
    assert any("usa distancia dos veces" in x["texto"] for x in r)
    r = validar("mod.reglas[0].si = []")
    assert any("no tiene ninguna condición" in x["texto"] for x in r)


@sin_node
def test_el_adaptador_de_reglas_acepta_las_dos_formas_del_antecedente_y_tolera_huecos():
    crudo = {"personalizadas": True, "variables": {"distancia": {"universo": [0, 20], "etiquetas": {"cerca": [0, 0, 3, 6], "mala": [1, 2], "lejos": [12, 17, 20, 20]}},
                                                    "rota": {"universo": [5, 1], "etiquetas": {"x": [0, 1, 2]}}},
             "salida": {"universo": [0, 1], "etiquetas": {"parar": [0, 0, 0.05, 0.15]}},
             "reglas": [{"si": {"distancia": "cerca"}, "entonces": "parar"}, {"id": 7, "si": [["distancia", "lejos"]], "entonces": "parar", "peso": 0.5, "activa": False, "texto": "t"}, None]}
    r = _js("difuso_reglas_datos.js", f"m.adaptarReglas({json.dumps(crudo)})")
    assert r["estado"] == "ok" and r["personalizadas"] is True and list(r["variables"]) == ["distancia"]
    assert list(r["variables"]["distancia"]["etiquetas"]) == ["cerca", "lejos"]            # la etiqueta con 2 puntos se descarta
    assert r["reglas"][0] == {"id": "R1", "si": [["distancia", "cerca"]], "entonces": "parar", "peso": 1, "activa": True, "texto": ""}
    assert r["reglas"][1]["id"] == "7" and r["reglas"][1]["si"] == [["distancia", "lejos"]] and r["reglas"][1]["activa"] is False
    for malo in ("null", "{}", "{variables: {}}", '{variables: {d: {universo: [0, 1], etiquetas: {a: [0, 1, 2]}}}, reglas: []}'):
        assert _js("difuso_reglas_datos.js", f"m.adaptarReglas({malo})")["estado"] == "vacio", malo


@sin_node
def test_la_superficie_y_el_barrido_se_recalculan_con_el_modelo_editado():
    expr = ("(() => { const base = m.modeloDeFabrica(); const e = {distancia: 1, bateria: 90, inclinacion: 2, temperatura: 15};"
            " const mod = m.clonar(base); mod.variables.distancia.etiquetas.cerca = [0, 0, 1, 2];"
            " const a = m.barrido(base, e), b = m.barrido(mod, e); const sa = m.superficie(base, e), sb = m.superficie(mod, e);"
            " return { n: a.length, desde: a[0].distancia, hasta: a[a.length - 1].distancia, distinto: a.some((f, i) => Math.abs(f.velocidad - b[i].velocidad) > 1e-6),"
            " dim: [sa.z.length, sa.z[0].length], cambia: sa.z.flat().some((v, i) => Math.abs(v - sb.z.flat()[i]) > 1e-6) }; })()")
    r = _js("difuso_reglas_datos.js", expr)
    assert r["n"] == 10 and r["desde"] == 10 and r["hasta"] == 1 and r["distinto"] and r["cambia"] and r["dim"] == [14, 28]


# ---------- estáticas ----------
def test_los_modulos_nuevos_no_usan_dialogos_nativos_ni_jerga():
    for nombre in NUEVOS:
        t = _leer(nombre)
        assert not re.search(r"\b(?:confirm|alert|prompt)\(", t), nombre
        assert "innerHTML" not in t, nombre
        for a, b in re.findall(r'"([^"\n]{6,})"|`([^`\n]{6,})`', t):
            cadena = a or b
            if cadena.startswith(("/", "#", ".")) or " " not in cadena:
                continue
            assert not JERGA.search(cadena), (nombre, cadena)


@sin_node
def test_los_textos_nuevos_no_tienen_jerga_ni_valores_sin_resolver():
    for objeto in ("EVO", "EDIT"):
        textos = _js("textos.js", f"Object.values(m.{objeto}).map((v) => typeof v === 'function' ? v('a', 'b', 'c') : v)")
        for t in textos:
            assert isinstance(t, str) and t and "undefined" not in t and "null" not in t, (objeto, t)
            assert not JERGA.search(t), (objeto, t)


def test_el_html_tiene_los_accesos_nuevos_con_ids_unicos():
    html = re.sub(r"<!--.*?-->", "", _leer("index.html"), flags=re.S)
    for ident in ("ag-ver-mapa", "evo-capa", "evo-abrir-controles", "dif-modo-explorar", "dif-modo-editar", "dif-explorar", "dif-edicion", "hud-reglas",
                  "cajon-izq", "menu-planeta-ficha", "rna-celda"):
        assert html.count(f'id="{ident}"') == 1, ident
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert "Reglas personalizadas activas" in html and "Ver la evolución en el mapa" in html


def test_el_css_angosto_no_toca_el_escritorio():
    css = _leer("estilos.css")
    bloque = css[css.index("/* ---- R23: anchos angostos"):]
    # todo lo del cajón vive dentro de @media (max-width: 900px) / 760px; fuera solo se oculta el asa
    fuera = re.sub(r"@media \(max-width: \d+px\) \{.*?\n\}\n", "", bloque, flags=re.S)
    assert ".cajon-asa { display: none; }" in fuera and "#columna" not in fuera
