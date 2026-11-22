"""ARES-X · R23: planificador con restricciones (AG sobre orden + selección + paradas de recarga).

El problema de la partida jugable, antes de R23, era un viajante de 3 a 4 sitios (24 órdenes): el AG convergía en la
generación 1 o 2. Aquí el problema es de verdad:

- 8 a 12 sitios científicos con valores distintos.
- **Ventanas de tiempo** (opcionales por sitio): entre los pasos `desde` y `hasta` la lectura vale el 100 % del valor del
  sitio; fuera de la ventana vale `CALIDAD_FUERA_VENTANA` (25 %: poca luz o instrumento sin calentar). No hay espera: el
  rover no se queda parado esperando una ventana.
- **Recarga obligatoria**: la batería no alcanza para la ruta completa. El plan debe pasar por bases de recarga (3 pasos
  parado, batería a la capacidad) en el momento adecuado.
- **Sacrificio**: los sitios *opcionales* se pueden descartar si no caben; los obligatorios no.

Cromosoma = (orden, sel, paradas):
- `orden`: permutación de los ids de TODOS los sitios pendientes.
- `sel`: un bit por sitio (por posición en `problema.sitios`); solo cuenta en los opcionales (los obligatorios van siempre).
- `paradas`: n+1 genes; el gen i es la base (índice) donde recargar justo antes del i-ésimo sitio de `orden` (el último, antes
  del refugio), o -1 si no hay parada.

Decodificación con **reparación**: se recorre la secuencia gastando batería (coste = pasos × factor). Si un tramo deja la
batería por debajo de lo que hace falta para seguir (llegar a la base más cercana desde el destino, o la reserva final en el
refugio), se inserta la parada de recarga que menos desvío cause. La reparación se escribe de vuelta en el cromosoma
(evolución lamarckiana) y se cuenta aparte: los individuos que dependen de la reparación puntúan un poco menos que los que ya
traen sus paradas, así que el AG aprende dónde recargar. Un sitio opcional inalcanzable se sacrifica; un obligatorio
inalcanzable deja el plan infactible.

Operadores: torneo; cruce OX sobre la permutación, uniforme sobre la selección, de un punto sobre las paradas; mutación por
intercambio, inserción, inversión (2-opt), alternancia de la selección, alta/baja/cambio de parada y una mutación guiada que
recoloca un sitio que perdió su ventana cerca de donde llega a tiempo. **Control de diversidad**: no se admiten duplicados en la
población (el hijo repetido se muta más o se sustituye por un inmigrante), la mutación se adapta cuando la diversidad cae
bajo el umbral y, si el fitness se estanca con la población homogénea, se reinicia el 40 % peor.

Todos los pesos, ventanas y costes son supuestos de simulación.
"""
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from simulador import MOVIMIENTOS

RECARGA_PASOS = 3                  # pasos parado en una base (igual que juego.partida.RECARGA_PASOS)
CALIDAD_FUERA_VENTANA = 0.25       # fracción del valor que se obtiene fuera de la ventana
MARGEN_ENERGIA = 15.0              # reserva final de batería al llegar al refugio (igual que integracion.MARGEN_ENERGIA)
W_PASOS = 0.25                     # peso del tiempo total (normalizado) en el fitness
W_REPARACION = 0.01                # una recarga que hubo que reparar cuesta un poco más que una planeada
PENAL_INFACTIBLE = 1.0

_CACHE_DIST = {}


