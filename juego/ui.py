"""Interfaz pygame de ARES-X: mapa de Marte a la izquierda y paneles de la IA a la derecha.

Organizacion:
- Funciones puras (sin ventana): mapeo de teclas y clics, nombres de celda, formato de paneles,
  semilla nueva, formato de errores. Son las que prueban juego/tests/test_ui.py y test_ui_v2.py.
- Clase Juego: estado de la sesion y despacho de acciones. Cada accion va en try/except
  y se muestra como texto de estado; ninguna tecla tumba el programa.
- Funciones de dibujo: reciben una vista (diccionario de datos) y no mutan la partida.

La partida se crea con una fabrica inyectada (main.py pasa Partida), para que este modulo
no dependa de juego/partida.py al importarse. Si la fabrica acepta el parametro `nivel`
(o **kwargs), Juego la llama con nivel=n; si no, solo se permite el nivel 1.
"""
import inspect
import os
import random

import pygame

from simulador import OBSTACULO, BARRANCO
from juego import visual, efectos

ANCHO, ALTO = 1280, 720
CELDA = 30
MARGEN = 20
PANEL_X = MARGEN + 30 * CELDA + 20      # 940
PANEL_ANCHO = ANCHO - PANEL_X - 20      # 320
ESTADO_Y = MARGEN + 20 * CELDA + 20     # 640
SEMILLA_INICIAL = 11
SEMILLAS_COMPARACION = range(20)
CARPETA_EXPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exportaciones")
MAX_LINEAS_PANEL = 8
NIVEL_MAX = 5
COLUMNAS_MAPA, FILAS_MAPA = 30, 20

ACCIONES_PARTIDA = {"mover", "avanzar", "evento", "nueva", "fijar"}

RUMBO_TECLA = {
    pygame.K_UP: "N", pygame.K_w: "N",
    pygame.K_DOWN: "S", pygame.K_s: "S",
    pygame.K_RIGHT: "E", pygame.K_d: "E",
    pygame.K_LEFT: "O", pygame.K_a: "O",
}

# Numpad en diagonal (ev3-d28): 7 = NO, 9 = NE, 1 = SO, 3 = SE
RUMBO_DIAGONAL_TECLA = {
    pygame.K_KP7: "NO", pygame.K_KP9: "NE",
    pygame.K_KP1: "SO", pygame.K_KP3: "SE",
}

ACCION_TECLA = {
    pygame.K_SPACE: ("avanzar", None),
    pygame.K_TAB: ("sugerencia", None),
    pygame.K_b: ("evento", "barranco"),
    pygame.K_f: ("evento", "falla_sensor"),
    pygame.K_e: ("evento", "bateria_baja"),
    pygame.K_r: ("nueva", None),
    pygame.K_c: ("comparar", None),
    pygame.K_x: ("exportar", None),
    pygame.K_RETURN: ("siguiente", None),      # ev3: nivel siguiente tras EXITO
    pygame.K_KP_ENTER: ("siguiente", None),
    pygame.K_ESCAPE: ("salir", None),
}

COLORES = {
    "libre": (232, 220, 200), "obstaculo": (90, 70, 60), "barranco": (160, 40, 30),
    "refugio": (60, 170, 90), "sitio": (60, 130, 230), "ruta": (250, 220, 60),
    "objetivo": (220, 60, 220), "rover": (255, 140, 0), "sugerencia": (120, 255, 255),
    "fondo": (20, 20, 30), "texto": (230, 230, 230), "panel": (35, 35, 50),
    "titulo": (120, 200, 255), "error": (255, 110, 110), "atenuado": (150, 150, 160),
}


# ---------------------------------------------------------------- funciones puras

def accion_de_tecla(tecla):
    """Convierte un codigo de tecla de pygame en (accion, argumento) o None si no esta mapeada."""
    if tecla in RUMBO_TECLA:
        return ("mover", RUMBO_TECLA[tecla])
    if tecla in RUMBO_DIAGONAL_TECLA:
        return ("mover", RUMBO_DIAGONAL_TECLA[tecla])
    return ACCION_TECLA.get(tecla)


