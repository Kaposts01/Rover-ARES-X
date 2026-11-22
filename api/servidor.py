"""API FastAPI de ARES-X (ARX-03). Capa delgada sobre juego/partida.py.

Una sola partida por proceso, en memoria. Los errores siempre devuelven JSON con `motivo`:
400 si la entrada no es válida, 409 si la partida ya terminó o la acción no se puede hacer ahora.
Ninguna respuesta de error expone un traceback.

Ejecutar en desarrollo (desde ares_x/):  uvicorn api.servidor:app --reload
"""
import csv
import json
import io
import math
import os
import re
import secrets
import sys

import numpy as np
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from integracion import forzar_probabilidad  # noqa: E402
from juego import conduccion  # noqa: E402
from genetico import GeneticPlanner, PESOS_POR_DEFECTO  # noqa: E402
from difuso import BATERIA_MAX, COLUMNAS_MEMBRESIA, DISTANCIA_MAX, INCLINACION_MAX  # noqa: E402
from juego.partida import FILAS_BASE, COLUMNAS_BASE  # noqa: E402
from juego.combate import ALCANCE_DISPARO, Combate, distancia  # noqa: E402
from juego.partida import Partida, METODO_ORDEN, bateria_por_defecto  # noqa: E402
from juego import termico  # noqa: E402
from simulador import MOVIMIENTOS  # noqa: E402

MODOS = {"manual", "rna", "difuso", "ag", "automatico"}
RUMBOS = {"N", "S", "E", "O", "NE", "NO", "SE", "SO"}
EVENTOS = {"barranco", "falla_sensor", "bateria_baja", "tormenta", "noche", "meteorito", "sismo", "baja_conectividad", "senal_biologica"}
ESTADOS_TERMINALES = {"EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"}
CARPETA_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
RADIO_EVASION = 3           # drones a esta distancia o menos activan la decisión de combate en automático


class ErrorApi(Exception):
    def __init__(self, status: int, motivo: str):
        self.status = status
        self.motivo = motivo


class Sesion:
    """Estado de la partida que sirve la API (uno por proceso)."""

    def __init__(self, semilla: int = 11, nivel: int = 1, filas: int = FILAS_BASE, columnas: int = COLUMNAS_BASE,
                 planeta: str = "Marte", bateria: float = None):
        self.partida = Partida(semilla=semilla, nivel=nivel, filas=filas, columnas=columnas, planeta=planeta,
                               bateria=bateria)   # ARX-83b; ARX-87
        # el combate se crea después; se engancha para contar los drones destruidos en la victoria

        self.semilla = semilla
        self.nivel = nivel
        self.modo = "manual"
        self.combate = Combate(mundo=self.partida.mundo, rover=self.partida.rover, semilla=semilla)
        self.partida.combate = self.combate
        self.intervencion = None      # {tecnica, valor} mientras esté activa
        self.veto = True              # veto de seguridad en los modos rna/difuso/ag (ARX-11)
        self.historial = []           # una fila por acción del jugador o de la IA (ARX-15)
        self.n = 0                    # contador de filas del historial
        self.pesos_ag = None          # ARX-47a: pesos del fitness del laboratorio /ag (None = los de defecto); no afecta al juego

    def terminada(self) -> bool:
        return self.partida.estado in ESTADOS_TERMINALES

    def exigir_activa(self):
        if self.terminada():
            raise ErrorApi(409, f"la partida ya terminó con estado {self.partida.estado}")


class PartidaIn(BaseModel):
    # Se valida a mano (validar_partida) para devolver un motivo legible; sin semilla, el backend elige una.
    semilla: Any = None
    nivel: Any = 1
    tamano: Any = "grande"      # ARX-21: pequeno (20x30, el de las evaluaciones), mediano (30x45) o grande (40x60)
    planeta: Any = "Marte"      # ev3-d39 B: planeta del escenario (validación; el terreno es el de Marte hasta el sprint 3)
    modo: Any = "rover"         # "rover" o "sonda"
    bateria: Any = None          # ARX-87: batería inicial opcional, entre el 50 y el 150 % del valor por defecto


SEMILLA_MAX = 2 ** 31 - 1
# ARX-53: nombres de los niveles (pedido del usuario, 2026-11-14); los números 1 a 5 siguen valiendo
NIVELES_POR_NOMBRE = {"muy_facil": 1, "muy facil": 1, "muy fácil": 1, "facil": 2, "fácil": 2,
                      "medio": 3, "dificil": 4, "difícil": 4, "hardcore": 5}
SEMILLA_ALEATORIA_MAX = 10 ** 6      # semillas aleatorias: 0 a 999999, fáciles de anotar para repetir


TAMANOS = {"pequeno": (20, 30), "mediano": (30, 45), "grande": (40, 60)}


def _tamano(nombre) -> tuple:
    """ARX-21: nombre del tamaño del mapa → (filas, columnas). Entrada inválida → 400 legible."""
    if nombre is None:
        return TAMANOS["grande"]
    if not isinstance(nombre, str) or nombre.strip().lower() not in TAMANOS:
        raise ErrorApi(400, "tamaño inválido: usa pequeno, mediano o grande")
    return TAMANOS[nombre.strip().lower()]


def _validar_planeta(planeta, modo) -> None:
    """CA-07: rover de ruedas en un gigante → 400 con la explicación y la sugerencia de modo sonda."""
    from simulador import validar_compatibilidad, PERFILES
    if not isinstance(planeta, str) or not isinstance(modo, str):
        raise ErrorApi(400, "planeta y modo deben ser texto")
    try:
        validar_compatibilidad(planeta, modo)
    except ValueError as exc:
        sugerencia = None
        if planeta in PERFILES and modo == "rover":
            sugerencia = "usa modo sonda para este planeta"
        raise ErrorApi(400, str(exc) + (f" Sugerencia: {sugerencia}." if sugerencia else ""))


def _bateria_inicial(valor, nivel, filas, columnas):
    """ARX-87: None si no hay campo; si lo hay, debe ser un número entre el 50 y el 150 % de la batería por defecto del
    nivel y el tamaño. Fuera de rango o no numérico: 422 con el motivo."""
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise ErrorApi(422, "batería inicial: escribe un número")
    try:
        b = float(valor)
    except (TypeError, ValueError):
        raise ErrorApi(422, "batería inicial: escribe un número")
    if not math.isfinite(b):
        raise ErrorApi(422, "batería inicial: escribe un número")
    defecto = bateria_por_defecto(nivel, filas, columnas)
    bajo, alto = 0.5 * defecto, 1.5 * defecto
    if not bajo <= b <= alto:
        raise ErrorApi(422, f"batería inicial fuera del 50–150 % del valor por defecto ({bajo:.0f}–{alto:.0f}) "
                            f"para el nivel {nivel} y el tamaño {filas}×{columnas}")
    return b


def validar_partida(datos: "PartidaIn") -> tuple:
    """Devuelve (semilla, nivel) válidos o lanza ErrorApi(400) con un motivo legible (ARX-14)."""
    s = datos.semilla
    if s is None or (isinstance(s, str) and s.strip().lower() in ("", "aleatoria", "aleatorio", "random")):
        semilla = secrets.randbelow(SEMILLA_ALEATORIA_MAX)
    else:
        mensaje_semilla = ("semilla inválida: escribe un número entero entre 0 y %d, o deja el campo vacío "
                           "para una semilla aleatoria" % SEMILLA_MAX)
        if isinstance(s, bool):
            raise ErrorApi(400, mensaje_semilla)
        if isinstance(s, str):
            texto = s.strip()
            if not re.fullmatch(r"\d+", texto):
                raise ErrorApi(400, mensaje_semilla)
            s = int(texto)
        elif isinstance(s, float):
            if not math.isfinite(s) or not s.is_integer():
                raise ErrorApi(400, mensaje_semilla)
            s = int(s)
        elif not isinstance(s, int):
            raise ErrorApi(400, mensaje_semilla)
        if not 0 <= s <= SEMILLA_MAX:
            raise ErrorApi(400, mensaje_semilla)
        semilla = s
    _validar_planeta(datos.planeta, datos.modo)
    n = datos.nivel
    mensaje_nivel = ("nivel inválido: usa un número entero entre 1 y 5, o un nombre: "
                     "muy_facil, facil, medio, dificil, hardcore")
    if isinstance(n, bool):
        raise ErrorApi(400, mensaje_nivel)
    if isinstance(n, str):
        texto = n.strip().lower()
        if texto in NIVELES_POR_NOMBRE:
            n = NIVELES_POR_NOMBRE[texto]
        elif re.fullmatch(r"\d+", texto or "x"):
            n = int(texto)
    if not isinstance(n, int) or not 1 <= n <= 5:
        raise ErrorApi(400, mensaje_nivel)
    return semilla, n


class MoverIn(BaseModel):
    rumbo: str


class ModoIn(BaseModel):
    modo: str
    veto: Any = None                # opcional: bool; sin valor se conserva el actual


class DisparoIn(BaseModel):
    rumbo: str


class EventoIn(BaseModel):
    nombre: str


class IntervencionIn(BaseModel):
    tecnica: str                    # "rna", "difuso" o "apagar"
    valor: Any = None   # rna: barranco|libre|obstaculo; difuso: número 0..1 (sin conversión previa)


