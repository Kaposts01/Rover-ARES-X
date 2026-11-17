# Operación del motor de ARES-X (para retomar)

Estado al 14/11/2026. Guía para levantar el servidor, no el informe de la entrega.

## Estado del motor (14/11)

- Partida con garantía de ganabilidad (ARX-66): al generar, se comprueba que exista una ruta por el mapa real que
  visite todos los sitios, después los drones obligatorios (desde Medio, con un margen de caza de 10 pasos por dron)
  y termine en el refugio con la batería inicial. Si no se cumple, se prueba una variante determinista del mismo mapa
  (hasta 59); la semilla del usuario no cambia.
- Medición del Híbrido en mapa pequeño (20 semillas por nivel, semillas 1009·k): Muy fácil 100 %, Fácil 100 %,
  Medio 95 %, Difícil 75 %, Hardcore 95 %. Mapa grande 40×60 en Muy fácil (10 semillas): 80 %.
- Pendiente: calibrar `MARGEN_CAZA` con el coste real de la caza (hoy 10 pasos por dron es una suposición); revisar
  los fallos de Muy fácil en 40×60; ARX-75 (disparo en rna, difuso y ag); ARX-30b y ARX-30c (baja conectividad y señal
  biológica, bloqueadas por ev3-d48 y ev3-d49). El sismo y el meteorito ya están (ver «Eventos del motor»).
- ARX-59 (escala por escalón): propuesta enviada, sin implementar. Espera la decisión del usuario en la ficha ev3-d45
  de la Bandeja (A: estaciones de recarga y más objetivos, recomendada; B: solo más sitios y drones; C: dejar la duración).
  Si elige A y hay 5 o más sitios, usar heurística (vecino más cercano más 2-opt) en vez de enumerar órdenes.

## Retomar la sesión

- La sesión que trabaja en este proyecto es `Lider_Rover`, desde la carpeta `ares_x`. Los ids y cómo reabrirla están en
  `00-Sistema-Agentico\REANUDAR_SESIONES.md`. La sesión antigua del motor, que se abría desde `Downloads`, ya no es la que trabaja.
- Antes de tocar nada, leer este documento y `docs/tareas_sprints.json` (tareas de la entrega; ARX-75 sigue asignada).

## Levantar el servidor 8765

Desde `ares_x/`:

```bash
python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765
```

- Sin `--reload`: el servidor carga el código al arrancar. Tras cambiar `juego/` o `api/` hay que reiniciarlo.
- Para reiniciar: avisar primero al orquestador, parar solo el proceso con esa línea de comando (`api.servidor:app` y
  `--port 8765`), arrancar de nuevo, comprobar `GET /` y `GET /estado` con código 200 y avisar después.
- **Nunca el puerto 8000**: es producción del CRM. Las instancias de prueba usan otros puertos.

## Regla de uso del 8765

Mientras el usuario prueba la interfaz en 8765, no crear partidas ni lanzar pasos desde otra sesión. Las mediciones van
en una instancia aparte (puerto distinto, o `TestClient` sin servidor), y se lanzan en segundo plano, de una en una.

## Eventos del motor (ARX-30, 17/11)

- **Disparo manual:** `POST /evento` con `{"nombre": "..."}`. Nombres válidos (`EVENTOS` en `api/servidor.py`): `barranco`,
  `falla_sensor`, `bateria_baja`, `tormenta`, `noche`, `meteorito`, `sismo`. Un nombre fuera de la lista responde 400.
  Un evento que no encuentra celda segura responde `ok: false` (por ejemplo, el sismo sin celda que no deje el refugio aislado).
- **Interfaz:** panel «5 · Eventos» en `api/static/index.html`: selector `#evento-nombre` con los nombres de `EVENTOS` y
  botón «Disparar» (`#evento-disparar`). Está deshabilitado sin partida o con la partida terminada. Muestra la respuesta
  como aviso y la registra en el historial de pantalla. La lista del selector está escrita a mano: al añadir un evento hay
  que editarla también.
- **Generadores propios:** los eventos espontáneos no comparten el generador de la partida.
  - Meteorito: `_rng_ambiente`, semilla `[semilla, 1313]` (como antes de ARX-30; su secuencia no cambia).
  - Sismo: `_rng_sismo`, semilla `[semilla, 1314]`.
  - Baja conectividad y señal biológica: sin generador todavía (ARX-30b y 30c).
- **Solo en partidas jugables:** los eventos espontáneos dependen de `meteoritos_activos` (la bandera `garantia`). Las
  evaluaciones congeladas no tienen eventos espontáneos; no quitar `garantia=False` de la evaluación.
- **Probabilidades y grietas:** `SISMO_PROB_POR_NIVEL`, `METEORITO_PROB_POR_NIVEL` y `GRIETAS_POR_NIVEL` en `juego/partida.py`.
  Son supuestos de simulación, no datos del PDF.
- **Limitación conocida:** el replanteo por sismo (fila `REPLAN-SISMO`) queda en la bitácora del motor (`mision.log`) y no
  aparece en `/historial`, que solo muestra las filas que anota la API. Se ve `evento:sismo` en el historial.

## Evaluación congelada

`juego/comparacion.py` (`partida_variante`) y `juego/conduccion.py` (`correr`) crean la partida con
`garantia=False`, `filas=20`, `columnas=30`. Así las cifras de `docs/TABLA_MODOS.md` y `docs/COMPARACION_POLITICAS.json`
no cambian cuando cambia la garantía. No quitar esos argumentos.

