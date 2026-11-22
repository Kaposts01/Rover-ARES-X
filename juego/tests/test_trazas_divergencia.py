"""ARX-28b: la traza de divergencias del escenario exigente debe atribuir diferencias a cada técnica (M2).

Dos pruebas: una lee la traza de 20 semillas ya generada (docs/TRAZA_DIVERGENCIAS_exigente.csv, rápida) y otra
recalcula una semilla en vivo (la 1 con el mundo v2; era la 4 con MUNDO_V1) en la que divergen las tres técnicas para que el CSV no pueda quedar desfasado del código.
"""
import csv
import os
import sys
from collections import defaultdict

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from juego import comparacion  # noqa: E402

CSV = os.path.join(RAIZ, "docs", "TRAZA_DIVERGENCIAS_exigente.csv")
TECNICAS = ("RNA", "difuso", "AG")
MIN_SEMILLAS_POR_TECNICA = 1   # criterio del Maestro (QA B2): al menos 1 semilla con divergencia real por técnica


def _semillas_con_divergencia_directa(filas):
    """Divergencia real = directa que altera decisión, velocidad o ruta; cambiar solo el código de motivo no cuenta."""
    por_tecnica = defaultdict(set)
    for f in filas:
        if f["origen"] == "directa" and f["cambio"] != "otros_motivos":
            por_tecnica[f["tecnica"]].add(int(f["semilla"]))
    return por_tecnica


def test_traza_20_semillas_tiene_divergencias_de_cada_tecnica():
    with open(CSV, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert {int(x["semilla"]) for x in filas} <= set(range(1, 21))
    por_tecnica = _semillas_con_divergencia_directa(filas)
    for t in TECNICAS:
        assert len(por_tecnica[t]) >= MIN_SEMILLAS_POR_TECNICA, (
            f"{t}: ninguna semilla con divergencia real (decisión, velocidad o ruta) en las 20 semillas")
    # la RNA se atribuye por su código de veto; el difuso por sus reglas; el AG por el orden/ruta
    assert any(x["motivo"].startswith("V-RNA-") for x in filas if x["tecnica"] == "RNA" and x["origen"] == "directa")
    assert any(x["motivo"].startswith("regla difusa: R") for x in filas if x["tecnica"] == "difuso" and x["origen"] == "directa")
    assert any(x["cambio"] != "otros_motivos" for x in filas if x["tecnica"] == "AG" and x["origen"] == "directa")


def test_traza_en_vivo_semilla_1_diverge_en_las_tres_tecnicas():
    # ARX-94f: con el mundo v2 la semilla 1 es la que hace divergir las tres técnicas (la 4 lo hacía con MUNDO_V1)
    filas = comparacion.trazar_divergencias([1], "exigente")
    por_tecnica = _semillas_con_divergencia_directa(filas)
    for t in TECNICAS:
        assert por_tecnica[t] == {1}, f"sin divergencia directa de {t} en la semilla 1"
