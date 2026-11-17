"""ARX-92 · Medición corta: ¿cambia el orden de visita si el AG original decide, frente a la permutación más corta?

Uso: python -I medir_arx92.py <raiz_del_repo> [max_segundos]
Solo lectura del repo; no escribe en él. Salida por consola.
"""
import sys
import time

RAIZ = sys.argv[1]
TOPE = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
sys.path.insert(0, RAIZ)

from integracion import ESTADOS_TERMINALES, Mision  # noqa: E402
from juego.comparacion import partida_variante  # noqa: E402

t0 = time.time()


def orden_sitios(m, ruta):
    sitios = set(tuple(int(v) for v in s) for s in m.mundo.sitios)
    vistos = []
    for c in ruta:
        c = tuple(int(v) for v in c)
        if c in sitios and c not in vistos:
            vistos.append(c)
    return vistos


def ag_original_decide(p):
    """Quita el envoltorio: el AG original fija objetivos y ruta."""
    m = p.mision
    m._optimizar_ag = Mision._optimizar_ag.__get__(m)
    m.objetivos = []
    m._planear()


def correr(p, max_pasos=400):
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < max_pasos:
        p.avanzar_ia()
        pasos += 1
    return p.estado, pasos, int(p.mision.colisiones), round(float(p.rover.bateria), 1), len(p.mision.visitados)


resumen = {}
for esc in ("congelado", "exigente"):
    filas = []
    for s in range(1, 21):
        if time.time() - t0 > TOPE:
            print("TOPE de tiempo alcanzado en", esc, "semilla", s)
            break
        p = partida_variante(s, "hibrido", esc)
        m = p.mision
        n_sitios = len(m.mundo.sitios)
        orden_env = orden_sitios(m, m.ruta)
        pend = {c: v for c, v in m.mundo.sitios.items() if c not in m.visitados}
        ruta_ag = Mision._optimizar_ag(m, m.rover.posicion, pend)
        orden_ag = orden_sitios(m, ruta_ag)
        completa = len(orden_ag) == n_sitios
        filas.append({"semilla": s, "n_sitios": n_sitios, "orden_env": orden_env, "orden_ag": orden_ag,
                      "ag_completa": completa, "difiere": orden_env != orden_ag,
                      "largo_env": len(m.ruta) - 1, "largo_ag": len(ruta_ag) - 1 if ruta_ag else None})
    resumen[esc] = filas
    dif = [f["semilla"] for f in filas if f["difiere"]]
    inc = [f["semilla"] for f in filas if not f["ag_completa"]]
    print(f"\n== {esc}: {len(filas)} semillas · orden distinto AG vs envoltorio: {len(dif)} {dif} · "
          f"rutas AG incompletas: {len(inc)} {inc} · sitios por mapa: {sorted(set(f['n_sitios'] for f in filas))}")
    for f in filas:
        print(f"  s{f['semilla']:2d} sitios={f['n_sitios']} env={f['orden_env']} largo={f['largo_env']} | "
              f"ag={f['orden_ag']} largo={f['largo_ag']} completa={f['ag_completa']} difiere={f['difiere']}")
print(f"\n[orden] {time.time() - t0:.0f} s")

# Resultado de partida completa solo donde el orden difiere y la ruta del AG está completa (congelado primero)
print("\n== resultado de partida donde el orden difiere (hibrido actual vs AG original decide)")
for esc in ("congelado", "exigente"):
    for f in resumen[esc]:
        if not f["difiere"]:
            continue
        if time.time() - t0 > TOPE + 60:
            print("TOPE de tiempo alcanzado en resultados", esc)
            break
        s = f["semilla"]
        a = correr(partida_variante(s, "hibrido", esc))
        pb = partida_variante(s, "hibrido", esc)
        ag_original_decide(pb)
        b = correr(pb)
        print(f"  {esc} s{s:2d} actual={a} | ag_decide={b} | ag_completa={f['ag_completa']}")
print(f"\n[total] {time.time() - t0:.0f} s")