class Distancias:
    """BFS por origen (8 direcciones) sobre una máscara de celdas transitables, con caché por origen."""

    def __init__(self, transitable):
        self.tr = np.asarray(transitable).tolist()
        self.filas = len(self.tr)
        self.columnas = len(self.tr[0]) if self.filas else 0
        self._arboles = {}

    @classmethod
    def de(cls, transitable):
        """Instancia compartida por máscara exacta (el BFS de un mismo mapa no se repite entre planes)."""
        clave = (transitable.shape, np.asarray(transitable).tobytes())
        if clave not in _CACHE_DIST:
            if len(_CACHE_DIST) >= 48:
                _CACHE_DIST.pop(next(iter(_CACHE_DIST)))
            _CACHE_DIST[clave] = cls(transitable)
        return _CACHE_DIST[clave]

    def arbol(self, origen):
        origen = (int(origen[0]), int(origen[1]))
        if origen not in self._arboles:
            tr, filas, cols = self.tr, self.filas, self.columnas
            deltas = list(MOVIMIENTOS.values())
            dist, previo = {origen: 0}, {origen: None}
            cola = deque([origen])
            while cola:
                ar, ac = cola.popleft()
                d = dist[(ar, ac)] + 1
                for df, dc in deltas:
                    vr, vc = ar + df, ac + dc
                    if 0 <= vr < filas and 0 <= vc < cols and (vr, vc) not in dist and tr[vr][vc]:
                        dist[(vr, vc)] = d
                        previo[(vr, vc)] = (ar, ac)
                        cola.append((vr, vc))
            self._arboles[origen] = (dist, previo)
        return self._arboles[origen]

    def largo(self, a, b):
        if a == b:
            return 0
        return self.arbol(a)[0].get((int(b[0]), int(b[1])))

    def camino(self, a, b):
        a, b = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
        if a == b:
            return [a]
        dist, previo = self.arbol(a)
        if b not in dist:
            return None
        c = [b]
        while previo[c[-1]] is not None:
            c.append(previo[c[-1]])
        return c[::-1]


@dataclass(frozen=True)
class SitioPlan:
    id: int
    celda: tuple
    valor: float
    ventana: tuple = None          # (desde, hasta) en pasos de la partida, o None
    obligatorio: bool = True


@dataclass
class Plan:
    orden: tuple
    sel: tuple
    paradas: tuple
    nodos: list                    # [(tipo, celda, id, llegada, bateria)]; tipo "inicio", "base", "sitio", "refugio"
    pasos: int
    ciencia: float
    recargas: int
    reparaciones: int
    factible: bool
    fitness: float
    bateria_final: float
    viol: list = field(default_factory=list)       # tuplas crudas; el texto sale de Problema.textos(plan)
    sacrificados: tuple = ()
    ventanas_falladas: int = 0

    @property
    def clave(self):
        return (self.orden, self.sel, self.paradas)

    @property
    def ids_visitados(self):
        return [n[2] for n in self.nodos if n[0] == "sitio"]


