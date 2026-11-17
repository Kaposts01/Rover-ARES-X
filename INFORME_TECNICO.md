# ARES-X: informe técnico breve

**Evaluación individual · IA aplicada · Plazo: mediodía del 10 de noviembre de 2026**

Simulación ficticia con parámetros de referencia. Todos los valores sin fuente son *supuestos de simulación*, no especificaciones de misión.

## 1. Arquitectura

Flujo por paso (sección 4 de la consigna):

1. **Mundo real** (`simulador.py`): mapa de cuadrícula con obstáculos, barrancos y sitios científicos. Solo lo usa el simulador y la evaluación. El rover se mueve en ocho direcciones (N, S, E, O y las diagonales, ev3-d29 B); la planificación y la física usan la misma regla: un paso es válido si la celda de destino es transitable.
2. **Sensores** (`SensorSuite`): lecturas con ruido de proximidad, borde de barranco y altimetría. Pueden devolver NaN.
3. **RNA** (`rna.py`): MLP 32-16 con ReLU y softmax de tres clases (libre, obstáculo, barranco).
4. **Difuso** (`difuso.py`): Mamdani min-max con centroide. Entradas: distancia a riesgo, batería e inclinación. Salida: velocidad en [0, 1].
5. **AG** (`genetico.py`): cromosoma de K puntos de paso, decodificado a ruta contigua con BFS sobre el mapa estimado. En el juego, el orden de los sitios lo fija la búsqueda exhaustiva de la ruta más corta (con hasta 6 sitios; con más, la voraz). El AG corre, pero no decide ese orden (ev3-d71 A; ver §4.2).
6. **Supervisor** (`integracion.py`): evalúa primero las prohibiciones físicas (sensor NaN, batería cero, barranco en el borde de la ruta, RNA con probabilidad alta de barranco u obstáculo) y después combina la velocidad. Cada veto lleva un código de motivo `V-…`.
7. **Bitácora** (`MissionLogger`): una fila por paso, exportable a CSV y JSON.

Los estados son EXPLORACION, ALERTA, MODO_SEGURO, EXITO, FRACASO y SIN_RUTA. El replanteo es una acción del supervisor, no un estado.

## 2. Decisiones de diseño

| Decisión | Motivo | Ficha |
|---|---|---|
| Cromosoma de K puntos de paso | Encaja con el subproblema del viajero y se repara con descarte de puntos inalcanzables | ev3-d01 |
| Mundo real separado del mapa estimado | La consigna prohíbe que el AG use el futuro conocido | ev3-d02 |
| Un solo notebook `.ipynb` | Decisión original para Colab; reemplazada por ev3-d30. Hoy el proyecto corre en local (pygame, o API + navegador) y el notebook queda como registro del pipeline | ev3-d03 (reemplazada por ev3-d30) |
| ipywidgets + matplotlib | Decisión original para Colab; reemplazada por ev3-d30. Hoy no se usa Colab y la interfaz es pygame o Three.js en navegador | ev3-d04 (reemplazada por ev3-d30) |
| Planificación de la ruta una vez; replanteo con BFS. En el juego, el orden de los sitios lo fija la búsqueda exhaustiva, no el AG (ARX-92 lo cambiará) | La integración reactiva con AG en cada paso no convergía (ver §5) | ev3-d07; ev3-d71 A |
| Recorte fuerte de alcance | Plazo de mediodía del 10 de noviembre | ev3-d06 |

## 3. Casos de prueba

- **45 pruebas automáticas** (`pytest`), todas en verde: simulador (11), RNA (6), difuso (10), AG (9) e integración (9 de supervisor y misiones).
- Casos de borde: batería 0 no mueve al rover; sensor NaN degrada a modo seguro; gigante con rover se bloquea; mapa sin sitios no falla; entrada NaN en el difuso degrada a velocidad 0.
- Prueba de que el rover nunca pisa un barranco ni colisiona, en semillas base. Las misiones de semillas 11, 12 y 13 llegan al refugio.
- Caso con barranco inyectado en la ruta: se ejecuta en el notebook, pero no hay prueba automática de su resultado.

## 4. Experimento y ablaciones

