"""Prueba causal (ARX-10, ev3-d32 A): forzar la salida de la RNA o del difuso y medir qué cambia.

Por cada semilla se corre una misión base (sin intervención) y una misión por variante, con la
misma semilla. Hasta el primer paso con intervención, las dos misiones son idénticas, así que el
primer paso con decisión distinta mide el efecto causal de la intervención.

Variantes:
- rna_barranco: la RNA devuelve probabilidad 0,95 de barranco.
- rna_libre: la RNA devuelve probabilidad 0,95 de libre.
- difuso_min: el difuso devuelve velocidad 0 (parar).
- difuso_max: el difuso devuelve velocidad 1 (máxima).
"""
import pandas as pd

from integracion import Mision, forzar_probabilidad
from simulador import generar_mundo

SEMILLAS_POR_DEFECTO = range(20)
MAX_PASOS = 400


def opciones_variantes() -> dict:
    return {
        "rna_barranco": {"intervencion_rna": forzar_probabilidad("barranco")},
        "rna_libre": {"intervencion_rna": forzar_probabilidad("libre")},
        "difuso_min": {"intervencion_difuso": 0.0},
        "difuso_max": {"intervencion_difuso": 1.0},
    }


def _mision(semilla: int, **opciones) -> Mision:
    mundo = generar_mundo(semilla=semilla, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    return Mision(mundo, semilla=semilla, **opciones)


def _primer_cambio(log_base: pd.DataFrame, log_var: pd.DataFrame):
    """Primer paso donde difieren la acción o la velocidad; None si nunca difieren."""
    n = min(len(log_base), len(log_var))
    for i in range(n):
        a, b = log_base.iloc[i], log_var.iloc[i]
        if a["accion"] != b["accion"] or a["velocidad"] != b["velocidad"]:
            return i + 1
    if len(log_base) != len(log_var):
        return n + 1
    return None


def correr_semilla(semilla: int, variante: str, opciones: dict) -> dict:
    """Corre base y variante con la misma semilla y devuelve el efecto medido."""
    base = _mision(semilla)
    res_base = base.ejecutar(max_pasos=MAX_PASOS)
    var = _mision(semilla, **opciones)
    res_var = var.ejecutar(max_pasos=MAX_PASOS)
    cambio = _primer_cambio(base.log.a_dataframe(), var.log.a_dataframe())
    return {
        "variante": variante, "semilla": semilla,
        "estado_base": res_base["estado"], "estado_var": res_var["estado"],
        "exito_base": res_base["estado"] == "EXITO", "exito_var": res_var["estado"] == "EXITO",
        "colisiones": res_var["colisiones"], "barrancos_pisados": res_var["barrancos_pisados"],
        "pasos": res_var["pasos"], "sitios": res_var["sitios_visitados"],
        "paso_primer_cambio": cambio,
    }


def correr(semillas=SEMILLAS_POR_DEFECTO) -> pd.DataFrame:
    """Tabla con una fila por semilla y variante."""
    filas = []
    for nombre, opciones in opciones_variantes().items():
        for s in semillas:
            filas.append(correr_semilla(s, nombre, opciones))
    return pd.DataFrame(filas)


def resumen(tabla: pd.DataFrame) -> pd.DataFrame:
    """Éxito, colisiones, barrancos, pasos, sitios y cambio de decisión por variante."""
    grupos = []
    for nombre, g in tabla.groupby("variante", sort=False):
        cambiaron = g["paso_primer_cambio"].notna()
        grupos.append({
            "variante": nombre,
            "exito_pct": round(100 * g["exito_var"].mean(), 1),
            "colisiones": int(g["colisiones"].sum()),
            "barrancos_pisados": int(g["barrancos_pisados"].sum()),
            "sitios_media": round(g["sitios"].mean(), 2),
            "pasos_mediana": float(g["pasos"].median()),
            "semillas_con_cambio_de_decision": int(cambiaron.sum()),
            "primer_cambio_mediana": (float(g.loc[cambiaron, "paso_primer_cambio"].median())
                                      if cambiaron.any() else None),
        })
    return pd.DataFrame(grupos).set_index("variante")


if __name__ == "__main__":
    tabla = correr()
    print(resumen(tabla).to_string())
