"""Pruebas de la interfaz v2 (contrato v2, Agente I): Numpad diagonal, clic para fijar objetivo,
ENTER/R y niveles, puntaje y record de sesion, eventos visibles de ambiente y falla de sensor.
Usan una partida falsa con la interfaz del contrato v2; no dependen de juego/partida.py."""
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pygame  # noqa: E402
import pytest  # noqa: E402

from juego import efectos, ui  # noqa: E402


SUG = {
    "rumbo": "E", "accion": "avanzar", "velocidad": 0.6,
    "p_barranco": 0.05, "p_obstaculo": 0.2, "p_libre": 0.75,
    "reglas": [("R1", 0.8, "obstaculo lejano")],
    "desglose": {"fitness": 1.5, "ciencia": 0.5, "distancia": 0.2, "energia": 0.3,
                 "riesgo": 0.1, "tiempo": 0.1, "penalizacion": 0.0},
    "motivos": ["OK"],
}


class PartidaV2:
    """Partida falsa con los atributos que el Agente I lee: estado, puntaje, ambiente, falla_restante,
    fijar_objetivo. Todo es opcional para la UI: si falta, la UI muestra '--' o no hace nada."""

    def __init__(self, semilla=11, nivel=1):
        self.semilla = semilla
        self.nivel = nivel
        self.estado = "EXPLORACION"
        self.ruta = [(19, 0), (18, 1)]
        self.rover = type("R", (), {"posicion": (19, 0), "bateria": 100.0})()
        self.mundo = type("W", (), {
            "tipo": np.zeros((20, 30), dtype=int), "refugio": (0, 29), "inicio": (19, 0),
            "sitios": {(5, 5): 7},
        })()
        self.puntaje_valor = 0
        self.ambiente = "normal"
        self.ambiente_restante = 0
        self.falla_restante = 0
        self.llamadas = []

    def sugerencia(self):
        return dict(SUG)

    def puntaje(self):
        return self.puntaje_valor

    def fijar_objetivo(self, celda):
        self.llamadas.append(("fijar", celda))
        if celda is None:
            return {"ok": True, "detalle": "plan normal"}
        if celda == (0, 0):
            return {"ok": False, "detalle": "celda no transitable"}
        return {"ok": True, "detalle": "ruta de 5 pasos"}

    def avanzar_ia(self):
        self.llamadas.append("avanzar")
        return {"estado": self.estado}

    def mover_jugador(self, rumbo):
        self.llamadas.append(("mover", rumbo))
        return {"movido": True, "estado": self.estado}

    def disparar_evento(self, nombre):
        self.llamadas.append(("evento", nombre))
        if nombre == "tormenta":
            self.ambiente, self.ambiente_restante = "tormenta", 6
        return {"ok": True, "detalle": "hecho"}


def fabrica_con_nivel(semilla, nivel=1):
    return PartidaV2(semilla, nivel)


def contar_titulo(juego, clave):
    titulo = efectos.CATALOGO[clave][0]
    return sum(1 for e in juego.efectos.activos if e["titulo"] == titulo)


# ---------------------------------------------------------------- teclas y clics

@pytest.mark.parametrize("tecla, esperado", [
    (pygame.K_KP7, ("mover", "NO")), (pygame.K_KP9, ("mover", "NE")),
    (pygame.K_KP1, ("mover", "SO")), (pygame.K_KP3, ("mover", "SE")),
])
def test_numpad_diagonales(tecla, esperado):
    assert ui.accion_de_tecla(tecla) == esperado


@pytest.mark.parametrize("tecla", [pygame.K_RETURN, pygame.K_KP_ENTER])
def test_enter_pide_siguiente_nivel(tecla):
    assert ui.accion_de_tecla(tecla) == ("siguiente", None)


def test_teclas_anteriores_siguen_igual():
    assert ui.accion_de_tecla(pygame.K_w) == ("mover", "N")
    assert ui.accion_de_tecla(pygame.K_SPACE) == ("avanzar", None)
    assert ui.accion_de_tecla(pygame.K_ESCAPE) == ("salir", None)