class Problema:
    """Instancia del problema de ruta con ventanas, recarga y selección. `dist` da longitudes de camino (BFS)."""

    def __init__(self, inicio, refugio, sitios, bases, bateria, capacidad, dist, factor=1.0, reserva=MARGEN_ENERGIA,
                 reserva_extra=0.0, t0=0, recarga_pasos=RECARGA_PASOS, calidad_fuera=CALIDAD_FUERA_VENTANA):
        self.inicio = (int(inicio[0]), int(inicio[1]))
        self.refugio = (int(refugio[0]), int(refugio[1]))
        self.sitios = list(sitios)
        self.n = len(self.sitios)
        self.indice = {s.id: i for i, s in enumerate(self.sitios)}
        self.bases = [(int(b[0]), int(b[1])) for b in bases]
        self.bateria = float(bateria)
        self.capacidad = float(max(capacidad, bateria, 1.0))
        self.dist = dist
        self.factor = float(factor)
        self.reserva = float(reserva)
        self.reserva_extra = float(reserva_extra)      # p. ej. margen de caza de drones obligatorios, en % de batería
        self.t0 = int(t0)
        self.recarga_pasos = int(recarga_pasos)
        self.calidad_fuera = float(calidad_fuera)
        self.valor_total = float(sum(s.valor for s in self.sitios)) or 1.0
        self._escape = {}
        self.pasos_ref = 60.0
        self.evaluaciones = 0

    # ---------- utilidades ----------
    def largo(self, a, b):
        return self.dist.largo(a, b)

    def escape(self, celda):
        """Batería mínima para llegar desde `celda` a la base más cercana (0 si no hay bases o ninguna es alcanzable)."""
        if celda not in self._escape:
            ds = [self.dist.largo(celda, b) for b in self.bases]
            ds = [d for d in ds if d is not None]
            self._escape[celda] = (min(ds) * self.factor) if ds else 0.0
        return self._escape[celda]

    def calidad(self, s: SitioPlan, t: int) -> float:
        if s.ventana is None:
            return 1.0
        return 1.0 if s.ventana[0] <= t <= s.ventana[1] else self.calidad_fuera

    def reserva_final(self):
        return self.reserva + self.reserva_extra

    # ---------- decodificación con reparación ----------
    def decodificar(self, orden, sel, paradas) -> Plan:
        self.evaluaciones += 1
        n = self.n
        pos, bat, t = self.inicio, self.bateria, self.t0
        cap, factor, dist = self.capacidad, self.factor, self.dist
        nodos = [("inicio", pos, None, t, bat)]
        pasos = recargas = reparaciones = 0
        score = 0.0
        viol, sacrificados = [], []
        nuevas = list(paradas)
        factible = True
        fallo = None
        faltan_obl = 0
        ventanas_falladas = 0
        nuevo_sel = list(sel)

        # secuencia a recorrer: (tipo, celda, id, slot)
        seq = []
        for i in range(n):
            sid = orden[i]
            s = self.sitios[self.indice[sid]]
            incluido = s.obligatorio or sel[self.indice[sid]]
            if paradas[i] >= 0 and incluido:
                seq.append(("base", self.bases[paradas[i]], paradas[i], i))
            if incluido:
                seq.append(("sitio", s.celda, sid, i))
            elif not s.obligatorio:
                sacrificados.append(sid)
        if paradas[n] >= 0:
            seq.append(("base", self.bases[paradas[n]], paradas[n], n))
        seq.append(("refugio", self.refugio, None, n))

        for k, (tipo, celda, ident, slot) in enumerate(seq):
            d = dist.largo(pos, celda)
            if d is None:
                if tipo == "sitio" and not self.sitios[self.indice[ident]].obligatorio:
                    sacrificados.append(ident)                       # opcional inalcanzable: se sacrifica
                    nuevo_sel[self.indice[ident]] = False
                    continue
                factible = False
                fallo = ("sin_camino", tipo, ident)
                faltan_obl += sum(1 for q in seq[k:] if q[0] in ("sitio", "refugio"))
                break
            necesario = (self.reserva_final() if tipo == "refugio"
                         else (self.escape(celda) if tipo == "sitio" else 0.0))
            costo = d * factor
            if bat - costo < necesario - 1e-9 and self.bases:
                # reparación: la base que menos desvío cause y desde la que el destino quede seguro con la batería llena
                mejor = None
                for bi, b in enumerate(self.bases):
                    d1 = dist.largo(pos, b)
                    d2 = dist.largo(b, celda)
                    if d1 is None or d2 is None or d1 * factor > bat + 1e-9:
                        continue
                    if d2 * factor + necesario > cap + 1e-9:
                        continue
                    extra = d1 + d2
                    if mejor is None or extra < mejor[0]:
                        mejor = (extra, bi, d1, d2)
                if mejor is not None:
                    _, bi, d1, d2 = mejor
                    pasos += d1
                    t += d1 + self.recarga_pasos
                    bat = cap
                    recargas += 1
                    reparaciones += 1
                    nodos.append(("base", self.bases[bi], bi, t, bat))
                    if nuevas[slot] < 0 and tipo != "base":
                        nuevas[slot] = bi
                    pos = self.bases[bi]
                    d, costo = d2, d2 * factor
            if bat - costo < (0.0 if tipo == "base" else necesario) - 1e-9:
                if tipo == "sitio" and not self.sitios[self.indice[ident]].obligatorio:
                    sacrificados.append(ident)                       # opcional que no cabe ni recargando
                    nuevo_sel[self.indice[ident]] = False
                    continue
                factible = False
                fallo = ("bateria", tipo, ident)
                faltan_obl += sum(1 for q in seq[k:] if q[0] in ("sitio", "refugio"))
                break
            pasos += d
            t += d
            bat -= costo
            pos = celda
            if tipo == "base":
                t += self.recarga_pasos
                bat = cap
                recargas += 1
                nodos.append(("base", celda, ident, t, bat))
            elif tipo == "sitio":
                s = self.sitios[self.indice[ident]]
                q = self.calidad(s, t)
                score += s.valor * q
                if q < 1.0:
                    ventanas_falladas += 1
                    viol.append(("ventana", ident, t))
                nodos.append(("sitio", celda, ident, t, bat))
            else:
                nodos.append(("refugio", celda, None, t, bat))

        ciencia = score / self.valor_total
        if factible:
            f = ciencia - W_PASOS * pasos / self.pasos_ref - W_REPARACION * reparaciones
        else:
            deficit = 0.0
            if fallo and fallo[0] == "bateria":
                deficit = 0.1
            f = ciencia - PENAL_INFACTIBLE - 0.05 * faltan_obl - deficit - W_PASOS * pasos / self.pasos_ref
            viol.append((fallo[0], fallo[1], fallo[2]) if fallo else ("infactible", None, None))
        return Plan(tuple(orden), tuple(nuevo_sel), tuple(nuevas), nodos, int(pasos), float(ciencia), int(recargas),
                    int(reparaciones), bool(factible), float(f), float(bat), viol,
                    tuple(dict.fromkeys(sacrificados)), int(ventanas_falladas))

    # ---------- salidas ----------
    def ruta(self, plan: Plan):
        """Celdas de la ruta del plan, de inicio a refugio, uniendo los nodos con el BFS. None si falta un tramo."""
        celdas = [n[1] for n in plan.nodos]
        if plan.nodos and plan.nodos[-1][0] != "refugio":
            celdas.append(self.refugio)
        ruta = [celdas[0]]
        for a, b in zip(celdas, celdas[1:]):
            tramo = self.dist.camino(a, b)
            if tramo is None:
                return None
            ruta.extend(tramo[1:])
        return ruta

    def textos(self, plan: Plan) -> list:
        """Violaciones del plan en texto claro (las de ventana son blandas; el resto, duras)."""
        out = []
        for tipo, a, b in plan.viol:
            if tipo == "ventana":
                s = self.sitios[self.indice[a]]
                out.append(f"sitio {a}: llega en el paso {b}, fuera de su ventana {s.ventana[0]}–{s.ventana[1]} "
                           f"(vale {int(round(100 * self.calidad_fuera))} %)")
            elif tipo == "sin_camino":
                out.append(f"sin camino conocido hasta " + ("el refugio" if a == "refugio" else
                           f"el sitio {b}" if a == "sitio" else "una base"))
            elif tipo == "bateria":
                out.append("la batería no alcanza para llegar a " + ("el refugio con reserva" if a == "refugio" else
                           f"el sitio {b}" if a == "sitio" else "la base") + ", ni recargando")
            else:
                out.append("plan infactible")
        for sid in plan.sacrificados:
            s = self.sitios[self.indice[sid]]
            out.append(f"sacrifica el sitio opcional {sid} (valor {s.valor:g})")
        return out


