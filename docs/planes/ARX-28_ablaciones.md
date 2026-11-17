# Plan ARX-28 · Escenario de evaluación donde cada técnica importe (ablaciones distintas)

Planner: `Esp_Planner`, 2026-11-17. Rama propuesta: `feat/arx-28-ablaciones` (base `main` en `2a6bfdd`, con el PR #1 integrado). Encargo del Orquestador. Frente 2 del proyecto; el frente 1 es ARX-30b/30c en `feat/arx-30-bc` (worktree `ares_x-wt-30bc`), hoy en QA.

## 1. Contexto

La nota de la tarea dice: «Hoy híbrido = sin RNA = sin difuso en /comparacion». Es cierto y se ve en `docs/COMPARACION_POLITICAS.json`: las tres variantes ganan 19 de 20, con mediana de 41 pasos, 0 colisiones y 53 de batería; solo difieren en las semillas 14 y 15, y por décimas. «Sin AG» sí se separa un poco (mediana 44 pasos). El PDF pide comparar el híbrido con al menos dos ablaciones (RF-14, CA-08) con 20 semillas y dispersión (RF-15); hoy la comparación existe pero no demuestra que la RNA ni el difuso aporten algo. El objetivo de ARX-28 es un escenario de evaluación en el que apagar cada técnica cambie el resultado, sin tocar las cifras congeladas del informe (`docs/TABLA_MODOS.md`, 20×30, `garantia=False`).

## 2. Estado actual (comprobado en el código)

**Arnés de comparación**
- `juego/comparacion.py`: `VARIANTES = ("hibrido", "sin_rna", "sin_difuso", "sin_ag")` (`:18`); `partida_variante` (`:44-61`) crea `Partida(semilla, filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)` y aplica la variante **sobre la instancia** (`m.usar_rna`, `m.usar_difuso`, o reemplaza `m._optimizar_ag` y replanifica). `comparar` (`:85-103`) resume éxito, pasos, colisiones y batería con media, mediana, desviación y rango intercuartílico.
- `scripts/comparacion_politicas.py` escribe `docs/COMPARACION_POLITICAS.json`; `GET /comparacion?semillas=` (`api/servidor.py:1018-1034`) sirve ese archivo para 20 semillas y calcula en la petición para otros valores (caché por número de semillas).
- Pruebas que lo fijan: `api/tests/test_datos_graficos.py:63-75` (cuatro variantes con dispersión; rango 1–40) y `juego/tests/test_ui.py:298-303` (líneas del panel). La interfaz lo consume en `api/static/laboratorio.js:613-614` (bloque de `index.html:885`).

**Por qué la RNA no cambia nada hoy**
- `SafetySupervisor.decidir` (`integracion.py:40-55`) veta por la RNA solo si `p(barranco)` o `p(obstáculo)` superan `UMBRAL_RIESGO_RNA = 0,5` (`:22`), y **después** de comprobar `borde_barranco` del sensor. Antes aún, `paso_mision` (`:192`) replanifica si `riesgo[siguiente] ≥ 0,5`, y `_actualizar_mapa_estimado` (`:258-262`) marca con 1,0 la celda que el sensor de proximidad ve a 1 m.
- El mapa estimado parte con `p_detectar = 0,8` (`genetico.py:24-36`): el 80 % de los peligros ya está marcado antes de salir y la ruta BFS los rodea. Los que faltan los descubre el sensor de proximidad con `ruido = 0,1` y `prob_fallo = 0` (`Mision.__init__`, `integracion.py:77`): es exacto, así que el veto por riesgo llega siempre antes que el de la RNA. La RNA es redundante con el sensor mientras el sensor sea fiable.
- La RNA usa cuatro rasgos (`rna.py:23-40`): proximidad, borde, gradiente y **vibración**, y la vibración depende de la clase real de la celda, no del sensor de proximidad. Con un sensor de proximidad ruidoso la RNA sigue teniendo señal propia.

**Por qué el difuso no cambia nada hoy**
- La velocidad del difuso **no tiene efecto físico**: `paso_mision` llama `paso_fisico(self.mundo, self.rover, rumbo)` (`integracion.py:214`) con el `costo` por defecto de 1,0 (`simulador.py:199`); la velocidad solo aparece en la bitácora, en el estado `ALERTA` y en `D-DIFUSO-LENTO` (detener si `velocidad < 0,2`, `:50`). Detenerse no consume batería ni mejora nada: con la física actual, apagar el difuso nunca puede empeorar el resultado. **Ninguna elección de escenario arregla esto sin cambiar una regla de la simulación** (sección 7).

**Palancas disponibles sin tocar `Mision` (congelada) ni `partida.py`**
- `Partida(nivel=5, filas=20, columnas=30, garantia=False)` (`juego/partida.py:276-300`): batería 84, 30 obstáculos, 9 barrancos, 4 sitios. El nivel es un parámetro público; no hace falta tocar la generación.
- Sobre la instancia: `m.sensor.ruido` (atributo de `SensorSuite`, `simulador.py:131`), `m.riesgo = mapa_estimado(mundo, m.rng, p_detectar=…)` seguido de `m._planear()` (el mismo patrón que usa `sin_ag`). `prob_fallo` **no** sirve como palanca: una lectura NaN manda a `MODO_SEGURO`, estado terminal (`integracion.py:41-42`), y mataría igual al híbrido y a las ablaciones.

**Contradicciones que señalo sin resolver**
1. `docs/MATRIZ_REQUISITOS_PDF.md:145` y `:156` marcan CA-08 y «dos ablaciones» como «Cumple» citando `intervencion.py` y `TABLA_MODOS.md`; con el dato de arriba, las ablaciones de RNA y difuso no distinguen nada. La fila RF-14 (`:84`) dice que falta «sin AG», pero `juego/comparacion.py:18` ya la tiene.
2. `INFORME_TECNICO.md:46-47` presenta «Sin RNA» y «Sin difuso» con cifras idénticas sin explicar por qué.
3. El docstring de `scripts/comparacion_politicas.py` dice «tarda varios minutos»: es trabajo pesado según `PROTOCOLO.md`, pide turno.

## 3. Propuesta

Agregar un **segundo escenario de evaluación, «exigente»**, al arnés de `juego/comparacion.py`, sin modificar el escenario congelado ni sus cifras. El escenario exigente degrada lo que hoy hace redundantes a las técnicas:
- **Para que la RNA importe:** sensor de proximidad ruidoso (`ruido` del orden de 0,6, a calibrar), mapa estimado pobre (`p_detectar` del orden de 0,4) y nivel 5 (más barrancos y obstáculos, menos batería). Así el veto por riesgo deja de llegar antes, y la RNA, con la vibración como rasgo propio, debería evitar colisiones y pasos a barranco. Se mide en `colisiones` y `pasos`.
- **Para que el AG importe:** los 4 sitios del nivel 5 y la batería de 84 hacen que el orden de visita pese más que con 3 sitios; `sin_ag` ya se separa y debería separarse más.
- **Para que el difuso importe:** hace falta que la velocidad tenga consecuencia física. Eso es una regla nueva de la simulación y la decide el usuario (ficha ev3-d54). Mientras no se decida, el escenario exigente se entrega con las ablaciones de RNA y AG separadas, y la de difuso declarada como limitación.

El trabajo empieza por una **calibración corta** (5 semillas, unas pocas combinaciones de `ruido` y `p_detectar`) porque este plan no puede garantizar de antemano que las curvas se separen: la RNA se entrenó con `ruido = 0,1` (`rna.py:43`) y puede degradarse con el sensor ruidoso. La calibración entrega los valores que quedan como constantes nombradas.

Decisiones de diseño que tomo:
- El escenario congelado no cambia: `docs/COMPARACION_POLITICAS.json`, `TABLA_MODOS.md` y `/comparacion` sin parámetro siguen devolviendo lo mismo. El nuevo escenario va en `docs/COMPARACION_POLITICAS_exigente.json` y en `/comparacion?escenario=exigente`.
- El escenario se aplica sobre la instancia de `Partida`/`Mision` dentro de `juego/comparacion.py`, antes de la variante. `partida.py`, `integracion.py` y `simulador.py` no cambian para el escenario (solo cambiarían para la física de la velocidad, si el usuario la aprueba).
- La física de la velocidad, si se aprueba, va detrás de una bandera de `Partida` apagada por defecto, encendida solo por el escenario exigente: las cifras congeladas y el juego no cambian hasta otra ficha.

Alternativas descartadas, una línea cada una:
- Cambiar el escenario congelado (por ejemplo, subir el ruido para todos): invalida `TABLA_MODOS.md` y el informe; el usuario puede pedirlo (ficha ev3-d55), no se asume.
- Degradar el sensor con `prob_fallo`: el NaN termina la misión en `MODO_SEGURO` para todas las variantes por igual.
- Bajar `UMBRAL_RIESGO_RNA` o reordenar los vetos del supervisor: cambia el controlador, no la evaluación, y `Mision` está congelada.
- Un escenario por técnica (uno para la RNA, otro para el difuso): tres tablas más en el informe; un solo escenario exigente basta si separa dos de tres.

## 4. Componentes afectados y fronteras

| Capa | Archivos | Qué cruza |
|---|---|---|
| Arnés | `juego/comparacion.py`, `scripts/comparacion_politicas.py` | escenarios como diccionario de parámetros aplicados a la instancia; argumento `escenario` del script |
| Datos | `docs/COMPARACION_POLITICAS_exigente.json` (nuevo) | generado por el script, 20 semillas |
| Pruebas | `juego/tests/test_comparacion_escenarios.py` (nuevo), `api/tests/test_datos_graficos.py` | `crm`-independiente; pytest local |
| API | `api/servidor.py` (`/comparacion?escenario=`) | compartido con el frente 1 |
| Interfaz | `api/static/laboratorio.js`, `api/static/index.html` (selector del escenario) | `index.html` compartido con el frente 1 |
| Motor (solo si ev3-d54 aprueba una física) | `juego/partida.py` (bandera y efecto tras `paso_mision`), pruebas | compartido con el frente 1 |
| Docs (paso Docs) | `docs/MATRIZ_REQUISITOS_PDF.md` (RF-14, CA-08, §13), `INFORME_TECNICO.md` §4, `docs/CONTRATOS_GRAFICOS.md` §7, `docs/OPERACION_MOTOR.md` | MATRIZ, CONTRATOS y OPERACION compartidos con el frente 1 |

Frontera que no se cruza: `Mision` sigue congelada; las evaluaciones del informe siguen con `garantia=False`, 20×30 y nivel 1.

## 5. Tareas

**ARX-28a · Calibración del escenario exigente (backend)** — ~1 h de trabajo, más un turno pesado de unos minutos
- Archivos: script temporal en la carpeta de la sesión (no en el repositorio); resultado en `docs/planes/ARX-28_calibracion.md` (nuevo).
- Hecho cuando: con 5 semillas (1–5) y nivel 5 en 20×30, se miden las cuatro variantes para una rejilla corta (`ruido` ∈ {0,3; 0,6; 1,0} × `p_detectar` ∈ {0,4; 0,6}), se elige la combinación donde `hibrido` y `sin_rna` difieren en colisiones o éxito en al menos 2 de 5 semillas sin que el híbrido baje de 3 éxitos de 5, y se anota la tabla completa y los valores elegidos. Si ninguna combinación separa la RNA, se informa así (resultado válido) y 28b usa la combinación con mayor diferencia.
- Pruebas: ninguna automática; el informe de calibración con la tabla es la evidencia. Pide turno al Orquestador antes de correr; no usa el 8765.

**ARX-28b · Escenario exigente en el arnés y el script (backend)** — ~1,5 h — depende de 28a
- Archivos: `juego/comparacion.py`, `scripts/comparacion_politicas.py`, `juego/tests/test_comparacion_escenarios.py` (nuevo), `docs/COMPARACION_POLITICAS_exigente.json` (generado, con turno).
- Hecho cuando: `ESCENARIOS = {"congelado": {...}, "exigente": {"nivel": 5, "ruido": R, "p_detectar": P}}` con las constantes de 28a; `partida_variante(semilla, variante, escenario="congelado")` aplica primero el escenario (nivel en el constructor; `ruido`, `mapa_estimado` y `_planear()` sobre la instancia) y después la variante; `comparar(semillas, escenario)` incluye `"escenario"` en la salida; el script acepta `python scripts/comparacion_politicas.py [n] [escenario]` y escribe `COMPARACION_POLITICAS_exigente.json` sin tocar el archivo congelado; `comparar(range(1, 4))` sin escenario produce exactamente las mismas filas que antes del cambio.
- Pruebas (4): regresión del escenario congelado (3 semillas, filas idénticas a las de `COMPARACION_POLITICAS.json` para esas semillas); `partida_variante(1, "hibrido", "exigente")` tiene `sensor.ruido == R`, nivel 5 y 4 sitios; la salida trae `"escenario"`; escenario desconocido lanza `ValueError`.

**ARX-28c · Física de la velocidad en la evaluación (backend)** — ~2 h — **BLOQUEADA por ev3-d54**; además comparte `juego/partida.py` con el frente 1: en fila tras integrar `feat/arx-30-bc`
- Archivos: `juego/partida.py`, `juego/comparacion.py`, `juego/tests/test_fisica_velocidad.py` (nuevo).
- Hecho cuando: `Partida` acepta una bandera (apagada por defecto) y, tras cada `m.paso_mision()` en `avanzar_ia`, aplica el efecto elegido en la ficha leyendo la velocidad de la última fila de la bitácora; el escenario exigente la enciende; con la bandera apagada, `comparar(range(1, 4))` congelado no cambia; `sin_difuso` y `hibrido` difieren en el escenario exigente en al menos una métrica.
- Pruebas (3): bandera apagada no altera batería ni colisiones; con la bandera, el efecto se observa en una partida de 1 paso con velocidad forzada (`intervencion_difuso`); regresión del congelado.

**ARX-28d · `/comparacion?escenario=` y contrato (backend)** — ~1 h — **BLOQUEADA por ev3-d55** y en fila tras integrar `feat/arx-30-bc` (comparte `api/servidor.py`)
- Archivos: `api/servidor.py`, `api/tests/test_datos_graficos.py`.
- Hecho cuando: `GET /comparacion?escenario=exigente&semillas=20` sirve el JSON nuevo; sin parámetro, todo sigue igual; escenario inválido → 400 legible; la caché distingue escenario; la respuesta incluye `"escenario"`.
- Pruebas (3): sin parámetro responde lo de hoy; `escenario=exigente&semillas=3` calcula y trae las cuatro variantes; `escenario=otro` → 400.

**ARX-28e · Selector de escenario en el panel de comparación (frontend)** — ~1 h — depende de 28d; en fila tras integrar `feat/arx-30-bc` (comparte `api/static/index.html`)
- Archivos: `api/static/index.html`, `api/static/laboratorio.js`.
- Hecho cuando: el bloque de comparación tiene un selector «Escenario: congelado | exigente» que cambia la consulta a `/comparacion`; el título de la tabla dice el escenario; sin el JSON del exigente la interfaz muestra el aviso del motor, no un error de consola.
- Pruebas: en Chrome, cambiar el selector recarga la tabla y las cifras del congelado no cambian.

Orden: 28a → 28b (frente 2, ahora) · integrar `feat/arx-30-bc` · 28d → 28e, y 28c cuando ev3-d54 esté decidida. Docs al final, sobre los documentos compartidos ya integrados.

## 6. Paralelismo

Comprobado con `git diff --stat main feat/arx-30-bc` (8 archivos): `api/servidor.py`, `api/static/index.html`, `api/tests/test_eventos_arx30.py`, `docs/CONTRATOS_GRAFICOS.md`, `docs/MATRIZ_REQUISITOS_PDF.md`, `docs/OPERACION_MOTOR.md`, `docs/planes/ARX-30_eventos.md`, `juego/partida.py`. Sus cambios de Docs pendientes van a CONTRATOS, MATRIZ y OPERACION.

| Tarea | Archivos | ¿Comparte con `feat/arx-30-bc`? | ¿Comparte con otra de ARX-28? | Veredicto |
|---|---|---|---|---|
| 28a | script temporal, `docs/planes/ARX-28_calibracion.md` | no | no | **puede correr en paralelo** (frente 2) |
| 28b | `juego/comparacion.py`, `scripts/comparacion_politicas.py`, `juego/tests/test_comparacion_escenarios.py`, `docs/COMPARACION_POLITICAS_exigente.json` | no | necesita el resultado de 28a | **en paralelo con el frente 1; en fila tras 28a** |
| 28c | `juego/partida.py`, `juego/comparacion.py`, `juego/tests/test_fisica_velocidad.py` | **sí: `juego/partida.py`** | `juego/comparacion.py` con 28b | **en fila**: tras integrar el frente 1 y tras 28b; además bloqueada por ev3-d54 |
| 28d | `api/servidor.py`, `api/tests/test_datos_graficos.py` | **sí: `api/servidor.py`** | necesita 28b | **en fila**: tras integrar el frente 1; bloqueada por ev3-d55 |
| 28e | `api/static/index.html`, `api/static/laboratorio.js` | **sí: `api/static/index.html`** | necesita 28d | **en fila**: tras 28d |
| Docs de ARX-28 | `docs/MATRIZ_REQUISITOS_PDF.md`, `INFORME_TECNICO.md`, `docs/CONTRATOS_GRAFICOS.md`, `docs/OPERACION_MOTOR.md` | **sí: MATRIZ, CONTRATOS, OPERACION** | — | **en fila**: después de los Docs del frente 1 |

**Conclusión:** ARX-28 **puede correr en paralelo** con ARX-30b/30c **solo con 28a y 28b**, que no comparten ningún archivo con `feat/arx-30-bc` ni con sus Docs pendientes. 28c, 28d, 28e y los Docs de ARX-28 **van en fila** detrás de la integración de `feat/arx-30-bc`, y al integrar el frente 1 la rama `feat/arx-28-ablaciones` trae `main` y QA repite las pruebas acotadas de 28b. Si el Orquestador prefiere no abrir un frente por solo dos subtareas, «va en fila» entero es un resultado igual de válido: 28a y 28b suman unas 2,5 h.

## 7. Riesgos

- **Que el escenario no separe a la RNA.** La RNA se entrenó con `ruido = 0,1`; con un sensor más ruidoso puede fallar tanto como el sensor. Por eso 28a mide antes de fijar nada y acepta como resultado «no se separa»; en ese caso el informe lo declara y el usuario decide si vale reentrenar (ficha nueva, no se adelanta).
- **El difuso no puede importar sin cambiar la física.** Es una regla de la simulación: ficha ev3-d54. Sin ella, el escenario exigente separa a lo más dos de tres técnicas.
- **Cifras congeladas.** Toda prueba de regresión del congelado compara filas, no solo resúmenes. La bandera de 28c apagada por defecto protege `TABLA_MODOS.md` y el juego.
- **`p_detectar` consume el `rng` de `Mision`.** Recalcular `mapa_estimado` con `m.rng` cambia la secuencia aleatoria del escenario exigente (no del congelado, que no lo recalcula). Es aceptable porque el escenario es nuevo, pero debe ser determinista por semilla: la prueba lo comprueba corriendo dos veces.
- **Trabajo pesado.** Calibración y generación del JSON tardan minutos: turno del Orquestador, CPU y RAM bajo 80 %, nunca en el 8765. La ventana de consumo va en 55 %: 28a usa 5 semillas y una rejilla de 6 puntos, no más.
- **Frente 2 con dos subtareas.** Si QA del frente 1 pide cambios y vuelve a `partida.py`, 28a y 28b no se ven afectadas; 28c sí, y por eso espera.

## 8. Decisiones del usuario (fichas; las carga el Orquestador)

Redactadas en `docs/planes/ARX-28_fichas.json`. Siguen a ev3-d53, la última que existe.

**ev3-d54 · ¿La velocidad del difuso tiene efecto físico?** (bloquea 28c)
- A: a más velocidad, más probabilidad de resbalar en pendiente: el paso se pierde y cuesta batería extra; despacio es seguro. Solo en el escenario exigente de la evaluación.
- B: la batería gastada por paso depende de la velocidad: rápido gasta más, lento gasta menos pero tarda más. Solo en el escenario exigente.
- C: la física no cambia; el informe declara que el difuso modula alertas y estado, y que su ablación no se separa. Sin trabajo.
- Recomendada: A, porque hace que «lento = seguro» sea verdad, que es lo que el difuso intenta.

**ev3-d55 · ¿Cómo entra el escenario exigente al informe y a la pantalla?** (bloquea 28d y 28e)
- A: se agrega junto al congelado: dos tablas en el informe, selector en la pantalla, las cifras actuales no cambian.
- B: reemplaza al congelado en el informe y en `/comparacion`; se rehacen `TABLA_MODOS.md` y el informe con el escenario nuevo.
- C: solo en el informe, sin API ni pantalla.
- Recomendada: A.

## 9. Verificación (para QA)

1. Pruebas acotadas:
   ```
   python -m pytest -q juego/tests/test_comparacion_escenarios.py
   python -m pytest -q api/tests/test_datos_graficos.py -k comparacion
   ```
   y, cuando existan, `juego/tests/test_fisica_velocidad.py`.
2. Regresión del congelado: `python -c "from juego.comparacion import comparar; print(comparar(range(1,4))['filas'])"` produce las mismas filas que las semillas 1–3 de `docs/COMPARACION_POLITICAS.json` (estado, pasos, colisiones, batería).
3. Separación: en `docs/COMPARACION_POLITICAS_exigente.json`, `hibrido` y `sin_rna` difieren en colisiones o éxito, y `sin_ag` difiere en pasos; se anotan las cifras en el informe de QA. Si no difieren, QA lo reporta como hallazgo, no como fallo de implementación, y cita `ARX-28_calibracion.md`.
4. API y pantalla (tras 28d y 28e, con una instancia de prueba en un puerto distinto del 8765): `/comparacion` sin parámetro idéntico a antes; `?escenario=exigente` responde con `"escenario": "exigente"`; el selector cambia la tabla sin errores de consola.
5. Documentación (paso Docs, después de los Docs del frente 1): MATRIZ (RF-14 con «sin AG» ya existente, CA-08 y §13 con la explicación de por qué las ablaciones eran iguales), INFORME_TECNICO §4 (dos tablas o la que diga ev3-d55, y la limitación del difuso si ev3-d54 = C), CONTRATOS §7 (parámetro `escenario`), OPERACION_MOTOR (cómo regenerar los dos JSON con turno).
