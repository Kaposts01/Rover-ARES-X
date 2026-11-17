"""Genera docs/COMPARACION_POLITICAS.json: híbrido, sin RNA, sin difuso, sin AG y las líneas base ruta_corta y ag_puro (RF-14, RF-15, ARX-45).

Uso (desde ares_x/):  python scripts/comparacion_politicas.py [n_semillas] [escenario]
Tarda varios minutos (6 variantes x n semillas). El endpoint GET /comparacion sirve este archivo para 20 semillas.
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.comparacion import comparar  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    escenario = sys.argv[2] if len(sys.argv) > 2 else "congelado"
    datos = comparar(range(1, n + 1), escenario)
    nombre = "COMPARACION_POLITICAS.json" if escenario == "congelado" else f"COMPARACION_POLITICAS_{escenario}.json"
    salida = os.path.join(RAIZ, "docs", nombre)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    for v, r in datos["variantes"].items():
        print(f"{v:12s} exito {r['exitos']}/{r['n']}  pasos mediana {r['pasos']['mediana']}  colisiones media {r['colisiones']['media']}")
    print("escrito", salida)


if __name__ == "__main__":
    main()
