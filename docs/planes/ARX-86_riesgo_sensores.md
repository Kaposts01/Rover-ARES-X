# ARX-86 · riesgo estimado e indicador de sensores

Base: b84e640. Frente único (no comparte archivos con ARX-87 ni ARX-88).

## Qué falta en b84e640 (evidencia)
- /mapa no devuelve el riesgo estimado (`mision.riesgo`), solo el terreno.
- /estado no devuelve las lecturas de los sensores (solo el resumen de la partida).
- La interfaz no tiene indicador de sensores (app.js solo decora el dron 3D con un sensor).

## Criterio de hecho
1. /mapa devuelve `riesgo_estimado`: matriz del mapa de riesgo de la misión, redondeada a 2 decimales, del mismo tamaño que `tipo`.
2. /estado devuelve `sensores`: las lecturas del sensor en el rumbo actual (proximidad, borde, gradiente, vibración), la probabilidad de la celda de enfrente (`riesgo_enfrente`) y `falla`: true si hay falla de sensor en curso. Se calcula con `_observar`, sin consumir el ruido real.
3. La interfaz muestra un indicador de sensores: las cuatro lecturas, el riesgo estimado de la celda de enfrente y «falla» cuando la hay.
4. Sin cambios de juego: el hash del congelado no cambia; las rutas y las partidas de la comparación no cambian.

## Pruebas
- API: /mapa tiene `riesgo_estimado` con la forma de `tipo`; /estado tiene `sensores` con las cuatro claves y `falla` booleano.
- Hash del congelado d6fb9079… sin cambios.
- Comprobación en Chrome en 8766 (no en 8765) de que el indicador aparece y cambia al moverse.
