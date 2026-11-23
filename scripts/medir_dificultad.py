"""R23: medición de la dificultad de la partida jugable (garantia=True), modo automático, por nivel y planeta.

Corre las partidas por la API en proceso (TestClient, sin servidor ni red), de una en una, con la política elegida:
    hibrido      controlador completo (RNA + difuso + AG)
    sin_rna      la RNA no interviene
    sin_difuso   velocidad fija 0,5
    sin_ag       el orden de los sitios lo elige el vecino más cercano
Cada fila: nivel, semilla, estado, pasos, batería sobrante (% de la capacidad) y causa de la derrota.

Uso (desde la raíz; medición pesada, una a la vez):
    python scripts/medir_dificultad.py --tamano pequeno --planetas Marte,Tierra --semillas 20 --niveles 1,2,3,4,5 \
        --politica hibrido --salida resultado.json
La tabla en markdown sale por la consola.
"""
import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

from fastapi.testclient import TestClient  # noqa: E402

from api.servidor import crear_app  # noqa: E402
from integracion import ESTADOS_TERMINALES  # noqa: E402

MAX_PASOS = 500


def aplicar_politica(partida, politica: str) -> None:
    from juego.comparacion import _orden_voraz
    m = partida.mision
    if politica == "sin_rna":
        m.usar_rna = False
    elif politica == "sin_difuso":
        m.usar_difuso = False
    elif politica in ("sin_ag", "sin_ag_2opt", "sin_ag_ventanas"):
        if partida.plan_activo:      # R23: la misma ejecución del plan restringido con una heurística en vez del AG
            from juego.partida import _ag_restringido
            m._optimizar_ag = _ag_restringido(partida, heuristica={"sin_ag": "vecino", "sin_ag_2opt": "2opt",
                                                                    "sin_ag_ventanas": "ventanas"}[politica])
            partida._wp = []
            partida._plan_inicial_pendiente = False
        else:
            m._optimizar_ag = _orden_voraz(m)
        m.objetivos = []
        m._planear()
    elif politica == "difuso_base":
        from difuso import FuzzyController
        partida.poner_difuso(FuzzyController())
        partida.conduccion = {}
    elif politica != "hibrido":
        raise SystemExit(f"política desconocida: {politica}")


def causa(p, c) -> str:
    if p.estado == "EXITO":
        return "EXITO"
    if p.estado not in ESTADOS_TERMINALES:
        return "sin terminar en %d pasos" % MAX_PASOS
    if p.estado == "SIN_RUTA":
        return "SIN_RUTA"
    if p.rover.bateria <= 0:
        return "bateria 0"
    return "FRACASO: " + (p.avisos[-1][:50] if p.avisos else "sin aviso")


def partida_api(sem, nivel, tamano, planeta, politica):
    app = crear_app()
    cli = TestClient(app)
    r = cli.post("/partida", json={"semilla": sem, "nivel": nivel, "tamano": tamano, "planeta": planeta,
                                    "modo": "rover" if planeta in ("Marte", "Mercurio", "Venus", "Tierra") else "sonda"})
    assert r.status_code == 200, r.text
    cli.post("/modo", json={"modo": "automatico"})
    s = app.state.sesion
    aplicar_politica(s.partida, politica)
    return cli, s


def correr(sem, nivel, tamano, planeta, politica) -> dict:
    cli, s = partida_api(sem, nivel, tamano, planeta, politica)
    p, c = s.partida, s.combate
    pasos = 0
    while pasos < MAX_PASOS and p.estado not in ESTADOS_TERMINALES:
        if cli.post("/paso").status_code != 200:
            break
        pasos += 1
    cap = float(getattr(p, "capacidad_bateria", 100.0) or 100.0)
    return {"planeta": planeta, "nivel": nivel, "semilla": sem, "estado": p.estado, "exito": p.estado == "EXITO",
            "pasos": pasos, "bateria_pct": round(100.0 * float(p.rover.bateria) / cap, 1),
            "recargas": int(p.recargas_hechas), "pilas": int(p.pilas_recogidas), "causa": causa(p, c)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamano", default="pequeno")
    ap.add_argument("--planetas", default="Marte")
    ap.add_argument("--semillas", type=int, default=20)
    ap.add_argument("--primera", type=int, default=1)
    ap.add_argument("--niveles", default="1,2,3,4,5")
    ap.add_argument("--politica", default="hibrido")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()
    niveles = [int(x) for x in a.niveles.split(",")]
    planetas = a.planetas.split(",")
    filas = []
    t0 = time.time()
    for planeta in planetas:
        for nivel in niveles:
            for sem in range(a.primera, a.primera + a.semillas):
                filas.append(correr(sem, nivel, a.tamano, planeta, a.politica))
                if a.salida:
                    Path(a.salida).write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n## {a.politica} · {a.tamano} · {len(filas)} partidas en {time.time() - t0:.0f} s")
    print("| Planeta | Nivel | Éxito | Pasos (ganadas) | Batería sobrante % (ganadas) | Causas de derrota |\n|---|---|---|---|---|---|")
    for planeta in planetas:
        for nivel in niveles:
            f = [x for x in filas if x["nivel"] == nivel and x["planeta"] == planeta]
            ok = [x for x in f if x["exito"]]
            cs = Counter(x["causa"] for x in f if not x["exito"])
            pm = f"{statistics.mean(x['pasos'] for x in ok):.1f}" if ok else "-"
            bm = f"{statistics.mean(x['bateria_pct'] for x in ok):.1f}" if ok else "-"
            print(f"| {planeta} | {nivel} | {len(ok)}/{len(f)} ({100 * len(ok) / len(f):.0f} %) | {pm} | {bm} | "
                  f"{'; '.join(f'{k}: {v}' for k, v in cs.items()) or '-'} |")


if __name__ == "__main__":
    main()
