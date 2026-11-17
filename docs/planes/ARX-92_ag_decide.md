# Plan ARX-92 · Que el AG decida el orden de visita en el juego y en el arnés (ev3-d71 A)

Planner: `Esp_Planner`, 2026-11-17. Base: `feat/regen-cifras` (`22dc129`, worktree `ares_x-wt-regen`; trae 45, 90, 91, 28 y 28c con las cifras regeneradas). Rama propuesta: `feat/arx-92-ag-decide`, desde `feat/regen-cifras`. Aporta a **M2** (variar el AG altera la ruta), **M8** (rutas completas y reparación), **M10** (pesos con efecto), **M11** (candidatos verificables), **M19** (ablaciones honestas) y, de rebote, **M1**.

## 1. Contexto

Hechos medidos por Esp_QA (`pedidos/2026-11-17_qa_arx28/`, `pedidos/2026-11-17_qa_motor/INFORME.md`): `Partida` instala `_ag_con_todos_los_sitios` (`juego/partida.py:242-287` en la base) y con 6 sitios o menos elige la permutación más corta por BFS; la salida del AG solo es respaldo (`:287`). Con pesos extremos el orden del juego no cambia en 18 de 18 casos y la salida del AG sí en 12 de 18. El AG puro devuelve rutas con menos sitios que los pendientes en 5 de 6 casos. En el arnés, `sin_ag` es vecino más cercano, `ruta_corta` es voraz y `ag_puro` es el envoltorio exhaustivo con riesgo congelado: ninguna mide el AG. El Maestro decidió (ev3-d71 A) que el AG decida el orden en el juego y en el arnés.

## 2. Estado actual (comprobado en el código de `feat/regen-cifras`)

- **Cromosoma:** `K` celdas de paso entre `sitios + celdas libres`, elegidas al azar sin reposición (`genetico.py:184-187`), con `K = k_puntos = 3` por defecto (`integracion.py:66, 83, 143`). Con 4 sitios (nivel ≥ 3) el cromosoma **no puede** contener todos los sitios; con 3 solo si los tres puntos caen en sitios. `decodificar` (`:136-158`) une los puntos con BFS y **descarta** un punto sin camino (reparación), pero no añade los sitios que faltan. El término `ciencia` del fitness (`:168`) premia los sitios visitados, pero compite con distancia, energía, riesgo y tiempo (`:169-177`): una ruta corta que salta sitios puede ganar.
- **Envoltorio:** `_ag_con_todos_los_sitios` (`juego/partida.py:242-287`) llama al AG, lo ignora y elige la permutación más corta por el mapa estimado (`riesgo < 0,5`), con paradas si hay estaciones; devuelve la ruta del AG solo si ninguna permutación es viable. Instalado en `:348`; `_planear` reemplazado en `:357`.
- **Garantía:** `_es_ganable` (`:191-239`) acepta el mapa si **alguna** permutación cabe en la batería con `MARGEN_ENERGIA`; ARX-79 (ev3-d66 A) le añade un factor de seguridad. La ruta que juega la misión es la misma permutación que validó la garantía: por eso hoy la promesa «partida ganable» y el orden jugado coinciden.
- **Arnés** (`juego/comparacion.py:26-28, 97-115`): `sin_ag` = `_orden_voraz` (vecino más cercano); `ruta_corta` = voraz sin riesgo ni RNA ni difuso; `ag_puro` = envoltorio con riesgo congelado (docstring `:109-110` ya lo declara: «no mide el AG; se redefine en ARX-92»).
- **Laboratorio:** `GET /ag` (`api/servidor.py:808-846`) corre un `GeneticPlanner` independiente y muestra candidatos y pesos; es el único lugar donde el AG se ve decidir.

## 3. Medido, no estimado (17/11, script `medir_arx92.py` en la carpeta de la sesión, sobre `22dc129`, 20×30, pesos por defecto, 155 s de CPU en total; el tope pedido era ~2 min: me pasé 35 s y lo informo)

**Orden de visita: AG original frente a permutación más corta** (`Mision._optimizar_ag` sin envoltorio frente a `m.ruta` del envoltorio, misma semilla y mismo mapa estimado):

| Escenario | Semillas medidas | Orden distinto | Ruta del AG incompleta (omite sitios) | Sitios por mapa |
|---|---|---|---|---|
| congelado | 20 | **17 de 20** (iguales: 3, 4, 13) | **16 de 20** (completas: 3, 4, 13, 15) | 3 |
| exigente | 13 de 20 (tope de tiempo) | **13 de 13** | **12 de 13** (completa: 9) | 4 |

