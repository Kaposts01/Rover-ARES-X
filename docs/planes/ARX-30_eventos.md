# Plan ARX-30 · Sismo, baja conectividad y señal biológica con efecto real (ev3-d41 B)

Planner: `Esp_Planner`, 2026-11-16. Piloto de la fase 2 del sistema de agentes. Rama propuesta: `feat/arx-30-eventos` (base `main` en `ab46b4a`). Encargo del Orquestador; palabras del usuario: «Sigamos con la fase 2, usemos ARX-30 como piloto».

## 1. Contexto

La ficha **ev3-d41** (aprobada el 13/11, opción **B**: «los cuatro con efecto real», unas 8 h) pide que sismo, meteorito, baja conectividad y señal biológica anómala existan en el juego con efecto sobre la partida, no solo como texto. El detalle de la opción A de esa misma ficha fija qué significa «efecto real» para sismo y meteorito: **replanteo del AG y veto del supervisor**. Para conectividad y señal biológica la ficha no dice cuál es el efecto; eso queda en la sección 7.

El meteorito ya está hecho y verificado en Chrome (ronda 15 del 14/11): cae solo con probabilidad por nivel, marca zona de riesgo 3×3, cuesta batería y se ve con estela, polvo y aviso. Faltan los otros tres. El PDF de la evaluación (§6) los lista como eventos; §9 pide «sismo» entre las interacciones mínimas; §3 exige que el sistema **nunca afirme que hay vida**.

## 2. Estado actual (comprobado en el código, no en la documentación)

**Motor (`juego\partida.py`)**
- `EVENTOS_SOPORTADOS` (`juego/partida.py:25`): barranco, falla_sensor, bateria_baja, tormenta, noche, meteorito. `disparar_evento` (`:1063`) despacha por nombre.
- `_tick_ambiente` (`:1044`) corre tras cada paso en los cuatro caminos: `avanzar_ia` (`:878`), `_paso_con_falla` (`:897`), `mover_jugador` (`:1018`) y `conduccion._estado_tras_paso` (`juego/conduccion.py:180`). Ahí tira el dado del meteorito con `METEORITO_PROB_POR_NIVEL` (`:26`) y solo si `meteoritos_activos = bool(garantia)` (`:320`): las evaluaciones congeladas (`garantia=False`) no tienen eventos espontáneos.
- `_evento_meteorito` (`:1077`) es el molde: elige celda libre a distancia 2–3, marca `mision.riesgo`, cobra `DANO_METEORITO`, guarda `self.meteoritos` y llama `_avisar`.
- `_rng_ambiente = np.random.default_rng([semilla, 1313])` (`:343`) es el único generador de los eventos espontáneos. `avisos` y `_avisar` (`:351`, `:707`) llegan a la interfaz por `/estado`.
- Falla de sensor (`:1121`): la IA se detiene `PASOS_FALLA_SENSOR` pasos con `_falla_restante` y `_paso_con_falla` (`:889`). Es el molde para cualquier evento «con duración».
- `_alcanzables(mundo, origen)` (`:88`) y `_es_ganable` (`:191`) son la garantía de ARX-66: toda partida generada es ganable.

**Simulador y misión**
- `World.marcar_barranco` (`simulador.py:81`) convierte una celda en BARRANCO; `paso_fisico` (`:199`) nunca entra en obstáculo ni barranco. `SensorSuite` (`:127`) tiene `ruido` y `prob_fallo`.
- `Mision.paso_mision` (`integracion.py:148`): si la siguiente celda de la ruta tiene `riesgo ≥ 0,5` decide `replanificar` con `V-RUTA-CON-RIESGO` (`:192`); `camino_valido` (`:314`). `Partida._planear_con_objetivo` (`juego/partida.py:905`) sustituye a `Mision._planear`, así que `m._planear()` es el replanteo del AG.

