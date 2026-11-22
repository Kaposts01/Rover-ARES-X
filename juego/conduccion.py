"""Conducción por modo (ARX-11): cada técnica mueve el rover por sí sola.

Modos sueltos (cada uno conduce sin depender de las otras dos técnicas):
- rna:    entre los 8 vecinos transitables, el de mayor p_libre que acerca al objetivo. Si ninguno acerca, rodea.
- difuso: avanza por el camino BFS hacia el objetivo con la velocidad difusa; si la velocidad es baja, espera
          y, tras PASOS_PARADO_MAXIMO pasos, rodea con la regla de la RNA.
- ag:     sigue la ruta del AG; replanifica con el AG solo si la siguiente celda queda bloqueada.

Veto de seguridad (interruptor, encendido por defecto):
- Encendido: el supervisor no deja avanzar hacia una celda que la RNA (barranco u obstáculo > 0,5) o el LIDAR
  (borde de barranco) marcan como peligrosa. Motivo: V-SEGURIDAD-BARRANCO / V-SEGURIDAD-OBSTACULO.
- Apagado: el movimiento se intenta igual. Si la celda es intransitable cuenta como colisión y queda marcada
  como riesgo para el resto de la partida. Sirve para ver cómo falla cada técnica sola.

Las celdas con riesgo conocido (>= 0,5) nunca son candidatas, con el veto encendido o apagado.
Capa de juego: no modifica simulador, rna, difuso, genetico ni integracion; usa sus funciones.
"""
import copy
from dataclasses import dataclass

from genetico import camino_bfs
from integracion import barrancos_medidos, camino_valido
from integracion import ESTADOS_TERMINALES, GRADOS_POR_GRADIENTE, PASOS_PARADO_MAXIMO, UMBRAL_RIESGO_RNA, \
    UMBRAL_VELOCIDAD_MINIMA, _rumbo
from rna import _rasgos_celda, inclinacion_de_rasgos
from simulador import BARRANCO, MOVIMIENTOS, SensorSuite, paso_fisico

MODOS_CONDUCCION = ("rna", "difuso", "ag")
HISTORIAL_RECIENTE = 4        # últimas celdas visitadas; la RNA evita volver a ellas si hay alternativa