# ---------- heurísticas «sin AG» ----------
def orden_vecino(p: Problema) -> list:
    """Vecino más cercano por longitud de camino desde el inicio (desempate por id)."""
    cur, pend, orden = p.inicio, list(p.sitios), []
    while pend:
        def coste(s):
            d = p.largo(cur, s.celda)
            return (float("inf") if d is None else d, s.id)
        s = min(pend, key=coste)
        orden.append(s.id)
        pend.remove(s)
        cur = s.celda
    return orden


def _largo_tour(p: Problema, orden) -> float:
    cur, total = p.inicio, 0.0
    for sid in list(orden) + [None]:
        celda = p.refugio if sid is None else p.sitios[p.indice[sid]].celda
        d = p.largo(cur, celda)
        total += 1e6 if d is None else d
        cur = celda
    return total


def orden_2opt(p: Problema, orden=None) -> list:
    """Vecino más cercano mejorado con 2-opt sobre el largo del tour inicio → sitios → refugio (sin ventanas ni recarga)."""
    orden = list(orden_vecino(p) if orden is None else orden)
    mejora = True
    while mejora and len(orden) > 1:
        mejora = False
        base = _largo_tour(p, orden)
        for i in range(len(orden) - 1):
            for j in range(i + 1, len(orden)):
                cand = orden[:i] + orden[i:j + 1][::-1] + orden[j + 1:]
                largo = _largo_tour(p, cand)
                if largo < base - 1e-9:
                    orden, base, mejora = cand, largo, True
    return orden