def _celda(c) -> list:
    """Coordenada como enteros de Python (los numpy.int64 no se serializan a JSON)."""
    return [int(c[0]), int(c[1])]


def _ultimo_replanteo(p) -> dict:
    """ARX-31b: {paso, motivo} del último replanteo del AG por un evento grave (fila REPLAN-AG-* de la bitácora), o None."""
    for fila in reversed(p.mision.log.filas):
        motivos = str(fila.get("motivos", ""))
        if motivos.startswith("REPLAN-AG-"):
            return {"paso": int(fila["paso"]), "motivo": motivos}
    return None


def _sensores(p) -> dict:
    """ARX-86: lecturas de los sensores en el rumbo actual y riesgo estimado de la celda de enfrente. Usa copias del
    sensor (no consume el ruido real de la partida). Durante una falla de sensor las lecturas son None (sin llamar a
    _observar) y cualquier valor no finito pasa a None (QA: NaN rompía el JSON)."""
    def finito(x, ndigitos=2):
        return None if x is None or not math.isfinite(float(x)) else round(float(x), ndigitos)

    rumbo = p.rover.rumbo or "N"
    df, dc = MOVIMIENTOS[rumbo]
    f, c = p.rover.posicion[0] + df, p.rover.posicion[1] + dc
    riesgo = None
    if 0 <= f < p.mision.riesgo.shape[0] and 0 <= c < p.mision.riesgo.shape[1]:
        riesgo = finito(p.mision.riesgo[f, c])
    falla = bool(p._falla_restante > 0)
    rasgos = None
    if not falla:
        obs = conduccion._observar(p)
        rasgos = (obs.get(rumbo) or next(iter(obs.values())))["rasgos"]
    # ARX-94 (QA O-5): nombres reales de los 4 rasgos según el modelo activo (v1: borde/gradiente; v2: desnivel/contraste)
    rna = p.mision.rna
    rna = rna._rna if hasattr(rna, "_rna") else rna
    return {"rumbo": p.rover.rumbo or "sin rumbo",
            "rasgos_nombres": list(getattr(rna, "nombres", [])),
            "proximidad": None if rasgos is None else finito(rasgos[0]),
            "borde": None if rasgos is None else finito(rasgos[1]),
            "gradiente": None if rasgos is None else finito(rasgos[2]),
            "vibracion": None if rasgos is None else finito(rasgos[3]),
            "riesgo_enfrente": riesgo,
            "falla": falla}


def _estado(sesion: Sesion) -> dict:
    p = sesion.partida
    sug = p.sugerencia()
    res = p.resumen()
    return {
        "semilla": sesion.semilla,
        "nivel": sesion.nivel,
        "planeta": getattr(sesion, "planeta", "Marte"),
        "modo_planeta": getattr(sesion, "modo_planeta", "rover"),
        "estado": p.estado_visible(),
        "posicion": _celda(p.rover.posicion),
        "rumbo": p.rover.rumbo,
        "bateria": round(float(p.rover.bateria), 2),
        "bateria_max": p.bateria_max,                # ARX-59: None en las evaluaciones congeladas
        "recargas": int(p.recargas_hechas),          # recargas completadas en la estación
        "puntaje": p.puntaje(),
        "modo": sesion.modo,
        "ambiente": p.ambiente,
        "ambiente_restante": p.ambiente_restante,
        "senal": _celda(p.senal_activa) if p.senal_activa is not None else None,   # ARX-30c: null si no hay o ya se visitó
        "enlace": {"activo": p.enlace_restante > 0, "restante": int(p.enlace_restante)},   # ARX-30b
        "objetivo": _celda(p.objetivo) if p.objetivo else None,
        "rumbo_sugerido": sug.get("rumbo"),
        "colisiones": res.get("colisiones", 0),
        "barrancos_pisados": res.get("barrancos_pisados", 0),
        "npcs": sesion.combate.npcs(),
        "eventos_combate": list(sesion.combate.eventos),
        "intervencion": sesion.intervencion,
        "veto": sesion.veto,
        "avisos": list(p.avisos),
        "ruta": [_celda(c) for c in (p.ruta or [])],
        "municion": sesion.combate.municion,
        "cooldown": sesion.combate.cooldown,
        "ultimo_replanteo": _ultimo_replanteo(p),    # ARX-31b: null si no hubo replanteo del AG
        "temperatura_interna": round(p.t_int, 2),    # ARX-83b: T_int en °C (modelo de PLAN_PLANETAS)
        "tolerancia": p.termico.tolerancia,    # ev3-d88 B: la tolerancia del planeta de la partida
        "aborto_termico_activo": termico.ABORTO_TERMICO_ACTIVO,    # O2 de QA: la interfaz aclara si el aborto está apagado
        "pasos_sobre_tolerancia": p.pasos_sobre_tolerancia,
        "sensores": _sensores(p),                    # ARX-86
        # Solo lectura, para la pantalla final (datos que el motor ya calcula)
        "paso": int(p.mision.paso),
        "vetos": int(p.mision.vetos),
        "replanes": int(p.mision.replanes),
        "sitios_visitados": int(res.get("sitios_visitados", 0)),
        "sitios_totales": int(res.get("sitios_totales", 0)),
        "distancia_recorrida": int(p.rover.distancia_recorrida),   # en celdas, sin escala en metros
        "barrancos_evitados": _barrancos_evitados(p),
    }


def _barrancos_evitados(p) -> int:
    """Filas de la bitácora cuyo motivo es un veto por barranco (V-BORDE-BARRANCO o V-RNA-BARRANCO). Solo lectura."""
    n = 0
    for fila in p.mision.log.filas:
        motivos = str(fila.get("motivos") or "")
        if "V-BORDE-BARRANCO" in motivos or "V-RNA-BARRANCO" in motivos:
            n += 1
    return n


def _ultimo_disparo(sesion: Sesion, motivos: list) -> dict:
    """`ultimo` de un disparo: mismo formato que un movimiento (paso, accion, motivos). Un disparo no avanza la misión
    ni escribe en su bitácora, así que el paso es el de la misión y los sensores van en blanco."""
    tiro = getattr(sesion.combate, "ultimo_disparo", None) or {}
    return {"paso": int(sesion.partida.mision.paso), "accion": "disparar", "velocidad": None,
            "p_barranco": None, "p_obstaculo": None, "p_libre": None, "reglas": [], "motivos": list(motivos),
            "rumbo": tiro.get("rumbo"), "objetivo": tiro.get("objetivo")}


def _ultimo_paso(sesion: Sesion) -> dict:
    """Lo que hizo la IA en el último paso (bitácora real, incluye la intervención activa)."""
    bitacora = sesion.partida.bitacora()
    if bitacora.empty:
        return {}
    fila = bitacora.iloc[-1]

    def num(x):
        return None if x is None or x != x else float(x)   # None o NaN -> None

    pb, po = num(fila.get("p_barranco")), num(fila.get("p_obstaculo"))
    reglas = [r for r in str(fila.get("reglas") or "").split(";") if r]
    motivos = [m for m in str(fila.get("motivos") or "").split(";") if m]
    return {
        "paso": int(fila.get("paso")),
        "accion": fila.get("accion"),
        "velocidad": num(fila.get("velocidad")),
        "p_barranco": pb,
        "p_obstaculo": po,
        "p_libre": None if pb is None or po is None else round(max(0.0, 1.0 - pb - po), 3),
        "reglas": reglas,
        "motivos": motivos,
    }


def _difuso_del_paso(ultimo, sesion, base) -> dict:
    """QA ARX-88: el difuso se considera usado si el paso mostrado activó reglas del difuso. Sin pasos, se usa el modo
    de la sesión (rna y ag no mueven con el difuso)."""
    fuente = ultimo or base          # sin pasos, la sugerencia actual (base) es la fuente de velocidad y reglas
    if ultimo:
        usado = bool(ultimo.get("reglas"))
    else:
        usado = sesion.modo not in ("rna", "ag")
    if not usado:
        return {"usado": False, "velocidad": None, "reglas": None}
    return {"usado": True, "velocidad": fuente.get("velocidad"), "reglas": fuente.get("reglas")}


def _paneles(sesion: Sesion) -> dict:
    """Entradas y salidas de cada técnica en el último paso; si no hay pasos, la sugerencia actual."""
    sug = sesion.partida.sugerencia()
    ultimo = _ultimo_paso(sesion)
    base = ultimo if ultimo else {
        "p_libre": sug.get("p_libre"), "p_obstaculo": sug.get("p_obstaculo"),
        "p_barranco": sug.get("p_barranco"), "velocidad": sug.get("velocidad"),
        "reglas": sug.get("reglas"), "accion": sug.get("accion"), "motivos": sug.get("motivos"),
    }
    return {
        "rna": {"p_libre": base.get("p_libre"), "p_obstaculo": base.get("p_obstaculo"),
                "p_barranco": base.get("p_barranco")},
        # rna y ag no usan el difuso para moverse: se muestra «no usado», no una velocidad 0 (ARX-18.3)
        # QA ARX-88: «usado» sale del paso mostrado (hubo reglas del difuso en ese paso), no del modo actual de la sesión
        "difuso": _difuso_del_paso(ultimo, sesion, base),
        "ag": {"ruta_planeada": [_celda(c) for c in (sesion.partida.ruta or [])],
               "desglose": sug.get("desglose")},
        "supervisor": {"accion": base.get("accion"), "motivos": base.get("motivos")},
        "intervencion": sesion.intervencion,
        "paso": ultimo.get("paso") if ultimo else None,
    }


