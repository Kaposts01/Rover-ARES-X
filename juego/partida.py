"""ARES-X · Juego: motor de partida (agente M, contrato v2 en juego/CONTRATO_V2.md).

Envuelve Mision (integracion.py) sin modificar los módulos congelados. El jugador conduce con
mover_jugador(); la IA sugiere con sugerencia() (sin efectos) y ejecuta con avanzar_ia().
"""
import copy
import functools
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genetico import GeneticPlanner, camino_bfs  # noqa: E402
import anticipacion  # noqa: E402
import planificacion  # noqa: E402
from integracion import (ESTADOS_TERMINALES, MARGEN_ENERGIA,  # noqa: E402
                         GRADOS_POR_GRADIENTE, PASOS_PARADO_MAXIMO,
                         Decision, Mision, _rumbo, camino_valido)
from difuso import ResultadoDifuso, aplanar_membresias  # noqa: E402
from difuso import FuzzyController  # noqa: E402
from juego import dificultad, difuso_planetas, planetas, termico  # noqa: E402
from rna import _rasgos_celda, inclinacion_de_rasgos  # noqa: E402
from simulador import (BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, SensorSuite,  # noqa: E402
                       generar_mundo, paso_fisico)

PASOS_CAZA_SIN_AVANCE = 12   # ARX-79c: pasos seguidos sin salir de la celda durante la caza antes de fracasar con causa
EVENTOS_SOPORTADOS = ("barranco", "falla_sensor", "bateria_baja", "tormenta", "noche", "meteorito", "sismo", "baja_conectividad", "senal_biologica")
# ARX-31a: eventos graves ante los que el AG vuelve a planificar el orden de visita (ev3-d07 B: fuera de ellos, solo BFS).
# Mitigación de costo (plan §7, M2 de QA: ~3,5 s por replanteo del AG en 40x60): solo sismo (si la grieta toca la ruta)
# y señal biológica (siempre). Meteorito y barranco replanifican por BFS, como antes de 31a (riesgo y veto del motor).
# Como máximo un replanteo del AG por paso.
# Costo conocido: el replanteo con AG tarda unos 3,5 s en 40x60, solo con sismo que toca la ruta y con señal biológica
# (eventos raros). Población y generaciones se mantienen (M9 exige >= 30 y >= 30).
EVENTOS_GRAVES = ("sismo", "senal_biologica")
SENAL_DIST_MIN, SENAL_DIST_MAX = 3, 6    # distancia Chebyshev de la señal biológica al rover (ARX-30c)
# ARX-30c (ev3-d50 C): probabilidad por paso de que la señal caiga sola, por nivel (supuesto de simulación)
SENAL_PROB_POR_NIVEL = {1: 0.002, 2: 0.003, 3: 0.004, 4: 0.005, 5: 0.006}
TEXTO_SENAL = "Señal biológica anómala: lectura anómala, no confirma vida"   # ningún texto afirma vida
GRIETAS_POR_NIVEL = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}                           # grietas por sismo (supuesto de simulación, ARX-30)
SISMO_PROB_POR_NIVEL = {1: 0.003, 2: 0.004, 3: 0.006, 4: 0.007, 5: 0.009}   # probabilidad por paso (ARX-30)
METEORITO_PROB_POR_NIVEL = {1: 0.004, 2: 0.006, 3: 0.008, 4: 0.010, 5: 0.012}   # probabilidad por paso (ARX-30)
DANO_METEORITO = 5.0                    # % de batería que cuesta el impacto (supuesto de simulación, ARX-30)
PASOS_FALLA_SENSOR = 3
PASOS_SIN_ENLACE = 4                    # pasos que dura un corte de enlace (ev3-d48 A, ARX-30b)
PROB_ORDEN_PERDIDA = 0.5                # en manual, probabilidad de perder una orden de /mover durante el corte (ev3-d48 A)
ENLACE_PROB_POR_NIVEL = {1: 0.002, 2: 0.003, 3: 0.004, 4: 0.005, 5: 0.006}   # corte espontáneo por paso (supuesto de simulación)
BATERIA_BAJA = 15.0

# ARX-28c (ev3-d54 A): resbalón por velocidad en pendiente, solo con la bandera fisica_velocidad (escenario exigente).
# Constantes CONGELADAS por ev3-d69 A: no se ajustan tras ver cifras; la sensibilidad se publica aparte (rejilla 3x2).
INCLINACION_RESBALON = 20.0     # grados: sobre esta pendiente la tracción de las ruedas deja de ser segura (plan: «p. ej. 20°»)
P_RESBALON = 0.5                # probabilidad = P_RESBALON * velocidad: el riesgo de perder agarre crece con la velocidad
COSTO_RESBALON = 1.0            # % de batería: esfuerzo extra de las ruedas al patinar y reanudar el avance (supuesto)
VELOCIDAD_SIN_RESBALON = 0.3    # por debajo de esta velocidad el avance es lento y no resbala (plan: v < 0,3)

NIVEL_MAX = 5
# ARX-21: tamaño del mapa. 20x30 es el de las evaluaciones congeladas (informe y /comparacion).
FILAS_BASE, COLUMNAS_BASE = 20, 30
MIN_LADO, MAX_LADO = 10, 80
PROB_AMBIENTE = 0.03                         # probabilidad por paso de iniciar un ambiente
PASOS_AMBIENTE = {"tormenta": 6, "noche": 8}
COSTO_AMBIENTE = {"tormenta": 1.0, "noche": 0.5}   # % de batería extra por paso
COSTO_DIAGONAL = 1.0
DIAGONALES = {"NE": (-1, 1), "NO": (-1, -1), "SE": (1, 1), "SO": (1, -1)}
RUMBOS_JUGADOR = {**MOVIMIENTOS, **DIAGONALES}


class _MisionPlanDiferido(Mision):
    """Mision que no planifica al construirse: con el plan restringido la planificación inicial la hace Partida (el AG de
    `Mision.__init__`, con K puntos de paso, se descartaba de inmediato y con 8 a 12 sitios costaba 1,5 s). No modifica Mision."""
    plan_diferido = True

    def _planear(self):
        if self.plan_diferido:
            return False
        return super()._planear()


class _RnaSegura:
    """Envoltorio de la RNA: con una lectura NaN (sensor en fallo) no llama al MLP, que no admite NaN.

    Devuelve probabilidades neutras; el supervisor de Mision veta por V-SENSOR-NAN antes de usarlas.
    Para entradas válidas delega sin cambios. Resto de atributos: delegados a la RNA original.
    """

    def __init__(self, rna):
        self._rna = rna

    def explicar(self, rasgos):
        if any(np.isnan(v) for v in rasgos):
            return {"probabilidades": {"libre": 1.0, "obstáculo": 0.0, "barranco": 0.0}}
        return self._rna.explicar(rasgos)

    def __getattr__(self, nombre):
        # Sin esta guarda, copy.deepcopy llama a __getattr__ antes de que exista _rna y entra en recursión
        if nombre.startswith("__") or nombre == "_rna":
            raise AttributeError(nombre)
        return getattr(self._rna, nombre)


MARGEN_CAZA = 10   # suelo del margen de caza: pasos extra por dron obligatorio (persecución desde su zona de patrulla)
MARGEN_CAZA_DIVISOR = 3   # ARX-79b (plan 79, sec. 3): el margen de caza es max(MARGEN_CAZA, lado mayor del mapa / 3)
# ARX-79b: factor de seguridad de la garantía = 1 + K_ESCALA·(escala − 1) + K_NIVEL·(nivel − 1), con escala = área / (20·30).
# El plan 79 (sec. 3) propone K_ESCALA = 0,15 y K_NIVEL = 0,05. Con esos valores NINGUNA variante de 40x60 pasa la garantía
# (batería 100 − 4·(nivel − 1) frente a rutas de ~65–80 pasos × 1,45 + 15) y en 20x30 Hardcore deja de hallar variante en
# 3 de 5 semillas (rompe 2 pruebas de api/tests/test_eventos_arx30.py que pasaban). El Maestro eligió la batería
# proporcional al tamaño (ev3-d75 A), así que K queda en 0 por esa decisión (factor 1,0); la fórmula y su prueba están listas.
FACTOR_SEGURIDAD_K_ESCALA = 0.0
FACTOR_SEGURIDAD_K_NIVEL = 0.0
FACTOR_SEGURIDAD_PLAN = (0.15, 0.05)    # valores del plan 79, descartados por la evidencia anterior
AVISO_SIN_GARANTIA = "Mapa sin garantía de victoria para este nivel y tamaño"


def margen_caza(filas: int, columnas: int) -> float:
    """ARX-79b: pasos extra por dron obligatorio, proporcional al mapa. La persecución recorre del orden del lado mayor
    (en 8 direcciones la «diagonal» en celdas es max(filas, columnas): 60 en 40x60) dividido por 3; en 20x30 vale 10."""
    return max(float(MARGEN_CAZA), max(int(filas), int(columnas)) / MARGEN_CAZA_DIVISOR)


def factor_seguridad_garantia(filas: int, columnas: int, nivel: int) -> float:
    """ARX-79b: multiplicador del recorrido estimado por la garantía (1,0 en 20x30 nivel 1; ≈1,45 en 40x60 nivel 1)."""
    escala = (int(filas) * int(columnas)) / (FILAS_BASE * COLUMNAS_BASE)
    return 1.0 + FACTOR_SEGURIDAD_K_ESCALA * (escala - 1.0) + FACTOR_SEGURIDAD_K_NIVEL * (int(nivel) - 1)


def _drones_obligatorios(mundo, semilla: int, nivel: int) -> list:
    """Posiciones de patrulla de los drones que la sesión creará con esta semilla (solo desde Medio, ARX-66)."""
    if nivel < 3:
        return []
    from types import SimpleNamespace
    from juego.combate import Combate
    combate = Combate(mundo=mundo, rover=SimpleNamespace(posicion=tuple(int(x) for x in mundo.inicio)), semilla=semilla)
    return [tuple(int(v) for v in d.pos) for d in combate.drones]


ESTACIONES_ACTIVAS = False                                    # ARX-59 en propuesta: apagado por defecto (no se publica)
ESTACIONES_POR_NIVEL = {1: 3, 2: 3, 3: 2, 4: 2, 5: 1}     # ARX-59 (ev3-d45 A): mapa grande; más chico, proporcional
AMBIENTE_FACTOR_POR_NIVEL = {1: 1.3, 2: 1.3, 3: 1.2, 4: 1.1, 5: 1.0}   # margen por tormenta y noche
FACTOR_DESVIO = 2.0                                              # ARX-59: desvío con el peor caso de tormenta
RESERVA_DESVIO = 5.0                                          # batería de reserva para el desvío a estación
RECARGA_PASOS = 3                                             # pasos parado para recargar en una estación
# 22/11 (pedido del usuario): en la partida jugable hay bases de recarga y pilas sin endurecer la garantía ni cambiar
# el mapa elegido. La capacidad del rover es su batería inicial (la interfaz la muestra como 100 %).
BASES_RECARGA_JUGABLES = True
FACTOR_DESVIO_JUGABLE = 1.3                                   # margen para ir a la base (ARX-59 usaba 2,0: peor tormenta)
UMBRAL_DESVIO_JUGABLE = 0.6                                   # no se desvía a una base con más del 60 % de la capacidad
PILAS_JUGABLES = True
COLCHON_RECARGA = 0.10                                        # R23: la recarga parcial deja este tanto de la capacidad sobre lo necesario
PILA_FRACCION = 0.10                                          # una pila da el 10 % de la capacidad
PILAS_MAPA_GRANDE = 5                                         # pilas en el mapa grande; más chico, proporcional (mín. 2)
# ARX-79 (ev3-d75 A): batería inicial del mapa más grande que el pequeño = batería por nivel × RAZON_BATERIA_GRANDE.
# R = mediana de pasos de las victorias del grande (77,5) / mediana del pequeño (52,0) = 1,49 (ver ARX-79_calibracion.md).
RAZON_BATERIA_GRANDE = 1.49
RAZON_BATERIA_GRANDE_JUGABLE = 2.8    # R23: calibrada con scripts/medir_dificultad.py --tamano grande
BATERIA_MAX_POR_NIVEL = {1: 60.0, 2: 56.0, 3: 52.0, 4: 48.0, 5: 44.0}   # calibrar: la ruta completa no llega sin recargar


