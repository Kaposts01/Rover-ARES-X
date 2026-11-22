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


# ARX-94f: semilla 5 (con el mundo v2 la ruta de la 1 no pisa ninguna pendiente > 20°; la 5 sí, y despacio no resbala)
def _correr(escenario, velocidad, pasos=50, semilla=5):
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
    p = comparacion.partida_variante(5, "hibrido", "exigente")   # ARX-94f: semilla 5, ver _correr
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


# ARX-92d: el hash cubre el diccionario completo de comparar(), con las variantes nuevas (sin_ag_mas_corta) quitadas
# y el renombre sin_ag_vecino → sin_ag deshecho. Así las cifras publicadas (y la nota) son las mismas que dieron d6fb9079…
_VARIANTES_NUEVAS = {"sin_ag_mas_corta", "sin_ag_2opt"}


def _hash_congelado(d):
    base = json.loads(json.dumps(d, default=str))
    base["variantes"] = {k: v for k, v in base["variantes"].items() if k not in _VARIANTES_NUEVAS}
    base["filas"] = [f for f in base["filas"] if f["variante"] not in _VARIANTES_NUEVAS]
    for f in base["filas"]:
        if f["variante"] == "sin_ag_vecino":
            f["variante"] = "sin_ag"
    base["variantes"] = {("sin_ag" if k == "sin_ag_vecino" else k): v for k, v in base["variantes"].items()}
    return hashlib.sha256(json.dumps(base, sort_keys=True, default=str).encode()).hexdigest()


def test_congelado_no_cambia():
    d = comparacion.comparar(range(1, 4))
    h = _hash_congelado(d)
    assert h == HASH_CONGELADO_BASE
    assert hashlib.sha256(d["nota"].encode("utf-8")).hexdigest() == HASH_NOTA_BASE


def test_una_cifra_cambiada_rompe_el_hash_congelado():
    d = comparacion.comparar(range(1, 2))
    cambiada = json.loads(json.dumps(d, default=str))
    fila = next(f for f in cambiada["filas"] if f["variante"] == "hibrido")
    fila["pasos"] = fila["pasos"] + 1
    assert _hash_congelado(cambiada) != _hash_congelado(d)
