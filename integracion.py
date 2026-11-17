"""ARES-X · Fase 5: integración híbrida, supervisor de seguridad y máquina de estados.

Pseudociclo por paso (sección 11):
observar → predecir riesgo (RNA) → inferir velocidad (difuso) → supervisar →
replanificar (AG) si corresponde → actuar → registrar.

El supervisor evalúa primero las prohibiciones físicas y después combina las recomendaciones.
Cada veto lleva un código de motivo reproducible.
"""
from dataclasses import dataclass, field, replace
from functools import lru_cache

import numpy as np

from difuso import FuzzyController, ResultadoDifuso
from genetico import GeneticPlanner, camino_bfs, mapa_estimado
from rna import NeuralPerception, _rasgos_celda, generar_dataset, particion_por_mapas
from simulador import (BARRANCO, MOVIMIENTOS, MissionLogger, Rover, SensorSuite, World,
                       paso_fisico)

ESTADOS_TERMINALES = {"EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"}
UMBRAL_RIESGO_RNA = 0.5           # probabilidad a partir de la cual la RNA veta
UMBRAL_VELOCIDAD_MINIMA = 0.2     # por debajo de esta velocidad el rover se detiene
GRADOS_POR_GRADIENTE = 20.0       # conversión supuesta de gradiente de altura a grados
DISTANCIA_BLOQUEO_RUTA = 6       # celdas de ruta adelante que se revisan por un obstáculo visto
MARGEN_ENERGIA = 15              # % de batería de reserva sobre el camino al refugio
PASOS_PARADO_MAXIMO = 3          # pasos detenido seguidos antes de replanificar


@dataclass
class Decision:
    accion: str                   # "avanzar", "detener", "replanificar" o "modo_seguro"
    velocidad: float
    motivos: list = field(default_factory=list)


class SafetySupervisor:
    """Veto con prioridad: primero la seguridad física, luego las recomendaciones."""

    def decidir(self, prob_clases: dict, velocidad: float, lectura: dict, bateria: float) -> Decision:
        if np.isnan(lectura["proximidad_frontal_m"]) or np.isnan(lectura["altimetria_m"]):
            return Decision("modo_seguro", 0.0, ["V-SENSOR-NAN"])
        if bateria <= 0:
            return Decision("modo_seguro", 0.0, ["V-BATERIA-0"])
        if lectura["borde_barranco"]:
            return Decision("replanificar", 0.0, ["V-BORDE-BARRANCO"])
        if prob_clases.get("barranco", 0.0) > UMBRAL_RIESGO_RNA:
            return Decision("replanificar", 0.0, ["V-RNA-BARRANCO"])
        if prob_clases.get("obstáculo", 0.0) > UMBRAL_RIESGO_RNA:
            return Decision("replanificar", 0.0, ["V-RNA-OBSTACULO"])
        if velocidad < UMBRAL_VELOCIDAD_MINIMA:
            return Decision("detener", velocidad, ["D-DIFUSO-LENTO"])
        return Decision("avanzar", velocidad, ["OK"])


@lru_cache(maxsize=1)
def rna_entrenada(semilla: int = 42) -> NeuralPerception:
    """RNA entrenada una sola vez por proceso (partición por mapas, tamaño reducido para rapidez)."""
    tr, _, _ = particion_por_mapas(total_mapas=30)
    X, y = generar_dataset(tr, muestras_por_mapa=300)
    return NeuralPerception(semilla=semilla).entrenar(X, y)