**Resultado de partida** con el AG original decidiendo (envoltorio quitado sobre la instancia, misión completa hasta estado terminal o 400 pasos), en las semillas del congelado donde el orden difiere (13 de 17 medidas por el tope):

| Semilla | Híbrido actual (estado, pasos, batería, sitios) | AG original decide | Lectura |
|---|---|---|---|
| 1 | EXITO 46 · 49 · 3/3 | **FRACASO** 46 · 49 · 2/3 | omite un sitio y la recuperación no lo rescata |
| 2 | EXITO 52 · 39 · 3/3 | EXITO 74 · 18 · 3/3 | +22 pasos, −21 de batería |
| 5 | EXITO 34 · 65 · 3/3 | EXITO 34 · 65 · 3/3 | igual: la ruta incompleta pasaba por el sitio |
| 6 | EXITO 40 · 57 · 3/3 | EXITO 77 · 17 · 3/3 | +37 pasos |
| 7 | EXITO 43 · 52 · 3/3 | EXITO 70 · 27 · 3/3 | +27 |
| 8 | EXITO 43 · 50 · 3/3 | **FRACASO** 47 · 42 · 1/3 | |
| 9 | EXITO 50 · 35 · 3/3 | **FRACASO** 39 · 47 · 2/3 | |
| 10 | EXITO 51 · 51 · 3/3 | **FRACASO** 32 · 69 · 0/3 | el AG fue directo al refugio |
| 11 | EXITO 54 · 36 · 3/3 | EXITO 69 · 23 · 3/3 | +15 |
| 12 | EXITO 51 · 54 · 3/3 | EXITO 76 · 19 · 3/3 | +25 |
| 14 | EXITO 37 · 58 · 3/3 | **FRACASO** 61 · 35 · 2/3 | |
| 15 | EXITO 43 · 58 · 3/3 | EXITO 67 · 31 · 3/3 | la única con ruta completa: +24 pasos por un orden peor |
| 16 | EXITO 45 · 52 · 3/3 | **FRACASO** 44 · 54 · 1/3 | |

Resumen: **6 de 13 fracasos** y, en las que ganan, entre 15 y 37 pasos más y 20 a 40 puntos menos de batería. Ninguna mejora. Lo que el envoltorio esconde no es un detalle: es que el AG actual, con su cromosoma de 3 puntos libres, **no resuelve el problema que la victoria exige** (visitar todos los sitios). Eso es un defecto de M8 (decodificación y reparación), independiente de quién elija el orden.

Sin medir (por el tope): resultado de partida en el exigente (13 semillas con orden distinto, 12 con ruta incompleta: se espera lo mismo o peor, con 4 sitios y K = 3) y el efecto de los pesos sobre el orden en una vía corregida (no existe aún el código). Cuando el Orquestador dé turno, el mismo script mide el exigente en unos 2 minutos más.

## 4. Las vías, con costo y riesgo

| Vía | Qué hace | Costo | Riesgo | Veredicto |
|---|---|---|---|---|
| **(a) Restaurar el AG original sobre la instancia y arreglar las rutas incompletas** | Quitar el envoltorio; corregir `decodificar` para que repare añadiendo los sitios que faltan (al final o en el mejor hueco) y que el cromosoma incluya los sitios | ~3 h motor + pruebas | **Medido:** sin la reparación, 6 de 13 fracasos. Con la reparación «añadir al final», el AG seguiría optimizando puntos libres y el orden de los sitios quedaría al azar de la reparación: el fitness no lo gobierna. Pierde la propiedad de que la ruta jugada sea la que validó la garantía | Insuficiente sola |
| **(b) El envoltorio elige entre las permutaciones viables por el fitness del AG con pesos, no por largo** | Mantener la enumeración de permutaciones (viabilidad por batería y garantía) y puntuar cada ruta con `GeneticPlanner.evaluar` (ciencia, distancia, energía, riesgo, tiempo) con los pesos vigentes; elegir la de mejor fitness | ~2 h | El AG no «ejecuta» nada: es una búsqueda exhaustiva puntuada por su función de fitness. Honesto si se declara así; con 3 o 4 sitios la exhaustiva es óptima y el AG como algoritmo no participa (M9 y M11 se demuestran en `/ag`, no en el juego) | Mínimo honesto y seguro |
| **(c) AG real sobre el orden: cromosoma = permutación de los sitios pendientes (+ puntos de paso opcionales), decodificación que garantiza todos los sitios, fitness multicriterio, y viabilidad por batería como restricción dura** | `GeneticPlanner` nuevo modo «orden»: genes = sitios, cruce OX, mutación por intercambio, elitismo; opcional un punto de paso entre sitios para la forma del camino; reparación = insertar sitios omitidos; descarte si excede la batería | ~6 h motor + 1 h arnés + pruebas | Con 3–4 sitios el AG converge a la misma permutación que la exhaustiva (ver §6); su aporte aparece con más sitios o con el fitness multicriterio (riesgo y tiempo, no solo largo). Hay que fijar qué hace si su mejor orden no es viable: cae a la permutación viable de mejor fitness (vía b) y lo anota | La que cumple ev3-d71 A en su letra: «el AG decide» |

