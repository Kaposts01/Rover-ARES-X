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

from juego import ui  # noqa: E402
from simulador import LIBRE, OBSTACULO, BARRANCO  # noqa: E402


SUG = {
    "rumbo": "E", "accion": "avanzar", "velocidad": 0.6,
    "p_barranco": 0.05, "p_obstaculo": 0.2, "p_libre": 0.75,
    "reglas": [("R1", 0.8, "obstaculo lejano"), ("R3", 0.4, "batería baja")],
    "desglose": {"fitness": 1.5, "ciencia": 0.5, "distancia": 0.2, "energia": 0.3,
                 "riesgo": 0.1, "tiempo": 0.1, "penalizacion": 0.0},
    "motivos": ["OK"],
}


class FakePartida:
    """Partida falsa con la interfaz del contrato, para probar el controlador sin partida.py."""

    def __init__(self, semilla=11, fallar_sugerencia=False):
        self.semilla = semilla
        self.estado = "EXPLORACION"
        self.ruta = [(19, 0), (19, 1), (18, 1)]
        self.rover = type("R", (), {"posicion": (19, 0), "bateria": 100.0})()
        self.mundo = type("W", (), {
            "tipo": np.zeros((20, 30), dtype=int), "refugio": (0, 29), "inicio": (19, 0),
            "sitios": {(5, 5): 7},
        })()
        self.fallar_sugerencia = fallar_sugerencia
        self.llamadas = []

    def sugerencia(self):
        if self.fallar_sugerencia:
            raise RuntimeError("fallo simulado")
        return dict(SUG)

    def avanzar_ia(self):
        self.llamadas.append("avanzar")
        return {"estado": "ALERTA", "posicion": (19, 1), "bateria": 99.0, **SUG}

    def mover_jugador(self, rumbo):
        self.llamadas.append(("mover", rumbo))
        return {"movido": rumbo == "N", "motivo": "barranco" if rumbo != "N" else "ok",
                "posicion": (19, 0), "bateria": 100.0, "estado": self.estado}

    def disparar_evento(self, nombre):
        self.llamadas.append(("evento", nombre))
        if nombre not in ("barranco", "falla_sensor", "bateria_baja"):
            return {"ok": False, "detalle": "no soportado"}
        return {"ok": True, "detalle": "hecho"}


# ---------------------------------------------------------------- teclas

@pytest.mark.parametrize("tecla, esperado", [
    (pygame.K_UP, ("mover", "N")), (pygame.K_w, ("mover", "N")),
    (pygame.K_DOWN, ("mover", "S")), (pygame.K_s, ("mover", "S")),
    (pygame.K_RIGHT, ("mover", "E")), (pygame.K_d, ("mover", "E")),
    (pygame.K_LEFT, ("mover", "O")), (pygame.K_a, ("mover", "O")),
    (pygame.K_SPACE, ("avanzar", None)), (pygame.K_TAB, ("sugerencia", None)),
    (pygame.K_b, ("evento", "barranco")), (pygame.K_f, ("evento", "falla_sensor")),
    (pygame.K_e, ("evento", "bateria_baja")), (pygame.K_r, ("nueva", None)),
    (pygame.K_c, ("comparar", None)), (pygame.K_x, ("exportar", None)),
    (pygame.K_ESCAPE, ("salir", None)),
])
def test_teclas_mapeadas(tecla, esperado):
    assert ui.accion_de_tecla(tecla) == esperado


def test_tecla_no_mapeada_devuelve_none():
    assert ui.accion_de_tecla(pygame.K_q) is None


# ---------------------------------------------------------------- formato de paneles

def test_lineas_rna_muestran_probabilidades():
    lineas = ui.lineas_rna(SUG)
    assert len(lineas) == 3
    assert "0.75" in lineas[0] and "0.20" in lineas[1] and "0.05" in lineas[2]


def test_lineas_difuso_incluyen_velocidad_y_reglas():
    lineas = ui.lineas_difuso(SUG)
    assert lineas[0] == "Velocidad: 0.60"
    assert "R1 (0.80): obstaculo lejano" in lineas[1]
    assert len(lineas) == 3


def test_lineas_difuso_sin_reglas():
    sug = dict(SUG, reglas=[])
    assert ui.lineas_difuso(sug)[-1] == "Reglas activadas: ninguna"


def test_lineas_ag_sin_desglose_avisa_sin_ruta():
    assert ui.lineas_ag(dict(SUG, desglose=None)) == ["Sin ruta: no hay desglose"]


