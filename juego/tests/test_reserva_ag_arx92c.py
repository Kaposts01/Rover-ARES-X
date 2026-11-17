"""ARX-92c (corrección única, ev3-d74 y aprobación del Maestro): la viabilidad del AG usa la reserva de _planear.

Criterio (ARX-92_ag_decide.md §14): una ruta con largo + MARGEN_ENERGIA > batería no puede ganar a una ruta completa
viable. Si ninguna ruta completa cumple la reserva, el envoltorio cae al respaldo y lo anota (AG-FALLBACK-GARANTIA);
nunca deja pasar una ruta que _planear descartaría.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from integracion import MARGEN_ENERGIA  # noqa: E402
from juego import comparacion  # noqa: E402

# semillas del exigente de 10 sitios donde el AG crudo era completo y _planear lo descartaba (§13)
SEMILLAS_DESAJUSTE = (12, 16, 19)


@pytest.mark.parametrize("semilla", SEMILLAS_DESAJUSTE + (1,))
def test_la_ruta_planificada_cumple_la_reserva_o_se_anota_el_respaldo(semilla):
    p = comparacion.partida_variante(semilla, "hibrido", "exigente10")
    m = p.mision
    ruta = m.ruta
    if ruta:
        assert len(ruta) - 1 + MARGEN_ENERGIA <= m.rover.bateria or m._optimizar_ag.fallbacks
