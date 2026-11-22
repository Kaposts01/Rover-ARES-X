"""R23: dificultad de la partida jugable (garantia=True) por nivel.

Antes los niveles solo cambiaban un poco la batería inicial (100 − 4·(nivel − 1)) y el número de peligros; el evaluador ganó
Hardcore 3 de 3 con 32 a 58 % de batería sobrante. Ahora cada nivel fija, además de la batería, la intensidad de las
mecánicas del planeta (gravedad, viento, hielo; `juego/planetas.py`) y el ruido de los sensores. La dificultad sale de
cosas que la IA maneja mejor o peor (ahorrar batería con un orden de visita corto, frenar sobre el hielo, descartar
peligros con sensores ruidosos), no de azar puro.

Todos los valores son supuestos de simulación calibrados con `scripts/medir_dificultad.py` (ver docs/planes/R23_dificultad.md).
Solo valen para la partida jugable: la evaluación congelada sigue con la batería de siempre.
"""

# Batería inicial del mapa pequeño (20x30), por nivel; el mapa grande la multiplica por RAZON_BATERIA_GRANDE.
BATERIA_POR_NIVEL = {1: 100.0, 2: 94.0, 3: 88.0, 4: 80.0, 5: 70.0}
# Escala de todas las mecánicas del planeta (1,0 = el perfil tal cual).
INTENSIDAD_POR_NIVEL = {1: 0.4, 2: 0.6, 3: 0.75, 4: 0.9, 5: 1.1}
# Ruido de los sensores (σ relativo; 0,1 es el nominal con que se entrenó la RNA).
RUIDO_POR_NIVEL = {1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1}
# Fracción del sobrecoste medio del planeta que la garantía da por supuesta (0 = ignora el planeta).
GARANTIA_FRACCION_SOBRECOSTO = 0.5
# True: la garantía cuenta con las bases de recarga y el sobrecoste del planeta (R23). False: la comprobación de antes (ruta completa
# sin recargar, sin planeta); la usan las pruebas que necesitan los mapas anteriores.
GARANTIA_CON_BASES_Y_PLANETA = True
# Pasos de referencia de una partida pequeña: la batería del nivel se compensa por lo que cuesta de más el planeta frente a Marte
# (la calibración del nivel se hizo en Marte), para que un planeta cambie el TIPO de reto y no solo lo haga más largo.
PASOS_REFERENCIA = 70


def bateria_inicial(nivel: int, planeta: str = "Marte") -> float:
    """Batería inicial de la partida jugable pequeña: la del nivel más la compensación del sobrecoste medio del planeta."""
    from juego import planetas
    extra = planetas.sobrecosto_medio(planeta, INTENSIDAD_POR_NIVEL[nivel]) - planetas.sobrecosto_medio("Marte", INTENSIDAD_POR_NIVEL[nivel])
    return float(round(BATERIA_POR_NIVEL[nivel] + max(0.0, extra) * PASOS_REFERENCIA, 1))


def parametros(nivel: int) -> dict:
    return {"nivel": int(nivel), "bateria": BATERIA_POR_NIVEL[nivel], "intensidad": INTENSIDAD_POR_NIVEL[nivel],
            "ruido": RUIDO_POR_NIVEL[nivel]}
