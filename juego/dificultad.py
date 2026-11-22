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


# ---------- R23 (AG): el problema de planificación de la partida jugable ----------
# Sitios científicos de la partida jugable (mapa pequeño 20x30); mediano +1, grande +2, con tope de 12.
SITIOS_POR_NIVEL = {1: 8, 2: 8, 3: 9, 4: 10, 5: 11}
SITIOS_MAXIMO = 12
# Bases de recarga del mapa pequeño por nivel; los mapas mayores multiplican por la raíz de la razón de áreas (mín. 1).
BASES_POR_NIVEL = {1: 4, 2: 4, 3: 3, 4: 3, 5: 3}
# Ventanas de tiempo por nivel: (fracción de sitios con ventana, ancho mínimo, ancho máximo) en pasos por cada lado de la
# llegada de un recorrido de referencia (aleatorio mejorado con tres 2-opt; el AG puede encontrar uno mejor). Más difícil = más
# sitios con ventana y más estrechas. Supuestos de simulación.
VENTANAS_POR_NIVEL = {1: (0.5, 26, 40), 2: (0.6, 22, 36), 3: (0.7, 18, 30), 4: (0.8, 14, 26), 5: (0.8, 12, 22)}
# Fracción de los sitios (los de menor valor) que son opcionales: se pueden sacrificar si no caben.
FRACCION_OPCIONALES = 0.25


def n_sitios(nivel: int, filas: int, columnas: int) -> int:
    """Sitios científicos de la partida jugable según el nivel y el tamaño del mapa."""
    area = (int(filas) * int(columnas)) / (20 * 30)
    extra = 0 if area <= 1.0 else (1 if area <= 2.5 else 2)
    return int(min(SITIOS_MAXIMO, SITIOS_POR_NIVEL[nivel] + extra))


def n_bases(nivel: int, filas: int, columnas: int) -> int:
    """Bases de recarga de la partida jugable (sube con la raíz del área del mapa)."""
    area = (int(filas) * int(columnas)) / (20 * 30)
    return max(1, int(round(BASES_POR_NIVEL[nivel] * area ** 0.5)))