> **Provisional: las tablas de esta sección se regeneran tras ARX-92.** Son anteriores a ARX-90, ARX-91 y ARX-28c. Las lecturas de abajo se reescriben con la regeneración. El estado medido hoy está en la sección 4.2.

20 semillas por variante, mapas de Marte con 20 obstáculos, 4 barrancos y 3 sitios científicos (`ARES_X_ejecutado.ipynb`):

| Variante | Éxito | Colisiones | Barrancos pisados | Sitios visitados (media) | Pasos (mediana) | Batería media |
|---|---|---|---|---|---|---|
| Híbrido | 100 % | 0 | 0 | 1.7 | 39.5 | 61.1 % |
| Sin RNA (ablación) | 100 % | 0 | 0 | 1.7 | 39.5 | 61.1 % |
| Sin difuso (ablación) | 100 % | 0 | 0 | 1.7 | 39.5 | 61.1 % |

**Lectura de los resultados:**

- Con ocho direcciones, las tres variantes dan exactamente los mismos resultados en estas 20 semillas: la RNA y el difuso no cambian ninguna decisión en este escenario. El sensor de proximidad y el supervisor ya cubren los peligros. Esto no demuestra que la RNA o el difuso sean inútiles; sí que su aporte no es medible en este conjunto.
- No se atribuye mejora causal a ninguna técnica, porque las diferencias son nulas o mínimas.

### 4.1 Prueba causal: intervención en la RNA y en el difuso (ARX-10, ev3-d32 A)

> **Provisional:** la tabla de esta sección es de ARX-10, anterior a ARX-91. Se regenera tras ARX-92.

Se fuerza la salida de una técnica y se mide el primer paso donde cambia la acción o la velocidad, frente a
la misión base con la misma semilla (20 semillas, mapas de Marte con 20 obstáculos, 4 barrancos y 3 sitios):

| Variante | Semillas con cambio de decisión | Éxito | Sitios (media) | Pasos (mediana) | Primer cambio (mediana) |
|---|---|---|---|---|---|
| RNA forzada a barranco (0,95) | 20 de 20 | 0 % | 0,0 | 400 (tope) | paso 1 |
| RNA forzada a libre (0,95) | 0 de 20 | 100 % | 1,7 | 39,5 | — |
| Difuso forzado a velocidad 0 | 20 de 20 | 0 % | 0,0 | 400 (tope) | paso 1 |
| Difuso forzado a velocidad 1 | 20 de 20 | 100 % | 1,7 | 39,5 | paso 1 |

**Lectura de los resultados:**

- Alterar la salida de la RNA a barranco sí cambia la decisión y el movimiento: el supervisor veta en cada paso,
  el rover no avanza y la misión agota los 400 pasos. Esto cumple la condición de auditoría de la sección 4.
- Forzar la RNA a libre no cambia ninguna decisión: la RNA base ya clasifica casi todas las celdas como libres,
  así que la intervención no altera nada en este escenario.
- Forzar el difuso a velocidad 0 detiene al rover en todas las semillas y la misión no termina.
- Forzar el difuso a velocidad 1 cambia la velocidad en el primer paso, pero el resultado final no cambia: el
  éxito y los sitios son los mismos que en la base.
- Conclusión: la RNA y el difuso influyen en la decisión del paso a paso, pero en este escenario el resultado
  final depende sobre todo del sensor y del supervisor. El aporte de cada técnica queda demostrado de forma causal
  en la decisión, no en el éxito de la misión.

### 4.2 M2 por técnica (ev3-d62, ev3-d71 A)

Estado medido en el escenario exigente, 20 semillas. **Provisional hasta ARX-92.** La traza es `docs/TRAZA_DIVERGENCIAS_exigente.csv`, con la regla «directa»: la primera divergencia por semilla y variante que cambia decisión, velocidad o ruta.

| Técnica (variante del arnés) | Semillas con divergencia directa | Rótulo |
|---|---|---|
| Difuso (`sin_difuso`) | 20 de 20 | difuso |
| RNA (`sin_rna`) | 3 de 20 (semillas 4, 10 y 18) | RNA |
| AG (`sin_ag`) | 12 de 20 (semillas 3–9, 11–14 y 17) | «sin AG: vecino más cercano». No mide el AG |

