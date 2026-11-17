# Plan RNA-aporte · Que la RNA aporte información que el resto del sistema no tiene

Planner: `Esp_Planner`, 2026-11-17 (borrador 08:3x, pausado por consumo; completado 12:17–12:45). Base de referencia `feat/integracion-rover` (`ac22f5f`); `main` está en `029e5cd` y `rna.py` es idéntico en ambas. Pedido del usuario (08:25): «veamos como podemos reparar». Criterio de éxito fijado antes de medir (ev3-d63 A y el encargo): recall de barrancos **sin** el rasgo `borde_barranco`; en 20 semillas, apagar la RNA cambia decisión, velocidad o ruta en al menos 5; informar si cambian colisiones o éxito; conservar o reportar completas las métricas de M5 y M6. Tope: congelación de código a las 19:00; la RNA es prioridad 4 (Maestro, 08:26). Esta ficha la responde el Maestro por delegación.

## 1. Encargo y alcance

Diseñar cómo la RNA podría aportar algo que el supervisor no tenga ya, medir fuera de línea si es posible en este simulador, y dejar al Maestro una ficha con números y costos para decidir si cabe antes de las 19:00 o queda como limitación documentada. Sin tocar código del repo: los dos scripts de medición están en `docs/planes/RNA_aporte_medicion.py` y `RNA_aporte_medicion_2.py` (sin versionar), parchean `generar_mundo` en memoria y no escriben nada.

## 2. Estado actual (evidencia reunida antes de medir)

- **Recall sin borde = 0,000** en las cuatro mediciones de 28f (`docs/planes/ARX-28_calibracion.md:118-135`): con rasgos normales 0,70–0,80; sin `borde_barranco`, 0 predicciones de barranco sobre 250 y 135 barrancos de test. La RNA depende por completo de ese rasgo, que es el mapa real sin ruido (`simulador.py:160-167`) y que el supervisor ya usa antes que ella (`integracion.py:45` frente a `:47-50`).
- **M2 medido tras ARX-91** (`pedidos/2026-11-17_rover_cola_continua/TEXTO_M2_INFORME.md`): la RNA altera decisiones en 3 de 20 semillas del exigente (4, 10, 18), solo con obstáculos fuera de la ruta; no cambia éxito ni colisiones.
- **Por qué no hay señal propia:** los rasgos son proximidad (sensor, también lo usa el supervisor), borde (mapa real), gradiente y vibración (`rna.py:23-40`). El gradiente **no informa de un barranco**: la elevación de `generar_mundo` es una suma acumulada suave que no baja en las celdas BARRANCO (`simulador.py:112`). La vibración separa barranco de libre en 0,2 con ruido σ 0,3 (`rna.py:20, 34`). En este simulador un barranco es solo una etiqueta de tipo, sin firma física medible a distancia.
- **Horizonte:** la RNA clasifica la celda de enfrente (`rna.py:27-30`), el mismo horizonte que el LIDAR de borde. Aunque su recall fuera perfecto, con el borde encendido el supervisor llega antes (misma celda, veto previo, `integracion.py:45`). Para aportar información que nadie tiene, la RNA necesita **o una firma física que el borde no ve, o un horizonte mayor (dos celdas)**.
- **Mapa estimado:** el rover nace con el 80 % de los peligros ya marcados (`genetico.py:24-36`, `p_detectar = 0.8`); el 20 % restante se descubre al llegar al lado (borde → `riesgo = 1,0`, `integracion.py:175-176`). Ahí, y solo ahí, una alerta a dos celdas cambiaría la ruta antes que el LIDAR.
- **Entrenamiento:** `rna_entrenada()` (`integracion.py:57-61`): 30 mapas, 300 muestras por mapa, MLP (32, 16) con parada temprana; `evaluar` da matriz, macro-F1, recall de barranco, línea base y ECE (`rna.py:102-121`). Pruebas en `tests/test_rna.py` (6).

## 3. Medición corta fuera de línea (12:20, 17 s de CPU en total, sin turno)

Mismo tamaño que `rna_entrenada()` (30 mapas, partición por mapas 70/15/15, 300 muestras por mapa, semilla 42). «Desnivel» = bajar la elevación de las celdas BARRANCO en `generar_mundo` (firma física); «sin borde» = la RNA entrena con proximidad, gradiente y vibración, sin `borde_barranco`.