def test_lineas_ag_con_desglose_tiene_siete_componentes():
    lineas = ui.lineas_ag(SUG)
    assert len(lineas) == 7
    assert lineas[0].startswith("fitness") and "1.500" in lineas[0]


def test_lineas_supervisor_muestra_accion_rumbo_y_motivos():
    lineas = ui.lineas_supervisor(dict(SUG, motivos=["V-OBST", "D-RUTA"]))
    assert lineas[0] == "Accion: avanzar"
    assert lineas[1] == "Rumbo:  E"
    assert lineas[2] == "Motivos: V-OBST, D-RUTA"


def test_lineas_supervisor_sin_motivos_dice_ok():
    assert ui.lineas_supervisor(dict(SUG, motivos=[]))[2] == "Motivos: OK"


def test_sin_sugerencia_todos_los_paneles_dicen_sin_datos():
    paneles = ui.lineas_paneles(None, True)
    assert all(lineas == ["Sin sugerencia"] for lineas in paneles.values())


def test_paneles_siempre_muestran_la_ia_aunque_tab_este_apagado():
    # ev3-d18: los paneles laterales siempre visibles; TAB solo controla la flecha de sugerencia
    paneles = ui.lineas_paneles(SUG, False)
    assert paneles == ui.lineas_paneles(SUG, True)
    assert not any("TAB" in linea for lineas in paneles.values() for linea in lineas)


def test_formato_tolera_valores_faltantes():
    # Un diccionario incompleto no debe lanzar excepcion.
    assert ui.lineas_rna({"p_libre": None})[0].endswith("--")
    assert ui.lineas_rna({})[0] == "Sin sugerencia"
    assert ui.lineas_difuso({"reglas": [("X",)]})  # regla mal formada


# ---------------------------------------------------------------- celdas y semilla

@pytest.mark.parametrize("tipo, refugio, sitio, esperado", [
    (LIBRE, False, False, "libre"), (OBSTACULO, False, False, "obstaculo"),
    (BARRANCO, False, False, "barranco"), (LIBRE, False, True, "sitio"),
    (LIBRE, True, False, "refugio"),
])
def test_nombre_celda(tipo, refugio, sitio, esperado):
    assert ui.nombre_celda(tipo, refugio, sitio) == esperado


def test_nombre_celda_nombres_tienen_color():
    for nombre in ["libre", "obstaculo", "barranco", "refugio", "sitio"]:
        assert nombre in ui.COLORES


def test_celda_objetivo_es_fin_de_ruta():
    assert ui.celda_objetivo([(1, 1), (1, 2), (0, 2)]) == (0, 2)
    assert ui.celda_objetivo([]) is None


def test_nueva_semilla_nunca_repite_la_anterior():
    rng = random.Random(0)
    for anterior in [1, 5, 9999]:
        for _ in range(200):
            s = ui.nueva_semilla(anterior, rng)
            assert s != anterior and 1 <= s <= 9999


# ---------------------------------------------------------------- controlador

def test_juego_crea_partida_y_sugerencia():
    juego = ui.Juego(lambda s: FakePartida(s), semilla=3)
    assert juego.partida.semilla == 3
    assert juego.sugerencia["rumbo"] == "E"
    assert juego.error is None


def test_tab_alterna_visibilidad_sin_avanzar_la_partida():
    juego = ui.Juego(lambda s: FakePartida(s))
    juego.despachar("sugerencia")
    assert juego.mostrar_sugerencia is True
    juego.despachar("sugerencia")
    assert juego.mostrar_sugerencia is False
    assert juego.partida.llamadas == []


def test_acciones_de_partida_llegan_a_la_partida():
    juego = ui.Juego(lambda s: FakePartida(s))
    juego.despachar("avanzar")
    juego.despachar("mover", "S")
    juego.despachar("mover", "N")
    juego.despachar("evento", "barranco")
    assert juego.partida.llamadas == ["avanzar", ("mover", "S"), ("mover", "N"), ("evento", "barranco")]
    assert juego.ultima_accion.startswith("Evento barranco")  # ultima accion es la del evento


def test_evento_no_aplicado_se_muestra_como_texto():
    juego = ui.Juego(lambda s: FakePartida(s))
    juego.despachar("evento", "inventado")
    assert "no aplicado" in juego.ultima_accion