def celda_desde_pixel(pos):
    """Celda (fila, columna) del mapa bajo un punto de la ventana, o None si cae fuera del mapa."""
    x, y = pos
    if not (MARGEN <= x < MARGEN + COLUMNAS_MAPA * CELDA and MARGEN <= y < MARGEN + FILAS_MAPA * CELDA):
        return None
    return ((y - MARGEN) // CELDA, (x - MARGEN) // CELDA)


def accion_de_clic(boton, pos):
    """Clic izquierdo sobre el mapa fija objetivo; clic derecho lo quita (ev3-d27).
    Devuelve (accion, argumento) o None si el clic no hace nada."""
    if boton == 3:
        return ("fijar", None)
    if boton == 1:
        celda = celda_desde_pixel(pos)
        if celda is not None:
            return ("fijar", celda)
    return None


def nombre_celda(tipo, es_refugio=False, es_sitio=False):
    """Nombre de la clave de color de una celda del mapa."""
    if es_refugio:
        return "refugio"
    if tipo == OBSTACULO:
        return "obstaculo"
    if tipo == BARRANCO:
        return "barranco"
    if es_sitio:
        return "sitio"
    return "libre"


def celda_objetivo(ruta):
    """Celda que la IA quiere alcanzar: el destino de la ruta planeada, o None."""
    return tuple(ruta[-1]) if ruta else None


def nueva_semilla(anterior, rng):
    """Semilla nueva en [1, 9999] distinta de la anterior."""
    semilla = rng.randint(1, 9999)
    while semilla == anterior:
        semilla = rng.randint(1, 9999)
    return semilla


def formatear_error(exc):
    return f"{type(exc).__name__}: {exc}"


def _fmt(valor, decimales=2):
    try:
        return f"{float(valor):.{decimales}f}"
    except (TypeError, ValueError):
        return "--"


def lineas_rna(sug):
    """Panel RNA: probabilidades de libre, obstaculo y barranco."""
    if not sug:
        return ["Sin sugerencia"]
    return [
        f"P(libre)     {_fmt(sug.get('p_libre'))}",
        f"P(obstaculo) {_fmt(sug.get('p_obstaculo'))}",
        f"P(barranco)  {_fmt(sug.get('p_barranco'))}",
    ]


def lineas_difuso(sug):
    """Panel difuso: velocidad recomendada y reglas activadas."""
    if not sug:
        return ["Sin sugerencia"]
    lineas = [f"Velocidad: {_fmt(sug.get('velocidad'))}"]
    reglas = sug.get("reglas") or []
    if not reglas:
        lineas.append("Reglas activadas: ninguna")
    for regla in reglas:
        try:
            id_, fuerza, motivo = regla
            lineas.append(f"{id_} ({_fmt(fuerza)}): {motivo}")
        except (TypeError, ValueError):
            lineas.append(str(regla))
    return lineas


def lineas_ag(sug):
    """Panel AG: desglose del fitness de la ruta actual."""
    if not sug:
        return ["Sin sugerencia"]
    desglose = sug.get("desglose")
    if not desglose:
        return ["Sin ruta: no hay desglose"]
    orden = ["fitness", "ciencia", "distancia", "energia", "riesgo", "tiempo", "penalizacion"]
    return [f"{clave:<14}{_fmt(desglose.get(clave), 3)}" for clave in orden]


def lineas_supervisor(sug):
    """Panel supervisor: accion, rumbo y motivos (codigos V-, D- u OK)."""
    if not sug:
        return ["Sin sugerencia"]
    lineas = [f"Accion: {sug.get('accion')}", f"Rumbo:  {sug.get('rumbo') or '-'}"]
    motivos = sug.get("motivos") or []
    lineas.append("Motivos: " + (", ".join(str(m) for m in motivos) if motivos else "OK"))
    return lineas


def lineas_paneles(sug, mostrar=True):
    """Devuelve {titulo: lineas} de los cuatro paneles. Los paneles siempre muestran la IA (ev3-d18).
    `mostrar` solo controla la flecha de sugerencia en el mapa, no los paneles."""
    return {
        "RNA": lineas_rna(sug),
        "Difuso": lineas_difuso(sug),
        "Algoritmo genetico": lineas_ag(sug),
        "Supervisor": lineas_supervisor(sug),
    }


def lineas_mision(datos):
    """Panel Misión (ev3-d24, d25, d27): nivel, puntaje, batería, ambiente, objetivo fijado y el
    récord de la sesión, que va debajo del resto de líneas. `datos` viene de datos_mision()."""
    d = datos or {}
    puntaje = d.get("puntaje")
    ambiente = d.get("ambiente") or "normal"
    if ambiente == "normal":
        texto_ambiente = "normal"
    else:
        texto_ambiente = f"{ambiente}: {d.get('ambiente_restante') or 0} pasos restantes"
    objetivo = d.get("objetivo")
    texto_objetivo = f"{tuple(objetivo)}" if objetivo else "ninguno (plan de la IA)"
    record = d.get("record")
    return [
        f"Nivel {d.get('nivel') or '--'}/{NIVEL_MAX}   Puntaje {puntaje if puntaje is not None else '--'}",
        f"Bateria: {_fmt(d.get('bateria'), 1)}",
        f"Ambiente: {texto_ambiente}",
        f"Objetivo: {texto_objetivo}",
        f"Record de sesion: {record if record is not None else '--'}",
    ]


def lineas_comparacion(tabla):
    """Texto de la tabla de comparacion (DataFrame de experimento.comparar_variantes)."""
    if tabla is None:
        return []
    return str(tabla.to_string()).splitlines()


def texto_estado(juego):
    """Lineas de la barra de estado inferior: partida, ultima accion y errores."""
    partida = juego.partida
    if partida is None:
        return ["Sin partida activa. Pulsa R para crear una."]
    lineas = [
        f"Semilla {juego.semilla} | Estado: {partida.estado} | "
        f"Bateria: {_fmt(partida.rover.bateria, 1)} | Pos: {partida.rover.posicion}",
        f"Ultima accion: {juego.ultima_accion or '-'}",
    ]
    if juego.error:
        lineas.append(f"ERROR: {juego.error}")
    return lineas


def datos_mision(juego):
    """Datos del panel Misión leidos de la sesion y de la partida (sin modificarlas)."""
    partida = juego.partida
    return {
        "nivel": juego.nivel,
        "puntaje": juego.puntaje,
        "bateria": partida.rover.bateria if partida is not None else None,
        "ambiente": getattr(partida, "ambiente", None),
        "ambiente_restante": getattr(partida, "ambiente_restante", 0),
        "objetivo": juego.objetivo_fijado,
        "record": juego.record,
    }


def construir_vista(juego):
    """Datos que necesita el dibujo. No modifica nada de la partida."""
    partida = juego.partida
    vista = {
        "tipo": None, "refugio": None, "inicio": None, "sitios": {},
        "rover": None, "ruta": [], "objetivo": None,
        "sugerencia": juego.sugerencia, "mostrar": juego.mostrar_sugerencia,
        "paneles": lineas_paneles(juego.sugerencia, juego.mostrar_sugerencia),
        "mision": lineas_mision(datos_mision(juego)),
        "comparacion": juego.resumen_comparacion,
        "estado": texto_estado(juego), "semilla": juego.semilla, "efectos": getattr(juego, "efectos", None),
    }
    if partida is not None:
        mundo = partida.mundo
        vista.update({
            "tipo": mundo.tipo, "refugio": mundo.refugio, "inicio": mundo.inicio,
            "sitios": dict(mundo.sitios), "rover": tuple(partida.rover.posicion),
            "ruta": [tuple(c) for c in (partida.ruta or [])],
            "objetivo": celda_objetivo(partida.ruta),
        })
    return vista


def _acepta_nivel(fabrica):
    """True si la fabrica de partidas admite el parametro `nivel` (por nombre o **kwargs)."""
    try:
        parametros = inspect.signature(fabrica).parameters
    except (TypeError, ValueError):
        return False
    return "nivel" in parametros or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in parametros.values())