def orden_ventanas(p: Problema) -> list:
    """Primero el que vence antes (ventana más temprana por `hasta`); sin ventana, al final por vecino más cercano."""
    con = sorted([s for s in p.sitios if s.ventana is not None], key=lambda s: (s.ventana[1], s.id))
    resto = [s for s in p.sitios if s.ventana is None]
    cur = con[-1].celda if con else p.inicio
    orden = [s.id for s in con]
    while resto:
        s = min(resto, key=lambda q: (p.largo(cur, q.celda) if p.largo(cur, q.celda) is not None else 1e9, q.id))
        orden.append(s.id)
        resto.remove(s)
        cur = s.celda
    return orden


def orden_valor(p: Problema) -> list:
    """Voraz por valor decreciente (los más valiosos primero)."""
    return [s.id for s in sorted(p.sitios, key=lambda s: (-s.valor, s.id))]


def plan_heuristico(p: Problema, orden) -> Plan:
    """Plan de un orden dado SIN AG: todos los sitios, paradas solo por reparación (insertadas donde hace falta).
    Si no cabe, descarta el opcional de menor valor (o el último del orden) hasta que quepa; los obligatorios no se tocan."""
    sel = [True] * p.n
    paradas = tuple([-1] * (p.n + 1))
    plan = p.decodificar(tuple(orden), tuple(sel), paradas)
    while not plan.factible:
        opcionales = [s for s in p.sitios if not s.obligatorio and sel[p.indice[s.id]]]
        if not opcionales:
            break
        quitar = min(opcionales, key=lambda s: (s.valor, -list(orden).index(s.id)))
        sel[p.indice[quitar.id]] = False
        plan = p.decodificar(tuple(orden), tuple(sel), paradas)
    return plan


def ordenes_heuristicos() -> dict:
    return {"vecino": orden_vecino, "2opt": orden_2opt, "ventanas": orden_ventanas, "valor": orden_valor}


# ---------- el AG ----------
@dataclass
class ResultadoPlan:
    mejor: Plan
    historial: list            # por generación: n, mejor, media, peor, diversidad, distintos, candidatos (Plan)
    tiempo_s: float
    evaluaciones: int
    ultima_mejora: int         # generación del último aumento del mejor fitness
    problema: Problema = None

    @property
    def viable(self) -> bool:
        return bool(self.mejor.factible)

    @property
    def evaluados(self) -> int:
        return int(self.evaluaciones)

    def historial_json(self) -> list:
        """Historial compacto por generación (sin los planes completos) para /ia/paso y los laboratorios."""
        return [{"generacion": h["n"], "n": h["n"], "mejor": float(h["mejor"]), "media": float(h["media"]),
                 "peor": float(h["peor"]), "diversidad": float(h["diversidad"]), "distintos": int(h["distintos"]),
                 "top": [{"cromosoma": [n[2] for n in pl.nodos if n[0] == "sitio"], "fitness": float(pl.fitness)}
                         for pl in h["candidatos"][:3]]} for h in self.historial]

    def desglose(self):
        """Desglose del mejor plan con los nombres de Desglose (distancia = pasos normalizados; sin riesgo ni giros)."""
        from types import SimpleNamespace
        m, p = self.mejor, self.problema
        return SimpleNamespace(fitness=m.fitness, ciencia=m.ciencia, distancia=m.pasos / max(p.pasos_ref, 1.0),
                               energia=min(1.0, m.pasos * p.factor / max(p.capacidad, 1.0)), riesgo=0.0, tiempo=0.0,
                               penalizacion=0.0 if m.factible else 1.0)