M2 se evalúa técnica por técnica; no hay un «cumple» único.

- **Difuso: cumple, con efecto en el resultado.** Sin difuso, la velocidad cambia en las 20 semillas. Esa velocidad es fija (0,5) en la variante, así que el efecto en el resultado es el de la comparación de éxitos: 20 de 20 con el difuso, 15 de 20 sin él (`docs/COMPARACION_POLITICAS_exigente.json`).
- **RNA: parcial, altera decisiones, sin efecto en el resultado.** Con la RNA apagada, la decisión, la velocidad o la ruta cambian en 3 de 20 semillas (4, 10 y 18). En las tres, la RNA veta un obstáculo que está fuera de la ruta y obliga a replanificar. Cuesta entre 1 y 4 pasos (+4 en la semilla 4; +1 en las semillas 10 y 18) y no cambia el éxito ni las colisiones en ninguna semilla. Cuando el obstáculo está en la ruta, el supervisor actúa antes (chequeo incondicional de ARX-91) y la decisión de la RNA queda enmascarada. En este diseño la RNA es redundante con el supervisor: altera decisiones puntuales, sin efecto en el resultado.
- **AG: pendiente de ARX-92.** En el juego el AG no decide el orden de visita. La variante del arnés que lo sustituye usa vecino más cercano y se rotula así. No hay todavía una medición del aporte del AG, y no se publica ninguna conclusión sobre él hasta ARX-92.
- **Recall de barrancos de la RNA sin `borde_barranco` (ARX-28f):** 0,70–0,80 con el rasgo y 0,000 sin él (sección 5).

No se abre ningún intento más para la RNA salvo que el usuario lo pida.

## 5. Resultados de la RNA

Cifra reproducible del informe (modelo del notebook: partición de 60 mapas, 42 entrenamiento, 9 validación y 9 prueba, 400 muestras por mapa, prueba en los mapas 51 a 59; semilla 42): macro-F1 **0.928** y recall de barrancos **0.943** (33 de 35 muestras de barranco), ECE 0.011. La línea base por clase mayoritaria es 0.927, porque el 93 % de las celdas son libres. Por eso se reporta macro-F1 y no exactitud.

El modelo que usa la partida del juego se entrena con una partición más pequeña (30 mapas: 21 entrenamiento, 4 validación y 5 prueba, 300 muestras por mapa) para que la carga sea rápida. En sus mapas de prueba 25 a 29 (1 401 muestras) obtiene macro-F1 0.909 y recall de barrancos **0.786** (11 de 14). Es una limitación conocida: la cifra del notebook no describe el modelo del juego, y se muestra en el laboratorio RNA con su configuración (`GET /rna/evaluacion?modelo=juego`).

**Control de la RNA sin el rasgo `borde_barranco` (ARX-28f).** Con la RNA entrenada, el recall de barranco es 0,70–0,80 con sus rasgos normales y 0,000 sin `borde_barranco` (ruido 0,1 y 0,6; 0 de 250 barrancos en la partición de 60 mapas y 0 de 135 en la de 30). Lo medido es que, sin ese rasgo, la RNA no predice barrancos. Que la causa sea la dependencia de ese rasgo es una inferencia. El muestreo es distinto del de la cifra de arriba (unos 3 000 intentos por mapa). Detalle en `docs/planes/ARX-28_calibracion.md`, sección 28f.

## 6. Limitaciones

**Del motor (simulación y sensores)**
- **Falso positivo del sensor.** Con ruido, el rover marca como obstáculo una celda libre y ese bloqueo no se libera. Con ocho direcciones, un barranco inyectado en los pasos 1 a 12 de la semilla 11 no impide llegar al refugio; el fallo sigue en la lógica y puede dar SIN_RUTA en otros mapas aunque el mapa real tenga camino.
- **Sitios omitidos por energía.** En promedio se visitan 1,7 de 3 sitios; el plan prioriza llegar al refugio.
- **La RNA es redundante en el escenario normal.** Con los sensores activos, la RNA y el difuso no cambian el resultado final. Su efecto solo se mide con la prueba causal (sección 4.1): cambian la decisión, pero no el éxito.
- **Replanteo con BFS, sin optimizar.** Tras la decisión ev3-d07, el replanteo solo busca un camino válido, sin volver a optimizar la ruta con el AG.
- **Supuestos de simulación.** Pesos del fitness, costos de batería, rangos de sensores y parámetros de los drones son supuestos, no datos de misión.