**API (`api\servidor.py`)**
- `EVENTOS` (`:43`) duplica la lista del motor; `POST /evento` (`:788`) valida contra ella.
- `GET /moviles` (`:910`) emite `moviles` (drones y meteoritos), `obstaculos_moviles: []` y `eventos_del_paso` (textos de combate y `{nombre:"meteorito", efecto:"zona_riesgo", celdas}` solo en el paso del impacto). Su docstring dice que los obstáculos móviles «llegarán en ARX-30»; según `docs\tareas_sprints.json` son de **ARX-29**. Este plan no los toca.
- `_estado` (`:190`) expone `ambiente`, `ambiente_restante` y `avisos`; no hay campo para el enlace ni para una señal.
- `GET /mapa` (`:662`) devuelve `mundo.tipo`; la interfaz lo pide **una sola vez** al crear la partida (`api/static/app.js:1593`).

**Interfaz 3D (`api\static`)**
- `moviles.js:111` `aplicarEvento` ya reacciona por nombre: `includes("sismo")` → `efectos.sacudir`; `includes("conectividad")` → `activarInterferencia(true)`; `includes("senal")` → `marcarSenalBiologica` en `e.celdas[0]` y aviso con `TEXTO_BIO = "anomalía, no confirma vida"`.
- `efectos.js`: temblor (`:119`, aplicado a la cámara en `app.js:2598`), interferencia del HUD (`:159`), anillo y etiqueta de la señal (`:178`).
- **Defectos ya presentes:** `activarInterferencia(false)` no se llama en ningún archivo (la interferencia, una vez encendida, no se apaga nunca) y `quitarSenalBiologica` tampoco se llama desde `moviles.js`.
- No hay ningún control que haga `POST /evento` (`index.html`: 0 coincidencias; `app.js`: ninguna llamada). Los eventos solo se disparan por API o solos. La matriz §9 ya marca «sismo» como interacción que falta.
- `adaptador.js:33` (datos de prueba) usa `celdas` para la señal biológica; el contrato §10 (`docs/CONTRATOS_GRAFICOS.md:250`) dice `celda`. El código manda: **`celdas`**.

**Pruebas:** `api/tests/test_meteorito.py` es el patrón (Partida directa + `TestClient`, 6 pruebas, incluida «la partida congelada no tiene meteoritos espontáneos»).

**Documentación que no cuadra con el código (se señala, no se resuelve aquí):**
1. `CONTEXTO_AGENTES.md` dice «sin repositorio remoto»; el encargo indica `origin = github.com/Kaposts01/Rover-ARES-X` (público). Que lo confirme el Orquestador o GitOps.
2. Contrato §10: `celda` frente a `celdas` (arriba).
3. Docstring de `/moviles`: obstáculos móviles atribuidos a ARX-30; son de ARX-29.
4. `docs/MATRIZ_REQUISITOS_PDF.md` §7 marca el meteorito como «Falta» aunque existe.
5. Hay cambios sin confirmar en el árbol de trabajo (`docs/tareas_sprints.json` modificado, `CONTEXTO_AGENTES.md` sin versionar). La rama debe salir de `main` limpio; esos dos archivos los confirma quien los posee.

## 3. Propuesta

Replicar el patrón del meteorito para los tres eventos: nombre en `EVENTOS_SOPORTADOS` y en `EVENTOS` de la API, método `_evento_<nombre>` disparable por `POST /evento`, caída espontánea en `_tick_ambiente` con probabilidad por nivel **solo en partidas jugables** (`garantia=True`), registro en la partida, aviso por `_avisar`, y exposición en `eventos_del_paso` de `/moviles` con los nombres que la interfaz ya reconoce: `sismo`, `baja_conectividad`, `senal_biologica`. La interfaz completa lo que le falta (apagar efectos, pintar grietas) y gana un control mínimo para disparar eventos.

