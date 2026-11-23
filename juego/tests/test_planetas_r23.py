"""R23: mecánicas por planeta, dificultad de la partida jugable, recarga con sentido, temperatura de los gigantes,
batería del difuso en porcentaje y registro de la IA en los modos sueltos."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego import dificultad, planetas, termico  # noqa: E402
from juego.partida import Partida, bateria_por_defecto  # noqa: E402


def _mec(planeta, activa=True, intensidad=1.0, semilla=5):
    p = Partida(semilla=semilla, nivel=1, filas=20, columnas=30, garantia=False)
    return planetas.MecanicasPlaneta(planeta, p.mundo, semilla, intensidad, activa), p.mundo


# ---------- perfiles ----------
def test_cada_planeta_tiene_perfil_distinto():
    from simulador import PERFILES
    assert set(planetas.PERFILES) == set(PERFILES)
    huellas = {tuple((k, v) for k, v in planetas.parametros(n).items() if k not in ("nombre", "resumen")) for n in planetas.PERFILES}
    assert len(huellas) == len(planetas.PERFILES)
    assert planetas.perfil("Neptuno").viento > planetas.perfil("Marte").viento
    assert planetas.perfil("Neptuno").hielo_fraccion > 0.2 and planetas.perfil("Mercurio").hielo_fraccion == 0
    assert planetas.perfil("Marte").gravedad_g < planetas.perfil("Tierra").gravedad_g


def test_contrato_parametros_planeta():
    p = Partida(semilla=7, nivel=3, filas=20, columnas=30, planeta="Neptuno")
    d = p.parametros_planeta()
    for clave in ("nombre", "gravedad_g", "viento", "rumbo_viento", "rafaga_prob", "hielo_fraccion", "fragilidad_hielo",
                  "factor_pendiente", "arrastre", "intensidad", "activa", "sobrecosto_medio"):
        assert clave in d
    assert d["nombre"] == "Neptuno" and d["activa"] is True and d["intensidad"] == dificultad.INTENSIDAD_POR_NIVEL[3]
    d["viento"] = 0                                             # es una copia: no altera el perfil
    assert planetas.perfil("Neptuno").viento == 0.85


# ---------- gravedad ----------
def test_gravedad_encarece_el_paso_y_la_subida():
    marte, mundo = _mec("Marte")
    tierra, _ = _mec("Tierra")
    marte.perfil = planetas.PerfilPlaneta(**{**marte.perfil.como_dict(), "viento": 0.0})
    tierra.perfil = planetas.PerfilPlaneta(**{**tierra.perfil.como_dict(), "viento": 0.0})
    tierra.mundo = mundo                                           # el mismo relieve para los dos
    mundo.elevacion[:] = 0.0
    mundo.elevacion[5, 6] = 1.0
    plano_m = marte.costo_extra((5, 4), (5, 5), 0.5)["total"]
    plano_t = tierra.costo_extra((5, 4), (5, 5), 0.5)["total"]
    assert plano_m == 0.0 and plano_t > 0.0                       # Marte es la referencia del coste base
    subida = tierra.costo_extra((5, 5), (5, 6), 0.5)["total"]
    bajada = tierra.costo_extra((5, 6), (5, 5), 0.5)["total"]
    assert subida > plano_t and bajada == plano_t                 # subir cuesta más; bajar no cuesta más


def test_extra_por_paso_tiene_tope():
    jup, mundo = _mec("Júpiter", intensidad=5.0)
    mundo.elevacion[:] = 0.0
    mundo.elevacion[5, 6] = 3.0
    assert jup.costo_extra((5, 5), (5, 6), 1.0)["total"] <= planetas.EXTRA_MAXIMO_PASO


# ---------- viento ----------
def test_viento_de_cara_cuesta_mas_que_de_cola_y_la_rafaga_lo_duplica():
    nep, mundo = _mec("Neptuno")
    mundo.elevacion[:] = 0.0
    # Neptuno sopla hacia el SO: avanzar al SO es de cola, al NE es de cara
    cola = nep.costo_extra((5, 5), (6, 4), 0.5)["viento"]
    cara = nep.costo_extra((5, 5), (4, 6), 0.5)["viento"]
    assert cola < 0 < cara
    nep.rafaga_restante = 4
    assert nep.costo_extra((5, 5), (4, 6), 0.5)["viento"] == pytest.approx(cara * planetas.RAFAGA_MULT)
    # a más velocidad, el viento de cara cuesta más
    assert nep.costo_extra((5, 5), (4, 6), 1.0)["viento"] > cara


def test_viento_de_costado_desvia_al_rover(monkeypatch):
    nep, mundo = _mec("Neptuno", intensidad=3.0)
    monkeypatch.setattr(planetas, "P_DESVIO_VIENTO", 5.0)         # desvío seguro con la intensidad alta
    nep.hielo[:] = False
    # viento al SO; avanzar al NO es de costado
    destino = (5, 4)
    resultados = [nep.perturbar((6, 5), destino, 0.5, lambda c: True) for _ in range(30)]
    desviados = [(f, m) for f, m in resultados if m == "D-VIENTO"]
    assert len(desviados) >= 20                                   # con probabilidad 0,9, casi siempre
    assert all(max(abs(f[0] - destino[0]), abs(f[1] - destino[1])) == 1 and f != destino for f, _ in desviados)
    assert nep.desvios_viento == len(desviados)


def test_las_rafagas_empiezan_y_terminan():
    nep, _ = _mec("Neptuno", intensidad=5.0)
    vistas = []
    for _ in range(300):
        nep.avanzar_clima()
        vistas.append(nep.rafaga_restante > 0)
    assert any(vistas) and not all(vistas)


# ---------- hielo ----------
def test_hielo_parches_segun_el_perfil():
    nep, mundo = _mec("Neptuno")
    mer, _ = _mec("Mercurio")
    libres = int((mundo.tipo == 0).sum())
    assert 0.2 * libres < nep.hielo.sum() < 0.5 * libres
    assert mer.hielo.sum() == 0
    assert not nep.hielo[tuple(mundo.refugio)] and not nep.hielo[tuple(mundo.inicio)]
    assert np.all(mundo.tipo[nep.hielo] == 0)                     # solo sobre celdas libres


def test_hielo_resbala_rapido_y_no_despacio(monkeypatch):
    nep, mundo = _mec("Neptuno", intensidad=3.0)
    monkeypatch.setattr(planetas, "P_DESVIO_VIENTO", 0.0)
    nep.hielo[:] = False
    nep.hielo[5, 5] = True
    rapido, motivo = nep.perturbar((5, 4), (5, 5), 1.0, lambda c: True)
    assert motivo == "D-HIELO" and rapido == (5, 6)               # se desliza una celda más en su rumbo
    lento, motivo = nep.perturbar((5, 4), (5, 5), 0.2, lambda c: True)
    assert motivo is None and lento == (5, 5)                      # despacio no resbala
    sin_hueco, motivo = nep.perturbar((5, 4), (5, 5), 1.0, lambda c: False)
    assert motivo == "D-HIELO" and sin_hueco == (5, 5)             # sin hueco, se queda


def test_resbalon_en_partida_gasta_bateria_y_deja_la_ruta_coherente():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, planeta="Neptuno", eventos_activos=())
    for _ in range(40):
        if p.estado in ("EXITO", "FRACASO", "SIN_RUTA"):
            break
        p.avanzar_ia()
        ruta = p.mision.ruta
        if len(ruta) > 1:
            assert tuple(ruta[0]) == tuple(p.rover.posicion)
    est = p.mecanicas.estado()
    assert est["energia_extra"] > 0 and est["resbalones_hielo"] + est["desvios_viento"] > 0


def test_el_difuso_frena_ante_el_hielo():
    p = Partida(semilla=11, nivel=3, filas=20, columnas=30, planeta="Neptuno", eventos_activos=())
    siguiente = tuple(p.mision.ruta[1])
    p.mecanicas.hielo[:] = False
    sin = p._inclinacion_con_hielo(5.0)
    p.mecanicas.hielo[siguiente] = True
    con = p._inclinacion_con_hielo(5.0)
    assert sin == 5.0 and con == 5.0 + planetas.HIELO_EQUIV_GRADOS
    v_sin = p.mision.difuso.inferir(20.0, 80.0, sin).velocidad
    v_con = p.mision.difuso.inferir(20.0, 80.0, con).velocidad
    assert v_con < v_sin


# ---------- el congelado no cambia ----------
def test_evaluacion_congelada_sin_mecanicas_ni_cambios():
    p = Partida(semilla=11, nivel=5, filas=20, columnas=30, garantia=False, planeta="Neptuno")
    assert p.mecanicas.activa is False and p.fisica_velocidad is False
    assert p.mecanicas.costo_extra((1, 1), (1, 2), 1.0)["total"] == 0.0
    assert p.rover.bateria == 100.0 - 4.0 * 4                      # la curva de batería de siempre
    assert "inferir" not in vars(p.mision.difuso)                  # el difuso sin envoltorio (batería en unidades del motor)
    assert bateria_por_defecto(5, 20, 30, garantia=False) == 84.0


# ---------- dificultad ----------
def test_dificultad_sube_con_el_nivel():
    b = [dificultad.BATERIA_POR_NIVEL[n] for n in range(1, 6)]
    i = [dificultad.INTENSIDAD_POR_NIVEL[n] for n in range(1, 6)]
    assert b == sorted(b, reverse=True) and i == sorted(i)
    assert bateria_por_defecto(5, 20, 30) == dificultad.BATERIA_POR_NIVEL[5]
    assert Partida(semilla=3, nivel=5, filas=20, columnas=30).rover.bateria == dificultad.BATERIA_POR_NIVEL[5]


def test_la_garantia_ya_no_promete_ganar_siempre():
    """La garantía es «existe una ruta ganadora» (con bases y sobrecoste medio), no «se gana siempre»: con las mecánicas
    activas el coste real puede superar al previsto y la partida puede perderse por batería."""
    p = Partida(semilla=3, nivel=5, filas=20, columnas=30, planeta="Neptuno", eventos_activos=())
    assert p.mecanicas.activa and p.parametros_planeta()["sobrecosto_medio"] > 0
    assert p.mision.factor_ambiente > 1.0


# ---------- recarga ----------
def _en_base(p, bateria):
    base = tuple(p.estaciones[0])
    p.rover.posicion = base
    p.rover.bateria = bateria
    p._ultima_estacion = None
    p.mision.objetivos = []
    p.mision.ruta = [base]
    return base


def test_no_se_recarga_con_bateria_alta_y_poca_ruta_por_delante():
    p = Partida(semilla=4, nivel=1, filas=20, columnas=30, eventos_activos=())
    _en_base(p, 0.79 * p.capacidad_bateria)
    p.mision.visitados = set(p.mundo.sitios)                       # sitios hechos: solo queda ir al refugio
    p.rover.bateria = 0.85 * p.capacidad_bateria                   # bajo el 90 % (antes recargaba), pero sobra para el refugio
    assert p._coste_restante() * p.factor_desvio + 15 < p.rover.bateria
    p._tras_paso_estacion()
    assert p._recargando == 0                                      # antes: 3 pasos de recarga aunque casi llena


def test_se_recarga_si_la_bateria_no_alcanza_para_lo_que_queda():
    p = Partida(semilla=4, nivel=1, filas=20, columnas=30, eventos_activos=())
    _en_base(p, 0.20 * p.capacidad_bateria)
    p._tras_paso_estacion()
    assert p._recargando > 0
    assert p._conviene_recargar() is True


def test_la_recarga_parcial_no_pasa_de_lo_necesario_y_nunca_baja_la_bateria():
    p = Partida(semilla=4, nivel=1, filas=20, columnas=30, eventos_activos=())
    _en_base(p, 0.20 * p.capacidad_bateria)
    antes = p.rover.bateria
    p._tras_paso_estacion()
    for _ in range(3):
        p._paso_recarga()
    assert p._recargando == 0 and antes < p.rover.bateria <= p.bateria_max
    assert p.recargas_hechas == 1


def test_recarga_sin_usar_en_partida_larga_marte_no_hay_pasos_con_bateria_alta():
    """Reproduce el reporte (Marte, automático): ningún paso «recargar» con la batería sobre el 70 % de la capacidad."""
    for semilla in (1, 2, 3):
        p = Partida(semilla=semilla, nivel=1, filas=20, columnas=30, planeta="Marte")
        for _ in range(120):
            if p.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
                break
            p.avanzar_ia()
        for fila in p.mision.log.filas:
            if fila.get("accion") == "recargar":
                assert fila["bateria"] < 0.70 * p.capacidad_bateria


# ---------- temperatura ----------
@pytest.mark.parametrize("planeta", ["Júpiter", "Saturno", "Urano", "Neptuno"])
def test_los_gigantes_tienen_modelo_termico_y_la_temperatura_se_mueve(planeta):
    p = Partida(semilla=11, planeta=planeta)
    assert p.termico.activo
    serie = []
    for _ in range(8):
        p.avanzar_ia()
        serie.append(round(p.t_int, 4))
    assert serie[0] < termico.T_INT_INICIAL and serie == sorted(serie, reverse=True)
    assert len(set(serie)) == len(serie)                           # cambia en cada paso, no queda fija en 20 °C


def test_temperatura_tiende_al_equilibrio_frio():
    t = termico.Termico("Neptuno")
    for _ in range(600):
        t.paso(sombra=True)
    assert t.t_int == pytest.approx(t.t_equilibrio_frio, abs=0.1)
    assert termico.TOLERANCIA_FRIA < t.t_equilibrio_frio < termico.T_INT_INICIAL


def test_planetas_calientes_no_cambian():
    t = termico.Termico("Venus")
    for _ in range(10):
        t.paso(sombra=False)
    assert t.t_int > termico.T_INT_INICIAL


# ---------- batería del difuso ----------
def test_el_difuso_recibe_la_bateria_en_porcentaje_en_el_mapa_grande():
    p = Partida(semilla=3, nivel=2, filas=40, columnas=60, planeta="Marte", eventos_activos=())
    assert p.capacidad_bateria > 100
    p.avanzar_ia()
    visto = p._entrada_difuso["bateria"]
    assert 0 <= visto <= 100
    assert visto == pytest.approx(100.0 * p.rover.bateria / p.capacidad_bateria, abs=3.0)
    ui = p.mision.ultima_ia
    assert ui["difuso"]["bateria_pct"] == pytest.approx(visto)     # /ia/paso muestra lo que el difuso recibió (en %)
    assert ui["difuso"]["bateria"] > 100                           # y la batería en unidades del motor aparte


def test_el_laboratorio_del_difuso_no_convierte_la_bateria():
    # R23: sin los parámetros evolucionados del planeta (con ellos el difuso de Marte ya no es el de defecto)
    p = Partida(semilla=3, nivel=2, filas=40, columnas=60, planeta="Marte", eventos_activos=(), difuso_evolucionado=False)
    a = p.mision.difuso.inferir(20.0, 80.0, 5.0)
    from difuso import FuzzyController
    b = FuzzyController().inferir(20.0, 80.0, 5.0)
    assert a.velocidad == pytest.approx(b.velocidad)


# ---------- ultima_ia en los modos sueltos ----------
@pytest.mark.parametrize("modo", ["rna", "difuso", "ag"])
def test_los_modos_sueltos_guardan_ultima_ia(modo):
    p = Partida(semilla=3, nivel=1, filas=20, columnas=30, planeta="Marte", eventos_activos=())
    p.modo_ia = modo
    for _ in range(4):
        p.avanzar_modo(modo)
    u = p.mision.ultima_ia
    assert u is not None and u["paso"] == p.mision.paso
    assert u["usar_rna"] is (modo == "rna") and u["usar_difuso"] is (modo == "difuso")
    assert set(u["probabilidades"]) and len(u["celda"]) == 2
    if modo == "difuso":
        assert 0 <= u["difuso"]["bateria"] <= 100
