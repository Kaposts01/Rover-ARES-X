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

Medición de éxito, colisiones y pasos (JSON regenerado, ev3-d64 A; `ruta_corta` rotulada como voraz; `ag_puro` no se publica hasta ARX-92):

| variante | éxitos | colisiones (media) | pasos (media) |
|---|---|---|---|
| hibrido | 20/20 | 0,0 | 54,3 |
| sin_rna | 20/20 | 0,0 | 54,0 |
| sin_difuso | 15/20 | 0,05 | 55,65 |
| sin_ag (orden de sitios: vecino más cercano) | 19/20 | 0,0 | 58,3 |
| ruta_corta (voraz, vecino más cercano) | 15/20 | 0,0 | 59,15 |

La semilla 7 termina en EXITO en el híbrido y en `sin_rna` (antes SIN_RUTA; cambio de ARX-90, atribución por resta, ver abajo).

Divergencias paso a paso frente al híbrido (misma semilla), con la regla de clasificación técnica: «directa» es la PRIMERA divergencia por (semilla, variante) que altera decisión, velocidad o ruta, con ambas partidas empezando el paso en la misma celda y con la misma batería; «directa_codigo» son las divergencias que solo cambian el código de motivo (se cuentan aparte y no cuentan como directa); «consecuencia» es el resto. Se omiten las filas de fin de partida. Traza: 1403 filas (`docs/TRAZA_DIVERGENCIAS_exigente.csv`, regenerada en la tanda de ev3-d64).

| técnica (variante) | semillas con directa real | filas totales | directas | directa_codigo | consecuencia |
|---|---|---|---|---|---|
| RNA (sin_rna) | 3 de 20 (4, 10 y 18) | 110 | 3 | 0 | 107 |
| difuso (sin_difuso) | 20 de 20 | 781 | 20 | 0 | 761 |
| Orden de sitios: vecino más cercano (sin_ag) | 12 de 20 (3-9, 11-14, 17) | 512 | 12 | 0 | 500 |

Qué cambia en las filas directas:
- RNA: 3 directas, todas con `V-RNA-OBSTACULO` y cambio de decisión, velocidad y ruta: semilla 4 paso 2, semilla 18 paso 2 (las mismas dos de la medición anterior) y semilla 10 paso 22 (nueva en esta regeneración; su causa no está verificada). Las 4 filas `directa_codigo` de la medición anterior (semillas 2, 4, 12 y 13) ya no aparecen en esta traza: 0 `directa_codigo`; no lo hemos investigado. Las semillas 4 y 18 cuestan +3 y +1 pasos, y ninguna de las tres cambia el éxito ni las colisiones de la RNA en esta tabla.
- Difuso: 20 directas (una por semilla); todas cambian la velocidad. Motivo: reglas difusas activadas en el híbrido (R4 en la mayoría).
- Orden de sitios (sin_ag, vecino más cercano en lugar de la permutación más corta): 12 directas, todas en la fila de paso 0 por el orden de sitios del plan inicial; todas cambian la ruta. No mide el aporte del AG.

Sobre la RNA, lo medido: en esta regeneración cambia una decisión en 3 semillas de 20 (4, 10 y 18). En el resultado final, `hibrido` y `sin_rna` dan 20/20 y las mismas colisiones (0 en ambas); la RNA no cambia el éxito en esta tabla. Si M2 queda demostrado para la RNA en estos términos lo decide el Maestro.

Tabla de atribución (exigente, 4 variantes originales, 20 semillas). Método: A = copia guardada pre-ARX-90; B = exigente con `fisica_velocidad=False` sobre el código actual (90+91); C = JSON regenerado (todo). 90+91 = A→B; 28c = B→C.

| causa | filas con cambio | cambios de éxito | delta colisiones |
|---|---|---|---|
| 90+91 (A→B) | 28 | hibrido s7 y sin RNA s7: SIN_RUTA → EXITO | 0 en total |
| 28c (B→C) | 73 | sin difuso s1, s5, s8, s11, s16 y sin AG s13: EXITO → FRACASO | +1 (sin difuso s11) |
| total (A→C) | 73 | 8 | +1 |

Inferencia por resta, no medida fila a fila: 90 frente a 91 por separado. La corrida de ARX-91 (contra la base que ya incluye 90) dio −1 colisión en el exigente; por resta, 90 aporta +1 y 91 aporta −1, y su suma es 0 en A→B. No se ha medido cada uno por separado.

