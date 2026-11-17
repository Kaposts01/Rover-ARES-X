"""ARX-28c: resbalón por velocidad en pendiente (D-RESBALON), solo en el escenario exigente (ev3-d54 A)."""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from juego import comparacion, partida  # noqa: E402
from juego.partida import Partida  # noqa: E402

# Hash de comparar(range(1, 4)) del congelado medido en la base 3a6c5a9, antes de tocar el código.
HASH_CONGELADO_BASE = "d6fb907994a30420652391e32b514bf5a4bb31c05f0d15f2f5aea9d1657cdfef"
# Hash de la nota de texto de la salida (la misma de la base; el hash anterior ya la cubría dentro del total, B2 de QA).
HASH_NOTA_BASE = "f0696978dedf462892e6348ae4fac3c215c8a19c1dc0d2ec4184b34d31f863d8"


def _motivos(p):
    return ";".join(str(x) for x in p.bitacora()["motivos"]) if len(p.mision.log.filas) else ""


def _correr(escenario, velocidad, pasos=50, semilla=1):
    p = comparacion.partida_variante(semilla, "hibrido", escenario)
    p.mision.intervencion_difuso = velocidad
    for _ in range(pasos):
        if p.estado in comparacion.ESTADOS_TERMINALES:
            break
        p.avanzar_ia()
    return p


def test_bandera_apagada_por_defecto_y_en_congelado():
    assert Partida(semilla=1).fisica_velocidad is False
    assert comparacion.partida_variante(1, "hibrido", "congelado").fisica_velocidad is False
    assert comparacion.partida_variante(1, "hibrido", "exigente").fisica_velocidad is True


def test_resbalon_a_velocidad_alta():
    p = _correr("exigente", 1.0)
    assert "D-RESBALON" in _motivos(p)
    assert p.resbalones >= 1


def test_sin_resbalon_a_velocidad_baja():
    p = _correr("exigente", 0.2)
    assert "D-RESBALON" not in _motivos(p)
    assert p.resbalones == 0


def test_resbalon_vuelve_a_la_celda_anterior_y_gasta_bateria():
    p = comparacion.partida_variante(1, "hibrido", "exigente")
    p.mision.intervencion_difuso = 1.0
    for _ in range(60):
        antes, bat = p.rover.posicion, p.rover.bateria
        n = p.resbalones
        p.avanzar_ia()
        if p.resbalones > n:
            assert p.rover.posicion == antes
            assert p.rover.bateria <= bat - partida.COSTO_RESBALON + 1e-9
            assert "D-RESBALON" in p.mision.log.filas[-1]["motivos"]
            return
    raise AssertionError("no hubo resbalón en 60 pasos")


def test_congelado_sin_resbalon_aunque_vaya_rapido():
    p = _correr("congelado", 1.0)
    assert "D-RESBALON" not in _motivos(p)


def test_congelado_no_cambia():
    d = comparacion.comparar(range(1, 4))
    h = hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()
    assert h == HASH_CONGELADO_BASE
    assert hashlib.sha256(d["nota"].encode("utf-8")).hexdigest() == HASH_NOTA_BASE
