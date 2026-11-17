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

## Medición de prob_fallo

Medición del 17/11/2026 sobre `feat/arx-28-ablaciones` (HEAD f2eb931). Escenario `exigente` (nivel 5, ruido 0,6, p_detectar 0,4), semillas 1 a 5, las cuatro variantes, `prob_fallo` ∈ {0,0; 0,05; 0,1; 0,2; 0,3} (0,0 se midió como `None`, igual que hoy). Un solo proceso, 244 s, RAM máxima 66 %. Los motivos se cuentan en la bitácora de la misión (`mision.log.filas[].motivos`); «modo seguro» es la partida que termina en `MODO_SEGURO`. Como `V-SENSOR-NAN` manda a modo seguro (estado terminal), cada partida cuenta como máximo 1 de cada uno. «Vetos RNA» = motivos `V-RNA-*` (la parte que sí es de la RNA).

| prob_fallo | variante | éxitos | pasos (s1..s5) | colisiones | V-SENSOR-NAN | modo seguro | vetos RNA |
|---|---|---|---|---|---|---|---|
| 0,0 | hibrido | 5/5 | 67, 60, 46, 51, 59 | 0 | 0 | 0 | 5 |
| 0,0 | sin_rna | 5/5 | 67, 60, 46, 48, 59 | 0 | 0 | 0 | 0 |
| 0,0 | sin_difuso | 5/5 | 66, 60, 46, 47, 58 | 0 | 0 | 0 | 3 |
| 0,0 | sin_ag | 5/5 | 67, 60, 47, 63, 63 | 0 | 0 | 0 | 3 |
| 0,05 | hibrido | 0/5 | 12, 1, 46, 11, 6 | 0 | 5 | 5 | 2 |
| 0,05 | sin_rna | 0/5 | 12, 1, 46, 11, 6 | 0 | 5 | 5 | 0 |
| 0,05 | sin_difuso | 0/5 | 12, 1, 46, 11, 6 | 0 | 5 | 5 | 2 |
| 0,05 | sin_ag | 0/5 | 12, 1, 46, 11, 6 | 0 | 5 | 5 | 2 |
| 0,1 | las 4 | 0/5 | 12, 1, 2, 1, 4 | 0 | 5 | 5 | 0 |
| 0,2 | las 4 | 0/5 | 16, 1, 2, 1, 2 | 0 | 5 | 5 | 0 |
| 0,3 | las 4 | 0/5 | 2, 1, 7, 12, 2 | 0 | 5 | 5 | 0 |

Diferencia hibrido frente a sin_rna, por valor, y parte atribuible al veto por NaN:

| prob_fallo | dif. éxito | dif. pasos (suma s1..s5) | dif. colisiones | vetos V-SENSOR-NAN (hibrido / sin_rna) | modo seguro (hibrido / sin_rna) | parte atribuible al veto |
|---|---|---|---|---|---|---|
| 0,0 | 0 | +3 (semilla 4) | 0 | 0 / 0 | 0 / 0 | ninguna: el veto no actúa; los 3 pasos vienen de 5 vetos RNA del híbrido, que le cuestan pasos, no éxitos |
| 0,05 | 0 | 0 | 0 | 5 / 5 | 5 / 5 | toda la diferencia (cero) es del veto: ambas variantes mueren igual |
| 0,1 | 0 | 0 | 0 | 5 / 5 | 5 / 5 | idem |
| 0,2 | 0 | 0 | 0 | 5 / 5 | 5 / 5 | idem |
| 0,3 | 0 | 0 | 0 | 5 / 5 | 5 / 5 | idem |

## Criterio aplicado y conclusión

Con cualquier `prob_fallo` > 0 la primera lectura NaN lleva a `V-SENSOR-NAN` y a `MODO_SEGURO` (terminal), igual en las cuatro variantes porque el supervisor se aplica a todas; la partida acaba en 1 a 46 pasos, con 0 éxitos y 0 colisiones, y las trayectorias de `hibrido`, `sin_rna`, `sin_difuso` y `sin_ag` son idénticas (misma semilla, mismo sensor). No hay ventaja del híbrido: hay un derrumbe común. Con 0,0 no hay veto y la diferencia es de 3 pasos en una semilla, sin éxito ni colisiones distintos (ya registrado en 28a).

**No se separa por la RNA.** M2 no queda demostrado para la RNA con `prob_fallo` en este escenario. Ningún valor cumple el criterio (ventaja estable y atribuible a la RNA), así que **`ESCENARIOS["exigente"]["prob_fallo"]` se deja en `None`**. Los valores 0,05 a 0,3 son ya demasiado altos para este diseño: incluso 0,05 aborta las 5 partidas, y un valor menor (p. ej. 0,005 a 0,01) solo cambiaría cuándo cae en modo seguro, sin que la RNA intervenga, porque el veto es previo a ella y se aplica igual a `sin_rna`.