Casos concretos de 28c:
- `sin_ag` s13 (EXITO con 28c apagado, 67 pasos → FRACASO con 28c, 78 pasos): cinco resbalones (pasos 13, 14, 27, 30 y 57, con 1 % de batería cada uno) y la batería llega a 0. Es el coste de batería de 28c; no hay colisión.
- `sin_difuso` s11 (EXITO con 28c apagado, 50 pasos → FRACASO con 28c, 72 pasos, con 1 colisión en el paso 46): seis resbalones (pasos 14, 20, 21, 26, 41 y 43); la colisión llega tres pasos después del resbalón del paso 43, y la batería termina en 0. La explicación de QA (17/11, `pedidos\2026-11-17_qa_arx28\ARX-28c_qa.md`, y el diagnóstico de ARX-90 para la semilla 20): el resbalón restaura posición y ruta de forma consistente, y la colisión es una lectura ruidosa que sitúa un obstáculo no detectado una celda más lejos; es el mismo mecanismo que la semilla 20 de ARX-90 (sin difuso no se detiene). Explicación de QA; no verificada por nosotros fila a fila.
- Explicación de QA para la RNA, semilla 10 (`repro\s10_rna.py` en `pedidos\2026-11-17_qa_arx28\`): tras ARX-91, cuando el obstáculo está en la ruta, `V-OBSTACULO-EN-RUTA` reemplaza la decisión de la RNA en el propio híbrido (`integracion.py:190-199`). Por eso los vetos de la RNA que sobreviven son solo los de obstáculos vistos fuera de la ruta, como en la semilla 10, y por eso la RNA no cambia éxito ni colisiones. No verificada por nosotros fila a fila.

Hallazgo de QA (17/11/2026), sin suavizar: en la semilla 7 el híbrido PERDÍA (`SIN_RUTA` en el paso 18, tras paradas por `D-DIFUSO-LENTO`) y `sin_difuso` la ganaba. Tras ARX-90 el híbrido y `sin_rna` ganan la semilla 7 (EXITO en 53 pasos). En este escenario el difuso puede empeorar el resultado, como en la semilla 7 antes de ARX-90.

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

Para el informe (M2): la RNA queda con el resultado negativo de 28f. Con el escenario exigente, la RNA cambia una decisión en 3 de 20 semillas (4, 10 y 18), sin cambiar éxito ni colisiones. La explicación probable es la redundancia: la RNA casi no aporta información que el supervisor no tenga por el sensor de borde.

## Regeneración única: método de atribución, ARX-91 y constantes de 28c

### Método de atribución (90 + 91 y 28c)

La regeneración cambió tres cosas a la vez: ARX-90 (la percepción no marca como riesgo los sitios pendientes, el inicio ni el refugio; ev3-d65 A), ARX-91 (el chequeo de obstáculo en ruta pasa a ser incondicional; ev3-d68 B) y ARX-28c (resbalón por velocidad en pendiente; ev3-d54 A). Para separar sus efectos se comparan tres versiones del exigente, con las mismas 20 semillas y las cuatro variantes:

- **A**: copia guardada antes de ARX-90 (línea base).
- **B**: el exigente con `fisica_velocidad=False` sobre el código actual. Recoge ARX-90 y ARX-91, sin ARX-28c.
- **C**: el JSON regenerado, con todo.

Así, 90 + 91 es el efecto de A a B, y 28c es el de B a C. La bandera `fisica_velocidad` es lo que separa B de C: `ESCENARIOS["exigente"]` la enciende (`juego/comparacion.py`), y `Partida` la deja apagada por defecto (`juego/partida.py`). El congelado no la usa. Los recuentos de cada paso están en la tabla de atribución de la sección «Resultado de 20 semillas»; aquí no se repiten.

### ARX-91: el chequeo de obstáculo en ruta

En `ab46b4a` (la base del proyecto al entrar a control de versiones), el chequeo de obstáculo en ruta solo corría si el difuso había parado el rover (`dec.accion == "detener"`, `integracion.py:196`). Desde `944296d` (ev3-d68 B) es incondicional, tanto en `Mision` (`integracion.py:196-198`) como en la sombra que usa `Partida` (`juego/partida.py:492-494`).

Por qué: con la condición, la ablación «sin difuso» medía también una política oculta. Con el difuso apagado el rover nunca se paraba, así que el chequeo no corría. Con el chequeo incondicional, la ablación quita solo el difuso.

Efecto sobre la RNA: en el híbrido, cuando el obstáculo está en la ruta, el chequeo reemplaza la decisión de la RNA (ver INFORME §4.2).

Riesgo conocido, documentado en el código (docstring de `ARX-90` en `juego/partida.py`): una lectura ruidosa que sitúa el obstáculo una celda más lejos puede causar colisión. El ejemplo está en el exigente, semilla 20, sin difuso, paso 31.

Nota de procedencia: el mensaje del commit `944296d` dice «desde ARX-91 (ab46b4a)», que es inexacto. Los comentarios se corrigieron en `603af29`.

### Constantes del resbalón (ARX-28c, ev3-d69 A)

Se fijaron antes de medir (ev3-d69 A) y no se ajustan tras ver las cifras. Cada una tiene su justificación:

| Constante | Valor | Justificación |
|---|---|---|
| `INCLINACION_RESBALON` | 20° | Pendiente sobre la que la tracción de las ruedas deja de ser segura. Valor del plan («p. ej. 20°»). Supuesto de simulación |
| `P_RESBALON` | 0,5 | La probabilidad de resbalar por avance es `P_RESBALON × velocidad`: el riesgo de perder agarre crece con la velocidad. El factor 0,5 es un supuesto |
| `COSTO_RESBALON` | 1 % de batería | Esfuerzo extra de las ruedas al patinar y reanudar el avance. Supuesto |
| `VELOCIDAD_SIN_RESBALON` | 0,3 | Por debajo de esta velocidad el avance es lento y no resbala (umbral del plan, v < 0,3) |

El resbalón usa su generador propio (semilla `[semilla, 1317]`) y no altera los demás.

La variante «sin difuso» usa velocidad fija 0,5 (`integracion.py:186`, rama `if not self.usar_difuso`), que es el punto medio del rango. Según ev3-d69 A, QA verifica que no pierda por cableado.

**Sensibilidad publicada completa.** Rejilla 3×2: `P_RESBALON` en {0,25; 0,5; 0,75} y `COSTO_RESBALON` en {1; 2}, con 20 semillas y las cuatro variantes. Se genera con `scripts/rejilla_resbalon.py` en `docs/REJILLA_RESBALON_exigente.json` y `.csv`. Los valores fijados no cambian por lo que muestre la rejilla.
