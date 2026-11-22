"""Reporte de la misión en una sola página HTML autocontenida (auditoría 22/11).

Solo lee el estado de la sesión: no cambia la partida ni el motor. Sin dependencias externas (CSS y gráficos SVG
en línea), para abrirlo sin conexión o adjuntarlo. Todo texto que viene del motor se escapa.
"""
import datetime
import html
from collections import Counter

ANCHO_SVG, ALTO_SVG = 640, 150


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _num(v, d=2) -> str:
    try:
        return f"{float(v):.{d}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "-"


def resumen_tecnicas(filas_log: list) -> dict:
    """Conteos por técnica a partir de los motivos y reglas de la bitácora del motor (una fila por paso)."""
    motivos = Counter()
    reglas = Counter()
    for f in filas_log:
        for m in str(f.get("motivos") or "").split(";"):
            if m:
                motivos[m.split(":")[0]] += 1
        for r in str(f.get("reglas") or "").split(";"):
            if r:
                reglas[r] += 1
    vel = [float(f["velocidad"]) for f in filas_log if f.get("velocidad") is not None]
    return {
        "rna": {k: v for k, v in motivos.items() if k.startswith(("V-RNA", "RNA-RIESGO"))},
        "difuso": dict(reglas.most_common(6)),
        "ag": {k: v for k, v in motivos.items() if k.startswith("REPLAN")},
        "supervisor": {k: v for k, v in motivos.items() if k.startswith("V-") and not k.startswith("V-RNA")},
        "velocidad_media": (sum(vel) / len(vel)) if vel else None,
        "pasos": len(filas_log),
    }