Decisiones de diseño que sí tomo (son supuestos de simulación, como `DANO_METEORITO`):
- **Un generador aleatorio por evento** (`np.random.default_rng([semilla, 1314])`, `[semilla, 1315]`, `[semilla, 1316]`), no el `_rng_ambiente` compartido. Si los nuevos dados salieran del mismo generador, cambiaría la secuencia de meteoritos de cada semilla y dejaría de valer el ejemplo documentado en el contrato §14 (semilla 5, Medio, pequeño: meteorito en el paso 20 en (16, 12)).
- **Sismo = grietas.** Efecto real según ev3-d41 A: 1–3 celdas libres a distancia Chebyshev 2–4 del rover pasan a BARRANCO en el mundo real, con `riesgo = 1,0` en el mapa estimado (supuesto: el rover siente el sismo y su sensor de borde ve las grietas). Si una grieta cae sobre la ruta, la misión replanifica de inmediato (`m._planear()`, replanteo del AG) y el supervisor la veta si la ruta volviera a pasar (`V-RUTA-CON-RIESGO`). Sin daño de batería (eso distingue al meteorito). Antes de marcar se comprueba con `_alcanzables` que el refugio y los sitios pendientes siguen alcanzables por el mapa real; si no, se descarta esa celda.
- Probabilidades por paso del orden de las del meteorito (sismo 0,3 %–0,9 % de Muy fácil a Hardcore; los otros dos, más raros). Son constantes nombradas y ajustables.
- Nada de esto cambia la regla vigente de que los drones son obligatorios solo desde Medio (`drones_obligatorios`, `juego/partida.py:485`).

Alternativas descartadas, una línea cada una:
- Sismo que solo detiene al rover N pasos (como la falla de sensor): no cumple «replanteo del AG y veto del supervisor».
- Sismo que deja los tipos del mundo intactos y solo marca riesgo: la grieta no sería real para el modo manual.
- Un solo evento genérico con `efecto` parametrizable: ahorra código pero rompe el molde que ya existe y la lectura del contrato.
- Refrescar `/mapa` entero tras cada evento: más tráfico y más trabajo que pintar las celdas que trae el evento.

## 4. Componentes afectados y fronteras

| Capa | Archivos | Qué cruza |
|---|---|---|
| Motor | `juego/partida.py` | nuevas constantes, tres `_evento_*`, tick, registros `sismos`, `senales`, `enlace_restante` |
| Simulador | `simulador.py` | solo lectura (`marcar_barranco`, `SensorSuite`); no se modifica |
| Misión | `integracion.py` | solo lectura; el replanteo se pide desde `Partida` |
| API | `api/servidor.py` | `EVENTOS`, `/moviles.eventos_del_paso`, `/estado` (campos `enlace`, `senal`); según ev3-d48, `/mover`, `/intervencion`, `/recomendacion` |
| Interfaz | `api/static/moviles.js`, `efectos.js`, `app.js`, `index.html` | apagar efectos por estado, grietas, control de eventos |
| Pruebas | `api/tests/test_eventos_arx30.py` (nuevo) | Partida + TestClient |
| Contrato y docs (paso Docs) | `docs/CONTRATOS_GRAFICOS.md` §10 y §14, `docs/MATRIZ_REQUISITOS_PDF.md` §7 y §9, `docs/OPERACION_MOTOR.md`, `CONTEXTO_AGENTES.md` | ver sección 8 |

Frontera que no se cruza: `Mision` sigue congelada (los ajustes van en `Partida` sobre la instancia); `juego/comparacion.py` y `juego/conduccion.py` siguen creando la evaluación con `garantia=False`, así que `docs/TABLA_MODOS.md` no cambia.

Forma de los eventos en `eventos_del_paso` (independiente de las fichas; las fichas cambian el efecto en el motor, no la forma):
```json
{"nombre": "sismo", "efecto": "grietas", "celdas": [[f, c], ...]}
{"nombre": "baja_conectividad", "efecto": "sin_enlace", "restante": 4}
{"nombre": "senal_biologica", "efecto": "lectura_anomala", "celdas": [[f, c]], "afirma_vida": false}
```
Y en `/estado`: `"enlace": {"activo": true|false, "restante": n}` y `"senal": [f, c] | null`, para que la interfaz apague la interferencia y el marcador sin depender del polling de `/moviles`.

