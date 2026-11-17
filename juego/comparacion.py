"""Comparación de políticas (RF-14, RF-15, CA-08): híbrido frente a sin RNA, sin difuso y sin AG.

Mismas semillas para todas las variantes. Cada variante es una partida de la capa de juego con una sola técnica
desactivada (o el AG reemplazado):
- hibrido:    el controlador completo (avanzar_ia).
- sin_rna:    la RNA no interviene (probabilidades neutras); el supervisor sigue activo.
- sin_difuso: velocidad fija de 0,5, sin controlador difuso.
- sin_ag:     el orden de visita de los sitios se elige por vecino más cercano, en vez del AG; la ruta sigue siendo BFS.

Métricas por variante: éxito, pasos, colisiones y energía final; media, mediana, desviación típica y rango
intercuartílico (dispersión). La comparación no atribuye causalidad fuera de estas condiciones (§14).
"""
import numpy as np

from genetico import camino_bfs, mapa_estimado
from integracion import ESTADOS_TERMINALES, Mision

VARIANTES = ("hibrido", "sin_rna", "sin_difuso", "sin_ag")
MAX_PASOS = 400

# Escenarios de evaluación (ARX-28b). "congelado" es la evaluación del informe: 20x30, nivel 1, parámetros por defecto.
# "exigente": nivel 5 con sensor más ruidoso y detección de peligros más pobre. ruido y p_detectar los fijó ARX-28a
# (calibración; ver docs/planes/ARX-28_calibracion.md). Si alguno fuera None el escenario no se podría usar.
ESCENARIOS = {
    "congelado": {"nivel": 1, "ruido": None, "p_detectar": None, "prob_fallo": None},      # None = no se toca: valores por defecto de Mision
    # prob_fallo (ev3-d60 A): probabilidad de lectura NaN del sensor de proximidad, solo en este escenario. None = sin fallo
    # (comportamiento de 11dae05). La rellena la calibración (medición pedida por el Orquestador); no tiene valor aún.
    "exigente": {"nivel": 5, "ruido": 0.6, "p_detectar": 0.4, "prob_fallo": None},         # calibrado en ARX-28a (docs/planes/ARX-28_calibracion.md)
}


def _orden_voraz(m: Mision):
    """Reemplazo del AG: visita los sitios pendientes por vecino más cercano y une los tramos con BFS."""
    def planear(origen, pendientes):
        transitable = m.riesgo < 0.5
        pts = list(pendientes)
        ruta, cur = [origen], origen
        while pts:
            nxt = min(pts, key=lambda c: max(abs(c[0] - cur[0]), abs(c[1] - cur[1])))
            tramo = camino_bfs(cur, nxt, transitable)
            if tramo is None:
                return []
            ruta.extend(tramo[1:])
            cur = nxt
            pts.remove(nxt)
        tramo = camino_bfs(cur, m.mundo.refugio, transitable)
        if tramo is None:
            return []
        ruta.extend(tramo[1:])
        return ruta
    return planear


def _parametros_escenario(escenario: str) -> dict:
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario desconocido: {escenario!r}")
    par = ESCENARIOS[escenario]
    if escenario != "congelado" and (par["ruido"] is None or par["p_detectar"] is None):
        raise ValueError(f"escenario {escenario} pendiente de ARX-28a (ruido y p_detectar sin fijar)")
    return par


