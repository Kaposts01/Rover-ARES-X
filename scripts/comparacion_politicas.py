"""Genera docs/COMPARACION_POLITICAS.json: híbrido frente a sin RNA, sin difuso y sin AG (RF-14, RF-15).

Uso (desde ares_x/):  python scripts/comparacion_politicas.py [n_semillas]
Tarda varios minutos (4 variantes x n semillas). El endpoint GET /comparacion sirve este archivo para 20 semillas.
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.comparacion import comparar  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    datos = comparar(range(1, n + 1))
    salida = os.path.join(RAIZ, "docs", "COMPARACION_POLITICAS.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    for v, r in datos["variantes"].items():
        print(f"{v:11s} exito {r['exitos']}/{r['n']}  pasos mediana {r['pasos']['mediana']}  colisiones media {r['colisiones']['media']}")
    print("escrito", salida)


if __name__ == "__main__":
    main()
