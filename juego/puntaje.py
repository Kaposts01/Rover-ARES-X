"""Puntaje de la partida: la única fórmula (R23b). Lo usan `Partida.puntaje()`, el estado de la API, la comparación, los récords y el reporte.

Premia lo que importa de la misión y castiga lo que el supervisor (los vetos) existe para evitar. Un veto en sí no suma ni resta: antes
cada veto valía +50 y «ganaba» el híbrido por vetar más; ahora un veto solo se nota por lo que evita (menos choques, menos caídas).

    puntaje = 450 × ciencia (fracción 0 a 1) + 300 si la misión se cumple (EXITO)
              + 125 × batería final (fracción 0 a 1) + 125 × eficiencia en pasos (1 − pasos ÷ 400, mínimo 0)
              − 100 × choques − 150 × caídas a barranco − 20 × pasos sobre la tolerancia térmica
    (mínimo 0, entero). La batería y la eficiencia solo cuentan si se cumple la misión.

Justificación de los pesos: la ciencia es lo que se viene a hacer (45 %); cumplir la misión pesa 300 para que un fracaso (máximo 450) valga
claramente menos que cualquier misión cumplida (un éxito con ciencia baja de 0,5 ya da 525); batería y pasos son la eficiencia (12,5 % cada
uno, solo si hay éxito: la batería de una misión fallida o los pasos de una que no llegó no son mérito); un choque (100) o una caída (150)
cuestan más que lo que se gana por un sitio promedio (~45); 20 por paso sobre la tolerancia térmica (el aborto llega a los 8 pasos seguidos).
"""
from __future__ import annotations

PESO_CIENCIA = 450.0
BONO_MISION_CUMPLIDA = 300.0
PESO_BATERIA = 125.0
PESO_EFICIENCIA = 125.0
PASOS_REFERENCIA = 400                # el tope de pasos de una misión (juego.comparacion.MAX_PASOS): con 400 pasos la eficiencia es 0
CASTIGO_CHOQUE = 100.0
CASTIGO_CAIDA = 150.0
CASTIGO_PASO_SOBRE_TOLERANCIA = 20.0

FORMULA = ("450 × ciencia recogida (0 a 1) + 300 si se cumple la misión + 125 × batería final (0 a 1) + 125 × eficiencia en pasos "
           "(1 − pasos ÷ 400); la batería y los pasos solo cuentan si se cumple la misión; − 100 por choque − 150 por caída a barranco "
           "− 20 por paso sobre la tolerancia térmica; mínimo 0. Los vetos no suman ni restan.")


def _fraccion(v) -> float:
    try:
        return min(1.0, max(0.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def desglose(*, ciencia: float, exito: bool, bateria_pct: float, pasos: int, choques: int = 0, caidas: int = 0,
             pasos_sobre_tolerancia: int = 0) -> list:
    """Lista de términos `{clave, etiqueta, valor, peso, puntos}` (puntos con signo) en el orden en que se muestran."""
    ciencia = _fraccion(ciencia)
    bateria = _fraccion(float(bateria_pct or 0) / 100.0)
    eficiencia = _fraccion(1.0 - float(pasos or 0) / PASOS_REFERENCIA) if exito else 0.0
    ok = 1.0 if exito else 0.0

    def t(clave, etiqueta, valor, peso, signo=1):
        return {"clave": clave, "etiqueta": etiqueta, "valor": round(float(valor), 4), "peso": float(peso),
                "puntos": round(signo * float(valor) * float(peso), 2)}
    return [
        t("ciencia", "Ciencia recogida (0 a 1)", ciencia, PESO_CIENCIA),
        t("mision", "Misión cumplida (1 = sí)", ok, BONO_MISION_CUMPLIDA),
        t("bateria", "Batería final (0 a 1, solo si se cumple)", bateria * ok, PESO_BATERIA),
        t("eficiencia", "Eficiencia en pasos (0 a 1, solo si se cumple)", eficiencia, PESO_EFICIENCIA),
        t("choques", "Choques", int(choques or 0), CASTIGO_CHOQUE, -1),
        t("caidas", "Caídas a barranco", int(caidas or 0), CASTIGO_CAIDA, -1),
        t("tolerancia", "Pasos sobre la tolerancia térmica", int(pasos_sobre_tolerancia or 0), CASTIGO_PASO_SOBRE_TOLERANCIA, -1),
    ]


def total(terminos: list) -> int:
    """El puntaje: suma de los puntos, redondeada y acotada a ≥ 0."""
    return max(0, int(round(sum(x["puntos"] for x in terminos))))


def calcular(**datos) -> dict:
    """`{puntaje, desglose, formula}` a partir de los mismos argumentos que `desglose`."""
    d = desglose(**datos)
    return {"puntaje": total(d), "desglose": d, "formula": FORMULA}
