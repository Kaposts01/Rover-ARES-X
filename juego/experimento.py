"""ARES-X · Experimento de ablación: híbrido, sin RNA y sin difuso sobre las mismas semillas.

Usa Mision directamente de integracion.py (sin UI). Reproduce la tabla de resumen del notebook.
Contrato: juego/CONTRATO.md.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from integracion import Mision  # noqa: E402
from simulador import generar_mundo  # noqa: E402

VARIANTES = {
    "híbrido": {},
    "sin RNA": {"usar_rna": False},
    "sin difuso": {"usar_difuso": False},
}
N_OBSTACULOS = 20
N_BARRANCOS = 4
N_SITIOS = 3
MAX_PASOS = 400


def comparar_variantes(semillas=range(20)) -> pd.DataFrame:
    """Corre híbrido, sin RNA y sin difuso con las mismas semillas (Mision directo, sin UI).

    Devuelve la tabla de resumen del notebook indexada por variante, con columnas:
    exito_pct, colisiones, barrancos_pisados, sitios_media, pasos_mediana, pasos_desv, bateria_media.
    """
    filas = []
    for nombre, opciones in VARIANTES.items():
        for s in semillas:
            mundo = generar_mundo(semilla=s, n_obstaculos=N_OBSTACULOS,
                                  n_barrancos=N_BARRANCOS, n_sitios=N_SITIOS)
            mision = Mision(mundo, semilla=s, **opciones)
            r = mision.ejecutar(max_pasos=MAX_PASOS)
            filas.append({"variante": nombre, "semilla": s, **r})

    tabla = pd.DataFrame(filas)
    tabla["exito"] = tabla["estado"].eq("EXITO").astype(int)
    resumen = tabla.groupby("variante").agg(
        exito_pct=("exito", lambda x: round(100 * x.mean(), 1)),
        colisiones=("colisiones", "sum"),
        barrancos_pisados=("barrancos_pisados", "sum"),
        sitios_media=("sitios_visitados", "mean"),
        pasos_mediana=("pasos", "median"),
        pasos_desv=("pasos", "std"),
        bateria_media=("bateria_final", "mean"),
    )
    return resumen.round(2)


if __name__ == "__main__":
    print(comparar_variantes())
