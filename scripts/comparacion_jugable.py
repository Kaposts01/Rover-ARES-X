"""R23: comparación de políticas en la partida jugable difícil (plan con ventanas, recarga obligatoria y mecánicas del planeta).

Híbrido frente a sin RNA, sin difuso, sin AG (vecino más cercano, 2-opt y por ventanas) y difuso sin evolucionar, con las mismas
semillas para todas las variantes: 20 semillas de desarrollo (1 a 20) y 20 de VALIDACIÓN no vistas (101 a 120; ni el diseño de la
dificultad ni la evolución del difuso, que usa 301 a 308, las vieron). Escribe docs/COMPARACION_POLITICAS_<escenario>.json con la
misma forma que los demás (variantes, filas) y la validación en la clave `validacion`.

Uso (desde la raíz; medición pesada, una a la vez):
    python scripts/comparacion_jugable.py --escenario jugable_dificil
    python scripts/comparacion_jugable.py --escenario jugable_dificil_neptuno
    python scripts/comparacion_jugable.py --escenario jugable_dificil --semillas 4 --validacion 0 --salida /tmp/prueba.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

from juego import comparacion  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escenario", default="jugable_dificil")
    ap.add_argument("--semillas", type=int, default=20)
    ap.add_argument("--validacion", type=int, default=20)
    ap.add_argument("--primera-validacion", type=int, default=101)
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()
    t0 = time.time()
    datos = comparacion.comparar(range(1, a.semillas + 1), escenario=a.escenario)
    print(f"desarrollo: {a.semillas} semillas en {time.time() - t0:.0f} s", flush=True)
    if a.validacion:
        val = comparacion.comparar(range(a.primera_validacion, a.primera_validacion + a.validacion), escenario=a.escenario)
        datos["validacion"] = {k: val[k] for k in ("semillas", "variantes", "filas")}
        print(f"validación: {a.validacion} semillas en {time.time() - t0:.0f} s", flush=True)
    datos["parametros"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in comparacion.ESCENARIOS[a.escenario].items()}
    salida = Path(a.salida) if a.salida else repo / "docs" / f"COMPARACION_POLITICAS_{a.escenario}.json"
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    for nombre, bloque in (("desarrollo", datos), ("validación", datos.get("validacion"))):
        if not bloque:
            continue
        print(f"\n## {a.escenario} · {nombre} · semillas {bloque['semillas'][0]}–{bloque['semillas'][-1]}")
        print("| Variante | Éxito | IC 95 % | Ciencia (media ± EE) | Puntaje (media ± EE) | Pasos | Recargas |\n|---|---|---|---|---|---|---|")
        for v, r in bloque["variantes"].items():
            print(f"| {v} | {r['exitos']}/{r['n']} ({r['tasa_exito']:.0f} %) | {r['ic95_exito'][0]:.0f}–{r['ic95_exito'][1]:.0f} | "
                  f"{r['ciencia']['media']:.3f} ± {r['ciencia']['error_estandar']:.3f} | "
                  f"{r['puntaje']['media']:.0f} ± {r['puntaje']['error_estandar']:.0f} | {r['pasos']['media']:.0f} | "
                  f"{r['recargas']['media']:.1f} |")


if __name__ == "__main__":
    main()
