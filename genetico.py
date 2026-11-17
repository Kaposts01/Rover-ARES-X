"""ARES-X · Fase 4: algoritmo genético de planificación (ev3-d01: K puntos de paso).

Cromosoma: K celdas (puntos de paso) dentro del mapa. Se decodifica a una ruta contigua
uniendo inicio → p1 → … → pK → refugio con BFS sobre el MAPA ESTIMADO (ev3-d02).
Reparación: si un tramo no tiene camino, el punto se descarta; los sitios que la ruta no toca se
insertan en el mejor hueco (ARX-92b). Ambas cuentan como reparación y se exponen por separado.

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
    descartes: int = 0          # puntos sin camino descartados (reparación)
    insertados: int = 0         # sitios omitidos que la reparación añadió a la ruta (ARX-92b)


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
    descartes: int = 0
    insertados: int = 0


@dataclass
class ResultadoAG:
    mejor: list
    mejor_desglose: Desglose
    mejor_ruta: list
    historial: list             # por generación: mejor y media de fitness
    candidatos: list = field(default_factory=list)   # top 3 distintos (cromosoma, desglose)


_CACHE_DISTANCIAS = {}     # ARX-92b: (forma, mapa transitable, origen) -> (distancias, padres)


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
        """Mismo resultado que camino_bfs(origen, destino, transitable), sacado del árbol BFS del origen
        (ARX-92b, rendimiento: una BFS por origen en vez de una por par)."""
        if origen == destino:
            return [origen]
        dist, previo = self._distancias_desde(origen)
        if destino not in dist:
            return None
        camino = [destino]
        while previo[camino[-1]] is not None:
            camino.append(previo[camino[-1]])
        return camino[::-1]

    def _unir(self, paradas):
        """Une las paradas consecutivas con BFS; None si algún tramo no tiene camino."""
        ruta = [paradas[0]]
        for a, b in zip(paradas, paradas[1:]):
            if a == b:
                continue
            tramo = self._camino(a, b)
            if tramo is None:
                return None
            ruta.extend(tramo[1:])
        return ruta

    def _distancias_desde(self, origen):
        """ARX-92b (rendimiento, QA): BFS una vez por origen; devuelve ({celda: pasos}, {celda: padre}) de todo lo
        alcanzable. Mismas reglas que camino_bfs (8 direcciones, solo se entra en celdas transitables, el origen se
        expande siempre). La caché es compartida entre planificadores y se indexa por el mapa transitable exacto, así
        que un planificador nuevo sobre el mismo mapa no repite la BFS (el desglose por paso crea uno por paso)."""
        clave = (self.transitable.shape, self.transitable.tobytes(), tuple(origen))
        cache = _CACHE_DISTANCIAS
        if clave not in cache:
            if len(cache) >= 4096:
                cache.clear()
            filas, columnas = self.transitable.shape
            tr = self.transitable.tolist()
            deltas = list(MOVIMIENTOS.values())
            dist = {origen: 0}
            previo = {origen: None}     # padre en el árbol BFS: da la ruta igual que camino_bfs (mismo orden de descubrimiento)
            cola = deque([origen])
            while cola:
                ar, ac = cola.popleft()
                for df, dc in deltas:
                    vr, vc = ar + df, ac + dc
                    if not (0 <= vr < filas and 0 <= vc < columnas):
                        continue
                    vecino = (vr, vc)
                    if vecino in dist or not tr[vr][vc]:
                        continue
                    dist[vecino] = dist[(ar, ac)] + 1
                    previo[vecino] = (ar, ac)
                    cola.append(vecino)
            cache[clave] = (dist, previo)
        return cache[clave]

    def _largo(self, a, b):
        if a == b:
            return 0
        return self._distancias_desde(a)[0].get(b)

    def decodificar(self, cromosoma) -> Decodificacion:
        """Cromosoma → ruta contigua inicio → … → refugio que visita TODOS los sitios o es inviable (ARX-92b, M8).

        1) Une los puntos con BFS; un punto sin camino se descarta (reparación por descarte).
        2) Los sitios que la ruta no toca se insertan, uno a uno, en el hueco donde menos pasos añaden
           (antes del refugio incluido); cada inserción cuenta como reparación. Un sitio sin hueco
           alcanzable deja la decodificación como `inviable_sin_camino`.
        """
        mundo = self.mundo
        paradas = [mundo.inicio]
        descartes = 0
        for punto in list(cromosoma):
            if punto == paradas[-1] or punto == mundo.refugio:
                continue
            if self._largo(paradas[-1], punto) is None:
                descartes += 1
                continue
            paradas.append(punto)
        if self._largo(paradas[-1], mundo.refugio) is None:
            ruta = self._unir(paradas) or [mundo.inicio]
            return Decodificacion(ruta, descartes, True, self._sitios_en(ruta), descartes, 0)
        paradas.append(mundo.refugio)

        insertados = 0
        sin_camino = False
        ruta = self._unir(paradas)
        for sitio in list(mundo.sitios):
            if sitio in ruta:
                continue
            mejor = None
            for i in range(len(paradas) - 1):
                a, b = paradas[i], paradas[i + 1]
                ida, vuelta, directo = self._largo(a, sitio), self._largo(sitio, b), self._largo(a, b)
                if ida is None or vuelta is None or directo is None:
                    continue
                extra = ida + vuelta - directo
                if mejor is None or extra < mejor[0]:
                    mejor = (extra, i + 1)
            if mejor is None:
                sin_camino = True
                continue
            paradas.insert(mejor[1], sitio)
            insertados += 1
            ruta = self._unir(paradas)
        return Decodificacion(ruta, descartes + insertados, sin_camino, self._sitios_en(ruta),
                              descartes, insertados)

    def _sitios_en(self, ruta):
        """Sitios científicos por los que pasa la ruta, en orden de primera visita."""
        vistos = []
        for c in ruta:
            if c in self.mundo.sitios and c not in vistos:
                vistos.append(c)
        return vistos

    # ---------- evaluación ----------
    def evaluar(self, cromosoma) -> Desglose:
        d = self.decodificar(cromosoma)
        pasos = len(d.ruta) - 1
        penal = d.reparaciones * 0.5 * PENALIZACION_INVIABLE
        if d.inviable_sin_camino:
            penal += PENALIZACION_INVIABLE
        if pasos * COSTO_BATERIA_PASO > self.bateria:
            penal += PENALIZACION_INVIABLE    # batería insuficiente para llegar a zona segura
        return self._desglosar(d.ruta, d.orden_sitios, penal, d.reparaciones, d.descartes, d.insertados)

    def evaluar_ruta(self, ruta, bateria_total=None) -> Desglose:
        """ARX-92a: puntúa con el mismo fitness una ruta ya construida (con paradas de recarga incluidas) y viable.

        No hay reparaciones ni penalización: la viabilidad (batería con margen y factor) ya la validó quien la
        construyó. `bateria_total` es la capacidad con la que se normaliza la energía (por defecto, la del planificador).
        """
        ruta = [tuple(int(v) for v in c) for c in ruta]
        return self._desglosar(ruta, self._sitios_en(ruta), 0.0, 0, 0, 0, bateria_total)

    def _desglosar(self, ruta, orden_sitios, penal, reparaciones, descartes, insertados, bateria=None) -> Desglose:
        bateria = self.bateria if bateria is None else bateria
        pasos = len(ruta) - 1
        ciencia = sum(self.mundo.sitios[s] for s in orden_sitios) / self.valor_total
        dist = pasos / self.pasos_maximos
        energia = min(1.0, pasos * COSTO_BATERIA_PASO / bateria)
        riesgo = float(np.mean([self.riesgo[c] for c in ruta])) if ruta else 1.0
        giros = sum(1 for a, b, c in zip(ruta, ruta[1:], ruta[2:])
                    if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]))
        tiempo = giros / max(pasos, 1)
        w = self.pesos
        fitness = (w["ciencia"] * ciencia - w["distancia"] * dist - w["energia"] * energia
                   - w["riesgo"] * riesgo - w["tiempo"] * tiempo - penal)
        return Desglose(fitness, ciencia, dist, energia, riesgo, tiempo, penal,
                        reparaciones, pasos, descartes, insertados)

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
