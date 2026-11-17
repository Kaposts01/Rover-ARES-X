"""ARX-28b: la traza de divergencias del escenario exigente debe atribuir diferencias a cada técnica (M2).

Dos pruebas: una lee la traza de 20 semillas ya generada (docs/TRAZA_DIVERGENCIAS_exigente.csv, rápida) y otra
recalcula la semilla 4 en vivo (en ella divergen las tres técnicas) para que el CSV no pueda quedar desfasado del código.
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
MIN_SEMILLAS_RNA = 3     # umbral del encargo ARX-28b: la RNA debe divergir en al menos 3 de las 20 semillas


def _semillas_con_divergencia_directa(filas):
    por_tecnica = defaultdict(set)
    for f in filas:
        if f["origen"] == "directa":
            por_tecnica[f["tecnica"]].add(int(f["semilla"]))
    return por_tecnica


def test_traza_20_semillas_tiene_divergencias_de_cada_tecnica():
    with open(CSV, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert {int(x["semilla"]) for x in filas} <= set(range(1, 21))
    por_tecnica = _semillas_con_divergencia_directa(filas)
    for t in TECNICAS:
        assert por_tecnica[t], f"ninguna divergencia atribuible a {t} en las 20 semillas"
    assert len(por_tecnica["RNA"]) >= MIN_SEMILLAS_RNA, f"la RNA diverge solo en {sorted(por_tecnica['RNA'])}"
    # la RNA se atribuye por su código de veto; el difuso por sus reglas; el AG por el orden/ruta
    assert any(x["motivo"].startswith("V-RNA-") for x in filas if x["tecnica"] == "RNA" and x["origen"] == "directa")
    assert any(x["motivo"].startswith("regla difusa: R") for x in filas if x["tecnica"] == "difuso" and x["origen"] == "directa")
    assert any(x["cambio"] != "otros_motivos" for x in filas if x["tecnica"] == "AG" and x["origen"] == "directa")


def test_traza_en_vivo_semilla_4_diverge_en_las_tres_tecnicas():
    filas = comparacion.trazar_divergencias([4], "exigente")
    por_tecnica = _semillas_con_divergencia_directa(filas)
    for t in TECNICAS:
        assert por_tecnica[t] == {4}, f"sin divergencia directa de {t} en la semilla 4"