def _turno(sesion: Sesion, previos: list = ()):
    """Un turno de combate: los drones actúan y, si el rover se queda sin batería, la partida termina.

    `previos` son los eventos de la acción que ocupó el turno (p. ej. un disparo). tick() vacía la lista
    de eventos, así que se reinyectan delante para que la respuesta muestre también el impacto.
    """
    sesion.combate.tick()
    sesion.combate.eventos = list(previos) + sesion.combate.eventos
    if sesion.partida.rover.bateria <= 0 and not sesion.terminada():
        sesion.partida.mision.estado = "FRACASO"


def _exigir_enlace(sesion: Sesion) -> None:
    """ARX-30b (ev3-d48 A): con el enlace cortado no hay recomendaciones ni intervenciones (409)."""
    if sesion.partida.enlace_restante > 0:
        raise ErrorApi(409, f"sin enlace: faltan {sesion.partida.enlace_restante} pasos para recuperarlo")


def _disparo_en_linea(sesion: Sesion):
    """ARX-75: disparo para los modos rna, difuso y ag. Si un dron está cerca, en línea recta y en alcance, con
    munición y sin enfriamiento, dispara (D-DISPARO-DRON). No evade ni replanifica: la técnica conduce el rover.
    Devuelve (si_disparó, motivos)."""
    c = sesion.combate
    p = sesion.partida
    r = p.rover.posicion
    cercanos = c.drones_cerca(RADIO_EVASION)
    if not cercanos:
        return False, []
    dron = min(cercanos, key=lambda d: distancia(d.pos, r))
    df, dc = dron.pos[0] - r[0], dron.pos[1] - r[1]
    en_linea = (df, dc) != (0, 0) and (df == 0 or dc == 0 or abs(df) == abs(dc))
    paso = (int(np.sign(df)), int(np.sign(dc))) if en_linea else None
    rumbo = next((k for k, v in MOVIMIENTOS.items() if v == paso), None) if paso else None
    if rumbo is not None and distancia(dron.pos, r) <= ALCANCE_DISPARO and c.cooldown == 0 and c.municion > 0:
        veto_motivo = _veto_disparo(sesion) if sesion.veto else None
        if veto_motivo:
            return False, [veto_motivo]
        c.eventos = []
        c.disparar(rumbo)
        c.ultimo_disparo = {"rumbo": rumbo, "objetivo": dron.id}
        return True, ["D-DISPARO-DRON"]
    return False, []


UMBRAL_RIESGO_DISPARO = 0.5    # celda de riesgo del mapa estimado a partir de la cual el supervisor veta el disparo
BATERIA_CRITICA_DISPARO = 15.0  # batería por debajo de la cual el supervisor veta el disparo


def _veto_disparo(sesion: Sesion):
    """ARX-75: motivo por el que el supervisor no deja disparar (riesgo, batería crítica o modo seguro), o None."""
    p = sesion.partida
    pos = tuple(int(v) for v in p.rover.posicion)
    if p.estado == "MODO_SEGURO" or p.rover.en_modo_seguro:
        return "V-DISPARO-MODO-SEGURO"
    if float(p.rover.bateria) < BATERIA_CRITICA_DISPARO:
        return "V-DISPARO-BATERIA-CRITICA"
    if float(p.mision.riesgo[pos]) >= UMBRAL_RIESGO_DISPARO:
        return "V-DISPARO-RIESGO"
    return None


def _decidir_combate_automatico(sesion: Sesion):
    """Capa de combate del modo automático (el supervisor congelado no conoce a los drones).

    Si un dron está cerca y el rover puede dispararle en línea recta, dispara (D-DISPARO-DRON).
    Si está cerca y no puede disparar, marca sus celdas vecinas como peligrosas y replanifica (V-DRON-CERCA).
    Devuelve (si_disparó, motivos).
    """
    c = sesion.combate
    p = sesion.partida
    r = p.rover.posicion
    cercanos = c.drones_cerca(RADIO_EVASION)
    if not cercanos:
        return False, []
    dron = min(cercanos, key=lambda d: distancia(d.pos, r))
    df, dc = dron.pos[0] - r[0], dron.pos[1] - r[1]
    # Un dron sobre el rover (df == dc == 0) no tiene rumbo de disparo: se evade, no se dispara.
    en_linea = (df, dc) != (0, 0) and (df == 0 or dc == 0 or abs(df) == abs(dc))
    paso = (int(np.sign(df)), int(np.sign(dc))) if en_linea else None
    rumbo = next((k for k, v in MOVIMIENTOS.items() if v == paso), None) if paso else None
    if rumbo is not None and distancia(dron.pos, r) <= ALCANCE_DISPARO and c.cooldown == 0 and c.municion > 0:
        c.eventos = []                      # solo los eventos de este disparo
        c.disparar(rumbo)
        c.ultimo_disparo = {"rumbo": rumbo, "objetivo": dron.id}
        return True, ["D-DISPARO-DRON"]
    # Evitar: solo la celda del dron cuenta como peligrosa para el plan, y se restaura después.
    # Marcar también sus vecinos puede cortar el único pasillo hacia el refugio (SIN_RUTA).
    mision = p.mision
    celdas = [d.pos for d in c.drones_cerca(RADIO_EVASION)]
    originales = {celda: mision.riesgo[celda] for celda in celdas}
    ruta_anterior = list(mision.ruta)
    for celda in celdas:
        mision.riesgo[celda] = 1.0
    try:
        mision._planear()
        if not mision.ruta:                 # sin ruta alternativa: se conserva el plan anterior
            mision.ruta = ruta_anterior
    finally:
        for celda, valor in originales.items():
            mision.riesgo[celda] = valor
    return False, ["V-DRON-CERCA"]


CAMPOS_HISTORIAL = ["n", "modo", "accion", "tecnica", "motivo", "paso_mision", "estado", "posicion", "bateria",
                    "velocidad", "p_libre", "p_obstaculo", "p_barranco", "reglas", "ruta_largo", "fitness",
                    "evento", "intervencion", "fitness_ag"] + COLUMNAS_MEMBRESIA     # ARX-80: fitness_ag y mu_* son nuevas
TECNICAS = {"humano", "rna", "difuso", "ag", "supervisor", "combate", "escenario"}


def _anotar(sesion: Sesion, accion: str, tecnica: str, motivos=(), ultimo: dict = None):
    """Añade una fila al historial con el estado después de la acción (ARX-15)."""
    p = sesion.partida
    u = ultimo or {}
    fitness = None
    if tecnica == "ag" and p.ruta:
        des = p.sugerencia().get("desglose")
        fitness = des.get("fitness") if des else None
    sesion.n += 1
    nuevas = _columnas_arx80(p)
    sesion.historial.append({
        "n": sesion.n, "modo": sesion.modo, "accion": accion, "tecnica": tecnica,
        "motivo": ";".join(m for m in motivos if m),
        "paso_mision": int(p.mision.paso), "estado": p.estado_visible(),   # ARX-33b: el mismo estado que /estado
        "posicion": _celda(p.rover.posicion), "bateria": round(float(p.rover.bateria), 2),
        "velocidad": u.get("velocidad"), "p_libre": u.get("p_libre"), "p_obstaculo": u.get("p_obstaculo"),
        "p_barranco": u.get("p_barranco"), "reglas": ";".join(u.get("reglas") or []),
        "ruta_largo": len(p.ruta or []), "fitness": fitness,
        "evento": ";".join(sesion.combate.eventos), "intervencion": (
            f"{sesion.intervencion['tecnica']}:{sesion.intervencion['valor']}" if sesion.intervencion else ""),
        **nuevas,
    })


def _columnas_arx80(p) -> dict:
    """ARX-80 (M3): fitness del AG y membresías difusas de la última fila de la bitácora (vacío si no hay dato)."""
    filas = p.mision.log.filas
    ultima = filas[-1] if filas else {}
    return {"fitness_ag": float(ultima.get("fitness_ag", 0.0)),
            **{c: ultima.get(c) for c in COLUMNAS_MEMBRESIA}}


def _filtrar_historial(sesion: Sesion, desde: int = 0, modo: str = None, tecnica: str = None,
                       motivo: str = None) -> list:
    filas = [f for f in sesion.historial if f["n"] >= desde]
    if modo:
        filas = [f for f in filas if f["modo"] == modo]
    if tecnica:
        filas = [f for f in filas if f["tecnica"] == tecnica]
    if motivo:
        filas = [f for f in filas if motivo in f["motivo"]]
    return filas


def _desglose_fitness(d) -> dict:
    """Desglose del fitness con los nombres de la consigna (inviabilidad = penalización por restricciones)."""
    return {"fitness": float(d.fitness), "ciencia": float(d.ciencia), "distancia": float(d.distancia),
            "energia": float(d.energia), "riesgo": float(d.riesgo), "tiempo": float(d.tiempo),
            "inviabilidad": float(d.penalizacion)}


