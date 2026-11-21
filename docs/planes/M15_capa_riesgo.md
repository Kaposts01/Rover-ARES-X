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

## Resultado en Chrome (8766, mapa grande 40×60 salvo donde se indica)
- Peticiones a `/mapa` con la capa encendida: 1 por paso (5 de 5 pasos). Apagada: 0 por paso.
- FPS (requestAnimationFrame, 3 a 4 s): primera medición con la capa apagada 74,6; con la capa encendida 60,0. Alternando apagada/encendida en las mismas condiciones: 60,0 / 60,0 / 60,1 / 60,2. La diferencia de la primera medición no viene de la capa (el valor base de la pestaña cambió a 60); con la capa no se aprecia caída. Durante 3 pasos seguidos con la capa: 60.
- Malla con celdas ≥ 0,3: vértices = 9 × celdas (738 = 82 × 9), coincide con `/mapa`.
- Reinicio de partida con la capa encendida: la malla se rehace (uuid nuevo, semilla nueva) con la casilla aún marcada, sin peticiones extra a `/mapa`. Un primer intento no reconstruyó la malla (mismo uuid); el repetido sí. No se investigó la causa (posible clic con la partida ocupada).
- Mapa pequeño 20×30: malla con extremos x=30, z=19, 25 celdas ≥ 0,3 = 225 vértices, coincide con `/mapa`.
- Consola sin errores en todo el recorrido.

## No comprobado
Mapa mediano (30×45), otros planetas distintos de Marte, clic con ratón real sobre el interruptor (se usó `change` por script), aspecto visual (una captura quedó tapada por el diálogo de inicio).

## Limitación declarada (QA 21/11, H-1)
El rover parte de un mapa previo parcial: `mision.riesgo` nace de `genetico.mapa_estimado`, que marca con riesgo 1,0 cerca del 80 % de los peligros reales desde el paso 0 (ya estaba en `main`; no se toca el motor). Por eso la capa dibuja desde el primer cuadro peligros que el sensor aún no vio. Decisión: no filtrar, rotular. La casilla, la leyenda y el aviso dicen «riesgo estimado: mapa previo orbital (≈80 % de detección) + sensores». En el modo Incertidumbre, la leyenda aclara que una celda roja no observada viene del mapa previo (el riesgo gana sobre la observación). Se mantiene «no observada», nunca «entropía».
