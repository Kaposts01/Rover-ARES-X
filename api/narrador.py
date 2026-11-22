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
    "AG-SIGUE-RUTA": "el AG siguió la ruta que había planificado",
    "RNA-MAX-PLIBRE": "la RNA eligió la celda que veía más libre",
    "D-VELOCIDAD-OK": "el difuso dio velocidad suficiente para avanzar",
    "D-VELOCIDAD-BAJA": "el difuso dio velocidad baja y se esperó",
    "D-RODEO": "el difuso rodeó el obstáculo",
    "D-SIN-CAMINO": "no había un camino libre hacia el objetivo",
    "D-SIN-CANDIDATO": "no había una celda candidata para avanzar",
    "D-FALLA-SENSOR": "un sensor estaba en falla",
    "D-SIN-ENLACE": "no había enlace con la base",
    "D-META-ALCANZADA": "se alcanzó la meta",
    "D-PARTIDA-TERMINADA": "la partida ya había terminado",
    "T-SOBRE-TOLERANCIA": "la temperatura interna estaba sobre la tolerancia",
    "REPLAN-RUTA-INCONSISTENTE": "la ruta dejó de ser coherente y se replanificó",
    "V-RODEO-SIN-CANDIDATO": "no había por dónde rodear el obstáculo",
    "V-SEGURIDAD-BARRANCO": "el supervisor vetó el avance por un barranco delante",
    "V-SEGURIDAD-OBSTACULO": "el supervisor vetó el avance por un obstáculo delante",
    "V-DISPARO-RIESGO": "el supervisor no dejó disparar porque la celda era de riesgo",
    "V-DISPARO-BATERIA-CRITICA": "el supervisor no dejó disparar por batería crítica",
    "V-DISPARO-MODO-SEGURO": "el supervisor no dejó disparar en modo seguro",
}
TEXTO_REGLA = {r["id"]: r["motivo"].rstrip(".") for r in REGLAS}
VERBO_ACCION = {"avanzar": "avanzó", "detener": "se detuvo", "replanificar": "replanificó", "modo_seguro": "entró en modo seguro",
                "mover": "se movió (manual)", "disparar": "disparó", "fin": "terminó la misión"}


def _pct(v) -> str:
    return f"{round(float(v) * 100):d} %"


def _vehiculo(vehiculo) -> str:
    """Vehículo de la partida con su artículo, para abrir la frase: «el rover» o «la sonda» (otro valor cae en rover)."""
    return "la sonda" if str(vehiculo or "").lower() == "sonda" else "el rover"


def narrar_fila(fila: dict, vehiculo: str = "rover") -> str:
    """Frase que explica el paso: qué vio la RNA, qué velocidad eligió el difuso y por qué, y qué decidió el supervisor.
    `vehiculo` es el de la partida («rover» o «sonda»): la frase usa su nombre real."""
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
        resto = len(reglas) - 1
        extra = "" if resto < 1 else (" y 1 regla más" if resto == 1 else f" y {resto} reglas más")
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
    cierre = f"{_vehiculo(vehiculo).capitalize()} {accion}"
    if explicaciones:
        cierre += ": " + "; ".join(explicaciones[:2])
    return f"Paso {fila.get('paso', '-')}. {frase}{cierre}."