# ---------------------------------------------------------------- controlador

class Juego:
    """Estado de la sesion. Las acciones se despachan con despachar(accion, argumento)."""

    def __init__(self, crear_partida, semilla=SEMILLA_INICIAL, rng=None, nivel=1):
        self.crear_partida = crear_partida
        self.rng = rng or random.Random()
        self.semilla = semilla
        self.nivel = nivel
        self.partida = None
        self.sugerencia = None
        self.mostrar_sugerencia = False
        self.ultima_accion = ""
        self.error = None
        self.resumen_comparacion = []
        self.salir = False
        self.puntaje = None           # puntaje actual de la partida (None si no se puede calcular)
        self.record = 0               # maximo puntaje de la sesion (todas las partidas y niveles)
        self.objetivo_fijado = None   # celda que el jugador fijo con clic, o None
        self._estado_previo = None
        self._ambiente_previo = None
        self.efectos = efectos.Efectos(self.rng)
        self.reiniciar(semilla, nivel)

    def reiniciar(self, semilla, nivel=None):
        """Crea una partida nueva del nivel indicado (o del actual). Si falla, conserva la anterior
        y muestra el error. Devuelve True si la partida nueva quedo activa."""
        nivel = self.nivel if nivel is None else nivel
        try:
            nueva = self._crear(semilla, nivel)
        except Exception as exc:  # noqa: BLE001 - se muestra como texto de estado
            self.error = formatear_error(exc)
            return False
        self.partida = nueva
        self.semilla = semilla
        self.nivel = nivel
        self.resumen_comparacion = []
        self.objetivo_fijado = None
        self._estado_previo = None
        self._ambiente_previo = None
        self.ultima_accion = f"Partida nueva con semilla {semilla} (nivel {nivel})"
        self.error = None
        self._refrescar_sugerencia()
        self._refrescar_mision()
        self._sincronizar_visual()
        return True

    def _crear(self, semilla, nivel):
        if _acepta_nivel(self.crear_partida):
            return self.crear_partida(semilla, nivel=nivel)
        if nivel != 1:
            raise RuntimeError("la fabrica de partidas no acepta nivel (falta pasar nivel en main.py)")
        return self.crear_partida(semilla)

    def _refrescar_sugerencia(self):
        try:
            self.sugerencia = self.partida.sugerencia()
        except Exception as exc:  # noqa: BLE001
            self.sugerencia = None
            self.error = f"sugerencia: {formatear_error(exc)}"

    def _refrescar_mision(self):
        """Lee el puntaje de la partida (si la partida lo ofrece) y actualiza el record de la sesion."""
        self.puntaje = None
        puntaje = getattr(self.partida, "puntaje", None)
        if not callable(puntaje):
            return
        try:
            valor = puntaje()
        except Exception as exc:  # noqa: BLE001
            self.error = f"puntaje: {formatear_error(exc)}"
            return
        self.puntaje = valor
        if isinstance(valor, int) and not isinstance(valor, bool) and valor > self.record:
            self.record = valor

    def _sincronizar_visual(self):
        """Tinte de ambiente, titulo al cambiar de ambiente y parpadeo de falla de sensor."""
        partida = self.partida
        ambiente = getattr(partida, "ambiente", "normal") or "normal"
        if ambiente != self._ambiente_previo:
            if ambiente in efectos.TINTES:
                self.efectos.disparar(ambiente, tuple(partida.rover.posicion))
            self._ambiente_previo = ambiente
        self.efectos.fijar_ambiente(ambiente)
        self.efectos.fijar_falla((getattr(partida, "falla_restante", 0) or 0) > 0)

    def despachar(self, accion, argumento=None):
        """Ejecuta una accion. Nunca lanza excepciones hacia el bucle principal."""
        if self.partida is None and accion not in ("nueva", "salir", "sugerencia"):
            self.error = "no hay partida activa (pulsa R)"
            return
        self.error = None
        try:
            self._ejecutar(accion, argumento)
        except Exception as exc:  # noqa: BLE001
            self.error = formatear_error(exc)
        if self.partida is not None:
            if accion in ACCIONES_PARTIDA:
                self._refrescar_sugerencia()
            self._refrescar_mision()
            self._sincronizar_visual()

    def _ejecutar(self, accion, argumento):
        if accion == "mover":
            r = self.partida.mover_jugador(argumento)
            self.ultima_accion = f"Mover {argumento}: " + ("movido" if r.get("movido") else str(r.get("motivo")))
            if not r.get("movido"):
                self.efectos.disparar("bloqueado", tuple(self.partida.rover.posicion))
            self._efecto_fin(r.get("estado"))
        elif accion == "avanzar":
            r = self.partida.avanzar_ia()
            self.ultima_accion = f"IA avanza -> {r.get('estado')}"
            self._efecto_fin(r.get("estado"))
        elif accion == "evento":
            r = self.partida.disparar_evento(argumento)
            resultado = "aplicado" if r.get("ok") else "no aplicado"
            self.ultima_accion = f"Evento {argumento}: {resultado}. {r.get('detalle', '')}"
            if r.get("ok"):
                self.efectos.disparar(argumento, tuple(self.partida.rover.posicion))
                if argumento in efectos.TINTES:
                    # El titulo ya salio arriba; que _sincronizar_visual no lo repita.
                    self._ambiente_previo = getattr(self.partida, "ambiente", argumento)
        elif accion == "fijar":
            self._fijar_objetivo(argumento)
        elif accion == "siguiente":
            self._siguiente_nivel()
        elif accion == "sugerencia":
            self.mostrar_sugerencia = not self.mostrar_sugerencia
            self.ultima_accion = "Sugerencia de la IA " + ("visible" if self.mostrar_sugerencia else "oculta")
        elif accion == "nueva":
            self.reiniciar(nueva_semilla(self.semilla, self.rng))
        elif accion == "comparar":
            self._comparar()
        elif accion == "exportar":
            self._exportar()
        elif accion == "salir":
            self.salir = True

    def _fijar_objetivo(self, celda):
        """Clic izquierdo: fijar_objetivo(celda). Clic derecho: fijar_objetivo(None)."""
        fijar = getattr(self.partida, "fijar_objetivo", None)   # Partida (agente M) aun puede no tenerlo
        if fijar is None:
            self.ultima_accion = "Objetivo no disponible: la partida aun no tiene fijar_objetivo"
            return
        r = fijar(celda)
        ok = bool(r.get("ok"))
        if celda is None or ok:
            self.objetivo_fijado = celda
        etiqueta = "quitar objetivo" if celda is None else f"fijar en {celda}"
        self.ultima_accion = f"Objetivo: {etiqueta} -> {'ok' if ok else 'no'}. {r.get('detalle', '')}"

    def _siguiente_nivel(self):
        """ENTER: pasa al siguiente nivel solo si la partida esta en EXITO (maximo NIVEL_MAX)."""
        estado = getattr(self.partida, "estado", None)
        if estado != "EXITO":
            self.ultima_accion = f"ENTER avanza de nivel solo tras EXITO (estado: {estado})"
            return
        if self.nivel >= NIVEL_MAX:
            self.ultima_accion = f"Nivel {NIVEL_MAX}/{NIVEL_MAX} completado. R reinicia el nivel"
            return
        if self.reiniciar(nueva_semilla(self.semilla, self.rng), self.nivel + 1):
            self.ultima_accion = f"Nivel {self.nivel}/{NIVEL_MAX} iniciado"

    def _efecto_fin(self, estado):
        """Título grande cuando la IA cambia a un estado de fin o de alerta grave."""
        if estado in ("EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA") and estado != self._estado_previo:
            self.efectos.disparar(estado, tuple(self.partida.rover.posicion))
        self._estado_previo = estado

    def _comparar(self):
        try:
            from juego.experimento import comparar_variantes
        except ImportError:
            self.ultima_accion = "Comparacion no disponible: falta juego/experimento.py"
            return
        tabla = comparar_variantes(SEMILLAS_COMPARACION)
        self.resumen_comparacion = lineas_comparacion(tabla)
        self.ultima_accion = "Comparacion con 20 semillas lista"

    def _exportar(self):
        try:
            from juego.exportar import exportar_partida
        except ImportError:
            self.ultima_accion = "Exportacion no disponible: falta juego/exportar.py"
            return
        csv_path, json_path = exportar_partida(self.partida, CARPETA_EXPORTAR)
        self.ultima_accion = f"Exportado: {os.path.basename(csv_path)} y {os.path.basename(json_path)}"


