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
  los fallos de Muy fácil en 40×60; ARX-75 (disparo en rna, difuso y ag); ARX-79 (ganabilidad de la señal en el mapa
  grande, ver «Baja de conectividad y señal biológica»); integrar `feat/arx-30-bc` en `main`.
- ARX-59 (escala por escalón): decidido (ev3-d45 A: estaciones de recarga y más objetivos); a medias detrás de
  `ESTACIONES_ACTIVAS = False`; se retoma al final del sprint (ev3-d47 B).
  Con ev3-d45 A y 5 o más sitios, usar heurística (vecino más cercano más 2-opt) en vez de enumerar órdenes.

## Retomar la sesión

- Reabrir desde `C:\Users\Usuario\Downloads` (no desde `ares_x`), con
  `claude --resume 8fabbd07-ce6f-5b4c-97eb-59ae80452d6d`. La conversación está en `~/.claude/projects/C--Users-Usuario-Downloads/`.
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

## Evaluación congelada

`juego/comparacion.py` (`partida_variante`) y `juego/conduccion.py` (`correr`) crean la partida con
`garantia=False`, `filas=20`, `columnas=30`. Así las cifras de `docs/TABLA_MODOS.md` y `docs/COMPARACION_POLITICAS.json`
no cambian cuando cambia la garantía. No quitar esos argumentos.

## Pruebas

- Puntuales: `python -m pytest -q juego/tests/test_partida.py` (11 pruebas) y `api/tests` por archivo o `-k`.
- Suite completa: unos 6 minutos; ejecutarla solo con turno asignado por el orquestador y sin `-n auto`.
- Suite completa de `feat/arx-30-bc` (QA, 17/11): 410 passed y 4 fallos previos de `main` (ARX-78:
  `test_historial::test_drones_pendientes…` y `test_partida_v2::test_nivel_genera_el_mundo_del_contrato[3,4,5]`).

## Trampas conocidas

- Los scripts de medición no van en la raíz del proyecto: se dejan en la carpeta temporal de la sesión.
- Un `TestClient` sin `combate` no reproduce la caza: el combate lo crea el servidor (`Combate(mundo, rover, semilla)`).
- `Mision` está congelada: los ajustes se hacen en `Partida` sobre la instancia (como `_planear` y `_optimizar_ag`).
- El disparo automático vive en la API (`_decidir_combate_automatico`), no en `Partida.avanzar_ia`.
- La orden perdida en manual y el corte espontáneo usan el mismo generador (`_rng_enlace`): mover el rover durante un corte
  cambia la secuencia de cortes espontáneos de esa semilla.

## Baja de conectividad y señal biológica (ARX-30b y 30c)

Estado: en `feat/arx-30-bc`, QA vuelta 2 (17/11): aprobado con observaciones. Pendiente de integrar en `main`.

- **Corte de enlace** (ev3-d48 A, ev3-d53 A): dura `PASOS_SIN_ENLACE` = 4 pasos. En manual, cada orden de `/mover` se pierde
  con probabilidad `PROB_ORDEN_PERDIDA` = 0,5 mientras dura; la orden perdida consume un paso y se registra con
  `D-SIN-ENLACE`. En los modos de IA, `/recomendacion` e `/intervencion` responden 409 hasta que vuelva el enlace.
  Caída espontánea con `ENLACE_PROB_POR_NIVEL` (0,2 % a 0,6 % por paso), solo en partidas jugables.
- **Señal biológica** (ev3-d49 B, ev3-d50 C, ev3-d51 A, ev3-d52 A): es objetivo obligatorio para ganar; pisar la celda la
  visita. No da puntos extra (no existe `BONUS_SENAL`) y siempre dice «no confirma vida». Cae sola en todos los niveles
  (`SENAL_PROB_POR_NIVEL`, 0,2 % a 0,6 % por paso). Con ev3-d51 A: no aparece si queda un solo objetivo pendiente, y solo si
  la batería alcanza para ir, volver y terminar con la caza de drones obligatorios (`_ganable_con_senal`, `MARGEN_ENERGIA`
  15 % y la reserva `DANO_METEORITO` de 5 % si el meteorito está activo).