def _cheb(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _alcanzables(mundo, origen) -> set:
    """Celdas libres alcanzables desde origen por el mapa real (8 direcciones)."""
    filas, columnas = mundo.tipo.shape
    vistas, pila = {origen}, [origen]
    while pila:
        f, c = pila.pop()
        for df, dc in MOVIMIENTOS.values():
            v = (f + df, c + dc)
            if 0 <= v[0] < filas and 0 <= v[1] < columnas and v not in vistas and mundo.tipo[v] == LIBRE:
                vistas.add(v)
                pila.append(v)
    return vistas


def _colocar_pilas(mundo, semilla: int, n: int, estaciones=()) -> list:
    """22/11: pilas de batería en celdas libres alcanzables, lejos del inicio y del refugio y fuera de sitios y
    bases. Generador propio (no altera los demás). Determinista con la semilla del mundo."""
    if n <= 0:
        return []
    inicio = tuple(int(x) for x in mundo.inicio)
    refugio = tuple(int(x) for x in mundo.refugio)
    ocupadas = {tuple(int(v) for v in s) for s in mundo.sitios} | {tuple(e) for e in estaciones}
    candidatas = [p for p in sorted(_alcanzables(mundo, inicio))
                  if _cheb(p, inicio) >= 3 and _cheb(p, refugio) >= 3 and p not in ocupadas]
    if not candidatas:
        return []
    rng = np.random.default_rng([int(semilla), 3141])
    idx = rng.choice(len(candidatas), size=min(n, len(candidatas)), replace=False)
    return [candidatas[int(i)] for i in sorted(idx)]


def _colocar_estaciones(mundo, semilla: int, n: int) -> list:
    """Estaciones de recarga: celdas libres alcanzables, lejos del inicio, del refugio y de los sitios,
    repartidas por el mapa (cada una la más lejana de las ya elegidas). Determinista con la semilla del mundo."""
    if n <= 0:
        return []
    inicio = tuple(int(x) for x in mundo.inicio)
    refugio = tuple(int(x) for x in mundo.refugio)
    sitios = [tuple(int(v) for v in s) for s in mundo.sitios]
    candidatas = [p for p in sorted(_alcanzables(mundo, inicio))
                  if _cheb(p, inicio) >= 4 and _cheb(p, refugio) >= 4 and all(_cheb(p, s) >= 3 for s in sitios)]
    if not candidatas:
        return []
    rng = np.random.default_rng([int(semilla), 2024])
    elegidas = [candidatas[int(rng.integers(len(candidatas)))]]
    while len(elegidas) < min(n, len(candidatas)):
        resto = [p for p in candidatas if p not in elegidas]
        elegidas.append(max(resto, key=lambda p: min(_cheb(p, e) for e in elegidas)))
    return elegidas


def _cadena_a_destino(pos, bat, destino, estaciones, largo, factor, bateria_max):
    """Cadena de estaciones desde pos hasta destino (ARX-59). El primer tramo sale con la batería actual; después,
    cada salto de estación en estación cuesta ≤ batería máxima / factor (la batería vuelve al máximo en cada estación).
    Devuelve la lista de nodos [estación…, destino] o None si no hay cadena."""
    import heapq
    contador = 0
    cola = []
    for s in estaciones:
        d1 = largo(pos, s)
        if d1 is not None and d1 * factor <= bat:
            heapq.heappush(cola, (d1, contador, s, None))
            contador += 1
    previo_de, visto = {}, set()
    while cola:
        coste, _, nodo, previo = heapq.heappop(cola)
        if nodo in visto:
            continue
        visto.add(nodo)
        previo_de[nodo] = previo
        if nodo == destino:
            break
        if nodo in estaciones:
            for siguiente in list(estaciones) + [destino]:
                if siguiente in visto:
                    continue
                d = largo(nodo, siguiente)
                if d is None or d * factor > bateria_max:
                    continue
                heapq.heappush(cola, (coste + d, contador, siguiente, nodo))
                contador += 1
    if destino not in visto:
        return None
    cadena, nodo = [], destino
    while nodo is not None:
        cadena.append(nodo)
        nodo = previo_de[nodo]
    return list(reversed(cadena))


def _plan_con_paradas(origen, seq, bateria, bateria_max, estaciones, largo, tramo, cazas=(), factor=1.0, margen_caza_pasos=None):
    """Camino por la secuencia seq (sitios, drones, refugio) con paradas en estaciones cuando falta batería.

    Un tramo directo cuesta largo × factor. Si no alcanza, se busca una cadena de estaciones (ARX-59).
    Devuelve la lista de celdas, o None si no hay forma de llegar al final con MARGEN_ENERGIA.
    Cada dron de cazas cuesta margen_caza_pasos (por omisión MARGEN_CAZA) pasos extra. Tras una estación la batería vuelve al máximo.
    """
    camino, pos, bat = [origen], origen, float(bateria)
    mc = MARGEN_CAZA if margen_caza_pasos is None else margen_caza_pasos
    for i, destino in enumerate(seq):
        extra = mc if destino in cazas else 0
        d = largo(pos, destino)
        # 22/11: el último tramo directo debe dejar la reserva final; si no la deja, se prueba pasando por una base
        # (antes se tomaba el directo y el plan entero se descartaba por la reserva, aunque una base lo salvara).
        # Sin bases da lo mismo que antes: en ambos casos no hay plan.
        reserva = MARGEN_ENERGIA if i == len(seq) - 1 else 0.0
        if d is not None and d * factor + extra + reserva <= bat:
            bat -= d * factor + extra
            camino.extend(tramo(pos, destino)[1:])
        else:
            cadena = _cadena_a_destino(pos, bat, destino, estaciones, largo, factor, bateria_max)
            if cadena is None:
                return None
            nodos = [pos] + cadena
            for a, b in zip(nodos, nodos[1:]):
                camino.extend(tramo(a, b)[1:])
            ultimo = cadena[-2] if len(cadena) >= 2 else pos
            bat = bateria_max - largo(ultimo, destino) * factor - extra
        pos = destino
    return camino if bat >= MARGEN_ENERGIA else None


def _es_ganable(mundo, bateria: float, drones=(), bateria_max=None, estaciones=(), factor=1.0, margen_caza_pasos=None) -> bool:
    """ARX-66 / ARX-59: existe un orden de sitios y drones obligatorios, con paradas en estaciones, que llega al
    refugio con la batería disponible. Sin estaciones equivale a comprobar la ruta completa sin recargar."""
    import itertools
    mascara = np.asarray(mundo.tipo == LIBRE)
    origen = tuple(int(x) for x in mundo.inicio)
    pts = [tuple(int(v) for v in p) for p in mundo.sitios]
    cazas = [tuple(int(v) for v in d) for d in drones]
    est = [tuple(int(v) for v in e) for e in estaciones]
    refugio = tuple(int(v) for v in mundo.refugio)
    if len(pts) + len(cazas) > 6:
        return False
    tope = float(bateria_max) if bateria_max is not None else float(bateria)
    tramos, largos = {}, {}

    def tramo(a, b):
        if (a, b) not in tramos:
            t = camino_bfs(a, b, mascara)
            tramos[(a, b)] = None if t is None else [tuple(int(v) for v in x) for x in t]
        return tramos[(a, b)]

    def largo(a, b):
        if (a, b) not in largos:
            t = tramo(a, b)
            largos[(a, b)] = None if t is None else len(t) - 1
        return largos[(a, b)]

    for orden_s in itertools.permutations(pts):
        for orden_d in itertools.permutations(cazas):
            seq = list(orden_s) + list(orden_d) + [refugio]
            if _plan_con_paradas(origen, seq, bateria, tope, est, largo, tramo, cazas, factor, margen_caza_pasos) is not None:
                return True
    return False


# ---------- R23 (AG): plan con ventanas de tiempo, recarga obligatoria y sitios opcionales ----------
PLAN_RESTRINGIDO_JUGABLE = True       # la partida jugable (garantia=True) usa el AG con restricciones (planificacion.py)
AG_PLAN_INICIAL = (60, 60)            # (población, generaciones) del plan inicial
AG_PLAN_REPLANTEO = (40, 30)          # y de los replanteos completos (eventos graves, plan inviable)
OLVIDOS_MAXIMOS = 4                 # veces por partida que se pueden olvidar las dudas de la RNA
MARGEN_ESCAPE_PLAN = 0.08           # fracción de la capacidad que debe quedar tras cada sitio para llegar a una base (tormentas, ráfagas)
MARGEN_FACTOR_PLAN = 1.2           # margen sobre el factor de energía del planeta al planificar recargas
# R23 (RNA): la RNA nominal da ~1,7 % de falsos barrancos entre las celdas libres; marcar una celda como riesgo permanente con una
# sola observación la cierra para siempre (en una prueba, la RNA «vio» un barranco sobre una base de recarga y el rover no llegó).
# Con True se exigen OBSERVACIONES_RNA_CONFIRMA observaciones con media de p(barranco) > 0,5, como Mision ya hace con ruido alto.
# El veto inmediato V-RNA-BARRANCO no cambia: sigue vetando con la lectura del paso. Las bases, los sitios, el inicio y el refugio
# son conocidos (mapa orbital): la RNA no los marca nunca (una lectura sobre ellos es un falso positivo).
CONFIRMAR_RNA_JUGABLE = True
# R23 (RNA con anticipación, anticipacion.py): en la partida jugable la RNA también clasifica las celdas de la ruta a 2, 3 y 4 pasos.
# Una celda con p(barranco) >= UMBRAL_ANT_PRECAUCION frena el paso (tope de velocidad); si la media de sus observaciones (al menos
# dos) llega a UMBRAL_ANT_MARCA, queda como riesgo y se replantea la ruta antes de llegar. Umbrales sobre probabilidades corregidas
# por la proporción real de clases; con ellos el recall a 2/3/4 celdas es ~61/47/34 % con ~1 % de falsos (ver docs/planes/R23_ag.md).
ANTICIPACION_JUGABLE = True
UMBRAL_ANT_PRECAUCION = 0.10
UMBRAL_ANT_MARCA = 0.30
VELOCIDAD_PRECAUCION = 0.30
OBSERVACIONES_RNA_CONFIRMA = 2


def _bfs_a(m, origen, destino):
    return camino_bfs(origen, destino, m.riesgo < 0.5)


def _plan_de_referencia(mundo, sitios_plan, bases, bateria, capacidad, factor, reserva_extra, semilla):
    """Recorrido de referencia sobre el mapa real: permutación aleatoria mejorada con tres movimientos 2-opt y puntuada con
    la reparación de recargas. Sus tiempos de llegada centran las ventanas (el AG puede hallar un recorrido mejor)."""
    mascara = np.asarray(mundo.tipo == LIBRE)
    prob = planificacion.Problema(mundo.inicio, mundo.refugio, sitios_plan, bases, bateria, capacidad,
                                  planificacion.Distancias.de(mascara), factor, reserva_extra=reserva_extra)
    rng = np.random.default_rng([int(semilla), 5151])
    ref = [int(x) for x in rng.permutation([s.id for s in sitios_plan])]
    hechos = 0
    while hechos < 3 and len(ref) > 1:
        base = planificacion._largo_tour(prob, ref)
        for i in range(len(ref) - 1):
            mejoro = False
            for j in range(i + 1, len(ref)):
                cand = ref[:i] + ref[i:j + 1][::-1] + ref[j + 1:]
                if planificacion._largo_tour(prob, cand) < base - 1e-9:
                    ref, hechos, mejoro = cand, hechos + 1, True
                    break
            if mejoro or hechos >= 3:
                break
        else:
            break
    return prob, planificacion.plan_heuristico(prob, ref)


def _es_ganable_plan(mundo, bateria, bases, factor, reserva_extra=0.0, capacidad=None) -> bool:
    """R23: garantía de la partida con plan restringido: algún recorrido por vecino más cercano o 2-opt visita los sitios
    obligatorios con las recargas que hagan falta (la reparación del planificador) y llega al refugio con reserva.
    Los opcionales no cuentan: se pueden sacrificar. Sobre el mapa real, con el factor y la reserva de caza dados."""
    obligatorios = _sitios_obligatorios(mundo)
    sitios = [planificacion.SitioPlan(i + 1, c, float(mundo.sitios[c]), None, True)
              for i, c in enumerate(sorted(obligatorios))]
    mascara = np.asarray(mundo.tipo == LIBRE)
    prob = planificacion.Problema(mundo.inicio, mundo.refugio, sitios, bases, bateria, capacidad or bateria,
                                  planificacion.Distancias.de(mascara), factor, reserva_extra=reserva_extra)
    for nombre in ("vecino", "2opt"):
        if planificacion.mejor_heuristico(prob, nombre).factible:
            return True
    return False


def _sitios_obligatorios(mundo) -> set:
    """Sitios que hay que visitar para ganar: todos menos la cuarta parte de menor valor (esos son opcionales)."""
    celdas = sorted(mundo.sitios, key=lambda c: (mundo.sitios[c], c))
    n_opc = int(len(celdas) * dificultad.FRACCION_OPCIONALES)
    return set(celdas[n_opc:])


def _ag_restringido(partida, heuristica: str = None, anotar=None):
    """Envoltorio de `Mision._optimizar_ag` para el plan restringido. Con `heuristica` ("vecino", "2opt", "ventanas",
    "valor") usa esa heurística «sin AG» en vez del AG; en ambos casos las paradas de recarga las inserta la reparación
    del planificador. Devuelve la ruta (celdas) del plan; el plan y el problema quedan en `optimizar.plan` y
    `optimizar.problema`, y el resultado del AG en `optimizar.ultimo`."""
    m = partida.mision

    def optimizar(origen, pendientes):
        origen = tuple(int(v) for v in origen)
        prob = partida._problema_plan(origen, pendientes)
        optimizar.problema = prob
        if heuristica is not None:
            plan = planificacion.mejor_heuristico(prob, heuristica)
            optimizar.ultimo = None
        elif not prob.sitios:
            plan = prob.decodificar((), (), (-1,))
            optimizar.ultimo = None
        else:
            pob, gens = AG_PLAN_INICIAL if partida._plan_inicial_pendiente else AG_PLAN_REPLANTEO
            if not partida._plan_inicial_pendiente:           # pocos sitios pendientes: espacio chico, menos esfuerzo
                pob, gens = min(pob, max(16, 8 * prob.n)), min(gens, max(10, 4 * prob.n + 6))
            semillas = partida._cromosomas_semilla(prob)
            ag = planificacion.AGRestringido(prob, poblacion=pob, generaciones=gens, semilla=m.semilla + 7919 * m.replanes,
                                             semillas_cromosomas=semillas)
            res = ag.optimizar()
            plan = res.mejor
            optimizar.ultimo, optimizar.ag = res, ag
            optimizar.decisiones.append(False)
            if partida._plan_inicial_pendiente:
                partida._guardar_evolucion(prob, res)
        optimizar.plan = plan
        if not plan.factible:
            if anotar is not None:
                anotar("Plan sin solución con las restricciones: la batería no alcanza para los sitios obligatorios")
            return []
        return prob.ruta(plan) or []
    optimizar.metodo = "AG con restricciones (orden, selección y recargas)" if heuristica is None else f"heurística {heuristica}"
    optimizar.metodo_respaldo = METODO_ORDEN
    optimizar.decisiones = []
    optimizar.fallbacks = []
    optimizar.ultimo = None
    optimizar.gp = None
    optimizar.plan = None
    optimizar.problema = None
    optimizar.ag = None
    return optimizar


METODO_ORDEN = "exhaustiva puntuada por el fitness"     # ARX-92a: respaldo (vía b) cuando el AG no da un orden viable
METODO_AG_ORDEN = "AG sobre el orden de los sitios"      # ARX-92c: cómo decide la partida el orden de visita
AVISO_FALLBACK = "AG-FALLBACK-GARANTIA"                  # ARX-92c: el mejor orden del AG no era viable; juega la vía b
# ARX-92a (ev3-d74 B, umbral único): permutaciones viables a este fitness o menos del mejor se consideran empatadas y gana
# la más corta. Fijado en docs/planes/ARX-92_ag_decide.md (p90 del error de fitness del exigente, 20 semillas).
UMBRAL_EMPATE = 0.0223
# ARX-92c: la partida no usa punto de paso por tramo (el AG decide el ORDEN; el camino entre sitios es el BFS de la
# garantía). Con True el cromosoma añade un punto de paso opcional por tramo; cambia la ruta jugada y la cifra congelada.
AG_ORDEN_CON_PASO = False


def _ag_con_todos_los_sitios(m, optimizar_original, pesos=None, anotar=None, con_paso=None, parada_sin_mejora=None):
    """ARX-66 / ARX-59 / ARX-92a / ARX-92c: la ruta visita todos los sitios pendientes y el orden lo decide un AG real
    (`GeneticPlanner.optimizar_orden`: permutación de sitios, cruce OX, mutación por intercambio, elitismo) puntuado por
    el fitness con los pesos dados o los de defecto. La viabilidad es restricción dura: el mismo `_plan_con_paradas` y
    factor de la garantía (con paradas en estaciones si las hay); un orden inviable no puede ganar. Si el mejor orden del
    AG no es viable (ningún orden evaluado lo es), cae a la vía b de 92a (permutación viable de mayor fitness entre todas,
    con más de 6 sitios solo el orden dado), lo anota con AG-FALLBACK-GARANTIA (`anotar` y `optimizar.fallbacks`) y,
    si tampoco hay ninguna, devuelve la ruta de `optimizar_original`. Entre viables a UMBRAL_EMPATE del mejor fitness
    gana la más corta (desempate de 92a). El método queda en `optimizar.metodo`."""
    import itertools
    from genetico import GeneticPlanner as _GP

    def optimizar(origen, pendientes):
        if not pendientes:
            return optimizar_original(origen, pendientes)
        origen = tuple(int(v) for v in origen)
        pts = [tuple(int(v) for v in p) for p in pendientes]
        mascara = m.riesgo < 0.5
        tramos, largos = {}, {}

        def tramo(a, b):
            if (a, b) not in tramos:
                t = camino_bfs(a, b, mascara)
                tramos[(a, b)] = None if t is None else [tuple(int(v) for v in x) for x in t]
            return tramos[(a, b)]

        def largo(a, b):
            if (a, b) not in largos:
                t = tramo(a, b)
                largos[(a, b)] = None if t is None else len(t) - 1
            return largos[(a, b)]

        con_estaciones = getattr(m, "estaciones_activas", False)
        elegido_pesos = pesos if pesos is not None else getattr(m, "pesos_ag", None)
        desde = replace(m.mundo, inicio=origen, sitios={p: m.mundo.sitios.get(p, 1) for p in pts})
        capacidad = max(float(getattr(m, "bateria_max", None) or m.rover.bateria), 1.0)
        gp = _GP(desde, m.riesgo, bateria=capacidad, k_puntos=m.k, poblacion=30, generaciones=30,
                 pesos=dict(elegido_pesos) if elegido_pesos else None, semilla=m.semilla)

        def construir(seq):
            """Ruta viable por la secuencia (sitios, puntos de paso y refugio) o None."""
            if con_estaciones:
                return _plan_con_paradas(origen, list(seq), m.rover.bateria, m.bateria_max, m.estaciones, largo, tramo,
                                         factor=m.factor_ambiente)
            c = [origen]
            for destino in seq:
                t = tramo(c[-1], destino)
                if t is None:
                    return None
                c.extend(t[1:])
            # ARX-92c (corrección aprobada por el Maestro): la viabilidad usa la misma reserva que _planear
            # (largo + MARGEN_ENERGIA ≤ batería). Una ruta que no la cumple devuelve None y queda por debajo de
            # cualquier ruta completa viable (piso de fitness en optimizar_orden).
            # ARX-92 B (§16): una ruta inviable se devuelve con su exceso (no se descarta): el planificador la penaliza
            exceso = len(c) - 1 + MARGEN_ENERGIA - m.rover.bateria
            if exceso > 0:
                return ("inviable", c, exceso)
            return c

        res = gp.optimizar_orden(construir, con_paso=AG_ORDEN_CON_PASO if con_paso is None else con_paso,
                                 umbral_empate=UMBRAL_EMPATE, parada_sin_mejora=parada_sin_mejora)
        optimizar.ultimo, optimizar.gp = res, gp
        if res.viable:
            optimizar.decisiones.append(res.desempate_cambio)
            return res.mejor_ruta
        # Respaldo (vía b de 92a): ningún orden evaluado por el AG es viable; se prueban todas las permutaciones
        optimizar.fallbacks.append(AVISO_FALLBACK)
        if anotar is not None:
            anotar(AVISO_FALLBACK + ": el mejor orden del AG no es viable; juega la permutación viable de mejor fitness")
        validas = []            # (fitness, largo de la ruta, ruta) de cada permutación viable
        candidatos = itertools.permutations(pts) if len(pts) <= 6 else [tuple(pts)]
        for orden in candidatos:
            c = construir(list(orden) + [tuple(int(v) for v in m.mundo.refugio)])
            if c is None or isinstance(c, tuple):
                continue
            validas.append((gp.evaluar_ruta(c, capacidad).fitness, len(c), c))
        if not validas:
            optimizar.decisiones.append(False)
            return optimizar_original(origen, pendientes)
        fmax = max(v[0] for v in validas)
        mejor_fitness = next(v for v in validas if v[0] == fmax)
        empate = [v for v in validas if v[0] >= fmax - UMBRAL_EMPATE]
        elegido = min(empate, key=lambda v: v[1])
        optimizar.decisiones.append(elegido[2] is not mejor_fitness[2])
        return elegido[2]
    optimizar.metodo = METODO_AG_ORDEN
    optimizar.metodo_respaldo = METODO_ORDEN
    optimizar.decisiones = []       # por cada planificación, True si decidió el desempate y no el fitness
    optimizar.fallbacks = []        # ARX-92c: un AVISO_FALLBACK por cada vez que se cayó a la vía b
    optimizar.ultimo = None         # último ResultadoAG del modo orden y su planificador (para /ag y pruebas)
    optimizar.gp = None
    return optimizar


def _cronometrado(metodo):
    """ARX-89b: suma al acumulador tiempo_computo_s el TIEMPO DE PARED (time.perf_counter, reloj de pared, no CPU) del
    método. Se usa pared porque time.process_time tiene resolución de unos 15 ms en Windows y pierde los pasos cortos.
    Las llamadas anidadas (avanzar_modo llama a avanzar_ia) no se cuentan dos veces."""
    @functools.wraps(metodo)
    def envuelto(self, *args, **kwargs):
        if self._cronometro_nivel:
            return metodo(self, *args, **kwargs)
        self._cronometro_nivel += 1
        t0 = time.perf_counter()
        try:
            return metodo(self, *args, **kwargs)
        finally:
            self.tiempo_computo_s += time.perf_counter() - t0
            self._cronometro_nivel -= 1
    return envuelto


def _paso_de_juego(metodo):
    """ev3-d88 B: marca que el método corre un paso de juego. Mientras dura, el difuso usa la T_int de la partida
    (envoltorio de __init__); fuera del paso (laboratorio /difuso), la temperatura que se pide."""
    @functools.wraps(metodo)
    def envuelto(self, *args, **kwargs):
        previo = self._en_paso_juego
        self._en_paso_juego = True
        try:
            return metodo(self, *args, **kwargs)
        finally:
            self._en_paso_juego = previo
    return envuelto


def bateria_por_defecto(nivel: int, filas: int, columnas: int, garantia: bool = True, planeta: str = "Marte") -> float:
    """ARX-87: batería inicial por defecto del nivel y el tamaño (la misma fórmula que usa Partida si no hay campo)."""
    con_estaciones = bool(garantia) and ESTACIONES_ACTIVAS   # ARX-59: solo con la bandera encendida
    if con_estaciones:
        bateria = BATERIA_MAX_POR_NIVEL[nivel]
    elif garantia:
        bateria = dificultad.bateria_inicial(nivel, planeta)   # R23: la partida jugable tiene su propia curva de dificultad
    else:
        bateria = 100.0 - 4.0 * (nivel - 1)                    # evaluación congelada: la de siempre
    if int(filas) * int(columnas) > FILAS_BASE * COLUMNAS_BASE and not con_estaciones:
        # ARX-79 (ev3-d75 A): el grande tiene batería proporcional. R23: la partida jugable, con drones, viento y hielo, gasta
        # más que la razón de pasos de las victorias del congelado: usa su propia razón
        bateria *= RAZON_BATERIA_GRANDE_JUGABLE if (garantia and not con_estaciones) else RAZON_BATERIA_GRANDE
    return float(bateria)


class Partida:
    # ARX-89b: tiempo de cómputo acumulado de la partida (construcción con el AG inicial, pasos, movimientos y eventos)
    tiempo_computo_s = 0.0
    _cronometro_nivel = 0

    def __init__(self, semilla: int = 11, bateria: float = None, nivel: int = 1,
                 eventos_activos=EVENTOS_SOPORTADOS, filas: int = FILAS_BASE, columnas: int = COLUMNAS_BASE,
                 garantia: bool = True, planeta: str = termico.PLANETA_POR_DEFECTO, n_sitios: int = None,
                 plan_restringido: bool = None, difuso_evolucionado: bool = None, ajustes_difuso: dict = None):
        _t0_construccion = time.perf_counter()      # tiempo de pared, igual que _cronometrado
        self.tiempo_computo_s = 0.0
        self._cronometro_nivel = 0
        if isinstance(nivel, bool) or not isinstance(nivel, int) or not 1 <= nivel <= NIVEL_MAX:
            raise ValueError(f"nivel inválido: {nivel!r} (debe estar entre 1 y {NIVEL_MAX})")
        con_estaciones = bool(garantia) and ESTACIONES_ACTIVAS   # ARX-59: solo con la bandera encendida
        if bateria is None:
            bateria = bateria_por_defecto(nivel, filas, columnas, garantia, planeta)   # ARX-87: misma fórmula, en una función
        self.nivel = nivel
        self.semilla = semilla
        # R23 (AG): la partida jugable planifica con ventanas de tiempo, recarga obligatoria y sitios opcionales
        self.plan_activo = bool(garantia) and (PLAN_RESTRINGIDO_JUGABLE if plan_restringido is None else bool(plan_restringido))             and not (garantia and ESTACIONES_ACTIVAS)
        self.eventos_activos = tuple(eventos_activos)
        if isinstance(filas, bool) or isinstance(columnas, bool) or not (
                MIN_LADO <= int(filas) <= MAX_LADO and MIN_LADO <= int(columnas) <= MAX_LADO):
            raise ValueError(f"tamaño inválido: {filas!r}x{columnas!r} (cada lado entre {MIN_LADO} y {MAX_LADO})")
        self.filas, self.columnas = int(filas), int(columnas)
        # Los obstáculos y barrancos escalan con el área; con 20x30 el resultado es el mismo de siempre (ARX-21).
        escala = (self.filas * self.columnas) / (FILAS_BASE * COLUMNAS_BASE)
        def _generar(semilla_mundo):
            return generar_mundo(semilla_mundo, filas=self.filas, columnas=self.columnas,
                                 n_obstaculos=round((20 + 2 * nivel) * escala), n_barrancos=round((4 + nivel) * escala),
                                 n_sitios=n_sitios if n_sitios is not None else (
                                     dificultad.n_sitios(nivel, self.filas, self.columnas) if self.plan_activo
                                     else (3 if nivel <= 2 else 4)))
        mundo = _generar(semilla)
        self.semilla_mundo = semilla
        self.factor_seguridad = factor_seguridad_garantia(self.filas, self.columnas, nivel)   # ARX-79b
        self.margen_caza = margen_caza(self.filas, self.columnas)                             # ARX-79b
        self._sin_garantia = False
        if garantia:
            # ARX-66: toda partida generada debe ser ganable (sitios, drones obligatorios y regreso al refugio con la
            # batería inicial). Si no lo es, se prueba una variante determinista del mismo mapa; la semilla no cambia.
            bat0 = bateria if bateria is not None else 100.0
            bat_max = BATERIA_MAX_POR_NIVEL[nivel] if con_estaciones else bat0
            escala_grande = (self.filas * self.columnas) / (40 * 60)
            minimo = 2 if nivel <= 2 else 1          # niveles bajos: al menos 2 estaciones en cualquier tamaño
            n_est = max(minimo, round(ESTACIONES_POR_NIVEL[nivel] * escala_grande)) if con_estaciones else 0
            fac = AMBIENTE_FACTOR_POR_NIVEL[nivel] if con_estaciones else 1.0
            fac *= self.factor_seguridad               # ARX-79b
            if not con_estaciones and BASES_RECARGA_JUGABLES and dificultad.GARANTIA_CON_BASES_Y_PLANETA:
                # R23: la garantía de la partida jugable es «existe una ruta ganadora» con las bases de recarga que habrá y
                # la mitad del sobrecoste medio del planeta; no promete ganar siempre (viento, hielo, eventos y la
                # conducción de la IA pueden hacerla fallar). Antes ignoraba las bases y el planeta.
                n_est = max(1, round(ESTACIONES_POR_NIVEL[nivel] * (self.filas * self.columnas) / (40 * 60)))
                fac *= 1.0 + dificultad.GARANTIA_FRACCION_SOBRECOSTO * planetas.sobrecosto_medio(
                    planeta, dificultad.INTENSIDAD_POR_NIVEL[nivel])
            if self.plan_activo:
                n_est = dificultad.n_bases(nivel, self.filas, self.columnas)

            def _comprobar(mundo_):
                drones_ = _drones_obligatorios(mundo_, semilla, nivel)
                est_ = _colocar_estaciones(mundo_, self.semilla_mundo, n_est)
                if self.plan_activo:
                    # R23: con más de 6 sitios no se prueban todas las permutaciones: la garantía usa el planificador
                    return _es_ganable_plan(mundo_, bat0, est_, fac * MARGEN_FACTOR_PLAN,
                                            reserva_extra=self.margen_caza * len(drones_) * fac * MARGEN_FACTOR_PLAN)
                return _es_ganable(mundo_, bat0, drones_, bateria_max=bat_max, estaciones=est_, factor=fac,
                                   margen_caza_pasos=self.margen_caza)
            ganable = False
            for k in range(1, 60):
                if _comprobar(mundo):
                    ganable = True
                    break
                self.semilla_mundo = semilla + 10007 * k
                mundo = _generar(self.semilla_mundo)
            else:   # la última variante generada no se había comprobado
                ganable = _comprobar(mundo)
            self._sin_garantia = not ganable
        self.mision = (_MisionPlanDiferido if self.plan_activo else Mision)(mundo, semilla=semilla, bateria=bateria)
        self.mision.plan_diferido = False
        if garantia:
            # R23: los sensores de la partida jugable tienen el ruido de su nivel (la RNA se reentrena sola con él)
            self.mision.sensor.ruido = dificultad.RUIDO_POR_NIVEL[nivel]
        self._fitness_paso = None          # ARX-80: fitness del AG ya medido en el paso en curso (avanzar_ia)
        self._fitness_ultimo = 0.0         # último fitness finito medido; se arrastra si no hay plan del AG
        self.mision.log.completar = self._completar_fila
        # ARX-59: estaciones de recarga y batería máxima (la partida jugable las usa; las evaluaciones congeladas no)
        self.bateria_max = BATERIA_MAX_POR_NIVEL[nivel] if con_estaciones else None
        self.estaciones = _colocar_estaciones(mundo, self.semilla_mundo, n_est) if con_estaciones else []
        self.capacidad_bateria = float(self.mision.rover.bateria)   # 22/11: la interfaz muestra la batería sobre esto
        self.factor_desvio = FACTOR_DESVIO
        self._desvio_jugable = False                                 # True con las bases de la partida jugable
        self.umbral_recarga = 1.0                                   # recarga si la batería está bajo este tanto del máximo
        self.recarga_parcial = False                                # True solo con las bases de la partida jugable (R23)
        escala_area = (self.filas * self.columnas) / (40 * 60)
        if garantia and not con_estaciones and BASES_RECARGA_JUGABLES:
            # bases de recarga sobre el mapa ya elegido (la garantía no las usa: el mapa es el mismo de siempre)
            self.bateria_max = self.capacidad_bateria
            self.estaciones = _colocar_estaciones(
                mundo, self.semilla_mundo,
                dificultad.n_bases(nivel, self.filas, self.columnas) if self.plan_activo
                else max(1, round(ESTACIONES_POR_NIVEL[nivel] * escala_area)))
            self.factor_desvio = FACTOR_DESVIO_JUGABLE
            self._desvio_jugable = True
            self.umbral_recarga = 0.9                               # de paso por una base casi llena, no se detiene
            self.recarga_parcial = not self.plan_activo             # R23: la base carga solo lo necesario (con plan: llena)
        elif con_estaciones:
            self.capacidad_bateria = float(self.bateria_max)
        self.pilas = (_colocar_pilas(mundo, self.semilla_mundo, max(2, round(PILAS_MAPA_GRANDE * escala_area)), self.estaciones)
                      if garantia and PILAS_JUGABLES else [])
        self.pilas_recogidas = 0
        self.recargas_hechas = 0
        self.meteoritos_activos = bool(garantia)   # ARX-30: meteoritos solo en la partida jugable (las evaluaciones no)
        self.meteoritos = []                       # impactos de la partida: paso, impacto y zona de riesgo
        self.sismos = []                           # sismos de la partida: paso y grietas (ARX-30a)
        self._recargando = 0               # pasos parado que quedan de una recarga
        self._ultima_estacion = None       # estación en la que está el rover (no se recarga dos veces seguidas)
        self._comprometido = None          # estación a la que va a recargar; no se reevalúa hasta llegar (ARX-59)
        self._estacion_reciente = None     # última estación en la que estuvo el rover (no se vuelve a ella al salir)
        self._paso_estacion_reciente = -100  # paso en que estuvo en esa estación (la exclusión dura 20 pasos)
        self.mision.estaciones_activas = con_estaciones
        self.mision.bateria_max = self.bateria_max
        self.mision.estaciones = self.estaciones
        self.mision.factor_ambiente = AMBIENTE_FACTOR_POR_NIVEL[nivel] if con_estaciones else 1.0
        # R23: mecánicas del planeta (gravedad, viento, hielo). Solo la partida jugable; el congelado no las usa.
        self.intensidad_planeta = dificultad.INTENSIDAD_POR_NIVEL[nivel]
        self.mecanicas = planetas.MecanicasPlaneta(planeta, mundo, self.semilla_mundo, self.intensidad_planeta,
                                                   activa=bool(garantia))
        if self.mecanicas.activa:
            # la caza de drones y la señal estiman su coste con el sobrecoste medio del planeta (la mitad, como la garantía)
            self.mision.factor_ambiente *= 1.0 + dificultad.GARANTIA_FRACCION_SOBRECOSTO * planetas.sobrecosto_medio(
                planeta, self.intensidad_planeta)
        self.sitios_plan = {}               # R23: {celda: SitioPlan} con id, valor, ventana y si es obligatorio
        self.visitas = {}                   # R23: {celda de sitio: paso en que se visitó por primera vez}
        self._wp = []                       # R23: paradas del plan vigente [(tipo, celda, id)], sin el refugio
        self._plan_inicial_pendiente = True
        self.evolucion_inicial = None       # R23: curva del AG del plan inicial (GET /ag/evolucion)
        if self.plan_activo:
            self._iniciar_plan_restringido(planeta)
            self.mision._optimizar_ag = _ag_restringido(self, anotar=self._avisar)
        else:
            self.mision._optimizar_ag = _ag_con_todos_los_sitios(self.mision, self.mision._optimizar_ag, anotar=self._avisar)
        # ARX-66 / N12: mientras se cazan drones obligatorios, el refugio no es destino (Mision.paso_mision fijaría EXITO
        # al llegar sin moverse, y la caza nunca se ejecutaría).
        _quedan_sitios_original = self.mision._quedan_sitios
        # ARX-30c (ev3-d49 B): una señal biológica sin visitar también impide ganar
        self.mision._quedan_sitios = lambda: (_quedan_sitios_original() or self._caza_con_bfs()
                                              or self.senal_activa is not None)
        self.mision.rna = _RnaSegura(self.mision.rna)
        # El planificador de la misión pasa a respetar el objetivo fijado por el jugador (ev3-d27).
        self.mision._planear = self._planear_con_objetivo
        # ARX-90: regla de percepción (método ligado: sobrevive a copy y deepcopy de la partida)
        self.mision._actualizar_mapa_estimado = self._actualizar_mapa_percepcion
        self.confirmar_rna = bool(garantia) and CONFIRMAR_RNA_JUGABLE      # R23: ver CONFIRMAR_RNA_JUGABLE
        self.anticipacion_activa = bool(garantia) and ANTICIPACION_JUGABLE
        self._ant_suma = np.zeros(mundo.tipo.shape)    # p(barranco) acumulada por celda mirada a 2-4 pasos
        self._ant_n = np.zeros(mundo.tipo.shape, dtype=int)
        self._ant_ultima = []                           # clasificación del tramo del último paso (para /ia/paso)
        self._precaucion_ant = False
        if garantia:
            self.mision._riesgo_por_rna = self._riesgo_por_rna_partida      # método ligado: sobrevive a copy y deepcopy
            self.mision._barrancos_fusionados = self._barrancos_fusionados_partida
        self._falla_restante = 0           # pasos de IA detenida por falla de sensor
        self._prob_fallo_base = None       # probabilidad de fallo del sensor antes de la falla
        self._ambiente = "normal"          # "normal" | "tormenta" | "noche"
        self._ambiente_restante = 0
        self._rng_ambiente = np.random.default_rng([int(semilla), 1313])  # propio, no comparte el de Mision
        self._rng_sismo = np.random.default_rng([int(semilla), 1314])     # ARX-30a: propio, no altera los meteoritos
        self._rng_enlace = np.random.default_rng([int(semilla), 1315])    # ARX-30b: propio, no altera meteoritos ni sismos
        self._rng_senal = np.random.default_rng([int(semilla), 1316])     # ARX-30c: propio
        self._rng_resbalon = np.random.default_rng([int(semilla), 1317])  # ARX-28c: propio, no altera los demás
        self.fisica_velocidad = bool(garantia)   # ARX-28c: resbalón por pendiente y velocidad; R23: también en la partida jugable (el escenario exigente la enciende aparte)
        self.resbalones = 0
        self.senales = []                  # señales biológicas: [{"paso", "celda", "visitada"}] (ARX-30c)
        self._ultimo_corte = None          # paso del último corte de enlace (para /moviles)
        self.enlace_restante = 0           # pasos que quedan de corte de enlace (ARX-30b)
        self._objetivo = None              # celda fijada por el jugador, o None
        self._paso_replan_ag = None        # paso del último replanteo del AG por evento grave (ARX-31a)
        # ARX-83a: temperatura interna. Solo con garantia=True; el aborto y la inyección al difuso, además, solo con
        # termico.ABORTO_TERMICO_ACTIVO (apagada por defecto). La evaluación congelada no la usa.
        self.planeta = planeta
        self.termico = termico.Termico(planeta)
        self._termico_activo = bool(garantia) and self.termico.activo     # planeta sin modelo: inactivo, sin ValueError
        self._en_paso_juego = False                                       # ev3-d88 B: ver _paso_de_juego
        self._entrada_difuso = None                                       # R23: lo último que recibió el difuso en un paso
        self._en_sugerencia = False                                       # R23: sugerencia() ve lo mismo que el paso real
        # R23 (AG evoluciona el difuso): parámetros del planeta, evolucionados fuera de línea (juego/difuso_planetas.json)
        self.conduccion = {}                       # topes de velocidad y umbrales de desvío; vacío = difuso por defecto
        self.parametros_difuso = {}                # lo que difiere del difuso por defecto (para GET /ag/evolucion)
        self.difuso_evolucionado = False
        ajustes = ajustes_difuso
        if ajustes is None and bool(garantia) and (difuso_evolucionado is None or difuso_evolucionado):
            ajustes = difuso_planetas.cargar(planeta)
        elif difuso_evolucionado is False and ajustes_difuso is None:
            ajustes = None
        self._params_difuso_planeta = (ajustes or {}).get("difuso")        # lo que restaura DELETE /difuso/reglas
        if ajustes:
            self.mision.difuso = FuzzyController(params=ajustes.get("difuso"))
            self.mision.difuso.personalizado = False        # «personalizadas» es lo que edita el usuario, no lo evolucionado
            self.conduccion = dict(ajustes.get("conduccion") or {})
            self.difuso_evolucionado = True
            self.parametros_difuso = {**self.mision.difuso.parametros_planos(), **{f"conduccion.{k}": v for k, v in self.conduccion.items()}}
        if self.conduccion.get("factor_desvio") and self._desvio_jugable:
            self.factor_desvio = float(self.conduccion["factor_desvio"])
        self._umbral_desvio = float(self.conduccion.get("umbral_desvio", UMBRAL_DESVIO_JUGABLE))
        if self._termico_activo or self.mecanicas.activa:
            self._envolver_difuso()
        self.avisos = []                   # avisos para la interfaz, p. ej. «Faltan objetivos: sitios 2/4» (N4); antes de planificar: el AG puede anotar AG-FALLBACK-GARANTIA (ARX-92c)
        # Mision() ya planificó con el AG original: se replanifica con el envoltorio que exige todos los sitios
        self.mision.objetivos = []
        self.mision._planear()
        self._plan_inicial_pendiente = False
        self.intentos_barranco = 0         # movimientos intentados hacia un barranco (modos sueltos, ARX-11)
        self.esperas = 0                   # pasos de espera del modo difuso (ARX-11)
        self._historial = []               # últimas celdas visitadas por los modos sueltos (ARX-11)
        if self._sin_garantia:             # ARX-79b: ninguna de las 59 variantes pasó la garantía
            self._avisar(AVISO_SIN_GARANTIA)
        self.combate = None                # Combate de la sesión; lo asigna la API para contar los drones destruidos
        self.modo_ia = "manual"            # modo de la sesión; decide si la IA puede disparar (N12)
        self.tiempo_computo_s += time.perf_counter() - _t0_construccion

    # ---------- atributos de lectura ----------
    @property
    def mundo(self):
        return self.mision.mundo

    @property
    def rover(self):
        return self.mision.rover

    @property
    def estado(self) -> str:
        return self.mision.estado

    def estado_visible(self) -> str:
        """Estado que muestra la interfaz (ARX-33). Los estados terminales se devuelven tal cual.

        Deriva de la misión sin tocar integracion.py: CONFIGURACION antes del primer paso; REPLANIFICACION si la
        última acción fue replanificar (también tras un sismo con grieta en la ruta);
        REFUGIO si ya no quedan sitios por visitar (la ruta va al refugio); ALERTA y EXPLORACION como en la misión.
        """
        from integracion import ESTADOS_TERMINALES
        estado = self.mision.estado
        if estado in ESTADOS_TERMINALES:
            return estado
        if self.mision.paso == 0:
            return "CONFIGURACION"        # antes del primer paso (ARX-33a)
        filas = self.mision.log.filas
        if filas and filas[-1].get("accion") == "replanificar":
            return "REPLANIFICACION"
        if not self.mision._quedan_sitios():
            return "REFUGIO"
        return estado

    @property
    def t_int(self) -> float:
        """Temperatura interna del rover en °C (ARX-83a)."""
        return float(self.termico.t_int)

    @property
    def pasos_sobre_tolerancia(self) -> int:
        return int(self.termico.pasos_sobre_tolerancia)

    @property
    def ruta(self) -> list:
        return list(self.mision.ruta)

    @property
    def ambiente(self) -> str:
        return self._ambiente

    @property
    def ambiente_restante(self) -> int:
        return self._ambiente_restante

    @property
    def senal_activa(self):
        """Celda de la señal biológica sin visitar, o None (ARX-30c)."""
        for s in self.senales:
            if not s["visitada"]:
                return s["celda"]
        return None

    @property
    def falla_restante(self) -> int:
        return self._falla_restante

    @property
    def objetivo(self):
        return self._objetivo

    # ---------- IA: sugerencia sin efectos ----------
    def sugerencia(self) -> dict:
        """Observa y decide como lo haría Mision.paso_mision, pero sobre copias (ver _sugerencia_sin_efectos)."""
        previo = self._en_sugerencia
        self._en_sugerencia = True
        try:
            return self._sugerencia_sin_efectos()
        finally:
            self._en_sugerencia = previo

    def _envolver_difuso(self) -> None:
        """Hace que el difuso de la misión vea lo que ve en juego: la T_int, el hielo como pendiente, la batería en % y los
        topes de velocidad de la conducción evolucionada. Método ligado (sobrevive a copy y deepcopy). Hay que volver a llamarlo
        si se cambia `mision.difuso` (PUT /difuso/reglas)."""
        self.mision.difuso.inferir = self._inferir_con_juego

    def poner_difuso(self, controlador) -> None:
        """Cambia el controlador difuso de la partida en curso (PUT/DELETE /difuso/reglas) y lo vuelve a envolver. Solo esta
        partida: no se guarda en disco ni toca las evaluaciones ni los escenarios de comparación."""
        self.mision.difuso = controlador
        self._envolver_difuso()

    def restaurar_difuso(self) -> None:
        """Vuelve al difuso del planeta (el evolucionado si lo hay, si no el de defecto)."""
        ctrl = FuzzyController(params=self._params_difuso_planeta) if self._params_difuso_planeta else FuzzyController()
        ctrl.personalizado = False
        self.poner_difuso(ctrl)

    def _inferir_con_juego(self, distancia, bateria, inclinacion, temperatura=0.0):
        # ev3-d88 B: solo durante el paso de juego se usa la T_int; el laboratorio /difuso responde con la temperatura que se pide
        inclinacion_real = inclinacion
        if self._en_paso_juego or self._en_sugerencia:
            if termico.ABORTO_TERMICO_ACTIVO and self._termico_activo and self._en_paso_juego:
                temperatura = self.termico.t_int
            if self.mecanicas.activa:
                inclinacion = self._inclinacion_con_hielo(inclinacion)   # R23: el hielo se ve como pendiente
                # R23: el universo del difuso es 0 a 100: recibe el porcentaje de la capacidad, no las unidades del motor
                bateria = self.bateria_pct_difuso(bateria)
        if self._en_paso_juego:
            self._entrada_difuso = {"distancia": float(distancia), "bateria": float(bateria),
                                    "inclinacion": float(inclinacion), "temperatura": float(temperatura)}
        if self._en_paso_juego and self._termico_activo:
            self.mision._ultima_temperatura = float(temperatura)   # solo registro: la T que usó el paso
        res = FuzzyController.inferir(self.mision.difuso, distancia, bateria, inclinacion, temperatura)
        if self._precaucion_ant and (self._en_paso_juego or self._en_sugerencia):
            res.velocidad = min(res.velocidad, VELOCIDAD_PRECAUCION)      # R23: frena antes de un posible barranco
        if self.conduccion and (self._en_paso_juego or self._en_sugerencia) and self.mecanicas.activa:
            res.velocidad = self._topes_conduccion(res.velocidad, inclinacion_real)
        return res

    def _topes_conduccion(self, v: float, inclinacion: float) -> float:
        """Topes de velocidad evolucionados por planeta: sobre hielo, con viento y en pendiente fuerte."""
        c, ruta = self.conduccion, self.mision.ruta
        if len(ruta) > 1 and self.mecanicas.hay_hielo(ruta[1]):
            v = min(v, float(c.get("v_hielo", 1.0)))
        if self.mecanicas.viento_actual >= difuso_planetas.UMBRAL_VIENTO:
            v = min(v, float(c.get("v_viento", 1.0)))
        if inclinacion >= difuso_planetas.UMBRAL_PENDIENTE_GRADOS:
            v = min(v, float(c.get("v_pendiente", 1.0)))
        return v

    def bateria_pct_difuso(self, bateria: float) -> float:
        """R23: batería en % de la capacidad (0 a 100), la unidad del universo del difuso."""
        return float(min(100.0, 100.0 * float(bateria) / max(float(self.capacidad_bateria), 1e-9)))

    def _inclinacion_con_hielo(self, inclinacion: float) -> float:
        """R23: el rover nota el hielo de la celda siguiente de su ruta; el difuso lo recibe como pendiente extra y frena."""
        ruta = self.mision.ruta
        if len(ruta) > 1 and self.mecanicas.hay_hielo(ruta[1]):
            return min(45.0, float(inclinacion) + planetas.HIELO_EQUIV_GRADOS)
        return inclinacion

    def parametros_planeta(self) -> dict:
        """R23 (contrato estable): parámetros del planeta de la partida y la intensidad que le da el nivel.

        Es lo que consulta el AG que optimiza el difuso por planeta. Incluye el perfil completo (`planetas.PerfilPlaneta`),
        `intensidad` (escala del nivel), `activa` (False en la evaluación congelada) y `sobrecosto_medio` (% de batería
        por paso). Siempre devuelve un diccionario nuevo.
        """
        d = planetas.parametros(self.planeta)
        d.update({"intensidad": float(self.intensidad_planeta), "activa": bool(self.mecanicas.activa),
                  "sobrecosto_medio": planetas.sobrecosto_medio(self.planeta, self.intensidad_planeta)})
        return d

    def _sugerencia_sin_efectos(self) -> dict:
        """Observa y decide como lo haría Mision.paso_mision, pero sobre copias.

        No reutiliza paso_mision porque este muta el estado. Se copian el generador aleatorio,
        el sensor, el mapa estimado y la lista de ruta; los helpers de Mision que solo leen o
        escriben en esas copias se reutilizan tal cual sobre una copia superficial de la misión.
        """
        m = self.mision
        pos = self.rover.posicion
        if self.estado in ESTADOS_TERMINALES:
            return _sugerencia("detener", None, 0.0, {}, [], None, ["D-PARTIDA-TERMINADA"])
        if pos == self.mundo.refugio and not m._quedan_sitios():
            return _sugerencia("detener", None, 0.0, {}, [], None, ["D-META-ALCANZADA"])
        if self._falla_restante > 0:
            return _sugerencia("detener", None, 0.0, {}, [], None, ["D-FALLA-SENSOR"])
        if len(m.ruta) < 2:
            return _sugerencia("replanificar", None, 0.0, {}, [], None, ["REPLAN-RUTA-VACIA"])

        # Copias: nada de lo que sigue toca el estado real.
        sombra = copy.copy(m)
        sombra.rng = copy.deepcopy(m.rng)
        sombra.sensor = SensorSuite(rng=sombra.rng, ruido=m.sensor.ruido,
                                    prob_fallo=m.sensor.prob_fallo)
        sombra.riesgo = m.riesgo.copy()
        sombra._actualizar_mapa_estimado = lambda *a: self._actualizar_mapa_percepcion(*a, destino=sombra)
        sombra.ruta = list(m.ruta)

        if self._ruta_inconsistente():
            # la ruta no parte del rover: se pide replanteo en vez de romper la consulta
            return _sugerencia("replanificar", None, 0.0, {}, [], None, ["REPLAN-RUTA-INCONSISTENTE"])
        siguiente = sombra.ruta[1]
        rumbo = _rumbo(pos, siguiente)
        rasgos, _ = _rasgos_celda(self.mundo, pos, rumbo, sombra.sensor, sombra.rng)
        lectura = sombra.sensor.leer(self.mundo, pos, rumbo)
        probs = sombra.rna.explicar(rasgos)["probabilidades"] if m.usar_rna else {"libre": 1.0}
        sombra._actualizar_mapa_estimado(pos, rumbo, lectura["proximidad_frontal_m"])
        for celda in m._barrancos_fusionados(lectura, guardar=False):   # ARX-94f: misma fusión, sin acumular
            sombra.riesgo[celda] = 1.0
        inclinacion = min(45.0, inclinacion_de_rasgos(rasgos) * GRADOS_POR_GRADIENTE)
        fz = sombra.difuso.inferir(sombra._distancia_a_riesgo_en_ruta(), self.rover.bateria, inclinacion)
        if not m.usar_difuso:
            fz = ResultadoDifuso(velocidad=0.5, membresias={}, reglas_activadas=[],
                                 agregado=None, universo=None, fallback=True)
        dec = m.supervisor.decidir(probs, fz.velocidad, lectura, self.rover.bateria)
        if sombra.riesgo[siguiente] >= 0.5:
            dec = Decision("replanificar", 0.0, ["V-RUTA-CON-RIESGO"])
        if m._riesgo_por_rna == self._riesgo_por_rna_partida:      # R23: la regla de la partida, sobre la sombra y sin guardar
            self._riesgo_por_rna_partida(probs, siguiente, dec, destino=sombra, guardar=False)
        else:
            sombra._riesgo_por_rna(probs, siguiente, dec)      # ARX-94c, igual que Mision.paso_mision
        distancia = lectura["proximidad_frontal_m"]
        # incondicional desde ARX-91 (ab46b4a es donde nació la versión que dependía de la parada del difuso)
        if sombra._obstaculo_en_ruta(pos, rumbo, distancia):
            dec = Decision("replanificar", 0.0, ["V-OBSTACULO-EN-RUTA"])
        paros = m.paros_seguidos + 1 if dec.accion == "detener" else 0
        if paros >= PASOS_PARADO_MAXIMO:
            dec = Decision("replanificar", 0.0, ["V-PARADO-SIN-AVANCE"])

        accion_rumbo = rumbo if dec.accion == "avanzar" else None
        return _sugerencia(dec.accion, accion_rumbo,
                           float(fz.velocidad) if dec.accion == "avanzar" else float(dec.velocidad),
                           probs, fz.reglas_activadas if fz else [],
                           self._desglose_ruta(), dec.motivos)

    def _completar_fila(self, datos: dict) -> dict:
        """ARX-80 (M3): toda fila de la bitácora lleva el fitness del AG vigente y las membresías difusas.

        Las membresías las aporta Mision._registrar cuando hubo inferencia; si la fila no la tuvo (recarga,
        falla, cierres, modos rna y ag) queda vacía (None): ese paso no evaluó el difuso.

        fitness_ag: en avanzar_ia es el medido antes de actuar; en las filas de fuera de avanzar_ia es el de la
        ruta tras actuar, no el de antes.
        """
        if self._fitness_paso is not None:
            fit = self._fitness_paso
        else:
            d = self._desglose_ruta()
            fit = d["fitness"] if d else None
        if fit is not None and np.isfinite(fit):
            self._fitness_ultimo = float(fit)
        return {"fitness_ag": round(self._fitness_ultimo, 4), **aplanar_membresias(None)}

    def _desglose_ruta(self):
        """Desglose del fitness del AG para la ruta pendiente desde la posición actual.

        Con un objetivo fijado por el jugador la ruta no es la del AG: se devuelve None.
        """
        m = self.mision
        if not m.ruta or self._objetivo is not None:
            return None
        pos = self.rover.posicion
        pendientes = {p: v for p, v in self.mundo.sitios.items() if p not in m.visitados}
        desde = replace(self.mundo, inicio=pos, sitios=pendientes)
        gp = GeneticPlanner(desde, m.riesgo, bateria=max(self.rover.bateria, 1.0),
                            k_puntos=m.k, poblacion=30, generaciones=30, semilla=m.semilla)
        cromosoma = [o for o in m.objetivos if o in pendientes and o not in m.visitados]
        d = gp.evaluar(cromosoma)
        return {"fitness": float(d.fitness), "ciencia": float(d.ciencia), "distancia": float(d.distancia),
                "energia": float(d.energia), "riesgo": float(d.riesgo), "tiempo": float(d.tiempo),
                "penalizacion": float(d.penalizacion)}

    # ---------- IA: un paso real ----------
    def drones_obligatorios(self) -> bool:
        """Decisión del usuario (14/11): los drones son obligatorios solo desde el nivel Medio (3)."""
        return self.nivel >= 3

    def objetivos_pendientes(self) -> list:
        """Condiciones obligatorias que faltan para ganar: sitios científicos y, desde Medio, drones destruidos."""
        falta = []
        exigidos = self.exigidos()
        total = len(exigidos)
        hechos = len(exigidos & {tuple(c) for c in self.mision.visitados})
        if hechos < total:
            falta.append(f"sitios {hechos}/{total}")
        if self.drones_obligatorios() and self.combate is not None:
            n = len(self.combate.drones)
            if int(self.combate.bajas) < n:
                falta.append(f"drones {int(self.combate.bajas)}/{n}")
        if self.senal_activa is not None:
            falta.append("señal 0/1")
        return falta

    def _revisar_victoria(self) -> None:
        """N4 (decisión del orquestador, 14/11): la victoria exige visitar todos los sitios científicos.

        Si la misión llega al refugio con sitios pendientes, la partida sigue en curso: se replanifica hacia
        los sitios que faltan y se avisa «Faltan objetivos: sitios k/n». Solo FRACASO termina por castigo.
        """
        m = self.mision
        total = len(self.exigidos())      # R23: con plan restringido, los opcionales no hacen falta para ganar
        self._recuperar_sin_ruta()
        falta = self.objetivos_pendientes()
        if not falta:
            self._caza_desde = None
        elif getattr(self, "_caza_desde", None) is not None and m.paso - self._caza_desde > 300:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y no se alcanzaron a tiempo")
            return
        if m.estado == "EXITO" and falta and any(f.startswith("drones") for f in falta) and self._exigidos_cumplidos():
            self._cazar_drones()
            return
        if m.estado == "EXITO" and not self._exigidos_cumplidos():
            hechos = len(self.exigidos() & {tuple(c) for c in m.visitados})
            # una sola replanificación; si no hay ruta a ningún sitio pendiente, la batería no alcanza: se termina (N6)
            m.objetivos = []
            m._planear()
            pendientes = [o for o in m.objetivos if o in self.exigidos() and o not in m.visitados]
            if pendientes:
                m.estado = "EXPLORACION"
                self._avisar(f"Faltan objetivos: sitios {hechos}/{total}")
                return
            # El AG no encontró ruta con el mapa de riesgo estimado. Antes de rendirse, se mira el mapa real:
            # sin ruta real o sin batería para ella, el fracaso dice la causa verdadera (N12, 591531 y 675131).
            ruta, faltan = self._ruta_real_a_sitios()
            if ruta and len(ruta) - 1 + MARGEN_ENERGIA <= self.rover.bateria:
                m.objetivos = faltan + [self.mundo.refugio]
                m.ruta = ruta
                self._planear_con_senal(False)   # 22/11: la ruta por el mapa real no conoce la señal pendiente
                m.estado = "EXPLORACION"
                self._avisar(f"Faltan objetivos: sitios {hechos}/{total}")
            elif ruta and self._ir_a_recargar_por_sitios(faltan):
                self._avisar("Batería baja para los sitios que faltan: la misión va a recargar a una base")
            elif ruta:
                m.estado = "FRACASO"
                self._avisar("Batería insuficiente para llegar a los sitios científicos restantes")
            else:
                m.estado = "FRACASO"
                self._avisar("Sin ruta a los sitios científicos restantes")

    def _ir_a_recargar_por_sitios(self, faltan) -> bool:
        """22/11: con bases de recarga, faltar batería para los sitios restantes no es un fracaso si el rover no está
        lleno y alcanza una base: va a recargar y después retoma los sitios. True si quedó comprometido con una base."""
        if not self.estaciones or self.bateria_max is None or self.rover.bateria >= self.bateria_max * self.umbral_recarga:
            return False
        pos = tuple(int(v) for v in self.rover.posicion)
        mascara = self.mision.riesgo < 0.5
        opciones = []
        for s_ in self.estaciones:
            t = camino_bfs(pos, s_, mascara)
            if t is not None and len(t) - 1 <= self.rover.bateria:
                opciones.append((len(t) - 1, s_))
        if not opciones:
            return False
        self._comprometido = min(opciones)[1]
        # los sitios siguen pendientes (si no, la misión volvería a darse por terminada en el refugio y no se movería)
        self.mision.objetivos = list(faltan) + [tuple(int(v) for v in self.mundo.refugio)]
        self._mover_al_compromiso(pos, mascara)
        return self.mision.estado == "EXPLORACION"

    def _recuperar_sin_ruta(self) -> None:
        """Falso positivo del sensor (INFORME §6, semilla 4036 en Fácil): la misión termina en SIN_RUTA porque el
        mapa de riesgo estimado bloquea el camino, aunque el mapa real tiene ruta a los sitios pendientes o al refugio.
        Se replanifica por el mapa real, como máximo 5 veces por partida, para no entrar en bucle."""
        m = self.mision
        if m.estado != "SIN_RUTA" or getattr(self, "_recuperaciones", 0) >= 5:
            return
        ruta, orden = self._ruta_real_a_sitios()     # sin sitios pendientes, es la ruta de regreso al refugio
        if not ruta or len(ruta) - 1 + MARGEN_ENERGIA > self.rover.bateria:
            return
        self._recuperaciones = getattr(self, "_recuperaciones", 0) + 1
        m.estado = "EXPLORACION"
        m.objetivos = orden + [self.mundo.refugio]
        m.ruta = ruta
        for c in ruta:                       # el mapa real dice que la ruta es libre: se limpia la creencia de riesgo
            if self.mundo.tipo[c] == LIBRE:
                m.riesgo[c] = 0.0
        self._planear_con_senal(False)       # 22/11: la ruta por el mapa real no conoce la señal pendiente
        self._avisar("Replanteo por el mapa real tras quedarse sin ruta estimada")

    def _caza_con_bfs(self) -> bool:
        """Con sitios completos y drones obligatorios vivos, la IA caza por BFS (ARX-66 / N12, ARX-75).
        Aplica a automático, rna, difuso y ag; el manual no caza solo."""
        return (self.modo_ia in ("automatico", "rna", "difuso", "ag") and self.combate is not None
                and self.drones_obligatorios()
                and self._exigidos_cumplidos()
                and any(d.vivo for d in self.combate.drones))

    def _seguir_caza(self) -> None:
        """Mueve la misión hacia el dron vivo más cercano, por el mapa real, con paradas en estaciones si falta
        batería. Nunca llama al AG (ARX-66 / N12)."""
        import numpy as np
        m = self.mision
        if self.combate.municion <= 0:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y no queda munición")
            return
        origen = tuple(int(x) for x in self.rover.posicion)
        # ARX-79c: el BFS de la caza ignora la parada del difuso; si el rover no sale de su celda, el BFS vuelve a
        # trazar la misma ruta y la partida se queda repitiendo D-DIFUSO-LENTO / V-PARADO-SIN-AVANCE. Se corta con causa.
        if getattr(self, "_caza_ult_pos", None) == origen:
            if self._falla_restante == 0:
                self._caza_sin_avance = getattr(self, "_caza_sin_avance", 0) + 1
        else:
            self._caza_ult_pos, self._caza_sin_avance = origen, 0
        if self._caza_sin_avance >= PASOS_CAZA_SIN_AVANCE:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y el rover lleva %d pasos detenido: la caza no avanza" % PASOS_CAZA_SIN_AVANCE)
            return
        # ARX-94f: el BFS de la caza evita primero las celdas con riesgo conocido, como el veto V-RUTA-CON-RIESGO de la
        # misión; si no, trazaba por la zona de un meteorito, la misión vetaba, se volvía a trazar igual y la caza se
        # cortaba por «no avanza» (repro: semilla 2, nivel 5, pequeño). Sin camino seguro, el mapa real como antes.
        mascara_real = np.asarray(self.mundo.tipo == LIBRE)
        mascara_segura = mascara_real & (np.asarray(m.riesgo) < 0.5)
        mascara_segura[origen] = True
        mascara = mascara_segura
        vivos = sorted([d for d in self.combate.drones if d.vivo],
                       key=lambda d: max(abs(d.pos[0] - origen[0]), abs(d.pos[1] - origen[1])))
        tramos, largos = {}, {}

        def tramo(a, b):
            if (a, b) not in tramos:
                t = camino_bfs(a, b, mascara)
                tramos[(a, b)] = None if t is None else [tuple(int(v) for v in x) for x in t]
            return tramos[(a, b)]

        def largo(a, b):
            if (a, b) not in largos:
                t = tramo(a, b)
                largos[(a, b)] = None if t is None else len(t) - 1
            return largos[(a, b)]

        bat_max = self.bateria_max if self.bateria_max is not None else self.rover.bateria
        mejor, hay_ruta = None, False
        if all(largo(origen, tuple(int(x) for x in d.pos)) is None for d in vivos):
            mascara = mascara_real                   # sin camino seguro a ningún dron: el mapa real, como antes
            tramos.clear(); largos.clear()
        for d in vivos:
            objetivo = tuple(int(x) for x in d.pos)
            if largo(origen, objetivo) is not None:
                hay_ruta = True
            c = _plan_con_paradas(origen, [objetivo], self.rover.bateria, bat_max, self.estaciones, largo, tramo,
                                  factor=self.mision.factor_ambiente)
            if c is not None and (mejor is None or len(c) < len(mejor[1])):
                mejor = (objetivo, c)
        if mejor is None:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y la batería no alcanza para llegar" if hay_ruta
                         else "Faltan drones por destruir y ninguno tiene ruta real")
            return
        objetivo, ruta = mejor
        if len(ruta) < 2:   # ya sobre el dron: un paso libre para que la misión no vuelva al AG
            vecinos = [(origen[0] + df, origen[1] + dc) for df, dc in MOVIMIENTOS.values()]
            libre = [v for v in vecinos if self.mundo.dentro(v) and self.mundo.tipo[v] == LIBRE]
            libre.sort(key=lambda v: m.riesgo[v] >= 0.5)   # ARX-94f: primero las vecinas sin riesgo (si no, el veto la frena)
            if not libre:
                m.estado = "FRACASO"
                self._avisar("Faltan drones por destruir y el rover no puede moverse")
                return
            ruta = [origen, libre[0]]
        if getattr(self, "_caza_objetivo", None) != objetivo:
            self._caza_objetivo = objetivo
            n = len(vivos)
            self._avisar(f"Faltan drones: {n} {'vivo' if n == 1 else 'vivos'}; el refugio queda bloqueado hasta destruirlos")
        m.estado = "EXPLORACION"
        m.ruta = ruta
        m.objetivos = [objetivo]

    def _cazar_drones(self) -> None:
        """N12 (decisión del orquestador): el refugio queda bloqueado y el objetivo pasa al dron vivo más cercano.

        Fracasa solo si no hay forma de cumplirlo: el manual no caza solo, no hay munición, no hay dron vivo,
        no hay ruta real al dron o la batería no alcanza.
        """
        m = self.mision
        if self.modo_ia == "manual" or self.combate is None:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir: en manual no se cazan solos; dispara tú con /disparo")
            return
        vivos = [d for d in self.combate.drones if d.vivo]
        if not vivos or self.combate.municion <= 0:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y no queda munición")
            return
        import numpy as np
        mascara = np.asarray(self.mundo.tipo == LIBRE)
        origen = tuple(int(x) for x in self.rover.posicion)
        mejor = None
        for d in sorted(vivos, key=lambda d: max(abs(d.pos[0] - origen[0]), abs(d.pos[1] - origen[1]))):
            objetivo = tuple(int(x) for x in d.pos)
            t = camino_bfs(origen, objetivo, mascara)
            if t is not None and (mejor is None or len(t) < len(mejor[1])):
                mejor = (objetivo, [tuple(int(v) for v in x) for x in t])
        if mejor is None:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y ninguno tiene ruta real")
            return
        objetivo, ruta = mejor
        if len(ruta) - 1 + MARGEN_ENERGIA > self.rover.bateria:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y la batería no alcanza para llegar")
            return
        m.estado = "EXPLORACION"
        m.ruta = ruta
        m.objetivos = [objetivo]           # la misión avanza hacia el dron; el refugio queda bloqueado
        if getattr(self, "_caza_desde", None) is None:
            self._caza_desde = m.paso
        self._avisar(f"Faltan drones: {len(vivos)} vivos; el refugio queda bloqueado hasta destruirlos")

    def _ruta_real_a_sitios(self):
        """Ruta más corta por el mapa real que visita los sitios pendientes y termina en el refugio.

        Prueba todos los órdenes (son pocos sitios) para no fallar por un orden malo. Devuelve (ruta, orden)
        o (None, []) si no hay camino.
        """
        import itertools
        import numpy as np
        m = self.mision
        mascara = np.asarray(self.mundo.tipo == LIBRE)
        origen = tuple(int(x) for x in self.rover.posicion)
        exigidos = self.exigidos()
        pts = [c for c in self.mundo.sitios if c not in m.visitados and c in exigidos]
        if len(pts) > 6:                       # demasiados sitios para probar todos los órdenes: voraz
            pts = sorted(pts, key=lambda c: max(abs(c[0] - origen[0]), abs(c[1] - origen[1])))
        tramos = {}

        def tramo(a, b):
            if (a, b) not in tramos:
                t = camino_bfs(a, b, mascara)
                tramos[(a, b)] = None if t is None else [tuple(int(v) for v in x) for x in t]
            return tramos[(a, b)]

        mejor, mejor_orden = None, []
        for orden in itertools.permutations(pts):
            ruta, cur, ok = [origen], origen, True
            for destino in list(orden) + [self.mundo.refugio]:
                t = tramo(cur, destino)
                if t is None:
                    ok = False
                    break
                ruta.extend(t[1:])
                cur = destino
            if ok and (mejor is None or len(ruta) < len(mejor)):
                mejor, mejor_orden = ruta, list(orden)
        return (mejor, mejor_orden) if mejor is not None else (None, [])

    def _avisar(self, texto: str) -> None:
        """Aviso para la interfaz; la lista se acota para no crecer sin fin (N6). Un aviso repetido seguido no se apila."""
        if self.avisos and self.avisos[-1] == texto:
            return
        self.avisos.append(texto)
        del self.avisos[:-20]

    @_cronometrado
    @_paso_de_juego
    @_paso_de_juego
    def avanzar_modo(self, modo: str, veto: bool = True) -> dict:
        """Un paso conducido solo por rna, difuso o ag (ARX-11). Ver juego/conduccion.py."""
        pos_previa, filas_previas = tuple(int(v) for v in self.rover.posicion), len(self.mision.log.filas)
        resultado = self._avanzar_modo_sin_planeta(modo, veto)
        self._efectos_planeta(pos_previa, filas_previas)
        return resultado

    def _avanzar_modo_sin_planeta(self, modo: str, veto: bool = True) -> dict:
        if self._recargando > 0:
            return self._paso_recarga()
        if self._caza_con_bfs():
            # ARX-75: sitios hechos y drones obligatorios vivos: la caza la mueve el BFS, no la técnica
            self._seguir_caza()
            if self.estado not in ESTADOS_TERMINALES:
                self.mision.paso_mision()
                self._tras_paso_estacion()
                self._revisar_victoria()
                return {"accion": "cazar", "motivos": ["CAZA-DRON-BFS"], **self._posicion_estado()}
            return {"accion": "cazar", "motivos": ["CAZA-DRON-BFS"], **self._posicion_estado()}
        from juego import conduccion
        if self.plan_activo:
            self._ir_a_estacion_si_falta_bateria()      # R23: los modos sueltos no planifican paradas: recargan por reserva
        r = conduccion.avanzar(self, modo, veto)
        self._tras_paso_estacion()
        self._revisar_victoria()
        return r

    # ---------- recarga (ARX-59) ----------
    def _recoger_pila(self) -> None:
        """22/11: si el rover está sobre una pila, la recoge: +10 % de la capacidad, sin pasar de ella."""
        if not self.pilas:
            return
        pos = tuple(int(v) for v in self.rover.posicion)
        if pos not in self.pilas:
            return
        self.pilas.remove(pos)
        self.pilas_recogidas += 1
        antes = float(self.rover.bateria)
        self.rover.bateria = min(self.capacidad_bateria, antes + PILA_FRACCION * self.capacidad_bateria)
        self._avisar(f"Pila recogida: +{round(100 * (self.rover.bateria - antes) / self.capacidad_bateria)} % de batería")

    def _tras_paso_estacion(self) -> None:
        """Si el rover acaba de llegar a una estación con batería por debajo del máximo, se recarga en RECARGA_PASOS."""
        self._recoger_pila()
        self._registrar_visitas()
        if self.plan_activo:
            self._muestrear_gasto()
        self._actualizar_plan()
        if not self.estaciones:
            return
        pos = tuple(int(v) for v in self.rover.posicion)
        if pos == self._comprometido:
            self._comprometido = None
        if pos in self.estaciones:
            self._estacion_reciente = pos
            self._paso_estacion_reciente = self.mision.paso
        if pos not in self.estaciones:
            self._ultima_estacion = None
            return
        if pos != self._ultima_estacion:
            self._ultima_estacion = pos
            if self.rover.bateria < self.bateria_max * self.umbral_recarga and self._conviene_recargar():
                self._recargando = RECARGA_PASOS

    def _coste_restante(self) -> float:
        """R23: pasos que faltan para terminar la misión desde la posición actual: los sitios pendientes (en el orden del
        plan), un margen de caza por cada dron obligatorio vivo y el tramo final al refugio. Por el mapa estimado."""
        m = self.mision
        pos = tuple(int(v) for v in self.rover.posicion)
        refugio = tuple(int(v) for v in self.mundo.refugio)
        pendientes = [tuple(int(v) for v in o) for o in m.objetivos
                      if tuple(int(v) for v in o) in self.mundo.sitios and o not in m.visitados]
        pendientes += [tuple(int(v) for v in o) for o in self.mundo.sitios
                       if o not in m.visitados and tuple(int(v) for v in o) not in pendientes]
        mascara = m.riesgo < 0.5
        total, actual = 0.0, pos
        for destino in pendientes + [refugio]:
            t = camino_bfs(actual, destino, mascara)
            total += (len(t) - 1) if t is not None else 1.5 * _cheb(actual, destino)
            actual = destino
        if self._drones_vivos_obligatorios():
            total += self.margen_caza * sum(1 for d in self.combate.drones if d.vivo)
        return total

    def _conviene_recargar(self) -> bool:
        """R23: parar tres pasos a recargar solo si la batería no alcanza para lo que queda de la misión (con el margen de
        desvío y la reserva). Antes se recargaba siempre al pasar por una base con menos del 90 %, aunque quedaran pocos
        pasos (p. ej. 3 pasos de recarga con el 79 % y la meta a 20 celdas)."""
        if self.bateria_max is None:
            return True
        necesario = self._coste_restante() * self.factor_desvio + MARGEN_ENERGIA
        return bool(self.rover.bateria < necesario)

    def _proximo_punto(self):
        """Próximo punto de la misión: el primer sitio o dron pendiente, o el refugio."""
        m = self.mision
        for o in m.objetivos:
            o = tuple(int(v) for v in o)
            if o in self.mundo.sitios and o in m.visitados:
                continue
            return o
        return tuple(int(v) for v in self.mundo.refugio)

    def _ir_a_estacion_si_falta_bateria(self) -> None:
        """ARX-59: antes de avanzar hacia el próximo punto, se comprueba que alcanza, y desde él a la estación más
        cercana, todo × factor del nivel. Si no alcanza, la misión se compromete con esa estación: va hasta llenar
        y no reevalúa a mitad de camino (evita el bucle de ida y vuelta)."""
        m = self.mision
        if not self.estaciones or self._recargando > 0 or self.estado in ESTADOS_TERMINALES:
            return
        # 22/11: en la partida jugable no se desvía a una base mientras le quede más del 60 % (evita desvíos tempranos)
        if (self._comprometido is None and self._desvio_jugable and self.bateria_max
                and self.rover.bateria > self._umbral_desvio * self.bateria_max):
            return
        pos = tuple(int(v) for v in self.rover.posicion)
        if pos in self.estaciones:
            return
        mascara = m.riesgo < 0.5
        f = self.factor_desvio              # ARX-59: 2,0 (peor tormenta); partida jugable con bases: 1,3
        bat = self.rover.bateria

        def largo(a, b):
            t = camino_bfs(a, b, mascara)
            return None if t is None else len(t) - 1

        if self._comprometido is None:
            siguiente = self._proximo_punto()
            # no se vuelve a la estación que se acaba de dejar (evita el ida y vuelta)
            excluir = self._estacion_reciente if self.mision.paso - self._paso_estacion_reciente < 20 else None
            c1 = largo(pos, siguiente)
            costes2 = [largo(siguiente, s) for s in self.estaciones]
            c2 = min((c for c in costes2 if c is not None), default=None)
            if c1 is not None and c2 is not None and (c1 + c2) * f <= bat:
                return                       # alcanza el próximo punto y después una estación: sigue
            alcanzables = [(largo(pos, s), s) for s in self.estaciones]
            alcanzables = [(d, s) for d, s in alcanzables if d is not None and d * f <= bat]
            # la estación recién dejada solo se descarta si hay otra alcanzable; si es la única, se vuelve a ella
            if excluir is not None and any(s != excluir for _, s in alcanzables):
                alcanzables = [(d, s) for d, s in alcanzables if s != excluir]
            if not alcanzables:
                return                       # ninguna estación se alcanza: la partida acabará por batería
            # salto hacia el próximo punto: una estación alcanzable que lo acerque (así no hay vuelta atrás)
            dist_actual = largo(pos, siguiente)
            saltos = []
            for d, s in alcanzables:
                dn = largo(s, siguiente)
                if dn is not None and (dist_actual is None or dn < dist_actual):
                    saltos.append((dn, s))
            if saltos:
                self._comprometido = min(saltos)[1]
                return self._mover_al_compromiso(pos, mascara)
            if c1 is not None and c1 * f <= bat:
                return                       # llega al próximo punto con lo que tiene: no retrocede a una estación
            if self.bateria_max is not None and bat >= self.bateria_max:
                return                       # llena y ninguna estación acerca: no hay a dónde saltar
            self._comprometido = min(alcanzables)[1]
            self._avisar("Batería baja: la misión va a recargar en la estación más cercana")
        self._mover_al_compromiso(pos, mascara)

    def _mover_al_compromiso(self, pos, mascara) -> None:
        """Pone la ruta hacia la estación comprometida."""
        m = self.mision
        t = camino_bfs(pos, self._comprometido, mascara)
        if t is None:
            self._comprometido = None
            return
        m.ruta = [tuple(int(v) for v in c) for c in t]
        m.estado = "EXPLORACION"

    def _paso_recarga(self) -> dict:
        """Un paso parado en la estación: no se mueve, la batería sube al máximo al terminar."""
        m = self.mision
        self._recargando -= 1
        m.paso += 1
        m.log.registrar(paso=m.paso, estado=m.estado, posicion=str(self.rover.posicion),
                        bateria=round(self.rover.bateria, 2), accion="recargar", velocidad=0.0,
                        p_barranco=None, p_obstaculo=None, reglas="", motivos="RECARGA")
        if self._recargando == 0:
            antes = float(self.rover.bateria)
            objetivo = float(self.bateria_max)
            if self.recarga_parcial:
                # R23: la base entrega lo que la misión necesita (con el margen de desvío, la reserva y un colchón del
                # 10 % de la capacidad), no siempre el 100 %: así recargar no regala la partida
                necesario = self._coste_restante() * self.factor_desvio + MARGEN_ENERGIA + COLCHON_RECARGA * self.bateria_max
                objetivo = min(objetivo, max(antes, necesario))
            self.rover.bateria = objetivo
            self.recargas_hechas += 1
            if objetivo >= float(self.bateria_max) - 1e-9:
                self._avisar("Recarga completa: batería al máximo")
            else:
                self._avisar(f"Recarga: +{round(100 * (objetivo - antes) / self.bateria_max)} % de batería (lo que pide la misión)")
        return {**self.sugerencia(), **self._posicion_estado()}

    def _ruta_inconsistente(self) -> bool:
        """La ruta debe empezar en la posición real del rover y su siguiente celda debe ser adyacente.

        Si no, `_rumbo` lanzaría ValueError en mitad de la partida (caso reportado el 14/11, semilla 641752).
        """
        ruta = self.mision.ruta
        if len(ruta) < 2:
            return False
        pos = tuple(int(x) for x in self.rover.posicion)
        if tuple(int(x) for x in ruta[0]) != pos:
            return True
        return max(abs(ruta[1][0] - pos[0]), abs(ruta[1][1] - pos[1])) > 1

    @_cronometrado
    @_paso_de_juego
    def avanzar_ia(self) -> dict:
        m = self.mision
        if self.estado in ESTADOS_TERMINALES:
            return {**self.sugerencia(), **self._posicion_estado()}
        if self._recargando > 0:
            return self._paso_recarga()
        if self._caza_con_bfs():
            self._seguir_caza()        # la caza va por BFS hacia el dron vivo más cercano, sin replanificar el AG
        elif m.objetivos and any(o not in self.mundo.sitios and o != self.mundo.refugio and o != self.senal_activa
                                 for o in m.objetivos):
            # la caza terminó: el objetivo vuelve al refugio (y a los sitios que queden) por el AG, una vez
            m.objetivos = [o for o in m.objetivos if (o in self.mundo.sitios and o not in m.visitados)
                           or o == self.senal_activa] + [self.mundo.refugio]
            m._planear()
        self._revisar_energia_plan()
        self._anticipar()
        self._ir_a_estacion_si_falta_bateria()
        if self._ruta_inconsistente():
            # corrección defensiva: se replanifica desde la posición real antes de decidir
            m._planear()
        decision = self.sugerencia()
        if self._falla_restante > 0:
            self._paso_con_falla()
            return {**decision, **self._posicion_estado()}

        paso_previo, filas_previas = m.paso, len(m.log.filas)
        des = decision.get("desglose")
        self._fitness_paso = des["fitness"] if des else None     # ARX-80: el fitness medido antes de actuar
        pos_previa, visitados_previos = self.rover.posicion, set(m.visitados)     # ARX-28c: para el resbalón
        try:
            m.paso_mision()
            if self.fisica_velocidad:
                self._resbalar_si_corresponde(pos_previa, filas_previas, visitados_previos)
            self._efectos_planeta(tuple(int(v) for v in pos_previa), filas_previas)
            ui = m.ultima_ia
            if ui and ui.get("paso") == m.paso:
                ui["tramo"] = self._tramo_clasificado(ui)
            if self.mecanicas.activa and ui and ui.get("paso") == m.paso and self._entrada_difuso:
                # R23: lo que vio el difuso: la inclinación (con el hielo) y la batería en % de la capacidad, aparte de las unidades
                ui["difuso"] = {**ui["difuso"], "inclinacion": self._entrada_difuso["inclinacion"],
                                "bateria_pct": self._entrada_difuso["bateria"]}
            self._tras_paso_estacion()
            self._revisar_victoria()
            if m.paso > paso_previo:
                self._revisar_objetivo()
                self._tick_ambiente()
                if len(m.log.filas) == filas_previas:
                    # Mision no registra los cierres (EXITO o SIN_RUTA): se anota para tener una fila por paso.
                    # N7: «fin» solo con un estado final; si la partida sigue (p. ej. faltan objetivos), es un replanteo.
                    terminal = m.estado in ESTADOS_TERMINALES
                    m.log.registrar(paso=m.paso, estado=m.estado, posicion=str(self.rover.posicion),
                                    bateria=round(self.rover.bateria, 2),
                                    accion="fin" if terminal else "replanificar",
                                    velocidad=0.0, p_barranco=None, p_obstaculo=None,
                                    reglas="", motivos=m.estado if terminal else "FALTAN-OBJETIVOS")
        finally:
            self._fitness_paso = None
        return {**decision, **self._posicion_estado()}

    def _resbalar_si_corresponde(self, pos_previa, filas_previas, visitados_previos) -> None:
        """ARX-28c: tras un avance, si la celda alcanzada es empinada, resbala con probabilidad P_RESBALON * velocidad.

        El rover vuelve a la celda anterior, gasta COSTO_RESBALON y la bitácora anota D-RESBALON. Despacio no resbala.

        La inclinación se mide con la elevación REAL del mundo (mundo.elevacion), no con la estimada que ve el difuso.
        """
        m = self.mision
        if len(m.log.filas) != filas_previas + 1:
            return
        fila = m.log.filas[-1]
        nueva = self.rover.posicion
        if fila.get("accion") != "avanzar" or nueva == pos_previa:
            return
        v = float(fila.get("velocidad") or 0.0)
        if v < VELOCIDAD_SIN_RESBALON:
            return
        inclinacion = abs(float(self.mundo.elevacion[nueva] - self.mundo.elevacion[pos_previa])) * GRADOS_POR_GRADIENTE
        if inclinacion <= INCLINACION_RESBALON:
            return
        if self._rng_resbalon.random() >= P_RESBALON * v:
            return
        self.rover.posicion = pos_previa
        self.rover.consumir(COSTO_RESBALON)
        m.ruta.insert(0, pos_previa)       # la celda alcanzada vuelve a ser la siguiente de la ruta
        if nueva in self.mundo.sitios and nueva in m.visitados and nueva not in visitados_previos:
            m.visitados.discard(nueva)
        self.resbalones += 1
        fila["posicion"] = str(pos_previa)
        fila["bateria"] = round(self.rover.bateria, 2)
        fila["motivos"] = (fila["motivos"] + ";" if fila.get("motivos") else "") + "D-RESBALON"

    def _efectos_planeta(self, pos_previa, filas_previas: int) -> None:
        """R23: tras un avance de una celda, aplica las mecánicas del planeta (gravedad, pendiente, viento, hielo).

        Gasta el sobrecoste de energía, y si el viento de costado o el hielo desplazan al rover, lo mueve, arregla la
        ruta (la celda alcanzada vuelve a ser la siguiente) y anota D-VIENTO o D-HIELO en la fila del paso. En el
        refugio no hay desplazamiento. No hace nada fuera de la partida jugable.
        """
        mec = self.mecanicas
        if not mec.activa or self.estado in ESTADOS_TERMINALES:
            return
        m = self.mision
        destino = tuple(int(v) for v in self.rover.posicion)
        if destino == pos_previa or max(abs(destino[0] - pos_previa[0]), abs(destino[1] - pos_previa[1])) != 1:
            return
        nueva_fila = len(m.log.filas) == filas_previas + 1
        fila = m.log.filas[-1] if nueva_fila else None
        v = float((fila or {}).get("velocidad") or 0.0)
        if v <= 0.0:
            v = planetas.VELOCIDAD_MANUAL                  # manual o técnica sin velocidad propia
        extra = mec.costo_extra(pos_previa, destino, v)["total"]
        if extra > 0:
            self.rover.consumir(extra)
            mec.energia_extra += extra
        nueva, motivo = mec.perturbar(pos_previa, destino, v, lambda c: self.mundo.transitable(c))
        if destino == tuple(int(x) for x in self.mundo.refugio):
            nueva, motivo = destino, None                   # la llegada al refugio no se desplaza
        if nueva != destino:
            nueva = (int(nueva[0]), int(nueva[1]))
            if motivo == "D-HIELO":
                self.rover.consumir(planetas.COSTO_DESLIZ)
                mec.energia_extra += planetas.COSTO_DESLIZ
            self.rover.posicion = nueva
            ruta = m.ruta
            if len(ruta) > 1 and tuple(ruta[0]) == destino and tuple(ruta[1]) == nueva:
                ruta.pop(0)                                 # el deslizamiento llevó justo a la celda que seguía
            elif ruta and tuple(ruta[0]) == destino:
                ruta.insert(0, nueva)                       # vuelve a la celda alcanzada y sigue
            if nueva in self.mundo.sitios:
                m.visitados.add(nueva)
            self._avisar_planeta(motivo)
        if fila is not None:
            if nueva != destino:
                fila["posicion"] = str(nueva)
                fila["motivos"] = (fila["motivos"] + ";" if fila.get("motivos") else "") + motivo
            fila["bateria"] = round(self.rover.bateria, 2)
        if self.rover.bateria <= 0 and self.estado not in ESTADOS_TERMINALES:
            m.estado = "FRACASO"

    def _avisar_planeta(self, motivo) -> None:
        """Aviso de interfaz la primera vez que el viento o el hielo desplazan al rover."""
        if motivo == "D-HIELO" and self.mecanicas.resbalones_hielo == 1:
            self._avisar("Hielo: el rover patinó; a menos velocidad no resbala")
        elif motivo == "D-VIENTO" and self.mecanicas.desvios_viento == 1:
            self._avisar("Viento: una ráfaga desvió al rover de su rumbo")

    def _paso_con_falla(self) -> None:
        """Paso de IA detenida por falla de sensor: no llama a paso_mision ni mueve al rover."""
        m = self.mision
        m.paso += 1
        self._falla_restante -= 1
        if self._falla_restante == 0 and self._prob_fallo_base is not None:
            m.sensor.prob_fallo = self._prob_fallo_base
        self._tick_ambiente()
        m.log.registrar(paso=m.paso, estado=m.estado, posicion=str(self.rover.posicion),
                        bateria=round(self.rover.bateria, 2), accion="detener",
                        velocidad=0.0, p_barranco=None, p_obstaculo=None,
                        reglas="", motivos="D-FALLA-SENSOR")

    def _posicion_estado(self) -> dict:
        return {"posicion": self.rover.posicion, "bateria": float(self.rover.bateria), "estado": self.estado}

    # ---------- R23 (AG): plan con ventanas de tiempo, recarga obligatoria y sitios opcionales ----------
    def _iniciar_plan_restringido(self, planeta) -> None:
        """Crea los sitios del plan (id, valor, ventana, obligatorio) y el factor de energía con que se planifica.

        Las ventanas se centran en las llegadas de un recorrido de referencia (`_plan_de_referencia`) con anchos por nivel
        (`dificultad.VENTANAS_POR_NIVEL`); un sitio sin ventana vale siempre el 100 %. Determinista con la semilla del mundo."""
        mundo = self.mundo
        self.factor_plan_base = float(self.mision.factor_ambiente) * MARGEN_FACTOR_PLAN
        self.factor_plan = self.factor_plan_base
        self._gasto_ema = self.factor_plan_base / MARGEN_FACTOR_PLAN     # gasto observado por paso (% de batería)
        self._gasto_prev = None
        self._paso_replan_energia = -100
        self._olvidos = 0                      # veces que se olvidaron las dudas de la RNA para recuperar un sitio inalcanzable
        self._rna_olvidada = False
        obligatorios = _sitios_obligatorios(mundo)
        celdas = sorted(mundo.sitios)
        base = [planificacion.SitioPlan(i + 1, c, float(mundo.sitios[c]), None, c in obligatorios)
                for i, c in enumerate(celdas)]
        frac, ancho_min, ancho_max = dificultad.VENTANAS_POR_NIVEL[self.nivel]
        rng = np.random.default_rng([int(self.semilla_mundo), 6262])
        ventanas = {}
        try:
            prob, ref = _plan_de_referencia(mundo, base, self.estaciones, self.capacidad_bateria, self.capacidad_bateria,
                                            self.factor_plan, 0.0, self.semilla_mundo)
            llegadas = {n[2]: n[3] for n in ref.nodos if n[0] == "sitio"} if ref.factible else {}
        except Exception:
            llegadas = {}
        for s in base:
            u, a, b = float(rng.random()), int(rng.integers(ancho_min, ancho_max + 1)), int(rng.integers(ancho_min, ancho_max + 1))
            if s.id in llegadas and u < frac:
                ventanas[s.id] = (max(0, llegadas[s.id] - a), llegadas[s.id] + b)
        self.sitios_plan = {s.celda: planificacion.SitioPlan(s.id, s.celda, s.valor, ventanas.get(s.id), s.obligatorio)
                            for s in base}

    def exigidos(self) -> set:
        """Celdas de los sitios que hay que visitar para ganar (con plan restringido, todos menos los opcionales)."""
        if self.plan_activo and self.sitios_plan:
            return {c for c, s in self.sitios_plan.items() if s.obligatorio}
        return {tuple(c) for c in self.mundo.sitios}

    def _exigidos_cumplidos(self) -> bool:
        return self.exigidos() <= {tuple(c) for c in self.mision.visitados}

    def _registrar_visitas(self) -> None:
        """Anota el paso de la primera visita de cada sitio (solo registro; sirve a la ventana de tiempo y a la ciencia)."""
        for c in self.mision.visitados:
            self.visitas.setdefault(tuple(c), int(self.mision.paso))

    def ciencia(self) -> dict:
        """Ciencia recogida: valor de cada sitio visitado por la calidad de su ventana (1,0 dentro, CALIDAD_FUERA fuera)."""
        self._registrar_visitas()
        total = float(sum(self.mundo.sitios.values())) or 1.0
        if not self.plan_activo or not self.sitios_plan:
            rec = float(sum(self.mundo.sitios[c] for c in self.visitas if c in self.mundo.sitios))
        else:
            rec = 0.0
            for c, paso in self.visitas.items():
                s = self.sitios_plan.get(c)
                if s is not None:
                    q = 1.0 if s.ventana is None or s.ventana[0] <= paso <= s.ventana[1] else planificacion.CALIDAD_FUERA_VENTANA
                    rec += s.valor * q
        return {"recogida": round(rec, 3), "maxima": total, "fraccion": round(rec / total, 4)}

    def _reserva_caza(self) -> float:
        """Batería (%) que el plan deja para cazar los drones obligatorios vivos (como `_coste_restante`)."""
        if getattr(self, "combate", None) is None or not self._drones_vivos_obligatorios():
            return 0.0
        return float(self.margen_caza * sum(1 for d in self.combate.drones if d.vivo) * getattr(self, "factor_plan", 1.0))

    def _problema_plan(self, origen, pendientes):
        """`planificacion.Problema` del estado actual: posición, batería, paso, mapa estimado y sitios pendientes."""
        m = self.mision
        origen = (int(origen[0]), int(origen[1]))
        refugio = tuple(int(v) for v in self.mundo.refugio)
        mascara = np.asarray(m.riesgo < 0.5).copy()
        mascara[origen] = True
        mascara[refugio] = True
        sitios = [self.sitios_plan[tuple(c)] for c in sorted(pendientes) if tuple(c) in self.sitios_plan]
        self.factor_plan = max(self.factor_plan_base, self._gasto_ema * MARGEN_FACTOR_PLAN)   # el gasto real manda
        return planificacion.Problema(origen, refugio, sitios, self.estaciones, self.rover.bateria, self.capacidad_bateria,
                                      planificacion.Distancias.de(mascara), self.factor_plan,
                                      reserva_extra=self._reserva_caza(), t0=int(m.paso),
                                      margen_escape=MARGEN_ESCAPE_PLAN * float(self.capacidad_bateria))

    def _cromosoma_de_wp(self, prob):
        """Cromosoma (orden, sel, paradas) del plan vigente sobre `prob`: las paradas que quedan, en su orden."""
        por_celda = {s.celda: s for s in prob.sitios}
        orden, paradas = [], [-1] * (prob.n + 1)
        for tipo, celda, ident in self._wp:
            if tipo == "sitio" and tuple(celda) in por_celda and por_celda[tuple(celda)].id not in orden:
                orden.append(por_celda[tuple(celda)].id)
            elif tipo == "base" and paradas[len(orden)] < 0 and ident is not None and 0 <= ident < len(prob.bases):
                paradas[len(orden)] = int(ident)
        incluidos = set(orden)
        sel = [s.id in incluidos for s in prob.sitios]
        resto = [s.id for s in prob.sitios if s.id not in incluidos]
        return (tuple(orden + resto), tuple(sel), tuple(paradas))

    def _cromosomas_semilla(self, prob) -> list:
        """Semillas del AG en un replanteo: el plan vigente y los órdenes del vecino más cercano y del 2-opt."""
        if self._plan_inicial_pendiente or not prob.n:
            return []
        semillas = []
        if self._wp:
            semillas.append(self._cromosoma_de_wp(prob))
        for f in (planificacion.orden_vecino, planificacion.orden_2opt):
            semillas.append((tuple(f(prob)), tuple([True] * prob.n), tuple([-1] * (prob.n + 1))))
        return semillas

    def _guardar_evolucion(self, prob, res) -> None:
        """Guarda la evolución del AG del plan inicial en el formato de GET /ag/evolucion (no se recalcula en cada llamada)."""
        def cand(plan, con_camino):
            ordenes = [n[2] for n in plan.nodos if n[0] == "sitio"]
            recargas, paradas, vistos = [], [], 0
            for n in plan.nodos:
                if n[0] == "sitio":
                    vistos += 1
                elif n[0] == "base":
                    recargas.append(vistos - 1)      # índice en `orden` del sitio tras el cual se recarga (-1: antes del primero)
                    paradas.append({"despues_de": vistos - 1, "base": [int(n[1][0]), int(n[1][1])]})
            camino = None
            if con_camino:
                ruta = prob.ruta(plan)
                camino = [[int(c[0]), int(c[1])] for c in ruta] if ruta else None
            return {"orden": [int(i) for i in ordenes], "recargas": recargas, "paradas": paradas, "camino": camino,
                    "fitness": round(float(plan.fitness), 5), "factible": bool(plan.factible),
                    "violaciones": prob.textos(plan), "sacrificados": [int(i) for i in plan.sacrificados],
                    "ciencia": round(float(plan.ciencia), 4), "pasos": int(plan.pasos)}
        ultima = len(res.historial) - 1
        gens = []
        for h in res.historial:
            primero = h["n"] in (0, ultima)
            gens.append({"n": int(h["n"]), "mejor": round(h["mejor"], 5), "media": round(h["media"], 5),
                         "peor": round(h["peor"], 5), "diversidad": round(h["diversidad"], 4),
                         "distintos": int(h["distintos"]),
                         "candidatos": [cand(pl, primero or i == 0) for i, pl in enumerate(h["candidatos"])]})
        self.evolucion_inicial = {
            "hay_plan": True, "planeta": self.planeta,
            "inicio": [int(v) for v in prob.inicio], "refugio": [int(v) for v in prob.refugio],
            "sitios": [{"id": int(s.id), "celda": [int(s.celda[0]), int(s.celda[1])], "valor": float(s.valor),
                        "ventana": list(s.ventana) if s.ventana else None, "unidad_ventana": "pasos",
                        "obligatorio": bool(s.obligatorio)}
                       for s in prob.sitios],
            "bases": [[int(b[0]), int(b[1])] for b in prob.bases],
            "generaciones": gens, "mejor": cand(res.mejor, True),
            "parametros_difuso": dict(getattr(self, "parametros_difuso", {}) or {}),
            "tiempo_s": round(float(res.tiempo_s), 3),
            "evaluaciones": int(res.evaluaciones), "ultima_mejora": int(res.ultima_mejora),
            "capacidad": float(prob.capacidad), "factor_energia": round(float(prob.factor), 3),
        }

    def _muestrear_gasto(self) -> None:
        """Media móvil del gasto de batería por paso movido (incluye viento, pendiente, hielo y tormentas): el plan la usa como
        factor de energía si supera la estimación del planeta."""
        pos, bat = tuple(int(v) for v in self.rover.posicion), float(self.rover.bateria)
        prev = self._gasto_prev
        if prev is not None and pos != prev[0] and bat < prev[1] and _cheb(pos, prev[0]) <= 2:
            self._gasto_ema = 0.12 * (prev[1] - bat) + 0.88 * self._gasto_ema
        self._gasto_prev = (pos, bat)

    def _revisar_energia_plan(self) -> None:
        """Cada paso de la IA: si con el gasto de ahora el plan vigente ya no llega sin una recarga que no tiene, se replantea
        (la reparación inserta la parada o, si no cabe, corre el AG). Evita llegar a la base «por reserva» demasiado tarde."""
        m = self.mision
        if not (self.plan_activo and self._wp and m.objetivos and self._objetivo is None) or self.estado in ESTADOS_TERMINALES:
            return
        if getattr(m._optimizar_ag, "plan", None) is None:
            return
        origen = tuple(int(v) for v in self.rover.posicion)
        pendientes = {c: v for c, v in self.mundo.sitios.items() if c not in m.visitados}
        if not pendientes:
            return
        prob = self._problema_plan(origen, pendientes)
        plan = prob.decodificar(*self._cromosoma_de_wp(prob))
        if plan.reparaciones > 0 or not plan.factible:
            # sin plan factible el replanteo cuesta un AG: no más de uno cada 6 pasos (si no, se repetiría en cada paso)
            if plan.factible or m.paso - self._paso_replan_energia >= 6:
                self._paso_replan_energia = m.paso
                m._planear()

    def _actualizar_plan(self) -> None:
        """Quita del plan vigente los sitios ya visitados y la base donde está el rover (ya pasó por ella)."""
        if not self._wp:
            return
        m = self.mision
        pos = tuple(int(v) for v in self.rover.posicion)
        wp = [w for w in self._wp if not (w[0] == "sitio" and tuple(w[1]) in m.visitados)]
        while wp and wp[0][0] == "base" and tuple(wp[0][1]) == pos:
            wp.pop(0)
        self._wp = wp

    def _planear_restringido(self) -> bool:
        """Sustituye a Mision._planear en la partida jugable. Replanteo barato si ya hay plan (el mismo plan, recalculado con
        el mapa, la batería y el paso de ahora, con la reparación de recargas); si eso no es factible, o no hay plan, corre
        el AG (más corto que el inicial). El plan decide también las paradas de recarga: la ruta pasa por las bases."""
        m = self.mision
        m.replanes += 1
        origen = tuple(int(v) for v in self.rover.posicion)
        refugio = tuple(int(v) for v in self.mundo.refugio)
        for c in self._celdas_conocidas():       # bases, sitios, inicio y refugio son libres por construcción: una marca es un falso positivo
            if m.riesgo[c] >= 0.5:
                m.riesgo[c] = 0.05
        self._actualizar_plan()
        pendientes = {c: v for c, v in self.mundo.sitios.items() if c not in m.visitados}
        prob = plan = None
        ruta = []
        if self._wp and m.objetivos and pendientes and getattr(m._optimizar_ag, "plan", None) is not None:
            prob = self._problema_plan(origen, pendientes)
            plan = prob.decodificar(*self._cromosoma_de_wp(prob))
            if plan.factible:
                ruta = prob.ruta(plan) or []
            if not ruta:
                plan = None
        if plan is None:
            ruta = m._optimizar_ag(origen, pendientes)
            plan = getattr(m._optimizar_ag, "plan", None)
            prob = getattr(m._optimizar_ag, "problema", None)
            if plan is None:                              # optimizador ajeno (variantes antiguas): la ruta tal cual
                self._wp = []
                m.objetivos = [c for c in ruta if c in self.mundo.sitios] + [refugio]
                m.ruta = ruta if camino_valido(ruta, m.riesgo) else (_bfs_a(m, origen, refugio) or [])
                return bool(m.ruta) and m.ruta[-1] == refugio
            if (not plan.factible or not ruta) and self._olvidos < OLVIDOS_MAXIMOS and prob is not None                     and any(prob.dist.largo(origen, sit.celda) is None for sit in prob.sitios if sit.obligatorio):
                # un sitio obligatorio quedó inalcanzable en el mapa estimado: las dudas de la RNA (riesgo entre 0,5 y 1, no medido)
                # lo habrán cerrado. Se olvidan y se planifica de nuevo (las lecturas firmes, riesgo 1, se conservan)
                dudas = (m.riesgo >= 0.5) & (m.riesgo < 0.99)
                if dudas.any():
                    self._olvidos += 1
                    m.riesgo[dudas] = 0.05
                    self._rna_olvidada = True
                    self._wp = []
                    ruta = m._optimizar_ag(origen, pendientes)
                    plan = getattr(m._optimizar_ag, "plan", None)
                    prob = getattr(m._optimizar_ag, "problema", None)
            if not plan.factible or not ruta:
                # sin plan con las restricciones: se intenta al menos llegar al refugio recargando
                alivio = self._problema_plan(origen, {})
                directo = alivio.decodificar((), (), (-1,))
                ruta = alivio.ruta(directo) if directo.factible else None
                wp_alivio = [(n[0], n[1], n[2]) for n in directo.nodos[1:] if n[0] == "base"] if directo.factible else []
                if not ruta:
                    # ni al refugio llega: se va a la base alcanzable más cercana (recargar es lo único que salva la partida)
                    cerca = [(len(t) - 1, i) for i, b in enumerate(self.estaciones)
                             for t in [camino_bfs(origen, tuple(b), m.riesgo < 0.5)] if t is not None
                             and len(t) - 1 <= self.rover.bateria]
                    if cerca:
                        _, i = min(cerca)
                        ruta = camino_bfs(origen, tuple(self.estaciones[i]), m.riesgo < 0.5)
                        wp_alivio = [("base", tuple(self.estaciones[i]), i)]
                    else:
                        ruta = camino_bfs(origen, refugio, m.riesgo < 0.5) or []
                m.objetivos = [refugio]
                self._wp = wp_alivio
                m.ruta = ruta if camino_valido(ruta, m.riesgo) else []
                return bool(m.ruta) and (m.ruta[-1] == refugio or bool(wp_alivio))     # ir a una base también es un plan
        m.objetivos = [n[1] for n in plan.nodos if n[0] == "sitio"] + [refugio]
        self._wp = [(n[0], n[1], n[2]) for n in plan.nodos[1:] if n[0] in ("base", "sitio")]
        m.ruta = ruta if camino_valido(ruta, m.riesgo) else []
        return bool(m.ruta) and m.ruta[-1] == refugio

    # ---------- RNA con anticipación (R23) ----------
    def _anticipar(self) -> None:
        """Clasifica con la RNA de anticipación las celdas de la ruta a 2, 3 y 4 pasos (lecturas con ruido creciente, generador
        propio). Una celda con p(barranco) alta frena el paso; con la media de al menos dos observaciones sobre el umbral, queda como
        riesgo y se replantea la ruta antes de llegar a ella. No hace nada sin RNA (ablación sin_rna) ni fuera de la partida jugable."""
        self._ant_ultima, self._precaucion_ant = [], False
        m = self.mision
        if not (self.anticipacion_activa and m.usar_rna) or len(m.ruta) < 3 or self.estado in ESTADOS_TERMINALES:
            return
        pos = tuple(int(v) for v in self.rover.posicion)
        if tuple(int(v) for v in m.ruta[0]) != pos:
            return
        rna = anticipacion.rna_anticipacion(round(float(m.sensor.ruido), 3))
        conocidas = self._celdas_conocidas()
        marcada = False
        for k in anticipacion.DISTANCIAS:
            if len(m.ruta) <= k:
                break
            celda = tuple(int(v) for v in m.ruta[k])
            anterior = tuple(int(v) for v in m.ruta[k - 1])
            if celda in conocidas or m.riesgo[celda] >= 0.5:
                continue
            rng = np.random.default_rng([int(self.semilla), 7777, int(m.paso), k])
            probs = rna.probabilidades(anticipacion.rasgos_anticipacion(
                self.mundo, pos, anterior, celda, k, rng, float(m.sensor.ruido), self._ambiente))
            pb = float(probs.get("barranco", 0.0))
            self._ant_suma[celda] += pb
            self._ant_n[celda] += 1
            media = float(self._ant_suma[celda] / self._ant_n[celda])
            marca = self._ant_n[celda] >= 2 and media >= UMBRAL_ANT_MARCA
            if marca:
                m.riesgo[celda] = max(m.riesgo[celda], 0.6)
                marcada = True
            if pb >= UMBRAL_ANT_PRECAUCION or marca:
                self._precaucion_ant = True
            self._ant_ultima.append({"celda": [celda[0], celda[1]], "distancia": int(k), "probabilidades": probs,
                                     "media_observaciones": round(media, 4), "observaciones": int(self._ant_n[celda]),
                                     "marcada": bool(marca)})
        if marcada:
            m._planear()

    def _tramo_clasificado(self, ui) -> list:
        """Clasificación por celda del tramo de ruta del paso: la celda siguiente (RNA original, distancia 1) y las de 2 a 4 pasos
        (RNA de anticipación). Cada elemento: {celda, distancia, probabilidades, fuente}."""
        tramo = [{"celda": [int(ui["celda"][0]), int(ui["celda"][1])], "distancia": 1,
                  "probabilidades": dict(ui["probabilidades"]), "fuente": "rna"}]
        tramo += [{"celda": e["celda"], "distancia": e["distancia"], "probabilidades": dict(e["probabilidades"]),
                   "fuente": "anticipacion", "marcada": e["marcada"]} for e in self._ant_ultima]
        return tramo

    # ---------- RNA: confirmación y celdas conocidas (R23) ----------
    def _celdas_conocidas(self) -> set:
        """Celdas que el rover conoce por el mapa orbital y son libres: bases, sitios, inicio y refugio."""
        m = self.mision
        celdas = {tuple(int(v) for v in e) for e in self.estaciones}
        celdas |= {tuple(int(v) for v in c) for c in self.mundo.sitios}
        celdas |= {tuple(int(v) for v in self.mundo.inicio), tuple(int(v) for v in self.mundo.refugio)}
        return celdas

    def _barrancos_fusionados_partida(self, lectura, guardar: bool = True) -> set:
        """Mision._barrancos_fusionados sin las celdas conocidas (bases, sitios, inicio, refugio): con tormenta el ruido del telémetro
        marcaba como barranco una celda libre sobre la que hay que pasar (en una prueba, un sitio obligatorio quedó inalcanzable)."""
        marcadas = Mision._barrancos_fusionados(self.mision, lectura, guardar)
        return marcadas - self._celdas_conocidas()

    def _riesgo_por_rna_partida(self, probs, celda, dec, destino=None, guardar: bool = True) -> None:
        """Como Mision._riesgo_por_rna (riesgo[celda] = max(riesgo, p) y nota RNA-RIESGO) con dos cambios de R23: no marca
        celdas conocidas y, con `confirmar_rna`, exige OBSERVACIONES_RNA_CONFIRMA observaciones con media > 0,5 también con el
        ruido nominal. `destino`: la misión sobre la que se escribe (la sombra de sugerencia() usa guardar=False)."""
        from integracion import RUIDO_NOMINAL_RNA, UMBRAL_RIESGO_RNA
        m = destino if destino is not None else self.mision
        if not m.usar_rna:
            return
        celda = (int(celda[0]), int(celda[1]))
        if celda in self._celdas_conocidas():
            return
        p = probs.get("barranco", 0.0)
        if self.confirmar_rna or float(m.sensor.ruido) > RUIDO_NOMINAL_RNA + 1e-9:
            suma, n = m._rna_suma[celda] + p, m._rna_n[celda] + 1
            if guardar:
                m._rna_suma[celda], m._rna_n[celda] = suma, n
            if n < OBSERVACIONES_RNA_CONFIRMA:
                return
            p = float(suma / n)
        if p > UMBRAL_RIESGO_RNA and p > m.riesgo[celda]:
            dec.motivos.append(f"RNA-RIESGO:{celda}:{p:.2f}")
            if dec.accion == "avanzar":
                # la confirmación llegó en este mismo paso con una lectura actual bajo el umbral: no se avanza hacia una celda
                # que acaba de quedar como barranco (el rover quedaría sobre una celda de riesgo y sin ruta)
                dec.accion, dec.velocidad = "replanificar", 0.0
                dec.motivos.append("V-RNA-BARRANCO-CONFIRMADO")
        m.riesgo[celda] = max(m.riesgo[celda], p)

    # ---------- regla de percepción (ARX-90) ----------
    def _actualizar_mapa_percepcion(self, pos, rumbo, distancia, destino=None):
        """Regla de percepción (ARX-90): un sensor ruidoso no marca como riesgo un sitio pendiente, el inicio ni el refugio.

        Esas celdas son LIBRE por construcción, así que marcarlas es siempre un falso positivo, y una marca basta para
        bloquear la ruta y agotar las recuperaciones (ARX-90, semilla 7 del escenario exigente). Envuelve, sobre la
        instancia, a Mision._actualizar_mapa_estimado (Mision está congelada). Igual para las cuatro variantes del arnés.

        Riesgo conocido (no corregido en ARX-90): una lectura ruidosa que sitúa el obstáculo una celda más lejos puede causar
        colisión; desde ARX-91 la ablación sin difuso también consulta _obstaculo_en_ruta (chequeo incondicional). Ejemplo: exigente, semilla 20,
        sin difuso, paso 31 (celda (14,27), obstáculo estimado a 0,05).
        """
        m = destino if destino is not None else self.mision
        celda = m._celda_observada(pos, rumbo, distancia)
        if celda is not None and (celda in (m.mundo.inicio, m.mundo.refugio) or celda in getattr(self, "estaciones", ())
                                  or (celda in m.mundo.sitios and celda not in m.visitados)):
            return
        Mision._actualizar_mapa_estimado(m, pos, rumbo, distancia)

    # ---------- planificación con objetivo fijado (ev3-d27) ----------
    def _planear_con_objetivo(self) -> bool:
        """Sustituye a Mision._planear: sin objetivo, plan normal; con objetivo, BFS hacia él."""
        m = self.mision
        if self._objetivo is None:
            if self.plan_activo:
                if not m.objetivos:
                    self._wp = []                     # plan nuevo: el AG vuelve a decidir (eventos graves, planificación inicial)
                r = self._planear_restringido()
            elif getattr(m, "estaciones_activas", False):
                r = self._planear_con_estaciones()
            else:
                r = Mision._planear(m)
            return self._planear_con_senal(r)
        m.replanes += 1
        ruta = camino_bfs(self.rover.posicion, self._objetivo, m.riesgo < 0.5) or []
        if len(ruta) < 2 or not camino_valido(ruta, m.riesgo):
            # Si el mapa estimado ya no deja camino, el objetivo se descarta y vuelve el plan normal.
            self._objetivo = None
            return Mision._planear(m)
        m.ruta = ruta
        return True

    def _planear_con_senal(self, resultado: bool) -> bool:
        """ARX-30c: el plan del AG no conoce la señal biológica; si está pendiente se vuelve a poner en mision.objetivos
        y la ruta pasa a ser la cadena BFS de Mision por los objetivos pendientes (misma vía que ya usa Mision)."""
        m = self.mision
        celda = self.senal_activa
        if celda is None:
            return resultado
        if celda not in m.objetivos:
            m.objetivos = [celda] + list(m.objetivos)
        ruta = m._ruta_bfs(self.rover.posicion)
        if ruta and camino_valido(ruta, m.riesgo):
            m.ruta = ruta
            return ruta[-1] == self.mundo.refugio
        return resultado

    def _marcar_senal(self) -> None:
        """Marca la señal como visitada cuando el rover pisa su celda y la quita de mision.objetivos."""
        celda = self.senal_activa
        if celda is None or tuple(self.rover.posicion) != tuple(celda):
            return
        for s in self.senales:
            if tuple(s["celda"]) == tuple(celda):
                s["visitada"] = True
        self.mision.objetivos = [o for o in self.mision.objetivos if tuple(o) != tuple(celda)]
        self._avisar("Lectura anómala registrada en la celda de la señal; no confirma vida")

    def _planear_con_estaciones(self) -> bool:
        """ARX-59: el plan de sitios y refugio ya incluye paradas en estaciones (lo valida la garantía). Mision._planear
        descartaría los sitios si la ruta total pasa de la batería, y con paradas eso es normal."""
        m = self.mision
        m.replanes += 1
        origen = self.rover.posicion
        refugio = self.mundo.refugio
        pendientes = {p: v for p, v in self.mundo.sitios.items() if p not in m.visitados}
        ruta = m._optimizar_ag(origen, pendientes) if pendientes else []
        if pendientes:
            m.objetivos = [c for c in ruta if c in self.mundo.sitios] + [refugio]
        else:
            m.objetivos = [refugio]
        if not ruta or len(ruta) < 2:
            ruta = camino_bfs(origen, refugio, m.riesgo < 0.5) or []
        m.ruta = ruta
        return True

    def _revisar_objetivo(self) -> bool:
        """Si el rover llegó al objetivo fijado, lo limpia y la IA vuelve al plan normal."""
        if self._objetivo is not None and self.rover.posicion == self._objetivo:
            self._objetivo = None
            self.mision._planear()
            return True
        return False

    def fijar_objetivo(self, celda) -> dict:
        """La IA planea y sigue la ruta hacia `celda`. None quita el objetivo y vuelve al plan normal."""
        m = self.mision
        if celda is None:
            if self._objetivo is not None:
                self._objetivo = None
                m._planear()
            return {"ok": True, "detalle": "objetivo quitado: la IA vuelve al plan normal"}
        if self.estado in ESTADOS_TERMINALES:
            return {"ok": False, "detalle": "partida terminada"}
        try:
            destino = (int(celda[0]), int(celda[1]))
        except (TypeError, ValueError, IndexError):
            return {"ok": False, "detalle": f"celda inválida: {celda!r}"}
        if not self.mundo.dentro(destino):
            return {"ok": False, "detalle": f"{destino} está fuera del mapa"}
        if not self.mundo.transitable(destino):
            return {"ok": False, "detalle": f"{destino} no es transitable"}
        origen = self.rover.posicion
        if destino == origen:
            return {"ok": False, "detalle": "el rover ya está en esa celda"}
        ruta = camino_bfs(origen, destino, m.riesgo < 0.5)
        if not ruta:
            return {"ok": False, "detalle": f"sin camino conocido hasta {destino}"}
        self._objetivo = destino
        m._planear()
        return {"ok": True, "detalle": f"objetivo en {destino}, {len(ruta) - 1} pasos"}

    # ---------- jugador ----------
    @_cronometrado
    def mover_jugador(self, rumbo: str) -> dict:
        m = self.mision
        if self.estado in ESTADOS_TERMINALES:
            return self._resultado_movimiento(False, "partida terminada")
        if rumbo not in RUMBOS_JUGADOR:
            return self._resultado_movimiento(False, f"rumbo inválido: {rumbo!r}")
        if self.rover.en_modo_seguro:
            return self._resultado_movimiento(False, "rover en modo seguro")
        if self.rover.bateria <= 0:
            return self._resultado_movimiento(False, "sin batería")
        if self.modo_ia == "manual" and self.enlace_restante > 0 and self._rng_enlace.random() < PROB_ORDEN_PERDIDA:
            # ARX-30b (ev3-d48 A): la orden no llega; el tiempo pasa igual y el rover no se mueve
            m.paso += 1
            self._tick_ambiente()
            m.log.registrar(paso=m.paso, estado=m.estado, posicion=str(self.rover.posicion),
                            bateria=round(self.rover.bateria, 2), accion="detener", velocidad=0.0,
                            p_barranco=None, p_obstaculo=None, reglas="", motivos="D-SIN-ENLACE")
            return self._resultado_movimiento(False, "sin enlace")
        df, dc = RUMBOS_JUGADOR[rumbo]
        destino = (self.rover.posicion[0] + df, self.rover.posicion[1] + dc)
        if not self.mundo.dentro(destino):
            return self._resultado_movimiento(False, "fuera del mapa")
        tipo = self.mundo.tipo[destino]
        if tipo == BARRANCO:
            return self._resultado_movimiento(False, "barranco: movimiento bloqueado")
        if tipo == OBSTACULO:
            return self._resultado_movimiento(False, "obstáculo: movimiento bloqueado")
        if rumbo in MOVIMIENTOS:
            if not paso_fisico(self.mundo, self.rover, rumbo):
                return self._resultado_movimiento(False, "movimiento bloqueado")
        else:
            # Diagonal: misma regla de transitable que las cardinales, pero cuesta COSTO_DIAGONAL.
            if not self.mundo.transitable(destino):
                return self._resultado_movimiento(False, "movimiento bloqueado")
            self.rover.rumbo = rumbo
            self.rover.consumir(COSTO_DIAGONAL)
            self.rover.posicion = destino
            self.rover.distancia_recorrida += 1

        pos_previa = tuple(int(v) for v in (destino[0] - df, destino[1] - dc))
        self._efectos_planeta(pos_previa, len(m.log.filas))     # R23: gravedad, viento y hielo también al conducir a mano
        pos = self.rover.posicion
        if pos in self.mundo.sitios:
            m.visitados.add(pos)
        # Conducir cambia la posición: el plan de la IA se reconstruye desde la nueva celda.
        if not self._revisar_objetivo():
            if len(m.ruta) > 1 and m.ruta[1] == pos:
                m.ruta.pop(0)
            else:
                m._planear()
        m.paso += 1        # ARX-30c (QA B1): un movimiento logrado avanza el mismo paso que una orden perdida
        self._tick_ambiente()
        self._actualizar_estado_tras_movimiento()
        return self._resultado_movimiento(True, "movido")

    def _actualizar_estado_tras_movimiento(self) -> None:
        m = self.mision
        self._tras_paso_estacion()
        if self.estado in ESTADOS_TERMINALES:
            return
        if self.rover.bateria <= 0:
            m.estado = "FRACASO"
        elif self.rover.posicion == self.mundo.refugio and not m._quedan_sitios():
            m.estado = "EXITO"

    def _drones_vivos_obligatorios(self) -> bool:
        return (self.drones_obligatorios() and self.combate is not None
                and any(d.vivo for d in self.combate.drones))

    def _resultado_movimiento(self, movido: bool, motivo: str) -> dict:
        return {"movido": movido, "motivo": motivo, **self._posicion_estado()}

    # ---------- ambiente (ev3-d25) ----------
    def _iniciar_ambiente(self, tipo: str) -> None:
        self._ambiente = tipo
        self._ambiente_restante = PASOS_AMBIENTE[tipo]

    def _tick_ambiente(self) -> None:
        """Un paso de ambiente: consume batería extra si hay tormenta o noche, o tira el dado de inicio."""
        self._marcar_senal()
        self.mecanicas.avanzar_clima()                  # R23: ráfagas de viento del planeta
        if self._ambiente_restante > 0:
            self.rover.consumir(COSTO_AMBIENTE[self._ambiente])
            self._ambiente_restante -= 1
            if self._ambiente_restante == 0:
                self._ambiente = "normal"
        elif self._rng_ambiente.random() < PROB_AMBIENTE:
            tipo = "tormenta" if self._rng_ambiente.random() < 0.5 else "noche"
            self._iniciar_ambiente(tipo)
        elif self.mecanicas.tormenta_de_polvo():
            self._iniciar_ambiente("tormenta")        # R23: Marte tiene más tormentas de polvo (generador propio)
        # ARX-30: meteoritos que caen solos en la partida jugable, con probabilidad por nivel
        if (self.meteoritos_activos and "meteorito" in self.eventos_activos
                and self.estado not in ESTADOS_TERMINALES
                and self._rng_ambiente.random() < METEORITO_PROB_POR_NIVEL[self.nivel]):
            self._evento_meteorito()
        # ARX-30a: sismo espontáneo con generador propio, después del bloque de meteoritos
        if (self.meteoritos_activos and "sismo" in self.eventos_activos
                and self.estado not in ESTADOS_TERMINALES
                and self._rng_sismo.random() < SISMO_PROB_POR_NIVEL[self.nivel]):
            self._evento_sismo()
        # ARX-30b: el corte de enlace se descuenta y puede caer solo (generador propio, tras el bloque de sismo)
        if self.enlace_restante > 0:
            self.enlace_restante -= 1
        elif (self.meteoritos_activos and "baja_conectividad" in self.eventos_activos
                and self.estado not in ESTADOS_TERMINALES
                and self._rng_enlace.random() < ENLACE_PROB_POR_NIVEL[self.nivel]):
            self._evento_baja_conectividad()
        # ARX-30c (ev3-d50 C): la señal cae sola en todos los niveles, con generador propio; las reglas de ev3-d51 A
        # (un solo objetivo pendiente, batería sin margen) las aplica _evento_senal_biologica: si no cabe, no se crea
        if (self.meteoritos_activos and "senal_biologica" in self.eventos_activos
                and self.estado not in ESTADOS_TERMINALES
                and self._rng_senal.random() < SENAL_PROB_POR_NIVEL[self.nivel]):
            self._evento_senal_biologica()
        self._tick_termico()
        if self.rover.bateria <= 0 and self.estado not in ESTADOS_TERMINALES:
            self.mision.estado = "FRACASO"

    def _tick_termico(self) -> None:
        """ARX-83a: actualiza T_int y, con la bandera encendida, aborta con MODO_SEGURO y V-TEMPERATURA tras más de
        PASOS_MAXIMOS_SOBRE_TOLERANCIA pasos seguidos sobre la tolerancia."""
        if not self._termico_activo or self.estado in ESTADOS_TERMINALES:
            return
        self.termico.paso(termico.es_sombra(self.mundo, self.rover.posicion))
        if self.termico.pasos_sobre_tolerancia == termico.PASOS_MAXIMOS_SOBRE_TOLERANCIA + 1:
            # ev3-d88 B, opción A: exceso sostenido, solo aviso con código y bitácora (sin MODO_SEGURO)
            self._avisar(f"T-SOBRE-TOLERANCIA: {self.t_int:.0f} °C interna, más de "
                         f"{termico.PASOS_MAXIMOS_SOBRE_TOLERANCIA} pasos sobre {self.termico.tolerancia:.0f} °C")
            self.mision._registrar("temperatura", 0.0, ["T-SOBRE-TOLERANCIA"], {}, None)
        if termico.ABORTO_TERMICO_ACTIVO and self.termico.debe_abortar:
            m = self.mision
            self.rover.en_modo_seguro = True
            m.estado = "MODO_SEGURO"
            m._registrar("modo_seguro", 0.0, ["V-TEMPERATURA"], {}, None)
            self._avisar(f"Aborto térmico: {self.t_int:.0f} °C interna, más de "
                         f"{termico.PASOS_MAXIMOS_SOBRE_TOLERANCIA} pasos sobre {self.termico.tolerancia:.0f} °C")

    # ---------- eventos ----------
    @_cronometrado
    def disparar_evento(self, nombre: str) -> dict:
        if nombre not in EVENTOS_SOPORTADOS or nombre not in self.eventos_activos:
            return {"ok": False, "detalle": f"evento no soportado: {nombre!r}"}
        if nombre == "barranco":
            return self._evento_barranco()
        if nombre == "falla_sensor":
            return self._evento_falla_sensor()
        if nombre == "meteorito":
            return self._evento_meteorito()
        if nombre == "sismo":
            return self._evento_sismo()
        if nombre == "baja_conectividad":
            return self._evento_baja_conectividad()
        if nombre == "senal_biologica":
            return self._evento_senal_biologica()
        if nombre in PASOS_AMBIENTE:
            self._iniciar_ambiente(nombre)
            return {"ok": True, "detalle": f"{nombre} durante {PASOS_AMBIENTE[nombre]} pasos"}
        return self._evento_bateria_baja()

    def _replanear_ag(self, motivo: str) -> bool:
        """ARX-31a: vuelve a correr el AG ante un evento grave (motivo en EVENTOS_GRAVES, en mayúsculas en la fila).

        Vacía mision.objetivos, llama a la planificación (AG), pone paros_seguidos en 0 y anota una fila
        «replanificar» con REPLAN-AG-<MOTIVO>. Como máximo uno por paso. No actúa (devuelve False) si la partida
        terminó, si el jugador fijó un objetivo o si se está cazando drones por BFS: ahí el plan no es del AG.
        """
        m = self.mision
        if (self.estado in ESTADOS_TERMINALES or self._objetivo is not None or self._caza_con_bfs()
                or self._paso_replan_ag == m.paso):
            return False
        self._paso_replan_ag = m.paso
        m.objetivos = []
        m.paros_seguidos = 0
        m._planear()
        m._registrar("replanificar", 0.0, [f"REPLAN-AG-{motivo.upper()}"], {}, None)
        return True

    def _evento_meteorito(self) -> dict:
        """ARX-30: impacto a 2–3 celdas del rover. La celda del impacto y su entorno quedan como zona de riesgo (el
        supervisor veta entrar y la misión replanifica); el impacto cuesta DANO_METEORITO de batería."""
        f, c = self.rover.posicion
        candidatas = []
        for df in range(-3, 4):
            for dc in range(-3, 4):
                celda = (f + df, c + dc)
                if max(abs(df), abs(dc)) < 2 or not self.mundo.dentro(celda):
                    continue
                if self.mundo.tipo[celda] != LIBRE or celda in self.mundo.sitios or celda in (self.mundo.inicio, self.mundo.refugio):
                    continue
                candidatas.append(celda)
        if not candidatas:
            return {"ok": False, "detalle": "sin celda libre para el impacto"}
        impacto = candidatas[int(self._rng_ambiente.integers(len(candidatas)))]
        self.mision.riesgo[impacto] = 1.0
        for df, dc in MOVIMIENTOS.values():
            vecina = (impacto[0] + df, impacto[1] + dc)
            if self.mundo.dentro(vecina) and self.mundo.tipo[vecina] == LIBRE and vecina != self.rover.posicion:
                self.mision.riesgo[vecina] = max(float(self.mision.riesgo[vecina]), 0.6)
        self.rover.consumir(DANO_METEORITO)
        zona = [impacto] + [(impacto[0] + df, impacto[1] + dc) for df, dc in MOVIMIENTOS.values()
                            if self.mundo.dentro((impacto[0] + df, impacto[1] + dc))
                            and self.mundo.tipo[(impacto[0] + df, impacto[1] + dc)] == LIBRE]
        self.meteoritos.append({"paso": int(self.mision.paso), "impacto": impacto, "zona_riesgo": zona})
        ruta = {tuple(x) for x in (self.mision.ruta or [])}
        if "meteorito" in EVENTOS_GRAVES and any(tuple(z) in ruta for z in zona):
            self._replanear_ag("meteorito")
        self._avisar("Meteorito: impacto en una zona de riesgo cercana")
        return {"ok": True, "detalle": f"meteorito en {impacto}; zona de riesgo alrededor", "impacto": impacto}

    def _evento_sismo(self) -> dict:
        """ARX-30a: hasta GRIETAS_POR_NIVEL grietas (BARRANCO) en celdas libres a distancia Chebyshev 2–4 del rover.
        Cada grieta deja el refugio y los sitios pendientes alcanzables por el mapa real, o se descarta. Si una cae
        en la ruta, la misión replanifica (AG) y se anota REPLAN-SISMO. Sin daño de batería."""
        f, c = self.rover.posicion
        excluidas = {tuple(self.rover.posicion), tuple(self.mundo.inicio), tuple(self.mundo.refugio),
                     *(tuple(s) for s in self.mundo.sitios), *(tuple(e) for e in self.estaciones)}
        candidatas = []
        for df in range(-4, 5):
            for dc in range(-4, 5):
                celda = (f + df, c + dc)
                if max(abs(df), abs(dc)) < 2 or not self.mundo.dentro(celda) or celda in excluidas:
                    continue
                if self.mundo.tipo[celda] != LIBRE:
                    continue
                candidatas.append(celda)
        pendientes = [tuple(s) for s in self.mundo.sitios if s not in self.mision.visitados]
        grietas = []
        orden = [candidatas[i] for i in self._rng_sismo.permutation(len(candidatas))] if candidatas else []
        for celda in orden:
            if len(grietas) >= GRIETAS_POR_NIVEL[self.nivel]:
                break
            self.mundo.marcar_barranco(celda)
            alcanzables = _alcanzables(self.mundo, tuple(self.rover.posicion))
            if tuple(self.mundo.refugio) in alcanzables and all(s in alcanzables for s in pendientes):
                grietas.append(celda)
            else:
                self.mundo.tipo[celda] = LIBRE      # descarta: la grieta aislaría el refugio o un sitio
        if not grietas:
            return {"ok": False, "detalle": "sin celda segura para una grieta"}
        for g in grietas:
            self.mision.riesgo[g] = 1.0
        ruta = {tuple(x) for x in (self.mision.ruta or [])}
        if any(g in ruta for g in grietas):
            if not ("sismo" in EVENTOS_GRAVES and self._replanear_ag("sismo")):
                self.mision._planear()
                self.mision._registrar("replanificar", 0.0, ["REPLAN-SISMO"], {}, None)
        self.sismos.append({"paso": int(self.mision.paso), "grietas": grietas})
        self._avisar("Sismo: grietas nuevas cerca del rover")
        return {"ok": True, "detalle": f"sismo: {len(grietas)} grieta(s) en {grietas}", "grietas": grietas}

    def _evento_baja_conectividad(self) -> dict:
        """ARX-30b (ev3-d48 A): corte de enlace de PASOS_SIN_ENLACE pasos. En manual, cada orden de /mover se pierde con
        PROB_ORDEN_PERDIDA; en los modos de IA el rover sigue, pero /intervencion y /recomendacion responden 409."""
        if self.estado in ESTADOS_TERMINALES:
            return {"ok": False, "detalle": "partida terminada"}
        self.enlace_restante = PASOS_SIN_ENLACE
        self._ultimo_corte = int(self.mision.paso)
        self._avisar("Baja conectividad: sin enlace con la base")
        return {"ok": True, "detalle": f"baja conectividad: sin enlace {PASOS_SIN_ENLACE} pasos",
                "restante": int(self.enlace_restante)}

    def _ganable_con_senal(self, celda) -> bool:
        """ARX-66 con la señal: desde la posición actual hay un orden señal, sitios pendientes y refugio que cabe en la
        batería (con paradas en estaciones, como _es_ganable). Cuenta además la caza de los drones obligatorios vivos
        (cazas con MARGEN_CAZA, igual que _es_ganable) y reserva DANO_METEORITO si el meteorito está activo."""
        import itertools
        mascara = np.asarray(self.mundo.tipo == LIBRE)
        origen = tuple(int(x) for x in self.rover.posicion)
        pendientes = [tuple(int(v) for v in s) for s in self.mundo.sitios if s not in self.mision.visitados]
        refugio = tuple(int(v) for v in self.mundo.refugio)
        tramos, largos = {}, {}

        def tramo(a, b):
            if (a, b) not in tramos:
                t = camino_bfs(a, b, mascara)
                tramos[(a, b)] = None if t is None else [tuple(int(v) for v in x) for x in t]
            return tramos[(a, b)]

        def largo(a, b):
            if (a, b) not in largos:
                t = tramo(a, b)
                largos[(a, b)] = None if t is None else len(t) - 1
            return largos[(a, b)]

        bat_max = self.bateria_max if self.bateria_max is not None else self.rover.bateria
        est = [tuple(int(v) for v in e) for e in self.estaciones]
        cazas = []
        if self.drones_obligatorios() and self.combate is not None:
            cazas = [tuple(int(v) for v in d.pos) for d in self.combate.drones if d.vivo]
        if len(pendientes) + len(cazas) > 6:        # la señal va primero y no se permuta
            return False
        bateria = self.rover.bateria
        if "meteorito" in self.eventos_activos:
            bateria -= DANO_METEORITO
        for orden_s in itertools.permutations(pendientes):
            for orden_d in itertools.permutations(cazas):
                seq = [celda, *orden_s, *orden_d, refugio]
                if _plan_con_paradas(origen, seq, bateria, bat_max, est, largo, tramo, cazas,
                                     factor=self.mision.factor_ambiente * self.factor_seguridad,
                                     margen_caza_pasos=self.margen_caza) is not None:
                    return True
        return False

    def _evento_senal_biologica(self) -> dict:
        """ARX-30c (ev3-d49 B): señal anómala en una celda libre a distancia 3–6 del rover. La celda entra en
        mision.objetivos como sitio obligatorio para ganar. Siempre «no confirma vida». Si no se puede llegar a ella
        sin dejar la partida sin ganar (ARX-66), responde ok False y no cambia nada."""
        if self.estado in ESTADOS_TERMINALES:
            return {"ok": False, "detalle": "partida terminada"}
        if self.senal_activa is not None:
            return {"ok": False, "detalle": "ya hay una señal biológica sin visitar"}
        f, c = self.rover.posicion
        excluidas = {tuple(self.rover.posicion), tuple(self.mundo.inicio), tuple(self.mundo.refugio),
                     *(tuple(s) for s in self.mundo.sitios), *(tuple(e) for e in self.estaciones)}
        candidatas = []
        for df in range(-SENAL_DIST_MAX, SENAL_DIST_MAX + 1):
            for dc in range(-SENAL_DIST_MAX, SENAL_DIST_MAX + 1):
                celda = (f + df, c + dc)
                if max(abs(df), abs(dc)) < SENAL_DIST_MIN or not self.mundo.dentro(celda) or celda in excluidas:
                    continue
                if self.mundo.tipo[celda] != LIBRE or self.mision.riesgo[celda] >= 0.5:
                    continue
                candidatas.append(celda)
        alcanzables = _alcanzables(self.mundo, tuple(self.rover.posicion))
        pendientes = [tuple(s) for s in self.mundo.sitios if s not in self.mision.visitados]
        if len(pendientes) <= 1:      # ev3-d51 A: casi lista, la señal no aparece
            return {"ok": False, "detalle": "queda un solo objetivo: no aparece la señal"}
        orden = [candidatas[i] for i in self._rng_senal.permutation(len(candidatas))] if candidatas else []
        celda = None
        hubo_alcanzable = False
        for cand in orden:
            cand = (int(cand[0]), int(cand[1]))
            if (cand in alcanzables and tuple(self.mundo.refugio) in alcanzables
                    and all(s in alcanzables for s in pendientes)):
                hubo_alcanzable = True
                if self._ganable_con_senal(cand):      # ev3-d51 A: batería para ir, volver y terminar (comprobación existente)
                    celda = cand
                    break
        if celda is None:
            if hubo_alcanzable:
                return {"ok": False, "detalle": "batería insuficiente para la señal"}
            return {"ok": False, "detalle": "sin celda alcanzable que deje la partida ganable"}
        self.senales.append({"paso": int(self.mision.paso), "celda": celda, "visitada": False})
        if not ("senal_biologica" in EVENTOS_GRAVES and self._replanear_ag("senal")):
            self._planear_con_senal(True)
        self._avisar(TEXTO_SENAL)
        return {"ok": True, "detalle": f"señal anómala en {celda}; no confirma vida", "celda": celda,
                "afirma_vida": False}

    def celda_para_barranco(self):
        """Dónde aparece el barranco del evento (22/11: «enfrente, cerca de la ruta»). Primero una celda de la ruta 2 a 4
        pasos por delante que no aísle el refugio ni los sitios pendientes; si no hay, la regla anterior (primera
        celda adyacente libre). Nunca un sitio, el inicio ni el refugio. None si no hay ninguna."""
        def valida(celda):
            return (self.mundo.dentro(celda) and self.mundo.tipo[celda] == LIBRE and celda not in self.mundo.sitios
                    and celda not in (self.mundo.inicio, self.mundo.refugio) and celda != tuple(self.rover.posicion))
        ruta = [tuple(int(v) for v in x) for x in (self.mision.ruta or [])]
        pendientes = [tuple(s_) for s_ in self.mundo.sitios if s_ not in self.mision.visitados]
        for celda in ruta[2:5]:
            if not valida(celda):
                continue
            previo = self.mundo.tipo[celda]
            self.mundo.tipo[celda] = BARRANCO             # prueba sin efectos: se restaura enseguida
            alcanzables = _alcanzables(self.mundo, tuple(self.rover.posicion))
            self.mundo.tipo[celda] = previo
            if tuple(self.mundo.refugio) in alcanzables and all(s_ in alcanzables for s_ in pendientes):
                return celda
        f, c = self.rover.posicion
        for df, dc in MOVIMIENTOS.values():
            if valida((f + df, c + dc)):
                return (f + df, c + dc)
        return None

    def _evento_barranco(self) -> dict:
        celda = self.celda_para_barranco()
        if celda is None:
            return {"ok": False, "detalle": "sin celda libre cerca del rover"}
        self.mundo.marcar_barranco(celda)
        self.mision.riesgo[celda] = 1.0
        if "barranco" in EVENTOS_GRAVES and celda in {tuple(x) for x in (self.mision.ruta or [])}:
            self._replanear_ag("barranco")
        return {"ok": True, "detalle": f"barranco en {celda}", "celdas": [[int(celda[0]), int(celda[1])]]}

    def _evento_falla_sensor(self) -> dict:
        """La IA se detiene PASOS_FALLA_SENSOR pasos (ev3-d23 B). No usa el modo seguro.

        La marca prob_fallo=1.0 en el sensor es solo visible: mientras dura la falla la IA no lee el sensor.
        """
        sensor = self.mision.sensor
        if self._falla_restante == 0:
            self._prob_fallo_base = sensor.prob_fallo
        sensor.prob_fallo = 1.0
        self._falla_restante = PASOS_FALLA_SENSOR
        return {"ok": True, "detalle": f"falla de sensor: la IA se detiene {PASOS_FALLA_SENSOR} pasos"}

    def _evento_bateria_baja(self) -> dict:
        self.rover.bateria = BATERIA_BAJA
        return {"ok": True, "detalle": f"batería fijada en {BATERIA_BAJA}"}

    # ---------- puntaje (ev3-d24) ----------
    def puntaje(self) -> int:
        m = self.mision
        total = len(self.mundo.sitios)
        if self.plan_activo:
            cientifica = 100.0 * self.ciencia()["fraccion"]      # R23: valor de cada sitio por la calidad de su ventana
        else:
            cientifica = 100 * len(m.visitados) / total if total else 0.0
        bonus = 50 if m.vetos == 0 else 0
        return int(round(cientifica + 0.5 * self.rover.bateria + bonus))

    # ---------- salidas ----------
    def bitacora(self) -> pd.DataFrame:
        return self.mision.log.a_dataframe()

    def resumen(self) -> dict:
        return {**self.mision.resumen(), "nivel": self.nivel, "puntaje": self.puntaje(),
                "ciencia": self.ciencia() if self.plan_activo else None}


def _sugerencia(accion, rumbo, velocidad, probs, reglas, desglose, motivos):
    return {
        "rumbo": rumbo,
        "accion": accion,
        "velocidad": float(velocidad),
        "p_barranco": float(probs.get("barranco", 0.0)),
        "p_obstaculo": float(probs.get("obstáculo", 0.0)),
        "p_libre": float(probs.get("libre", 0.0)),
        "reglas": [(r[0], float(r[1]), r[2]) for r in reglas],
        "desglose": desglose,
        "motivos": list(motivos),
    }
