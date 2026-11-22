"""Medición ARX-94e (M2): híbrido frente a sin_rna, 20 semillas, escenarios congelado y exigente.

Uso (desde la raíz del repositorio):
    OMP_NUM_THREADS=1 python scripts/medicion_94e.py                 # completa: 20 semillas, congelado y exigente
    OMP_NUM_THREADS=1 python scripts/medicion_94e.py --rapido        # verificación: 3 semillas, mapa chico
    opciones: --semillas N  --escenarios congelado,exigente  --salida DIR

Escribe en DIR (por defecto docs/planes/mediciones; en --rapido, un directorio aparte que se indica o el temporal):
    medicion_94e_<escenario>.json   cifras por semilla y por variante
    medicion_94e.md                 resumen con el conteo X/N frente al criterio M2

Criterio M2 (docs/planes/ARX-94_umbrales.md): >= 5/20 semillas con divergencia por RNA-RIESGO o V-RNA-*.
Se publica tal como salga. No se ajusta nada del motor ni de los umbrales.

Método. Por semilla se corre UNA partida de `hibrido` y UNA de `sin_rna` (juego.comparacion._correr_traza), de las que salen
a la vez las cifras (éxito, colisiones, pasos) y la traza. La comparación paso a paso repite la regla de
`juego.comparacion.trazar_divergencias` (misma firma, mismo estado previo = divergencia "directa"), pero solo para sin_rna.
Atribución: se leen los motivos de la bitácora del híbrido en el paso divergente (RNA-RIESGO[-2]:..., V-RNA-*).
Una semilla cuenta para M2 si su PRIMERA divergencia directa (decisión, velocidad o ruta) trae uno de esos motivos.
Como dato aparte (no cuenta para M2) se cuenta si algún paso divergente, directo o consecuencia, los trae.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego import comparacion as C  # noqa: E402

CRITERIO_M2 = 5            # de 20 semillas (ARX-94_umbrales.md)
HASH_CONGELADO_PUBLICADO = "d6fb907994a30420652391e32b514bf5a4bb31c05f0d15f2f5aea9d1657cdfef"   # ev3-d84, 17/11
ESCENARIO_RAPIDO = "rapido_94e"
MAPA_RAPIDO = (12, 16)
VARIANTE = "sin_rna"


def _motivos_rna(filas) -> list:
    """Motivos de la técnica RNA presentes en las filas de la bitácora de un paso."""
    out = []
    for f in filas:
        for m in str(f["motivos"]).split(";"):
            m = m.strip()
            if m.startswith("RNA-RIESGO") or m.startswith("V-RNA-"):
                out.append(m)
    return out


def _tipo_motivo(m: str) -> str:
    return "RNA-RIESGO" if m.startswith("RNA-RIESGO") else m.split(":")[0]


def _resultado(p) -> dict:
    m = p.mision
    return {"estado": p.estado, "exito": p.estado == "EXITO", "pasos": max((f["paso"] for f in m.log.filas), default=0),
            "colisiones": int(m.colisiones), "bateria_final": round(float(p.rover.bateria), 2),
            "sitios_visitados": len(m.visitados)}


def divergencias(fh: dict, fv: dict) -> list:
    """Pasos en que difiere la bitácora del híbrido (fh) y de sin_rna (fv), con la regla de trazar_divergencias."""
    out = []
    previa_h = previa_v = None
    hubo_directa = False
    for paso in sorted(set(fh) | set(fv)):
        a, b = fh.get(paso, []), fv.get(paso, [])
        igual_previo = previa_h == previa_v
        if a and b and C._firma(a) != C._firma(b):
            _, cambio = C._motivo_y_cambio(VARIANTE, a, b)
            if igual_previo and not hubo_directa:
                origen = "directa_codigo" if cambio == "otros_motivos" else "directa"
            else:
                origen = "consecuencia"
            mot = _motivos_rna(a)
            out.append({"paso": paso, "celda": str(a[-1]["posicion"]), "origen": origen, "cambio": cambio,
                        "motivos_rna": mot, "motivos_hibrido": ";".join(str(f["motivos"]) for f in a)})
            hubo_directa = hubo_directa or origen == "directa"
        previa_h = (a[-1]["posicion"], a[-1]["bateria"]) if a else previa_h
        previa_v = (b[-1]["posicion"], b[-1]["bateria"]) if b else previa_v
    return out


def medir_semilla(semilla: int, escenario: str) -> dict:
    t = time.time()
    ph, _ = C._correr_traza(semilla, "hibrido", escenario)
    pv, _ = C._correr_traza(semilla, VARIANTE, escenario)
    divs = divergencias(C._filas_por_paso(ph), C._filas_por_paso(pv))
    directa = next((d for d in divs if d["origen"] == "directa"), None)
    tipos_directa = [t_ for t_ in directa["cambio"].split("+")] if directa else []
    atribuida = bool(directa and directa["motivos_rna"])
    return {
        "semilla": semilla,
        "hibrido": _resultado(ph), VARIANTE: _resultado(pv),
        "n_pasos_divergentes": len(divs),
        "primera_directa": directa,
        "tipos_primera_directa": tipos_directa,
        "motivo_atribuido": sorted({_tipo_motivo(m) for m in directa["motivos_rna"]}) if atribuida else [],
        "cuenta_para_m2": atribuida,
        "algun_paso_con_motivo_rna": any(d["motivos_rna"] for d in divs),
        "divergencias": divs,
        "segundos": round(time.time() - t, 2),
    }


def _res(valores) -> dict:
    return C._resumen(valores)


def resumir(filas_semilla: list, escenario: str, semillas: list) -> dict:
    por_var = {}
    for v in ("hibrido", VARIANTE):
        g = [f[v] for f in filas_semilla]
        por_var[v] = {"exitos": sum(x["exito"] for x in g), "n": len(g),
                      "colisiones_total": sum(x["colisiones"] for x in g),
                      "semillas_con_colision": sum(1 for x in g if x["colisiones"] > 0),
                      "pasos": _res([x["pasos"] for x in g]), "colisiones": _res([x["colisiones"] for x in g]),
                      "bateria_final": _res([x["bateria_final"] for x in g])}
    cuentan = [f["semilla"] for f in filas_semilla if f["cuenta_para_m2"]]
    con_div = [f["semilla"] for f in filas_semilla if f["primera_directa"]]
    por_tipo = {"decision": 0, "velocidad": 0, "ruta": 0}
    por_motivo = {}
    for f in filas_semilla:
        if f["cuenta_para_m2"]:
            for t_ in f["tipos_primera_directa"]:
                por_tipo[t_] = por_tipo.get(t_, 0) + 1
            for m in f["motivo_atribuido"]:
                por_motivo[m] = por_motivo.get(m, 0) + 1
    n = len(semillas)
    return {
        "escenario": escenario, "semillas": semillas, "variantes": por_var,
        "m2": {"criterio": f">= {CRITERIO_M2}/20", "semillas_que_cuentan": cuentan, "conteo": len(cuentan), "n": n,
               "semillas_con_divergencia_directa": con_div,
               "semillas_con_divergencia_directa_no_rna": [s for s in con_div if s not in cuentan],
               "semillas_con_algun_paso_rna": [f["semilla"] for f in filas_semilla if f["algun_paso_con_motivo_rna"]],
               "por_tipo_de_cambio": por_tipo, "por_motivo": por_motivo,
               "cumple": len(cuentan) >= CRITERIO_M2 if n == 20 else None},
    }


def hash_filas(filas_semilla: list) -> str:
    """sha256 de las cifras por semilla de híbrido y sin_rna (JSON canónico). Es el hash de ESTA corrida del congelado."""
    base = [{"semilla": f["semilla"], "hibrido": f["hibrido"], VARIANTE: f[VARIANTE]} for f in filas_semilla]
    return hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()


def hash_publicado_en_repo() -> str:
    ruta = os.path.join(RAIZ, "docs", "COMPARACION_POLITICAS.json")
    if not os.path.exists(ruta):
        return "no encontrado"
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def correr_escenario(escenario: str, semillas: list, log=print) -> dict:
    filas = []
    for s in semillas:
        r = medir_semilla(s, escenario)
        filas.append(r)
        log(f"  [{escenario}] semilla {s}: híbrido {r['hibrido']['estado']} col {r['hibrido']['colisiones']} | "
            f"sin_rna {r[VARIANTE]['estado']} col {r[VARIANTE]['colisiones']} | "
            f"directa {r['primera_directa']['cambio'] if r['primera_directa'] else '-'} "
            f"rna {r['motivo_atribuido'] or '-'} ({r['segundos']} s)")
    res = resumir(filas, escenario, semillas)
    res["hash_filas"] = hash_filas(filas)
    res["filas"] = filas
    return res


def _fila_tabla(nombre, r):
    h, v = r["variantes"]["hibrido"], r["variantes"][VARIANTE]
    return (f"| {nombre} | {h['exitos']}/{h['n']} | {v['exitos']}/{v['n']} | {h['colisiones_total']} ({h['semillas_con_colision']} sem.) | "
            f"{v['colisiones_total']} ({v['semillas_con_colision']} sem.) | {h['pasos']['mediana']} | {v['pasos']['mediana']} |")


def redactar(resultados: dict, meta: dict) -> str:
    L = ["# ARX-94e · medición M2 (resumen generado por scripts/medicion_94e.py)", "",
         f"Generado: {meta['fecha']} · semillas: {meta['n']} · modo: {meta['modo']} · duración total: {meta['segundos']} s.", ""
         "Se publica tal como salga. Criterio M2 (ARX-94_umbrales.md): al menos 5/20 semillas con divergencia por RNA-RIESGO o V-RNA-*.", ""]
    for esc, r in resultados.items():
        m = r["m2"]
        L += [f"## Escenario {esc}", "",
              f"**M2: {m['conteo']}/{m['n']} semillas** con divergencia atribuida a RNA-RIESGO o V-RNA-* (criterio {m['criterio']}): "
              + ("CUMPLE" if m["cumple"] else ("NO CUMPLE" if m["cumple"] is False else "no evaluable (menos de 20 semillas)")) + ".", "",
              f"- Semillas que cuentan: {m['semillas_que_cuentan'] or 'ninguna'}",
              f"- Semillas con divergencia directa de cualquier origen: {m['semillas_con_divergencia_directa'] or 'ninguna'}; "
              f"de ellas, no atribuidas a la RNA: {m['semillas_con_divergencia_directa_no_rna'] or 'ninguna'}",
              f"- Semillas con algún paso divergente (directo o consecuencia) con motivo RNA (dato aparte, no cuenta): {m['semillas_con_algun_paso_rna'] or 'ninguna'}",
              f"- Por tipo de cambio de la primera divergencia atribuida (una semilla puede sumar en varios): {m['por_tipo_de_cambio']}",
              f"- Por motivo: {m['por_motivo'] or 'ninguno'}", "",
              "| escenario | éxito híbrido | éxito sin_rna | colisiones híbrido | colisiones sin_rna | pasos med. híbrido | pasos med. sin_rna |",
              "|---|---|---|---|---|---|---|", _fila_tabla(esc, r), "",
              "Por semilla (primera divergencia directa; cambio = decisión, velocidad y/o ruta):", "",
              "| semilla | primera directa (paso, cambio) | motivo RNA | cuenta | col. híbrido | col. sin_rna | estado híbrido | estado sin_rna |",
              "|---|---|---|---|---|---|---|---|"]
        for f in r["filas"]:
            d = f["primera_directa"]
            L.append(f"| {f['semilla']} | {(str(d['paso']) + ', ' + d['cambio']) if d else '-'} | {', '.join(f['motivo_atribuido']) or '-'} | "
                     f"{'sí' if f['cuenta_para_m2'] else 'no'} | {f['hibrido']['colisiones']} | {f[VARIANTE]['colisiones']} | "
                     f"{f['hibrido']['estado']} | {f[VARIANTE]['estado']} |")
        L += ["", f"Hash de las cifras de esta corrida ({esc}, híbrido + sin_rna): `{r['hash_filas']}`", ""]
    L += ["## Hash del congelado", "",
          f"- Publicado el 17/11 (ev3-d84, test de regresión): `{HASH_CONGELADO_PUBLICADO}`",
          f"- sha256 del archivo `docs/COMPARACION_POLITICAS.json` de esta rama (antes de 94f): `{meta['hash_json_publicado']}`",
          "- Hash de esta corrida: ver cada escenario (solo híbrido y sin_rna, 94e no regenera `docs/`).", "",
          "94e no escribe nada en `docs/` fuera de `docs/planes/mediciones/`; la regeneración única es 94f.", ""]
    return "\n".join(L)


def _correr_todos(escenarios, n, semillas, salida, resultados):
    for esc in escenarios:
        print(f"escenario {esc}: {n} semillas", flush=True)
        t = time.time()
        r = correr_escenario(esc, semillas)
        r["segundos"] = round(time.time() - t, 1)
        resultados[esc] = r
        with open(os.path.join(salida, f"medicion_94e_{esc}.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print(f"  M2 {esc}: {r['m2']['conteo']}/{n}  ({r['segundos']} s)", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rapido", action="store_true", help="3 semillas y mapa chico (verificación del script)")
    ap.add_argument("--semillas", type=int, default=None)
    ap.add_argument("--escenarios", default="congelado,exigente")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    t0 = time.time()
    if a.rapido:
        import juego.partida as P
        _previo = (P.FILAS_BASE, P.COLUMNAS_BASE)
        P.FILAS_BASE, P.COLUMNAS_BASE = MAPA_RAPIDO
        C.ESCENARIOS[ESCENARIO_RAPIDO] = {"nivel": 2, "ruido": 0.6, "p_detectar": 0.4, "prob_fallo": None, "fisica_velocidad": True}
        escenarios, n, modo = [ESCENARIO_RAPIDO], a.semillas or 3, "rápido (mapa %dx%d)" % MAPA_RAPIDO
        salida = a.salida or os.path.join(RAIZ, "docs", "planes", "mediciones", "_rapido")
    else:
        escenarios, n, modo = [e for e in a.escenarios.split(",") if e], a.semillas or 20, "completo"
        salida = a.salida or os.path.join(RAIZ, "docs", "planes", "mediciones")
    os.makedirs(salida, exist_ok=True)
    semillas = list(range(1, n + 1))

    resultados = {}
    try:
        _correr_todos(escenarios, n, semillas, salida, resultados)
    finally:
        if a.rapido:        # no dejar el mapa chico ni el escenario de verificación en el proceso (pruebas en la misma sesión)
            P.FILAS_BASE, P.COLUMNAS_BASE = _previo
            C.ESCENARIOS.pop(ESCENARIO_RAPIDO, None)

    meta = {"fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "n": n, "modo": modo,
            "segundos": round(time.time() - t0, 1), "hash_json_publicado": hash_publicado_en_repo()}
    with open(os.path.join(salida, "medicion_94e.md"), "w", encoding="utf-8") as f:
        f.write(redactar(resultados, meta))
    print("escrito en", salida, "·", meta["segundos"], "s")
    return resultados


if __name__ == "__main__":
    main()