## 5. Tareas

Cada una cabe en su propio commit sobre `feat/arx-30-eventos`. Especialista entre paréntesis. Las pruebas acotadas se corren por archivo; la suite completa solo con turno del Orquestador.

**ARX-30a · Sismo en el motor y la API (backend)** — ~2 h
- Archivos: `juego/partida.py`, `api/servidor.py`, `api/tests/test_eventos_arx30.py` (nuevo).
- Hecho cuando: `"sismo"` está en `EVENTOS_SOPORTADOS` y en `EVENTOS`; `_evento_sismo` marca `GRIETAS_POR_NIVEL[nivel]` celdas LIBRE a distancia 2–4 como BARRANCO (`mundo.marcar_barranco`) y `riesgo = 1,0`, excluyendo rover, sitios, inicio, refugio y estaciones, y descartando toda celda que deje el refugio o un sitio pendiente fuera de `_alcanzables`; si una grieta está en `m.ruta`, llama `m._planear()` y anota una fila en la bitácora con motivo `REPLAN-SISMO`; guarda `self.sismos = [{paso, grietas}]`; `_avisar("Sismo: grietas nuevas cerca del rover")`; cae solo en `_tick_ambiente` con `SISMO_PROB_POR_NIVEL` y un generador propio, solo con `garantia`; `/moviles` emite `{nombre:"sismo", efecto:"grietas", celdas}` en el paso del sismo. Sin cambios en el consumo de batería.
- Pruebas (5): `POST /evento sismo` → 200 y `ok`; las grietas son BARRANCO en `mundo.tipo` y riesgo 1,0; refugio y sitios pendientes siguen alcanzables; partida `garantia=False` tras 3000 ticks no tiene sismos; la secuencia de meteoritos de `Partida(semilla=11, nivel=5, filas=40, columnas=60)` tras 3000 ticks es la misma que antes del cambio (regresión del generador separado).

**ARX-30b · Baja conectividad (backend)** — ~2 h — **BLOQUEADA por ev3-d48**
- Archivos: `juego/partida.py`, `api/servidor.py`, `api/tests/test_eventos_arx30.py`.
- Hecho cuando: `"baja_conectividad"` en ambas listas; `_evento_baja_conectividad` fija `enlace_restante = PASOS_SIN_ENLACE` y `_tick_ambiente` lo descuenta; `/estado.enlace` y el evento `sin_enlace` con `restante` en `/moviles`; el efecto real es el que elija la ficha (A: en manual cada orden de `/mover` se pierde con probabilidad `PROB_ORDEN_PERDIDA` con motivo `sin enlace` y, en los modos de IA, `/intervencion` y `/recomendacion` responden 409 mientras dure; B: el rover se detiene como en la falla de sensor con motivo `D-SIN-ENLACE`; C: consumo extra de batería por paso). Cae solo con probabilidad por nivel y generador propio.
- Pruebas (4): disparo por API; el efecto elegido se observa en el motor; termina a los N pasos y `/estado.enlace.activo` vuelve a `false`; sin eventos espontáneos con `garantia=False`.

**ARX-30c · Señal biológica anómala (backend)** — ~2 h — **BLOQUEADA por ev3-d49**
- Archivos: `juego/partida.py`, `api/servidor.py`, `api/tests/test_eventos_arx30.py`.
- Hecho cuando: `"senal_biologica"` en ambas listas; `_evento_senal_biologica` elige una celda libre a distancia 3–6, la guarda en `self.senales = [{paso, celda, visitada}]`, avisa con el texto de cautela; `/moviles` emite `{nombre:"senal_biologica", efecto:"lectura_anomala", celdas:[celda], afirma_vida:false}` y `/estado.senal`; el efecto real es el de la ficha (A: al pisar la celda el puntaje suma `BONUS_SENAL` y queda `visitada`, sin tocar la victoria; B: la celda entra en `mision.objetivos` como sitio obligatorio; C: la celda queda con riesgo 0,6 durante N pasos y la misión la rodea). Ningún texto del motor ni de la API contiene «vida» sin la negación.
- Pruebas (4): disparo por API; efecto elegido observable; `afirma_vida` es `false` y el aviso contiene «no confirma vida»; sin eventos espontáneos con `garantia=False`.

