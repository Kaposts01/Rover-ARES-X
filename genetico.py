"""ARES-X · Fase 4: algoritmo genético de planificación (ev3-d01: K puntos de paso).

Cromosoma: K celdas (puntos de paso) dentro del mapa. Se decodifica a una ruta contigua
uniendo inicio → p1 → … → pK → refugio con BFS sobre el MAPA ESTIMADO (ev3-d02).
Reparación: si un tramo no tiene camino, el punto se descarta y se cuenta como reparación.

Subproblemas: laberinto (factibilidad del camino por BFS) y viajero (orden de visitas a sitios
científicos, que determina cuándo se obtiene cada valor).
Todos los pesos y costos son supuestos de simulación.
"""
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from simulador import BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, World

PESOS_POR_DEFECTO = {"ciencia": 1.0, "distancia": 0.3, "energia": 0.2,
                     "riesgo": 0.8, "tiempo": 0.1}
PENALIZACION_INVIABLE = 1.0     # P(inviabilidad) por violación dura
COSTO_BATERIA_PASO = 1.0        # % de batería por celda (supuesto de simulación)


def mapa_estimado(mundo: World, rng: np.random.Generator, p_detectar: float = 0.8,
                  p_prior: float = 0.05) -> np.ndarray:
    """Riesgo estimado por celda en [0, 1] que el rover construye con sus sensores.

    Un peligro detectado vale 1.0; uno no detectado queda con el prior bajo p_prior.
    Las celdas libres también tienen prior, porque el rover no conoce el mapa completo.
    """
    riesgo = np.full(mundo.forma, p_prior, dtype=float)
    peligros = np.argwhere(mundo.tipo != LIBRE)
    for f, c in peligros:
        if rng.random() < p_detectar:
            riesgo[f, c] = 1.0
    return riesgo


def camino_bfs(origen, destino, transitable):
    """Camino más corto en 8 direcciones, o None si no existe (laberinto)."""
    if origen == destino:
        return [origen]
    filas, columnas = transitable.shape
    # Mismo recorrido que antes (mismo orden de vecinos y de descubrimiento), pero sobre listas de Python:
    # indexar el array de numpy celda a celda era el cuello de botella (N3, rendimiento).
    tr = transitable.tolist()
    deltas = list(MOVIMIENTOS.values())
    previo = {origen: None}
    cola = deque([origen])
    while cola:
        ar, ac = cola.popleft()
        for df, dc in deltas:
            vr, vc = ar + df, ac + dc
            if not (0 <= vr < filas and 0 <= vc < columnas):
                continue
            vecino = (vr, vc)
            if vecino in previo or not tr[vr][vc]:
                continue
            previo[vecino] = (ar, ac)
            if vecino == destino:
                camino = [destino]
                while previo[camino[-1]] is not None:
                    camino.append(previo[camino[-1]])
                return camino[::-1]
            cola.append(vecino)
    return None


@dataclass
class Decodificacion:
    ruta: list
    reparaciones: int
    inviable_sin_camino: bool
    orden_sitios: list          # sitios científicos en el orden en que se visitan


@dataclass
class Desglose:
    fitness: float
    ciencia: float
    distancia: float
    energia: float
    riesgo: float
    tiempo: float
    penalizacion: float
    reparaciones: int
    ruta_pasos: int


@dataclass
class ResultadoAG:
    mejor: list
    mejor_desglose: Desglose
    mejor_ruta: list
    historial: list             # por generación: mejor y media de fitness
    candidatos: list = field(default_factory=list)   # top 3 distintos (cromosoma, desglose)


