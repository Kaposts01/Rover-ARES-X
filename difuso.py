"""ARES-X · Fase 3: controlador difuso Mamdani (min–max, centroide).

Entradas: distancia al riesgo (m), batería (%), inclinación (°).
Salida: velocidad en [0, 1]. Todos los rangos y funciones son supuestos de simulación.
"""
from dataclasses import dataclass

import numpy as np


def trapecio(x, a, b, c, d):
    """Membresía trapezoidal. Con b == a o c == d se obtienen formas de hombro."""
    x = np.asarray(x, dtype=float)
    izq = np.where(b > a, (x - a) / max(b - a, 1e-12), np.where(x >= b, 1.0, 0.0))
    der = np.where(d > c, (d - x) / max(d - c, 1e-12), np.where(x <= c, 1.0, 0.0))
    mu = np.minimum(izq, der)
    return np.clip(np.where((x >= a) & (x <= d), mu, 0.0), 0.0, 1.0)


def triangulo(x, a, b, c):
    return trapecio(x, a, b, b, c)


# Universos de discurso (supuestos de simulación)
DISTANCIA_MAX, BATERIA_MAX, INCLINACION_MAX = 20.0, 100.0, 45.0
TEMPERATURA_MIN, TEMPERATURA_MAX = -80.0, 80.0
TEMPERATURA_TOLERANCIA = 60.0   # °C: por encima, §12 pide abortar o aislar (supuesto de simulación)

# Conjuntos lingüísticos por variable (RF-05: tres por variable de entrada). R23: se definen por sus PUNTOS (trapecio de 4 puntos,
# triángulo de 3) para poder parametrizarlos; las funciones salen de los puntos y dan exactamente los mismos valores de antes.
PUNTOS_ENTRADA = {
    "distancia": {"cerca": [0, 0, 3, 6], "media": [4, 10, 16], "lejos": [12, 17, 20, 20]},
    "bateria": {"critica": [0, 0, 15, 30], "baja": [20, 40, 60], "alta": [50, 70, 100, 100]},
    "inclinacion": {"plana": [0, 0, 5, 12], "media": [8, 18, 28], "fuerte": [24, 32, 45, 45]},
    # ev3-d40 A: temperatura exterior en °C como cuarta entrada (§2, §10.2)
    "temperatura": {"fria": [-80, -80, -40, -20], "templada": [-40, -5, 30], "caliente": [10, 35, 80, 80]},
}
# Conjuntos de salida (velocidad 0..1)
PUNTOS_SALIDA = {
    "parar": [0.0, 0.0, 0.05, 0.15],
    "lenta": [0.1, 0.25, 0.4],
    "moderada": [0.35, 0.5, 0.65],
    "rapida": [0.6, 0.8, 1.0, 1.0],
}


def funcion_de_puntos(pts):
    """Función de pertenencia de un conjunto dado por sus puntos: 4 = trapecio, 3 = triángulo."""
    pts = [float(v) for v in pts]
    if len(pts) == 4:
        return lambda x: trapecio(x, *pts)
    return lambda x: triangulo(x, *pts)


CONJUNTOS = {var: {nombre: funcion_de_puntos(p) for nombre, p in etiquetas.items()}
             for var, etiquetas in PUNTOS_ENTRADA.items()}
SALIDA = {nombre: funcion_de_puntos(p) for nombre, p in PUNTOS_SALIDA.items()}

# Reglas documentadas (RF-05: al menos ocho). Operador Y = mínimo.
REGLAS = [
    {"id": "R1", "si": [("distancia", "cerca")], "entonces": "parar",
     "motivo": "Obstáculo o barranco muy cerca: detenerse."},
    {"id": "R2", "si": [("bateria", "critica")], "entonces": "lenta",
     "motivo": "Batería crítica: avanzar lento para ahorrar energía."},
    {"id": "R3", "si": [("inclinacion", "fuerte"), ("distancia", "media")], "entonces": "lenta",
     "motivo": "Pendiente fuerte con riesgo a distancia media: cautela."},
    {"id": "R4", "si": [("bateria", "alta"), ("inclinacion", "plana"), ("distancia", "lejos")],
     "entonces": "rapida", "motivo": "Condiciones ideales: velocidad máxima."},
    {"id": "R5", "si": [("bateria", "baja"), ("distancia", "lejos")], "entonces": "moderada",
     "motivo": "Batería baja pero camino libre: velocidad media."},
    {"id": "R6", "si": [("inclinacion", "media"), ("distancia", "lejos")], "entonces": "moderada",
     "motivo": "Pendiente media con camino libre."},
    {"id": "R7", "si": [("bateria", "alta"), ("distancia", "media")], "entonces": "moderada",
     "motivo": "Energía suficiente con riesgo a distancia media."},
    {"id": "R8", "si": [("inclinacion", "fuerte")], "entonces": "lenta",
     "motivo": "Pendiente fuerte: velocidad lenta para evitar vuelco."},
    {"id": "R10", "si": [("temperatura", "caliente")], "entonces": "moderada",
     "motivo": "Temperatura alta: el sobrecalentamiento obliga a moderar la marcha."},
    {"id": "R11", "si": [("temperatura", "fria"), ("bateria", "baja")], "entonces": "lenta",
     "motivo": "Frío con batería baja: se reduce la marcha para cuidar la energía."},
    {"id": "R9", "si": [("distancia", "media"), ("inclinacion", "plana")], "entonces": "moderada",
     "motivo": "Terreno plano con riesgo a distancia media."},
]

