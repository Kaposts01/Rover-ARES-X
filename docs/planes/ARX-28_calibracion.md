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

Divergencias paso a paso frente al híbrido (misma semilla), con la regla de clasificación técnica: «directa» es la PRIMERA divergencia por (semilla, variante) que altera decisión, velocidad o ruta, con ambas partidas empezando el paso en la misma celda y con la misma batería; «directa_codigo» son las divergencias que solo cambian el código de motivo (se cuentan aparte y no cuentan como directa); «consecuencia» es el resto. Se omiten las filas de fin de partida. Una fila es un paso en que difiere lo registrado (celda, acción, velocidad o motivo).

| técnica (variante) | semillas con directa real | filas totales | directas | directa_codigo | consecuencia |
|---|---|---|---|---|---|
| RNA (sin_rna) | 2 de 20 (4 y 18) | 90 | 2 | 4 | 84 |
| difuso (sin_difuso) | 20 de 20 | 803 | 20 | 0 | 783 |
| AG (sin_ag) | 12 de 20 (3-9, 11-14, 17) | 446 | 12 | 0 | 434 |

Qué cambia en las filas directas:
- RNA: 2 directas, semilla 4 paso 2 y semilla 18 paso 2 (el híbrido veta por la RNA con `V-RNA-OBSTACULO` al salir y `sin_rna` avanza; cambian decisión, velocidad y ruta). Cuestan +3 pasos (semilla 4) y +1 paso (semilla 18); no tocan el éxito ni las colisiones. Las 4 filas `directa_codigo` (semilla 2 paso 2, semilla 4 paso 1, semilla 12 paso 46, semilla 13 paso 43) son vetos de la RNA redundantes con `V-OBSTACULO-EN-RUTA`: misma acción `replanificar` en la misma celda, solo cambia el código de motivo (`V-RNA-OBSTACULO` o `V-RNA-BARRANCO`). Las otras 84 filas son consecuencia. Códigos `V-RNA-*` registrados en el híbrido en las 90 filas: 8.
- Difuso: 20 directas (una por semilla); 16 cambian solo la velocidad y 4 decisión, velocidad y ruta. Motivo: reglas difusas activadas en el híbrido (R4 en 14, R1 en 4, R1;R7;R9 en 2).
- AG: 12 directas, todas la fila de paso 0 por el orden de sitios del plan inicial, que difiere en 12 semillas; todas cambian la ruta.

Sobre la RNA, lo medido: no altera el éxito (19/20 en híbrido y en `sin_rna`, misma semilla fallida) ni las colisiones (0 en las cuatro variantes). Cambia una decisión en 2 semillas de 20 (la 4 y la 18), una vez en cada una, con un veto `V-RNA-OBSTACULO` en el paso 2 que cuesta pasos y no éxito. En las demás divergencias el veto de la RNA es redundante con el del supervisor para el resultado. Si M2 queda demostrado para la RNA en estos términos lo decide el Maestro; las divergencias que solo cambian el código de motivo (semillas 2, 4, 12 y 13) se cuentan aparte como `directa_codigo` y no se usan como criterio.

Hallazgo de QA (17/11/2026), sin suavizar: en la semilla 7 el híbrido PIERDE (`SIN_RUTA` en el paso 18, tras paradas por `D-DIFUSO-LENTO`) y `sin_difuso` la gana. En este escenario el difuso empeora el resultado en esa semilla; `sin_rna` también la pierde y `sin_ag` también la gana.

Prueba: `juego/tests/test_trazas_divergencia.py` falla si alguna técnica no tiene divergencia directa en las 20 semillas (CSV) o en la semilla 4 recalculada en vivo.

## 28f: recall sin borde (ev3-d63 A, control previo 28f-a)

Pregunta: con `borde_barranco` = falso y la proximidad sin desniveles, ¿la RNA reconoce barrancos? Es un control fuera de línea, sin correr las 20 semillas: recall de barranco de la RNA entrenada (`rna_entrenada()`) sobre muestras de los mapas de test de `particion_por_mapas`, con ruido 0,1 y 0,6. Umbral del plan: 0,5. El script es temporal y está fuera del repo (sesión de Lider_Rover).

| Partición (test) | Ruido | Rasgos normales (recall / precisión) | Sin `borde_barranco` (recall / precisión) |
|---|---|---|---|
| 60 mapas (test: semillas 51–59; 250 barrancos) | 0,1 | 0,780 / 0,687 | 0,000 / 0,000 (0 de 250) |
| 60 mapas (test: semillas 51–59; 250 barrancos) | 0,6 | 0,704 / 0,633 | 0,000 / 0,000 (0 de 250) |
| 30 mapas (test: semillas 25–29, no vistos; 135 barrancos) | 0,1 | 0,800 / 0,692 | 0,000 / 0,000 (0 de 135) |
| 30 mapas (test: semillas 25–29, no vistos; 135 barrancos) | 0,6 | 0,719 / 0,693 | 0,000 / 0,000 (0 de 135) |

Veredicto: sin el rasgo `borde_barranco` la RNA no predice ningún barranco (0 predicciones de barranco en todas las medidas). El recall queda en 0,000, por debajo de 0,5, así que el control se cierra en negativo según ev3-d63 A. **No se corren las 20 semillas del escenario `exigente_rna`** (28f-b y 28f-c no se hacen). El escenario no se crea.

Lo medido: la RNA reconoce barrancos con sus rasgos normales (recall 0,70–0,80), y sin `borde_barranco` no reconoce ninguno.

Inferencia (no medida): la RNA depende casi por completo del rasgo `borde_barranco` para distinguir barranco de libre. Con la vibración sola, la separación es pequeña (ver `docs/planes/ARX-28f_rna_unica.md`, sección 1), y el control confirma que no alcanza.

Para el informe (M2): la RNA queda con el resultado negativo de 28f. Con el escenario exigente, la RNA cambia una decisión en 2 de 20 semillas, sin cambiar éxito ni colisiones. La explicación probable es la redundancia: la RNA casi no aporta información que el supervisor no tenga por el sensor de borde.
