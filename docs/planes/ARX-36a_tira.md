# ARX-36a · Tira de decisiones de la vista del automático

Cierra M17 (explicación por decisión). Rama `feat/arx-36a-tira`, desde `a0bf109`. Solo interfaz (`api/static/`); sin cambios en el motor ni en los cálculos.

## Qué es la tira

Una fila por paso reciente del modo «automático». Cada fila lleva el número de paso y las mismas cuatro líneas de ARX-88 como datos, una por técnica:

1. RNA: clase predicha y su probabilidad.
2. Difuso: reglas activadas con su fuerza y la velocidad, o «no usado».
3. Planificador: celdas de la ruta planeada, o «sin ruta».
4. Supervisor: acción y vetos `V-*` si los hubo.

Se conservan los últimos 12 pasos, el más reciente arriba. Las frases salen de una sola función (`decisionesDelPaso`) que usan tanto el bloque ARX-88 del panel de supervisión como la tira: no hay texto fijo por paso (M17).

## De dónde salen los datos

- Fuente única: `GET /paneles` (ya existe, lo llama `refrescarPaneles` tras cada paso). Campos `rna`, `difuso`, `ag.ruta_planeada`, `supervisor` y `paso`.
- La tira se alimenta en `pintarPaneles`, o sea en el mismo refresco que ya corre por paso; sin temporizador aparte. Un mismo `paso` no se duplica (los refrescos tras un evento repiten el paso).
- Se vacía al empezar otra misión (el número de paso retrocede o no hay paso).
- Sin endpoint nuevo ni cambios en `api/servidor.py`.

## Cuando no hay datos

- Sin ningún paso aún: la tira dice «sin pasos todavía».
- Dato ausente en una técnica de un paso: esa celda dice «sin dato» (RNA, difuso, supervisor) o «sin ruta» (planificador); el difuso dice «no usado» si no actuó. Nunca «null» ni celda vacía.

## Dónde se ve

Bloque `#tira-caja` bajo «Automático continuo», visible solo con el modo en «automático» y partida cargada.

## Hecho cuando

- Con modo automático y unos pasos dados, la tira muestra una fila por paso con las cuatro decisiones, coincidentes con el panel de supervisión del último paso.
- Con otro modo (manual, rna, difuso, ag) la tira no se ve.
- Al iniciar otra misión se vacía.
- Consola limpia.

## Comprobación en Chrome (puerto 8766)

`uvicorn api.servidor:app --host 127.0.0.1 --port 8766` desde el worktree. Arrancar una partida en modo automático, dar varios pasos, confirmar que aparecen filas reales cuyo último renglón coincide con el bloque ARX-88, que un modo no automático la oculta y que la consola no tiene errores. Cerrar servidor y pestaña. Como no cambia el endpoint, no se agregan pruebas en `api/tests`.
