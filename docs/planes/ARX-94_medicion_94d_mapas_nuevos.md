# ARX-94d · repetición de la medición en mapas nuevos (200 a 219)

Motivo: la QA y el Maestro señalaron que los mapas 100 a 119 de la medición oficial de 94d ya se habían usado al explorar el ruido de la cámara, así que como evaluación eran optimistas. Esta es una única repetición con `scripts/medicion_94d.py 200 220` (un hilo, 2,5 s), sobre 20 mapas que nadie había tocado, con los **mismos umbrales escritos antes** (`ARX-94_umbrales.md`). No se ajustó nada después de ver el resultado.

| Métrica | Umbral | Mapas 100–119 (ya vistos) | Mapas 200–219 (nuevos) | Resultado en los nuevos |
|---|---|---|---|---|
| Recall de barrancos | ≥ 0,6 | 0,643 (45 de 70) | **0,548 (40 de 73)** | **NO cumple** |
| Falsos positivos | ≤ 0,2 % | 0,058 % | 0,130 % | cumple |
| ECE | ≤ 0,03 | 0,008 | 0,007 | cumple |
| Macro-F1 v2 | sin umbral | 0,913 | 0,877 | informativo |

Matriz en los mapas nuevos (filas = real, columnas = predicho; libre, obstáculo, barranco): [[6923, 11, 9], [7, 448, 0], [33, 0, 40]].

Lectura honesta: con 70 a 73 barrancos por conjunto, el intervalo de confianza del recall es ancho (aprox. 0,43 a 0,66 para 0,548), y la diferencia entre 0,643 y 0,548 es compatible con la variación entre mapas; pero el umbral de 0,6 **no se cumple en mapas no vistos**, y así debe declararse en el INFORME (M2 y M7 no pueden apoyarse en el 0,643 como si fuera una evaluación limpia). La decisión de qué sigue (aceptarlo declarado, mejorar la RNA v2 o cambiar el diseño del sensor) es del usuario y se lleva a ficha; no se cambia ningún umbral ni dato para que cumpla.
