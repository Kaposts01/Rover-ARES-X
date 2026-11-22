"""R23 (correcciones tras el QA final): bucle de replanteo parado sobre una base de recarga (partidas completas por la API, con drones)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import planificacion  # noqa: E402
from api.servidor import crear_app  # noqa: E402
from integracion import ESTADOS_TERMINALES  # noqa: E402
from juego import partida as jp  # noqa: E402


def _partida_auto(semilla, nivel):
    app = crear_app()
    cli = TestClient(app)
    assert cli.post("/partida", json={"semilla": semilla, "nivel": nivel, "tamano": "pequeno", "planeta": "Marte", "modo": "rover"}).status_code == 200
    cli.post("/modo", json={"modo": "automatico"})
    return cli, app.state.sesion.partida


@pytest.mark.parametrize("semilla,nivel", [(5, 4), (4, 3)])
def test_la_partida_no_se_queda_replanteando_parada_en_una_base(semilla, nivel):
    """Regresión QA: nivel 4 semilla 5 (269 replanteos parado en la base (18,4), fracaso con 0 de 10 sitios) y nivel 3 semilla 4 (247
    replanteos, batería de 100 % a 12,5 %). Causas: el refugio quedaba encerrado en el mapa estimado por lecturas falsas (el plan,
    infactible, mandaba a la base donde ya estaba) y la reserva de caza de drones hacía infactible el plan con la batería llena."""
    cli, p = _partida_auto(semilla, nivel)
    racha = maxima = pasos = 0
    while pasos < 500 and p.estado not in ESTADOS_TERMINALES:
        previa = tuple(p.rover.posicion)
        cli.post("/paso")
        pasos += 1
        quieto = tuple(p.rover.posicion) == previa and p._recargando == 0 and p._falla_restante == 0
        racha = racha + 1 if quieto else 0
        maxima = max(maxima, racha)
    assert p.estado in ESTADOS_TERMINALES, (p.estado, pasos)      # terminó: ni parada ni en bucle (con la batería de N4 recalibrada, 5-4 puede perder)
    if (semilla, nivel) == (4, 3):
        assert p.estado == "EXITO"
    assert maxima <= jp.PASOS_QUIETO_MAXIMO, f"{maxima} pasos seguidos sin moverse"
    assert pasos < 500


def test_un_plan_infactible_con_la_bateria_llena_se_degrada_en_vez_de_quedarse_parado():
    """Nivel 4 semilla 5, paso 16: en la base (18,4) con la batería llena el plan completo no cabe (gasto real de 1,5 por paso y reserva de
    caza de 2 drones). El plan degradado visita lo alcanzable y vuelve al refugio, con movimiento."""
    cli, p = _partida_auto(5, 4)
    for _ in range(16):
        cli.post("/paso")
    pendientes = {c: v for c, v in p.mundo.sitios.items() if c not in p.mision.visitados}
    origen = tuple(int(v) for v in p.rover.posicion)
    completo = p._problema_plan(origen, pendientes)
    assert not planificacion.AGRestringido(completo, poblacion=40, generaciones=30, semilla=1).optimizar().mejor.factible
    deg = p._plan_degradado(origen, pendientes)
    assert deg is not None
    ruta, plan, etapa = deg
    assert len(ruta) > 1 and plan.factible and 0 <= etapa < len(jp.ETAPAS_DEGRADADO)
