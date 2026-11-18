# Plan · Rediseño de sensores y diseño del juego (ARX-94, ARX-29, ARX-50/51/57, ARX-59)

Planner: `Esp_Planner`, 2026-11-17 (22:00–). Base `main` = `a0bf109` (lo publicado). Rama `docs/plan-sensores`. Decisión del usuario (17/11 ~22:05): «Vamos con las tareas de diseño y el rediseño de qué ve cada sensor para que no sea redundante la red neuronal». Se escribe y confirma por partes: **1** rediseño de sensores (primero; M2 y M7 para la RNA), **2** diseño (ARX-29, 50, 51, 57, 59), **3** paralelismo y plan de regeneración. Fuentes: `docs/planes/RNA_aporte.md` (§3 y §10, cierre C+ de ARX-93), `docs/PLAN_PLANETAS.md`, `docs/planes/META_brechas.md`, el cuadro de la meta del 17/11 y la cola del proyecto. Las fichas las responde el Maestro por delegación; cada una trae evidencia medida, criterios M por opción y costo.

Scripts de medición de este plan (solo lectura del repo, parchean el mundo en memoria): `docs/planes/PLAN_sensores_medicion_1.py` y `_2.py`.

---

## Parte 1 · Rediseño de sensores (ARX-94)

### 1.1 Qué ve cada sensor hoy y por qué la RNA es redundante

| Lectura (`simulador.py`, `SensorSuite.leer`; `rna.py`, `_rasgos_celda`) | Qué hace hoy | Problema físico |
|---|---|---|
| `proximidad_frontal_m` | Distancia a la primera celda **no libre** en línea, hasta 20 celdas (ve obstáculos **y barrancos**) | Un haz de distancia rebota en un volumen que sobresale; **no ve un hoyo**. Hoy el barranco lejano lo detecta el sensor de proximidad, y con ARX-91 `V-OBSTACULO-EN-RUTA` replanifica solo: por eso la alerta a dos celdas de ARX-93c resultó redundante (RNA_aporte §10). |
| `borde_barranco` / `celdas_barranco` | Tipo real de las 8 celdas vecinas, **sin ruido** | Es el mapa verdadero, no una medición. La RNA lo recibe como rasgo y aprende a copiarlo: sin él su recall es 0,000 (28f). El supervisor lo usa antes que la RNA (`integracion.py:59-62`). |
| `gradiente_altura_m` | Elevación de la celda siguiente menos la actual, ruido σ 0,05 | La medición es física, pero el **relieve** no: `generar_mundo` suma ruido por fila de forma independiente (`np.cumsum(..., axis=1)`), así que dos vecinos norte-sur difieren en 0,67 m de mediana y hasta 6 m (medido, 1.2). El desnivel natural tapa cualquier señal del barranco, que además hoy no tiene profundidad. |
| `vibracion` | Media según la **clase de la celda de enfrente** + ruido | Un rover no puede medir la vibración de una celda que no pisa: es una política oculta (la misma que descartó 93c). La vibración física es la de la celda actual (IMU) e informa del tipo de suelo que se pisa. |
| `altimetria_m` | Elevación propia con ruido | Correcta (barómetro/IMU). Nadie la usa para decidir. |
| Mapa estimado (`genetico.mapa_estimado`) | El 80 % de los peligros nace marcado (`p_detectar = 0.8`) | Equivale a un mapa orbital previo; aceptable si se declara, pero hoy ve igual de bien obstáculos grandes y barrancos de cualquier tamaño. |

Conclusión: la RNA es redundante porque **todo lo que ella podría inferir ya llega como lectura exacta** (borde) o lo ve otro sensor a mayor alcance (proximidad). No es un problema del modelo sino del simulador.

### 1.2 Hallazgo del relieve (medido, 20 mapas, `PLAN_sensores_medicion_2.py`)

| Vecinos | mediana |desnivel| | p90 | máximo |
|---|---|---|---|
| norte-sur | 0,67 m | 1,90 m | 6,05 m |
| este-oeste | 0,13 m | 0,33 m | 0,80 m |

El 8,5 % de los pares norte-sur difiere en más de 2 m. Con este relieve, un veto por desnivel a −2 m daría cientos de falsos positivos (211 en 7402 lecturas, medición 1) y la RNA con [proximidad, desnivel, vibración] no aprende (recall 0,12). **Cualquier rediseño de sensores exige antes un relieve 2D suave**; con el actual no hay sensor físico de desnivel que sirva.

### 1.3 Medición del diseño propuesto (fuera de línea, 9 s de CPU, 60 mapas de entrenamiento, 20 de prueba no vistos, 7402 lecturas, 73 barrancos)