**Horizonte 1 (la celda de enfrente), test de 5 mapas (14 barrancos, n = 1401):**

| Mundo | Con borde (4 rasgos) | Sin borde | Falsos positivos sin borde |
|---|---|---|---|
| Actual (desnivel 0) | 0,786 | **0,000** | 0 |
| Desnivel −1 m | 1,000 | 0,071 | 1 |
| Desnivel −3 m | 1,000 | **1,000** (14/14) | 2 |
| Desnivel −3 m, ruido del gradiente ×10 (σ 0,5) | — | 1,000 | 1 |

**Horizonte 1, test grande de 20 mapas no vistos (semillas 100–119; 57 barrancos, n = 5558):**

| Desnivel | Con borde | Sin borde | Falsos positivos sin borde | macro-F1 sin borde |
|---|---|---|---|---|
| −1 m | 0,895 | 0,088 (5/57) | 6 | 0,684 |
| −2 m | 0,982 | 0,561 (32/57) | 11 | 0,858 |
| −3 m | 1,000 | **0,842 (48/57)** | 4 | 0,950 |

**Horizonte 2 (la celda a dos pasos, con la de enfrente libre: alerta temprana; test 5 mapas, 15 barrancos, n = 1214):**

| Mundo | Recall barranco | Falsos positivos |
|---|---|---|
| Actual (desnivel 0) | 0,000 | 0 |
| Desnivel −3 m, altímetro a 2 con ruido σ 0,05 | **0,667 (10/15)** | 0 |
| Desnivel −3 m, ruido σ 0,5 | 0,600 (9/15) | 0 |

Otros datos: celdas LIBRE vecinas a un barranco en los 5 mapas de test: 206 de 3000 (6,9 %). ECE entre 0,010 y 0,018 en todas las filas (la calibración no empeora). La partición de test de 30 mapas tiene solo 14 barrancos: por eso se repitió con 20 mapas; las cifras del test grande son las que valen.

**Lectura:** la RNA sí puede aprender barrancos del terreno, sin copiar el mapa, si el barranco tiene una firma física clara (−3 m: 0,84; −2 m ya cae a 0,56; −1 m no sirve). Con esa firma también es posible una alerta **a dos celdas** (0,67 sin falsos positivos), que hoy nadie da: el LIDAR de borde solo ve los vecinos. Lo que **no** cambia con la firma sola: si la RNA sigue mirando la celda de enfrente, el veto de borde se dispara antes (`integracion.py:45`) y en el juego solo se verían sus falsos positivos; la divergencia en 20 semillas seguiría cerca de 3/20.

## 4. Propuesta

Tres piezas, en orden; cada una vale por sí sola y la ficha decide hasta dónde se llega.

- **(a) Firma física del barranco.** En `generar_mundo` las celdas BARRANCO quedan 3 m por debajo de la elevación suave (`elevacion[tipo == BARRANCO] -= 3.0`, una línea tras `simulador.py:112`). Efectos colaterales, medidos o acotados: el rover nunca pisa un barranco (la física lo impide), así que el resbalón de 28c (`partida.py:1044`, elevación real entre dos celdas pisadas) no cambia; la inclinación que entra al difuso (`integracion.py:180`, `|gradiente| × 20`, saturada a 45°) pasa a ser 45° solo en el paso en que el rover **mira de frente** a un barranco, paso que el veto de borde ya convierte en replanificación; el gradiente ruidoso de la RNA en esas celdas vale ≈ −3. El mapa estimado, las rutas y la garantía no dependen de la elevación. Cambia las cifras de M5/M6 (se regeneran a las 19:00 igual) y, en principio, nada del congelado: se verifica (sección 8).
- **(b) La RNA sin `borde_barranco`.** `NOMBRES_RASGOS` y `_rasgos_celda` quedan con 3 rasgos (proximidad, gradiente, vibración); el supervisor conserva su veto de borde con el LIDAR (`integracion.py:45`), que es sensor y no RNA. La RNA deja de ser un espejo del mapa: recall esperado 0,84 (medido), falsos positivos 4 de 5558 (0,07 %). `explicar()` y `/rna` muestran 3 entradas. M5/M6 se reportan con la matriz nueva.
- **(c) Alerta temprana a dos celdas.** Rasgo nuevo `desnivel_a_2` (altímetro frontal: elevación de la celda a distancia 2 menos la actual, ruido σ 0,05, NaN si está fuera del mapa) y la RNA predice **la celda a dos pasos**; en el paso de la misión, si `p(barranco)` o `p(obstáculo)` de esa celda supera `UMBRAL_RIESGO_RNA` (0,5) y `riesgo[celda] < 0,5`, se marca `riesgo[celda] = max(riesgo, p)` **sin veto nuevo**: la planificación (BFS/AG sobre `riesgo < 0,5`) la evita un paso antes de que el LIDAR la vea y de que `V-RUTA-CON-RIESGO` obligue a replanificar parado. Donde el mapa estimado ya la conocía (80 %), no pasa nada. Es la única pieza que puede mover M2: divergencia esperada solo en las semillas donde la ruta pasa junto a un barranco **no** cartografiado (≈ 1,2 por mapa). No se garantiza llegar a 5/20: se mide y se publica tal como salga (regla de ev3-d63).