Propuesta: **(b) ahora como base segura y (c) encima**, en la misma tarea: (b) deja al juego y al arnés usando el fitness con pesos desde el primer commit (M10 con efecto real); (c) convierte la elección en un AG verdadero sobre el orden, con (b) como red de seguridad para la garantía. (a) se descarta por la medición.

## 5. Ablaciones redefinidas, con nombres honestos

| Variante | Qué decide el orden | Qué más cambia | Para qué sirve |
|---|---|---|---|
| **híbrido** | el AG (vía c; mientras no exista, vía b) con pesos por defecto, sobre el mapa estimado | RNA y difuso activos | sistema completo |
| **sin AG: permutación más corta** | la permutación de menor largo por el mapa estimado (lo que hoy hace el envoltorio) | RNA y difuso activos | aislar el aporte del fitness multicriterio frente al largo |
| **sin AG: vecino más cercano** | `_orden_voraz` (lo que hoy se llama `sin_ag`) | RNA y difuso activos | control clásico de M19 |
| **AG puro** | el AG (vía c) con el mapa de riesgo **congelado** al inicio y sin RNA ni difuso | `_congelar_riesgo` ya existe | el AG solo, sin percepción ni control de velocidad |
| ruta corta | voraz sin riesgo, sin RNA ni difuso (como hoy) | — | línea base de M19 |

Aporte del AG medido contra cada una (en 20 semillas × 2 escenarios, tras implementar): **frente a permutación más corta** = cuántas semillas cambian de orden y cuánto cambian éxito, pasos, batería final y riesgo medio de la ruta (el fitness debe ganar en riesgo o energía, no en largo); **frente a vecino más cercano** = lo mismo; **AG puro frente a híbrido** = aporte de RNA y difuso con el AG fijo. Criterio de éxito fijado antes: el híbrido no empeora el éxito frente a «permutación más corta» en ninguno de los dos escenarios y mejora el riesgo medio de la ruta o la batería final en al menos 5 de 20 semillas del exigente; si no, se declara que con 3–4 sitios el fitness no separa (§6).

## 6. Pregunta franca: con 3 o 4 sitios, ¿aporta algo el AG frente a la exhaustiva?

**En el orden, no.** Con 3 sitios hay 6 permutaciones; con 4, 24. La exhaustiva las evalúa todas en milisegundos (los largos se cachean por par) y encuentra el óptimo exacto para cualquier fitness; un AG con población 30 y 30 generaciones sobre 24 individuos posibles solo puede empatar o perder. Decir que «el AG decide el orden» con 4 sitios es una demostración de operadores (M9, M11), no de utilidad (M2, M19). La medición de hoy lo confirma en la única semilla con ruta completa (congelado 15): el AG eligió un orden peor (+24 pasos).

**Dónde sí puede aportar, y qué propongo:**
1. **Más sitios en el exigente.** Con 8 sitios hay 40 320 permutaciones (la exhaustiva aún las recorre en segundos con largos cacheados: sigue sin necesitar AG); con **10 sitios** son 3,6 millones y la exhaustiva ya no es razonable por paso: ahí el AG es la herramienta. Un exigente con 10 sitios cambia la duración de la partida y la batería (hoy 84 en nivel 5): hay que recalibrar. Es una decisión de evaluación → **ficha ev3-d73**.
2. **Fitness multicriterio real** (ya existe en `evaluar`: ciencia, distancia, energía, riesgo, tiempo; M10): con pesos distintos de «largo», la permutación de menor largo deja de ser la mejor y el fitness sí decide. Esto funciona con 4 sitios y es lo que (b) y (c) entregan de inmediato.
3. **Forma del camino, no solo orden.** El cromosoma actual (puntos de paso libres) es el subproblema «laberinto»: elegir por dónde pasar entre dos sitios para evitar riesgo o giros. Es donde el AG tiene espacio de búsqueda grande incluso con 3 sitios. La vía (c) lo conserva como gen opcional entre sitios.