class Mision:
    def __init__(self, mundo: World, rna: NeuralPerception = None, semilla: int = 0,
                 bateria: float = 100.0, k_puntos: int = 3, ruido: float = 0.1,
                 eventos: dict = None, usar_rna: bool = True, usar_difuso: bool = True,
                 intervencion_rna=None, intervencion_difuso: float = None):
        self.mundo = mundo
        self.usar_rna = usar_rna
        self.usar_difuso = usar_difuso
        # Intervención causal (ARX-10, ev3-d32 A). Apagada por defecto: None no cambia nada.
        self.intervencion_rna = intervencion_rna          # función(probs) -> probs
        self.intervencion_difuso = intervencion_difuso    # velocidad fija en [0, 1]
        self.rna = rna or rna_entrenada()
        self.rng = np.random.default_rng(semilla)
        self.semilla = semilla
        self.sensor = SensorSuite(rng=self.rng, ruido=ruido)
        self.rover = Rover(posicion=mundo.inicio, bateria=bateria)
        self.riesgo = mapa_estimado(mundo, self.rng)
        self.difuso = FuzzyController()
        self.supervisor = SafetySupervisor()
        self.k = k_puntos
        self.eventos = eventos or {}
        self.log = MissionLogger()
        self.estado = "EXPLORACION"
        self.paso = 0
        self.ruta = []
        self.visitados = set()
        self.replanes = 0
        self.vetos = 0
        self.colisiones = 0
        self.paros_seguidos = 0
        self.objetivos = []           # orden de visita fijado por el AG en la planificación inicial
        self.bateria_inicial = bateria
        self._planear()

    # ---------- planificación ----------
    def _planear(self):
        """Planificación inicial con AG (una sola vez). Después solo BFS (ev3-d07, opción B)."""
        self.replanes += 1
        origen = self.rover.posicion
        if not self.objetivos:
            pendientes = {p: v for p, v in self.mundo.sitios.items() if p not in self.visitados}
            ruta = self._optimizar_ag(origen, pendientes)
            self.objetivos = [c for c in ruta if c in self.mundo.sitios] + [self.mundo.refugio]
            if pendientes and (not ruta or len(ruta) - 1 + MARGEN_ENERGIA > self.rover.bateria):
                self.objetivos = [self.mundo.refugio]
                ruta = []
        else:
            ruta = []
        if not ruta:
            ruta = self._ruta_bfs(origen)
        self.ruta = ruta if camino_valido(ruta, self.riesgo) else []
        return bool(self.ruta) and self.ruta[-1] == self.mundo.refugio

    def _ruta_bfs(self, origen):
        """Une caminos BFS desde el punto actual por los objetivos pendientes, en el orden del AG."""
        pendientes = [o for o in self.objetivos if o not in self.visitados]
        if pendientes and pendientes[-1] != self.mundo.refugio:
            pendientes.append(self.mundo.refugio)
        if not pendientes:
            pendientes = [self.mundo.refugio]
        transitable = self.riesgo < 0.5
        ruta, actual = [origen], origen
        for destino in pendientes:
            tramo = camino_bfs(actual, destino, transitable)
            if tramo is None:
                return []
            ruta.extend(tramo[1:])
            actual = destino
        # Energía: si el recorrido no cabe con margen, se descartan los sitios y se va al refugio
        if len(ruta) - 1 + MARGEN_ENERGIA > self.rover.bateria and self.mundo.refugio != origen:
            tramo = camino_bfs(origen, self.mundo.refugio, transitable)
            return tramo or []
        return ruta

    def _optimizar_ag(self, origen, pendientes):
        if not pendientes:
            return camino_bfs(origen, self.mundo.refugio, self.riesgo < 0.5) or []
        desde = replace(self.mundo, inicio=origen, sitios=pendientes)
        gp = GeneticPlanner(desde, self.riesgo, bateria=max(self.rover.bateria, 1.0),
                            k_puntos=self.k, poblacion=30, generaciones=30,
                            semilla=self.semilla)
        return gp.optimizar().mejor_ruta

    # ---------- pseudociclo ----------
    def paso_mision(self):
        if self.estado in ESTADOS_TERMINALES:
            return self.estado
        self.paso += 1
        if self.paso in self.eventos:
            self.eventos[self.paso](self)

        pos = self.rover.posicion
        if pos == self.mundo.refugio and not self._quedan_sitios():
            self.estado = "EXITO"
            return self.estado
        if len(self.ruta) < 2:
            if not self._planear():
                self.estado = "SIN_RUTA"
                return self.estado
            self._registrar("replanificar", 0.0, ["REPLAN-RUTA-VACIA"], {}, None)
            return self.estado

        siguiente = self.ruta[1]
        rumbo = _rumbo(pos, siguiente)
        # observar: sensores y rasgos para la RNA
        rasgos, _ = _rasgos_celda(self.mundo, pos, rumbo, self.sensor, self.rng)
        lectura = self.sensor.leer(self.mundo, pos, rumbo)
        probs = self.rna.explicar(rasgos)["probabilidades"] if self.usar_rna else {"libre": 1.0}
        if self.intervencion_rna is not None and self.usar_rna:
            probs = self.intervencion_rna(probs)
        self._actualizar_mapa_estimado(pos, rumbo, lectura["proximidad_frontal_m"])
        for celda in lectura["celdas_barranco"]:
            self.riesgo[celda] = 1.0
        # el borde de barranco solo veta si el precipicio está en la siguiente celda de la ruta
        lectura = dict(lectura, borde_barranco=siguiente in lectura["celdas_barranco"])
        # inferir velocidad
        inclinacion = min(45.0, abs(rasgos[2]) * GRADOS_POR_GRADIENTE)
        # la velocidad depende de la distancia a lo largo de la ruta, no solo de lo que hay al frente
        fz = self.difuso.inferir(self._distancia_a_riesgo_en_ruta(), self.rover.bateria, inclinacion)
        if self.intervencion_difuso is not None and self.usar_difuso:
            fz = ResultadoDifuso(velocidad=float(self.intervencion_difuso), membresias={},
                                 reglas_activadas=[], agregado=None, universo=None, fallback=True)
        if not self.usar_difuso:          # ablación: velocidad fija, sin controlador difuso
            fz = ResultadoDifuso(velocidad=0.5, membresias={}, reglas_activadas=[],
                                 agregado=None, universo=None, fallback=True)
        # supervisar
        dec = self.supervisor.decidir(probs, fz.velocidad, lectura, self.rover.bateria)
        # si la siguiente celda de la ruta ya es peligrosa, el plan está roto: replanificar
        if self.riesgo[siguiente] >= 0.5:
            dec = Decision("replanificar", 0.0, ["V-RUTA-CON-RIESGO"])
        # un obstáculo cercano en la ruta invalida el plan: se replanifica, no se espera.
        # Antes dependía de la parada del difuso (dec.accion == "detener"); desde ARX-91 (ab46b4a) es incondicional.
        distancia = lectura["proximidad_frontal_m"]
        if self._obstaculo_en_ruta(pos, rumbo, distancia):
            dec = Decision("replanificar", 0.0, ["V-OBSTACULO-EN-RUTA"])
        # vigilante: un rover detenido varios pasos seguidos replanifica en lugar de quedarse parado
        self.paros_seguidos = self.paros_seguidos + 1 if dec.accion == "detener" else 0
        if self.paros_seguidos >= PASOS_PARADO_MAXIMO:
            dec = Decision("replanificar", 0.0, ["V-PARADO-SIN-AVANCE"])
            self.paros_seguidos = 0
        self.estado = "ALERTA" if dec.accion != "avanzar" or fz.velocidad < 0.5 else "EXPLORACION"

        if any(m.startswith("V-") for m in dec.motivos):
            self.vetos += 1
        if dec.accion == "modo_seguro":
            self.rover.en_modo_seguro = True
            self.estado = "MODO_SEGURO"
        elif dec.accion == "replanificar":
            self._registrar(dec.accion, dec.velocidad, dec.motivos, probs, fz)
            if not self._planear():
                self.estado = "SIN_RUTA"
            return self.estado
        elif dec.accion == "avanzar":
            if paso_fisico(self.mundo, self.rover, rumbo):
                self.ruta.pop(0)
                if self.rover.posicion in self.mundo.sitios:
                    self.visitados.add(self.rover.posicion)
            else:
                self.colisiones += 1
                dec.motivos.append("V-CELDA-BLOQUEADA")
                self._planear()
        self._registrar(dec.accion, dec.velocidad, dec.motivos, probs, fz)
        if self.rover.bateria <= 0 and self.estado not in ESTADOS_TERMINALES:
            self.estado = "FRACASO"
        return self.estado

    def ejecutar(self, max_pasos: int = 400) -> dict:
        while self.estado not in ESTADOS_TERMINALES and self.paso < max_pasos:
            self.paso_mision()
        if self.estado not in ESTADOS_TERMINALES:
            self.estado = "FRACASO"
        return self.resumen()

    def resumen(self) -> dict:
        return {
            "estado": self.estado,
            "pasos": self.paso,
            "sitios_visitados": len(self.visitados),
            "sitios_totales": len(self.mundo.sitios),
            "bateria_final": round(self.rover.bateria, 1),
            "vetos": self.vetos,
            "replanes": self.replanes,
            "colisiones": self.colisiones,
            "barrancos_pisados": int(self.mundo.tipo[self.rover.posicion] == BARRANCO),
        }

    def _celda_observada(self, pos, rumbo, distancia):
        """Celda donde el sensor de proximidad ve el obstáculo, o None si no ve nada."""
        if np.isnan(distancia) or distancia >= 20:
            return None
        df, dc = MOVIMIENTOS[rumbo]
        paso = max(1, round(distancia))
        celda = (pos[0] + df * paso, pos[1] + dc * paso)
        return celda if self.mundo.dentro(celda) else None

    def _actualizar_mapa_estimado(self, pos, rumbo, distancia):
        """El rover marca en su mapa estimado el obstáculo que su sensor de proximidad ve."""
        celda = self._celda_observada(pos, rumbo, distancia)
        if celda is not None:
            self.riesgo[celda] = 1.0

    def _distancia_a_riesgo_en_ruta(self) -> float:
        """Pasos hasta el primer peligro conocido sobre la ruta (20 si la ruta está libre)."""
        for i, celda in enumerate(self.ruta[1:], start=1):
            if self.riesgo[celda] >= 0.5:
                return float(min(i, 20))
        return 20.0

    def _obstaculo_en_ruta(self, pos, rumbo, distancia) -> bool:
        """¿El obstáculo visto cae sobre las próximas celdas de la ruta planeada?"""
        celda = self._celda_observada(pos, rumbo, distancia)
        if celda is None or celda == pos:
            return False
        proximas = self.ruta[1:DISTANCIA_BLOQUEO_RUTA + 1]
        return celda in proximas

    def _quedan_sitios(self) -> bool:
        """¿Quedan sitios en el plan vigente? Un sitio fuera del plan (energía) ya no cuenta."""
        return any(o in self.mundo.sitios and o not in self.visitados for o in self.objetivos)

    def _registrar(self, accion, velocidad, motivos, probs, fz):
        self.log.registrar(
            paso=self.paso,
            estado=self.estado,
            posicion=str(self.rover.posicion),
            bateria=round(self.rover.bateria, 2),
            accion=accion,
            velocidad=round(float(velocidad), 3),
            p_barranco=round(float(probs.get("barranco", 0.0)), 3) if probs else None,
            p_obstaculo=round(float(probs.get("obstáculo", 0.0)), 3) if probs else None,
            reglas=";".join(r[0] for r in fz.reglas_activadas) if fz else "",
            motivos=";".join(motivos),
        )