def _valor_entrada(texto, nombre: str, minimo: float, maximo: float):
    """Valor numérico de una entrada manual del difuso; NaN, texto o fuera de rango → 400 legible."""
    if texto is None:
        return None
    try:
        v = float(texto)
    except (TypeError, ValueError):
        raise ErrorApi(400, f"{nombre} debe ser un número")
    if not math.isfinite(v):
        raise ErrorApi(400, f"{nombre} debe ser un número finito")
    if not minimo <= v <= maximo:
        raise ErrorApi(400, f"{nombre} fuera de rango [{minimo:g}, {maximo:g}]")
    return v


def _difuso_datos(sesion, distancia: float, bateria: float, inclinacion: float, temperatura: float = 0.0) -> dict:
    """Universos, curvas, punto de entrada, reglas y salida del difuso (CA-05, §10.2)."""
    from difuso import CONJUNTOS, REGLAS, SALIDA, TEMPERATURA_TOLERANCIA, _rango
    m = sesion.partida.mision
    res = m.difuso.inferir(distancia, bateria, inclinacion, temperatura)
    universos, curvas = {}, {}
    for var, conjuntos in CONJUNTOS.items():
        lo, hi = _rango(var)
        xs = np.linspace(lo, hi, 101)
        universos[var] = {"min": float(lo), "max": float(hi)}
        curvas[var] = {"x": [round(float(x), 3) for x in xs],
                       "conjuntos": {nombre: [round(float(f(x)), 4) for x in xs] for nombre, f in conjuntos.items()}}
    ys = np.linspace(0.0, 1.0, 101)
    return {
        "entradas": {"distancia": float(distancia), "bateria": float(bateria), "inclinacion": float(inclinacion),
                     "temperatura": float(temperatura)},
        "universos": universos,
        "curvas": curvas,
        "punto_entrada": {var: {c: round(float(g), 4) for c, g in res.membresias[var].items()}
                          for var in res.membresias},
        "reglas_activadas": [{"id": i, "fuerza": round(float(f), 4), "motivo": mo}
                             for i, f, mo in res.reglas_activadas],
        "aborto": ({"activo": True, "motivo": f"temperatura {temperatura:g} °C por encima de la tolerancia "
                                              f"({TEMPERATURA_TOLERANCIA:g} °C): abortar o aislar (§12)"}
                   if temperatura > TEMPERATURA_TOLERANCIA else {"activo": False, "motivo": None}),
        "reglas": [{"id": r["id"], "si": [list(c) for c in r["si"]], "entonces": r["entonces"],
                    "motivo": r["motivo"]} for r in REGLAS],
        "salida": {"velocidad": round(float(res.velocidad), 4), "fallback": bool(res.fallback),
                   "universo": [round(float(y), 3) for y in ys],
                   "conjuntos": {nombre: [round(float(f(y)), 4) for y in ys] for nombre, f in SALIDA.items()},
                   "agregado": [round(float(a), 4) for a in res.agregado] if res.agregado is not None else None},
    }


_cache_evaluacion_rna = {}
_cache_ag = {}
_cache_comparacion = {}
ESCENARIOS_COMPARACION = ("congelado", "exigente")   # ARX-28d; si el motor declara ESCENARIOS, manda el motor


PESO_MAX = 5.0


def _pesos_ag(sesion, pedidos: dict) -> dict:
    """Pesos del laboratorio /ag: los pedidos (validados en [0, 5]) sobre los de la sesión o los de defecto."""
    from genetico import PESOS_POR_DEFECTO
    pesos = dict(getattr(sesion, "pesos_ag", None) or PESOS_POR_DEFECTO)
    for nombre, crudo in pedidos.items():
        if crudo is None:
            continue
        try:
            v = float(crudo)
        except (TypeError, ValueError):
            raise ErrorApi(400, f"w_{nombre} debe ser un número entre 0 y {PESO_MAX:g}")
        if not 0.0 <= v <= PESO_MAX:   # también rechaza nan e inf
            raise ErrorApi(400, f"w_{nombre} debe estar entre 0 y {PESO_MAX:g} (recibido: {crudo!s:.20})")
        pesos[nombre] = v
    if any(c is not None for c in pedidos.values()):
        sesion.pesos_ag = dict(pesos)
    return pesos


def _escenarios_comparacion():
    try:
        from juego.comparacion import ESCENARIOS
        return tuple(ESCENARIOS)
    except ImportError:
        return ESCENARIOS_COMPARACION
COMPARACION_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "docs", "COMPARACION_POLITICAS.json")


# ARX-94d: parámetro de la consulta /rna, rango y rasgo del modelo al que corresponde
PARAMETROS_RNA = {
    "proximidad_frontal_m": ("proximidad", 0.0, 20.0),
    "desnivel_frontal_m": ("desnivel", -10.0, 10.0),
    "contraste_optico": ("contraste", -2.0, 2.0),
    "vibracion": ("vibracion", -5.0, 5.0),
    "borde_barranco": ("borde", 0.0, 1.0),
    "gradiente_altura_m": ("gradiente", -10.0, 10.0),
}


def _modelo_rna(sesion):
    """El NeuralPerception que usa la partida (la misión puede traerlo envuelto)."""
    r = sesion.partida.mision.rna
    return r._rna if hasattr(r, "_rna") else r


def _info_modelo(rna) -> dict:
    return {"perfil": getattr(rna, "perfil", None), "rasgos": list(rna.nombres)}


def _rna_entrada(sesion, entrada: dict) -> dict:
    """Entrada → normalización → activaciones de las capas → probabilidades → acción (CA-06, §10.1).

    `entrada` va por nombre de rasgo del modelo activo (v1 o v2). Las activaciones se calculan con los pesos
    del MLP (ReLU en las ocultas, softmax a la salida). La acción la decide el supervisor con los mismos valores.
    """
    from rna import CLASES
    m = sesion.partida.mision
    modelo = _modelo_rna(sesion)
    nn, esc = modelo.modelo, modelo.escalador
    nombres = list(modelo.nombres)
    x = np.asarray([entrada[k] for k in nombres], dtype=float)
    z = esc.transform(x.reshape(1, -1))[0]
    capas = [z]
    a = z
    for i, (W, b) in enumerate(zip(nn.coefs_, nn.intercepts_)):
        pre = a @ W + b
        a = np.maximum(pre, 0.0) if i < len(nn.coefs_) - 1 else pre
        capas.append(a)
    e = np.exp(capas[-1] - capas[-1].max())
    probs = e / e.sum()
    proba = {CLASES[c]: round(float(p), 4) for c, p in zip(nn.classes_, probs)}
    # altimetria_m no es entrada de la RNA: se pasa 0 para que el supervisor pueda decidir
    if "desnivel_frontal_m" in entrada:
        desnivel = float(entrada["desnivel_frontal_m"])
    else:
        desnivel = -3.0 if entrada.get("borde_barranco", 0.0) >= 0.5 else 0.0
    lectura = {"proximidad_frontal_m": float(entrada["proximidad_frontal_m"]), "altimetria_m": 0.0,
               "desnivel_frontal_m": desnivel}
    dec = m.supervisor.decidir({k: float(v) for k, v in zip(["libre", "obstáculo", "barranco"],
                                                             [proba.get("libre", 0), proba.get("obstáculo", 0),
                                                              proba.get("barranco", 0)])},
                               0.5, lectura, float(sesion.partida.rover.bateria))
    return {
        "modelo": _info_modelo(modelo),
        "entrada": dict(zip(nombres, [float(v) for v in x])),
        "normalizada": dict(zip(nombres, [round(float(v), 4) for v in z])),
        "activaciones": {"oculta_1": [round(float(v), 4) for v in capas[1]],
                         "oculta_2": [round(float(v), 4) for v in capas[2]],
                         "salida_logits": [round(float(v), 4) for v in capas[3]]},
        "probabilidades": proba,
        "confianza": round(float(probs.max()), 4),
        "accion": dec.accion,
        "motivos": list(dec.motivos),
    }


def _modelo_evaluacion(perfil: str):
    """(perfil resuelto, nombres de rasgos) del modelo a evaluar: el pedido o, sin pedido, el activo."""
    from rna import PERFILES_RASGOS, perfil_activo
    perfil = perfil or perfil_activo()
    if perfil not in ("v1", "v2"):
        raise ErrorApi(400, "perfil debe ser v1 o v2")
    return perfil, PERFILES_RASGOS[perfil]


