"""ARX-92a (QA): ¿cambian los pesos del fitness el orden de visita del juego, con y sin el umbral de empate?

Receta de la tabla del informe de QA del piso (M2 / ev3-d79): para cada juego de pesos no trivial, cuenta en cuántas
semillas el orden de los sitios que juega la partida difiere del orden con los pesos por defecto, con el umbral vigente
(UMBRAL_EMPATE) y sin umbral (0,0). Nivel 3, mapa pequeño (20x30, 20 semillas) y grande (40x60, 10 semillas).

Uso: python medicion_92a_pesos_umbral.py [pequeno|grande|ambos] [n_semillas]
La raíz del repositorio se calcula desde la ubicación del archivo (docs/planes/ o cualquier subcarpeta de dos niveles);
si no se encuentra, se usa el directorio actual.
"""
import sys
from pathlib import Path

_AQUI = Path(__file__).resolve()
RAIZ = next((p for p in (_AQUI.parents[2] if len(_AQUI.parents) > 2 else _AQUI.parent, Path.cwd()) if (p / "juego" / "partida.py").exists()), Path.cwd())
sys.path.insert(0, str(RAIZ))

import juego.partida as pm  # noqa: E402
from juego.partida import Partida  # noqa: E402

PESOS = {
    "riesgo x5": {"ciencia": 0, "distancia": 0, "energia": 0, "riesgo": 5, "tiempo": 0},
    "ciencia x5": {"ciencia": 5, "distancia": 0, "energia": 0, "riesgo": 0, "tiempo": 0},
    "energia x5": {"ciencia": 0, "distancia": 0, "energia": 5, "riesgo": 0, "tiempo": 0},
    "tiempo x5": {"ciencia": 0, "distancia": 0, "energia": 0, "riesgo": 0, "tiempo": 5},
    "riesgo 3 / distancia 0,3": {"ciencia": 1, "distancia": 0.3, "energia": 0.2, "riesgo": 3, "tiempo": 0.1},
}
TAMANOS = {"pequeno": (20, 30, 20), "grande": (40, 60, 10)}


def orden_del_juego(p, pesos, umbral):
    """Replanifica la partida con esos pesos y ese umbral; devuelve el orden de sitios del plan."""
    m = p.mision
    anterior = pm.UMBRAL_EMPATE
    pm.UMBRAL_EMPATE = umbral
    try:
        m.pesos_ag = pesos
        m.objetivos = []
        m._planear()
    finally:
        pm.UMBRAL_EMPATE = anterior
    return tuple(o for o in m.objetivos if o in m.mundo.sitios)


def medir(tam, n):
    filas, columnas, _ = TAMANOS[tam]
    umbral = pm.UMBRAL_EMPATE
    cambios = {(k, con): 0 for k in PESOS for con in (True, False)}
    for semilla in range(1, n + 1):
        p = Partida(semilla=semilla, nivel=3, filas=filas, columnas=columnas)
        base = orden_del_juego(p, None, umbral)
        for nombre, pesos in PESOS.items():
            for con in (True, False):
                if orden_del_juego(p, pesos, umbral if con else 0.0) != base:
                    cambios[(nombre, con)] += 1
    print(f"{tam} ({filas}x{columnas}), nivel 3, {n} semillas, umbral {umbral}. Semillas en que el orden cambia frente a los pesos por defecto:")
    for nombre in PESOS:
        print(f"  {nombre:26s} con umbral {cambios[(nombre, True)]:2d}/{n}   sin umbral {cambios[(nombre, False)]:2d}/{n}")


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "ambos"
    for tam in (("pequeno", "grande") if que == "ambos" else (que,)):
        n = int(sys.argv[2]) if len(sys.argv) > 2 else TAMANOS[tam][2]
        medir(tam, n)
