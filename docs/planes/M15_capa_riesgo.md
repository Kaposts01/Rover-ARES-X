# M15 · capa de riesgo estimado en la escena 3D

Base: a0bf109. Solo `api/static/` (index.html, app.js). La API no cambia.

## Evidencia de la base
- `/mapa` ya devuelve `riesgo_estimado` (`api/servidor.py`, ARX-86): matriz filas×columnas, valores 0..1 redondeados a 2 decimales (`mision.riesgo`).
- El terreno se dibuja en `construirTerreno`/`construirCuadricula` (`grupoMapa`, se vacía en cada `construirMapa`). La altura sale de `alturaTerreno(x, z)`.

## Criterio de hecho
1. **Qué se dibuja.** Una malla de una celda por celda del mapa (un solo `Mesh` con color por vértice), apoyada sobre el relieve (`alturaTerreno` + 0,04), en un grupo propio `grupoRiesgo` que no se vacía con `grupoMapa`.
2. **Color y umbral.** Rampa amarillo (0,3) → rojo (1). Solo se dibujan las celdas con riesgo ≥ 0,3, constante con nombre `UMBRAL_CAPA_RIESGO = 0.3` (decisión del Orquestador). Motivo: la capa muestra peligro; con umbral bajo teñía el mapa entero y no distinguía nada. Sustituye al umbral previo de 0,05 y a la rampa con verde.
3. **Opacidad.** Material semitransparente fijo 0,45, sin escribir profundidad.
4. **Dato.** Campo `riesgo_estimado` de `GET /mapa`. Al encender el interruptor se vuelve a pedir `/mapa` (el riesgo estimado cambia con la partida) y se redibuja; no se inventa ningún valor en la interfaz.
4b. **Refresco por paso (decisión del Orquestador).** Con la capa encendida, cada vez que avanza el rover (paso o movimiento, vía `refrescarEstado`) la capa vuelve a leer `GET /mapa` y se redibuja: una petición por avance, sin solapar peticiones. Con la capa apagada no se pide nada extra. Se mide en Chrome el número de peticiones a `/mapa` por paso y los FPS antes y después; si bajan de forma visible se informa con la cifra y no se optimiza sin aviso.
5. **Interruptor.** Casilla «Riesgo estimado» en el panel de controles, **apagada por defecto**; con ella apagada no se crea ni se añade nada a la escena. Al reiniciar partida/mapa, la capa se rehace solo si el interruptor está encendido.
6. **Sin dato.** Si `/mapa` no trae `riesgo_estimado` (o no tiene la forma de `tipo`), la capa no se dibuja, la casilla se desmarca y se avisa junto a ella: «sin datos de riesgo».
7. Sin cambios de API, de juego ni de otros archivos.

## Comprobación en Chrome (puerto 8766, nunca 8765)
- Interruptor apagado: `grupoRiesgo` vacío (no hay malla), consola sin errores.
- Encendido: aparece la malla con colores de `/mapa` reales (comparar un par de celdas con la respuesta de `/mapa`).
- Apagado de nuevo: la malla desaparece.
- Consola sin errores en todo el recorrido.

## Comprobación adicional pedida (puerto 8766)
- Reinicio de partida con la capa encendida: la capa se rehace.
- Mapa pequeño (20×30): la capa usa las dimensiones correctas.
- Declarado como NO comprobado: mapa mediano, otros planetas, clic con ratón real sobre el interruptor.
