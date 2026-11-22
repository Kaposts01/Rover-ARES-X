"""Ronda 23: comparación de dos políticas lado a lado y récords por semilla.

Se instala con una sola línea en crear_app (`extras.instalar(app, sys.modules[__name__])`).

Comparación (/comparar): cada lado es una `Sesion` propia, distinta de la partida global (`app.state.sesion`), que no se
toca. Para dar un paso se reutiliza la ruta POST /paso del propio servidor (así los drones y el combate funcionan igual
que en una partida normal): se pone la sesión del lado como activa durante esa llamada y se restaura siempre al
terminar. Es seguro porque el middleware del servidor atiende de a una las peticiones al motor (candado de hilos).
Se guardan como mucho MAX_COMPARACIONES a la vez; las más viejas se descartan, y también las que llevan
TTL_SEGUNDOS sin usarse.

Récords (/records): ver api/records.py.
"""
import collections
import hashlib
import math
import time
import uuid
from typing import Any

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from api import records

MAX_COMPARACIONES = 4
TTL_SEGUNDOS = 30 * 60
MAX_PASOS_LADO = 600          # tope por lado: una partida que no termina se corta aquí y se marca «sin terminar»
MAX_AVANCE = 60               # pasos por petición
LIMITE = "LIMITE"

# política → (modo de conducción de la sesión, variante del híbrido). Los nombres claros viven en textos.js.
POLITICAS = {
    "hibrido": ("automatico", "hibrido"),
    "sin_rna": ("automatico", "sin_rna"),
    "sin_difuso": ("automatico", "sin_difuso"),
    "sin_ag_vecino": ("automatico", "sin_ag_vecino"),
    "sin_ag_mas_corta": ("automatico", "sin_ag_mas_corta"),
    "sin_ag_2opt": ("automatico", "sin_ag_2opt"),
    "ruta_corta": ("automatico", "ruta_corta"),
    "ag_puro": ("automatico", "ag_puro"),
    "solo_rna": ("rna", "hibrido"),
    "solo_difuso": ("difuso", "hibrido"),
    "solo_ag": ("ag", "hibrido"),
}


def puntaje_de_juego(e: dict) -> int:
    """El puntaje de la pantalla final (la misma fórmula que final_datos.js): ciencia(0 a 1)×1000 + vetos por barranco×50 +
    batería(%)×5 − violaciones×500, mínimo 0. Es el que ve el jugador, por eso es el de los récords."""
    total = float(e.get("sitios_totales") or 0)
    ciencia = min(1.0, max(0.0, float(e.get("sitios_visitados") or 0) / total)) if total > 0 else 0.0
    violaciones = float(e.get("colisiones") or 0) + float(e.get("pasos_sobre_tolerancia") or 0)
    bruto = 1000 * ciencia + 50 * float(e.get("barrancos_evitados") or 0) + 5 * float(e.get("bateria_pct") or 0) - 500 * violaciones
    return max(0, int(math.floor(bruto + 0.5)))


class ComparacionIn(BaseModel):
    semilla: Any = None
    nivel: Any = 1
    tamano: Any = "pequeno"
    planeta: Any = "Marte"
    modo: Any = "rover"
    politica_a: Any = "hibrido"
    politica_b: Any = "sin_rna"


class AvanceIn(BaseModel):
    pasos: Any = 1


def _aplicar_variante(partida, variante: str) -> None:
    """Misma preparación que juego.comparacion.partida_variante, pero sobre una partida ya creada con el planeta, el
    nivel y el tamaño pedidos (partida_variante solo sabe del mapa base de las evaluaciones)."""
    if variante == "hibrido":
        return
    from juego import comparacion as cmp
    m = partida.mision
    if variante == "sin_rna":
        m.usar_rna = False
        return
    if variante == "sin_difuso":
        m.usar_difuso = False
        return
    if getattr(partida, "plan_activo", False) and variante in ("sin_ag_vecino", "sin_ag_2opt", "sin_ag_mas_corta"):
        # R23: en la partida jugable el plan lleva ventanas y recargas: la «sin AG» es la heurística con la misma ejecución del plan
        from juego.partida import _ag_restringido
        m._optimizar_ag = _ag_restringido(partida, heuristica="2opt" if variante == "sin_ag_2opt" else "vecino",
                                          anotar=partida._avisar)
        partida._wp = []
        partida._plan_inicial_pendiente = False
    elif variante == "sin_ag_vecino":
        m._optimizar_ag = cmp._orden_voraz(m)
    elif variante == "sin_ag_2opt":
        m._optimizar_ag = cmp._orden_2opt(m)
    elif variante == "sin_ag_mas_corta":
        from juego.partida import _ag_con_todos_los_sitios
        m._optimizar_ag = _ag_con_todos_los_sitios(m, cmp._orden_voraz(m), pesos={"ciencia": 0, "distancia": 5, "energia": 0, "riesgo": 0, "tiempo": 0})
    elif variante == "ruta_corta":
        m.usar_rna = False
        m.usar_difuso = False
        m.riesgo = np.zeros_like(m.riesgo)
        m._optimizar_ag = cmp._orden_voraz(m)
    elif variante == "ag_puro":
        m.usar_rna = False
        m.usar_difuso = False
        cmp._congelar_riesgo(m)
        return
    else:
        raise ValueError(variante)
    m.objetivos = []
    m._planear()