# ARX-80: columnas planas de la bitácora con los grados de membresía de cada paso (M3, RF-08)
COLUMNAS_MEMBRESIA = [f"mu_{var}_{conj}" for var, conjuntos in CONJUNTOS.items() for conj in conjuntos]


def aplanar_membresias(membresias) -> dict:
    """{variable: {conjunto: grado}} -> {"mu_variable_conjunto": grado}.

    Sin datos (None o vacío) o con un grado no finito el valor es None (celda vacía en el CSV): no se inventa 0.0.
    """
    plano = {}
    for col in COLUMNAS_MEMBRESIA:
        _, var, conj = col.split("_", 2)
        g = (membresias or {}).get(var, {}).get(conj)
        plano[col] = round(float(g), 4) if g is not None and np.isfinite(g) else None
    return plano


# Valor de salida cuando ninguna regla se activa (sección 12: fallback documentado)
SALIDA_FALLBACK = 0.0


@dataclass
class ResultadoDifuso:
    velocidad: float
    membresias: dict          # {variable: {conjunto: grado}}
    reglas_activadas: list    # [(id, fuerza, motivo)]
    agregado: np.ndarray      # conjunto de salida agregado
    universo: np.ndarray      # eje x de la salida
    fallback: bool


def _rango(var: str):
    return {
        "distancia": (0.0, DISTANCIA_MAX),
        "bateria": (0.0, BATERIA_MAX),
        "inclinacion": (0.0, INCLINACION_MAX),
        "temperatura": (TEMPERATURA_MIN, TEMPERATURA_MAX),
    }[var]


def _num(v, nombre):
    if isinstance(v, bool):
        raise ValueError(f"{nombre}: debe ser un número")
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre}: debe ser un número")
    if not np.isfinite(x):
        raise ValueError(f"{nombre}: debe ser un número finito")
    return x


def validar_puntos(pts, lo: float, hi: float, nombre: str) -> list:
    """Puntos de un conjunto (3 = triángulo, 4 = trapecio): números finitos, no decrecientes, dentro del universo."""
    if not isinstance(pts, (list, tuple)) or len(pts) not in (3, 4):
        raise ValueError(f"{nombre}: usa 3 puntos (triángulo) o 4 (trapecio)")
    v = [_num(x, nombre) for x in pts]
    if any(b < a for a, b in zip(v, v[1:])):
        raise ValueError(f"{nombre}: los puntos deben ir de menor a mayor")
    if v[0] >= v[-1]:
        raise ValueError(f"{nombre}: el conjunto no puede tener ancho cero")
    if v[0] < lo - 1e-9 or v[-1] > hi + 1e-9:
        raise ValueError(f"{nombre}: los puntos deben estar dentro del universo [{lo:g}, {hi:g}]")
    return v


def texto_regla(si, entonces) -> str:
    cond = " y ".join(f"{v} es {e}" for v, e in si)
    return f"Si {cond}, la velocidad es {entonces}"


