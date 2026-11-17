"""Rejilla de sensibilidad del resbalón (ARX-28c, ev3-d69 A; M20): P_RESBALON x COSTO_RESBALON.

Escenario exigente, 20 semillas, 4 variantes (hibrido, sin_rna, sin_difuso, sin_ag); 6 celdas, 480 partidas.
Vuelca TODAS las celdas, sin filtrar (también donde la ventaja del difuso sea menor, nula o negativa).
No modifica el repositorio salvo los dos archivos de salida; cambia las constantes solo en memoria.

Uso (desde la raíz del repositorio; es una corrida pesada, con turno):
    python scripts/rejilla_resbalon.py [--salida docs]
Salida: docs/REJILLA_RESBALON_exigente.json y docs/REJILLA_RESBALON_exigente.csv
"""
import csv
import json
import sys
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
salida = Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else raiz / "docs"
sys.path.insert(0, str(raiz))

from juego import comparacion, partida  # noqa: E402

PROBS, COSTOS, SEMILLAS = (0.25, 0.5, 0.75), (1.0, 2.0), list(range(1, 21))
VARS = ("hibrido", "sin_rna", "sin_difuso", "sin_ag")
orig = (partida.P_RESBALON, partida.COSTO_RESBALON)
celdas = []
try:
    for p in PROBS:
        for c in COSTOS:
            partida.P_RESBALON, partida.COSTO_RESBALON = p, c
            filas = [comparacion.correr(s, v, "exigente") for v in VARS for s in SEMILLAS]
            cel = {"P_RESBALON": p, "COSTO_RESBALON": c, "variantes": {}}
            for v in VARS:
                g = [f for f in filas if f["variante"] == v]
                n = len(g)
                cel["variantes"][v] = {"exitos": sum(f["exito"] for f in g), "n": n,
                                       "colisiones_media": round(sum(f["colisiones"] for f in g) / n, 3),
                                       "bateria_media": round(sum(f["bateria_final"] for f in g) / n, 2),
                                       "pasos_media": round(sum(f["pasos"] for f in g) / n, 2)}
            h, d = cel["variantes"]["hibrido"], cel["variantes"]["sin_difuso"]
            cel["ventaja_difuso_exitos"] = h["exitos"] - d["exitos"]       # puede ser <= 0: se publica igual
            cel["ventaja_difuso_bateria"] = round(h["bateria_media"] - d["bateria_media"], 2)
            celdas.append(cel)
            print(p, c, "hibrido", h["exitos"], "sin_difuso", d["exitos"], flush=True)
finally:
    partida.P_RESBALON, partida.COSTO_RESBALON = orig

salida.mkdir(parents=True, exist_ok=True)
(salida / "REJILLA_RESBALON_exigente.json").write_text(json.dumps(celdas, ensure_ascii=False, indent=1), encoding="utf-8")
with open(salida / "REJILLA_RESBALON_exigente.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["P_RESBALON", "COSTO_RESBALON", "variante", "exitos", "n", "colisiones_media", "bateria_media", "pasos_media",
                "ventaja_difuso_exitos", "ventaja_difuso_bateria"])
    for cel in celdas:
        for v in VARS:
            r = cel["variantes"][v]
            w.writerow([cel["P_RESBALON"], cel["COSTO_RESBALON"], v, r["exitos"], r["n"], r["colisiones_media"],
                        r["bateria_media"], r["pasos_media"], cel["ventaja_difuso_exitos"], cel["ventaja_difuso_bateria"]])
print("celdas volcadas:", len(celdas), "->", salida)
