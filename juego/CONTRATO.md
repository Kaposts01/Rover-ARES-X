# ARES-X · Juego interactivo del rover · Contrato de coordinación

Coordinador: Claude (sesión principal). Decisiones aprobadas: ev3-d12 (pygame), ev3-d13 (2 a 3 días),
ev3-d14 a ev3-d22 (objetivo: entender las decisiones de la IA; misión única en Marte; el jugador conduce
y la IA sugiere; eventos barranco, falla de sensor y batería baja; paneles laterales; solo Marte;
botón de comparación con 20 semillas; CSV y JSON por partida; código, instrucciones y video).

## Reglas de coordinación

1. **Módulos congelados:** `simulador.py`, `rna.py`, `difuso.py`, `genetico.py` y `integracion.py` NO se modifican
   (ev3-d08). El juego los importa tal cual. Si algo falta, se resuelve en `juego/` sin tocarlos.
2. **Propiedad de archivos:** cada agente escribe SOLO en sus archivos. Nadie edita archivos de otro agente.
3. **Preguntas al usuario:** no se preguntan en el chat; se cargan como fichas en la Bandeja (proyecto "Trabajo", orden desde 3023).
4. **Pruebas:** cada agente entrega sus pruebas en `juego/tests/` y las corre antes de reportar.
   Sin pruebas en verde no hay entrega.
5. **Reporte:** cada agente responde con: archivos creados, pruebas ejecutadas con su resultado real,
   lo que no pudo verificar, y dependencias pendientes.

## Mapa de agentes

| Agente | Archivos que escribe | Depende de | Fase |
|---|---|---|---|
| A · Motor de partida | `juego/partida.py` | módulos congelados | 1 |
| B · Interfaz pygame | `juego/ui.py`, `juego/main.py` | `juego/partida.py` (contrato abajo) | 2 |
| C · Exportación y experimento | `juego/exportar.py`, `juego/experimento.py` | `juego/partida.py` (contrato abajo) | 2 |
| D · Guion del video | `juego/GUION_VIDEO.md` | ninguno (lee el código existente) | 1 |
| E · Pruebas del juego | `juego/tests/test_partida.py`, `juego/tests/test_exportar.py` | `juego/partida.py`, `juego/exportar.py` | 3 |

El coordinador integra, corre todas las pruebas y revisa `juego/README.md` al final.

## Contrato de `juego/partida.py` (agente A implementa; B, C y E lo usan tal cual)

```python
class Partida:
    def __init__(self, semilla: int = 11, bateria: float = 100.0,
                 eventos_activos=("barranco", "falla_sensor", "bateria_baja")):
        """Crea un mapa de Marte con generar_mundo(semilla) y el rover en el inicio.
        Usa Mision internamente (integracion.py), sin cambiar su comportamiento."""

    # Atributos de lectura
    mundo          # World
    rover          # Rover (posicion, bateria, rumbo)
    estado         # str: "EXPLORACION", "ALERTA", "EXITO", "FRACASO", "MODO_SEGURO", "SIN_RUTA"
    ruta           # list de celdas (tuplas) de la ruta planeada

    def sugerencia(self) -> dict:
        """Lo que la IA recomienda en ESTE paso, sin ejecutarlo. Claves:
        {"rumbo": "N"|"S"|"E"|"O"|None,
         "accion": "avanzar"|"detener"|"replanificar"|"modo_seguro",
         "velocidad": float en [0,1],
         "p_barranco": float, "p_obstaculo": float, "p_libre": float,
         "reglas": [(id, fuerza, motivo), ...],
         "desglose": {"fitness": float, "ciencia": float, "distancia": float,
                      "energia": float, "riesgo": float, "tiempo": float, "penalizacion": float} | None,
         "motivos": [codigos V-... o D-... o OK]}"""

    def avanzar_ia(self) -> dict:
        """Ejecuta un paso del pseudociclo con la IA. Devuelve la misma forma que sugerencia()
        más {"posicion": (f, c), "bateria": float, "estado": str}."""

    def mover_jugador(self, rumbo: str) -> dict:
        """El jugador intenta moverse una celda en rumbo ("N","S","E","O").
        Usa paso_fisico. Devuelve {"movido": bool, "motivo": str, "posicion": (f, c),
        "bateria": float, "estado": str}. Un barranco o un obstáculo real BLOQUEA el movimiento
        (no es un error). Gasta batería solo si se mueve."""

    def disparar_evento(self, nombre: str) -> dict:
        """nombre en {"barranco", "falla_sensor", "bateria_baja"}. Devuelve {"ok": bool, "detalle": str}.
        - barranco: marca una celda libre adyacente al rover como BARRANCO (nunca inicio ni refugio).
        - falla_sensor: activa prob_fallo=1.0 en el sensor durante 3 pasos.
        - bateria_baja: fija la batería del rover en 15.0.
        Un evento no soportado devuelve ok=False."""

    def bitacora(self):
        """pandas.DataFrame con una fila por paso (columnas de MissionLogger)."""

    def resumen(self) -> dict:
        """Mismas claves que Mision.resumen()."""
```

