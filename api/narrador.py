"""Narrador de pasos: explica en una o dos frases qué hizo cada técnica en un paso y por qué (auditoría 22/11).

Funciones puras sobre una fila de la bitácora del motor (paso, acción, velocidad, p_barranco, p_obstaculo, reglas,
motivos). No leen el estado de la partida ni cambian nada. Las usan GET /ia/paso y el reporte de la misión.
"""
from difuso import REGLAS

# Motivos del motor en lenguaje natural (los que no están aquí se muestran tal cual)
TEXTO_MOTIVO = {
    "OK": "el supervisor no encontró riesgos y dejó avanzar",
    "V-RUTA-CON-RIESGO": "la siguiente celda de la ruta ya estaba marcada como peligrosa, así que replanificó",
    "V-RNA-BARRANCO": "la RNA vio un barranco delante y el supervisor vetó el avance",
    "V-RNA-OBSTACULO": "la RNA vio un obstáculo delante y el supervisor vetó el avance",
    "V-BORDE-BARRANCO": "el telémetro midió un desnivel de barranco justo enfrente y vetó el avance",
    "V-OBSTACULO-EN-RUTA": "el sensor de proximidad vio un obstáculo sobre la ruta y replanificó",
    "V-PARADO-SIN-AVANCE": "llevaba varios pasos detenido y replanificó para no quedarse quieto",
    "V-CELDA-BLOQUEADA": "intentó pisar una celda que no se puede atravesar y la marcó en el mapa",
    "V-SENSOR-NAN": "un sensor falló y entró en modo seguro",
    "V-BATERIA-0": "se quedó sin batería",
    "V-TEMPERATURA": "la temperatura interna superó la tolerancia",
    "V-DRON-CERCA": "un dron enemigo estaba cerca",
    "RNA-RIESGO": "la RNA confirmó riesgo en la celda y la marcó en el mapa estimado",
    "REPLAN-RUTA-VACIA": "la ruta se terminó y el AG planificó la siguiente",
    "REPLAN-SIN-RUTA": "no quedaba ruta válida y replanificó",
    "REPLAN-SISMO": "un sismo abrió grietas en la ruta y replanificó",
    "REPLAN-AG-SISMO": "un sismo abrió grietas en la ruta y el AG recalculó el orden de visita",
    "REPLAN-AG-METEORITO": "un meteorito cayó cerca de la ruta y el AG recalculó el orden de visita",
    "D-RESBALON": "resbaló en una pendiente por ir rápido y volvió a la celda anterior",
    "D-DIFUSO-LENTO": "el difuso pidió ir tan lento que se detuvo",
    "D-DISPARO-DRON": "disparó a un dron en línea",
    "AG-FALLBACK-GARANTIA": "el AG no encontró un orden que cumpliera todo y usó el orden de respaldo",
}
TEXTO_REGLA = {r["id"]: r["motivo"].rstrip(".") for r in REGLAS}
VERBO_ACCION = {"avanzar": "avanzó", "detener": "se detuvo", "replanificar": "replanificó", "modo_seguro": "entró en modo seguro",
                "mover": "se movió (manual)", "disparar": "disparó", "fin": "terminó la misión"}


def _pct(v) -> str:
    return f"{round(float(v) * 100):d} %"


def narrar_fila(fila: dict) -> str:
    """Frase que explica el paso: qué vio la RNA, qué velocidad eligió el difuso y por qué, y qué decidió el supervisor."""
    if not fila:
        return "Todavía no hay pasos de la IA."
    partes = []
    pb, po = fila.get("p_barranco"), fila.get("p_obstaculo")
    if pb is not None and po is not None and pb == pb and po == po:
        pl = max(0.0, 1.0 - float(pb) - float(po))
        clase, p = max([("libre", pl), ("obstáculo", float(po)), ("barranco", float(pb))], key=lambda x: x[1])
        partes.append(f"La RNA vio la celda de enfrente como {clase} ({_pct(p)})")
    reglas = [r for r in str(fila.get("reglas") or "").split(";") if r]
    vel = fila.get("velocidad")
    if reglas and vel is not None:
        razon = TEXTO_REGLA.get(reglas[0], reglas[0]).lower()
        extra = f" y {len(reglas) - 1} regla(s) más" if len(reglas) > 1 else ""
        velocidad = f"{float(vel):.2f}".replace(".", ",")
        partes.append(f"el difuso fijó la velocidad en {velocidad} ({reglas[0]}: {razon}{extra})")
    motivos = [m for m in str(fila.get("motivos") or "").split(";") if m]
    accion = VERBO_ACCION.get(str(fila.get("accion") or ""), str(fila.get("accion") or "actuó"))
    explicaciones = []
    for m in motivos:
        base = m.split(":")[0]
        t = TEXTO_MOTIVO.get(base) or next((v for k, v in TEXTO_MOTIVO.items() if base.startswith(k)), None)
        if t and t not in explicaciones:
            explicaciones.append(t)
    frase = ", ".join(partes)
    if frase:
        frase = frase[0].upper() + frase[1:] + ". "
    cierre = f"El rover {accion}"
    if explicaciones:
        cierre += ": " + "; ".join(explicaciones[:2])
    return f"Paso {fila.get('paso', '-')}. {frase}{cierre}."