class FuzzyController:
    """Controlador Mamdani. Sin `params` es el controlador por defecto (idéntico al de siempre). Con `params` (el mismo
    formato que PUT /difuso/reglas) cambia los puntos de las funciones de pertenencia y los pesos/estado de las reglas.

    `params`: {"variables": {var: {"etiquetas": {etiqueta: [puntos]}}}, "salida": {"etiquetas": {...}},
               "reglas": [{"id", "si": {var: etiqueta}, "entonces", "peso" 0..1, "activa"}]}.
    Las variables y etiquetas que no se nombran quedan como están; con `reglas` se da la lista completa de reglas
    (una regla ya existente puede darse solo con su id y los campos que cambian).
    """

    def __init__(self, resolucion: int = 201, params: dict = None):
        self.universo = np.linspace(0.0, 1.0, resolucion)
        self.entrada_pts = {v: {e: list(p) for e, p in et.items()} for v, et in PUNTOS_ENTRADA.items()}
        self.salida_pts = {e: list(p) for e, p in PUNTOS_SALIDA.items()}
        self.reglas = [{"id": r["id"], "si": list(r["si"]), "entonces": r["entonces"], "motivo": r["motivo"],
                        "peso": 1.0, "activa": True} for r in REGLAS]
        self.conjuntos = CONJUNTOS
        self.salida = SALIDA
        self.personalizado = False
        if params:
            self.aplicar(params)

    def copia(self) -> "FuzzyController":
        """Controlador nuevo con los mismos puntos y reglas (para editarlo sin tocar el original)."""
        c = FuzzyController(resolucion=len(self.universo))
        c.entrada_pts = {v: {e: list(p) for e, p in et.items()} for v, et in self.entrada_pts.items()}
        c.salida_pts = {e: list(p) for e, p in self.salida_pts.items()}
        c.reglas = [dict(r, si=list(r["si"])) for r in self.reglas]
        c.conjuntos = {v: {e: funcion_de_puntos(p) for e, p in et.items()} for v, et in c.entrada_pts.items()}
        c.salida = {e: funcion_de_puntos(p) for e, p in c.salida_pts.items()}
        c.personalizado = self.personalizado
        return c

    # ---------- parámetros ----------
    def aplicar(self, params: dict) -> None:
        """Valida y aplica `params` (ValueError con un mensaje claro si no es válido). Atómico: si falla, no cambia nada."""
        if not isinstance(params, dict):
            raise ValueError("los parámetros deben ser un objeto")
        entrada = {v: {e: list(p) for e, p in et.items()} for v, et in self.entrada_pts.items()}
        salida = {e: list(p) for e, p in self.salida_pts.items()}
        for var, datos in (params.get("variables") or {}).items():
            if var not in entrada:
                raise ValueError(f"variable desconocida: {var!r}; usa {sorted(entrada)}")
            lo, hi = _rango(var)
            for etiqueta, pts in ((datos or {}).get("etiquetas") or {}).items():
                if etiqueta not in entrada[var]:
                    raise ValueError(f"{var}: etiqueta desconocida {etiqueta!r}; usa {sorted(entrada[var])}")
                entrada[var][etiqueta] = validar_puntos(pts, lo, hi, f"{var}.{etiqueta}")
        for etiqueta, pts in ((params.get("salida") or {}).get("etiquetas") or {}).items():
            if etiqueta not in salida:
                raise ValueError(f"salida: etiqueta desconocida {etiqueta!r}; usa {sorted(salida)}")
            salida[etiqueta] = validar_puntos(pts, 0.0, 1.0, f"salida.{etiqueta}")
        reglas = [dict(r) for r in self.reglas]
        if "reglas" in params:
            lista = params["reglas"]
            if not isinstance(lista, list) or not lista:
                raise ValueError("reglas: debe ser una lista con al menos una regla")
            reglas, vistos = [], set()
            previas = {r["id"]: {**r, "si": list(r["si"]), "peso": 1.0} for r in REGLAS}      # las de fábrica, por id
            previas.update({r["id"]: r for r in self.reglas})
            for k, r in enumerate(lista):
                if not isinstance(r, dict) or not str(r.get("id", "")).strip():
                    raise ValueError(f"regla {k + 1}: falta el id")
                rid = str(r["id"]).strip()
                if len(rid) > 12 or rid in vistos:
                    raise ValueError(f"regla {rid!r}: id repetido o de más de 12 caracteres")
                vistos.add(rid)
                if "si" in r:
                    si = r["si"]
                    if not isinstance(si, dict) or not si:
                        raise ValueError(f"regla {rid}: «si» debe ser {{variable: etiqueta}} con al menos una condición")
                    cond = []
                    for var, et in si.items():
                        if var not in entrada or et not in entrada[var]:
                            raise ValueError(f"regla {rid}: condición desconocida {var} = {et!r}")
                        cond.append((var, et))
                else:
                    if rid not in previas:
                        raise ValueError(f"regla {rid}: una regla nueva necesita «si» y «entonces»")
                    cond = list(previas[rid]["si"])
                entonces = r.get("entonces", previas.get(rid, {}).get("entonces"))
                if entonces not in salida:
                    raise ValueError(f"regla {rid}: «entonces» debe ser una de {sorted(salida)}")
                peso = _num(r.get("peso", previas.get(rid, {}).get("peso", 1.0)), f"regla {rid}: peso")
                if not 0.0 <= peso <= 1.0:
                    raise ValueError(f"regla {rid}: el peso debe estar entre 0 y 1")
                activa = r.get("activa", True)
                if not isinstance(activa, bool):
                    raise ValueError(f"regla {rid}: «activa» debe ser verdadero o falso")
                reglas.append({"id": rid, "si": cond, "entonces": entonces, "peso": peso, "activa": activa,
                               "motivo": previas.get(rid, {}).get("motivo") or texto_regla(cond, entonces)})
            if not any(r["activa"] and r["peso"] > 0 for r in reglas):
                raise ValueError("reglas: al menos una regla debe estar activa y con peso mayor que 0")
        self.entrada_pts, self.salida_pts, self.reglas = entrada, salida, reglas
        self.conjuntos = {v: {e: funcion_de_puntos(p) for e, p in et.items()} for v, et in entrada.items()}
        self.salida = {e: funcion_de_puntos(p) for e, p in salida.items()}
        self.personalizado = True

    def como_dict(self) -> dict:
        """Estado del controlador en el formato de GET /difuso/reglas (y de `params`)."""
        return {
            "personalizadas": bool(self.personalizado),
            "variables": {v: {"universo": list(_rango(v)),
                              "etiquetas": {e: [float(x) for x in p] for e, p in et.items()}}
                          for v, et in self.entrada_pts.items()},
            "salida": {"universo": [0.0, 1.0], "etiquetas": {e: [float(x) for x in p] for e, p in self.salida_pts.items()}},
            "reglas": [{"id": r["id"], "si": {v: e for v, e in r["si"]}, "entonces": r["entonces"],
                        "peso": float(r["peso"]), "activa": bool(r["activa"]), "texto": texto_regla(r["si"], r["entonces"])}
                       for r in self.reglas],
        }

    def parametros_planos(self) -> dict:
        """Parámetros que difieren de los de defecto, como {nombre: valor} (para /ag/evolucion y los informes)."""
        planos = {}
        for v, et in self.entrada_pts.items():
            for e, p in et.items():
                if list(p) != list(PUNTOS_ENTRADA[v][e]):
                    planos[f"{v}.{e}"] = [round(float(x), 3) for x in p]
        for e, p in self.salida_pts.items():
            if list(p) != list(PUNTOS_SALIDA[e]):
                planos[f"salida.{e}"] = [round(float(x), 3) for x in p]
        base = {r["id"] for r in REGLAS}
        for r in self.reglas:
            if r["peso"] != 1.0 or not r["activa"] or r["id"] not in base:
                planos[f"regla.{r['id']}"] = round(float(r["peso"]), 3) if r["activa"] else 0.0
        return planos

    # ---------- inferencia ----------
    def fusificar_con(self, distancia, bateria, inclinacion, temperatura=0.0) -> dict:
        entradas = {"distancia": distancia, "bateria": bateria, "inclinacion": inclinacion,
                    "temperatura": temperatura}
        return {
            var: {nombre: float(f(np.clip(entradas[var], _rango(var)[0], _rango(var)[1])))
                  for nombre, f in self.conjuntos[var].items()}
            for var in self.conjuntos
        }

    @staticmethod
    def fusificar(distancia, bateria, inclinacion, temperatura=0.0) -> dict:
        entradas = {"distancia": distancia, "bateria": bateria, "inclinacion": inclinacion,
                    "temperatura": temperatura}
        return {
            var: {nombre: float(f(np.clip(entradas[var], _rango(var)[0], _rango(var)[1])))
                  for nombre, f in CONJUNTOS[var].items()}
            for var in CONJUNTOS
        }

    def inferir(self, distancia, bateria, inclinacion, temperatura=0.0) -> ResultadoDifuso:
        # RF-13: una entrada NaN no se propaga; se degrada a la salida fallback
        if any(np.isnan(v) for v in (distancia, bateria, inclinacion, temperatura)):
            mu = {var: {c: 0.0 for c in CONJUNTOS[var]} for var in CONJUNTOS}
            return ResultadoDifuso(velocidad=SALIDA_FALLBACK, membresias=mu, reglas_activadas=[],
                                   agregado=np.zeros_like(self.universo), universo=self.universo,
                                   fallback=True)
        mu = self.fusificar_con(distancia, bateria, inclinacion, temperatura)

        activaciones = {}          # conjunto de salida -> lista de fuerzas
        disparadas = []
        for regla in self.reglas:
            if not regla["activa"]:
                continue
            fuerza = min(mu[var][conj] for var, conj in regla["si"])
            if regla["peso"] != 1.0:
                fuerza = fuerza * regla["peso"]
            if fuerza > 0:
                disparadas.append((regla["id"], float(fuerza), regla["motivo"]))
                activaciones.setdefault(regla["entonces"], []).append(fuerza)

        agregado = np.zeros_like(self.universo)
        for conjunto, fuerzas in activaciones.items():
            recortado = np.minimum(max(fuerzas), self.salida[conjunto](self.universo))
            agregado = np.maximum(agregado, recortado)

        if agregado.sum() == 0:
            velocidad, fallback = SALIDA_FALLBACK, True
        else:
            velocidad = float(np.sum(self.universo * agregado) / np.sum(agregado))
            fallback = False

        return ResultadoDifuso(velocidad=velocidad, membresias=mu, reglas_activadas=disparadas,
                               agregado=agregado, universo=self.universo, fallback=fallback)
