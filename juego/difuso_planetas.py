"""R23: parámetros del difuso y de la conducción por planeta, evolucionados fuera de línea por un AG.

El AG (scripts/evolucionar_difuso.py, semilla fija) busca, para cada planeta, un vector de `GENES` que maximiza un fitness medido
simulando partidas jugables en ese planeta (juego/planetas.py: gravedad, viento, hielo). El resultado se guarda en
`juego/difuso_planetas.json` (versionado) y la partida lo carga si existe el planeta. El difuso por defecto (sin evolucionar)
sigue disponible: `Partida(..., difuso_evolucionado=False)` o la variante `difuso_base` de la comparación.

Un vector tiene tres partes:
- puntos de las funciones de pertenencia (distancia cerca/lejos, inclinación plana/fuerte, batería crítica/alta y salida);
- peso de cada regla (R1 a R11): la fuerza de la regla se multiplica por el peso;
- umbrales de conducción: tope de velocidad sobre hielo, con viento y en pendiente fuerte; factor de desvío y umbral de batería
  para ir a una base. Con 1,0 el tope no actúa (así es el difuso sin evolucionar).
Todos los rangos son supuestos de simulación.
"""
import json
import os

import numpy as np

from difuso import REGLAS

RUTA_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difuso_planetas.json")
IDS_REGLAS = [r["id"] for r in REGLAS]

# (nombre, mínimo, máximo, valor por defecto). Los «_gap» son anchuras: el segundo punto = primero + gap (orden garantizado).
GENES = [
    ("dist_cerca_c", 1.5, 5.0, 3.0), ("dist_cerca_gap", 1.0, 5.0, 3.0),
    ("dist_lejos_a", 8.0, 15.0, 12.0), ("dist_lejos_gap", 2.0, 6.0, 5.0),
    ("incl_plana_c", 2.0, 10.0, 5.0), ("incl_plana_gap", 3.0, 10.0, 7.0),
    ("incl_fuerte_a", 14.0, 30.0, 24.0), ("incl_fuerte_gap", 2.0, 10.0, 8.0),
    ("bat_critica_c", 8.0, 30.0, 15.0), ("bat_critica_gap", 8.0, 25.0, 15.0),
    ("bat_alta_a", 35.0, 65.0, 50.0), ("bat_alta_gap", 10.0, 35.0, 20.0),
    ("sal_rapida_a", 0.45, 0.75, 0.6), ("sal_moderada_c", 0.4, 0.6, 0.5),
] + [(f"peso_{rid}", 0.2, 1.0, 1.0) for rid in IDS_REGLAS] + [
    ("v_hielo", 0.25, 1.0, 1.0), ("v_viento", 0.25, 1.0, 1.0), ("v_pendiente", 0.25, 1.0, 1.0),
    ("factor_desvio", 1.1, 1.8, 1.3), ("umbral_desvio", 0.3, 0.9, 0.6),
]
NOMBRES = [g[0] for g in GENES]
MINIMOS = np.array([g[1] for g in GENES])
MAXIMOS = np.array([g[2] for g in GENES])
DEFECTO = np.array([g[3] for g in GENES])
UMBRAL_VIENTO = 0.35          # el tope de velocidad por viento actúa con viento (ya por la intensidad) de este valor o más
UMBRAL_PENDIENTE_GRADOS = 12.0


def recortar(v) -> np.ndarray:
    return np.clip(np.asarray(v, dtype=float), MINIMOS, MAXIMOS)


def a_parametros(vector) -> dict:
    """Vector de genes → {"difuso": params para FuzzyController, "conduccion": umbrales}."""
    g = dict(zip(NOMBRES, recortar(vector)))
    r = lambda x: round(float(x), 4)
    variables = {
        "distancia": {"etiquetas": {
            "cerca": [0, 0, r(g["dist_cerca_c"]), r(g["dist_cerca_c"] + g["dist_cerca_gap"])],
            "lejos": [r(g["dist_lejos_a"]), r(min(19.5, g["dist_lejos_a"] + g["dist_lejos_gap"])), 20, 20]}},
        "inclinacion": {"etiquetas": {
            "plana": [0, 0, r(g["incl_plana_c"]), r(g["incl_plana_c"] + g["incl_plana_gap"])],
            "fuerte": [r(g["incl_fuerte_a"]), r(g["incl_fuerte_a"] + g["incl_fuerte_gap"]), 45, 45]}},
        "bateria": {"etiquetas": {
            "critica": [0, 0, r(g["bat_critica_c"]), r(g["bat_critica_c"] + g["bat_critica_gap"])],
            "alta": [r(g["bat_alta_a"]), r(min(99.0, g["bat_alta_a"] + g["bat_alta_gap"])), 100, 100]}},
    }
    salida = {"etiquetas": {"rapida": [r(g["sal_rapida_a"]), r(min(0.95, g["sal_rapida_a"] + 0.2)), 1.0, 1.0],
                            "moderada": [r(g["sal_moderada_c"] - 0.15), r(g["sal_moderada_c"]), r(g["sal_moderada_c"] + 0.15)]}}
    reglas = [{"id": rid, "peso": r(g[f"peso_{rid}"])} for rid in IDS_REGLAS]
    conduccion = {k: r(g[k]) for k in ("v_hielo", "v_viento", "v_pendiente", "factor_desvio", "umbral_desvio")}
    return {"difuso": {"variables": variables, "salida": salida, "reglas": reglas}, "conduccion": conduccion}


def por_defecto() -> dict:
    return a_parametros(DEFECTO)


_cache = {}


def cargar_todo(ruta: str = None) -> dict:
    ruta = ruta or RUTA_JSON
    if ruta not in _cache:
        try:
            with open(ruta, encoding="utf-8") as f:
                _cache[ruta] = json.load(f)
        except (OSError, ValueError):
            _cache[ruta] = {"planetas": {}}
    return _cache[ruta]


def cargar(planeta: str, ruta: str = None):
    """Ajustes evolucionados del planeta ({"difuso", "conduccion", ...}) o None si el planeta no tiene."""
    return (cargar_todo(ruta).get("planetas") or {}).get(planeta)


def guardar(datos: dict, ruta: str = None) -> None:
    ruta = ruta or RUTA_JSON
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1, sort_keys=False)
    _cache.pop(ruta, None)
