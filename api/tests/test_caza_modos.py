"""ARX-75 / N12: en Medio, con sitios hechos y un dron obligatorio vivo, rna sale a cazarlo en vez de fracasar."""
from juego.combate import Combate
from juego.partida import Partida


def test_medio_rna_llega_al_refugio_con_dron_vivo_y_sale_a_cazarlo():
    p = Partida(semilla=11, nivel=3, filas=20, columnas=30)
    p.combate = Combate(mundo=p.mundo, rover=p.rover, semilla=11)
    p.modo_ia = "rna"
    p.mision.visitados = set(p.mundo.sitios)
    p.rover.posicion = p.mundo.refugio
    p.mision.estado = "EXITO"
    p._revisar_victoria()
    assert p.estado != "FRACASO", p.avisos[-1:]
    assert p.mision.objetivos and tuple(int(v) for v in p.mision.objetivos[0]) in [
        tuple(int(v) for v in d.pos) for d in p.combate.drones if d.vivo]
    posicion_antes = tuple(int(v) for v in p.rover.posicion)
    p.avanzar_modo("rna", veto=True)
    assert tuple(int(v) for v in p.rover.posicion) != posicion_antes
    assert p.estado != "FRACASO", p.avisos[-1:]
