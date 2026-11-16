# ARES-X · Contrato v2 del juego (mejoras aprobadas)

Decisiones aprobadas: ev3-d23 B, ev3-d24 A, ev3-d25 A, ev3-d26 A, ev3-d27 A, ev3-d28 A.
Reglas de coordinación de CONTRATO.md siguen vigentes. Los módulos congelados (simulador.py, rna.py,
difuso.py, genetico.py, integracion.py) NO se tocan. Todo cambio de reglas vive en juego/.

## Agente M · lógica de la partida (archivo: juego/partida.py y juego/tests/test_partida_v2.py)

1. **Niveles (ev3-d26).** `Partida(semilla, bateria=None, nivel=1)`. Nivel n in 1..5:
   - barrancos = 4 + n, obstáculos = 20 + 2*n, sitios = 3 si n<=2 else 4,
   - batería inicial = 100 - 4*(n-1) si `bateria` es None.
   Nivel fuera de 1..5 -> ValueError.
2. **Falla de sensor (ev3-d23 B).** `disparar_evento("falla_sensor")` NO usa el modo seguro. Activa
   `falla_restante = 3`. Mientras sea > 0, `avanzar_ia()` NO llama a paso_mision: devuelve
   accion="detener", motivos=["D-FALLA-SENSOR"], no mueve al rover, y decrementa falla_restante.
   Luego la falla termina y la IA continúa. Nunca lleva a MODO_SEGURO por este evento.
3. **Ambiente (ev3-d25).** Atributo `ambiente`: "normal", "tormenta" o "noche", y `ambiente_restante`.
   - Cada paso (avanzar_ia o mover_jugador que se mueve) hay 3% de probabilidad de iniciar una tormenta
     (6 pasos) o una noche (8 pasos), con rng propio sembrado por semilla. Una a la vez.
   - Efecto tormenta: cada paso consume 1 % extra de batería.
   - Efecto noche: cada paso consume 0.5 % extra de batería.
   - Evento manual nuevo `disparar_evento("tormenta")` y `disparar_evento("noche")` con la misma duración.
4. **Puntaje (ev3-d24).** `puntaje()` devuelve un entero:
   `round(100 * sitios_visitados / sitios_totales + 0.5 * bateria + (50 if vetos == 0 else 0))`.
   Sin sitios (sitios_totales == 0) la parte científica vale 0, nunca divide entre cero.
5. **Diagonales del jugador (ev3-d28).** `mover_jugador(rumbo)` acepta "N","S","E","O" y además
   "NE","NO","SE","SO". Diagonal: destino = (f±1, c±1), misma regla de transitable, cuesta 1 % de batería.
   `sugerencia()` y la IA siguen con cuatro direcciones.
6. **Objetivo fijado por el jugador (ev3-d27).** `fijar_objetivo(celda)`: la IA planea la ruta hacia
   esa celda (BFS sobre el mapa estimado) y la sigue con avanzar_ia(). Devuelve {"ok": bool, "detalle": str};
   celda no transitable o sin camino -> ok=False. `fijar_objetivo(None)` vuelve al plan normal.
   Si el objetivo se alcanza, se limpia y la IA vuelve al plan normal.
7. **Mantener del contrato v1:** sugerencia() idempotente; mover_jugador y disparar_evento devuelven
   sus mismas claves; resumen() y bitacora() sin cambios de forma (se pueden agregar claves).

Pruebas del agente M: falla_sensor detiene 3 pasos y no termina la partida; tormenta/noche consumen batería
extra; puntaje sin división por cero; diagonal válida y bloqueada; fijar_objetivo ok y error; niveles 1..5 y
nivel inválido. Ejecutar: cd ares_x && python -m pytest -q juego/tests tests -p no:warnings.

## Agente I · interfaz (archivos: juego/ui.py, juego/efectos.py y juego/tests/test_ui_v2.py)

1. **Movimiento diagonal:** teclas Numpad 7 (NO), Numpad 9 (NE), Numpad 1 (SO), Numpad 3 (SE).
   Llaman mover_jugador con el rumbo correspondiente.
2. **Clic para fijar objetivo (ev3-d27):** clic izquierdo en una celda del mapa -> partida.fijar_objetivo(celda).
   Clic derecho -> fijar_objetivo(None). El resultado aparece en la línea de última acción.
3. **Nivel:** ENTER pasa al siguiente nivel cuando el estado es EXITO (máx. 5); R reinicia el nivel actual
   con semilla nueva. Muestra "Nivel n/5".
4. **Puntaje y récord:** panel nuevo "Misión" con nivel, puntaje actual, batería, ambiente restante y
   objetivo fijado. El récord de la sesión (máximo puntaje de la sesión) se muestra debajo.
5. **Eventos visibles (ev3-d25 y ev3-d23):** tormenta y noche con título grande (usar efectos.py: añadir
   "tormenta" y "noche" a CATALOGO) y tinte de pantalla mientras dure el ambiente (ocre para tormenta,
   azul oscuro para noche). Falla de sensor: título y las celdas del mapa "parpadean" 3 pasos.
6. **Mantener:** TAB, B, F, E, X, C, ESC, WASD y flechas funcionan igual. Las 67 pruebas actuales de
   juego/tests deben seguir en verde (algunas pueden actualizarse solo si el contrato lo exige, y se
   reporta cada cambio).

Pruebas del agente I: mapeo de Numpad, clic -> fijar_objetivo con partida falsa, ENTER solo en EXITO,
récord de sesión, títulos de tormenta/noche. Ejecutar la misma suite.

## Reporte de cada agente

Archivos tocados; resultado real de pytest; qué parte no verificaste; cualquier decisión que tomaste
fuera del contrato (listarla). No hagas preguntas al usuario: propón la decisión en el reporte.