def test_clic_izquierdo_sobre_mapa_fija_celda():
    x = ui.MARGEN + 2 * ui.CELDA + 1
    y = ui.MARGEN + 1 * ui.CELDA + 1
    assert ui.accion_de_clic(1, (x, y)) == ("fijar", (1, 2))


def test_clic_izquierdo_fuera_del_mapa_no_hace_nada():
    assert ui.accion_de_clic(1, (ui.MARGEN + 30 * ui.CELDA, ui.MARGEN)) is None   # borde derecho
    assert ui.accion_de_clic(1, (5, 5)) is None                                   # margen
    assert ui.celda_desde_pixel((ui.MARGEN, ui.MARGEN + 20 * ui.CELDA)) is None   # borde inferior


def test_clic_derecho_quita_objetivo_en_cualquier_sitio():
    assert ui.accion_de_clic(3, (0, 0)) == ("fijar", None)
    assert ui.accion_de_clic(3, (600, 300)) == ("fijar", None)


def test_otros_botones_no_hacen_nada():
    assert ui.accion_de_clic(2, (100, 100)) is None   # central
    assert ui.accion_de_clic(4, (100, 100)) is None   # rueda


# ---------------------------------------------------------------- objetivo fijado

def test_clic_llama_fijar_objetivo_y_guarda_la_celda():
    juego = ui.Juego(lambda s: PartidaV2(s))
    juego.despachar("fijar", (3, 4))
    assert juego.partida.llamadas == [("fijar", (3, 4))]
    assert juego.objetivo_fijado == (3, 4)
    assert "ok" in juego.ultima_accion


def test_objetivo_fallido_conserva_el_anterior_y_lo_dice():
    juego = ui.Juego(lambda s: PartidaV2(s))
    juego.despachar("fijar", (3, 4))
    juego.despachar("fijar", (0, 0))
    assert juego.objetivo_fijado == (3, 4)
    assert "no" in juego.ultima_accion and "no transitable" in juego.ultima_accion


def test_clic_derecho_quita_el_objetivo():
    juego = ui.Juego(lambda s: PartidaV2(s))
    juego.despachar("fijar", (3, 4))
    juego.despachar("fijar", None)
    assert juego.objetivo_fijado is None
    assert juego.partida.llamadas[-1] == ("fijar", None)


def test_partida_sin_fijar_objetivo_avisa_sin_caerse():
    class SinFijar(PartidaV2):
        fijar_objetivo = None   # getattr(..., None) devuelve None: la UI no puede fijar

    juego = ui.Juego(lambda s: SinFijar(s))
    juego.despachar("fijar", (3, 4))
    assert "no disponible" in juego.ultima_accion
    assert juego.error is None
    assert juego.objetivo_fijado is None


def test_fijar_sin_partida_avisa():
    def fabrica_rota(_semilla):
        raise RuntimeError("sin mapa")

    juego = ui.Juego(fabrica_rota)
    juego.despachar("fijar", (1, 1))
    assert "no hay partida" in juego.error


# ---------------------------------------------------------------- niveles

def test_enter_solo_avanza_tras_exito():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    partida = juego.partida
    juego.despachar("siguiente")                   # estado EXPLORACION
    assert juego.nivel == 1 and juego.partida is partida
    assert "solo tras EXITO" in juego.ultima_accion


def test_enter_en_exito_pasa_al_nivel_siguiente_con_semilla_nueva():
    juego = ui.Juego(fabrica_con_nivel, semilla=5, rng=random.Random(3))
    juego.partida.estado = "EXITO"
    juego.despachar("siguiente")
    assert juego.nivel == 2
    assert juego.partida.nivel == 2
    assert juego.semilla != 5
    assert juego.error is None


def test_nivel_maximo_no_pasa_de_cinco():
    juego = ui.Juego(fabrica_con_nivel, semilla=5, nivel=5)
    juego.partida.estado = "EXITO"
    juego.despachar("siguiente")
    assert juego.nivel == 5
    assert "5/5" in juego.ultima_accion


def test_r_reinicia_el_nivel_actual_con_semilla_nueva():
    juego = ui.Juego(fabrica_con_nivel, semilla=5, nivel=2)
    juego.despachar("nueva")
    assert juego.nivel == 2 and juego.partida.nivel == 2
    assert juego.semilla != 5


