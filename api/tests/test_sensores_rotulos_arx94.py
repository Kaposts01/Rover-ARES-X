"""ARX-94 (QA O-5): /estado rotula los rasgos 1 y 2 según el modelo activo (v1: borde/gradiente; v2: desnivel/contraste)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

import simulador  # noqa: E402
from api.servidor import Sesion, crear_app  # noqa: E402


def _nombres(v1):
    anterior = simulador.MUNDO_V1
    simulador.MUNDO_V1 = v1
    try:
        cliente = TestClient(crear_app(Sesion(semilla=11)))
        s = cliente.get("/estado").json()["sensores"]
        rna = cliente.get("/rna").json()
    finally:
        simulador.MUNDO_V1 = anterior
    assert s["rasgos_nombres"] == rna["modelo"]["rasgos"]          # sin lista duplicada: coincide con /rna
    assert {"borde", "gradiente"} <= set(s)              # claves anteriores intactas
    return s["rasgos_nombres"]


def test_rotulos_v2():
    n = _nombres(False)
    assert n[0].startswith("proximidad") and n[1].startswith("desnivel") and n[2].startswith("contraste")


def test_rotulos_v1():
    n = _nombres(True)
    assert n[1].startswith("borde") and n[2].startswith("gradiente")