class AGRestringido:
    def __init__(self, problema: Problema, poblacion: int = 60, generaciones: int = 60, prob_cruce: float = 0.85,
                 prob_mutacion: float = 0.35, elite: int = 2, torneo: int = 3, semilla: int = 0,
                 umbral_diversidad: float = 0.12, inmigrantes: float = 0.10, n_candidatos: int = 6,
                 semillas_cromosomas=()):
        self.p = problema
        self.poblacion = int(poblacion)
        self.generaciones = int(generaciones)
        self.prob_cruce = prob_cruce
        self.prob_mutacion = prob_mutacion
        self.elite = elite
        self.torneo = torneo
        self.umbral_diversidad = umbral_diversidad
        self.inmigrantes = inmigrantes
        self.n_candidatos = n_candidatos
        self.rng = np.random.default_rng(int(semilla))
        self.cache = {}
        self.semillas_cromosomas = list(semillas_cromosomas)
        self.cruces = 0
        self.mutaciones = 0
        # escala del tiempo: el largo del vecino más cercano (con el refugio), para que W_PASOS sea comparable entre mapas
        ids = [s.id for s in problema.sitios]
        problema.pasos_ref = max(40.0, float(_largo_tour(problema, orden_vecino(problema)) if ids else 40.0))

    # ----- evaluación con caché y escritura de la reparación -----
    def evaluar(self, crom):
        if crom not in self.cache:
            plan = self.p.decodificar(*crom)
            self.cache[crom] = plan
            if plan.clave != crom:               # evolución lamarckiana: se guarda también el cromosoma reparado
                self.cache.setdefault(plan.clave, plan)
        return self.cache[crom]

    def _canonico(self, crom):
        return self.evaluar(crom).clave

    # ----- generación de individuos -----
    def _aleatorio(self, con_paradas=True):
        p, rng = self.p, self.rng
        ids = [s.id for s in p.sitios]
        orden = tuple(int(x) for x in rng.permutation(ids))
        sel = tuple(bool(rng.random() < 0.9) for _ in range(p.n))
        paradas = tuple((int(rng.integers(len(p.bases))) if (con_paradas and p.bases and rng.random() < 0.12) else -1)
                        for _ in range(p.n + 1))
        return (orden, sel, paradas)

    def _desde_orden(self, orden):
        p = self.p
        return (tuple(orden), tuple([True] * p.n), tuple([-1] * (p.n + 1)))

    # ----- operadores -----
    def _ox(self, a, b):
        n = len(a)
        if n < 2:
            return a
        i, j = sorted(int(x) for x in self.rng.choice(n + 1, size=2, replace=False))
        medio = a[i:j]
        resto = [g for g in b if g not in medio]
        return tuple(resto[:i]) + tuple(medio) + tuple(resto[i:])

    def _cruzar(self, c1, c2):
        if self.rng.random() > self.prob_cruce:
            return c1, c2
        self.cruces += 1
        n = self.p.n
        pa = tuple(c1[1][k] if self.rng.random() < 0.5 else c2[1][k] for k in range(n))
        pb = tuple(c2[1][k] if self.rng.random() < 0.5 else c1[1][k] for k in range(n))
        corte = int(self.rng.integers(0, n + 2))
        xa = c1[2][:corte] + c2[2][corte:]
        xb = c2[2][:corte] + c1[2][corte:]
        return (self._ox(c1[0], c2[0]), pa, xa), (self._ox(c2[0], c1[0]), pb, xb)

    def _mutar(self, crom, fuerza=1):
        p, rng = self.p, self.rng
        orden, sel, paradas = list(crom[0]), list(crom[1]), list(crom[2])
        n = p.n
        for _ in range(fuerza):
            r = rng.random()
            if n >= 2 and r < 0.22:                              # intercambio
                i, j = (int(x) for x in rng.choice(n, size=2, replace=False))
                orden[i], orden[j] = orden[j], orden[i]
            elif n >= 2 and r < 0.42:                            # inserción: mueve un sitio a otra posición
                i = int(rng.integers(n))
                g = orden.pop(i)
                orden.insert(int(rng.integers(n)), g)
            elif n >= 3 and r < 0.60:                            # inversión de un tramo (2-opt)
                i, j = sorted(int(x) for x in rng.choice(n, size=2, replace=False))
                orden[i:j + 1] = orden[i:j + 1][::-1]
            elif r < 0.70:                                       # alterna la selección de un opcional
                opc = [k for k, s in enumerate(p.sitios) if not s.obligatorio]
                if opc:
                    k = opc[int(rng.integers(len(opc)))]
                    sel[k] = not sel[k]
            elif r < 0.85 and p.bases:                           # parada de recarga: alta, cambio o baja
                k = int(rng.integers(n + 1))
                paradas[k] = -1 if (paradas[k] >= 0 and rng.random() < 0.4) else int(rng.integers(len(p.bases)))
            elif n >= 2:                                         # mutación guiada por las ventanas
                self._mutar_ventana(orden)
        self.mutaciones += 1
        return (tuple(orden), tuple(sel), tuple(paradas))

    def _mutar_ventana(self, orden):
        """Recoloca un sitio con ventana donde el plan llega cerca de su ventana (si no hay ninguno, un intercambio)."""
        p, rng = self.p, self.rng
        con = [sid for sid in orden if p.sitios[p.indice[sid]].ventana is not None]
        if not con:
            i, j = (int(x) for x in rng.choice(len(orden), size=2, replace=False))
            orden[i], orden[j] = orden[j], orden[i]
            return
        sid = con[int(rng.integers(len(con)))]
        centro = sum(p.sitios[p.indice[sid]].ventana) / 2.0
        plan = self.evaluar((tuple(orden), tuple([True] * p.n), tuple([-1] * (p.n + 1))))
        llegadas = [(abs(n[3] - centro), k) for k, n in enumerate([x for x in plan.nodos if x[0] == "sitio"])]
        if not llegadas:
            return
        _, k = min(llegadas)
        orden.remove(sid)
        orden.insert(min(k, len(orden)), sid)

    # ----- diversidad -----
    def diversidad(self, poblacion) -> float:
        """Distancia media entre pares (fracción de genes distintos: posiciones de la permutación, selección y paradas)."""
        m = len(poblacion)
        if m < 2:
            return 0.0
        M = np.array([list(c[0]) + [int(x) for x in c[1]] + list(c[2]) for c in poblacion], dtype=np.int32)
        tot = 0.0
        for i in range(m - 1):
            tot += float((M[i + 1:] != M[i]).sum())
        return tot / (m * (m - 1) / 2) / max(M.shape[1], 1)

    # ----- bucle -----
    def optimizar(self) -> ResultadoPlan:
        t0 = time.perf_counter()
        p, rng = self.p, self.rng
        pob = []
        vistos = set()

        def agregar(c):
            c = self._canonico(c)
            if c not in vistos:
                vistos.add(c)
                pob.append(c)
                return True
            return False

        for c in self.semillas_cromosomas:
            agregar(c)
        if not self.semillas_cromosomas and p.n:
            for f in (orden_vecino, orden_2opt):
                agregar(self._desde_orden(f(p)))
        intentos = 0
        while len(pob) < self.poblacion and intentos < self.poblacion * 20:
            agregar(self._aleatorio())
            intentos += 1
        historial = []
        mejor_visto, ultima_mejora, sin_mejora = -np.inf, 0, 0
        for gen in range(self.generaciones):
            planes = [self.evaluar(c) for c in pob]
            fit = np.array([pl.fitness for pl in planes])
            orden_i = np.argsort(-fit, kind="stable")
            div = self.diversidad(pob)
            distintos = len(set(pob))
            # los mejores distintos (por orden y selección: no se repite el mismo recorrido con otra parada trivial)
            cands, firmas = [], set()
            for i in orden_i:
                firma = (planes[i].orden, planes[i].sel)
                if firma in firmas:
                    continue
                firmas.add(firma)
                cands.append(planes[i])
                if len(cands) >= self.n_candidatos:
                    break
            historial.append({"n": gen, "mejor": float(fit.max()), "media": float(fit.mean()), "peor": float(fit.min()),
                              "diversidad": float(div), "distintos": int(distintos), "candidatos": cands})
            if fit.max() > mejor_visto + 1e-12:
                mejor_visto, ultima_mejora, sin_mejora = float(fit.max()), gen, 0
            else:
                sin_mejora += 1
            if gen == self.generaciones - 1:
                break
            # --- siguiente generación ---
            adaptativa = div < self.umbral_diversidad
            pm = min(0.95, self.prob_mutacion * (2.0 if adaptativa else 1.0))
            nueva, firmas_n = [], set()
            for i in orden_i[:self.elite]:
                nueva.append(pob[i])
                firmas_n.add(pob[i])
            if sin_mejora >= 8 and adaptativa:                  # reinicio parcial: el 40 % peor se renueva
                corte = int(len(pob) * 0.6)
                nueva = [pob[i] for i in orden_i[:max(self.elite, corte)]]
                firmas_n = set(nueva)
                sin_mejora = 0
            n_inm = int(round(self.inmigrantes * self.poblacion * (2.0 if adaptativa else 1.0)))
            while len(nueva) < self.poblacion - n_inm:
                padres = []
                for _ in range(2):
                    idx = rng.choice(len(pob), size=min(self.torneo, len(pob)), replace=False)
                    padres.append(pob[max(idx, key=lambda k: fit[k])])
                for h in self._cruzar(*padres):
                    if len(nueva) >= self.poblacion - n_inm:
                        break
                    if rng.random() < pm:
                        h = self._mutar(h)
                    h = self._canonico(h)
                    tries = 0
                    while h in firmas_n and tries < 4:       # sin duplicados: se muta más
                        h = self._canonico(self._mutar(h, fuerza=2 + tries))
                        tries += 1
                    if h in firmas_n:
                        continue
                    firmas_n.add(h)
                    nueva.append(h)
            guard = 0
            while len(nueva) < self.poblacion and guard < self.poblacion * 20:
                guard += 1
                h = self._canonico(self._aleatorio())
                if h not in firmas_n:
                    firmas_n.add(h)
                    nueva.append(h)
            pob = nueva
        planes = sorted((self.cache[c] for c in pob), key=lambda q: -q.fitness)
        mejor = max(self.cache.values(), key=lambda q: q.fitness)
        return ResultadoPlan(mejor=mejor, historial=historial, tiempo_s=time.perf_counter() - t0,
                             evaluaciones=self.p.evaluaciones, ultima_mejora=ultima_mejora, problema=self.p)


def mejor_heuristico(p: Problema, nombre: str = "2opt") -> Plan:
    """Plan de una heurística «sin AG» (`vecino`, `2opt`, `ventanas`, `valor`) con la reparación de recargas."""
    return plan_heuristico(p, ordenes_heuristicos()[nombre](p))
