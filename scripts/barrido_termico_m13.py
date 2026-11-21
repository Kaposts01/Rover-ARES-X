"""M13: barrido térmico de Mercurio (de día) y Venus, 20 semillas por nivel, tamaño grande (40×60).

La bandera termico.ABORTO_TERMICO_ACTIVO se enciende SOLO dentro de este script (atributo del módulo) y se restaura al
terminar. Criterio en docs/planes/M13_barrido_termico.md.

Uso (desde la raíz del repositorio; es medición pesada, con turno):  python scripts/barrido_termico_m13.py SALIDA.json
"""
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from integracion import ESTADOS_TERMINALES  # noqa: E402
from juego import termico  # noqa: E402
from juego.partida import Partida  # noqa: E402

PLANETAS = ("Mercurio", "Venus")
FILAS, COLUMNAS = 40, 60
MAX_PASOS = 500


def jugar(semilla, nivel, planeta, bandera):
    termico.ABORTO_TERMICO_ACTIVO = bandera
    try:
        p = Partida(semilla=semilla, nivel=nivel, filas=FILAS, columnas=COLUMNAS, planeta=planeta)
        tmax = p.t_int
        aborto_paso = None
        pasos = 0
        while pasos < MAX_PASOS and p.estado not in ESTADOS_TERMINALES:
            p.avanzar_ia()
            pasos += 1
            tmax = max(tmax, p.t_int)
            if aborto_paso is None and p.estado == "MODO_SEGURO":
                aborto_paso = int(p.mision.paso)
        return {"estado": p.estado, "pasos": pasos, "tmax": round(float(tmax), 1), "aborto_paso": aborto_paso}
    finally:
        termico.ABORTO_TERMICO_ACTIVO = False


def main():
    salida = sys.argv[1]
    t0 = time.perf_counter()
    filas = []
    try:
        for planeta in PLANETAS:
            for nivel in range(1, 6):
                for s in range(1, 21):
                    off = jugar(s, nivel, planeta, False)
                    fila = {"planeta": planeta, "nivel": nivel, "semilla": s, "apagada": off}
                    if off["estado"] == "EXITO":
                        fila["encendida"] = jugar(s, nivel, planeta, True)
                    filas.append(fila)
                print(planeta, "nivel", nivel, "listo", round(time.perf_counter() - t0), "s", flush=True)
    finally:
        termico.ABORTO_TERMICO_ACTIVO = False
    resumen = {}
    for planeta in PLANETAS:
        for nivel in range(1, 6):
            g = [f for f in filas if f["planeta"] == planeta and f["nivel"] == nivel]
            hoy = [f for f in g if f["apagada"]["estado"] == "EXITO"]
            abortos = [f for f in hoy if f.get("encendida", {}).get("estado") == "MODO_SEGURO"]
            siguen = [f for f in hoy if f.get("encendida", {}).get("estado") == "EXITO"]
            otros = [f for f in hoy if f.get("encendida", {}).get("estado") not in ("EXITO", "MODO_SEGURO")]
            tmax = [f["encendida"]["tmax"] for f in hoy if "encendida" in f]
            pasos_aborto = [f["encendida"]["aborto_paso"] for f in abortos]
            resumen[f"{planeta}-{nivel}"] = {
                "se_gana_hoy": len(hoy), "de": len(g),
                "abortadas": len(abortos), "siguen_ganando": len(siguen), "otro_estado_encendida": len(otros),
                "paso_medio_aborto": round(sum(pasos_aborto) / len(pasos_aborto), 1) if pasos_aborto else None,
                "tmax_media": round(sum(tmax) / len(tmax), 1) if tmax else None,
                "tmax_maxima": max(tmax) if tmax else None,
            }
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"filas": filas, "resumen": resumen, "segundos": round(time.perf_counter() - t0)}, f,
                  ensure_ascii=False, indent=1)
    for k, v in resumen.items():
        print(k, v, flush=True)
    print("escrito", os.path.basename(salida), flush=True)


if __name__ == "__main__":
    main()