Mundo v2: relieve suave 2D (ruido gaussiano filtrado, desviación 1,5 m, suavidad 3 celdas) y barrancos con profundidad propia U(1, 4) m. Sensores: telémetro frontal de obstáculos (ruido como hoy), telémetro inclinado que mide el desnivel de la celda siguiente (σ_t), cámara que da un contraste óptico de la celda siguiente (hoyo en sombra → oscuro proporcional a la profundidad; roca → claro; suelo → 0; σ_c). Veto duro declarado: desnivel medido < −2 m.

| σ_t | cámara | Veto duro solo (recall / FP) | RNA (recall / FP / macro-F1 / ECE) | Barrancos que **solo** la RNA ve | Veto ∪ RNA |
|---|---|---|---|---|---|
| 0,3 | σ 0,4 | 0,699 / 2 | 0,740 / 5 / 0,936 / 0,007 | 3 (4,1 %) | 0,740 |
| 0,5 | σ 0,4 | 0,630 / 9 | 0,685 / 6 / 0,923 / 0,007 | 7 (9,6 %) | 0,726 |
| 0,5 | σ 0,6 | 0,630 / 9 | 0,644 / 5 / 0,914 / 0,012 | 4 (5,5 %) | 0,685 |
| 0,5 | sin cámara | 0,630 / 9 | 0,589 / 5 / 0,902 / 0,044 | 0 (0 %) | 0,630 |
| 0,8 | σ 0,6 | 0,658 / 96 | 0,548 / 8 / 0,886 / 0,015 | 1 (1,4 %) | 0,671 |

Lectura honesta:
- Con sensores físicos y ruidosos la RNA **sí aporta algo propio**: fusiona dos señales que por separado no bastan y cubre entre un 4 y un 10 % de los barrancos que el veto duro no ve (los de 1 a 2 m de profundidad), con menos falsos positivos que el veto. Sin la cámara, la RNA es un umbral aprendido sobre el telémetro: redundante por construcción (0 %).
- El aporte es **pequeño**: con el mapa orbital al 80 %, en el juego solo el 20 % de los barrancos es desconocido, y de esos la RNA decide sola en ~1 de cada 10. Esperado: menos de un barranco por partida donde la RNA cambie algo. **El criterio previo (≥ 5 de 20 semillas con cambio de decisión, velocidad o ruta) está en riesgo con el rediseño solo.** Lo que lo haría alcanzable, con justificación física: que el mapa orbital previo no vea barrancos poco profundos (p. ej. `p_detectar` 0,8 para obstáculos y para barrancos de más de 2 m; 0,3 para los de menos de 2 m), porque una imagen orbital resuelve relieve grande, no grietas. Eso multiplica por ~3 las celdas donde la RNA es la única fuente. Es un supuesto de simulación más, declarado, y va a la ficha.
- Lo que **no vale la pena**: la alerta a dos celdas (descartada en ARX-93, sigue descartada: el telémetro de obstáculos ya cubre la distancia y un hoyo a dos celdas no se ve con sensores de a bordo); un rediseño «solo de rasgos» sin tocar el relieve (medición 1: no funciona); una RNA con más capas o más datos (el límite es la señal, no el modelo).

### 1.4 Diseño propuesto

**Mundo v2** (`simulador.py`, `generar_mundo`): relieve suave 2D en vez de la suma por filas; cada BARRANCO con `profundidad` propia U(1, 4) m restada del relieve; cada OBSTACULO con `altura` U(0,3, 2) m (solo para la cámara y la escena). Nuevo arreglo `World.profundidad` (0 fuera de barrancos). `marcar_barranco` asigna profundidad con el generador del evento. Nada de esto depende de etiquetas: el sensor mide geometría.

**Sensores** (`SensorSuite.leer`, con la justificación física que exige la ficha):

| Lectura nueva | Qué mide | Qué no mide | Ruido (supuesto) |
|---|---|---|---|
| `proximidad_frontal_m` | Distancia al primer **obstáculo** (volumen) en línea, hasta 20 celdas | Hoyos, tipo de suelo | como hoy |
| `desnivel_frontal_m` | Elevación de la celda siguiente menos la actual (telémetro inclinado hacia el suelo de la celda contigua) | Celdas a más de una | σ 0,5 m |
| `desniveles_vecinos` | Lo mismo para las 8 vecinas (barrido lento del mismo telémetro); reemplaza `celdas_barranco` | — | σ 0,5 m cada una |
| `contraste_optico` | Cámara: claro/oscuro de la celda siguiente (sombra de un hoyo, cara de una roca), degradado de noche y en tormenta (×0,5 de señal, ×2 de ruido) | Celdas lejanas; nada en la noche sin luz | σ 0,4 |
| `altimetria_m` | Elevación propia | — | como hoy |
| `vibracion` | IMU de la **celda actual**: tipo de suelo que se pisa (hoy todas libres iguales → sin información; útil con los terrenos de ARX-51) | La celda siguiente | σ 0,3 |
| Mapa orbital previo (`mapa_estimado`) | Obstáculos y barrancos profundos con `p_detectar` 0,8; barrancos de menos de 2 m con 0,3 (opción A de la ficha) o 0,8 (opción B) | — | — |