def test_fabrica_sin_parametro_nivel_solo_admite_nivel_uno():
    juego = ui.Juego(lambda s: PartidaV2(s), semilla=5)
    juego.partida.estado = "EXITO"
    juego.despachar("siguiente")
    assert juego.nivel == 1
    assert "no acepta nivel" in juego.error


def test_fabrica_sin_nivel_con_nivel_inicial_mayor_falla_con_mensaje():
    juego = ui.Juego(lambda s: PartidaV2(s), semilla=5, nivel=3)
    assert juego.partida is None
    assert "no acepta nivel" in juego.error


# ---------------------------------------------------------------- puntaje y record

def test_record_de_sesion_es_el_maximo_entre_partidas():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    juego.partida.puntaje_valor = 40
    juego.despachar("avanzar")
    assert juego.puntaje == 40 and juego.record == 40

    juego.despachar("nueva")                        # partida nueva con puntaje menor
    juego.partida.puntaje_valor = 10
    juego.despachar("avanzar")
    assert juego.puntaje == 10 and juego.record == 40

    juego.despachar("nueva")
    juego.partida.puntaje_valor = 70
    juego.despachar("avanzar")
    assert juego.record == 70


def test_puntaje_ausente_muestra_guion():
    class SinPuntaje(PartidaV2):
        puntaje = None

    juego = ui.Juego(lambda s: SinPuntaje(s))
    assert juego.puntaje is None
    assert "Puntaje --" in ui.construir_vista(juego)["mision"][0]


def test_lineas_mision_con_datos_completos():
    lineas = ui.lineas_mision({"nivel": 2, "puntaje": 73, "bateria": 88.0, "ambiente": "tormenta",
                               "ambiente_restante": 4, "objetivo": (3, 4), "record": 80})
    assert len(lineas) == 5
    assert lineas[0] == "Nivel 2/5   Puntaje 73"
    assert lineas[1] == "Bateria: 88.0"
    assert lineas[2] == "Ambiente: tormenta: 4 pasos restantes"
    assert lineas[3] == "Objetivo: (3, 4)"
    assert lineas[4] == "Record de sesion: 80"


def test_lineas_mision_sin_datos_no_lanza():
    lineas = ui.lineas_mision({})
    assert lineas[0] == "Nivel --/5   Puntaje --"
    assert lineas[2] == "Ambiente: normal"
    assert lineas[3] == "Objetivo: ninguno (plan de la IA)"


def test_vista_incluye_mision_con_nivel_y_record():
    juego = ui.Juego(fabrica_con_nivel, semilla=5, nivel=3)
    juego.partida.puntaje_valor = 55
    juego.despachar("avanzar")
    vista = ui.construir_vista(juego)
    assert vista["mision"][0].startswith("Nivel 3/5   Puntaje 55")
    assert vista["mision"][4] == "Record de sesion: 55"


# ---------------------------------------------------------------- eventos visibles

def test_titulos_de_tormenta_y_noche_existen():
    assert efectos.titulo_de("tormenta") is not None
    assert efectos.titulo_de("noche") is not None
    assert "TORMENTA" in efectos.titulo_de("tormenta")[0]
    assert "NOCHE" in efectos.titulo_de("noche")[0]


def test_tinte_solo_para_ambientes_conocidos():
    e = efectos.Efectos(random.Random(1))
    e.fijar_ambiente("noche")
    assert e.ambiente == "noche"
    e.fijar_ambiente("normal")
    assert e.ambiente is None


def test_evento_manual_tormenta_muestra_titulo_una_sola_vez():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    juego.despachar("evento", "tormenta")
    assert contar_titulo(juego, "tormenta") == 1
    assert juego.efectos.ambiente == "tormenta"


def test_cambio_espontaneo_de_ambiente_muestra_titulo_sin_repetirlo():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    juego.partida.ambiente = "noche"                 # la partida cambio sola en un paso
    juego.partida.ambiente_restante = 8
    juego.despachar("avanzar")
    juego.despachar("avanzar")
    assert contar_titulo(juego, "noche") == 1
    assert juego.efectos.ambiente == "noche"