**ARX-30d · Cierre de los efectos en la escena (frontend)** — ~1,5 h — depende de 30a para el sismo; conectividad y señal se prueban con los datos de prueba de `adaptador.js` hasta que existan 30b y 30c
- Archivos: `api/static/moviles.js`, `api/static/efectos.js`, `api/static/app.js`, `api/static/adaptador.js` (solo los datos de prueba).
- Hecho cuando: tras cada `/estado`, la interferencia se apaga si `estado.enlace.activo` es `false` y el marcador biológico se quita si `estado.senal` es `null`; el evento `sismo` pinta las `celdas` como grietas en la escena (mismo material que los barrancos del terreno) sin volver a pedir `/mapa`; el texto de cautela sigue apareciendo siempre; ningún móvil malo corta el ciclo (regla E5 que ya existe).
- Pruebas: una carga con datos de prueba (`FUENTE_MOTOR.moviles = false` temporalmente en local) muestra y luego apaga interferencia y marcador; en Chrome con el motor real, un `POST /evento sismo` desde una instancia de prueba (puerto distinto del 8765) sacude la cámara y pinta grietas.

**ARX-30e · Control de eventos en la interfaz (frontend)** — ~1 h
- Archivos: `api/static/index.html`, `api/static/app.js`.
- Hecho cuando: en el panel de controles hay un selector con los eventos de `EVENTOS` y un botón «Disparar» que hace `POST /evento`, muestra la respuesta como aviso y registra la acción en el historial de pantalla; deshabilitado sin partida o con partida terminada. Cubre la interacción «sismo» de §9 y da a QA una forma de disparar eventos sin consola.
- Pruebas: en Chrome, cada evento del selector responde 200 y produce su efecto visible; con la partida terminada el botón está deshabilitado.

Orden sugerido: 30a → 30e → 30d (sismo) → cuando lleguen las fichas, 30b y 30c, y 30d termina la parte de conectividad y señal. Nada aquí depende de la suite completa; se corre una vez al final con turno.

## 6. Riesgos

- **Secuencia de meteoritos.** Compartir `_rng_ambiente` cambiaría la caída de meteoritos por semilla y el ejemplo del contrato §14. Mitigación: generador propio por evento y la prueba de regresión de 30a.
- **Ganabilidad (ARX-66).** Una grieta mal puesta puede aislar el refugio o un sitio. Mitigación: comprobación con `_alcanzables` antes de marcar; si ninguna celda es segura, el evento responde `ok: false` como hace el meteorito «sin celda libre».
- **Evaluación congelada.** Todos los eventos espontáneos quedan tras `garantia`; `TABLA_MODOS.md` y `/comparacion` no cambian. QA debe confirmarlo con la prueba de 3000 ticks.
- **Dos detenciones a la vez.** Si ev3-d48 elige B, la falla de sensor y el corte de enlace detienen al rover por mecanismos parecidos; hay que fijar el orden en `avanzar_ia` (primero falla, luego enlace) y que ambos descuenten en `_tick_ambiente`.
- **Modo manual.** `mover_jugador` también llama `_tick_ambiente`, así que los eventos caen en manual; la opción A de ev3-d48 toca `/mover` y hay que mantener el formato de respuesta de §14.
- **Interfaz desacoplada.** Los efectos visuales dependen de `includes("sismo"|"conectividad"|"senal")`: los nombres exactos de este plan deben respetarse o nada se ve.
- **Memoria y CPU.** Ninguna tarea requiere la suite completa; la repetición de la suite (6 min) pide turno del Orquestador y menos del 80 % de uso.
- **Sin producción.** Nada toca el 8765 mientras el usuario prueba; las instancias de QA van en otro puerto y nunca en el 8000.

