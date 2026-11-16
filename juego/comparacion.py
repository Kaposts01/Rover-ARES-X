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

from genetico import camino_bfs
from integracion import ESTADOS_TERMINALES, Mision

VARIANTES = ("hibrido", "sin_rna", "sin_difuso", "sin_ag")
MAX_PASOS = 400


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


def partida_variante(semilla: int, variante: str):
    """Partida de la capa de juego con la variante aplicada antes de empezar."""
    from juego.partida import Partida
    if variante not in VARIANTES:
        raise ValueError(f"variante desconocida: {variante!r}")
    from juego.partida import FILAS_BASE, COLUMNAS_BASE
    p = Partida(semilla=semilla, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)   # evaluación congelada: 20x30, sin redibujar el mapa
    m = p.mision
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


def correr(semilla: int, variante: str) -> dict:
    """Una partida completa de una variante con una semilla."""
    p = partida_variante(semilla, variante)
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


def comparar(semillas) -> dict:
    """Ejecuta todas las variantes con las mismas semillas y resume cada una."""
    semillas = [int(s) for s in semillas]
    filas = [correr(s, v) for v in VARIANTES for s in semillas]
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
    return {"semillas": semillas, "variantes": politicas, "filas": filas,
            "nota": "Arnés: capa de juego (juego/partida.py), misma semilla por variante. Sin atribución causal fuera "
                    "de estas condiciones (§14). Los intentos a barranco no se miden en el híbrido."}