## Pruebas

- Puntuales: `python -m pytest -q juego/tests/test_partida.py` (11 pruebas) y `api/tests` por archivo o `-k`.
- Suite completa: unos 6 minutos; ejecutarla solo con turno asignado por el orquestador y sin `-n auto`.
- La última suite completa en verde (342/342) fue antes de la garantía de ARX-66 y del cambio de caza: falta repetirla.

## Trampas conocidas

- Los scripts de medición no van en la raíz del proyecto: se dejan en la carpeta temporal de la sesión.
- Un `TestClient` sin `combate` no reproduce la caza: el combate lo crea el servidor (`Combate(mundo, rover, semilla)`).
- `Mision` está congelada: los ajustes se hacen en `Partida` sobre la instancia (como `_planear` y `_optimizar_ag`).
- El disparo automático vive en la API (`_decidir_combate_automatico`), no en `Partida.avanzar_ia`.

## ARX-59 (estaciones de recarga): propuesta, detrás de bandera

Estado al 14/11 (noche). Sin publicar en 8765.

- **Bandera:** `ESTACIONES_ACTIVAS = False` en `juego/partida.py` (apagada por defecto). Con ella apagada, la partida
  usa la batería 100 − 4·(nivel−1), sin estaciones ni desvíos; criterio 2 y `test_partida`/`test_conduccion`/`test_api` en verde.
- **Con la bandera encendida** (solo en pruebas; se enciende en el script, no en la app):
  - Criterio 2 de la API: pasa (EXITO, 3–6 recargas).
  - Fácil 40×60, semillas 11 y 1009: ÉXITO (134 y 107 pasos). Semilla 2018: parada en la estación (39,4) con
    recargas en bucle.
  - Duración: 107–171 pasos frente a 300–500 de ev3-d45. Meta 90 % en Muy fácil y Fácil no alcanzada; la medición de
    20 semillas no se hizo (RAM por encima de 80 %).
- **Piezas:** `_plan_con_paradas` y `_cadena_a_destino` (cadenas de estaciones en la garantía, tramo ≤ batería máxima / factor);
  `_ir_a_estacion_si_falta_bateria` con factor 2 (peor caso de tormenta), compromiso hasta llenar, saltos hacia el próximo punto,
  exclusión de la estación recién dejada (20 pasos) y vuelta solo si no se llega directo.
- **Pista de la 2018:** el planificador sí devuelve la ruta al refugio (56 celdas) si se le llama a mano en esa posición,
  pero en la partida la ruta queda en una sola celda y el rover no sale de la estación. Hay que localizar qué vuelve a fijar
  `m.ruta` entre pasos (candidatos: `_ir_a_estacion_si_falta_bateria` y `_mover_al_compromiso`, o el replanteo de `avanzar_ia`).

## Veto del disparo (ARX-75) y dificultad (O3), 14/11 noche

- **Veto reproducible:** no se ha encontrado una semilla simple. Con `POST /evento {"nombre": "bateria_baja"}` la batería
  queda en 15, y el veto de batería crítica actúa solo por debajo de 15. Buscando en semillas 1–59 con modo rna, veto
  encendido y 80 pasos, no apareció ningún caso (el disparo necesita un dron en línea y en alcance con la batería ya baja).
  Para que Maestro lo pruebe hace falta un caso preparado: pendiente de decisión (por ejemplo, un parámetro de depuración
  que coloque un dron junto al rover, o una semilla con dron en línea que se localice con más tiempo).
- **O3 (dato para ARX-59, sin cambiar nada):** la dificultad no alarga la partida hoy. Según la ronda 11 de Maestro:
  Hardcore 35 pasos y Difícil 38, frente a Medio 42–56. De Medio a Hardcore siempre hay 4 sitios y 2 drones.
  Va junto con ev3-d47, pendiente del usuario.


## Cierre del día 14/11 (estado y primer paso de mañana)

- **8765:** arriba con el código de hoy (meteorito con formato de §10, caza en todos los modos con IA, `ultimo` de
  disparo con `rumbo` y `objetivo`, cabecera no-cache en `/` y `/static/`). No reiniciar sin avisar al orquestador.
- **Bandera de ARX-59:** `ESTACIONES_ACTIVAS = False`. Mientras esté apagada, las partidas no tienen estaciones.
- **Primer paso de mañana:** ARX-30 (sismo, baja conectividad y señal biológica), luego ARX-29 (obstáculos móviles reales
  en `/moviles`, que hoy van vacíos).
- **Pendiente de la entrega:**
  - Suite completa: no repetida desde ARX-21, ARX-66 y los cambios de caza, meteorito y O11. Va en un turno pesado que
    decide el orquestador.
  - ARX-59 como propuesta: la duración está en 107–171 pasos frente a 300–500; la semilla 2018 queda parada. Lo decide el
    usuario en ev3-d47.
  - Veto del disparo en la interfaz: falta una semilla reproducible.
- **Cómo retomar:** ver `00-Sistema-Agentico\REANUDAR_SESIONES.md` (sesión `Lider_Rover`). La sesión de `Downloads` de entonces ya no trabaja aquí.


## Estado al 15/11 (20:3x)

- **8765 detenido** por pedido del usuario (dar de baja el rover por ahora). Para levantarlo: desde `ares_x`,
  `python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765`.
- **Primer paso al volver:** ARX-30 (sismo, baja conectividad y señal biológica), luego ARX-29 (obstáculos móviles).
