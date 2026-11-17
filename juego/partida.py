"""ARES-X · Juego: motor de partida (agente M, contrato v2 en juego/CONTRATO_V2.md).

Envuelve Mision (integracion.py) sin modificar los módulos congelados. El jugador conduce con
mover_jugador(); la IA sugiere con sugerencia() (sin efectos) y ejecuta con avanzar_ia().
"""
import copy
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genetico import GeneticPlanner, camino_bfs  # noqa: E402
from integracion import (ESTADOS_TERMINALES, MARGEN_ENERGIA,  # noqa: E402
                         GRADOS_POR_GRADIENTE, PASOS_PARADO_MAXIMO,
                         Decision, Mision, _rumbo, camino_valido)
from difuso import ResultadoDifuso, aplanar_membresias  # noqa: E402
from juego import termico  # noqa: E402
from rna import _rasgos_celda  # noqa: E402
from simulador import (BARRANCO, LIBRE, MOVIMIENTOS, OBSTACULO, SensorSuite,  # noqa: E402
                       generar_mundo, paso_fisico)

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


MARGEN_CAZA = 10   # pasos extra estimados por cada dron obligatorio (persecución desde su zona de patrulla)


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


def _plan_con_paradas(origen, seq, bateria, bateria_max, estaciones, largo, tramo, cazas=(), factor=1.0):
    """Camino por la secuencia seq (sitios, drones, refugio) con paradas en estaciones cuando falta batería.

    Un tramo directo cuesta largo × factor. Si no alcanza, se busca una cadena de estaciones (ARX-59).
    Devuelve la lista de celdas, o None si no hay forma de llegar al final con MARGEN_ENERGIA.
    Cada dron de cazas cuesta MARGEN_CAZA pasos extra. Tras una estación la batería vuelve al máximo.
    """
    camino, pos, bat = [origen], origen, float(bateria)
    for destino in seq:
        extra = MARGEN_CAZA if destino in cazas else 0
        d = largo(pos, destino)
        if d is not None and d * factor <= bat:
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


def _es_ganable(mundo, bateria: float, drones=(), bateria_max=None, estaciones=(), factor=1.0) -> bool:
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
            if _plan_con_paradas(origen, seq, bateria, tope, est, largo, tramo, cazas, factor) is not None:
                return True
    return False


def _ag_con_todos_los_sitios(m, optimizar_original):
    """ARX-66 / ARX-59: la ruta visita todos los sitios pendientes, en el orden más corto por el mapa real, con
    paradas en estaciones cuando falta batería. El AG no decide qué sitios se visitan (la victoria los exige todos).
    Con pocos sitios se prueban todos los órdenes; la ruta que usa la misión es la que validó la garantía."""
    import itertools

    def optimizar(origen, pendientes):
        ruta_ag = optimizar_original(origen, pendientes)
        if not pendientes:
            return ruta_ag
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
        mejor = None
        candidatos = itertools.permutations(pts) if len(pts) <= 6 else [tuple(pts)]
        for orden in candidatos:
            seq = list(orden) + [tuple(int(v) for v in m.mundo.refugio)]
            if con_estaciones:
                c = _plan_con_paradas(origen, seq, m.rover.bateria, m.bateria_max, m.estaciones, largo, tramo,
                                      factor=m.factor_ambiente)
            else:
                c = [origen]
                for destino in seq:
                    t = tramo(c[-1], destino)
                    if t is None:
                        c = None
                        break
                    c.extend(t[1:])
            if c is not None and (mejor is None or len(c) < len(mejor)):
                mejor = c
        return mejor if mejor is not None else ruta_ag
    return optimizar


