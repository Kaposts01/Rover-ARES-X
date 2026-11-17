# Plan ARX-28f · Escenario acotado donde la RNA sea la única alerta temprana (ev3-d63 A)

Planner: `Esp_Planner`, 2026-11-17. Rama: `feat/arx-28-ablaciones` (mismo frente que ARX-28b; worktree `ares_x-wt-28`). Decisión ev3-d63 A del Maestro por delegación. Aporta a **M2** (variar la RNA altera una decisión o ruta) y **M19** (ablaciones comparables); de paso a **M7** (vínculo observable RNA → seguridad).

**Estado: cerrado en negativo en el control previo (28f-a, 17/11/2026).** Recall de barranco sin `borde_barranco` = 0,000 en las dos particiones y con los dos ruidos, frente a 0,70–0,80 con los rasgos normales. Resultados en `docs/planes/ARX-28_calibracion.md`, sección «28f: recall sin borde». Por el umbral de 0,5, no se corren 28f-b ni 28f-c, y el escenario `exigente_rna` no se crea. Solo queda 28f-d (cierre de docs).

## 1. Contexto

Medido en `docs/planes/ARX-28_calibracion.md` y `docs/TRAZA_DIVERGENCIAS_exigente.csv` (rama `feat/arx-28-ablaciones`): en el escenario exigente apagar la RNA cambia decisión, velocidad o ruta en 2 de 20 semillas (4 y 18); apagar el difuso en 20 de 20 y el AG en 12. Ninguna rejilla de `ruido` × `p_detectar` separa a la RNA, y `prob_fallo > 0` derrumba a las cuatro variantes por igual (`V-SENSOR-NAN` → `MODO_SEGURO`). Se pide una variante **declarada** del escenario donde parte del peligro no esté en el mapa estimado ni lo vea el sensor de proximidad, y la RNA sea la única alerta temprana, con criterio de éxito fijado antes de medir.

## 2. Estado actual: de dónde saca cada veto el supervisor

| Veto / decisión | Fuente | Evidencia | Qué significa para la RNA |
|---|---|---|---|
| `V-SENSOR-NAN` | sensor (lectura NaN) | `integracion.py:41-42`; `simulador.py:134-137` | No se toca (límite 3) |
| `V-BATERIA-0` | estado del rover | `integracion.py:43-44` | Independiente |
| `V-BORDE-BARRANCO` | **mapa real, sin ruido**: `SensorSuite._barrancos_vecinos` lee `mundo.tipo` en los 4 vecinos | `simulador.py:160-167`; `integracion.py:170, 177`; se evalúa **antes** que la RNA (`:45` frente a `:47-50`) | Todo barranco adyacente se detecta con certeza un paso antes de pisarlo: el mismo horizonte que la RNA (clasifica la celda de enfrente, `rna.py:27-30`). **Es lo que hace redundante a la RNA para barrancos.** |
| riesgo del mapa (`V-RUTA-CON-RIESGO`) | mapa estimado: `mapa_estimado` muestrea el **mapa real** con `p_detectar` (`genetico.py:31-35`); se completa con los barrancos vecinos (**reales**, `integracion.py:174-175`) y con el sensor de proximidad (`_actualizar_mapa_estimado`, `:258-262`) | `integracion.py:192`: anula la decisión del supervisor, incluida la de la RNA | Con `p_detectar` 0,8 (congelado) u 0,4 (exigente), la mayoría de los peligros ya está marcada antes de salir |
| `V-OBSTACULO-EN-RUTA` | sensor de proximidad (ruidoso) | `integracion.py:271-277`, `:196-197`; el sensor mide la distancia a la **primera celda no LIBRE**, es decir, ve obstáculos **y barrancos** (`simulador.py:142-148`) | El sensor de proximidad también «ve» los desniveles; hoy no hay peligro invisible para él |
| `V-RNA-BARRANCO`, `V-RNA-OBSTACULO` | RNA (`p > 0,5`) | `integracion.py:47-50` | Se evalúan después del borde y quedan anulados por el riesgo del mapa |
| `D-DIFUSO-LENTO` | difuso | `integracion.py:51-52` | Independiente |
| Física | `paso_fisico` nunca entra en obstáculo ni barranco; cuenta `colisiones` y replanifica | `simulador.py:209-216`; `integracion.py:218-221` | **No existen caídas en la física**: pisar un barranco es imposible; el costo de no anticiparlo es una colisión y una replanificación |

Rasgos de la RNA (`rna.py:23-40`): `proximidad_frontal_m` y `borde_barranco` vienen del **mismo** `SensorSuite` que usa el supervisor (`integracion.py:169-170`); `gradiente_altura_m` y `vibracion` se calculan desde el mapa real con ruido propio. Dos hechos que limitan cualquier escenario: (a) la elevación de `generar_mundo` es una suma acumulada suave que **no baja en los barrancos** (`simulador.py:112`), así que el gradiente no informa de un precipicio; (b) la vibración media es 0,2 libre, 0,4 barranco y 0,6 obstáculo con ruido σ = 0,3 (`rna.py:20, 34`): la separación libre/barranco es de dos tercios de la desviación. Sin el rasgo `borde_barranco`, la RNA queda casi sola con la vibración.

