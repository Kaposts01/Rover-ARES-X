"""Pantalla final: pruebas del módulo JS puro (final_datos.js) con node y de las claves nuevas de /estado; node es opcional."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parents[1] / "static"
NODE = shutil.which("node")
sin_node = pytest.mark.skipif(NODE is None, reason="node no está instalado")

OCHO = ["Mercurio", "Venus", "Tierra", "Marte", "Júpiter", "Saturno", "Urano", "Neptuno"]


def _js(expresion: str):
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'final_datos.js').as_uri())};"
              f"console.log(JSON.stringify({expresion}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _p(**k):
    base = dict(codigo="EXITO", ciencia=1, bateria_pct=50, violaciones=0, barrancos_evitados=0)
    return json.dumps({**base, **k})


@sin_node
def test_constantes_umbrales_y_rotulo_sin_formula_propia():
    assert [_js(f"m.{n}") for n in ("UMBRAL_2_ESTRELLAS", "UMBRAL_3_CIENCIA", "UMBRAL_3_BATERIA")] == [0.6, 0.85, 20]
    assert _js("m.ROTULO_PUNTAJE") == "Puntaje de juego, no es un criterio de evaluación."
    assert _js("m.ROTULO_FICCION") == "Ficción, no evidencia"
    assert _js("m.CIERRE_INACTIVIDAD_S") == 120
    # un solo puntaje: no existen los pesos ni el «puntaje simple» del HUD
    for nombre in ("PESO_CIENCIA", "PESO_BARRANCOS_EVITADOS", "PESO_BATERIA", "PENALIZACION_VIOLACION", "ROTULO_PUNTAJE_HUD"):
        assert _js(f"typeof m.{nombre}") == "undefined", nombre
    assert "simple" not in _js("m.NOTA_PUNTAJE").lower() and "vetos" not in _js("m.NOTA_PUNTAJE").lower()


_DESGLOSE = [
    {"clave": "ciencia", "etiqueta": "Ciencia recogida (0 a 1)", "valor": 0.495, "peso": 1000, "puntos": 495.0},
    {"clave": "bateria", "etiqueta": "Batería final (%)", "valor": 40, "peso": 5, "puntos": 200},
    {"clave": "violaciones", "etiqueta": "Violaciones", "valor": 1, "peso": 500, "puntos": -500},
]


@sin_node
def test_el_puntaje_es_el_que_manda_el_servidor_sin_cuenta_propia():
    e = dict(estado="EXITO", puntaje=1027, puntaje_desglose=_DESGLOSE, puntaje_formula="ciencia × 1000 + batería × 5 − violaciones × 500",
             ciencia_fraccion=0.495, ciencia_recogida=3.96, ciencia_maxima=8, sitios_visitados=8, sitios_totales=8, vetos=9, barrancos_evitados=9)
    r = _js(f"m.normalizarResultado({json.dumps(e)})")
    assert r["puntaje"] == 1027 and r["ciencia"] == 0.495 and r["ciencia_recogida"] == 3.96 and r["ciencia_maxima"] == 8
    assert r["objetivos_muestreados"] == 8 and r["objetivos_totales"] == 8     # sitios visitados: dato aparte de la ciencia
    d = _js(f"m.desglosePuntaje(m.normalizarResultado({json.dumps(e)}))")
    assert d["total"] == 1027 and d["formula"].startswith("ciencia × 1000") and [t["clave"] for t in d["terminos"]] == ["ciencia", "bateria", "violaciones"]
    assert _js(f"m.puntajeFinal(m.normalizarResultado({json.dumps(e)}))") == 1027
    # los vetos no cambian el puntaje: es el mismo con 0 o con 50 vetos
    assert _js(f"m.puntajeFinal(m.normalizarResultado({json.dumps({**e, 'vetos': 50, 'barrancos_evitados': 50})}))") == 1027
    lineas = _js(f"m.desglosePuntaje(m.normalizarResultado({json.dumps(e)})).terminos.map(m.lineaTermino)")
    assert lineas == ["Ciencia recogida (0 a 1): 0,5 × 1.000 = +495", "Batería final (%): 40 × 5 = +200", "Violaciones: 1 × 500 = −500"]


@sin_node
def test_sin_puntaje_del_motor_se_muestra_sin_dato_y_no_se_inventa_una_cuenta():
    r = _js("m.normalizarResultado({estado:'EXITO', sitios_visitados: 3, sitios_totales: 3, bateria_pct: 80, vetos: 4, barrancos_evitados: 4})")
    assert r["puntaje"] is None and r["puntaje_desglose"] is None and r["puntaje_formula"] is None and r["ciencia"] is None
    assert _js("m.puntajeFinal(m.normalizarResultado({estado:'EXITO', sitios_visitados: 3, sitios_totales: 3}))") is None
    assert _js("m.desglosePuntaje(m.normalizarResultado({}))") == {"terminos": [], "formula": None, "total": None}
    assert _js("m.lineaTermino({clave:'x', etiqueta:'Dato', valor: null, puntos: null})") == "Dato: sin dato"


@sin_node
def test_dato_ausente_no_es_un_cero_inventado():
    r = _js("m.normalizarResultado({estado:'EXITO'})")
    for clave in ("ciencia", "bateria_pct", "violaciones", "barrancos_evitados", "vetos", "replanificaciones", "distancia", "paso"):
        assert r[clave] is None, clave
    assert _js("[m.formatoDato(null), m.formatoDato(undefined), m.formatoDato('x'), m.formatoDato(0)]") == ["—", "—", "—", "0"]
    assert _js("m.formatoDato(12,{sufijo:' celdas'})") == "12 celdas"


@sin_node
def test_normalizar_estado_real():
    e = dict(estado="EXITO", planeta="Marte", modo_planeta="rover", bateria=61.5, colisiones=1, pasos_sobre_tolerancia=2,
             vetos=3, replanes=4, sitios_visitados=3, sitios_totales=4, distancia_recorrida=77, paso=120,
             barrancos_evitados=2, avisos=["Aviso corto"])
    r = _js(f"m.normalizarResultado({json.dumps(e)})")
    assert r["ciencia"] is None and r["objetivos_muestreados"] == 3 and r["objetivos_totales"] == 4     # sitios ÷ totales ya no es «ciencia»
    assert r["bateria_pct"] == 61.5 and r["violaciones"] == 3 and r["colisiones"] == 1 and r["pasos_sobre_tolerancia"] == 2
    assert r["vetos"] == 3 and r["replanificaciones"] == 4 and r["distancia"] == 77 and r["paso"] == 120
    assert r["barrancos_evitados"] == 2 and r["planeta"] == "Marte" and r["modo"] == "rover"
    assert r["motivo_final"] == "EXITO" and r["codigo"] == "EXITO"
    # solo uno de los dos orígenes de la violación
    assert _js("m.normalizarResultado({colisiones:2}).violaciones") == 2
    assert _js("m.normalizarResultado({pasos_sobre_tolerancia:5}).violaciones") == 5
    assert _js("m.normalizarResultado(null).planeta") is None


@sin_node
@pytest.mark.parametrize("r,n", [
    (dict(codigo="FRACASO"), 0),
    (dict(codigo="MODO_SEGURO", ciencia=1), 0),
    (dict(codigo="EXITO", violaciones=1, ciencia=1, bateria_pct=90), 0),
    (dict(codigo="EXITO", ciencia=0.59, bateria_pct=90), 1),
    (dict(codigo="EXITO", ciencia=0.6, bateria_pct=90), 2),
    (dict(codigo="EXITO", ciencia=0.84, bateria_pct=90), 2),
    (dict(codigo="EXITO", ciencia=0.85, bateria_pct=19.9), 2),
    (dict(codigo="EXITO", ciencia=0.85, bateria_pct=20), 3),
    (dict(codigo="EXITO", ciencia=1, bateria_pct=None), 2),
    (dict(codigo="EXITO", ciencia=None, bateria_pct=50), 1),
])
def test_estrellas_en_los_umbrales(r, n):
    assert _js(f"m.estrellas({_p(**r)})") == n


def _det(**k):
    return _js(f"m.detalleEstrellas({_p(**k)})")


@sin_node
def test_las_estrellas_siempre_explican_cuantas_y_que_falta():
    d = _det(ciencia=0.495, bateria_pct=60)
    assert d["n"] == 1 and d["texto"].startswith("1 de 3: misión cumplida sin violaciones.")
    assert "Para la segunda" in d["texto"] and "60 %" in d["texto"] and "(llevas 49,5 %)" in d["texto"]
    d = _det(ciencia=0.7, bateria_pct=10)
    assert d["n"] == 2 and "Para la tercera" in d["texto"] and "85 %" in d["texto"] and "(llevas 70,0 %)" in d["texto"]
    assert "20 % de batería o más (quedó 10,0 %)" in d["texto"]
    d = _det(ciencia=0.9, bateria_pct=10)          # la ciencia ya alcanza: solo falta la batería
    assert d["n"] == 2 and "85 %" not in d["texto"].split("Para la tercera")[1] and "batería" in d["texto"]
    d = _det(ciencia=1, bateria_pct=80)
    assert d["n"] == 3 and d["texto"].startswith("3 de 3") and "máximo" in d["texto"]
    assert all(_det(**k)["texto"] for k in (dict(codigo="FRACASO"), dict(ciencia=None), dict(violaciones=None)))


@sin_node
def test_cero_estrellas_en_un_exito_se_explica_por_choques_calor_o_dato_desconocido():
    r = _js("m.detalleEstrellas(m.normalizarResultado({estado:'EXITO', colisiones: 2, pasos_sobre_tolerancia: 0, ciencia_fraccion: 1, bateria_pct: 80}))")
    assert r["n"] == 0 and "se cumplió" in r["texto"] and "2 choques" in r["texto"] and "cero violaciones" in r["texto"]
    r = _js("m.detalleEstrellas(m.normalizarResultado({estado:'EXITO', colisiones: 0, pasos_sobre_tolerancia: 3, ciencia_fraccion: 1}))")
    assert r["n"] == 0 and "3 pasos sobre la tolerancia térmica" in r["texto"]
    r = _js("m.detalleEstrellas(m.normalizarResultado({estado:'EXITO', ciencia_fraccion: 1}))")
    assert r["n"] == 0 and "no se pudo comprobar" in r["texto"]
    r = _js("m.detalleEstrellas(m.normalizarResultado({estado:'EXITO', colisiones: 0, pasos_sobre_tolerancia: 0}))")
    assert r["n"] == 1 and "dato no disponible" in r["texto"]       # sin ciencia del motor: 1 estrella y se dice
    r = _js("m.detalleEstrellas(m.normalizarResultado({estado:'FRACASO'}))")
    assert r["n"] == 0 and "no se cumplió" in r["texto"]


@sin_node
def test_titulos_y_decisiones_de_pantalla():
    assert _js("m.tituloFinal('EXITO')") == "¡Misión cumplida!"
    assert "fallida" in _js("m.tituloFinal('FRACASO')")
    assert "abortada" in _js("m.tituloFinal('MODO_SEGURO')") and "abortada" in _js("m.tituloFinal('SIN_RUTA')")
    f = lambda **k: _js(f"m.debeMostrarFinal({json.dumps(k)})")
    assert f(activada=True, terminal=True) is True
    assert f(activada=False, terminal=True) is False
    assert f(activada=True, terminal=False) is False
    assert f(activada=True, terminal=True, reducido=True) is True
    assert _js("m.debeMostrarFinal()") is False
    assert _js("[m.confetiPermitido({n:3,reducido:false}), m.confetiPermitido({n:3,reducido:true}), m.confetiPermitido({n:2,reducido:false})]") == [True, False, False]


@sin_node
def test_hay_22_logros_unicos_con_estado_y_ficcion_rotulada():
    logros = _js("m.LOGROS")
    assert len(logros) == 22 and len({x["id"] for x in logros}) == 22
    assert all(x["estado"] in ("directo", "adaptacion", "bloqueado") for x in logros)
    ficcion = {x["id"] for x in logros if x["ficcion"]}
    assert ficcion == {"primer_contacto", "senal_anomala", "geiser", "volcan", "frio_extremo"}
    assert all(x["nota"] for x in logros if x["ficcion"])                 # cada ficción lleva su nota visible
    bloqueados = {x["id"] for x in logros if x["estado"] == "bloqueado"}
    assert bloqueados == {"geiser", "volcan", "frio_extremo", "ojos_robot"}
    assert all(x["nota"] for x in logros if x["estado"] == "bloqueado")
    assert "Requiere un evento que este motor no tiene" in _js("m.NOTA_SIN_EVENTO")
    assert "no afirma vida" in _js("m.NOTA_SENAL")
    assert "8 cuerpos" in next(x for x in logros if x["id"] == "gran_explorador")["descripcion"]


def _evaluar(evento, memoria=None):
    mem = json.dumps(memoria) if memoria is not None else "undefined"
    return _js(f"(()=>{{const r=m.evaluarLogros({json.dumps(evento)},{mem},'F');return {{ids:r.nuevos.map(x=>x.id),memoria:r.memoria}};}})()")


def _paso(resultado, **k):
    return {"tipo": "paso", "resultado": resultado, **k}


@sin_node
def test_logros_de_inicio_viaje_y_cuerpos():
    r = _evaluar({"tipo": "inicio", "planeta": "Marte", "modo": "rover"})
    assert r["ids"] == ["explorador"] and r["memoria"]["visitados"] == ["Marte"]
    assert _evaluar({"tipo": "inicio", "planeta": "Marte"}, r["memoria"])["ids"] == []        # no se repite
    assert _evaluar({"tipo": "viaje", "desde": "Marte", "hacia": "Venus"})["ids"] == ["viajero"]
    mem = {"obtenidos": {}, "visitados": OCHO[:4], "labs": []}
    r = _evaluar({"tipo": "inicio", "planeta": "Saturno"}, mem)
    assert "trotamundos" in r["ids"] and "gran_explorador" not in r["ids"]
    mem = {"obtenidos": {}, "visitados": OCHO[:7], "labs": []}
    assert "gran_explorador" in _evaluar({"tipo": "viaje", "desde": "Tierra", "hacia": "Neptuno"}, mem)["ids"]
    # un cuerpo que no es perfil no cuenta
    assert _evaluar({"tipo": "inicio", "planeta": "Plutón"})["memoria"]["visitados"] == []


@sin_node
def test_logros_de_muestras_y_ciencia():
    assert _evaluar(_paso({"objetivos_muestreados": 0, "objetivos_totales": 3}))["ids"] == []
    assert _evaluar(_paso({"objetivos_muestreados": 1, "objetivos_totales": 3}))["ids"] == ["primera_muestra"]
    assert sorted(_evaluar(_paso({"objetivos_muestreados": 3, "objetivos_totales": 3}))["ids"]) == ["cientifico", "primera_muestra"]
    assert "cientifico" not in _evaluar(_paso({"objetivos_muestreados": 0, "objetivos_totales": 0}))["ids"]


@sin_node
def test_logros_de_resultado():
    exito = {"codigo": "EXITO", "modo": "rover", "bateria_pct": 50, "vetos": 0}
    assert _evaluar(_paso(exito))["ids"] == ["mision_cumplida"]
    assert _evaluar(_paso({**exito, "codigo": "FRACASO"}))["ids"] == []
    assert "aeronauta" in _evaluar(_paso({**exito, "modo": "sonda"}))["ids"]
    assert "aeronauta" not in _evaluar(_paso(exito))["ids"]
    assert "limite" in _evaluar(_paso({**exito, "bateria_pct": 14.9}))["ids"]
    assert "limite" not in _evaluar(_paso({**exito, "bateria_pct": 15}))["ids"]
    assert "limite" not in _evaluar(_paso({**exito, "bateria_pct": None}))["ids"]
    assert "ingeniero_cauto" in _evaluar(_paso({**exito, "vetos": 5}))["ids"]
    assert "ingeniero_cauto" not in _evaluar(_paso({**exito, "vetos": 4}))["ids"]
    # fracaso previo en la misma misión: no hay «sin fracaso»
    mem = _evaluar(_paso({"codigo": "SIN_RUTA"}))["memoria"]
    assert mem["mision"]["fallo"] is True
    assert "ingeniero_cauto" not in _evaluar(_paso({**exito, "vetos": 9}), mem)["ids"]


@sin_node
def test_logros_de_ambiente_y_eventos():
    base = {"codigo": "EXPLORACION"}
    en = _evaluar(_paso(base, ambiente="tormenta"))
    assert en["ids"] == [] and en["memoria"]["mision"]["ambiente"] == "tormenta"
    assert _evaluar(_paso(base, ambiente="normal", restante=0), en["memoria"])["ids"] == ["tormenta"]
    assert _evaluar(_paso({"codigo": "FRACASO"}, ambiente="normal", restante=0), en["memoria"])["ids"] == []   # no sobrevivió
    noche = _evaluar(_paso(base, ambiente="noche"))["memoria"]
    assert _evaluar(_paso(base, ambiente="noche"), noche)["ids"] == []
    assert _evaluar(_paso(base, ambiente="normal", restante=0), noche)["ids"] == ["noctambulo"]
    assert _evaluar(_paso(base, ambiente="normal", restante=0), noche)["memoria"]["mision"]["ambiente"] == "normal"
    assert _evaluar(_paso(base, meteorito=True))["ids"] == ["impacto"]
    assert _evaluar(_paso(base, meteorito=False))["ids"] == []
    assert _evaluar({"tipo": "meteorito"})["ids"] == ["impacto"]
    assert sorted(_evaluar(_paso(base, senalVisitada=True))["ids"]) == ["primer_contacto", "senal_anomala"]


@sin_node
def test_logros_de_cliente_laboratorios_y_barranco():
    r = _evaluar({"tipo": "laboratorio", "id": "ag"})
    r = _evaluar({"tipo": "laboratorio", "id": "difuso"}, r["memoria"])
    assert r["ids"] == []
    r = _evaluar({"tipo": "laboratorio", "id": "rna"}, r["memoria"])
    assert r["ids"] == ["cientifico_datos"]
    assert _evaluar({"tipo": "laboratorio", "id": "politicas"})["ids"] == ["comparador"]
    assert _evaluar({"tipo": "barranco"})["ids"] == ["arquitecto"]
    assert _evaluar({"tipo": "inventado"})["ids"] == [] and _evaluar(None)["ids"] == []


@sin_node
def test_los_bloqueados_nunca_se_desbloquean():
    for ev in ({"tipo": "inicio", "planeta": "Plutón"}, {"tipo": "inicio", "planeta": "Tritón"},
               _paso({"codigo": "EXITO", "modo": "sonda", "bateria_pct": 1, "vetos": 9, "objetivos_muestreados": 3, "objetivos_totales": 3},
                     senalVisitada=True, meteorito=True)):
        ids = set(_evaluar(ev)["ids"])
        assert not ids & {"geiser", "volcan", "frio_extremo", "ojos_robot"}


@sin_node
def test_evaluar_no_modifica_la_memoria_recibida():
    mem = {"obtenidos": {}, "visitados": [], "labs": []}
    antes = json.dumps(mem)
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'final_datos.js').as_uri())};"
              f"const mem={antes};m.evaluarLogros({{tipo:'inicio',planeta:'Marte'}},mem,'F');console.log(JSON.stringify(mem));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == mem


@sin_node
def test_leer_y_serializar_logros_tolerantes():
    vacia = {"obtenidos": {}, "visitados": [], "labs": [], "mision": {"ambiente": "normal", "fallo": False}}
    for malo in ("", "no es json", "null", "[]", "42", '"x"', "{", '{"obtenidos":5}', '{"obtenidos":[1,2],"visitados":"x"}'):
        assert _js(f"m.leerLogros({json.dumps(malo)})") == vacia, malo
    assert _js("m.leerLogros(undefined)") == vacia
    ok = _js("m.leerLogros(JSON.stringify({obtenidos:{impacto:{fecha:'F'},inventado:{fecha:'G'},viajero:7},visitados:['Marte','Plutón',3,'Marte'],labs:['ag','xx']}))")
    assert ok["obtenidos"] == {"impacto": {"fecha": "F"}} and ok["visitados"] == ["Marte"] and ok["labs"] == ["ag"]
    ida = _js("m.leerLogros(m.serializarLogros({obtenidos:{impacto:{fecha:'F'}},visitados:['Venus'],labs:['rna']}))")
    assert ida["obtenidos"] == {"impacto": {"fecha": "F"}} and ida["visitados"] == ["Venus"] and ida["labs"] == ["rna"]
    assert _js("m.serializarLogros(null)") == '{"obtenidos":{},"visitados":[],"labs":[]}'


@sin_node
def test_lista_logros_marca_los_obtenidos():
    lista = _js("m.listaLogros({obtenidos:{impacto:{fecha:'F'}}})")
    assert len(lista) == 22
    assert [x["id"] for x in lista if x["obtenido"]] == ["impacto"]
    assert next(x for x in lista if x["id"] == "impacto")["fecha"] == "F"


def test_teclas_que_pasan_y_guardas_en_app():
    # con la pantalla abierta solo pasan Tab y Enter; el espacio dispara en la partida, así que las funciones de atajo también salen
    if NODE:
        assert _js("m.TECLAS_QUE_PASAN") == ["Tab", "Enter"]
    else:
        assert '["Tab", "Enter"]' in (ESTATICOS / "final_datos.js").read_text(encoding="utf-8")
    tarjeta = (ESTATICOS / "final_tarjeta.js").read_text(encoding="utf-8")
    assert re.search(r"if \(!TECLAS_QUE_PASAN\.includes\(e\.key\)\) e\.stopPropagation\(\)", tarjeta)
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    for fn in ("disparar", "mover", "dispararEvento", "paso"):
        patron = rf"async function {fn}\([^)]*\) \{{(?:\s*if \([^\n]*\) return;[^\n]*)*?\s*if \(finActiva\(\)\) return"
        assert re.search(patron, app), f"falta la guarda en {fn}()"
    assert re.search(r"window\.addEventListener\(\"keydown\", \(ev\) => \{\s*if \(finActiva\(\)\) return;", app)


def test_textos_prohibidos_ausentes():
    # nombres del ejemplo armados por partes para no dejar su rastro en el repositorio
    prohibidos = ["REC" + "-BOT", "Persever" + "ance", "/ho" + "me", "herramien" + "tas/", "ESTA" + "DO.md",
                  "C:\\" + "Users", "Down" + "loads", "vista" + "3d", "ares" + "-x\\", "http://", "https://", "cdn", "innerHTML",
                  "__mod" + "Final", "__mod" + "Logros", "__mod" + "Iconos", "axf" + "-", "ares" + "x.logros"]
    for nombre in ("final_datos.js", "final_iconos.js", "final_tarjeta.js", "final_logros.js", "final_momentos.js"):
        ruta = ESTATICOS / nombre
        if not ruta.exists():
            continue
        txt = ruta.read_text(encoding="utf-8")
        for p in prohibidos:
            assert not re.search(re.escape(p), txt, re.I), f"{p} en {nombre}"
        assert not re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50]", txt), f"emoji en {nombre}"


@sin_node
def test_los_iconos_de_los_logros_existen():
    codigo = (f"import * as i from {json.dumps((ESTATICOS / 'final_iconos.js').as_uri())};"
              f"import * as m from {json.dumps((ESTATICOS / 'final_datos.js').as_uri())};"
              "console.log(JSON.stringify(m.LOGROS.map(l=>l.icono).filter(n=>!i.NOMBRES_ICONOS.includes(n))));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []


def test_el_rotulo_de_ficcion_y_del_puntaje_estan_en_la_tarjeta():
    tarjeta = (ESTATICOS / "final_tarjeta.js").read_text(encoding="utf-8")
    assert "ROTULO_PUNTAJE" in tarjeta and "ROTULO_FICCION" in tarjeta and "NOTA_PUNTAJE" in tarjeta
    for archivo in ESTATICOS.glob("*.js"):
        assert "Puntaje simple" not in archivo.read_text(encoding="utf-8"), archivo.name
    assert "Puntaje simple" not in (ESTATICOS / "index.html").read_text(encoding="utf-8")


# ---------- /estado: claves de solo lectura nuevas ----------
def test_estado_trae_las_claves_nuevas_sin_cambiar_las_existentes():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from fastapi.testclient import TestClient
    from api.servidor import Sesion, crear_app
    c = TestClient(crear_app(Sesion(semilla=11)))
    antes = c.get("/estado").json()
    for k in ("paso", "vetos", "replanes", "sitios_visitados", "sitios_totales", "distancia_recorrida", "barrancos_evitados"):
        assert isinstance(antes[k], int), k
    assert antes["paso"] == 0 and antes["distancia_recorrida"] == 0 and antes["sitios_visitados"] == 0 and antes["sitios_totales"] >= 1
    for k in ("planeta", "modo_planeta", "estado", "bateria", "puntaje", "colisiones", "pasos_sobre_tolerancia", "avisos"):
        assert k in antes
    assert c.post("/modo", json={"modo": "automatico"}).status_code == 200
    for _ in range(400):
        if c.post("/paso").json()["estado"] in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
    fin = c.get("/estado").json()
    assert fin["paso"] > 0 and fin["distancia_recorrida"] > 0 and fin["sitios_visitados"] >= 1
    assert fin["barrancos_evitados"] >= 0 and fin["vetos"] >= 0 and fin["replanes"] >= 0


def test_barrancos_evitados_cuenta_filas_con_veto_por_barranco():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from api.servidor import _barrancos_evitados

    class _Log:
        filas = [{"motivos": "V-BORDE-BARRANCO"}, {"motivos": "A;V-RNA-BARRANCO"}, {"motivos": "V-OBSTACULO-EN-RUTA"},
                 {"motivos": ""}, {"motivos": None}, {}]

    class _M:
        log = _Log()

    class _P:
        mision = _M()

    assert _barrancos_evitados(_P()) == 2


@sin_node
def test_h1_senal_de_otra_partida_no_desbloquea():
    # lógica del cliente: la señal activa de la partida A no cuenta en la B (inicio o semilla distinta)
    codigo = (f"import * as m from {json.dumps((ESTATICOS / 'final_logros.js').as_uri())};"
              "globalThis.localStorage={getItem(){return null},setItem(){},removeItem(){}};"
              "const l=m.crearLogros({almacen:m.crearAlmacenLocal()});"
              "const ids=[];const e=(x)=>l.revisarEstado({estado:'EXPLORACION',ambiente:'normal',...x}).forEach(n=>ids.push(n.id));"
              "e({semilla:1,senal:[2,3],paso:3});l.revisar({tipo:'inicio',planeta:'Marte'});e({semilla:2,senal:null,paso:0});"
              "const A=[...ids];e({semilla:2,senal:[4,4],paso:2});e({semilla:2,senal:null,paso:3});"
              "console.log(JSON.stringify({A,B:ids.filter(i=>i==='senal_anomala'||i==='primer_contacto')}));")
    r = subprocess.run([NODE, "--input-type=module", "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert "senal_anomala" not in o["A"] and "primer_contacto" not in o["A"]
    assert sorted(o["B"]) == ["primer_contacto", "senal_anomala"]


@sin_node
def test_h2_ambiente_solo_cuenta_si_termino_de_verdad():
    base = {"codigo": "EXPLORACION"}
    tor = _evaluar(_paso(base, ambiente="tormenta", restante=3))["memoria"]
    assert _evaluar(_paso(base, ambiente="noche", restante=8), tor)["ids"] == []        # evento manual que lo sobreescribe
    assert _evaluar(_paso(base, ambiente="normal", restante=0), tor)["ids"] == ["tormenta"]
    noc = _evaluar(_paso(base, ambiente="noche", restante=2))["memoria"]
    assert _evaluar(_paso(base, ambiente="tormenta", restante=6), noc)["ids"] == []
    assert _evaluar(_paso(base, ambiente="normal", restante=0), noc)["ids"] == ["noctambulo"]


@sin_node
def test_h4_violaciones_desconocidas_no_dan_estrella():
    assert _js(f"m.estrellas({_p(violaciones=None)})") == 0
    assert _js(f"m.estrellas({_p(violaciones=0)})") == 3


def test_h5_foco_atrapado_en_la_tarjeta():
    txt = (ESTATICOS / "final_tarjeta.js").read_text(encoding="utf-8")
    assert 'e.key === "Tab"' in txt and "e.shiftKey && activo === primero" in txt and "!e.shiftKey && activo === ultimo" in txt


def test_h6_plan_sin_referencia_a_inventario():
    plan = (Path(__file__).resolve().parents[2] / "docs" / "planes" / "PANTALLA_FINAL.md").read_text(encoding="utf-8")
    assert "inventario del ejemplo" not in plan and "proyecto de ejemplo del usuario" in plan


def test_cierre_de_la_pantalla_final_y_textos_sin_vehiculo_fijo():
    """Esc y «Cerrar y revisar la partida» dejan la partida a la vista; «Ver resultado» la reabre; los textos nombran al vehículo según el modo."""
    tarjeta = (ESTATICOS / "final_tarjeta.js").read_text(encoding="utf-8")
    html = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    app = (ESTATICOS / "app.js").read_text(encoding="utf-8")
    assert "Cerrar y revisar la partida" in tarjeta and "Omitir el informe" not in tarjeta
    assert 'e.key === "Escape"' in tarjeta and "llamar(alContinuar)" in tarjeta
    assert 'id="ver-resultado"' in html and "Ver resultado" in html and 'cierreDeMision(estado.estado, null)' in app
    assert 'cerrarFinal("revisar")' in app or 'cerrarFinal && cerrarFinal("revisar")' in app
    # ningún «rover» fijo en los textos visibles del HTML que no cambian con el modo
    assert "Celda frente al rover" not in html and "La cámara sigue al rover</label>" not in html
    assert "3 mejores rutas" not in html and 'id="ag-desglose-titulo"' in html