Notas de implementación para A:
- `sugerencia()` NO avanza el estado. Debe ser idempotente: llamarla dos veces da lo mismo.
  Calcúlala con los mismos pasos del pseudociclo de `Mision.paso_mision`, sin mutar el mundo ni el rover.
  Si esto no es posible sin tocar `integracion.py`, `sugerencia()` puede copiar la lógica de observación en `partida.py`.
- `desglose` viene de `GeneticPlanner.evaluar` sobre la ruta actual; `None` si no hay ruta.
- `avanzar_ia()` usa `Mision.paso_mision()`.

## Contrato de `juego/exportar.py` (agente C implementa)

```python
def exportar_partida(partida, carpeta: str) -> tuple[str, str]:
    """Escribe <carpeta>/partida_<semilla>_<hora>.csv (bitácora) y .json (configuración + resumen).
    Devuelve las dos rutas. Crea la carpeta si no existe. Nunca sobrescribe."""
```

## Contrato de `juego/experimento.py` (agente C implementa)

```python
def comparar_variantes(semillas=range(20)) -> "pandas.DataFrame":
    """Corre híbrido, sin RNA y sin difuso con las mismas semillas (Mision directo, sin UI).
    Devuelve la tabla de resumen del notebook: exito_pct, colisiones, barrancos_pisados,
    sitios_media, pasos_mediana, pasos_desv, bateria_media por variante."""
```

## Interfaz de `juego/ui.py` y `juego/main.py` (agente B implementa)

- Ventana pygame de 1280x720. Mapa a la izquierda; paneles a la derecha (ev3-d18): RNA (probabilidades),
  difuso (velocidad y reglas activadas), AG (desglose del fitness) y supervisor (motivos).
- Teclado: flechas o WASD = el jugador intenta moverse (`mover_jugador`); ESPACIO = que la IA avance un paso
  (`avanzar_ia`); TAB = mostrar/ocultar la sugerencia de la IA (ev3-d16: la IA sugiere, el jugador decide);
  B = barranco, F = falla de sensor, E = batería baja (ev3-d17); R = nueva partida (semilla nueva); C = comparar con 20 semillas (ev3-d20); X = exportar CSV y JSON (ev3-d21); ESC = salir.
- Dibujo: celdas por tipo (libre, obstáculo, barranco, refugio, sitio científico), rover, ruta planeada,
  y la celda que la IA quiere alcanzar. Texto de estado y de la última acción.
- `main.py` solo arranca la ventana: `python juego/main.py`.

## Entregables y criterios de aceptación

1. `juego/partida.py`: todas las funciones del contrato; pruebas de E en verde.
2. `juego/ui.py` y `juego/main.py`: la ventana abre, responde a todas las teclas listadas y no se cae al
   pulsar ninguna de ellas, con partida en EXITO, FRACASO o SIN_RUTA.
3. `juego/exportar.py` y `juego/experimento.py`: archivos CSV y JSON válidos; la tabla de comparación
   reproduce los resultados del notebook (90 % de éxito en híbrido y sin RNA sobre 20 semillas).
4. `juego/GUION_VIDEO.md`: guion de 6 a 8 minutos que cubre cada función del juego y cada tema estudiado
   (ver ev3-d22: el estudiante graba, el guion lo prepara el agente).
5. `juego/README.md`: instalación (`pip install pygame-ce numpy pandas scikit-learn matplotlib`), cómo
   ejecutar el juego y las pruebas, y los supuestos de simulación.
6. `python -m pytest -q juego/tests tests`: todo en verde. Los 45 de `tests/` no deben romperse.