Dónde va (c): preferible en `Mision.paso` (`integracion.py:169-176`, junto a `_actualizar_mapa_estimado`), porque 92c no toca `integracion.py` (COLA, ajuste 12:30: 92c = `genetico.py`, `partida.py`, `servidor.py`); la alternativa de envolver la instancia en `Partida` chocaría con 92c en `partida.py`. La sombra de `partida.py:544` y `:1092` (modo sonda) reutiliza `_actualizar_mapa_estimado`, así que la marca a dos celdas conviene ponerla dentro de un método propio `_marcar_riesgo_rna(celda, probs)` que la sombra también llame, o declarar en el plan de QA que la sonda no la usa.

**Recomendación del Planner:** por prioridad (4) y calendario, el **piso** es documentar la limitación con estos números (opción C de la ficha, 0,5 h de Esp_Docs, sin código). La opción A (a + b + c) es la única que puede cambiar M2 y cabe solo si se abre como segundo frente a las 15:00, cuando cierre 92d; si a las 15:00 no hay hueco, se cae a C sin discusión. La opción B (a + b) mejora la honestidad de M5/M6 a bajo costo pero no mueve M2; no la recomiendo sola: gasta la ventana sin tocar lo que el informe necesita.

## 5. Tareas (nueva ARX-93, rama `feat/arx-93-rna-terreno` desde la punta de integración que indique el líder)

| Tarea | Qué | Archivos | Pruebas | Costo |
|---|---|---|---|---|
| 93a | Firma física: barrancos 3 m bajo la elevación suave (pieza a) | `simulador.py` (generar_mundo, 1 línea) | `tests/test_simulador.py`: nueva prueba «las celdas BARRANCO están ≥ 2,5 m por debajo de sus vecinas libres»; la suite entera debe seguir en verde (el congelado no cambia: sección 8) | 0,5 h |
| 93b | RNA sin borde (pieza b): 3 rasgos; `explicar`, `/rna` y la bitácora con 3 entradas | `rna.py`, `api/servidor.py` (solo si serializa los nombres), `api/static/*.js` (si el panel de la RNA lista rasgos fijos) | `tests/test_rna.py`: recall sin borde ≥ 0,7 en test de 20 mapas (umbral escrito ahora, bajo el 0,84 medido); `test_explicacion_contiene_evidencia` con 3 rasgos; prueba de la API `/rna` | 1 h |
| 93c | Alerta a dos celdas (pieza c): rasgo `desnivel_a_2`, etiqueta de la celda +2, marca de riesgo sin veto nuevo, motivo en la bitácora (`RNA-RIESGO-2`) para M3 | `simulador.py` (SensorSuite: altímetro a 2), `rna.py`, `integracion.py` (paso) | `tests/test_integracion.py`: con una RNA falsa que devuelve p = 0,9 para un barranco no cartografiado a dos celdas, el riesgo queda marcado y la ruta lo evita; con el borde encendido los vetos no cambian | 1,5 h |
| 93d | Medición de 20 semillas, congelado y exigente, híbrido frente a `sin_rna` (`juego/comparacion.py`, `traza_divergencias.py`), con turno del Orquestador: divergencias de decisión, velocidad o ruta; colisiones y éxito; M5/M6 con y sin borde (test de 20 mapas); publicación tal como salga | `docs/` (cifras) | QA verifica que las divergencias vengan de `RNA-RIESGO-2` | 0,5 h + ~3 min de CPU |
| 93e | Si las divergencias son < 5/20: cierre negativo con los números; si ≥ 5/20: texto de M2 por técnica actualizado | `TEXTO_M2_INFORME.md`, `docs/META.md` | Esp_Docs | 0,5 h |