def test_excepcion_de_partida_no_tumba_y_queda_como_error():
    juego = ui.Juego(lambda s: FakePartida(s))

    def romper(*_a, **_k):
        raise ValueError("boom")

    juego.partida.avanzar_ia = romper
    juego.despachar("avanzar")
    assert juego.error == "ValueError: boom"
    # La siguiente tecla sigue funcionando y limpia el error.
    juego.despachar("sugerencia")
    assert juego.error is None


def test_fallo_de_sugerencia_se_registra_sin_caerse():
    juego = ui.Juego(lambda s: FakePartida(s, fallar_sugerencia=True))
    assert juego.sugerencia is None
    assert "sugerencia" in juego.error


def test_nueva_partida_usa_semilla_distinta_y_conserva_anterior_si_falla():
    juego = ui.Juego(lambda s: FakePartida(s), semilla=7, rng=random.Random(1))
    juego.despachar("nueva")
    assert juego.semilla != 7

    intento = {"n": 0}

    def fabrica(s):
        intento["n"] += 1
        if intento["n"] > 1:
            raise RuntimeError("sin mapa")
        return FakePartida(s)

    juego2 = ui.Juego(fabrica, semilla=7)
    anterior = juego2.partida
    juego2.despachar("nueva")
    assert juego2.partida is anterior
    assert "sin mapa" in juego2.error


def test_sin_partida_las_teclas_de_juego_avisan():
    def fabrica_rota(s):
        raise RuntimeError("no")

    juego = ui.Juego(fabrica_rota, semilla=1)
    assert juego.partida is None
    assert "no" in juego.error
    juego.despachar("avanzar")
    assert "no hay partida" in juego.error
    assert juego.salir is False


def test_salir_marca_bandera():
    juego = ui.Juego(lambda s: FakePartida(s))
    juego.despachar("salir")
    assert juego.salir is True


def test_comparar_sin_experimento_muestra_mensaje(monkeypatch):
    juego = ui.Juego(lambda s: FakePartida(s))
    import builtins
    real_import = builtins.__import__

    def sin_experimento(name, *a, **k):
        if name == "juego.experimento":
            raise ImportError("no existe")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_experimento)
    juego.despachar("comparar")
    assert "falta juego/experimento.py" in juego.ultima_accion


def test_exportar_sin_modulo_muestra_mensaje(monkeypatch):
    juego = ui.Juego(lambda s: FakePartida(s))
    import builtins
    real_import = builtins.__import__

    def sin_exportar(name, *a, **k):
        if name == "juego.exportar":
            raise ImportError("no existe")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_exportar)
    juego.despachar("exportar")
    assert "falta juego/exportar.py" in juego.ultima_accion


def test_lineas_comparacion_desde_dataframe():
    pd = pytest.importorskip("pandas")
    tabla = pd.DataFrame({"exito_pct": [90.0, 90.0]}, index=["hibrido", "sin_rna"])
    lineas = ui.lineas_comparacion(tabla)
    assert any("hibrido" in linea for linea in lineas)
    assert ui.lineas_comparacion(None) == []


def test_texto_estado_con_y_sin_partida():
    juego = ui.Juego(lambda s: FakePartida(s), semilla=4)
    lineas = ui.texto_estado(juego)
    assert lineas[0].startswith("Semilla 4 | Estado: EXPLORACION")
    juego.partida = None
    assert ui.texto_estado(juego) == ["Sin partida activa. Pulsa R para crear una."]


def test_construir_vista_no_muta_la_partida():
    juego = ui.Juego(lambda s: FakePartida(s))
    antes = list(juego.partida.llamadas)
    vista = ui.construir_vista(juego)
    assert vista["objetivo"] == (18, 1)
    assert vista["rover"] == (19, 0)
    assert juego.partida.llamadas == antes


# ---------------------------------------------------------------- ventana (dummy)

def test_ventana_se_crea_y_cierra_sin_error():
    juego_salida = ui.ejecutar(lambda s: FakePartida(s), semilla=2, max_cuadros=3)
    assert juego_salida is None
    assert not pygame.get_init()


def test_dibujo_completo_con_vista_real():
    pygame.init()
    try:
        superficie = pygame.Surface((ui.ANCHO, ui.ALTO))
        fuentes = {"cuerpo": pygame.font.Font(None, 20), "titulo": pygame.font.Font(None, 24)}
        juego = ui.Juego(lambda s: FakePartida(s))
        juego.despachar("sugerencia")
        ui.dibujar_todo(superficie, fuentes, ui.construir_vista(juego))
        juego.partida = None
        ui.dibujar_todo(superficie, fuentes, ui.construir_vista(juego))
    finally:
        pygame.quit()