def _cheb(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _objetivo(partida):
    """Siguiente sitio pendiente en el orden del AG; el refugio cuando no quedan."""
    m = partida.mision
    pendientes = [o for o in m.objetivos if o not in m.visitados]
    return pendientes[0] if pendientes else partida.mundo.refugio


def _observar(partida) -> dict:
    """Rasgos, probabilidades y borde LIDAR de cada una de las 8 direcciones.

    Usa copias del generador y del sensor: la observación no consume el ruido real de la partida.
    """
    m = partida.mision
    pos = partida.rover.posicion
    rng = copy.deepcopy(m.rng)
    sensor = SensorSuite(rng=rng, ruido=m.sensor.ruido, prob_fallo=m.sensor.prob_fallo)
    obs = {}
    for rumbo in MOVIMIENTOS:
        rasgos, _ = _rasgos_celda(partida.mundo, pos, rumbo, sensor, rng)
        probs = m.rna.explicar(rasgos)["probabilidades"] if m.usar_rna else {"libre": 1.0}
        if m.intervencion_rna is not None and m.usar_rna:
            probs = m.intervencion_rna(probs)
        # LIDAR por celda: solo cuenta si la celda de enfrente (pos + rumbo) es un barranco detectado
        lectura = sensor.leer(partida.mundo, pos, rumbo)
        df, dc = MOVIMIENTOS[rumbo]
        frente = (pos[0] + df, pos[1] + dc)
        obs[rumbo] = {"rasgos": rasgos, "probs": probs, "borde": frente in barrancos_medidos(lectura)}
    return obs


def _motivo_veto(obs_dir: dict, veto: bool):
    if not veto:
        return None
    if obs_dir["borde"] or obs_dir["probs"].get("barranco", 0.0) > UMBRAL_RIESGO_RNA:
        return "V-SEGURIDAD-BARRANCO"
    if obs_dir["probs"].get("obstáculo", 0.0) > UMBRAL_RIESGO_RNA:
        return "V-SEGURIDAD-OBSTACULO"
    return None


@dataclass
class Candidato:
    rumbo: str
    destino: tuple
    p_libre: float
    veto: str = None


def _marcar_veto(partida, destino) -> None:
    """Lo que el veto ve como peligroso pasa a riesgo conocido: así la planificación lo rodea."""
    partida.mision.riesgo[destino] = 1.0


def _candidatos(partida, obs: dict, veto: bool) -> list:
    m = partida.mision
    pos = partida.rover.posicion
    res = []
    for rumbo, (df, dc) in MOVIMIENTOS.items():
        destino = (pos[0] + df, pos[1] + dc)
        if not partida.mundo.dentro(destino) or m.riesgo[destino] >= UMBRAL_RIESGO_RNA:
            continue
        motivo = _motivo_veto(obs[rumbo], veto)
        if motivo:
            _marcar_veto(partida, destino)
        res.append(Candidato(rumbo, destino, obs[rumbo]["probs"].get("libre", 0.0), motivo))
    return res


def _elegir_rna(partida, cands: list, objetivo) -> Candidato:
    """Mayor p_libre entre los que acercan al objetivo; si ninguno acerca, rodea (mayor p_libre)."""
    pos = partida.rover.posicion
    recientes = getattr(partida, "_historial", [])
    libres = [c for c in cands if c.veto is None]
    if not libres:
        return None
    acercan = [c for c in libres if _cheb(c.destino, objetivo) < _cheb(pos, objetivo)]
    frescos = [c for c in acercan if c.destino not in recientes]
    if frescos or acercan:
        return max(frescos or acercan, key=lambda c: c.p_libre)
    return max(libres, key=lambda c: (c.destino not in recientes, c.p_libre))


def _ruta_bfs(partida, objetivo):
    m = partida.mision
    return camino_bfs(partida.rover.posicion, objetivo, m.riesgo < UMBRAL_RIESGO_RNA)


def _replanear_ag(partida) -> None:
    """Replanteo del modo ag con el AG de verdad (ARX-18.4): reordena los sitios pendientes y reconstruye la ruta.

    Usa el mismo optimizador que la planificación inicial (`Mision._optimizar_ag`). Si el AG no da ruta,
    cae al BFS por el orden anterior. Un objetivo fijado por el jugador no se toca.
    """
    m = partida.mision
    if partida._objetivo is not None:
        _replanear_ag(partida)
        return
    origen = partida.rover.posicion
    pendientes = {p: v for p, v in partida.mundo.sitios.items() if p not in m.visitados}
    ruta = m._optimizar_ag(origen, pendientes) if pendientes else []
    if ruta and any(c in partida.mundo.sitios for c in ruta):
        m.objetivos = [c for c in ruta if c in partida.mundo.sitios] + [partida.mundo.refugio]
        m.replanes += 1
        m.ruta = ruta if camino_valido(ruta, m.riesgo) else []
        if not m.ruta:
            m.ruta = _ruta_bfs(partida, origen)
    elif not pendientes:
        # sin sitios pendientes el destino es el refugio; antes se volvía a llamar a sí misma sin fin (RecursionError)
        m.objetivos = [partida.mundo.refugio]
        m.ruta = _ruta_bfs(partida, partida.mundo.refugio)
        m.replanes += 1
    else:
        m.ruta = _ruta_bfs(partida, origen)


def _ejecutar(partida, rumbo: str, destino) -> bool:
    """Intenta el movimiento. Si la física lo bloquea, cuenta colisión y marca la celda como riesgo."""
    m = partida.mision
    if paso_fisico(partida.mundo, partida.rover, rumbo):
        return True
    m.colisiones += 1
    if partida.mundo.tipo[destino] == BARRANCO:
        partida.intentos_barranco += 1
    m.riesgo[destino] = 1.0
    return False


def _tras_mover(partida, destino, objetivo, ruta_ag: bool):
    """Mantiene la ruta y el historial coherentes con la nueva posición."""
    m = partida.mision
    pos = partida.rover.posicion
    historial = getattr(partida, "_historial", [])
    partida._historial = (historial + [pos])[-HISTORIAL_RECIENTE:]
    if pos in partida.mundo.sitios:
        m.visitados.add(pos)
    if ruta_ag and len(m.ruta) > 1 and m.ruta[1] == pos:
        m.ruta.pop(0)
    else:
        tramo = _ruta_bfs(partida, objetivo)
        m.ruta = [pos] + (tramo[1:] if tramo else [])


def _estado_tras_paso(partida, accion: str, motivos: list, obs_dir, velocidad: float, fz=None):
    m = partida.mision
    partida._tick_ambiente()
    if partida.rover.bateria <= 0 and partida.estado not in ESTADOS_TERMINALES:
        m.estado = "FRACASO"
    m._registrar(accion, velocidad, motivos, obs_dir or {}, fz)   # ARX-80: fz real en el modo difuso
    return {"accion": accion, "motivos": motivos, **partida._posicion_estado()}


def _rodear(partida, obs, veto, objetivo, motivos):
    """Regla de la RNA aplicada como alternativa (difuso al esperar demasiado o con el paso vetado)."""
    cands = _candidatos(partida, obs, veto)
    elegido = _elegir_rna(partida, cands, objetivo)
    for c in cands:
        if c.veto:
            motivos.append(c.veto)
    return elegido


def avanzar(partida, modo: str, veto: bool = True) -> dict:
    """Un paso del modo indicado. Devuelve accion, motivos y la posición (igual que Partida.avanzar_ia)."""
    if modo not in MODOS_CONDUCCION:
        raise ValueError(f"modo de conducción inválido: {modo!r}; usa uno de {MODOS_CONDUCCION}")
    m = partida.mision
    if partida.estado in ESTADOS_TERMINALES:
        return {**partida.sugerencia(), **partida._posicion_estado()}
    if partida._falla_restante > 0:
        partida._paso_con_falla()
        return {**partida.sugerencia(), **partida._posicion_estado()}

    m.paso += 1
    pos = partida.rover.posicion
    objetivo = _objetivo(partida)
    if pos == partida.mundo.refugio and not m._quedan_sitios():
        m.estado = "EXITO"
        return _estado_tras_paso(partida, "fin", ["D-META-ALCANZADA"], None, 0.0)

    obs = _observar(partida)
    motivos = []

    if modo == "rna":
        cands = _candidatos(partida, obs, veto)
        motivos += sorted({c.veto for c in cands if c.veto})
        elegido = _elegir_rna(partida, cands, objetivo)
        if elegido is None:
            return _estado_tras_paso(partida, "detener", motivos + ["D-SIN-CANDIDATO"], None, 0.0)
        ok = _ejecutar(partida, elegido.rumbo, elegido.destino)
        if ok:
            _tras_mover(partida, elegido.destino, objetivo, ruta_ag=False)
        return _estado_tras_paso(partida, "avanzar" if ok else "bloqueado",
                                 motivos + ["RNA-MAX-PLIBRE"], obs[elegido.rumbo]["probs"], 0.0)

    if modo == "difuso":
        tramo = _ruta_bfs(partida, objetivo)
        if not tramo or len(tramo) < 2:
            return _estado_tras_paso(partida, "replanificar", ["D-SIN-CAMINO"], None, 0.0)
        siguiente = tramo[1]
        rumbo = _rumbo(pos, siguiente)
        # auditoría 22/11: con el perfil v2 el rasgo 2 es el contraste óptico; la pendiente sale como en Mision.paso_mision
        inclinacion = min(45.0, inclinacion_de_rasgos(obs[rumbo]["rasgos"]) * GRADOS_POR_GRADIENTE)
        fz = m.difuso.inferir(m._distancia_a_riesgo_en_ruta(), partida.rover.bateria, inclinacion)
        v = float(fz.velocidad)
        if m.intervencion_difuso is not None:        # prueba causal (ARX-10) también en el modo difuso (ARX-18.2)
            v = float(m.intervencion_difuso)
        veto_dir = _motivo_veto(obs[rumbo], veto)
        if veto_dir:
            motivos.append(veto_dir)
            _marcar_veto(partida, siguiente)
        if v < UMBRAL_VELOCIDAD_MINIMA or veto_dir:
            partida.esperas = getattr(partida, "esperas", 0) + 1
            if partida.esperas < PASOS_PARADO_MAXIMO:
                return _estado_tras_paso(partida, "detener", motivos + ["D-VELOCIDAD-BAJA"],
                                         obs[rumbo]["probs"], v, fz)
            # espera agotada: rodea con la regla de la RNA
            partida.esperas = 0
            elegido = _rodear(partida, obs, veto, objetivo, motivos)
            if elegido is None:
                return _estado_tras_paso(partida, "replanificar", motivos + ["V-RODEO-SIN-CANDIDATO"], None, v, fz)
            ok = _ejecutar(partida, elegido.rumbo, elegido.destino)
            if ok:
                _tras_mover(partida, elegido.destino, objetivo, ruta_ag=False)
            return _estado_tras_paso(partida, "rodear" if ok else "bloqueado", motivos + ["D-RODEO"],
                                     obs[elegido.rumbo]["probs"], v, fz)
        partida.esperas = 0
        ok = _ejecutar(partida, rumbo, siguiente)
        if ok:
            _tras_mover(partida, siguiente, objetivo, ruta_ag=False)
        return _estado_tras_paso(partida, "avanzar" if ok else "bloqueado", motivos + ["D-VELOCIDAD-OK"],
                                 obs[rumbo]["probs"], v, fz)

    # modo "ag": sigue su ruta; replanifica solo si el siguiente paso queda bloqueado
    salto_invalido = len(m.ruta) >= 2 and max(abs(m.ruta[1][0] - pos[0]), abs(m.ruta[1][1] - pos[1])) > 1
    if len(m.ruta) < 2 or m.ruta[0] != pos or salto_invalido:
        _replanear_ag(partida)
    if len(m.ruta) < 2:
        m.estado = "SIN_RUTA"
        return _estado_tras_paso(partida, "replanificar", ["REPLAN-SIN-RUTA"], None, 0.0)
    siguiente = m.ruta[1]
    rumbo = _rumbo(pos, siguiente)
    veto_dir = _motivo_veto(obs[rumbo], veto)
    if veto_dir:
        _marcar_veto(partida, siguiente)
    if m.riesgo[siguiente] >= UMBRAL_RIESGO_RNA or veto_dir:
        motivos = [veto_dir] if veto_dir else ["V-RUTA-CON-RIESGO"]
        _replanear_ag(partida)
        return _estado_tras_paso(partida, "replanificar", motivos, obs[rumbo]["probs"], 0.0)
    ok = _ejecutar(partida, rumbo, siguiente)
    if ok:
        _tras_mover(partida, siguiente, objetivo, ruta_ag=True)
    else:
        _replanear_ag(partida)
    return _estado_tras_paso(partida, "avanzar" if ok else "bloqueado",
                             ["AG-SIGUE-RUTA"] if ok else ["V-CELDA-BLOQUEADA"],
                             obs[rumbo]["probs"], 0.0)


def correr(semilla: int, modo: str, veto: bool = True, max_pasos: int = 400) -> dict:
    """Una partida completa con un modo. `automatico` usa el controlador híbrido (sin veto aparte)."""
    from juego.partida import Partida
    from juego.partida import FILAS_BASE, COLUMNAS_BASE
    p = Partida(semilla=semilla, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)   # evaluación congelada: 20x30, sin redibujar el mapa
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < max_pasos:
        if modo == "automatico":
            p.avanzar_ia()
        else:
            p.avanzar_modo(modo, veto)
        pasos += 1
    return {"semilla": semilla, "modo": modo, "veto": None if modo == "automatico" else veto,
            "estado": p.estado, "exito": p.estado == "EXITO", "pasos": pasos,
            "colisiones": p.mision.colisiones, "intentos_barranco": p.intentos_barranco,
            "sitios_visitados": len(p.mision.visitados)}