def partida_variante(semilla: int, variante: str, escenario: str = "congelado"):
    """Partida de la capa de juego con el escenario y, después, la variante aplicados antes de empezar."""
    from juego.partida import Partida
    if variante not in VARIANTES:
        raise ValueError(f"variante desconocida: {variante!r}")
    par = _parametros_escenario(escenario)
    from juego.partida import FILAS_BASE, COLUMNAS_BASE
    p = Partida(semilla=semilla, nivel=par["nivel"], filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)   # 20x30, sin redibujar el mapa
    m = p.mision
    if par["ruido"] is not None or par["p_detectar"] is not None or par.get("prob_fallo") is not None:
        # El escenario se aplica sobre la instancia y se replanifica con el mapa estimado nuevo
        if par["ruido"] is not None:
            m.sensor.ruido = par["ruido"]
        if par.get("prob_fallo") is not None:
            m.sensor.prob_fallo = par["prob_fallo"]
        if par["p_detectar"] is not None:
            m.riesgo = mapa_estimado(m.mundo, m.rng, p_detectar=par["p_detectar"])
        m.objetivos = []
        m._planear()
    if variante == "sin_rna":
        m.usar_rna = False
    elif variante == "sin_difuso":
        m.usar_difuso = False
    elif variante == "sin_ag":
        # Partida() ya planificó con el AG al construirse: se sustituye el optimizador y se replanifica
        m._optimizar_ag = _orden_voraz(m)
        m.objetivos = []
        m._planear()
    return p


def correr(semilla: int, variante: str, escenario: str = "congelado") -> dict:
    """Una partida completa de una variante con una semilla."""
    p = partida_variante(semilla, variante, escenario)
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    return {"semilla": semilla, "variante": variante, "estado": p.estado, "exito": p.estado == "EXITO",
            "pasos": pasos, "colisiones": int(p.mision.colisiones),
            "bateria_final": round(float(p.rover.bateria), 2),
            "sitios_visitados": len(p.mision.visitados)}


def _resumen(valores) -> dict:
    v = np.asarray(valores, dtype=float)
    q1, q3 = np.percentile(v, [25, 75])
    return {"media": round(float(v.mean()), 3), "mediana": round(float(np.median(v)), 3),
            "desviacion": round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 3),
            "rango_intercuartil": round(float(q3 - q1), 3)}


def comparar(semillas, escenario: str = "congelado") -> dict:
    """Ejecuta todas las variantes con las mismas semillas y resume cada una."""
    _parametros_escenario(escenario)          # falla pronto si el escenario no existe o está pendiente
    semillas = [int(s) for s in semillas]
    filas = [correr(s, v, escenario) for v in VARIANTES for s in semillas]
    politicas = {}
    for v in VARIANTES:
        grupo = [f for f in filas if f["variante"] == v]
        politicas[v] = {
            "exitos": sum(f["exito"] for f in grupo),
            "n": len(grupo),
            "tasa_exito": round(100.0 * sum(f["exito"] for f in grupo) / len(grupo), 1),
            "pasos": _resumen([f["pasos"] for f in grupo]),
            "colisiones": _resumen([f["colisiones"] for f in grupo]),
            "bateria_final": _resumen([f["bateria_final"] for f in grupo]),
            "sitios_visitados": _resumen([f["sitios_visitados"] for f in grupo]),
        }
    return {"escenario": escenario, "semillas": semillas, "variantes": politicas, "filas": filas,
            "nota": "Arnés: capa de juego (juego/partida.py), misma semilla por variante. Sin atribución causal fuera "
                    "de estas condiciones (§14). Los intentos a barranco no se miden en el híbrido."}


# ---------- traza de divergencias por técnica (ARX-28b) ----------
TECNICA = {"sin_rna": "RNA", "sin_difuso": "difuso", "sin_ag": "AG"}


def _filas_por_paso(p) -> dict:
    """Filas de la bitácora agrupadas por paso, como tuplas comparables (posición, acción, velocidad, motivos)."""
    por_paso = {}
    for f in p.mision.log.filas:
        por_paso.setdefault(f["paso"], []).append(f)
    return por_paso


def _correr_traza(semilla: int, variante: str, escenario: str):
    p = partida_variante(semilla, variante, escenario)
    orden = [c for c in p.mision.objetivos if c in p.mundo.sitios]
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    return p, orden


def _firma(filas) -> tuple:
    return tuple((f["posicion"], f["accion"], f["velocidad"], f["motivos"]) for f in filas)