def test_al_terminar_el_ambiente_se_quita_el_tinte():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    juego.partida.ambiente = "tormenta"
    juego.despachar("avanzar")
    juego.partida.ambiente = "normal"
    juego.despachar("avanzar")
    assert juego.efectos.ambiente is None


def test_falla_de_sensor_activa_parpadeo_mientras_dure():
    juego = ui.Juego(fabrica_con_nivel, semilla=5)
    juego.partida.falla_restante = 3
    juego.despachar("sugerencia")
    assert juego.efectos.falla_activa is True
    juego.partida.falla_restante = 0
    juego.despachar("sugerencia")
    assert juego.efectos.falla_activa is False


def test_tinte_de_noche_cambia_pixeles_del_mapa_y_no_el_panel():
    e = efectos.Efectos(random.Random(1))
    e.fijar_ambiente("noche")
    superficie = pygame.Surface((ui.ANCHO, ui.ALTO))
    superficie.fill((255, 255, 255))
    e.dibujar(superficie, (ui.MARGEN, ui.MARGEN), ui.CELDA, 30 * ui.CELDA, None, alto_mapa=20 * ui.CELDA)
    assert tuple(superficie.get_at((ui.MARGEN + 5, ui.MARGEN + 5)))[:3] != (255, 255, 255)
    assert tuple(superficie.get_at((ui.PANEL_X + 5, ui.MARGEN + 5)))[:3] == (255, 255, 255)


def test_parpadeo_alterna_celdas_en_el_tiempo():
    e = efectos.Efectos(random.Random(1))
    e.fijar_falla(True)
    superficie = pygame.Surface((ui.ANCHO, ui.ALTO))
    superficie.fill((255, 255, 255))
    ojo = (ui.MARGEN + ui.CELDA + 5, ui.MARGEN + 5)   # fila 0, columna 1: fase par la deja clara
    e.dibujar(superficie, (ui.MARGEN, ui.MARGEN), ui.CELDA, 30 * ui.CELDA, None, alto_mapa=20 * ui.CELDA)
    assert tuple(superficie.get_at(ojo))[:3] == (255, 255, 255)
    for _ in range(efectos.CUADROS_POR_FASE_FALLA):
        e.actualizar()
    superficie.fill((255, 255, 255))
    e.dibujar(superficie, (ui.MARGEN, ui.MARGEN), ui.CELDA, 30 * ui.CELDA, None, alto_mapa=20 * ui.CELDA)
    assert tuple(superficie.get_at(ojo))[:3] != (255, 255, 255)


# ---------------------------------------------------------------- dibujo con los paneles nuevos

def test_dibujo_con_mision_ambiente_y_falla_no_lanza():
    pygame.init()
    try:
        superficie = pygame.Surface((ui.ANCHO, ui.ALTO))
        fuentes = {"cuerpo": pygame.font.Font(None, 20), "titulo": pygame.font.Font(None, 24),
                   "grande": pygame.font.Font(None, 44)}
        juego = ui.Juego(fabrica_con_nivel, semilla=5, nivel=2)
        juego.partida.ambiente = "tormenta"
        juego.partida.ambiente_restante = 5
        juego.partida.falla_restante = 2
        juego.despachar("evento", "falla_sensor")
        juego.despachar("fijar", (3, 4))
        ui.dibujar_todo(superficie, fuentes, ui.construir_vista(juego))
    finally:
        pygame.quit()


def test_ventana_con_clic_y_enter_no_tumba_el_bucle():
    # Ejecuta el bucle real con la ventana dummy; los eventos se inyectan parcheando pygame.event.get.
    eventos_por_cuadro = [
        [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(ui.MARGEN + 40, ui.MARGEN + 40))],
        [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="", scancode=0)],
        [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(0, 0))],
    ]
    original = pygame.event.get
    cola = list(eventos_por_cuadro)

    def falso_get(*_a, **_k):
        return cola.pop(0) if cola else []

    pygame.event.get = falso_get
    try:
        assert ui.ejecutar(lambda s, nivel=1: PartidaV2(s, nivel), semilla=2, max_cuadros=5) is None
    finally:
        pygame.event.get = original
    assert not pygame.get_init()