Total opción A: ~4 h de agente + QA (~1 h) → de 15:00 a 19:00 **sin margen**. Opción B (93a + 93b + M5/M6): ~2 h + QA. Opción C: 93e en su versión negativa, con los números de la sección 3: 0,5 h, sin código, sin QA de código.

## 6. Paralelismo

- Archivos de ARX-93: `simulador.py`, `rna.py`, `integracion.py`, `tests/test_rna.py`, `tests/test_simulador.py`, `tests/test_integracion.py`, quizá `api/servidor.py` y un JS del panel de la RNA.
- **Compatible por archivos con 92c** (`genetico.py`, `partida.py`, `servidor.py`) salvo `api/servidor.py` si 93b lo toca: dejar `/rna` para el final y rebasar. **Compatible con 92d** (`comparacion.py`, su prueba y el script); 93d solo **lee** `comparacion.py`.
- **Incompatible en `integracion.py` y `simulador.py`** con ramas aún sin integrar: `feat/arx-33-31-83-motor`, `feat/arx-80-bitacora`, `feat/arx-92a`, `feat/integracion-rover`, `feat/api-28d-47a` (todas difieren de `main` en esos archivos). Por eso ARX-93 debe salir de la **punta de integración** (donde ya estén 79 y 92a), no de `main`, y entrar después de ellas: es la prioridad 3 del Maestro antes que la 4.
- Es un **tercer frente** si 92c y 92d siguen abiertos: la regla de dos frentes por proyecto obliga a esperar al cierre de 92d (~15:00 según COLA). La medición 93d usa turno.
- La regeneración de cifras de las 19:00 absorbe M5/M6 nuevos; si A entra, hay que decirlo antes de lanzar la regeneración.

## 7. Ficha (ev3-d78, en `RNA_aporte_fichas.json`, lista para cargar)

Título: «ARES-X (RNA): sin el rasgo de borde la RNA no ve ningún barranco; con una firma física de −3 m vería el 84 % y podría alertar a dos celdas. ¿Se hace antes de las 19:00 o se documenta?». Opciones: **A** alerta temprana completa (a + b + c + medición), condicionada al hueco de las 15:00, ~4 h + QA, única que puede mover M2 (no garantizado; se publica tal como salga); **B** solo firma física y RNA sin borde, ~2 h + QA, M5/M6 honestos, M2 sin cambio; **C** documentar la limitación con los números medidos, 0,5 h, sin código. Recomendada: **C** como piso, con A solo si hay hueco a las 15:00 (y en ese caso la decisión de A ya está tomada: no hace falta otra ficha).

## 8. Verificación

- **El congelado no cambia con (a) y (b):** antes de abrir el PR, `comparacion_politicas.py` del escenario congelado, 20 semillas, híbrido: pasos, batería, colisiones y éxito idénticos a la rama base, salvo en las semillas donde la RNA cambiaba una decisión por un falso positivo; QA lista esas semillas. Si cambia algo más, la causa se explica o 93a se retira.
- **Umbral escrito antes de medir:** recall sin borde ≥ 0,7 en test de 20 mapas (medido hoy 0,842); recall a dos celdas ≥ 0,5 (medido 0,667); falsos positivos ≤ 0,2 % de las lecturas (medido 0,07 %). Divergencia M2 ≥ 5/20 según ev3-d63; si no se alcanza, se publica el negativo con los números.
- **Vetos intactos:** `V-BORDE-BARRANCO` sigue antes que la RNA; ninguna prueba de `test_integracion.py` ni de `test_partida.py` cambia de resultado.
- **Sonda y bitácora:** `/historial.csv` y la bitácora muestran `RNA-RIESGO-2` con la celda y la probabilidad (M3, M7).
- **Suite completa y CPU/RAM < 80 %** durante 93d, con turno.

## 9. Texto de la limitación (para la opción C, y como párrafo de M2 si A no alcanza 5/20)

