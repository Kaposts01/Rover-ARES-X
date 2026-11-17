"""Genera docs/TRAZA_DIVERGENCIAS_<escenario>.csv: divergencias paso a paso del híbrido frente a sin_rna, sin_difuso, sin_ag_vecino y sin_ag_mas_corta.

Uso (desde ares_x/):  python scripts/traza_divergencias.py [n_semillas] [escenario]
"""
import csv
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.comparacion import trazar_divergencias  # noqa: E402

CAMPOS = ["semilla", "variante", "tecnica", "paso", "celda", "origen", "motivo", "cambio", "detalle"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    escenario = sys.argv[2] if len(sys.argv) > 2 else "exigente"
    filas = trazar_divergencias(range(1, n + 1), escenario)
    salida = os.path.join(RAIZ, "docs", f"TRAZA_DIVERGENCIAS_{escenario}.csv")
    with open(salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    print("escrito", salida, len(filas), "filas")


if __name__ == "__main__":
    main()