**De la capa 3D y del combate**
- **El supervisor está congelado y no conoce a los drones.** La decisión de combate (disparar o evitar) vive en la capa de la API. Esa capa solo marca como peligrosa la celda exacta del dron al replanificar; no evita las celdas vecinas, porque hacerlo cortaba el único pasillo al refugio (SIN_RUTA).
- **Modos individuales (ARX-11).** Cada modo rna, difuso y ag conduce el rover por sí solo (`juego/conduccion.py`). Con el veto de seguridad encendido no hay colisiones en la semilla 11 ni en la tabla de 20 semillas (`docs/TABLA_MODOS.md`). Con el veto apagado aparecen colisiones e intentos a barranco, que es lo que muestra cómo falla cada técnica sola. Los modos sueltos no reaccionan a los drones más allá del daño de batería; solo el modo automático y el generativo usan la decisión de combate.
- **Eventos.** Tormenta y noche existen en el motor de partida. En la escena 3D no hay eventos de sismo ni de tormenta visibles.

**Explicación en lenguaje natural (ev3-d33, descartada).** Qwen2.5-0.5B-Instruct se probó y se descartó por decisión del estudiante (ev3-d37). No forma parte del entregable.

**Fuera de alcance del MVP** (lista de la especificación, sección 10): otros planetas y modo sonda; varios tipos de enemigos; eventos de sismo en 3D; video y defensa (los graba el estudiante); despliegue en internet y cuentas de usuario.

## 7. Aportes individuales

> **BORRADOR para revisión del estudiante.** Redactado a partir de las decisiones registradas en la Bandeja. Corregir cualquier punto que no corresponda antes de entregar.

Trabajo individual. Las decisiones de diseño se tomaron con el estudiante y quedaron registradas (fichas `ev3-d01` a `ev3-d09`):

- **Modelo del problema:** elección de K puntos de paso para el cromosoma (`ev3-d01`) y separación del mundo real y el mapa estimado (`ev3-d02`).
- **Entrega:** la decisión original de un notebook para Colab (`ev3-d03`) y de ipywidgets con matplotlib (`ev3-d04`) quedó reemplazada por `ev3-d30`: el proyecto ya no usa Colab y todo corre en local.
- **Revisión de la fase del AG:** aprobación de la Fase 4 y paso a la integración (`ev3-d05`).
- **Plazo:** recorte del alcance para entregar al mediodía (`ev3-d06`).
- **Integración:** simplificación del diseño a planificación única con replanteo por BFS, y control de cambios de una sesión no autorizada, con reversión (`ev3-d07`, `ev3-d08`).
- **Informe:** redacción de este documento con revisión del estudiante (`ev3-d09`).

Módulos implementados: `simulador.py`, `rna.py`, `difuso.py`, `genetico.py` e `integracion.py`, con sus pruebas en `tests/`.

## 8. Declaración de uso de IA generativa

> **BORRADOR para revisión del estudiante.** Confirmar que refleja el uso real antes de entregar.

Se usó Claude (Anthropic), a través de Claude Code, para:

- generar código de los módulos y de las pruebas, a partir de las especificaciones de la consigna;
- depurar fallos, en particular la integración reactiva de la Fase 5, que llevó a la decisión de simplificar el diseño (`ev3-d07`);
- redactar documentación, incluido este informe.

Se usó Gemini (Google) para generar la imagen de fondo del menú de inicio de la interfaz. Es una imagen ilustrativa, sin carácter oficial ni respaldo de ninguna agencia espacial; su origen está declarado en el README.

Las decisiones de diseño se tomaron con el estudiante y quedaron registradas en la Bandeja. Cada resultado se verificó ejecutando las 45 pruebas y el notebook. Los valores de simulación son supuestos, no especificaciones de misión.

[Completar por el estudiante: qué partes revisó y modificó a mano, y qué entiende de cada módulo, porque la defensa oral exige explicarlo.]
