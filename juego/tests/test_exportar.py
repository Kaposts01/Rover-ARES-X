import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def tmp_path():
    """Directorio temporal propio: el tmp_path de pytest falla en este equipo por permisos."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "juego"))

from exportar import exportar_partida  # noqa: E402
from experimento import comparar_variantes  # noqa: E402
from simulador import generar_mundo  # noqa: E402


class PartidaFalsa:
    """Stub con la forma que usa exportar_partida: mundo, bitacora() y resumen()."""

    def __init__(self, semilla=7):
        self.mundo = generar_mundo(semilla, n_obstaculos=20, n_barrancos=4, n_sitios=3)
        self._bitacora = pd.DataFrame({
            "paso": [1, 2, 3],
            "estado": ["EXPLORACION", "EXPLORACION", "ALERTA"],
            "bateria": [99.0, 98.0, 97.5],
            "motivos": ["OK", "OK", "V-RNA-OBSTACULO"],
        })
        self._resumen = {"estado": "EXITO", "pasos": 3, "sitios_visitados": 1,
                         "sitios_totales": 3, "bateria_final": 97.5, "vetos": 1,
                         "replanes": 1, "colisiones": 0, "barrancos_pisados": 0}

    def bitacora(self):
        return self._bitacora.copy()

    def resumen(self):
        return dict(self._resumen)


def test_exportar_escribe_csv_y_json_validos(tmp_path):
    carpeta = tmp_path / "salida"
    ruta_csv, ruta_json = exportar_partida(PartidaFalsa(semilla=7), str(carpeta))

    assert Path(ruta_csv).suffix == ".csv" and Path(ruta_json).suffix == ".json"
    assert Path(ruta_csv).name.startswith("partida_7_")
    assert Path(ruta_csv).parent == carpeta

    bitacora = pd.read_csv(ruta_csv)
    assert list(bitacora.columns) == ["paso", "estado", "bateria", "motivos"]
    assert len(bitacora) == 3

    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)
    assert datos["semilla"] == 7
    assert datos["planeta"] == "Marte"
    assert datos["n_obstaculos"] == 20
    assert datos["n_barrancos"] == 4
    assert datos["n_sitios"] == 3
    assert isinstance(datos["bateria_inicial"], float)
    assert datos["resumen"]["estado"] == "EXITO"
    assert "parámetros de simulación ficticios, no especificaciones NASA" in datos["nota"]


def test_exportar_nunca_sobrescribe(tmp_path, monkeypatch):
    import exportar

    class _Ahora:
        def strftime(self, fmt):
            return "20260101-120000"

    class Fecha:
        @staticmethod
        def now():
            return _Ahora()

    monkeypatch.setattr(exportar, "datetime", Fecha)  # fuerza el mismo nombre base en ambas llamadas
    carpeta = str(tmp_path)
    csv1, json1 = exportar_partida(PartidaFalsa(), carpeta)
    csv2, json2 = exportar_partida(PartidaFalsa(), carpeta)

    assert csv1 != csv2 and json1 != json2
    assert Path(csv1).exists() and Path(json1).exists()
    assert Path(csv2).exists() and Path(json2).exists()
    assert Path(csv2).stem.endswith("_2")
    with open(json1, encoding="utf-8") as f:
        json.load(f)  # el primero sigue intacto y válido


def test_exportar_crea_carpeta_si_falta(tmp_path):
    carpeta = tmp_path / "no" / "existe" / "aun"
    assert not carpeta.exists()
    ruta_csv, ruta_json = exportar_partida(PartidaFalsa(), str(carpeta))
    assert carpeta.is_dir()
    assert Path(ruta_csv).exists() and Path(ruta_json).exists()


@pytest.fixture(scope="module")
def tabla_tres_semillas():
    return comparar_variantes(semillas=range(3))


def test_comparar_variantes_tres_semillas_columnas_y_tipos(tabla_tres_semillas):
    tabla = tabla_tres_semillas
    assert len(tabla) == 3
    assert set(tabla.index) == {"híbrido", "sin RNA", "sin difuso"}
    columnas = ["exito_pct", "colisiones", "barrancos_pisados", "sitios_media",
                "pasos_mediana", "pasos_desv", "bateria_media"]
    assert list(tabla.columns) == columnas
    for c in columnas:
        assert pd.api.types.is_numeric_dtype(tabla[c]), c
    assert ((tabla["exito_pct"] >= 0) & (tabla["exito_pct"] <= 100)).all()