def _huella(sesion) -> str:
    m = sesion.partida.mundo
    h = hashlib.sha1()
    h.update(np.asarray(m.tipo).tobytes())
    h.update(repr((sorted(m.sitios.items()), list(m.inicio), list(m.refugio))).encode())
    return h.hexdigest()[:12]


class Lado:
    def __init__(self, sesion, politica: str):
        self.sesion = sesion
        self.politica = politica
        self.pasos = []          # una ficha por paso dado
        self.huella = _huella(sesion)

    @property
    def terminado(self) -> bool:
        return self.sesion.terminada() or self.limite

    @property
    def limite(self) -> bool:
        return len(self.pasos) >= MAX_PASOS_LADO and not self.sesion.terminada()


class Comparacion:
    def __init__(self, ident: str, datos: dict, lados: list):
        self.id = ident
        self.datos = datos
        self.lados = lados
        self.divergencia = None
        self.usada = time.time()


def instalar(app: FastAPI, servidor) -> None:
    """Registra las rutas /comparar y /records en `app`. `servidor` es el módulo api.servidor (sus ayudas)."""
    Sesion, ErrorApi = servidor.Sesion, servidor.ErrorApi
    app.state.comparaciones = collections.OrderedDict()

    def ruta_paso():
        for r in app.routes:
            if getattr(r, "path", None) == "/paso" and "POST" in getattr(r, "methods", ()):
                return r.endpoint
        raise ErrorApi(500, "ruta de paso no disponible")

    def limpiar():
        ahora = time.time()
        for k in [k for k, c in app.state.comparaciones.items() if ahora - c.usada > TTL_SEGUNDOS]:
            del app.state.comparaciones[k]

    def obtener(ident: str) -> Comparacion:
        limpiar()
        c = app.state.comparaciones.get(ident)
        if c is None:
            raise ErrorApi(404, "esa comparación ya no existe (se descartan las más viejas): crea otra")
        c.usada = time.time()
        app.state.comparaciones.move_to_end(ident)
        return c

    def estado_de(l: Lado) -> str:
        return LIMITE if l.limite else l.sesion.partida.estado_visible()

    def ficha(l: Lado, n: int, r: dict) -> dict:
        e = servidor._estado(l.sesion)
        ci = l.sesion.partida.ciencia()      # R23: valor de cada sitio por la calidad de su ventana
        return {"n": n, "posicion": e["posicion"], "accion": r.get("accion"), "motivos": list(r.get("motivos") or []),
                "estado": estado_de(l), "bateria_pct": e["bateria_pct"], "puntaje": puntaje_de_juego(e),
                "ciencia_recogida": float(ci["recogida"]), "ciencia_maxima": float(ci["maxima"]),
                "ciencia_fraccion": float(ci["fraccion"]),
                "sitios_visitados": e["sitios_visitados"], "sitios_totales": e["sitios_totales"],
                "visitados": [list(map(int, c)) for c in sorted(l.sesion.partida.mision.visitados)],
                "vetos": e["vetos"], "colisiones": e["colisiones"], "replanes": e["replanes"]}

    def dar_paso(l: Lado) -> None:
        if l.terminado:
            return
        previa = app.state.sesion
        app.state.sesion = l.sesion
        try:
            try:
                r = ruta_paso()()
            except ErrorApi as exc:                 # la partida del lado ya había terminado
                r = {"accion": "fin", "motivos": [exc.motivo]}
            except Exception:
                r = {"accion": "error", "motivos": []}
                l.sesion.partida.mision.estado = "FRACASO"
        finally:
            app.state.sesion = previa
        l.pasos.append(ficha(l, len(l.pasos) + 1, r))

    def divergir(c: Comparacion) -> None:
        if c.divergencia is not None:
            return
        a, b = c.lados[0].pasos, c.lados[1].pasos
        for i in range(min(len(a), len(b))):
            if a[i]["posicion"] != b[i]["posicion"] or a[i]["accion"] != b[i]["accion"]:
                c.divergencia = {"n": i + 1,
                                 "a": {k: a[i][k] for k in ("posicion", "accion", "motivos")},
                                 "b": {k: b[i][k] for k in ("posicion", "accion", "motivos")}}
                return

    def tabla(c: Comparacion):
        a, b = c.lados
        if not (a.terminado and b.terminado):
            return None
        fa, fb = a.pasos[-1] if a.pasos else None, b.pasos[-1] if b.pasos else None
        if fa is None or fb is None:
            return None
        ra, rb = fa["estado"], fb["estado"]
        mismo = (ra == "EXITO") == (rb == "EXITO")

        def mejor(x, y, mayor=True, solo_si=True):
            if not solo_si or x == y:
                return "empate" if x == y else None
            return "a" if (x > y) == mayor else "b"
        filas = [
            {"clave": "resultado", "a": ra, "b": rb, "ganador": ("a" if ra == "EXITO" else "b") if not mismo else "empate"},
            {"clave": "pasos", "a": fa["n"], "b": fb["n"], "ganador": mejor(fa["n"], fb["n"], False, mismo)},
            {"clave": "puntaje", "a": fa["puntaje"], "b": fb["puntaje"], "ganador": mejor(fa["puntaje"], fb["puntaje"])},
            {"clave": "ciencia_fraccion", "a": fa["ciencia_fraccion"], "b": fb["ciencia_fraccion"],
             "ganador": mejor(fa["ciencia_fraccion"], fb["ciencia_fraccion"])},
            {"clave": "bateria_pct", "a": fa["bateria_pct"], "b": fb["bateria_pct"], "ganador": mejor(fa["bateria_pct"], fb["bateria_pct"])},
            {"clave": "sitios_visitados", "a": fa["sitios_visitados"], "b": fb["sitios_visitados"], "ganador": mejor(fa["sitios_visitados"], fb["sitios_visitados"])},
            {"clave": "vetos", "a": fa["vetos"], "b": fb["vetos"], "ganador": mejor(fa["vetos"], fb["vetos"], False)},
            {"clave": "colisiones", "a": fa["colisiones"], "b": fb["colisiones"], "ganador": mejor(fa["colisiones"], fb["colisiones"], False)},
        ]
        general = filas[0]["ganador"]
        if general == "empate":
            general = filas[2]["ganador"]
        return {"filas": filas, "ganador": general if general in ("a", "b") else "empate"}

    def resumen(c: Comparacion, desde=(0, 0)) -> dict:
        divergir(c)
        return {"id": c.id, "divergencia": c.divergencia, "tabla": tabla(c),
                "lados": [{"politica": l.politica, "terminado": l.terminado, "estado": estado_de(l),
                           "total": len(l.pasos), "pasos": l.pasos[desde[i]:]} for i, l in enumerate(c.lados)]}

    @app.post("/comparar")
    def crear(datos: ComparacionIn):
        for p in (datos.politica_a, datos.politica_b):
            if not isinstance(p, str) or p not in POLITICAS:
                raise ErrorApi(400, f"política inválida: {p!r}; usa una de {sorted(POLITICAS)}")
        semilla, nivel = servidor.validar_partida(servidor.PartidaIn(semilla=datos.semilla, nivel=datos.nivel, planeta=datos.planeta, modo=datos.modo))
        filas, columnas = servidor._tamano(datos.tamano)
        lados = []
        for politica in (datos.politica_a, datos.politica_b):
            modo, variante = POLITICAS[politica]
            try:
                s = Sesion(semilla=semilla, nivel=nivel, filas=filas, columnas=columnas, planeta=datos.planeta)
            except ValueError as exc:
                raise ErrorApi(400, str(exc))
            s.planeta, s.modo_planeta = datos.planeta, datos.modo
            s.modo = modo
            s.partida.modo_ia = modo
            _aplicar_variante(s.partida, variante)
            lados.append(Lado(s, politica))
        limpiar()
        while len(app.state.comparaciones) >= MAX_COMPARACIONES:
            app.state.comparaciones.popitem(last=False)
        c = Comparacion(uuid.uuid4().hex[:10], {"semilla": semilla, "nivel": nivel, "tamano": datos.tamano,
                                               "planeta": datos.planeta, "vehiculo": datos.modo}, lados)
        app.state.comparaciones[c.id] = c
        m = lados[0].sesion.partida
        mundo = m.mundo
        return {**resumen(c), **c.datos,
                "mapas_iguales": lados[0].huella == lados[1].huella, "huellas": [l.huella for l in lados],
                "mapa": {"filas": int(mundo.tipo.shape[0]), "columnas": int(mundo.tipo.shape[1]), "tipo": mundo.tipo.tolist(),
                         "inicio": servidor._celda(mundo.inicio), "refugio": servidor._celda(mundo.refugio),
                         "sitios": [{"pos": servidor._celda(p), "valor": int(v)} for p, v in mundo.sitios.items()],
                         "estaciones": [servidor._celda(e) for e in m.estaciones]},
                "inicio": [{"posicion": servidor._celda(l.sesion.partida.rover.posicion),
                            "bateria_pct": servidor._estado(l.sesion)["bateria_pct"],
                            "sitios_totales": len(l.sesion.partida.mundo.sitios)} for l in lados]}

    @app.get("/comparar/{ident}")
    def ver(ident: str):
        return resumen(obtener(ident))

    @app.post("/comparar/{ident}/avanzar")
    def avanzar(ident: str, datos: AvanceIn):
        c = obtener(ident)
        n = datos.pasos
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_AVANCE:
            raise ErrorApi(400, f"pasos debe ser un entero entre 1 y {MAX_AVANCE}")
        desde = (len(c.lados[0].pasos), len(c.lados[1].pasos))
        for _ in range(n):
            for l in c.lados:
                dar_paso(l)
            if all(l.terminado for l in c.lados):
                break
        return resumen(c, desde)

    @app.delete("/comparar/{ident}")
    def borrar(ident: str):
        return {"ok": app.state.comparaciones.pop(ident, None) is not None}

    # ---------- récords ----------
    @app.post("/records/registrar")
    def registrar():
        """Guarda la misión terminada de la partida activa (una sola vez por partida) y dice si es récord."""
        s = app.state.sesion
        if s is None:
            raise ErrorApi(409, "sin partida: crea una con POST /partida")
        if not s.terminada():
            raise ErrorApi(409, "la misión aún no terminó")
        previo = getattr(s, "record_registrado", None)
        if previo is not None:
            return {**previo, "ya_registrado": True}
        e = servidor._estado(s)
        mundo = s.partida.mundo
        filas, columnas = int(mundo.tipo.shape[0]), int(mundo.tipo.shape[1])
        tamano = next((k for k, v in servidor.TAMANOS.items() if v == (filas, columnas)), f"{filas}x{columnas}")
        origen = records.origen_de(s.historial)
        nuevo = {"planeta": e["planeta"], "nivel": int(s.nivel), "tamano": tamano, "semilla": int(s.semilla),
                 "vehiculo": e["modo_planeta"], "origen": origen, "modo": s.modo,
                 "resultado": e["estado"], "pasos": int(e["paso"]), "puntaje": puntaje_de_juego(e),
                 "puntaje_simple": int(e["puntaje"]),
                 "bateria_pct": float(e["bateria_pct"]), "sitios_visitados": e["sitios_visitados"],
                 "sitios_totales": e["sitios_totales"]}
        try:
            r = records.registrar(nuevo)
        except OSError:
            raise ErrorApi(500, "no se pudo guardar el récord en el disco")
        s.record_registrado = r
        return {**r, "ya_registrado": False}

    @app.get("/records")
    def listar(planeta: str = None, nivel: str = None, tamano: str = None, semilla: str = None, vehiculo: str = None,
               origen: str = None, resultado: str = None):
        if origen not in (None, "") and origen not in records.ORIGENES:
            raise ErrorApi(400, f"origen inválido: usa {', '.join(records.ORIGENES)}")
        return records.consultar({"planeta": planeta, "nivel": nivel, "tamano": tamano, "semilla": semilla,
                                  "vehiculo": vehiculo, "origen": origen, "resultado": resultado})

    @app.delete("/records")
    def borrar_records():
        return {"borrados": records.borrar_todos()}
