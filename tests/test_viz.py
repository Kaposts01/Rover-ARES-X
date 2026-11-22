import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from viz import COLOR_BASE, COLOR_HIBRIDO, plot_ablacion, plot_matriz_confusion  # noqa: E402

ETIQ = ["libre", "obstáculo", "barranco"]


def _textos(fig):
    return [t.get_text() for ax in fig.axes for t in ax.texts]


@pytest.fixture(autouse=True)
def _cerrar():
    yield
    plt.close("all")


def test_matriz_forma_y_rotulos_en_espanol():
    fig = plot_matriz_confusion([[8, 1, 0], [2, 5, 1], [0, 1, 6]], ETIQ)
    ax = fig.axes[0]
    assert len(ax.texts) == 9
    assert ax.get_xlabel() == "Clase predicha" and ax.get_ylabel() == "Clase real"
    assert "obstáculo" in [t.get_text() for t in ax.get_xticklabels()]
    assert "8\n88.9 %" in _textos(fig)


def test_matriz_con_ceros_no_falla():
    fig = plot_matriz_confusion(np.zeros((3, 3), dtype=int), ETIQ)
    assert all(t.endswith("0.0 %") for t in _textos(fig))
    fig2 = plot_matriz_confusion([[5, 0, 0], [0, 0, 0], [0, 0, 2]], ETIQ)  # una clase sin muestras
    assert len(fig2.axes[0].texts) == 9


def test_matriz_rechaza_forma_invalida():
    with pytest.raises(ValueError):
        plot_matriz_confusion([[1, 2], [3, 4]], ETIQ)


def _variantes():
    def v(tasa, pasos, col):
        return {"n": 20, "tasa_exito": tasa, "pasos": {"media": pasos, "desviacion": 5.0},
                "colisiones": {"media": col}}
    return {"hibrido": v(100.0, 54.3, 0.0), "sin_rna": v(100.0, 54.0, 0.0), "sin_difuso": v(75.0, 55.6, 0.05)}


def test_ablacion_tres_paneles_y_rotulos():
    fig = plot_ablacion(_variantes(), escenario="exigente")
    assert len(fig.axes) == 3
    etiquetas = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert etiquetas == ["Híbrido", "Sin RNA", "Sin difuso"]
    assert "Tasa de éxito" == fig.axes[0].get_title()
    assert "20 semillas" in fig._suptitle.get_text() and "exigente" in fig._suptitle.get_text()


def test_ablacion_colores_accesibles_y_hibrido_destacado():
    fig = plot_ablacion(_variantes())
    barras = fig.axes[0].patches
    assert to_hex(barras[0].get_facecolor()).upper() == COLOR_HIBRIDO
    assert barras[0].get_hatch()
    assert to_hex(barras[1].get_facecolor()).upper() == COLOR_BASE


def test_ablacion_ceros_y_vacio_no_fallan():
    ceros = {"hibrido": {"n": 0, "tasa_exito": 0.0, "pasos": {"media": 0.0, "desviacion": 0.0},
                         "colisiones": {"media": 0.0}}}
    assert len(plot_ablacion(ceros).axes) == 3
    fig = plot_ablacion({})
    assert "Sin datos de ablación" in _textos(fig)
    assert plot_ablacion({"otra_variante": {}}).axes[0].get_yticklabels()[0].get_text() == "Otra variante"