## 3. Propuesta: escenario `exigente_rna` con el desnivel invisible para los sensores

Variante declarada en `ESCENARIOS` de `juego/comparacion.py`, aplicada **sobre la instancia** de la misión en el arnés, sin tocar `simulador.py`, `integracion.py` ni ningún veto del juego:

1. **Sensor sin desnivel.** Una subclase `SensorSinDesnivel(SensorSuite)` definida en `juego/comparacion.py` que redefine `leer`: la proximidad se detiene solo en `OBSTACULO` (ignora `BARRANCO`) y `celdas_barranco` vale siempre `[]` (LIDAR de borde apagado). `_ruidoso` y `prob_fallo` quedan intactos, así `V-SENSOR-NAN` no cambia. Se instala con `m.sensor = SensorSinDesnivel(rng=m.rng, ruido=R)`.
2. **Mapa estimado sin barrancos.** `m.riesgo = mapa_estimado(...)` recalculado solo sobre `OBSTACULO`: los barrancos quedan con el prior bajo (0,05). Función `_mapa_estimado_sin_barrancos` en `juego/comparacion.py`, misma firma y semilla que `mapa_estimado`; después `m._planear()`.
3. Lo demás, como el exigente: nivel 5 (9 barrancos en 20×30), `ruido 0,6`, `p_detectar 0,4` para los obstáculos, `prob_fallo None`.
4. Declaración en el JSON y en la nota del contrato: «en `exigente_rna` los sensores de proximidad y de borde no detectan desniveles; la única alerta anticipada de barranco es la clasificación de la RNA; la física sigue impidiendo la caída».

Con esto, en `sin_rna` el rover llega al barranco sin aviso: `paso_fisico` lo bloquea, suma una colisión, anota `V-CELDA-BLOQUEADA` y replanifica (`integracion.py:218-221`). En `hibrido`, si la RNA clasifica la celda de enfrente como barranco, veta un paso antes (`V-RNA-BARRANCO`) y replanifica sin colisión. La diferencia esperada es en colisiones, motivos y ruta.

Alternativas descartadas, una línea cada una:
- Dejar el borde encendido para la RNA y apagado para el supervisor: comparten el mismo sensor (`integracion.py:169-170`); separarlos exige tocar `Mision` o el supervisor (límite 3).
- Bajar la elevación en los barrancos para que el gradiente los delate: cambia `generar_mundo` y el mapa congelado.
- Reentrenar la RNA con el rasgo de borde apagado: fuera de alcance por límite 3.
- Subir la prioridad de la RNA en el supervisor: es tocar un veto del juego.

## 4. Riesgo principal, y por eso un control previo

Sin `borde_barranco`, la RNA depende de la vibración (SNR ≈ 0,67) para distinguir barranco de libre; su recall de barranco en esas condiciones es desconocido y puede ser bajo. En ese caso el escenario no separa nada aunque el peligro sea invisible. Por eso la primera subtarea mide eso **fuera de línea en segundos** y decide si vale correr las 20 semillas.

## 5. Criterio de éxito (fijado antes de medir)

- **Principal:** en 20 semillas (1–20) del escenario `exigente_rna`, apagar la RNA cambia decisión, velocidad o ruta en **al menos 5 semillas** (misma herramienta que hoy: `scripts/traza_divergencias.py`, `trazar_divergencias(semillas, "exigente_rna")`).
- **Se informa aparte**, sin condicionar el principal: diferencia de éxito y de **colisiones** entre `hibrido` y `sin_rna` (no hay caídas en la física; las colisiones son el intento bloqueado de pisar el barranco), y el número de `V-RNA-BARRANCO` del híbrido.
- **Control previo (28f-a):** recall de barranco de la RNA ya entrenada sobre muestras del dataset con `borde_barranco = 0` y `proximidad` calculada ignorando barrancos. Si es **menor que 0,5**, se cierra con resultado negativo **sin correr las 20 semillas**: la RNA no puede ser alerta temprana con sus rasgos actuales.
- Si el principal no se alcanza, se cierra con resultado negativo, se registra en `ARX-28_calibracion.md` y en el informe, sin más intentos.

## 6. Tareas (tope total: medio día; estimado 4 h)