Efecto en la meta: M1 (el AG vuelve a estar en el flujo real, no de adorno), M2 (variar el AG o sus pesos altera la ruta: medible), M8 (rutas completas por construcción, reparación explícita), M10 (pesos con efecto en el juego, no solo en `/ag`), M19 (ablaciones comparables y honestas). Sin más sitios, M2 y M19 se demuestran por el fitness multicriterio; con 10 sitios, además por la escala.

## 7. Convivencia con la garantía (ARX-79, ev3-d66 A)

La garantía promete que **existe** un orden que cabe en la batería con margen (y factor de seguridad). Si el AG elige otro orden, la promesa sigue valiendo solo si ese orden también cabe. Regla propuesta, declarada: el AG (vía c) solo puede elegir entre órdenes **viables** (cada candidato se valida con el mismo `_plan_con_paradas` y factor de ARX-79; los inviables reciben la penalización dura y no pueden ganar); si al final ninguno de sus candidatos es viable, cae a la permutación viable de mejor fitness (vía b) y anota `AG-FALLBACK-GARANTIA` en la bitácora. Así la garantía no valida «la permutación más corta» sino «al menos una viable», y la misión juega una viable. La prueba de regresión: en las 20 semillas de cada nivel donde la garantía aceptó el mapa, la ruta elegida cabe en la batería estimada.

## 8. Tareas (rama `feat/arx-92-ag-decide` desde `feat/regen-cifras`)

**ARX-92a · Envoltorio por fitness (vía b) (backend)** — ~2 h — M10, M2
- Archivos: `juego/partida.py` (`_ag_con_todos_los_sitios` → `_orden_por_fitness`: enumera permutaciones viables, puntúa con `GeneticPlanner.evaluar` sobre la ruta completa y los pesos de la partida, elige la mejor; declara `metodo: "exhaustiva+fitness"` en un atributo para `/estado`), `juego/tests/test_orden_fitness_arx92.py`.
- Hecho cuando: con pesos por defecto la elección puede diferir de la más corta (se mide: cuántas de 20 semillas por escenario); con `pesos = {"distancia": 5, resto 0}` coincide con la más corta en 20 de 20 (prueba de coherencia); con `riesgo = 5` el riesgo medio de la ruta elegida es ≤ al de la más corta en 20 de 20; la ruta elegida es siempre viable.
- Medición (sin turno, ~1 min): tabla de órdenes distintos y Δ riesgo medio por escenario.

**ARX-92b · Decodificación completa y reparación del AG (backend)** — ~1,5 h — M8
- Archivos: `genetico.py` (`decodificar`: tras recorrer el cromosoma, insertar los sitios no visitados por el mejor hueco por BFS antes del refugio; contar como reparación), `tests/test_genetico.py`.
- Hecho cuando: toda ruta decodificada visita todos los sitios o es `inviable_sin_camino`; `/ag` ya no devuelve candidatos con menos sitios (hoy 5 de 6); los contadores de reparación se exponen.

**ARX-92c · AG sobre el orden (vía c) (backend)** — ~4 h — M2, M8, M9, M10, M11 — depende de 92a y 92b
- Archivos: `genetico.py` (modo `orden`: cromosoma = permutación de sitios + punto de paso opcional por tramo; cruce OX; mutación por intercambio y por desplazar un punto de paso; elitismo; viabilidad por batería y factor de garantía como restricción dura), `juego/partida.py` (la misión usa el modo `orden`; fallback a 92a con `AG-FALLBACK-GARANTIA`), `integracion.py` solo lectura, `api/servidor.py` (`/ag` muestra el modo y los candidatos como órdenes), `tests/test_genetico.py`, `juego/tests/test_ag_orden_arx92.py`.
- Hecho cuando: con 3 sitios el AG alcanza el óptimo de la exhaustiva en 20 de 20 semillas (coherencia); el historial por generación y los 3 candidatos son órdenes completos; determinismo por semilla; la ruta jugada es viable en 20 de 20 por nivel.

