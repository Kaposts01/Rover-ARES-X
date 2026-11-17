"""ARX-58: mapas ganables por nivel y tamaño (garantía de la semilla pedida, semillas 1..N). Rotulado aparte de las
partidas ganadas (medir_garantia.py). No juega partidas: solo construye el mapa con la garantía activa.

Uso (desde la raíz del repositorio):  python scripts/linea_base_58.py [semillas=20] [salida.json]
"""
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.partida import Partida  # noqa: E402

TAMANOS = {"pequeno": (20, 30), "grande": (40, 60)}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    salida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "docs", "planes", "mediciones", "medicion_58_mapas.json")
    t0 = time.perf_counter()
    filas = []
    for tam, (f, c) in TAMANOS.items():
        for nivel in range(1, 6):
            for s in range(1, n + 1):
                p = Partida(semilla=s, nivel=nivel, filas=f, columnas=c)
                filas.append({"tamano": tam, "nivel": nivel, "semilla": s, "ganable": not p._sin_garantia})
        print("tamano", tam, "listo", round(time.perf_counter() - t0), "s", flush=True)
    resumen = {}
    for tam in TAMANOS:
        for nivel in range(1, 6):
            g = [x for x in filas if x["tamano"] == tam and x["nivel"] == nivel]
            resumen[f"{tam}-{nivel}"] = {"ganables": sum(x["ganable"] for x in g), "n": len(g)}
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"filas": filas, "resumen": resumen, "segundos": round(time.perf_counter() - t0)}, f,
                  ensure_ascii=False, indent=1)
    for k, v in resumen.items():
        print(k, f"mapas ganables {v['ganables']}/{v['n']}", flush=True)
    print("escrito", os.path.basename(salida), flush=True)


if __name__ == "__main__":
    main()
