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
def test_constantes_de_la_formula_y_rotulo():
    assert [_js(f"m.{n}") for n in ("PESO_CIENCIA", "PESO_BARRANCOS_EVITADOS", "PESO_BATERIA", "PENALIZACION_VIOLACION")] == [1000, 50, 5, 500]
    assert [_js(f"m.{n}") for n in ("UMBRAL_2_ESTRELLAS", "UMBRAL_3_CIENCIA", "UMBRAL_3_BATERIA")] == [0.6, 0.85, 20]
    assert _js("m.ROTULO_PUNTAJE") == "Puntaje de juego, no es un criterio de evaluación."
    assert _js("m.ROTULO_FICCION") == "Ficción, no evidencia"
    assert _js("m.ROTULO_PUNTAJE_HUD") != _js("m.ROTULO_PUNTAJE")
    assert _js("m.CIERRE_INACTIVIDAD_S") == 120


@sin_node
@pytest.mark.parametrize("r,esperado", [
    (dict(ciencia=1, bateria_pct=100, violaciones=0, barrancos_evitados=0), 1500),
    (dict(ciencia=0, bateria_pct=0, violaciones=0, barrancos_evitados=0), 0),
    (dict(ciencia=0.5, bateria_pct=40, violaciones=1, barrancos_evitados=4), 500 + 200 + 200 - 500),
    (dict(ciencia=0, bateria_pct=10, violaciones=9, barrancos_evitados=0), 0),            # mínimo 0
    (dict(ciencia=0.8333, bateria_pct=33.3, violaciones=0, barrancos_evitados=0), 1000),   # redondeo: 833,3+166,5 = 999,8
    (dict(ciencia=0.75, bateria_pct=20, violaciones=0, barrancos_evitados=0), 850),
])
def test_puntaje_final(r, esperado):
    assert _js(f"m.puntajeFinal({json.dumps(r)})") == esperado


@sin_node
def test_dato_ausente_no_es_un_cero_inventado():
    r = _js("m.normalizarResultado({estado:'EXITO'})")
    for clave in ("ciencia", "bateria_pct", "violaciones", "barrancos_evitados", "vetos", "replanificaciones", "distancia", "paso"):
        assert r[clave] is None, clave
    d = _js("m.desglosePuntaje(m.normalizarResultado({}))")
    assert d["total"] == 0 and all(t["dato"] is False for t in d["terminos"])
    assert _js("[m.formatoDato(null), m.formatoDato(undefined), m.formatoDato('x'), m.formatoDato(0)]") == ["—", "—", "—", "0"]
    assert _js("m.formatoDato(12,{sufijo:' celdas'})") == "12 celdas"


@sin_node
def test_normalizar_estado_real():
    e = dict(estado="EXITO", planeta="Marte", modo_planeta="rover", bateria=61.5, colisiones=1, pasos_sobre_tolerancia=2,
             vetos=3, replanes=4, sitios_visitados=3, sitios_totales=4, distancia_recorrida=77, paso=120,
             barrancos_evitados=2, avisos=["Aviso corto"])
    r = _js(f"m.normalizarResultado({json.dumps(e)})")
    assert r["ciencia"] == 0.75 and r["bateria_pct"] == 61.5 and r["violaciones"] == 3
    assert r["vetos"] == 3 and r["replanificaciones"] == 4 and r["distancia"] == 77 and r["paso"] == 120
    assert r["barrancos_evitados"] == 2 and r["planeta"] == "Marte" and r["modo"] == "rover"
    assert r["motivo_final"] == "EXITO" and r["codigo"] == "EXITO"
    # solo uno de los dos orígenes de la violación
    assert _js("m.normalizarResultado({colisiones:2}).violaciones") == 2
    assert _js("m.normalizarResultado({pasos_sobre_tolerancia:5}).violaciones") == 5
    assert _js("m.normalizarResultado(null).planeta") is None


@sin_node
def test_desglose_suma_el_total():
    d = _js(f"m.desglosePuntaje({_p(ciencia=0.5, bateria_pct=40, violaciones=1, barrancos_evitados=4)})")
    assert [t["clave"] for t in d["terminos"]] == ["ciencia", "barrancos", "bateria", "violaciones"]
    assert sum(t["puntos"] for t in d["terminos"]) == d["bruto"] == 400 and d["total"] == 400


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
    assert "Requiere un evento que el rover no tiene" in _js("m.NOTA_SIN_EVENTO")
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
    assert _evaluar(_paso(base, ambiente="normal"), en["memoria"])["ids"] == ["tormenta"]
    assert _evaluar(_paso({"codigo": "FRACASO"}, ambiente="normal"), en["memoria"])["ids"] == []   # no sobrevivió
    noche = _evaluar(_paso(base, ambiente="noche"))["memoria"]
    assert _evaluar(_paso(base, ambiente="noche"), noche)["ids"] == []
    assert _evaluar(_paso(base, ambiente="normal"), noche)["ids"] == ["noctambulo"]
    assert _evaluar(_paso(base, ambiente="normal"), noche)["memoria"]["mision"]["ambiente"] == "normal"
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
    assert "ROTULO_PUNTAJE_HUD" in (ESTATICOS / "app.js").read_text(encoding="utf-8") or "Puntaje simple" in (ESTATICOS / "index.html").read_text(encoding="utf-8")


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