**ARX-92d · Ablaciones honestas en el arnés (backend)** — ~1,5 h — M19 — depende de 92a (y de 92c para «híbrido = el AG decide»)
- Archivos: `juego/comparacion.py` (`sin_ag_mas_corta`, `sin_ag_vecino` (renombrada desde `sin_ag`), `ag_puro` con el AG real y riesgo congelado), `juego/tests/test_comparacion_escenarios.py`, `scripts/comparacion_politicas.py`, docstring de módulo.
- Hecho cuando: las cinco variantes de §5 corren en los dos escenarios; la tabla de atribución de `trazar_divergencias` distingue las dos ablaciones del AG; regeneración de los JSON (turno) y criterio de §5 evaluado.

**ARX-92e · Laboratorio: candidatos como órdenes y nota declarativa (frontend)** — ~1 h — M11, M17 — depende de 92c
- Archivos: `api/static/laboratorio.js` (candidatos como secuencia de sitios con su desglose; texto del método vigente: exhaustiva por fitness o AG sobre el orden).

## 9. Paralelismo

| Frente | Archivos | ¿Comparte con ARX-92? | Veredicto |
|---|---|---|---|
| `feat/regen-cifras` (base) | `comparacion.py`, `partida.py` (28c, 90), JSON, `TABLA_MODOS` | es la base | ARX-92 sale de ahí; la **regeneración definitiva** de cifras va **después** de 92d (las variantes cambian) |
| `feat/arx-33-31-83-motor` (faltan 33b, 31b, 83b, 33c, 83c, 89b) | `partida.py`, `servidor.py`, `app.js`, `termico.py` | **sí**: `partida.py` (92a, 92c) y `servidor.py` (92c) | **en fila**: integrar la rama del motor antes de 92a, o 92a trae `main` al final; zonas distintas de `partida.py` (envoltorio `:242-287` frente a estados, eventos, térmico) |
| ARX-47 (pesos en vivo; plan `ARX-47_pesos.md`) | `servidor.py`, `partida.py`, `laboratorio.js` | **sí, en todo** | **ARX-92 absorbe 47b** (los pesos de la partida deciden el orden) y 47a/47c pasan a depender de 92a; no abrir 47 aparte |
| ARX-79 (garantía) | `partida.py` (`_es_ganable`, `_plan_con_paradas`) | **sí**: 92a y 92c usan `_plan_con_paradas` y el factor | **en fila**: 79b antes que 92a, o misma rama |
| `fix/arx-90-percepcion`, ARX-45, ARX-91 | ya en la base | no | — |
| ARX-28d/28e, ARX-36, ARX-34 | `servidor.py` (28d), interfaz | 28d comparte `servidor.py` con 92c | 28e, 36, 34 en paralelo; 28d coordinar |

Conclusión: ARX-92 **va en fila** detrás de la rama del motor y de ARX-79b en `partida.py`, y absorbe ARX-47b. Mientras tanto, 92b (`genetico.py` y `tests/test_genetico.py`) **puede correr ya en paralelo**: no comparte archivos con nadie. Turno pesado solo para regenerar cifras tras 92d.

## 10. Decisiones del usuario (fichas; las responde el Maestro)

- **ev3-d72 · ¿Qué vía para que el AG decida?** Evidencia medida (§3): con el AG actual decidiendo, 6 de 13 fracasos y 15–37 pasos más en el congelado; 16 de 20 rutas incompletas; QA: pesos extremos sin efecto en 18 de 18. Opciones: **A) (b) + (c): exhaustiva por fitness ahora y AG sobre el orden encima**, con fallback declarado a la garantía (M2, M8, M9, M10, M11, M19; ~9 h en 5 subtareas) **recomendada**; B) solo (b): exhaustiva por fitness con pesos (M10, M2 parcial; M9 y M11 solo en `/ag`; ~2 h); C) (a): restaurar el AG actual con reparación mínima (M8 parcial; ~3 h; medido peor: el orden lo decide la reparación, no el fitness). Duda declarada: si el plazo de la entrega no admite 9 h, B es honesta si el informe dice que el AG se demuestra en el laboratorio y el fitness en el juego.
- **ev3-d73 · ¿Más sitios en el escenario exigente para que el AG tenga algo que optimizar?** Evidencia: 6 y 24 permutaciones con 3 y 4 sitios (exhaustiva en milisegundos); congelado s15: el AG eligió un orden peor. Opciones: **A) exigente con 10 sitios y batería recalibrada** (M2, M19 por escala; ~2 h + recalibración de 28a con turno + regeneración) **recomendada si se elige ev3-d72 A**; B) mantener 4 sitios y demostrar M2/M19 solo por el fitness multicriterio (0 h); C) 6 sitios (720 permutaciones: todavía exhaustiva; 1 h). Duda declarada: A alarga las partidas del exigente y cambia su dificultad; si el Maestro prefiere no tocar la duración, B.