class GeneticPlanner:
    def __init__(self, mundo: World, riesgo: np.ndarray, bateria: float = 100.0,
                 k_puntos: int = 4, poblacion: int = 30, generaciones: int = 30,
                 prob_cruce: float = 0.8, prob_mutacion: float = 0.2, elite: int = 2,
                 torneo: int = 3, pesos=None, semilla: int = 42):
        if poblacion < 30 or generaciones < 30:
            raise ValueError("La consigna pide población ≥ 30 y generaciones ≥ 30.")
        self.mundo = mundo
        self.riesgo = riesgo
        self.bateria = bateria
        self.k = k_puntos
        self.poblacion = poblacion
        self.generaciones = generaciones
        self.prob_cruce = prob_cruce
        self.prob_mutacion = prob_mutacion
        self.elite = elite
        self.torneo = torneo
        self.pesos = {**PESOS_POR_DEFECTO, **(pesos or {})}
        self.cruces = 0                        # acumulados de todas las generaciones
        self.mutaciones = 0
        self.rng = np.random.default_rng(semilla)
        self.transitable = riesgo < 0.5   # el rover solo cruza lo que no estima peligroso
        self.transitable[mundo.inicio] = True
        self.transitable[mundo.refugio] = True
        self.pasos_maximos = mundo.forma[0] * mundo.forma[1]
        self.valor_total = sum(mundo.sitios.values()) or 1

    # ---------- decodificación ----------
    def _camino(self, origen, destino):
        """camino_bfs con caché por par de celdas: el mapa transitable no cambia dentro de un planificador (N3, rendimiento)."""
        cache = self.__dict__.setdefault("_cache_bfs", {})
        clave = (origen, destino)
        if clave not in cache:
            cache[clave] = camino_bfs(origen, destino, self.transitable)
        tramo = cache[clave]
        return None if tramo is None else list(tramo)

    def decodificar(self, cromosoma) -> Decodificacion:
        ruta = [self.mundo.inicio]
        reparaciones = 0
        visitados = []
        actual = self.mundo.inicio
        for punto in list(cromosoma) + [self.mundo.refugio]:
            if punto == actual:
                continue
            if punto == self.mundo.refugio:
                tramo = self._camino(actual, punto)
                if tramo is None:
                    return Decodificacion(ruta, reparaciones, True, visitados)
            else:
                tramo = self._camino(actual, punto)
                if tramo is None:        # reparación: descartar el punto
                    reparaciones += 1
                    continue
            ruta.extend(tramo[1:])
            actual = punto
            if punto in self.mundo.sitios and punto not in visitados:
                visitados.append(punto)
        return Decodificacion(ruta, reparaciones, False, visitados)

    # ---------- evaluación ----------
    def evaluar(self, cromosoma) -> Desglose:
        d = self.decodificar(cromosoma)
        pasos = len(d.ruta) - 1
        penal = d.reparaciones * 0.5 * PENALIZACION_INVIABLE
        if d.inviable_sin_camino:
            penal += PENALIZACION_INVIABLE
        if pasos * COSTO_BATERIA_PASO > self.bateria:
            penal += PENALIZACION_INVIABLE    # batería insuficiente para llegar a zona segura
        ciencia = sum(self.mundo.sitios[s] for s in d.orden_sitios) / self.valor_total
        dist = pasos / self.pasos_maximos
        energia = min(1.0, pasos * COSTO_BATERIA_PASO / self.bateria)
        riesgo = float(np.mean([self.riesgo[c] for c in d.ruta])) if d.ruta else 1.0
        giros = sum(1 for a, b, c in zip(d.ruta, d.ruta[1:], d.ruta[2:])
                    if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]))
        tiempo = giros / max(pasos, 1)
        w = self.pesos
        fitness = (w["ciencia"] * ciencia - w["distancia"] * dist - w["energia"] * energia
                   - w["riesgo"] * riesgo - w["tiempo"] * tiempo - penal)
        return Desglose(fitness, ciencia, dist, energia, riesgo, tiempo, penal,
                        d.reparaciones, pasos)

    # ---------- operadores ----------
    def _individuo_aleatorio(self):
        libres = np.argwhere(self.transitable)
        candidatos = list(self.mundo.sitios) + [tuple(p) for p in libres]
        idx = self.rng.choice(len(candidatos), size=self.k, replace=False)
        return [candidatos[i] for i in idx]

    def _seleccion(self, poblacion, fitness):
        indices = self.rng.choice(len(poblacion), size=self.torneo, replace=False)
        ganador = max(indices, key=lambda i: fitness[i])
        return list(poblacion[ganador])

    def _cruce(self, a, b):
        """Cruce de un punto: prefijo de a, sufijo de b."""
        if self.rng.random() > self.prob_cruce or self.k < 2:
            return list(a), list(b)
        punto = int(self.rng.integers(1, self.k))
        self.cruces += 1                       # operación efectiva de cruce (ARX-22)
        return a[:punto] + b[punto:], b[:punto] + a[punto:]

    def _mutar(self, individuo):
        ind = list(individuo)
        for i in range(self.k):
            if self.rng.random() < self.prob_mutacion:
                self.mutaciones += 1           # gen mutado (ARX-22)
                libres = np.argwhere(self.transitable)
                ind[i] = tuple(libres[self.rng.integers(len(libres))])
        return ind

    # ---------- bucle evolutivo ----------
    def optimizar(self, parada_sin_mejora: int = None) -> ResultadoAG:
        """Ejecuta el AG. `parada_sin_mejora=n` para si el mejor fitness no mejora en n generaciones (§12).

        Por defecto (None) corre todas las generaciones, como antes. El historial guarda por generación el
        mejor, la media, los 3 mejores y toda la población con su fitness y la operación que lo produjo
        (`elite`, `cruce` o `copia`, con marca de mutación si la hubo).
        """
        poblacion = [self._individuo_aleatorio() for _ in range(self.poblacion)]
        operaciones = ["inicial"] * len(poblacion)
        historial = []
        desgloses = {}
        mejor_visto, gen_mejora = -np.inf, 0

        for gen in range(self.generaciones):
            fitness = []
            for ind in poblacion:
                clave = tuple(ind)
                if clave not in desgloses:
                    desgloses[clave] = self.evaluar(ind)
                fitness.append(desgloses[clave].fitness)
            fitness = np.array(fitness)
            orden = np.argsort(-fitness)
            top = [{"cromosoma": [list(map(int, c)) for c in poblacion[i]], "fitness": float(fitness[i])}
                   for i in orden[:3]]
            poblacion_gen = [{"cromosoma": [list(map(int, c)) for c in poblacion[i]],
                              "fitness": float(fitness[i]), "operacion": operaciones[i]}
                             for i in range(len(poblacion))]
            historial.append({"generacion": gen, "mejor": float(fitness.max()),
                              "media": float(fitness.mean()), "peor": float(fitness.min()),
                              "top": top, "poblacion": poblacion_gen,
                              "cruces": 0, "mutaciones": 0})

            if fitness.max() > mejor_visto:
                mejor_visto, gen_mejora = float(fitness.max()), gen
            if parada_sin_mejora is not None and gen - gen_mejora >= parada_sin_mejora:
                break

            c0, m0 = self.cruces, self.mutaciones
            nueva = [list(poblacion[i]) for i in orden[:self.elite]]   # elitismo
            operaciones_nuevas = ["elite"] * len(nueva)
            while len(nueva) < self.poblacion:
                p1 = self._seleccion(poblacion, fitness)
                p2 = self._seleccion(poblacion, fitness)
                c_antes = self.cruces
                h1, h2 = self._cruce(p1, p2)
                op1 = "cruce" if self.cruces > c_antes else "copia"
                m_antes = self.mutaciones
                nueva.append(self._mutar(h1))
                operaciones_nuevas.append(op1 + ("+mutacion" if self.mutaciones > m_antes else ""))
                if len(nueva) < self.poblacion:
                    m_antes = self.mutaciones
                    nueva.append(self._mutar(h2))
                    operaciones_nuevas.append(op1 + ("+mutacion" if self.mutaciones > m_antes else ""))
            historial[-1]["cruces"] = self.cruces - c0
            historial[-1]["mutaciones"] = self.mutaciones - m0
            poblacion = nueva
            operaciones = operaciones_nuevas

        for ind in poblacion:
            clave = tuple(ind)
            if clave not in desgloses:
                desgloses[clave] = self.evaluar(ind)
        ordenados = sorted(desgloses.items(), key=lambda kv: -kv[1].fitness)
        mejor_clave, mejor_des = ordenados[0]
        mejor_ruta = self.decodificar(list(mejor_clave)).ruta
        candidatos = [(list(k), v) for k, v in ordenados[:3]]
        return ResultadoAG(mejor=list(mejor_clave), mejor_desglose=mejor_des,
                           mejor_ruta=mejor_ruta, historial=historial, candidatos=candidatos)