«La RNA de percepción reconoce barrancos con recall 0,70–0,80, pero solo gracias al rasgo `borde_barranco`, que es la misma lectura del LIDAR que el supervisor usa antes que ella; sin ese rasgo no predice ninguno (0 de 250 y 0 de 135). La causa es del simulador, no del modelo: un barranco es una etiqueta sin firma física (la elevación no baja en esas celdas y la vibración apenas lo distingue). Medimos fuera de línea qué haría falta: con un desnivel de −3 m la RNA sin borde alcanza recall 0,842 (48 de 57, 4 falsos positivos en 5558 lecturas) y puede anticipar un barranco a dos celdas con recall 0,667 sin falsos positivos, algo que ningún otro módulo da. Esa modificación del mundo (ARX-93) queda fuera de esta entrega por prioridad y plazo; con el mundo actual la RNA es redundante con el supervisor y así se reporta en M2.»

## Dónde quedé

- 17/11 08:3x · Evidencia (§2) y esbozo. Pausado por consumo (84 %).
- 17/11 12:45 · Medición hecha (§3, 17 s de CPU), plan completo (§4–§9), ficha ev3-d78 en `RNA_aporte_fichas.json`. Informe enviado al Orquestador. Falta solo lo que decida la ficha.

## 10. Cierre de ARX-93 (C+, decisión del Maestro, sin 93d)

Rama `feat/arx-93-rna`. Solo código detrás de banderas apagadas y esta sección; no se mide 93d.

**Qué queda y qué no**

- 93a (firma física −3 m) y 93b (RNA sin `borde_barranco`): se quedan, detrás de `simulador.FIRMA_BARRANCO_ACTIVA` e `integracion.RNA_APORTE_ACTIVA`, ambas apagadas. `aporte_rna(True)` las enciende juntas.
- 93c (alerta a dos celdas): **descartada**. Queda el código con `ALERTA_RNA_2_ACTIVA = False`, comentado como no usado; no se enciende ni con el aporte activo.
- Pendiente no hecho: `/rna` y el panel (`laboratorio.js`) con la lista de rasgos del modelo activo, que iba al final y depende de que cierre 92c.

**Métricas del modelo terreno (aparte del actual; M5/M6 siguen con el modelo actual)**

Una sola corrida, no el protocolo de 93d: firma física encendida, 60 mapas (partición 70/15/15, 400 muestras por mapa), semilla 42, prueba en 20 mapas no vistos (semillas 100–119). Matriz de confusión, filas = real y columnas = predicho (libre, obstáculo, barranco):

| Real \ Predicho | libre | obstáculo | barranco |
|---|---|---|---|
| libre | 6890 | 0 | 2 |
| obstáculo | 4 | 416 | 14 |
| barranco | 2 | 8 | 63 |

macro-F1 0,933; recall de barrancos 0,863 (63 de 73); umbral previo ≥ 0,7. En el mundo actual (sin firma) este mismo modelo no ve ningún barranco (0 de 250 y 0 de 135, §3). Estas cifras valen solo con la bandera encendida.

**Hallazgos que descartan 93c**

1. **El sensor de proximidad ya lo ve.** `SensorSuite.leer` devuelve la primera celda no libre en línea hasta 20 celdas y `_actualizar_mapa_estimado` la marca; con ARX-91, `V-OBSTACULO-EN-RUTA` replanifica sin la RNA. Con la bandera apagada, un barranco real a 2 celdas sobre la ruta queda en riesgo 1,0 y el paso registra `V-OBSTACULO-EN-RUTA`. La premisa de §4(c), «antes de que el LIDAR la vea», no vale: el LIDAR de borde son los cuatro vecinos, pero el de proximidad llega a 20.
2. **El recall de 0,667 dependía de la vibración de la celda a 2.** El rover no puede medirla a distancia; el simulador la genera según la clase. Reproducido (60 mapas de entrenamiento, 20 de prueba): con vibración, recall 0,727; sin ella 0,000, y la vibración sola también 0,000; el desnivel a 2 solo no lo aprende el MLP (barrancos 0,9 % de las muestras). Usarla sería una política oculta.

**Para QA liviano**

- Con las dos banderas apagadas: 20 semillas del escenario por defecto (bitácora completa más resumen), SHA-256 abreviado `6e49858a300c58e6` en la rama base `ac22f5f` y en esta rama.
- `python -m pytest -q tests/test_integracion.py tests/test_rna.py tests/test_simulador.py`: 37 de 37. Suite completa, congelado y exigente: no corridos.
- La limitación para el informe es el texto de §9.