## 11. Verificación (QA)

1. `python -m pytest -q tests/test_genetico.py juego/tests/test_orden_fitness_arx92.py juego/tests/test_ag_orden_arx92.py juego/tests/test_comparacion_escenarios.py`.
2. Viabilidad: en 20 semillas por nivel con `garantia=True`, la ruta inicial cabe en la batería estimada con el factor de ARX-79 (sin `AG-FALLBACK-GARANTIA` o con él anotado).
3. Coherencia: con `distancia = 5` y el resto 0, el orden coincide con la permutación más corta en 20 de 20; con 3 sitios el AG iguala a la exhaustiva en 20 de 20.
4. Aporte (§5): tabla de 20 semillas × 2 escenarios × 5 variantes tras regenerar (turno); criterio de éxito de §5 evaluado y declarado, positivo o negativo.
5. `/ag` sin candidatos incompletos; laboratorio con el método vigente en pantalla; consola limpia.
6. Docs: contrato §1 (`/ag`), §7 (variantes), MATRIZ §4 (M8–M11), INFORME §4 y §6 (qué decide el AG en el juego y por qué las cifras cambian), `docs/planes/ARX-47_pesos.md` marcado como absorbido.

## Dónde quedé
- 17/11 · Plan completo (11 secciones). Medición parcial anotada en §3 (exigente sin resultado de partida por el tope; el script `medir_arx92.py` de la carpeta de la sesión lo completa en ~2 min con turno).

## Umbral de empate de 92a (ev3-d74 B) · fijado antes de aplicarlo

Decisión del Maestro (ev3-d74 = B): bajo el umbral de empate gana la permutación más corta (regla de desempate declarada); los pesos no se tocan. Este plan no fijaba el criterio del umbral, así que se usa el percentil 90 del error absoluto de fitness del escenario exigente, como pidió el líder.

**Valor fijado: umbral de empate = 0,0223** (0,022256472696630815 sin redondear; unidades de fitness de `evaluar_ruta`, pesos por defecto).

**Cálculo.** Por cada una de las 20 semillas (1 a 20) del exigente: error de fitness = fitness de la ruta ejecutada (con el mapa de riesgo final) menos fitness de la ruta planificada (con el mapa estimado inicial), ambos con `GeneticPlanner.evaluar_ruta`. Se toma el valor absoluto y el percentil 90 (interpolación lineal de numpy) de las 20 cifras.

**Resultados medidos** (20 semillas por escenario, todas terminan en EXITO, ninguna toca el tope de 500):

| Escenario | Error de pasos real − estimado (media / mediana / máx / p90) | Error de fitness con signo (media / máx) | Error absoluto de fitness (media / mediana / máx / p90) |
|---|---|---|---|
| congelado | 1,6 / 1 / 5 / 3,1 | −0,0010 / +0,0022 | 0,0012 / 0 / 0,0105 / 0,0043 |
| exigente | 8,4 / 8 / 16 / 12 | −0,0112 / 0,0000 | 0,0112 / 0,0099 / 0,0243 / **0,0223** |

Lectura: en el congelado el error es casi nulo (los pasos extra son esperas y recargas; los movimientos efectivos difieren en 0,1 de media). En el exigente la partida es peor que lo estimado en fitness (el error con signo es siempre ≤ 0), por lo que dos permutaciones a menos de 0,0223 de fitness no se distinguen con honestidad: el error de estimación puede invertir su orden. Para el congelado, 0,0223 es unas cinco veces su p90 (0,0043): el umbral único es conservador ahí.

**Datos de origen:** `docs/planes/mediciones/medicion_error_estimacion_92a.json` (filas por semilla y resumen) y `.log`. Script en la carpeta temporal de la sesión (fuera del repositorio). Se midió sobre el worktree `feat/arx-92a` con el código de 92a sin confirmar (`evaluar_ruta`); "pasos real" cuenta las llamadas de `avanzar_ia` hasta estado terminal (incluye esperas y recargas); el JSON trae también los movimientos efectivos (`pasos_mov_real`). Duración: 224,6 s de CPU en un solo proceso.

**El umbral se fijó antes de aplicarlo.** Quedó escrito y con su cálculo antes de tocar el código del desempate; no se ha aplicado. Aplicarlo (con su prueba y el control del congelado contra `d67f96d`) es el paso siguiente y requiere el visto bueno del líder.
