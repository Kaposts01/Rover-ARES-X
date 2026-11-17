"""El medidor de tiempos corre en pocos pasos y devuelve las tres estadísticas (ARX-44)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from medir_tiempos import medir_pasos, resumen  # noqa: E402


def test_resumen_calcula_media_mediana_maximo():
    r = resumen([0.001, 0.002, 0.006])
    assert r["n"] == 3
    assert abs(r["media_ms"] - 3.0) < 1e-9 and abs(r["mediana_ms"] - 2.0) < 1e-9 and abs(r["maximo_ms"] - 6.0) < 1e-9


def test_medir_pasos_corre_en_pocos_pasos():
    r = medir_pasos([1], modos=("automatico", "rna"), max_pasos=3)
    assert set(r) == {"automatico", "rna"}
    assert 1 <= r["rna"]["n"] <= 3 and r["rna"]["maximo_ms"] >= r["rna"]["mediana_ms"] > 0