Se eliminan `borde_barranco` (lectura exacta) y la vibración por clase de la celda de enfrente. Los eventos ya existentes conservan su efecto: la tormenta sube el ruido de todos los sensores; la noche degrada la cámara; la falla de sensor da NaN.

**Vetos** (`SafetySupervisor.decidir`): ningún peligro pierde cobertura; cambia la vía.

| Peligro | Hoy | Nuevo (vía declarada) |
|---|---|---|
| Barranco contiguo en la ruta | `V-BORDE-BARRANCO` por el tipo real | `V-BORDE-BARRANCO` si `desnivel_frontal_m < −2 m` (sensor); además `V-RNA-BARRANCO` si p(barranco) > 0,5 (fusión telémetro + cámara, banda de 1 a 2 m); y la física: `paso_fisico` **nunca** entra en un barranco (colisión +1 y replanificación), como hoy |
| Barranco vecino fuera de la ruta | `riesgo = 1,0` por el tipo real | `riesgo = 1,0` si su desnivel medido < −2 m; `riesgo = max(riesgo, p)` con la p de la RNA cuando mira hacia él |
| Barranco lejano en la ruta | Lo veía la proximidad (irreal) | Mapa orbital previo (0,8 o 0,3 según profundidad); los que falten se descubren al llegar al lado |
| Obstáculo en la ruta | `V-OBSTACULO-EN-RUTA`, `V-RNA-OBSTACULO` | Igual (la proximidad sigue viendo obstáculos) |
| NaN, batería, parado, celda bloqueada | Igual | Igual |

**RNA** (`rna.py`): rasgos `["proximidad_frontal_m", "desnivel_frontal_m", "contraste_optico", "vibracion"]` (4, como hoy; la vibración entra para que ARX-51 no cambie la arquitectura); etiqueta: tipo real de la celda siguiente, como hoy; mismo MLP (32, 16), misma partición por mapas, mismos reportes (`evaluar`: matriz, macro-F1, recall de barrancos, línea base, ECE). El **modelo actual se conserva** como perfil `"v1"` con su dataset (mundo v1 detrás de `MUNDO_V1`) y sus métricas publicadas; el nuevo (`"v2"`) se reporta completo en `/rna/evaluacion` y en el informe (M5, M6). `/rna` muestra entrada → normalizada → probabilidades → activaciones con los rasgos nuevos (M7) y el vínculo con el riesgo: la celda que la RNA marcó y con qué p.

**Difuso y AG**: sin cambios de código. La velocidad depende de la distancia al riesgo conocido en la ruta; con el riesgo blando de la RNA (`riesgo = p` en 0,5–1) esa distancia cambia en más pasos que hoy: es la vía por la que la RNA mueve la **velocidad** (cuenta como divergencia).

### 1.5 Congelado: dos caminos (ficha ev3-d84)

El rediseño cambia el mundo (relieve), así que **todas** las cifras (congelado, exigente, exigente de 10 sitios, traza, tabla de modos, rejilla, línea base por nivel, garantía) cambian. (A) **Regenerar con atribución**: una sola regeneración al cierre de la parte 1, tabla «antes → después» por métrica con la causa «mundo v2 + sensores», hash nuevo del congelado; el informe conserva la tabla publicada como «entrega del 17/11» y suma la nueva. (B) **Mantener el esquema viejo**: mundo v1 y sensores v1 detrás de `MUNDO_V1 = True` por defecto; el v2 solo en el laboratorio de la RNA y en una comparación aparte. B protege las cifras pero deja el juego con la RNA redundante, que es lo que el usuario pidió cambiar, y duplica caminos de código y pruebas. Recomiendo **A**, con la regeneración única del plan de la parte 3.

### 1.6 Tareas (ARX-94, rama `feat/arx-94-sensores` desde `a0bf109`, un solo frente)

