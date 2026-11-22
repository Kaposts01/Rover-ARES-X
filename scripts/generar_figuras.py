"""Genera docs/figuras/matriz_confusion.png y docs/figuras/ablacion.png.

Uso (desde ares_x/):  python scripts/generar_figuras.py [escenario]
La ablación sale de docs/COMPARACION_POLITICAS[_<escenario>].json (sin escenario: el exigente). La matriz de confusión
se calcula con la misma configuración del notebook (60 mapas, 400 muestras por mapa, semilla 42), generando los mapas
de a uno y en un solo hilo, y se evalúa en los mapas de prueba.
"""
import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import numpy as np  # noqa: E402

from rna import CLASES, NeuralPerception, generar_dataset, particion_por_mapas  # noqa: E402
from viz import plot_ablacion, plot_matriz_confusion  # noqa: E402

SALIDA = os.path.join(RAIZ, "docs", "figuras")


def _por_mapa(semillas):
    partes = [generar_dataset([s], muestras_por_mapa=400) for s in semillas]
    return np.vstack([p[0] for p in partes]), np.concatenate([p[1] for p in partes])


def figura_matriz():
    tr, _, te = particion_por_mapas(total_mapas=60)
    X_tr, y_tr = _por_mapa(tr)
    X_te, y_te = _por_mapa(te)
    res = NeuralPerception(semilla=42).entrenar(X_tr, y_tr).evaluar(X_te, y_te)
    return plot_matriz_confusion(res.matriz_confusion, list(CLASES.values()),
                                 titulo=f"Matriz de confusión de la RNA (prueba: {len(te)} mapas)")


def figura_ablacion(escenario="exigente"):
    nombre = "COMPARACION_POLITICAS.json" if escenario == "base" else f"COMPARACION_POLITICAS_{escenario}.json"
    with open(os.path.join(RAIZ, "docs", nombre), encoding="utf-8") as f:
        datos = json.load(f)
    return plot_ablacion(datos["variantes"], escenario=datos.get("escenario"))


if __name__ == "__main__":
    escenario = sys.argv[1] if len(sys.argv) > 1 else "exigente"
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, fig in (("matriz_confusion.png", figura_matriz()), ("ablacion.png", figura_ablacion(escenario))):
        fig.savefig(os.path.join(SALIDA, nombre), dpi=150)
        print("Escrito:", os.path.join("docs", "figuras", nombre))
