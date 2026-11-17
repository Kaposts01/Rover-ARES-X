# ARX-28a · Calibración del escenario exigente

Medición del 17/11/2026 sobre la rama `feat/arx-28-ablaciones` (HEAD f4ae5f1). Semillas 1 a 5, nivel 5, mapa 20×30 (`garantia=False`), las cuatro variantes de `juego/comparacion.py` (`hibrido`, `sin_rna`, `sin_difuso`, `sin_ag`), rejilla `ruido` ∈ {0,3; 0,6; 1,0} × `p_detectar` ∈ {0,4; 0,6}. Referencia de la RNA entrenada: `ruido = 0,1`, `p_detectar = 0,8` (valores por defecto de `Mision` y de `mapa_estimado`). Tiempo total de la medición: unos 350 s, un solo proceso.

## Resultado

**Ninguna combinación separa la RNA.** En las 6 combinaciones, las 4 variantes tienen 5 de 5 éxitos y 0 colisiones en las 5 semillas; `hibrido` y `sin_rna` difieren en colisiones o éxito en 0 de 5 semillas (criterio: al menos 2). El híbrido cumple el mínimo de 3 éxitos de 5 en todas. Es un resultado válido según el plan (riesgo del §7).

## Tabla completa (pasos por semilla 1..5; colisiones siempre 0; éxitos 5/5 en todas las celdas)

| ruido | p_detectar | hibrido | sin_rna | sin_difuso | sin_ag | semillas donde hibrido≠sin_rna (colisión o éxito) |
|---|---|---|---|---|---|---|
| 0,3 | 0,4 | 68, 58, 46, 47, 59 | 68, 58, 46, 44, 59 | 66, 58, 45, 47, 58 | 68, 58, 47, 60, 63 | 0 |
| 0,3 | 0,6 | 68, 55, 45, 47, 58 | 68, 55, 45, 44, 58 | 65, 55, 45, 47, 58 | 68, 55, 46, 60, 63 | 0 |
| 0,6 | 0,4 | 67, 60, 46, 51, 59 | 67, 60, 46, 48, 59 | 66, 60, 46, 47, 58 | 67, 60, 47, 63, 63 | 0 |
| 0,6 | 0,6 | 68, 60, 46, 51, 58 | 68, 60, 46, 48, 58 | 66, 57, 46, 47, 58 | 68, 60, 46, 63, 63 | 0 |
| 1,0 | 0,4 | 67, 59, 46, 51, 59 | 67, 59, 46, 51, 59 | 66, 59, 46, 48, 59 | 67, 59, 47, 63, 59 | 0 |
| 1,0 | 0,6 | 68, 60, 46, 51, 59 | 68, 60, 46, 51, 59 | 66, 59, 46, 48, 59 | 68, 60, 46, 63, 59 | 0 |

Lectura: lo único que cambia entre variantes son los pasos (unos pocos, sobre todo en la semilla 4); con `ruido = 1,0` el híbrido y `sin_rna` son idénticos. `sin_ag` es la única ablación con una diferencia sistemática (hasta 12 pasos más en la semilla 4).

## Valores elegidos

Como ninguna combinación separa la RNA, se aplica la regla del plan: usar la de mayor diferencia. Con el criterio de colisiones/éxito todas empatan en 0; con pasos como desempate, cuatro combinaciones empatan (3 pasos de diferencia en la semilla 4, con `ruido` 0,3 y 0,6). Se elige **`ruido = 0,6` y `p_detectar = 0,4`**: es la que mantiene diferencia entre `hibrido` y `sin_rna` (3 pasos), tiene el mapa estimado más pobre y el mayor contraste de `sin_ag` (63 frente a 51 pasos en la semilla 4). Es una elección de desempate, no una separación demostrada. Quedan en `ESCENARIOS["exigente"]` de `juego/comparacion.py`.

## Para decidir (ficha del usuario)

El escenario exigente no hace que apagar la RNA cambie el resultado. Causa probable, ya descrita en el plan: el sensor de proximidad sigue siendo exacto (`prob_fallo = 0`) y el veto por riesgo llega antes que el de la RNA; subir el ruido no afecta esa ruta. Opciones: aceptar el resultado y declararlo en el informe, o abrir una tarea aparte (sensor con `prob_fallo > 0` o reentrenar la RNA). No se adelanta.