| Tarea | Paso | Criterio de hecho | Archivos |
|---|---|---|---|
| 94a Relieve y profundidad | `generar_mundo` con relieve suave 2D, `profundidad` y `altura`; `marcar_barranco` coherente; `MUNDO_V1` para reproducir el mundo viejo en pruebas | Prueba: desnivel mediano entre vecinos N-S < 0,3 m y p90 < 0,8 m en 20 mapas; cada barranco 1–4 m bajo sus vecinos; con `MUNDO_V1` el mapa es idéntico al de hoy (hash de `tipo` y `elevacion`) | `simulador.py`, `tests/test_simulador.py` |
| 94b Sensores | `leer` con las lecturas de 1.4; `borde_barranco` y `celdas_barranco` desaparecen; tormenta y noche degradan según lo declarado; falla → NaN | Pruebas por sensor: la proximidad ignora barrancos; el desnivel tiene σ 0,5 y NaN fuera del mapa; la cámara se degrada de noche; ninguna lectura consulta `tipo` salvo para la geometría (revisión de código: `tipo` solo aparece en obstáculos de la proximidad) | `simulador.py`, `tests/test_simulador.py` |
| 94c Supervisor y mapa estimado | Vetos de la tabla de 1.4; `mapa_estimado` por profundidad (opción de ev3-d83); `riesgo = max(riesgo, p)` para la celda mirada; motivo `RNA-RIESGO:(celda):p` en la bitácora | Pruebas: barranco de 3 m contiguo → `V-BORDE-BARRANCO`; de 1,5 m con p > 0,5 → `V-RNA-BARRANCO`; de 1,5 m con p ≤ 0,5 → `paso_fisico` lo rechaza, colisión +1 y replanificación (nunca cae); obstáculo en ruta → igual que hoy | `integracion.py`, `genetico.py` (`mapa_estimado`), `tests/test_integracion.py` |
| 94d RNA v2 | Rasgos nuevos, perfiles `v1`/`v2`, `rna_entrenada()` entrena v2; v1 reproducible con `MUNDO_V1`; `/rna`, `/rna/evaluacion` y el panel con el modelo activo y su lista de rasgos | Umbrales escritos antes de medir: recall de barrancos v2 ≥ 0,6 y FP ≤ 0,2 % en 20 mapas no vistos (medido 0,685 y 0,08 %); ECE ≤ 0,03; macro-F1 v1 publicada sin cambios | `rna.py`, `integracion.py`, `api/servidor.py`, `api/static/laboratorio.js`, `tests/test_rna.py`, `api/tests/` |
| 94e Medición M2 | 20 semillas, congelado y exigente, híbrido frente a `sin_rna` con `juego/comparacion.py` y `scripts/traza_divergencias.py`; colisiones y éxito aparte; con turno | Se publica tal como salga: divergencias por semilla (decisión, velocidad, ruta), colisiones y éxito; si < 5/20, el informe lo dice y la ficha ev3-d83 fija qué sigue | `docs/` (cifras), `scripts/` |
| 94f Regeneración y docs | Según ev3-d84: regeneración única con atribución (parte 3) o esquema viejo; `INFORME_TECNICO.md` §RNA con v1 y v2, texto de M2 por técnica, `CONTRATOS_GRAFICOS.md` §4–§5 | Hash del congelado nuevo registrado; tabla antes/después; QA verifica que las divergencias vengan de `RNA-RIESGO`/`V-RNA-*` | docs |

Costo: 94a–94d ~6 h de agente; 94e ~15 min de CPU con turno; 94f 1–2 h de Docs; QA ~2 h. Un día de trabajo.

### 1.7 Verificación

- **Nada oculto:** revisión de código con un criterio escrito: ninguna lectura de `SensorSuite` ni rasgo de la RNA se construye a partir de `mundo.tipo` salvo la proximidad a obstáculos; todo lo demás sale de `elevacion`, `profundidad`, `altura` o del estado del rover.
- **Vetos intactos:** suite completa en verde; prueba nueva de que ningún barranco se pisa en 20 semillas (colisiones por barranco cuentan, caídas no existen).
- **Determinismo:** misma semilla → mismo mundo, mismas lecturas, misma partida (hash de la bitácora).
- **Umbrales previos:** los de 94d y el criterio de 94e (≥ 5/20) escritos aquí antes de medir.
- **CPU/RAM < 80 %** durante 94e, con turno.

### 1.8 Fichas de la parte 1 (`docs/planes/PLAN_sensores_fichas.json`)

- **ev3-d83** · Alcance del rediseño: **A** sensores físicos + mapa orbital que no ve barrancos poco profundos (recomendada: única con la que el criterio de 5/20 es alcanzable; ~1 día); **B** sensores físicos con el mapa orbital como hoy (la RNA aporta un 4–10 % de los barrancos; M7 honesto, M2-RNA probablemente sigue parcial; ~1 día); **C** no rediseñar: declarar la RNA como fusión redundante y cerrar M2-RNA con los números de 28f y 93 (0,5 h).
- **ev3-d84** · Congelado: **A** regenerar con atribución (recomendada); **B** mantener el esquema viejo por defecto y el mundo v2 solo en el laboratorio.

---

## Parte 2 · Diseño del juego (ARX-29, 50, 51, 57, 59)

*(pendiente: se escribe y confirma después de la parte 1)*

## Parte 3 · Paralelismo y plan de regeneración

*(pendiente)*

## Dónde quedé

- 17/11 22:5x · Parte 1 escrita y medida (scripts junto al plan). Faltan partes 2 y 3.
