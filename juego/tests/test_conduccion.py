"""Pruebas de la conducción por modo (ARX-11): rna, difuso y ag conducen solos, con o sin veto."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from juego.conduccion import correr  # noqa: E402
from juego.partida import Partida  # noqa: E402


def trayectoria(modo: str, veto: bool = True, semilla: int = 11, max_pasos: int = 400):
    p = Partida(semilla=semilla)
    t = [tuple(int(x) for x in p.rover.posicion)]
    for _ in range(max_pasos):
        if p.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
        if modo == "automatico":
            p.avanzar_ia()
        else:
            p.avanzar_modo(modo, veto)
        t.append(tuple(int(x) for x in p.rover.posicion))
    return t, p


@pytest.mark.parametrize("modo", ["rna", "difuso", "ag"])
def test_cada_modo_da_pasos_propios_distintos_al_automatico(modo):
    base, _ = trayectoria("automatico")
    propia, _ = trayectoria(modo)
    assert propia != base


@pytest.mark.parametrize("modo", ["rna", "difuso", "ag"])
def test_con_veto_encendido_no_hay_colisiones_en_semilla_11(modo):
    r = correr(11, modo, veto=True)
    assert r["colisiones"] == 0
    assert r["intentos_barranco"] == 0
    assert r["exito"]


@pytest.mark.parametrize("modo", ["rna", "difuso", "ag"])
def test_con_veto_apagado_nunca_aparece_motivo_de_veto(modo):
    p = Partida(semilla=11)
    motivos = []
    for _ in range(200):
        if p.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
        motivos += p.avanzar_modo(modo, veto=False)["motivos"]
    assert not any(m.startswith("V-SEGURIDAD") for m in motivos)


def test_un_modo_desconocido_no_se_acepta_en_la_conduccion():
    p = Partida(semilla=11)
    with pytest.raises(Exception):
        p.avanzar_modo("manual", veto=True)


def test_intervencion_del_difuso_cambia_la_trayectoria_en_modo_difuso():
    # ARX-18.2: la intervención de /intervencion (difuso) debe llegar al modo difuso, no solo al automático
    base, _ = trayectoria("difuso")
    p = Partida(semilla=11)
    p.mision.intervencion_difuso = 0.0
    t = [tuple(int(x) for x in p.rover.posicion)]
    for _ in range(400):
        if p.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
        p.avanzar_modo("difuso", True)
        t.append(tuple(int(x) for x in p.rover.posicion))
    assert t != base


def test_replanteo_del_modo_ag_vuelve_a_correr_el_algoritmo_genetico():
    # ARX-18.4: al replanificar en modo ag, el AG se re-ejecuta (no solo BFS)
    from juego import conduccion
    p = Partida(semilla=11)
    llamadas = []
    original = p.mision._optimizar_ag

    def espia(origen, pendientes):
        llamadas.append(dict(pendientes))
        return original(origen, pendientes)

    p.mision._optimizar_ag = espia
    conduccion._replanear_ag(p)
    assert len(llamadas) == 1
    assert p.mision.ruta and p.mision.ruta[0] == p.rover.posicion
    assert p.mision.objetivos[-1] == p.mundo.refugio
