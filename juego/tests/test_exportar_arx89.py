import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "juego"))

import exportar  # noqa: E402
from exportar import exportar_partida  # noqa: E402
from partida import Partida  # noqa: E402


def _leer(partida):
    with tempfile.TemporaryDirectory() as d:
        _, ruta_json = exportar_partida(partida, d)
        return json.loads(Path(ruta_json).read_text(encoding="utf-8"))


def test_version_y_metricas_en_partida_real():
    p = Partida(semilla=11)
    for _ in range(5):
        p.avanzar_ia()
    datos = _leer(p)
    assert datos["version_software"] and datos["version_origen"] in ("git", "constante")
    r = datos["resumen"]
    assert r["energia_restante"] == round(p.rover.bateria, 1)
    assert r["distancia_recorrida"] == p.rover.distancia_recorrida
    assert r["replanes"] == p.mision.replanes
    assert isinstance(r["sitios_visitados_celdas"], list)
    # ARX-89b (en el piso) sí guarda el tiempo de pared de cada paso: es un float no negativo, no None
    assert isinstance(r["tiempo_computo_s"], float) and r["tiempo_computo_s"] >= 0
    assert "estado" in r and "puntaje" in r       # claves existentes intactas


def test_version_usa_constante_si_git_falla(monkeypatch):
    def falla(*a, **k):
        raise FileNotFoundError("sin git")
    monkeypatch.setattr(exportar.subprocess, "run", falla)
    assert exportar._version_software() == (exportar.VERSION_CONSTANTE, "constante")