def svg_serie(valores: list, color: str, ymin: float = None, ymax: float = None, titulo: str = "") -> str:
    """Polilínea SVG simple de una serie por paso (None = hueco)."""
    puntos = [(i, v) for i, v in enumerate(valores) if v is not None]
    if not puntos:
        return f'<p class="nota">{_e(titulo)}: sin datos.</p>'
    lo = min(v for _, v in puntos) if ymin is None else ymin
    hi = max(v for _, v in puntos) if ymax is None else ymax
    if hi - lo < 1e-9:
        hi = lo + 1.0
    n = max(1, len(valores) - 1)
    m = 28
    def xy(i, v):
        x = m + (ANCHO_SVG - m - 8) * i / n
        y = 8 + (ALTO_SVG - 28) * (1 - (v - lo) / (hi - lo))
        return f"{x:.1f},{y:.1f}"
    trazo = " ".join(xy(i, v) for i, v in puntos)
    return (f'<figure><figcaption>{_e(titulo)}</figcaption>'
            f'<svg viewBox="0 0 {ANCHO_SVG} {ALTO_SVG}" role="img" aria-label="{_e(titulo)}">'
            f'<line x1="{m}" y1="{ALTO_SVG - 20}" x2="{ANCHO_SVG - 8}" y2="{ALTO_SVG - 20}" class="eje"/>'
            f'<text x="2" y="14" class="et">{_num(hi, 2)}</text><text x="2" y="{ALTO_SVG - 22}" class="et">{_num(lo, 2)}</text>'
            f'<text x="{m}" y="{ALTO_SVG - 4}" class="et">paso 1</text><text x="{ANCHO_SVG - 60}" y="{ALTO_SVG - 4}" class="et">paso {len(valores)}</text>'
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{trazo}"/></svg></figure>')


def _tabla_conteos(titulo: str, conteos: dict, vacio: str, nota: str = "") -> str:
    extra = f"<p class='nota'>{_e(nota)}</p>" if nota else ""
    if not conteos:
        return f"<section><h3>{_e(titulo)}</h3>{extra}<p class='nota'>{_e(vacio)}</p></section>"
    filas = "".join(f"<tr><td>{_e(k)}</td><td class='n'>{v}</td></tr>" for k, v in sorted(conteos.items(), key=lambda x: -x[1]))
    return f"<section><h3>{_e(titulo)}</h3>{extra}<table><thead><tr><th>motivo o regla</th><th>pasos</th></tr></thead><tbody>{filas}</tbody></table></section>"


def construir_html(datos: dict) -> str:
    """datos: estado (dict de /estado), filas_log (bitácora del motor), historial (filas de /historial), generado."""
    est = datos.get("estado") or {}
    log = datos.get("filas_log") or []
    hist = datos.get("historial") or []
    t = resumen_tecnicas(log)
    generado = datos.get("generado") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    filas_resumen = [
        ("Planeta y vehículo", f"{est.get('planeta', '-')} · {est.get('modo_planeta', '-')}"),
        ("Semilla y nivel", f"{est.get('semilla', '-')} · nivel {est.get('nivel', '-')}"),
        ("Modo de control", est.get("modo", "-")),
        ("Resultado", est.get("estado", "-")),
        ("Pasos de la misión", est.get("paso", "-")),
        ("Batería final", f"{_num(est.get('bateria'), 1)} %"),
        ("Sitios científicos", f"{est.get('sitios_visitados', '-')}/{est.get('sitios_totales', '-')}"),
        ("Vetos · replanteos · choques", f"{est.get('vetos', '-')} · {est.get('replanes', '-')} · {est.get('colisiones', '-')}"),
        ("Velocidad media (difuso)", _num(t["velocidad_media"], 3)),
        ("Puntaje simple", est.get("puntaje", "-")),
    ]
    resumen = "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in filas_resumen)
    avisos = "".join(f"<li>{_e(a)}</li>" for a in (est.get("avisos") or [])) or "<li>Sin avisos.</li>"
    graficos = "".join([
        svg_serie([f.get("bateria") for f in log], "#5fd3ff", 0, None, "Batería (%) por paso"),
        svg_serie([f.get("velocidad") for f in log], "#6ee7a8", 0, 1, "Velocidad decidida por el difuso"),
        svg_serie([f.get("p_barranco") for f in log], "#ff5d6c", 0, 1, "p(barranco) según la RNA"),
        svg_serie([f.get("fitness_ag") for f in log], "#ffc857", None, None, "Fitness del plan del AG en juego"),
    ])
    bitacora = "".join(
        f"<tr><td class='n'>{_e(h.get('n'))}</td><td class='n'>{_e(h.get('paso_mision'))}</td><td>{_e(h.get('modo'))}</td>"
        f"<td>{_e(h.get('accion'))}</td><td>{_e(h.get('tecnica'))}</td><td>{_e(h.get('motivo'))}</td>"
        f"<td class='n'>{_num(h.get('velocidad'), 2)}</td><td class='n'>{_num(h.get('p_barranco'), 2)}</td>"
        f"<td class='n'>{_num(h.get('bateria'), 1)}</td><td>{_e(h.get('reglas'))}</td></tr>" for h in hist)
    from api.narrador import narrar_fila
    narracion = "".join(f"<li>{_e(narrar_fila(f))}</li>" for f in log)
    semilla, nivel = est.get("semilla", "-"), est.get("nivel", "-")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARES-X · reporte de misión · semilla {_e(semilla)}</title>
<style>
body {{ font: 14px/1.5 "Segoe UI", system-ui, sans-serif; margin: 0; background: #0b0f1a; color: #e7edf7; }}
main {{ max-width: 980px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 22px; letter-spacing: .08em; margin: 0 0 4px; color: #5fe6ff; }}
h2 {{ font-size: 16px; margin: 28px 0 8px; border-bottom: 1px solid #22304a; padding-bottom: 4px; }}
h3 {{ font-size: 13px; margin: 16px 0 6px; color: #b4bfd3; text-transform: uppercase; letter-spacing: .06em; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid #1b2638; vertical-align: top; }}
td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
.resumen th {{ width: 40%; color: #b4bfd3; font-weight: 600; }}
.rejilla {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0 20px; }}
figure {{ margin: 12px 0; }} figcaption {{ font-size: 12px; color: #b4bfd3; }}
svg {{ width: 100%; height: auto; background: #0f1626; border-radius: 6px; }}
.eje {{ stroke: #2a3a58; }} .et {{ fill: #8fa0bd; font-size: 10px; }}
.nota {{ color: #8fa0bd; font-size: 12px; }}
.bitacora {{ max-height: 520px; overflow: auto; }}
.narracion li {{ margin: 3px 0; }} summary {{ cursor: pointer; color: #5fe6ff; }}
@media print {{ body {{ background: #fff; color: #111; }} svg {{ background: #f4f6fa; }} .bitacora {{ max-height: none; }} }}
</style></head><body><main>
<h1>ARES-X · reporte de misión</h1>
<p class="nota">Generado {_e(generado)}. Para reproducirla: semilla {_e(semilla)}, nivel {_e(nivel)}, planeta {_e(est.get('planeta', '-'))}.</p>
<h2>Resumen</h2><table class="resumen"><tbody>{resumen}</tbody></table>
<h2>Qué hizo cada técnica</h2>
<div class="rejilla">
{_tabla_conteos("RNA (vetos y riesgo)", t["rna"], "La RNA no vetó ni marcó riesgo.")}
{_tabla_conteos("Difuso (reglas más usadas)", t["difuso"], "Sin reglas registradas.")}
{_tabla_conteos("AG (replanteos)", t["ag"], "Sin replanteos por evento.", f"Replanteos de la misión: {est.get('replanes', '-')} (incluye los de rutina, al visitar un sitio). Abajo, los que dejaron motivo en la bitácora.")}
{_tabla_conteos("Supervisor (vetos)", t["supervisor"], "Sin vetos del supervisor.")}
</div>
<h2>Evolución por paso</h2>{graficos}
<h2>Avisos de la misión</h2><ul>{avisos}</ul>
<h2>Narración paso a paso</h2>
<details><summary>{len(log)} pasos explicados por el narrador (desplegar)</summary><ol class="narracion">{narracion}</ol></details>
<h2>Bitácora ({len(hist)} acciones)</h2>
<div class="bitacora"><table><thead><tr><th>#</th><th>paso</th><th>modo</th><th>acción</th><th>técnica</th><th>motivo</th><th>vel.</th><th>p(b)</th><th>bat.</th><th>reglas</th></tr></thead>
<tbody>{bitacora or "<tr><td colspan='10'>Sin acciones todavía.</td></tr>"}</tbody></table></div>
</main></body></html>"""
