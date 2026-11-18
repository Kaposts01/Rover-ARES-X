# M15 · capa de riesgo estimado en la escena 3D

Base: a0bf109. Solo `api/static/` (index.html, app.js). La API no cambia.

## Evidencia de la base
- `/mapa` ya devuelve `riesgo_estimado` (`api/servidor.py`, ARX-86): matriz filas×columnas, valores 0..1 redondeados a 2 decimales (`mision.riesgo`).
- El terreno se dibuja en `construirTerreno`/`construirCuadricula` (`grupoMapa`, se vacía en cada `construirMapa`). La altura sale de `alturaTerreno(x, z)`.

## Criterio de hecho
1. **Qué se dibuja.** Una malla de una celda por celda del mapa (un solo `Mesh` con color por vértice), apoyada sobre el relieve (`alturaTerreno` + 0,04), en un grupo propio `grupoRiesgo` que no se vacía con `grupoMapa`.
2. **Color.** Rampa verde (riesgo 0) → amarillo (0,5) → rojo (1). Celdas con riesgo menor a 0,05 no se pintan (alfa 0) para no cubrir todo el suelo de verde.
3. **Opacidad.** Material semitransparente fijo 0,45, sin escribir profundidad.
4. **Dato.** Campo `riesgo_estimado` de `GET /mapa`. Al encender el interruptor se vuelve a pedir `/mapa` (el riesgo estimado cambia con la partida) y se redibuja; no se inventa ningún valor en la interfaz.
5. **Interruptor.** Casilla «Riesgo estimado» en el panel de controles, **apagada por defecto**; con ella apagada no se crea ni se añade nada a la escena. Al reiniciar partida/mapa, la capa se rehace solo si el interruptor está encendido.
6. **Sin dato.** Si `/mapa` no trae `riesgo_estimado` (o no tiene la forma de `tipo`), la capa no se dibuja, la casilla se desmarca y se avisa junto a ella: «sin datos de riesgo».
7. Sin cambios de API, de juego ni de otros archivos.

## Comprobación en Chrome (puerto 8766, nunca 8765)
- Interruptor apagado: `grupoRiesgo` vacío (no hay malla), consola sin errores.
- Encendido: aparece la malla con colores de `/mapa` reales (comparar un par de celdas con la respuesta de `/mapa`).
- Apagado de nuevo: la malla desaparece.
- Consola sin errores en todo el recorrido.