## 7. Decisiones del usuario (fichas; las carga el Orquestador)

Las redacto completas en `docs\planes\ARX-30_fichas.json` con el esquema de la Bandeja (`project` «Trabajo», `group` «ARES-X», `order` 3000 + NN). Los identificadores siguen a ev3-d47, el último que existe.

**ev3-d48 · ¿Qué efecto real tiene la baja conectividad?** (bloquea ARX-30b)
- A (recomendada): en manual, cada orden se pierde con un 50 % mientras dura el corte (unos 4 pasos) y hay que insistir; en los modos de IA el rover sigue solo pero sin recomendaciones ni intervenciones. Unas 2 h.
- B: el rover se detiene esperando enlace, igual que en la falla de sensor, en todos los modos. Unas 1,5 h.
- C: el rover sigue y nada se bloquea, pero gasta batería extra buscando enlace. Unas 1,5 h.

**ev3-d49 · ¿Qué efecto real tiene la señal biológica anómala?** (bloquea ARX-30c)
- A (recomendada): aparece un punto de interés opcional; si el rover lo pisa, suma puntos (+20 sobre la fórmula de ev3-d24) y se anota «lectura anómala, no confirma vida». No cambia las reglas de victoria. Unas 2 h.
- B: el punto pasa a ser un sitio obligatorio más para ganar (cambia la victoria y la garantía de ARX-66). Unas 3 h.
- C: la lectura anómala marca la celda como riesgo medio durante unos pasos y la misión la rodea; sin puntaje. Unas 1,5 h.

Lo que **no** necesita ficha: el efecto del sismo (lo fija el detalle de ev3-d41 A), las probabilidades por nivel y el número de grietas (supuestos de simulación, constantes nombradas), el control de eventos de la interfaz (interacción pedida por el PDF §9).

## 8. Verificación (para QA)

1. Pruebas acotadas, en este orden y sin `-n auto`:
   ```
   python -m pytest -q api/tests/test_eventos_arx30.py
   python -m pytest -q api/tests/test_meteorito.py juego/tests/test_partida.py
   ```
   Todo en verde y la prueba de regresión de meteoritos sin cambios.
2. En una instancia de prueba (puerto ≠ 8765 y ≠ 8000, `TestClient` o uvicorn aparte): `POST /partida` con `semilla 5, nivel medio, tamano pequeno`; `POST /evento {"nombre":"sismo"}`; comprobar en `/mapa` que las celdas de `eventos_del_paso` son BARRANCO, en `/estado.avisos` el aviso y en `/historial` una fila `REPLAN-SISMO` si la ruta pasaba por ahí.
3. En Chrome (skill `prueba-juego-chrome`, contra la instancia de prueba): el sismo sacude la cámara y pinta grietas; la interferencia se enciende con el corte y se apaga al terminar; el anillo y la etiqueta «anomalía, no confirma vida» aparecen con la señal y desaparecen al pisarla o expirar; el selector de eventos dispara cada uno; ninguna consola con errores `[movil …]`.
4. Buscar en el motor, la API y la interfaz que ningún texto afirme vida: `grep -rni "vida" juego api/servidor.py api/static --include=*.py --include=*.js` debe mostrar solo «no confirma vida», «puntos de vida» de los drones y «vivo/vivos».
5. Suite completa (6 min, un solo trabajo pesado, con turno): 342 + las nuevas pruebas en verde.
6. Documentación (paso Docs, misma rama): contrato §10 (`celda` → `celdas`, los tres eventos nuevos y los campos `enlace`/`senal` de `/estado`), §14 (sismo), matriz §7 (meteorito «Cumple», los tres nuevos con su evidencia) y §9 (sismo como interacción cumplida), docstring de `/moviles` (obstáculos móviles son ARX-29), `OPERACION_MOTOR.md` y `CONTEXTO_AGENTES.md` (remoto en GitHub, si GitOps lo confirma).