def _evaluacion_rna_notebook(perfil: str = None) -> dict:
    """Evaluación reproducible del informe: 60 mapas (42/9/9), 400 muestras por mapa, prueba en los mapas 51-59.
    Es la misma configuración de construir_notebook.py. Se calcula una vez por proceso y perfil (v1 o v2)."""
    perfil, nombres = _modelo_evaluacion(perfil)
    if ("notebook", perfil) in _cache_evaluacion_rna:
        return _cache_evaluacion_rna[("notebook", perfil)]
    from rna import generar_dataset, particion_por_mapas, NeuralPerception, CLASES
    tr, _, te = particion_por_mapas(total_mapas=60)
    X_tr, y_tr = generar_dataset(tr, muestras_por_mapa=400, perfil=perfil)
    X_te, y_te = generar_dataset(te, muestras_por_mapa=400, perfil=perfil)
    res = NeuralPerception(semilla=42, nombres=nombres, perfil=perfil).entrenar(X_tr, y_tr).evaluar(X_te, y_te)
    datos = {
        "configuracion": "notebook: 60 mapas (42/9/9), 400 muestras por mapa, semilla 42",
        "perfil": perfil, "rasgos": list(nombres),
        "clases": [CLASES[c] for c in sorted(CLASES)],
        "matriz_confusion": res.matriz_confusion.tolist(),
        "macro_f1": round(float(res.macro_f1), 3),
        "recall_barranco": round(float(res.recall_barranco), 3),
        "error_calibracion": round(float(res.error_calibracion), 3),
        "linea_base_exactitud": round(float(res.precision_base), 3),
        "muestras_prueba": int(len(y_te)),
        "mapas_prueba": [int(v) for v in te],
    }
    _cache_evaluacion_rna[("notebook", perfil)] = datos
    return datos


def _evaluacion_rna(sesion, perfil: str = None) -> dict:
    """Matriz de confusión, macro-F1, recall de barrancos y línea base de la RNA del juego (CA-06).

    Usa los mapas de prueba de la misma partición con la que se entrena el modelo del juego
    (`integracion.rna_entrenada`: 30 mapas). Es distinta de la evaluación de 60 mapas del INFORME.
    Sin `perfil` evalúa el modelo de la partida; con `perfil` v1 o v2, el de ese perfil. Una vez por proceso.
    """
    from rna import generar_dataset, particion_por_mapas, CLASES
    from integracion import rna_entrenada
    modelo = _modelo_rna(sesion)
    perfil, nombres = _modelo_evaluacion(perfil or getattr(modelo, "perfil", None))
    if ("juego", perfil) in _cache_evaluacion_rna:
        return _cache_evaluacion_rna[("juego", perfil)]
    base = modelo if getattr(modelo, "perfil", None) == perfil else rna_entrenada(perfil=perfil)
    _, _, prueba = particion_por_mapas(total_mapas=30)
    X, y = generar_dataset(prueba, muestras_por_mapa=300, perfil=perfil)
    res = base.evaluar(X, y)
    datos = {
        "perfil": perfil, "rasgos": list(nombres),
        "clases": [CLASES[c] for c in sorted(CLASES)],
        "matriz_confusion": res.matriz_confusion.tolist(),
        "macro_f1": round(float(res.macro_f1), 4),
        "recall_barranco": round(float(res.recall_barranco), 4),
        "error_calibracion": round(float(res.error_calibracion), 4),
        "linea_base_exactitud": round(float(res.precision_base), 4),
        "muestras_prueba": int(len(y)),
        "mapas_prueba": [int(v) for v in prueba],
        "configuracion": "juego: 30 mapas (21/4/5), 300 muestras por mapa; modelo que usa la partida",
    }
    _cache_evaluacion_rna[("juego", perfil)] = datos
    return datos


def _valor_rango(texto, nombre: str, minimo: float, maximo: float, por_defecto: float) -> float:
    """Entrada manual de la RNA dentro de un rango; sin valor usa el por defecto de la lectura real."""
    if texto is None:
        return float(por_defecto)
    v = _valor_entrada(texto, nombre, minimo, maximo)
    return float(por_defecto) if v is None else float(v)


_RAZONES = {
    "RNA-MAX-PLIBRE": "la RNA ve la celda de enfrente como la más libre",
    "AG-SIGUE-RUTA": "el AG sigue la ruta que planificó",
    "D-VELOCIDAD-OK": "el difuso da velocidad suficiente",
    "D-VELOCIDAD-BAJA": "el difuso da velocidad baja: conviene esperar",
    "D-RODEO": "el difuso rodea el obstáculo",
    "OK": "no hay peligro en la siguiente celda",
    "REPLAN-SIN-RUTA": "no hay ruta: conviene replanificar",
}


def _razon_corta(modelo: str, motivos: list, accion) -> str:
    """Una razón corta en español para la recomendación (ARX-55)."""
    for m in motivos:
        if m in _RAZONES:
            return _RAZONES[m]
    if motivos and motivos[0].startswith("V-"):
        return f"la supervisión veta el paso ({motivos[0]})"
    if accion == "detener":
        return "conviene detenerse"
    if accion == "replanificar":
        return "conviene replanificar la ruta"
    return f"{modelo} propone {accion}" if accion else f"{modelo} no tiene propuesta"


def _rumbo_entre(a, b) -> str | None:
    """Nombre del rumbo (N, NE...) de la celda a a la b, o None si no hay movimiento."""
    from simulador import MOVIMIENTOS
    paso = (b[0] - a[0], b[1] - a[1])
    for nombre, delta in MOVIMIENTOS.items():
        if tuple(delta) == paso:
            return nombre
    return None


def _validar_rumbo(rumbo: str):
    if rumbo not in RUMBOS:
        raise ErrorApi(400, f"rumbo inválido: {rumbo!r}; usa uno de {sorted(RUMBOS)}")