Opciones para el usuario (ficha, sin decidir aquí): (A) aceptar y declarar en el informe que el escenario exigente no separa la RNA ni con fallo de sensor (costo: solo redacción; aporta a M2 como resultado negativo honesto); (B) tarea aparte para que el fallo del sensor degrade en vez de abortar (p. ej. ignorar la lectura NaN y seguir con el mapa estimado) y medir de nuevo (costo: cambia `integracion.py`/supervisor, fuera de ARX-28, requiere pruebas y reabre el límite de seguridad V-SENSOR-NAN); (C) reentrenar la RNA con ruido alto y detección pobre (costo: reentrenar y revalidar métricas ya congeladas).

## Resultado de 20 semillas

Escenario exigente (nivel 5, ruido 0,6, p_detectar 0,4, `prob_fallo` = None), semillas 1 a 20, cuatro variantes. Archivos: `docs/COMPARACION_POLITICAS_exigente.json` (`python scripts/comparacion_politicas.py 20 exigente`) y `docs/TRAZA_DIVERGENCIAS_exigente.csv` (`python scripts/traza_divergencias.py 20 exigente`). El congelado `docs/COMPARACION_POLITICAS.json` no se tocó.

Medición de éxito, colisiones y pasos (JSON):

| variante | éxitos | colisiones (media) | pasos (media) |
|---|---|---|---|
| hibrido | 19/20 | 0,0 | 50,85 |
| sin_rna | 19/20 | 0,0 | 50,65 |
| sin_difuso | 20/20 | 0,0 | 50,85 |
| sin_ag | 20/20 | 0,0 | 55,2 |

La semilla 7 termina en `SIN_RUTA` en el híbrido y en `sin_rna`; `sin_difuso` y `sin_ag` la ganan.

Divergencias paso a paso frente al híbrido (misma semilla). «Directa» es una fila en que ambas partidas empezaban el paso en la misma celda y con la misma batería, así que la diferencia sale de la técnica en ese paso; «consecuencia» es una fila posterior a que las trayectorias ya se separaron. Una fila es un paso en que difiere lo registrado (celda, acción, velocidad o motivo).

| técnica (variante) | semillas con divergencia | filas totales | directas | consecuencia |
|---|---|---|---|---|
| RNA (sin_rna) | 5 de 20 (2, 4, 12, 13, 18) | 94 | 9 | 85 |
| difuso (sin_difuso) | 20 de 20 | 863 | 423 | 440 |
| AG (sin_ag) | 12 de 20 (3-9, 11-14, 17) | 541 | 40 | 501 |

Qué cambia en las filas directas:
- RNA: 9 filas marcadas «directas», pero solo 2 son divergencias directas reales: semilla 4, paso 2, y semilla 18, paso 2 (el híbrido veta por la RNA al salir y `sin_rna` avanza). Cuestan +3 pasos (semilla 4) y +1 paso (semilla 18); no tocan el éxito ni las colisiones. Las filas de los pasos 11 y 12 de la semilla 4 son consecuencia del desfase de un paso (distinto `paros_seguidos` y lecturas del sensor), y la del paso 42 de la semilla 18 es un artefacto de fin de partida. En las semillas 2, 12 y 13 (y en el paso 1 de la 4) el veto de la RNA es redundante con `V-OBSTACULO-EN-RUTA`: misma acción `replanificar` en la misma celda, solo cambia el código de motivo (`V-RNA-OBSTACULO` o `V-RNA-BARRANCO` frente a `V-OBSTACULO-EN-RUTA`). Códigos `V-RNA-*` registrados en el híbrido en las 94 filas: 8.
- Difuso: 423 filas; 380 cambian solo la velocidad, 42 también decisión y ruta, 1 velocidad y ruta. Motivo: reglas difusas activadas en el híbrido (la más frecuente, R4, en 173 filas directas donde es la única regla activada; 259 si se cuentan las que la incluyen junto a otras).
- AG: 40 filas; 15 cambian la ruta, 12 la velocidad, 9 decisión, velocidad y ruta, 4 velocidad y ruta. Además, el orden de sitios del plan inicial difiere en 12 semillas (fila de paso 0).

Sobre la RNA, lo medido: no altera el éxito (19/20 en híbrido y en `sin_rna`, misma semilla fallida) ni las colisiones (0 en las cuatro variantes). Cambia una decisión en 2 semillas de 20 (la 4 y la 18), una vez en cada una, con un veto `V-RNA-OBSTACULO` en el paso 2 que cuesta pasos y no éxito. En las demás divergencias el veto de la RNA es redundante con el del supervisor para el resultado. Si M2 queda demostrado para la RNA en estos términos lo decide el Maestro; la cifra de «5 semillas» cuenta divergencias que solo cambian el código de motivo y no se usa como criterio.

Prueba: `juego/tests/test_trazas_divergencia.py` falla si alguna técnica no tiene divergencia directa en las 20 semillas (CSV) o en la semilla 4 recalculada en vivo.