- **Generadores propios:** `_rng_enlace` con `[semilla, 1315]` (la orden perdida en manual también lo usa) y `_rng_senal`
  con `[semilla, 1316]`. Los de sismo (1314) y meteoritos (`_rng_ambiente`, 1313) no cambian.
- **Selector de eventos:** el control «5 · Eventos» de `api/static/index.html` tiene los 9 valores de `EVENTOS`:
  `barranco`, `falla_sensor`, `bateria_baja`, `tormenta`, `noche`, `meteorito`, `sismo`, `baja_conectividad` y
  `senal_biologica`. Su lista está escrita a mano: si se añade un evento, hay que editarla también.

### Limitaciones conocidas

- **R1 · ganabilidad de la señal en el mapa grande (40×60, el tamaño por defecto).** Con la reserva actual (5 % de meteorito,
  caza y `MARGEN_ENERGIA` 15 %): en Muy fácil, semilla 5, la señal aceptada deja la partida en batería 0 (1 de 9 semillas
  ganables en la prueba de QA). En Medio, Difícil y Hardcore la señal se rechaza por batería en 12 de 12 casos, así que casi
  nunca aparece. La causa es previa a la rama: el estimador de `_es_ganable` y `_plan_con_paradas` es optimista en el mapa
  grande (ya ocurre en `main` sin eventos). Lo sigue la tarea ARX-79. **La reserva definitiva depende de la ficha ev3-d56,
  que sigue abierta**; hoy es la de 5 %, y no es definitiva. Mientras tanto, no contar con la señal en el mapa grande. En
  pequeño, el barrido de QA (12 semillas por nivel) acepta la señal en los 5 niveles y todas las aceptadas terminan en EXITO.
- **O-b (BAJO):** la fila «Señal biológica» desaparece del panel de objetivos al visitarla, y `/objetivos` no la devuelve.
  Sin resolver.
- **O-a (BAJO):** la prueba `test_ninguna_senal_aceptada_con_drones_deja_sin_ganar` acepta EXITO sin comprobar que la señal
  entró. Sin resolver.

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
  Va junto con ev3-d47 (decidido B: se retoma al final del sprint).


## Cierre del día 14/11 (estado y primer paso de mañana)

- **8765:** arriba con el código de hoy (meteorito con formato de §10, caza en todos los modos con IA, `ultimo` de
  disparo con `rumbo` y `objetivo`, cabecera no-cache en `/` y `/static/`). No reiniciar sin avisar al orquestador.
- **Bandera de ARX-59:** `ESTACIONES_ACTIVAS = False`. Mientras esté apagada, las partidas no tienen estaciones.
- **Primer paso de mañana:** ARX-30 (sismo, baja conectividad y señal biológica), luego ARX-29 (obstáculos móviles reales
  en `/moviles`, que hoy van vacíos).
- **Pendiente de la entrega:**
  - Suite completa: no repetida desde ARX-21, ARX-66 y los cambios de caza, meteorito y O11. Va en un turno pesado que
    decide el orquestador.
  - ARX-59: decidido ev3-d45 A y a medias. La duración está en 107–171 pasos frente a 300–500; la semilla 2018 queda
    parada. Se retoma al final del sprint (ev3-d47 B).
  - Veto del disparo en la interfaz: falta una semilla reproducible.
- **Cómo retomar:** `claude --resume 8fabbd07-ce6f-5b4c-97eb-59ae80452d6d` desde `C:\Users\Usuario\Downloads`.


## Estado al 15/11 (20:3x)

- **8765 detenido** por pedido del usuario (dar de baja el rover por ahora). Para levantarlo: desde `ares_x`,
  `python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765`.
- **Primer paso al volver:** ARX-30 (sismo, baja conectividad y señal biológica), luego ARX-29 (obstáculos móviles).
