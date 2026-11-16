import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego import cli  # noqa: E402


@pytest.fixture
def carpeta():
    # tmp_path de pytest falla en este equipo (permisos de AppData), así que se usa tempfile propio
    ruta = tempfile.mkdtemp(prefix="ares_x_test_")
    yield ruta
    shutil.rmtree(ruta, ignore_errors=True)


def test_partida_semilla_11_llega_y_puntaje_es_reproducible(carpeta):
    a = cli.correr(semilla=11, pasos=300, salida=carpeta, capturas=False)
    b = cli.correr(semilla=11, pasos=300, salida=carpeta, capturas=False)
    assert a["llego"] is True
    assert a["estado"] == "EXITO"
    assert isinstance(a["puntaje"], int)
    assert a["puntaje"] == b["puntaje"]
    assert a["pasos"] == b["pasos"]


def test_eventos_programados_se_registran(carpeta):
    res = cli.correr(semilla=11, pasos=300, salida=carpeta, capturas=False)
    nombres = [e.split(":")[1] for e in res["eventos"]]
    assert nombres == ["barranco", "falla_sensor", "tormenta"]


def test_exportacion_csv_y_json_validos(carpeta):
    res = cli.correr(semilla=11, pasos=300, salida=carpeta, capturas=False)
    assert os.path.isfile(res["csv"])
    assert os.path.isfile(res["json"])
    with open(res["json"], encoding="utf-8") as f:
        datos = json.load(f)
    assert datos["semilla"] == 11
    assert "resumen" in datos and "nota" in datos
    with open(res["csv"], encoding="utf-8") as f:
        cabecera = f.readline().strip().split(",")
    assert "paso" in cabecera and "posicion" in cabecera


def test_capturas_se_guardan_en_la_carpeta_indicada(carpeta):
    from juego.capturas import generar_capturas
    rutas = generar_capturas(semilla=11, carpeta=os.path.join(carpeta, "capturas"))
    assert set(rutas) == {"inicio", "barranco", "falla_sensor", "tormenta", "llegada_refugio"}
    for ruta in rutas.values():
        assert os.path.getsize(ruta) > 1000


def test_main_exige_headless(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