# ---------------------------------------------------------------- dibujo

def _recortar(fuente, texto, ancho):
    if fuente.size(texto)[0] <= ancho:
        return texto
    while texto and fuente.size(texto + "...")[0] > ancho:
        texto = texto[:-1]
    return texto + "..."


def dibujar_mapa(superficie, fuente, vista):
    superficie.fill(COLORES["fondo"], pygame.Rect(MARGEN, MARGEN, 30 * CELDA, 20 * CELDA))
    tipo = vista["tipo"]
    if tipo is None:
        return
    terreno = visual.preparar_terreno(tipo, vista["refugio"], vista["sitios"], CELDA, MARGEN,
                                      semilla=vista.get("semilla", 0))
    superficie.blit(terreno, (MARGEN, MARGEN))
    visual.dibujar_ruta(superficie, vista["ruta"], CELDA, MARGEN)
    if vista["objetivo"] is not None:
        f, c = vista["objetivo"]
        rect = pygame.Rect(MARGEN + c * CELDA, MARGEN + f * CELDA, CELDA - 1, CELDA - 1)
        pygame.draw.rect(superficie, COLORES["objetivo"], rect, 2)
    if vista["rover"] is not None:
        sug = vista["sugerencia"]
        rumbo = sug.get("rumbo") if sug else None
        visual.dibujar_rover(superficie, vista["rover"], rumbo or "", CELDA, MARGEN)
    sug = vista["sugerencia"]
    if vista["mostrar"] and sug and sug.get("rumbo") and vista["rover"] is not None:
        _dibujar_flecha(superficie, vista["rover"], sug["rumbo"])


_DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1),
          "NE": (-1, 1), "NO": (-1, -1), "SE": (1, 1), "SO": (1, -1)}


def _dibujar_flecha(superficie, rover, rumbo):
    df, dc = _DELTA.get(rumbo, (0, 0))
    f, c = rover
    origen = (MARGEN + c * CELDA + CELDA // 2, MARGEN + f * CELDA + CELDA // 2)
    destino = (origen[0] + dc * CELDA, origen[1] + df * CELDA)
    pygame.draw.line(superficie, COLORES["sugerencia"], origen, destino, 3)
    pygame.draw.circle(superficie, COLORES["sugerencia"], destino, 5)


def _dibujar_caja(superficie, fuente, fuente_titulo, y, titulo, lineas, max_lineas=MAX_LINEAS_PANEL):
    """Dibuja una caja con titulo y lineas. Devuelve la altura usada."""
    alto = 26 + min(len(lineas), max_lineas) * 17 + 8
    superficie.fill(COLORES["panel"], pygame.Rect(PANEL_X, y, PANEL_ANCHO, alto))
    superficie.blit(fuente_titulo.render(titulo, True, COLORES["titulo"]), (PANEL_X + 8, y + 5))
    for i, linea in enumerate(lineas[:max_lineas]):
        texto = _recortar(fuente, linea, PANEL_ANCHO - 16)
        superficie.blit(fuente.render(texto, True, COLORES["texto"]), (PANEL_X + 8, y + 26 + i * 17))
    return alto


def dibujar_paneles(superficie, fuente, fuente_titulo, vista):
    y = MARGEN
    bloques = [("Misión", vista.get("mision") or ["Sin partida"])] + list(vista["paneles"].items())
    for titulo, lineas in bloques:
        y += _dibujar_caja(superficie, fuente, fuente_titulo, y, titulo, lineas) + 8
    if vista["comparacion"]:
        superficie.fill(COLORES["panel"], pygame.Rect(PANEL_X, y, PANEL_ANCHO, ALTO - y - 10))
        superficie.blit(fuente_titulo.render("Comparacion 20 semillas", True, COLORES["titulo"]),
                        (PANEL_X + 8, y + 5))
        for i, linea in enumerate(vista["comparacion"][:7]):
            texto = _recortar(fuente, linea, PANEL_ANCHO - 16)
            superficie.blit(fuente.render(texto, True, COLORES["texto"]), (PANEL_X + 8, y + 26 + i * 16))


def dibujar_estado(superficie, fuente, vista):
    lineas = vista["estado"]
    for i, linea in enumerate(lineas):
        color = COLORES["error"] if linea.startswith("ERROR") else COLORES["texto"]
        texto = _recortar(fuente, linea, 30 * CELDA)
        superficie.blit(fuente.render(texto, True, color), (MARGEN, ESTADO_Y + i * 18))
    ayuda = ("Flechas/WASD/Numpad mover | ESPACIO IA | TAB sugerencia | clic izq/der objetivo | "
             "ENTER nivel | B/F/E eventos | R nueva | C comparar | X exportar | ESC salir")
    superficie.blit(fuente.render(_recortar(fuente, ayuda, ANCHO - 40), True, COLORES["atenuado"]),
                    (MARGEN, ALTO - 24))


def dibujar_todo(superficie, fuentes, vista):
    superficie.fill(COLORES["fondo"])
    dibujar_mapa(superficie, fuentes["cuerpo"], vista)
    if vista.get("efectos") is not None and fuentes.get("grande") is not None:
        vista["efectos"].dibujar(superficie, (MARGEN, MARGEN), CELDA, 30 * CELDA, fuentes["grande"],
                                 alto_mapa=20 * CELDA)
    dibujar_paneles(superficie, fuentes["cuerpo"], fuentes["titulo"], vista)
    dibujar_estado(superficie, fuentes["cuerpo"], vista)


# ---------------------------------------------------------------- bucle principal

def ejecutar(crear_partida, semilla=SEMILLA_INICIAL, max_cuadros=None):
    """Abre la ventana y corre el bucle. max_cuadros permite cerrarla sola (pruebas)."""
    pygame.init()
    try:
        superficie = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("ARES-X: rover en Marte")
        reloj = pygame.time.Clock()
        fuentes = {"cuerpo": pygame.font.Font(None, 20), "titulo": pygame.font.Font(None, 24),
                   "grande": pygame.font.Font(None, 44)}
        juego = Juego(crear_partida, semilla=semilla)
        cuadros = 0
        while not juego.salir:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    juego.salir = True
                elif evento.type == pygame.KEYDOWN:
                    accion = accion_de_tecla(evento.key)
                    if accion is not None:
                        juego.despachar(*accion)
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    accion = accion_de_clic(evento.button, evento.pos)
                    if accion is not None:
                        juego.despachar(*accion)
            dibujar_todo(superficie, fuentes, construir_vista(juego))
            juego.efectos.actualizar()
            pygame.display.flip()
            reloj.tick(30)
            cuadros += 1
            if max_cuadros is not None and cuadros >= max_cuadros:
                break
    finally:
        pygame.quit()