**ARX-28f-a · Control previo del recall sin borde (backend)** — ~1 h, sin turno pesado (segundos de cómputo)
- Archivos: script temporal en la carpeta de la sesión; resultado en `docs/planes/ARX-28_calibracion.md` (sección nueva «28f: recall sin borde»).
- Hecho cuando: con `rna_entrenada()` y `generar_dataset` de `rna.py`, sobre los mapas de test de `particion_por_mapas`, se mide recall y precisión de barranco con los rasgos del escenario (borde 0, proximidad sin desniveles) frente a los rasgos normales; se anota la tabla y el veredicto «seguir» o «cerrar negativo».
- Pruebas: ninguna automática; la tabla es la evidencia.

**ARX-28f-b · Escenario `exigente_rna` en el arnés (backend)** — ~1,5 h — solo si 28f-a dice «seguir»
- Archivos: `juego/comparacion.py` (`SensorSinDesnivel`, `_mapa_estimado_sin_barrancos`, entrada `exigente_rna` en `ESCENARIOS`, aplicación en `partida_variante`), `juego/tests/test_comparacion_escenarios.py`, `scripts/comparacion_politicas.py` y `scripts/traza_divergencias.py` solo si no aceptan ya cualquier clave de `ESCENARIOS`.
- Hecho cuando: `partida_variante(1, "hibrido", "exigente_rna")` tiene `sensor` de la subclase, `riesgo` sin barrancos marcados y `borde_barranco` siempre falso; los escenarios `congelado` y `exigente` producen filas idénticas a antes (regresión); la nota declarativa del punto 4 va en la salida de `comparar`.
- Pruebas (4): sensor ignora barrancos (distancia a un barranco frontal = 20 m; a un obstáculo, su distancia); `celdas_barranco == []`; mapa estimado sin barrancos marcados; regresión de los dos escenarios anteriores con 3 semillas.

**ARX-28f-c · Medición de 20 semillas (backend)** — ~1 h con turno pesado (unos 6 minutos de cómputo por el precedente de 28a)
- Archivos: `docs/COMPARACION_POLITICAS_exigente_rna.json`, `docs/TRAZA_DIVERGENCIAS_exigente_rna.csv` (generados), `docs/planes/ARX-28_calibracion.md` (resultado y veredicto).
- Hecho cuando: están los dos archivos y la sección con el conteo de semillas divergentes, la diferencia de éxito y colisiones, y los `V-RNA-BARRANCO`; veredicto según la sección 5, sin segundo intento.

**ARX-28f-d · Cierre (Docs, misma rama)** — ~0,5 h
- `docs/CONTRATOS_GRAFICOS.md` §7 (escenario nuevo y su declaración), `INFORME_TECNICO.md` §4 (resultado positivo o negativo, con la causa de la redundancia de la sección 2), `docs/MATRIZ_REQUISITOS_PDF.md` (RF-14, CA-08).

Si 28f-a cierra en negativo, solo se hace 28f-d con el resultado negativo (~0,5 h): el tope se respeta con margen.

## 7. Paralelismo

| Frente | Archivos | ¿Comparte con ARX-28f? | Veredicto |
|---|---|---|---|
| `feat/arx-28-ablaciones` (ARX-28b) | `juego/comparacion.py`, `juego/tests/test_comparacion_escenarios.py`, `scripts/*`, `docs/*` | **sí, los mismos** | ARX-28f **va dentro de este frente**, en la misma rama, después del estado actual de 28b (no en paralelo con él: el líder los encadena) |
| `feat/arx-80-bitacora` (gitops) | `api/servidor.py`, `integracion.py`, `juego/conduccion.py`, `juego/partida.py`, `difuso.py`, `simulador.py`, pruebas | no | **puede correr en paralelo** |
| ARX-84 (prueba de eventos simultáneos) | `api/tests/test_eventos_arx30.py` o archivo nuevo de pruebas | no | **puede correr en paralelo** |
| ARX-33/31/83 (plan en curso) | `juego/partida.py`, `api/servidor.py`, módulo térmico nuevo | no | **puede correr en paralelo** |
| ARX-28c (física de la velocidad) | `juego/partida.py`, `juego/comparacion.py` | sí (`comparacion.py`) | en fila, detrás de 28f |

Turno pesado: solo 28f-c (uno a la vez en el equipo).

## 8. Decisiones del usuario

Ninguna nueva: ev3-d63 A fija el alcance, el criterio y el tope. No se toca ningún veto, no se reentrena, el congelado no cambia.

## 9. Verificación (QA)

1. `python -m pytest -q juego/tests/test_comparacion_escenarios.py` en verde, con la regresión de `congelado` y `exigente`.
2. Revisión estática: `simulador.py`, `integracion.py`, `rna.py` sin cambios (`git diff main -- simulador.py integracion.py rna.py` vacío en la rama).
3. Los archivos de 28f-c existen y la sección de `ARX-28_calibracion.md` declara el veredicto con la regla de la sección 5, sin reinterpretarla.
4. `docs/COMPARACION_POLITICAS.json` y `TABLA_MODOS.md` sin cambios.
