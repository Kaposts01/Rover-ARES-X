"""Genera docs/COMPARACION_POLITICAS.json: híbrido, sin RNA, sin difuso, sin AG (orden voraz) y la línea base ruta_corta (RF-14, RF-15, ARX-45). ag_puro se calcula pero no se publica (ev3-d71).

Uso (desde ares_x/):  python scripts/comparacion_politicas.py [n_semillas] [escenario]
Tarda varios minutos (6 variantes x n semillas). El endpoint GET /comparacion sirve este archivo para 20 semillas.
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.comparacion import comparar  # noqa: E402

# Publicación (ev3-d71): ag_puro no se publica porque no mide el AG (el envoltorio de Partida elige la permutación más
# corta; se redefine en ARX-92). ruta_corta se publica con su rótulo real: voraz, vecino más cercano.
NO_PUBLICAR = ("ag_puro", "sin_ag_mas_corta")   # ARX-92d: hasta la regeneración definitiva
NOTA_RUTA_CORTA = (" ruta_corta es ruta corta voraz (vecino más cercano), no la ruta óptima; ag_puro no se publica "
                   "hasta ARX-92 (el envoltorio de Partida elige la permutación más corta).")


def para_publicar(datos):
    """Quita las variantes que no se publican y rotula ruta_corta en la nota. No recalcula ninguna cifra."""
    variantes = {v: r for v, r in datos["variantes"].items() if v not in NO_PUBLICAR}
    filas = [f for f in datos["filas"] if f["variante"] not in NO_PUBLICAR]
    return {**datos, "variantes": variantes, "filas": filas, "nota": datos["nota"] + NOTA_RUTA_CORTA}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    escenario = sys.argv[2] if len(sys.argv) > 2 else "congelado"
    datos = para_publicar(comparar(range(1, n + 1), escenario))
    nombre = "COMPARACION_POLITICAS.json" if escenario == "congelado" else f"COMPARACION_POLITICAS_{escenario}.json"
    salida = os.path.join(RAIZ, "docs", nombre)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    for v, r in datos["variantes"].items():
        print(f"{v:12s} exito {r['exitos']}/{r['n']}  pasos mediana {r['pasos']['mediana']}  colisiones media {r['colisiones']['media']}")
    print("escrito", salida)


if __name__ == "__main__":
    main()
