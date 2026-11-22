"""Genera docs/figuras/matriz_confusion.png y docs/figuras/ablacion.png.

Uso (desde ares_x/):  python scripts/generar_figuras.py [escenario] [--version HASH]
Cada figura lleva un pie con la versión de main con que se generó (por defecto, git rev-parse --short main).
La ablación sale de docs/COMPARACION_POLITICAS[_<escenario>].json (sin escenario: el exigente). La matriz de confusión
se calcula con la misma configuración del notebook (60 mapas, 400 muestras por mapa, semilla 42), generando los mapas
de a uno y en un solo hilo, y se evalúa en los mapas de prueba.
"""
import argparse
import json
import os
import subprocess
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


def version_de_main():
    """Hash corto de main; «versión desconocida» si git no está disponible."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "main"], cwd=RAIZ, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "versión desconocida"
    except (OSError, subprocess.SubprocessError):
        return "versión desconocida"


def _pie(version):
    return f"Datos publicados de main {version}; regenerar tras ARX-94f" if version != "versión desconocida"         else "Datos publicados: versión desconocida; regenerar tras ARX-94f"


def figura_matriz(version):
    tr, _, te = particion_por_mapas(total_mapas=60)
    X_tr, y_tr = _por_mapa(tr)
    X_te, y_te = _por_mapa(te)
    res = NeuralPerception(semilla=42).entrenar(X_tr, y_tr).evaluar(X_te, y_te)
    return plot_matriz_confusion(res.matriz_confusion, list(CLASES.values()),
                                 titulo=f"Matriz de confusión de la RNA (prueba: {len(te)} mapas)", pie=_pie(version))


def figura_ablacion(escenario, version):
    nombre = "COMPARACION_POLITICAS.json" if escenario == "base" else f"COMPARACION_POLITICAS_{escenario}.json"
    with open(os.path.join(RAIZ, "docs", nombre), encoding="utf-8") as f:
        datos = json.load(f)
    return plot_ablacion(datos["variantes"], escenario=datos.get("escenario"), pie=_pie(version))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("escenario", nargs="?", default="exigente")
    ap.add_argument("--version", default=None, help="hash de main que se escribe en el pie")
    a = ap.parse_args()
    version = a.version or version_de_main()
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, hacer in (("matriz_confusion.png", lambda: figura_matriz(version)),
                          ("ablacion.png", lambda: figura_ablacion(a.escenario, version))):
        fig = hacer()
        fig.savefig(os.path.join(SALIDA, nombre), dpi=150)
        print("Escrito:", os.path.join("docs", "figuras", nombre))