class Partida:
    def __init__(self, semilla: int = 11, bateria: float = None, nivel: int = 1,
                 eventos_activos=EVENTOS_SOPORTADOS, filas: int = FILAS_BASE, columnas: int = COLUMNAS_BASE,
                 garantia: bool = True, planeta: str = termico.PLANETA_POR_DEFECTO):
        if isinstance(nivel, bool) or not isinstance(nivel, int) or not 1 <= nivel <= NIVEL_MAX:
            raise ValueError(f"nivel inválido: {nivel!r} (debe estar entre 1 y {NIVEL_MAX})")
        con_estaciones = bool(garantia) and ESTACIONES_ACTIVAS   # ARX-59: solo con la bandera encendida
        if bateria is None:
            bateria = BATERIA_MAX_POR_NIVEL[nivel] if con_estaciones else 100.0 - 4.0 * (nivel - 1)
        self.nivel = nivel
        self.semilla = semilla
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
                                 n_sitios=3 if nivel <= 2 else 4)
        mundo = _generar(semilla)
        self.semilla_mundo = semilla
        if garantia:
            # ARX-66: toda partida generada debe ser ganable (sitios, drones obligatorios y regreso al refugio con la
            # batería inicial). Si no lo es, se prueba una variante determinista del mismo mapa; la semilla no cambia.
            bat0 = bateria if bateria is not None else 100.0
            bat_max = BATERIA_MAX_POR_NIVEL[nivel] if con_estaciones else bat0
            escala_grande = (self.filas * self.columnas) / (40 * 60)
            minimo = 2 if nivel <= 2 else 1          # niveles bajos: al menos 2 estaciones en cualquier tamaño
            n_est = max(minimo, round(ESTACIONES_POR_NIVEL[nivel] * escala_grande)) if con_estaciones else 0
            fac = AMBIENTE_FACTOR_POR_NIVEL[nivel] if con_estaciones else 1.0
            for k in range(1, 60):
                drones = _drones_obligatorios(mundo, semilla, nivel)
                est = _colocar_estaciones(mundo, self.semilla_mundo, n_est)
                if _es_ganable(mundo, bat0, drones, bateria_max=bat_max, estaciones=est, factor=fac):
                    break
                self.semilla_mundo = semilla + 10007 * k
                mundo = _generar(self.semilla_mundo)
        self.mision = Mision(mundo, semilla=semilla, bateria=bateria)
        self._fitness_paso = None          # ARX-80: fitness del AG ya medido en el paso en curso (avanzar_ia)
        self._fitness_ultimo = 0.0         # último fitness finito medido; se arrastra si no hay plan del AG
        self.mision.log.completar = self._completar_fila
        # ARX-59: estaciones de recarga y batería máxima (la partida jugable las usa; las evaluaciones congeladas no)
        self.bateria_max = BATERIA_MAX_POR_NIVEL[nivel] if con_estaciones else None
        self.estaciones = _colocar_estaciones(mundo, self.semilla_mundo, n_est) if con_estaciones else []
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
        self.mision._optimizar_ag = _ag_con_todos_los_sitios(self.mision, self.mision._optimizar_ag)
        # ARX-66 / N12: mientras se cazan drones obligatorios, el refugio no es destino (Mision.paso_mision fijaría EXITO
        # al llegar sin moverse, y la caza nunca se ejecutaría).
        _quedan_sitios_original = self.mision._quedan_sitios
        # ARX-30c (ev3-d49 B): una señal biológica sin visitar también impide ganar
        self.mision._quedan_sitios = lambda: (_quedan_sitios_original() or self._caza_con_bfs()
                                              or self.senal_activa is not None)
        self.mision.rna = _RnaSegura(self.mision.rna)
        # El planificador de la misión pasa a respetar el objetivo fijado por el jugador (ev3-d27).
        self.mision._planear = self._planear_con_objetivo
        self._falla_restante = 0           # pasos de IA detenida por falla de sensor
        self._prob_fallo_base = None       # probabilidad de fallo del sensor antes de la falla
        self._ambiente = "normal"          # "normal" | "tormenta" | "noche"
        self._ambiente_restante = 0
        self._rng_ambiente = np.random.default_rng([int(semilla), 1313])  # propio, no comparte el de Mision
        self._rng_sismo = np.random.default_rng([int(semilla), 1314])     # ARX-30a: propio, no altera los meteoritos
        self._rng_enlace = np.random.default_rng([int(semilla), 1315])    # ARX-30b: propio, no altera meteoritos ni sismos
        self._rng_senal = np.random.default_rng([int(semilla), 1316])     # ARX-30c: propio
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
        if self._termico_activo:
            _inferir = self.mision.difuso.inferir

            def _inferir_con_temperatura(distancia, bateria, inclinacion, temperatura=0.0):
                if termico.ABORTO_TERMICO_ACTIVO:
                    temperatura = self.termico.t_int
                return _inferir(distancia, bateria, inclinacion, temperatura)
            self.mision.difuso.inferir = _inferir_con_temperatura
        # Mision() ya planificó con el AG original: se replanifica con el envoltorio que exige todos los sitios
        self.mision.objetivos = []
        self.mision._planear()
        self.intentos_barranco = 0         # movimientos intentados hacia un barranco (modos sueltos, ARX-11)
        self.esperas = 0                   # pasos de espera del modo difuso (ARX-11)
        self._historial = []               # últimas celdas visitadas por los modos sueltos (ARX-11)
        self.avisos = []                   # avisos para la interfaz, p. ej. «Faltan objetivos: sitios 2/4» (N4)
        self.combate = None                # Combate de la sesión; lo asigna la API para contar los drones destruidos
        self.modo_ia = "manual"            # modo de la sesión; decide si la IA puede disparar (N12)

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
        for celda in lectura["celdas_barranco"]:
            sombra.riesgo[celda] = 1.0
        lectura = dict(lectura, borde_barranco=siguiente in lectura["celdas_barranco"])
        inclinacion = min(45.0, abs(rasgos[2]) * GRADOS_POR_GRADIENTE)
        fz = sombra.difuso.inferir(sombra._distancia_a_riesgo_en_ruta(), self.rover.bateria, inclinacion)
        if not m.usar_difuso:
            fz = ResultadoDifuso(velocidad=0.5, membresias={}, reglas_activadas=[],
                                 agregado=None, universo=None, fallback=True)
        dec = m.supervisor.decidir(probs, fz.velocidad, lectura, self.rover.bateria)
        if sombra.riesgo[siguiente] >= 0.5:
            dec = Decision("replanificar", 0.0, ["V-RUTA-CON-RIESGO"])
        distancia = lectura["proximidad_frontal_m"]
        if dec.accion == "detener" and sombra._obstaculo_en_ruta(pos, rumbo, distancia):
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
        total = len(self.mundo.sitios)
        if len(self.mision.visitados) < total:
            falta.append(f"sitios {len(self.mision.visitados)}/{total}")
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
        total = len(self.mundo.sitios)
        self._recuperar_sin_ruta()
        falta = self.objetivos_pendientes()
        if not falta:
            self._caza_desde = None
        elif getattr(self, "_caza_desde", None) is not None and m.paso - self._caza_desde > 300:
            m.estado = "FRACASO"
            self._avisar("Faltan drones por destruir y no se alcanzaron a tiempo")
            return
        if m.estado == "EXITO" and falta and any(f.startswith("drones") for f in falta) and len(m.visitados) >= total:
            self._cazar_drones()
            return
        if m.estado == "EXITO" and len(m.visitados) < total:
            # una sola replanificación; si no hay ruta a ningún sitio pendiente, la batería no alcanza: se termina (N6)
            m.objetivos = []
            m._planear()
            pendientes = [o for o in m.objetivos if o in self.mundo.sitios and o not in m.visitados]
            if pendientes:
                m.estado = "EXPLORACION"
                self._avisar(f"Faltan objetivos: sitios {len(m.visitados)}/{total}")
                return
            # El AG no encontró ruta con el mapa de riesgo estimado. Antes de rendirse, se mira el mapa real:
            # sin ruta real o sin batería para ella, el fracaso dice la causa verdadera (N12, 591531 y 675131).
            ruta, faltan = self._ruta_real_a_sitios()
            if ruta and len(ruta) - 1 + MARGEN_ENERGIA <= self.rover.bateria:
                m.objetivos = faltan + [self.mundo.refugio]
                m.ruta = ruta
                m.estado = "EXPLORACION"
                self._avisar(f"Faltan objetivos: sitios {len(m.visitados)}/{total}")
            elif ruta:
                m.estado = "FRACASO"
                self._avisar("Batería insuficiente para llegar a los sitios científicos restantes")
            else:
                m.estado = "FRACASO"
                self._avisar("Sin ruta a los sitios científicos restantes")

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
        self._avisar("Replanteo por el mapa real tras quedarse sin ruta estimada")

    def _caza_con_bfs(self) -> bool:
        """Con sitios completos y drones obligatorios vivos, la IA caza por BFS (ARX-66 / N12, ARX-75).
        Aplica a automático, rna, difuso y ag; el manual no caza solo."""
        return (self.modo_ia in ("automatico", "rna", "difuso", "ag") and self.combate is not None
                and self.drones_obligatorios()
                and len(self.mision.visitados) >= len(self.mundo.sitios)
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
        mascara = np.asarray(self.mundo.tipo == LIBRE)
        origen = tuple(int(x) for x in self.rover.posicion)
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
        pts = [c for c in self.mundo.sitios if c not in m.visitados]
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

    def avanzar_modo(self, modo: str, veto: bool = True) -> dict:
        """Un paso conducido solo por rna, difuso o ag (ARX-11). Ver juego/conduccion.py."""
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
        r = conduccion.avanzar(self, modo, veto)
        self._tras_paso_estacion()
        self._revisar_victoria()
        return r

    # ---------- recarga (ARX-59) ----------
    def _tras_paso_estacion(self) -> None:
        """Si el rover acaba de llegar a una estación con batería por debajo del máximo, se recarga en RECARGA_PASOS."""
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
            if self.rover.bateria < self.bateria_max:
                self._recargando = RECARGA_PASOS

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
        pos = tuple(int(v) for v in self.rover.posicion)
        if pos in self.estaciones:
            return
        mascara = m.riesgo < 0.5
        f = FACTOR_DESVIO                   # peor caso de tormenta: 2 de batería por paso (1 base + 1 extra)
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
            self.rover.bateria = float(self.bateria_max)
            self.recargas_hechas += 1
            self._avisar("Recarga completa: batería al máximo")
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
        try:
            m.paso_mision()
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

    # ---------- planificación con objetivo fijado (ev3-d27) ----------
    def _planear_con_objetivo(self) -> bool:
        """Sustituye a Mision._planear: sin objetivo, plan normal; con objetivo, BFS hacia él."""
        m = self.mision
        if self._objetivo is None:
            if getattr(m, "estaciones_activas", False):
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
        if self._ambiente_restante > 0:
            self.rover.consumir(COSTO_AMBIENTE[self._ambiente])
            self._ambiente_restante -= 1
            if self._ambiente_restante == 0:
                self._ambiente = "normal"
        elif self._rng_ambiente.random() < PROB_AMBIENTE:
            tipo = "tormenta" if self._rng_ambiente.random() < 0.5 else "noche"
            self._iniciar_ambiente(tipo)
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
        if termico.ABORTO_TERMICO_ACTIVO and self.termico.debe_abortar:
            m = self.mision
            self.rover.en_modo_seguro = True
            m.estado = "MODO_SEGURO"
            m._registrar("modo_seguro", 0.0, ["V-TEMPERATURA"], {}, None)
            self._avisar(f"Aborto térmico: {self.t_int:.0f} °C interna, más de "
                         f"{termico.PASOS_MAXIMOS_SOBRE_TOLERANCIA} pasos sobre {termico.TOLERANCIA:.0f} °C")

    # ---------- eventos ----------
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
                                     factor=self.mision.factor_ambiente) is not None:
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

    def _evento_barranco(self) -> dict:
        f, c = self.rover.posicion
        for df, dc in MOVIMIENTOS.values():
            celda = (f + df, c + dc)
            if (self.mundo.dentro(celda) and self.mundo.tipo[celda] == LIBRE
                    and celda not in self.mundo.sitios
                    and celda not in (self.mundo.inicio, self.mundo.refugio)):
                self.mundo.marcar_barranco(celda)
                self.mision.riesgo[celda] = 1.0
                if "barranco" in EVENTOS_GRAVES and celda in {tuple(x) for x in (self.mision.ruta or [])}:
                    self._replanear_ag("barranco")
                return {"ok": True, "detalle": f"barranco en {celda}"}
        return {"ok": False, "detalle": "sin celda libre adyacente al rover"}

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
        cientifica = 100 * len(m.visitados) / total if total else 0.0
        bonus = 50 if m.vetos == 0 else 0
        return int(round(cientifica + 0.5 * self.rover.bateria + bonus))

    # ---------- salidas ----------
    def bitacora(self) -> pd.DataFrame:
        return self.mision.log.a_dataframe()

    def resumen(self) -> dict:
        return {**self.mision.resumen(), "nivel": self.nivel, "puntaje": self.puntaje()}


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