def crear_app(sesion: Sesion = None) -> FastAPI:
    """Sin `sesion` la app arranca sin partida: la página muestra el menú y crea la partida con POST /partida."""
    app = FastAPI(title="ARES-X API", version="0.3.0")
    app.state.sesion = sesion

    def activa() -> Sesion:
        if app.state.sesion is None:
            raise ErrorApi(409, "sin partida: crea una con POST /partida")
        return app.state.sesion

    @app.exception_handler(ErrorApi)
    async def _error_api(request: Request, exc: ErrorApi):
        return JSONResponse(status_code=exc.status, content={"ok": False, "motivo": exc.motivo})

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"ok": False, "motivo": "entrada inválida",
                                                      "detalle": exc.errors()[:3]})

    @app.exception_handler(Exception)
    async def _error_interno(request: Request, exc: Exception):
        # Nunca se devuelve un traceback al cliente; el detalle queda fuera de la respuesta.
        return JSONResponse(status_code=500, content={"ok": False, "motivo": "error interno"})

    app.mount("/static", StaticFiles(directory=CARPETA_STATIC), name="static")

    @app.middleware("http")
    async def _sin_cache_interfaz(request: Request, call_next):
        # O11: la interfaz se corrige a menudo; el navegador debe revalidar y no usar módulos JS viejos
        respuesta = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta

    @app.get("/")
    def pagina():
        return FileResponse(os.path.join(CARPETA_STATIC, "index.html"))

    @app.get("/mapa")
    def mapa():
        """Terreno de la partida actual para dibujar la escena (no cambia la partida)."""
        mundo = activa().partida.mundo
        return {
            "filas": int(mundo.tipo.shape[0]),
            "columnas": int(mundo.tipo.shape[1]),
            "tipo": mundo.tipo.tolist(),
            "inicio": _celda(mundo.inicio),
            "refugio": _celda(mundo.refugio),
            "sitios": [{"pos": _celda(p), "valor": int(v)} for p, v in mundo.sitios.items()],
            "estaciones": [[int(f), int(c)] for f, c in activa().partida.estaciones],   # ARX-59 (§14)
            "riesgo_estimado": np.round(np.asarray(activa().partida.mision.riesgo, dtype=float), 2).tolist(),   # ARX-86
            "observada": np.asarray(activa().partida.mision.observadas, dtype=int).tolist(),   # Paquete A: solo registro
        }

    @app.get("/estado")
    def estado():
        """Nunca responde 500 por un submódulo: si algo falla, entrega lo que tiene y un campo `error`.
        La traza completa queda en la consola del servidor."""
        if app.state.sesion is None:
            return {"sin_partida": True, "motivo": "sin partida: pulsa Iniciar partida"}
        sesion = app.state.sesion
        try:
            return _estado(sesion)
        except Exception as exc:
            import logging
            logging.getLogger("ares_x").exception("fallo al construir /estado")
            p = sesion.partida
            return {"semilla": sesion.semilla, "nivel": sesion.nivel, "estado": p.estado,
                    "posicion": _celda(p.rover.posicion), "bateria": round(float(p.rover.bateria), 2),
                    "modo": sesion.modo, "error": {"tipo": type(exc).__name__,
                                                  "motivo": "error en un submódulo; ver la consola del servidor"}}

    @app.post("/partida")
    def nueva_partida(datos: PartidaIn):
        semilla, nivel = validar_partida(datos)
        try:
            filas, columnas = _tamano(datos.tamano)
            bateria = _bateria_inicial(datos.bateria, nivel, filas, columnas)   # ARX-87
            app.state.sesion = Sesion(semilla=semilla, nivel=nivel, filas=filas, columnas=columnas,
                                       planeta=datos.planeta, bateria=bateria)
            app.state.sesion.planeta = datos.planeta
            app.state.sesion.modo_planeta = datos.modo
        except ValueError as exc:
            raise ErrorApi(400, str(exc))
        return _estado(app.state.sesion)

    @app.post("/mover")
    def mover(datos: MoverIn):
        sesion = activa()
        _validar_rumbo(datos.rumbo)
        sesion.exigir_activa()
        r = sesion.partida.mover_jugador(datos.rumbo)
        sin_enlace = r.get("motivo") == "sin enlace"      # ARX-30b: la orden se perdió, pero el tiempo pasó
        if r.get("movido") or sin_enlace:
            _turno(sesion)
        _anotar(sesion, "mover" if r.get("movido") else ("sin_enlace" if sin_enlace else "bloqueado"),
                "humano", [r.get("motivo")])
        return {"movido": bool(r.get("movido")), "motivo": r.get("motivo"),
                "estado": sesion.partida.estado_visible(), "eventos_combate": list(sesion.combate.eventos)}

    @app.post("/paso")
    def paso():
        sesion = activa()
        sesion.exigir_activa()
        motivos_combate = []
        if sesion.modo in conduccion.MODOS_CONDUCCION:
            # Modos sueltos (ARX-11): la técnica elegida conduce el rover sola; con un dron en línea, dispara (ARX-75)
            disparo_hecho, motivos_disparo = _disparo_en_linea(sesion)
            if disparo_hecho:
                _turno(sesion, previos=list(sesion.combate.eventos))
                _anotar(sesion, "disparar", sesion.modo, motivos_disparo)
                return {"accion": "disparar", "motivos": motivos_disparo,
                        "estado": sesion.partida.estado_visible(), "ultimo": _ultimo_disparo(sesion, motivos_disparo),
                        "eventos_combate": list(sesion.combate.eventos)}
            r = sesion.partida.avanzar_modo(sesion.modo, sesion.veto)
            motivos = motivos_disparo + r.get("motivos", [])   # el veto del disparo también queda anotado (ARX-75)
            _turno(sesion)
            _anotar(sesion, r.get("accion"), sesion.modo, motivos, _ultimo_paso(sesion))
            return {"accion": r.get("accion"), "motivos": motivos,
                    "estado": sesion.partida.estado_visible(), "ultimo": _ultimo_paso(sesion),
                    "eventos_combate": list(sesion.combate.eventos)}
        if sesion.modo == "automatico":
            disparo_hecho, motivos_combate = _decidir_combate_automatico(sesion)
            if disparo_hecho:
                # El turno lo ocupó el disparo; la IA no avanza en este paso
                disparo_eventos = list(sesion.combate.eventos)
                _turno(sesion, previos=disparo_eventos)
                _anotar(sesion, "disparar", "combate", motivos_combate)
                return {"accion": "disparar", "motivos": motivos_combate,
                        "estado": sesion.partida.estado_visible(), "ultimo": _ultimo_disparo(sesion, motivos_combate),
                        "eventos_combate": list(sesion.combate.eventos)}
        r = sesion.partida.avanzar_ia()
        _turno(sesion)
        ultimo = _ultimo_paso(sesion)
        # La acción y los motivos son los del paso real (incluye la intervención activa)
        motivos = ultimo.get("motivos", r.get("motivos", []))
        _anotar(sesion, ultimo.get("accion", r.get("accion")), "supervisor", motivos_combate + motivos, ultimo)
        return {"accion": ultimo.get("accion", r.get("accion")),
                "motivos": motivos_combate + motivos if motivos_combate else motivos,
                "estado": sesion.partida.estado_visible(), "ultimo": ultimo,
                "eventos_combate": list(sesion.combate.eventos)}

    @app.post("/modo")
    def modo(datos: ModoIn):
        sesion = activa()
        if datos.modo not in MODOS:
            raise ErrorApi(400, f"modo inválido: {datos.modo!r}; usa uno de {sorted(MODOS)}")
        if datos.veto is not None:
            if not isinstance(datos.veto, bool):
                raise ErrorApi(400, "veto debe ser true o false")
            sesion.veto = datos.veto
        sesion.modo = datos.modo
        sesion.partida.modo_ia = datos.modo
        return _estado(sesion)

    @app.post("/disparo")
    def disparo(datos: DisparoIn):
        sesion = activa()
        _validar_rumbo(datos.rumbo)
        sesion.exigir_activa()
        sesion.combate.eventos = []         # solo los eventos de este disparo
        try:
            res = sesion.combate.disparar(datos.rumbo)
        except ValueError as exc:
            raise ErrorApi(409, str(exc))
        disparo_eventos = list(sesion.combate.eventos)
        _turno(sesion, previos=disparo_eventos)
        _anotar(sesion, "disparar", "humano", [] if res.get("impacto") else ["sin impacto"])
        return {**res, "eventos_combate": list(sesion.combate.eventos)}

    @app.post("/evento")
    def evento(datos: EventoIn):
        sesion = activa()
        if datos.nombre not in EVENTOS:
            raise ErrorApi(400, f"evento inválido: {datos.nombre!r}; usa uno de {sorted(EVENTOS)}")
        sesion.exigir_activa()
        r = sesion.partida.disparar_evento(datos.nombre)
        _anotar(sesion, f"evento:{datos.nombre}", "escenario", [datos.nombre])
        return r

    @app.get("/ag")
    def diagnostico_ag(parada_sin_mejora: int = None, w_ciencia: str = None, w_distancia: str = None,
                       w_energia: str = None, w_riesgo: str = None, w_tiempo: str = None):
        """Diagnóstico del AG sobre los sitios pendientes (CA-04, RF-11): historial por generación con
        cromosomas, fitness y operación; los 3 mejores con su desglose; cruces y mutaciones efectivas.
        `parada_sin_mejora=n` para tras n generaciones sin mejora (§12).
        `w_ciencia, w_distancia, w_energia, w_riesgo, w_tiempo` en [0, 5] cambian los pesos del fitness solo en este
        laboratorio (ARX-47a): se guardan en la sesión y se reutilizan. No cambia la partida."""
        sesion = activa()
        p = sesion.partida
        pesos = _pesos_ag(sesion, {"ciencia": w_ciencia, "distancia": w_distancia, "energia": w_energia,
                                   "riesgo": w_riesgo, "tiempo": w_tiempo})
        pendientes = {c: v for c, v in p.mundo.sitios.items() if c not in p.mision.visitados}
        if not pendientes:
            return {"sin_sitios": True, "motivo": "no quedan sitios científicos pendientes"}
        clave = (p.mision.semilla, tuple(sorted(pendientes)), tuple(p.rover.posicion),
                 p.mision.riesgo.tobytes(), parada_sin_mejora, tuple(sorted(pesos.items())))
        if clave in _cache_ag:
            return _cache_ag[clave]
        if parada_sin_mejora is not None and (isinstance(parada_sin_mejora, bool) or parada_sin_mejora < 1):
            raise ErrorApi(400, "parada_sin_mejora debe ser un entero mayor que 0")
        # ARX-92c: el laboratorio corre el MISMO AG sobre el orden que decide la partida (mismo envoltorio, pesos del lab)
        from juego.partida import (AG_ORDEN_CON_PASO, AVISO_FALLBACK, METODO_AG_ORDEN, UMBRAL_EMPATE,
                                   _ag_con_todos_los_sitios)
        envoltorio = _ag_con_todos_los_sitios(p.mision, lambda o, pe: [], pesos=dict(pesos),
                                              parada_sin_mejora=parada_sin_mejora)
        ruta_jugada = envoltorio(tuple(p.rover.posicion), pendientes)
        res = envoltorio.ultimo
        cae = bool(envoltorio.fallbacks)
        gp = envoltorio.gp
        candidatos = [{"cromosoma": [list(map(int, c)) for c in cr[0]],
                       "orden": [list(map(int, c)) for c in cr[0]],
                       "pasos": [None if q is None else list(map(int, q)) for q in cr[1]],
                       "fitness": float(d.fitness), "desglose": _desglose_fitness(d)}
                      for cr, d in res.candidatos]
        salida = {
            "modo": "orden",
            "parametros": {"poblacion": gp.poblacion, "generaciones": gp.generaciones, "k_puntos": gp.k,
                           "prob_cruce": gp.prob_cruce, "prob_mutacion": gp.prob_mutacion, "elite": gp.elite,
                           "torneo": gp.torneo, "semilla": p.mision.semilla, "pesos": gp.pesos,
                           "parada_sin_mejora": parada_sin_mejora, "umbral_empate": UMBRAL_EMPATE,
                           "punto_de_paso": AG_ORDEN_CON_PASO},
            "generaciones": res.historial,
            "candidatos": candidatos,
            "mejor_ruta": [_celda(c) for c in ruta_jugada],
            "mejor_desglose": _desglose_fitness(res.mejor_desglose),
            "cruces": gp.cruces, "mutaciones": gp.mutaciones,
            "generaciones_ejecutadas": len(res.historial),
            "viable": bool(res.viable), "ordenes_evaluados": res.evaluados,
            "fallback": AVISO_FALLBACK if cae else None,
            # El orden que juega la partida es el de este AG (92c); la vía b de 92a queda de respaldo declarado
            "orden_en_juego": {"metodo": METODO_AG_ORDEN, "respaldo": METODO_ORDEN,
                               "pesos": dict(getattr(p.mision, "pesos_ag", None) or PESOS_POR_DEFECTO)},
        }
        if len(_cache_ag) >= 16:
            _cache_ag.pop(next(iter(_cache_ag)))
        _cache_ag[clave] = salida
        return salida

    @app.get("/rna")
    def diagnostico_rna(proximidad: str = None, desnivel: str = None, contraste: str = None,
                        vibracion: str = None, borde: str = None, gradiente: str = None):
        """Laboratorio RNA (CA-06): entrada editable → normalización → activaciones → probabilidades → acción.
        Sin parámetros usa la celda de enfrente en el rumbo del rover. Responde con el modelo activo (`modelo`:
        perfil y lista de rasgos). v2: proximidad, desnivel, contraste, vibracion; v1: proximidad, borde,
        gradiente, vibracion. Todo parámetro dado se valida; solo cuentan los del modelo activo."""
        sesion = activa()
        p = sesion.partida
        from juego.conduccion import _observar
        obs = _observar(p)
        base = obs.get(p.rover.rumbo or "N") or next(iter(obs.values()))
        rasgos = base["rasgos"]
        dados = {"proximidad": proximidad, "desnivel": desnivel, "contraste": contraste,
                 "vibracion": vibracion, "borde": borde, "gradiente": gradiente}
        for param, lo, hi in PARAMETROS_RNA.values():
            if dados[param] is not None:
                _valor_entrada(dados[param], param, lo, hi)
        entrada = {}
        for i, clave in enumerate(_modelo_rna(sesion).nombres):
            param, lo, hi = PARAMETROS_RNA[clave]
            actual = rasgos[i]
            entrada[clave] = _valor_rango(dados[param], param, lo, hi, 0.0 if actual != actual else actual)
        return _rna_entrada(sesion, entrada)

    @app.get("/rna/red")
    def red_rna():
        """Forma y pesos del MLP que usa la partida, para dibujar la red en el panel (solo lectura).
        `capas`: neuronas por capa (entrada, ocultas, salida); `pesos[i]`: matriz capas[i] × capas[i+1], redondeada a 3
        decimales. Los pesos no cambian durante la partida: el panel la pide una vez y luego solo /rna."""
        from rna import CLASES
        modelo = _modelo_rna(activa())
        nn = modelo.modelo
        capas = [int(nn.coefs_[0].shape[0])] + [int(W.shape[1]) for W in nn.coefs_]
        return {
            "modelo": _info_modelo(modelo),
            "capas": capas,
            "clases": [CLASES[c] for c in nn.classes_],
            "pesos": [[[round(float(v), 3) for v in fila] for fila in W] for W in nn.coefs_],
        }

    @app.get("/rna/evaluacion")
    def evaluacion_rna(modelo: str = "notebook", perfil: str = None):
        """Matriz de confusión, macro-F1, recall de barrancos y línea base de la RNA (CA-06).
        `modelo=notebook` (por defecto): la cifra reproducible del informe. `modelo=juego`: el modelo que usa la partida.
        `perfil` (v1 o v2; sin él, el modelo activo); la respuesta lleva `perfil` y `rasgos`.
        La primera llamada de cada modelo tarda (entrena); después queda en caché."""
        if modelo == "notebook":
            return _evaluacion_rna_notebook(perfil)
        if modelo == "juego":
            return _evaluacion_rna(activa(), perfil)
        raise ErrorApi(400, "modelo debe ser notebook o juego")

    @app.get("/difuso")
    def diagnostico_difuso(distancia: str = None, bateria: str = None, inclinacion: str = None,
                           temperatura: str = None):
        """Laboratorio difuso (CA-05, §10.2). Sin parámetros usa el estado actual de la partida.
        Las entradas manuales son opcionales; NaN o fuera de rango → 400 con motivo."""
        sesion = activa()
        p = sesion.partida
        dist_actual = float(p.mision._distancia_a_riesgo_en_ruta())
        d = _valor_entrada(distancia, "distancia", 0.0, DISTANCIA_MAX)
        b = _valor_entrada(bateria, "bateria", 0.0, BATERIA_MAX)
        i = _valor_entrada(inclinacion, "inclinacion", 0.0, INCLINACION_MAX)
        t = _valor_entrada(temperatura, "temperatura", -80.0, 80.0)
        return _difuso_datos(sesion,
                             d if d is not None else min(dist_actual, DISTANCIA_MAX),
                             b if b is not None else float(p.rover.bateria),
                             i if i is not None else 0.0,
                             t if t is not None else 0.0)

    @app.get("/difuso/barrido")
    def barrido_difuso(desde: float = 10.0, hasta: float = 1.0, paso: float = 1.0, bateria: str = None,
                       inclinacion: str = None, temperatura: str = None):
        """Barrido de la distancia (CA-05: de 10 m a 1 m). Devuelve velocidad y reglas por cada valor."""
        sesion = activa()
        if not (math.isfinite(desde) and math.isfinite(hasta) and math.isfinite(paso)) or paso <= 0:
            raise ErrorApi(400, "desde, hasta y paso deben ser números finitos y el paso mayor que 0")
        if not (0.0 <= min(desde, hasta) and max(desde, hasta) <= DISTANCIA_MAX):
            raise ErrorApi(400, f"la distancia debe estar en [0, {DISTANCIA_MAX:g}]")
        if (abs(desde - hasta) / paso) > 200:
            raise ErrorApi(400, "barrido demasiado largo: como máximo 200 valores")
        b = _valor_entrada(bateria, "bateria", 0.0, BATERIA_MAX)
        i = _valor_entrada(inclinacion, "inclinacion", 0.0, INCLINACION_MAX)
        b = float(sesion.partida.rover.bateria) if b is None else b
        i = 0.0 if i is None else i
        t = _valor_entrada(temperatura, "temperatura", -80.0, 80.0)
        t = 0.0 if t is None else t
        n = int(round(abs(desde - hasta) / paso)) + 1
        valores = [desde + (hasta - desde) * k / (n - 1) for k in range(n)] if n > 1 else [desde]
        filas = []
        for d in valores:
            res = sesion.partida.mision.difuso.inferir(d, b, i, t)
            filas.append({"distancia": round(float(d), 3), "velocidad": round(float(res.velocidad), 4),
                          "fallback": bool(res.fallback),
                          "reglas": [{"id": r, "fuerza": round(float(f), 4)} for r, f, _ in res.reglas_activadas]})
        return {"bateria": b, "inclinacion": i, "temperatura": t, "filas": filas}

    @app.get("/moviles")
    def moviles():
        """Elementos móviles por paso (ARX-29): drones con su trayectoria, eventos del último turno y la ruta
        planificada frente a la ejecutada. Los obstáculos móviles llegarán en ARX-29; por ahora la lista de
        `obstaculos_moviles` va vacía."""
        sesion = activa()
        p = sesion.partida
        drones = []
        for n in sesion.combate.npcs():
            tray = sesion.combate.trayectorias.get(n["id"], [n["pos"]])
            drones.append({"id": f"dron-{n['id']}", "tipo": "dron", "pos": n["pos"], "trayectoria": tray,
                           "estado": n["estado"], "vida": n["vida"]})
        ejecutada = []
        for f in sesion.historial:
            pos = f["posicion"]
            if not ejecutada or ejecutada[-1] != pos:
                ejecutada.append(pos)
        actual = [int(p.rover.posicion[0]), int(p.rover.posicion[1])]
        if not ejecutada or ejecutada[-1] != actual:
            ejecutada.append(actual)
        # ARX-30 (borrador §10): los meteoritos van dentro de `moviles` y su evento en `eventos_del_paso`
        for m in p.meteoritos:
            f, c = m["impacto"]
            # caída de 3 puntos que termina en el impacto (aproximada en diagonal, dentro del mapa)
            trayectoria = [[max(0, f - k), max(0, c - k)] for k in (2, 1, 0)]
            drones.append({"id": f"meteorito-{m['paso']}", "tipo": "meteorito", "pos": _celda(m["impacto"]),
                           "trayectoria": trayectoria, "impacto": True,
                           "zona_riesgo": [_celda(z) for z in m["zona_riesgo"]]})
        eventos = [{"texto": e} for e in sesion.combate.eventos]
        eventos += [{"nombre": "meteorito", "efecto": "zona_riesgo", "celdas": [_celda(c) for c in m["zona_riesgo"]]}
                    for m in p.meteoritos if m["paso"] == int(p.mision.paso)]
        eventos += [{"nombre": "sismo", "efecto": "grietas", "celdas": [_celda(c) for c in s["grietas"]]}
                    for s in p.sismos if s["paso"] == int(p.mision.paso)]
        eventos += [{"nombre": "senal_biologica", "efecto": "lectura_anomala", "celdas": [_celda(s["celda"])],
                     "afirma_vida": False} for s in p.senales if s["paso"] == int(p.mision.paso)]
        replanteo = _ultimo_replanteo(p)
        if replanteo is not None and replanteo["paso"] == int(p.mision.paso):      # ARX-31b
            eventos.append({"nombre": "replanteo_ag", "motivo": replanteo["motivo"]})
        if p._ultimo_corte is not None and p._ultimo_corte == int(p.mision.paso):
            eventos.append({"nombre": "baja_conectividad", "efecto": "sin_enlace", "restante": int(p.enlace_restante)})
        return {
            "paso": int(p.mision.paso),
            "moviles": drones,
            "obstaculos_moviles": [],
            "eventos_del_paso": eventos,
            "ruta": {"planificada": [_celda(c) for c in (p.ruta or [])], "ejecutada": ejecutada},
        }

    @app.get("/recomendacion")
    def recomendacion():
        """ARX-55: el paso que propone cada modelo desde la posición actual, sin ejecutarlo en la partida real.

        Cada modelo corre sobre una copia de la partida. Modelos: hibrido (controlador completo), rna, difuso y ag.
        Sirve en modo manual, para que los modelos actúen como recomendadores (pedido del usuario, 2026-11-14).
        """
        import copy
        sesion = activa()
        p = sesion.partida
        if p.estado in ESTADOS_TERMINALES:
            raise ErrorApi(409, f"la partida ya terminó con estado {p.estado}")
        _exigir_enlace(sesion)
        pos0 = tuple(int(x) for x in p.rover.posicion)
        propuestas = []
        for modelo in ("hibrido", "rna", "difuso", "ag"):
            copia = copy.deepcopy(p)
            if modelo == "hibrido":
                r = copia.avanzar_ia()
            else:
                r = copia.avanzar_modo(modelo, sesion.veto)
            pos1 = tuple(int(x) for x in copia.rover.posicion)
            motivos = [m for m in (r.get("motivos") or []) if m]
            propuestas.append({
                "modelo": modelo,
                "accion": r.get("accion"),
                "rumbo": _rumbo_entre(pos0, pos1),
                "razon": _razon_corta(modelo, motivos, r.get("accion")),
                "motivos": motivos,
            })
        return {"posicion": list(pos0), "modo_actual": sesion.modo, "propuestas": propuestas}

    @app.get("/objetivos")
    def objetivos():
        """ARX-66: condiciones de victoria de la misión (esquema acordado con Diseño). Progreso real del motor:
        sitios científicos visitados y drones destruidos; llegar al refugio cumple la misión."""
        sesion = activa()
        p = sesion.partida
        total_sitios = len(p.mundo.sitios)
        visitados = len(p.mision.visitados)
        total_drones = len(sesion.combate.drones)
        destruidos = int(sesion.combate.bajas)
        condiciones = [
            {"nombre": "Sitios científicos", "progreso": visitados, "total": total_sitios,
             "cumplido": visitados >= total_sitios, "obligatorio": True},
            {"nombre": "Drones destruidos", "progreso": destruidos, "total": total_drones,
             "cumplido": destruidos >= total_drones, "obligatorio": p.drones_obligatorios()},
            {"nombre": "Llegar al refugio", "progreso": 1 if p.estado == "EXITO" else 0, "total": 1,
             "cumplido": p.estado == "EXITO", "obligatorio": True},
        ]
        nombres = {1: "muy fácil", 2: "fácil", 3: "medio", 4: "difícil", 5: "hardcore"}
        return {"mision": f"Visitar {total_sitios} sitios científicos y llegar al refugio (nivel {nombres.get(sesion.nivel, sesion.nivel)}).",
                "condiciones": condiciones}

    @app.get("/planetas")
    def planetas():
        """Planetas del escenario y su modo viable (ev3-d39 B, CA-07). El modo activo es el de la partida."""
        from simulador import PERFILES
        sesion = app.state.sesion
        lista = []
        for nombre, perfil in PERFILES.items():
            lista.append({"nombre": nombre, "modo": perfil.modo, "viable": perfil.modo == "rover",
                          "motivo": None if perfil.modo == "rover" else
                          f"{nombre} es un gigante sin suelo accesible: no admite rodaje; usa modo sonda"})
        activo = ({"planeta": getattr(sesion, "planeta", "Marte"), "modo": getattr(sesion, "modo_planeta", "rover")}
                  if sesion is not None else None)
        return {"planetas": lista, "modos": ["rover", "sonda"], "activo": activo}

    @app.get("/comparacion")
    def comparacion(semillas: int = 20, escenario: str = "congelado"):
        """Comparación de políticas (RF-14, RF-15): híbrido frente a sin RNA, sin difuso y sin AG.
        `escenario=congelado` (por defecto) o `exigente` (ARX-28d). Con 20 semillas sirve el JSON del escenario
        (docs/COMPARACION_POLITICAS.json o docs/COMPARACION_POLITICAS_<escenario>.json); otros valores calculan
        en la petición y tardan (1 a 40 semillas). La caché distingue escenario y número de semillas."""
        if isinstance(semillas, bool) or not 1 <= semillas <= 40:
            raise ErrorApi(400, "semillas debe ser un entero entre 1 y 40")
        validos = _escenarios_comparacion()
        if escenario not in validos:
            raise ErrorApi(400, "escenario debe ser uno de: " + ", ".join(validos)
                           + f" (recibido: {str(escenario)[:40]!r})")
        clave = (escenario, semillas)
        if clave in _cache_comparacion:
            return _cache_comparacion[clave]
        ruta = COMPARACION_JSON if escenario == "congelado" else COMPARACION_JSON.replace(
            ".json", f"_{escenario}.json")
        if semillas == 20 and os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        else:
            from juego import comparacion as motor
            if escenario == "congelado":
                datos = motor.comparar(range(1, semillas + 1))
            elif not hasattr(motor, "ESCENARIOS"):
                raise ErrorApi(400, f"el escenario {escenario} aún no está disponible en el motor de comparación")
            else:
                datos = motor.comparar(range(1, semillas + 1), escenario=escenario)
        # ev3-d71: ag_puro no se publica (no mide el AG); mismo criterio que scripts/comparacion_politicas.py
        no_publicar = ()   # ev3-d71 corregido: ag_puro se publica entre las ablaciones; ARX-92 regeneración
        datos = {**datos, "escenario": escenario,
                 "variantes": {v: r for v, r in datos["variantes"].items() if v not in no_publicar},
                 "filas": [f for f in datos["filas"] if f["variante"] not in no_publicar]}
        _cache_comparacion[clave] = datos
        return datos

    @app.get("/serie")
    def serie_por_paso(desde: int = 0):
        """Serie por paso para los gráficos en vivo: batería, velocidad difusa, acción y fitness de la ruta.
        El fitness por paso solo se registra en modo ag (null en los demás); el resto de filas no lo tiene."""
        sesion = activa()
        filas = [{"n": f["n"], "modo": f["modo"], "accion": f["accion"], "tecnica": f["tecnica"],
                  "bateria": f["bateria"], "velocidad": f["velocidad"], "p_libre": f["p_libre"],
                  "p_obstaculo": f["p_obstaculo"], "p_barranco": f["p_barranco"], "fitness": f["fitness"]}
                 for f in _filtrar_historial(sesion, desde)]
        return {"total": len(filas), "filas": filas,
                "nota": "fitness por paso: solo en modo ag; los demás modos devuelven null"}

    @app.get("/historial")
    def historial(desde: int = 0, modo: str = None, tecnica: str = None, motivo: str = None):
        """Historial de decisiones (Panel D de la consigna): una fila por acción, filtrable."""
        filas = _filtrar_historial(activa(), desde, modo, tecnica, motivo)
        return {"total": len(filas), "filas": filas}

    @app.get("/historial.csv")
    def historial_csv(desde: int = 0, modo: str = None, tecnica: str = None, motivo: str = None):
        """Exportación CSV del historial con las columnas de la bitácora (paso, estado, posición...) y las nuevas."""
        filas = _filtrar_historial(activa(), desde, modo, tecnica, motivo)
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=CAMPOS_HISTORIAL, extrasaction="ignore")
        w.writeheader()
        for f in filas:
            w.writerow({**f, "posicion": f"({f['posicion'][0]}, {f['posicion'][1]})"})
        return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=historial_decisiones.csv"})

    @app.get("/paneles")
    def paneles():
        datos = _paneles(activa())
        datos["sensores"] = _sensores(activa().partida)    # ARX-86: lo pinta el panel de supervisión
        return datos

    @app.post("/intervencion")
    def intervencion(datos: IntervencionIn):
        """Prueba causal (ARX-10): fuerza la salida de la RNA o del difuso en la misión de la partida."""
        _exigir_enlace(activa())
        mision = activa().partida.mision
        if datos.tecnica == "apagar":
            mision.intervencion_rna = None
            mision.intervencion_difuso = None
            activa().intervencion = None
            return {"ok": True, "tecnica": "apagar", "valor": None}
        if datos.tecnica == "rna":
            if datos.valor not in ("barranco", "libre", "obstaculo"):
                raise ErrorApi(400, "rna: valor debe ser barranco, libre u obstaculo")
            mision.intervencion_rna = forzar_probabilidad(datos.valor)
            activa().intervencion = {"tecnica": "rna", "valor": datos.valor}
            return {"ok": True, "tecnica": "rna", "valor": datos.valor}
        if datos.tecnica == "difuso":
            v = datos.valor
            # bool es subclase de int en Python: se rechaza de forma explícita
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.0 <= float(v) <= 1.0:
                raise ErrorApi(400, "difuso: valor debe ser un número entre 0 y 1")
            mision.intervencion_difuso = float(datos.valor)
            activa().intervencion = {"tecnica": "difuso", "valor": float(datos.valor)}
            return {"ok": True, "tecnica": "difuso", "valor": float(datos.valor)}
        raise ErrorApi(400, f"técnica inválida: {datos.tecnica!r}; usa rna, difuso o apagar")

    return app


app = crear_app()
