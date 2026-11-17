"""ARX-92c (medición única aprobada por el Maestro): exigente de 10 sitios, 20 semillas.

Columnas: todas las variantes con el umbral oficial (ev3-d74) y el híbrido también SIN umbral (diagnóstico, no oficial).
Desglose del híbrido por semilla: sin batería en el camino, o sitios descartados por _planear (el plan inicial no
tiene sitios). Se publica tal como sale; no hay segunda corrección.

Uso (desde ares_x/):  python scripts/medicion_92c_ex10.py SALIDA.json [semillas=20]
"""
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from integracion import ESTADOS_TERMINALES  # noqa: E402
from juego import comparacion  # noqa: E402
import juego.partida as pm  # noqa: E402


def jugar_hibrido(semilla):
    p = comparacion.partida_variante(semilla, "hibrido", "exigente10")
    sitios = set(p.mundo.sitios)
    plan_sitios = len([o for o in p.mision.objetivos if o in sitios])
    for _ in range(400):
        if p.estado in ESTADOS_TERMINALES:
            break
        p.avanzar_ia()
    visitados = len(p.mision.visitados)
    if p.estado == "EXITO":
        causa = "exito"
    elif plan_sitios == 0:
        causa = "sitios descartados (plan sin sitios)"
    elif p.rover.bateria <= 0 and visitados < len(sitios):
        causa = "sin batería en el camino"
    else:
        causa = "otra"
    return {"semilla": semilla, "estado": p.estado, "exito": p.estado == "EXITO", "sitios_visitados": visitados,
            "plan_sitios": plan_sitios, "bateria_final": round(float(p.rover.bateria), 1), "causa": causa}


def main():
    salida = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    semillas = list(range(1, n + 1))
    t0 = time.perf_counter()
    res = {"inicio": time.strftime("%H:%M:%S"), "escenario": "exigente10", "con_umbral": {}, "hibrido_sin_umbral": [],
           "hibrido_con_umbral": [], "sin_umbral_nota": "diagnóstico; no pasa a oficial (ARX-92c §14)"}
    d = comparacion.comparar(semillas, "exigente10")
    res["con_umbral"] = {"variantes": d["variantes"], "filas": d["filas"]}
    print("con umbral listo", round(time.perf_counter() - t0), "s", flush=True)
    for s in semillas:
        res["hibrido_con_umbral"].append(jugar_hibrido(s))
    print("hibrido con umbral (desglose) listo", round(time.perf_counter() - t0), "s", flush=True)
    umbral_original = pm.UMBRAL_EMPATE
    pm.UMBRAL_EMPATE = 0.0
    try:
        for s in semillas:
            res["hibrido_sin_umbral"].append(jugar_hibrido(s))
    finally:
        pm.UMBRAL_EMPATE = umbral_original
    print("sin umbral listo", round(time.perf_counter() - t0), "s", flush=True)
    res["fin"] = time.strftime("%H:%M:%S")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print("escrito", os.path.basename(salida), "fin", res["fin"], flush=True)


if __name__ == "__main__":
    main()