def _motivo_y_cambio(variante, fh, fv):
    """Motivo (en el híbrido, que es quien tiene la técnica) y qué cambió, entre dos filas del mismo paso."""
    mh = ";".join(f["motivos"] for f in fh)
    cambios = []
    if [f["accion"] for f in fh] != [f["accion"] for f in fv]:
        cambios.append("decision")
    if [f["velocidad"] for f in fh] != [f["velocidad"] for f in fv]:
        cambios.append("velocidad")
    if [f["posicion"] for f in fh] != [f["posicion"] for f in fv]:
        cambios.append("ruta")
    if variante == "sin_rna":
        vetos = [m for m in mh.split(";") if m.startswith("V-RNA-")]
        motivo = ";".join(vetos) if vetos else "RNA (probabilidades distintas; motivos: " + (mh or "-") + ")"
    elif variante == "sin_difuso":
        reglas = ";".join(f["reglas"] for f in fh if f["reglas"])
        motivo = "regla difusa: " + (reglas or "-")
    else:
        motivo = "ruta del AG frente a vecino más cercano"
    return motivo, "+".join(cambios) or "otros_motivos"


def trazar_divergencias(semillas, escenario: str = "exigente") -> list:
    """Comparación paso a paso del híbrido contra cada variante con la misma semilla.

    Una fila por paso en que difiere lo registrado (posición, acción, velocidad o motivos). `origen`:
    - "directa": la PRIMERA divergencia de cada (semilla, variante) que altera decisión, velocidad o ruta, con el
      mismo estado previo (misma posición y batería al empezar el paso), por lo que la causa la técnica en ese paso
      (o, en el AG, el orden de sitios del plan);
    - "directa_codigo": divergencia con el mismo estado previo que solo cambia el código de motivo y aparece antes de
      la directa (o si no hay directa); se cuenta aparte y no cuenta como directa;
    - "consecuencia": el resto (toda divergencia posterior a la directa o con estado previo distinto).
    Se omiten los pasos en que una de las dos partidas ya terminó y no tiene fila (artefacto de fin de partida).
    Con sin_ag se añade, en paso 0, la fila de orden de sitios si el plan inicial difiere.
    """
    filas = []
    for s in semillas:
        ph, orden_h = _correr_traza(s, "hibrido", escenario)
        fh = _filas_por_paso(ph)
        for var in ("sin_rna", "sin_difuso", "sin_ag"):
            pv, orden_v = _correr_traza(s, var, escenario)
            fv = _filas_por_paso(pv)
            if var == "sin_ag" and orden_h != orden_v:
                filas.append({"semilla": s, "variante": var, "tecnica": "AG", "paso": 0, "celda": str(ph.mundo.inicio),
                              "origen": "directa", "motivo": "ruta del AG frente a vecino más cercano",
                              "cambio": "ruta", "detalle": f"orden AG {orden_h} / orden voraz {orden_v}"})
            previa_h = previa_v = None
            hubo_directa = bool(filas) and filas[-1]["semilla"] == s and filas[-1]["variante"] == var
            for paso in sorted(set(fh) | set(fv)):
                a, b = fh.get(paso, []), fv.get(paso, [])
                igual_previo = previa_h == previa_v
                if a and b and _firma(a) != _firma(b):
                    motivo, cambio = _motivo_y_cambio(var, a, b)
                    celda = (a or b)[-1]["posicion"]
                    if igual_previo and not hubo_directa:
                        origen = "directa_codigo" if cambio == "otros_motivos" else "directa"
                    else:
                        origen = "consecuencia"
                    filas.append({"semilla": s, "variante": var, "tecnica": TECNICA[var], "paso": paso, "celda": celda,
                                  "origen": origen,
                                  "motivo": motivo,
                                  "cambio": cambio,
                                  "detalle": f"hibrido {_firma(a)} / {var} {_firma(b)}"})
                    hubo_directa = hubo_directa or origen == "directa"
                previa_h = (a[-1]["posicion"], a[-1]["bateria"]) if a else previa_h
                previa_v = (b[-1]["posicion"], b[-1]["bateria"]) if b else previa_v
    return filas