def forzar_probabilidad(clase: str, confianza: float = 0.95):
    """Intervención de la RNA: fuerza la probabilidad a una clase (libre, obstáculo o barranco)."""
    def fn(probs):
        resto = (1.0 - confianza) / max(len(probs) - 1, 1)
        return {k: (confianza if k == clase else resto) for k in probs}
    return fn


def _rumbo(origen, destino) -> str:
    diferencia = (destino[0] - origen[0], destino[1] - origen[1])
    for rumbo, paso in MOVIMIENTOS.items():
        if paso == diferencia:
            return rumbo
    raise ValueError(f"Las celdas {origen} y {destino} no son adyacentes.")


def camino_valido(ruta, riesgo) -> bool:
    """La ruta debe ser contigua y no pasar por celdas que el mapa estimado marca como peligrosas."""
    if not ruta:
        return False
    for a, b in zip(ruta, ruta[1:]):
        df, dc = b[0] - a[0], b[1] - a[1]
        if max(abs(df), abs(dc)) != 1:              # paso de ocho direcciones
            return False
    return all(riesgo[c] < 0.5 for c in ruta)


def evento_barranco_en_ruta(mision: Mision):
    """Evento: aparece un barranco justo delante de la siguiente celda de la ruta."""
    if len(mision.ruta) > 2:
        celda = mision.ruta[2]
        if celda not in (mision.mundo.inicio, mision.mundo.refugio) and celda not in mision.mundo.sitios:
            mision.mundo.marcar_barranco(celda)
            mision.riesgo[celda] = 1.0
