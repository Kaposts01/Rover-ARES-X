# Matriz de requisitos del PDF de caso de uso (ARX-22, paso 1)

Fuente: `Caso_Uso_Rover_IA_Hibrida_Evaluacion.pdf` (8 páginas, versión 1.0). Su texto coincide con la pauta
`Evaluacion_CasoUsoRoverIAHibrida.pdf` leída antes. RF-16 (Colab) queda excluido por decisión del usuario.

Estados: **Cumple** · **Parcial** · **Falta**. Las rutas son relativas a `ares_x/`. Los esfuerzos son estimaciones en horas.
Las celdas marcadas *(UI)* dependen de la interfaz de Diseño (`api/static/**`) y solo tienen el dato en la API.

## 1. Integración por paso (§2, §4)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Flujo mundo → sensores con ruido → RNA → difuso + AG → supervisor → acción → bitácora | Cumple | `integracion.py:148` (`paso_mision`); `juego/partida.py` (`avanzar_ia`); `simulador.py:127-170` (sensores con ruido) | — |
| Auditoría causal: alterar una salida cambia la decisión | Cumple | `integracion.py:183-185` (gancho), `intervencion.py:48-65`, INFORME §4.1 | — |
| El AG se recalcula al llegar a un objetivo, bloqueo o evento grave | Parcial | Replanteo con AG en modo `ag` (`juego/conduccion.py`, `_replanear_ag`, ARX-18.4). En el automático solo BFS tras la planificación inicial (`integracion.py:99-112`). Evento grave: no dispara replanteo del AG | 3 h |

## 2. RNA (§4, §10.1, RF-04, CA-06)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| MLP 2 capas ocultas (32, 16), ReLU, softmax 3 clases | Cumple | `rna.py:83` (`hidden_layer_sizes=(32,16)`, `activation="relu"`); salida softmax implícita en `MLPClassifier` multiclase | — |
| Partición train/valid/test por mapas | Cumple | `rna.py:63` (`particion_por_mapas`) | — |
| Baseline, matriz de confusión, macro-F1, recall de barrancos | Cumple | `rna.py:116-121`; INFORME §5 (macro-F1 0,928; línea base 0,927; recall 0,943) | — |
| Error de calibración (ECE) | Cumple | `rna.py:105-121` | — |
| Evidencia visible: entrada → normalización → activaciones → probabilidades → acción | Parcial | Probabilidades por paso en `/paneles` (`api/servidor.py`); no hay activaciones de capas ni normalización expuestas | 3 h + *(UI)* |
| Veto con el sensor de borde | Cumple | `juego/conduccion.py` (`_motivo_veto`, LIDAR por celda); `integracion.py:47` (supervisor) | — |
| Laboratorio RNA (§8) y CA-06 (cambiar rasgos → cambian probabilidades) | Parcial | Datos en API; falta endpoint de entrada → probabilidades y la vista | 4 h + *(UI)* |

## 3. Lógica difusa (§4, §10.2, RF-05, RF-06, CA-05)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Entradas distancia, batería, inclinación | Cumple | `difuso.py:95-103` (`fusificar`, `inferir`); rangos en `difuso.py:135` (`_rango`) | — |
| Temperatura como entrada (§2, §4, §10.2 «temperatura °C») | Falta | No aparece en `difuso.py`. Sí aparece como texto de planeta en `simulador.py:36` (Venus). **Decisión de alcance → ficha** | 4 h si se implementa |
| ≥ 3 conjuntos por variable | Cumple | `difuso.py:31-41` (cerca/media/lejos, crítica/baja/alta, plana/media/fuerte con formas triangulares y trapezoidales) | — |
| ≥ 8 reglas documentadas | Cumple | 9 reglas `R1`-`R9` en `difuso.py:55-72` | — |
| Mamdani min–max con centroide | Cumple | `difuso.py:103-131` (`inferir`); centroide en la desfusificación | — |
| Fallback si ninguna regla se activa | Cumple | `difuso.py:107` (`SALIDA_FALLBACK`) | — |
| Mostrar universo de discurso, curvas y punto de entrada (§10.2) | Falta | Las membresías se calculan (`difuso.py:95`), pero no se exponen en la API | 3 h + *(UI)* |
| Laboratorio difuso (§8) y CA-05 (10 m → 1 m: curvas, reglas, velocidad) | Parcial | `/paneles` expone velocidad y reglas activadas; faltan membresías y el barrido de distancia | 3 h + *(UI)* |
| RF-06: desfusificación numérica y reglas activadas | Cumple | `difuso.py:103-131`; `/paneles` (`difuso.reglas`) | — |

## 4. Algoritmo genético (§4, §10.3, RF-07, CA-04)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Población ≥ 30, generaciones ≥ 30 | Cumple | `genetico.py:99-100` (la clase rechaza valores menores) | — |
| Torneo, cruce, mutación, elitismo | Cumple | `genetico.py:172-175` (torneo), `177-183` (cruce), `184-192` (mutación), `209-210` (elitismo) | — |
| Semilla controlada | Cumple | `genetico.py:98` (`semilla`) | — |
| Fitness con desglose y pesos configurables | Cumple | `genetico.py:18` (`PESOS_POR_DEFECTO`), `111` (`pesos`), `144-162` (`evaluar`, desglose) | — |
| Restricciones duras (precipicio, batería, límites) | Parcial | Penalizaciones en `genetico.py:144-162`; no todas las restricciones del §10.3 están como restricción dura explícita | 2 h |
| Reparación de rutas inviables | Cumple | `genetico.py:120-143` (`decodificar`, descarte de puntos inalcanzables, ev3-d01) | — |
| ≥ 3 rutas candidatas inspeccionables | Cumple (API) | `genetico.py` (`candidatos`, top 3); `GET /ag` devuelve `candidatos` con cromosoma, fitness y desglose (`api/servidor.py`, `diagnostico_ag`). Vista *(UI)* | — |
| Historial por generación (mejor y media) | Cumple (API) | `genetico.py` (`optimizar`): mejor, media, top 3 y población con operación por generación; `GET /ag` → `generaciones` (`test_ag_expone_generaciones_candidatos_y_operaciones`) | — |
| ≥ 2 familias de subproblemas (laberinto, viajero, mochila) | Cumple | `genetico.py:7` (laberinto por BFS, `40`; viajero por orden de visitas). Mochila no está; con dos basta | — |
| Laboratorio genético (§8) y CA-04 (generación 5: ≥ 3 cromosomas, fitness, cruce o mutación) | Parcial | Datos por generación en `GET /ag` (cromosomas, fitness, operación `elite`/`cruce`/`copia`/`+mutacion`, cruces y mutaciones por generación). Falta la vista de selección de generación *(UI)* | 2 h + *(UI)* |

## 5. Supervisor y máquina de estados (§4, §10.4, §11)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Código de motivo reproducible por decisión | Cumple | 12 códigos `V-…`/`D-…` en `integracion.py` (p. ej. `V-SENSOR-NAN`, `V-BATERIA-0`) | — |
| Estados del §11: CONFIGURACIÓN, EXPLORACIÓN, ALERTA, REPLANIFICACIÓN, REFUGIO, MODO SEGURO, ÉXITO, FRACASO | Parcial | `integracion.py:21,86,203,209,213,226`: existen EXPLORACION, ALERTA, MODO_SEGURO, EXITO, FRACASO, SIN_RUTA. Faltan CONFIGURACION, REPLANIFICACION y REFUGIO como estados | 2 h |
| Pseudociclo del §11 | Parcial | El ciclo está en `integracion.py:148`; no hay pasos `validar_sensores()` ni `actualizar_dashboard()` como funciones | 1 h |
| Prioridad de seguridad determinista (meteorito + batería baja, §12) | Parcial | `integracion.py:42-51` (orden de vetos) | 1 h |

## 6. Requisitos funcionales (§7)

| ID | Requisito | Estado | Evidencia / brecha | Esfuerzo |
|---|---|---|---|---|
| RF-01 | Planeta, modo, mapa, dificultad, semilla; validar rover/sonda | Parcial | `simulador.py:34-41` (perfiles de los 8 planetas), `simulador.py:45` (`validar_compatibilidad`). La partida solo arranca en Marte. **Decisión de alcance → ficha** | 4 h + *(UI)* |
| RF-02 | Mapas con elevación, obstáculos, recursos, refugios, sitios; crear obstáculos a mano | Parcial | Elevación `simulador.py:112`; sitios y refugio sí. Colocar obstáculos a mano: no existe | 2 h + *(UI)* |
| RF-03 | Ciclos observación/decisión/acción con duración configurable y sensores ruidosos | Parcial | Ruido `simulador.py:134`; la duración de paso configurable no existe (el paso es discreto) | 1 h |
| RF-04 | RNA real con partición sin fuga | Cumple | `rna.py:63` | — |
| RF-05 | ≥ 3 conjuntos por variable y ≥ 8 reglas | Cumple | `difuso.py:31-72` | — |
| RF-06 | Desfusificación y activación de reglas | Cumple | `difuso.py:103-131` | — |
| RF-07 | AG con selección, cruce, mutación, elitismo, restricciones; ≥ 3 rutas inspeccionables | Cumple (API) | Operadores y 3 candidatos en `GET /ag`; restricciones blandas por penalización (ver §4) | — |
| RF-08 | Registro por paso: señales, probabilidades, grados difusos, crisp, fitness, ruta, acción, explicación | Parcial | Bitácora `juego/partida.py` (`bitacora`), `/historial` (ARX-15). Faltan grados de membresía y fitness por paso en la bitácora | 2 h |
| RF-09 | Iniciar, pausar, paso a paso, reiniciar, velocidad, inyectar eventos | Cumple | `api/servidor.py` (`/paso`, `/partida`, `/evento`); controles en `api/static` | — |
| RF-10 | Trazado de ruta ejecutada vs planificada, estado del rover y eventos sobre el mapa | Parcial | `/estado` (`ruta`) y `/paneles` (`ag.ruta_planeada`) existen; el trazado comparado lo dibuja la interfaz *(UI)* | 1 h + *(UI)* |
| RF-11 | Evolución del fitness y precisión de la RNA con controles por iteración | Parcial | Fitness por generación en `GET /ag` (Cumple en API). Falta la precisión de la RNA por iteración y la vista *(UI)* | 2 h + *(UI)* |
| RF-12 | Exportar trazas a CSV y configuración/resultados a JSON; guardar semillas y versiones | Parcial | `juego/exportar.py:55-91` (CSV bitácora + JSON configuración). Versión del software no se registra | 1 h |
| RF-13 | Fallos de sensor, pérdida de enlace y modo seguro sin excepción no controlada | Parcial | Falla de sensor `juego/partida.py` (`_evento_falla_sensor`, 3 pasos); modo seguro `integracion.py:209`; pérdida de enlace no existe | 3 h |
| RF-14 | Comparar híbrido con ≥ 2 ablaciones (sin RNA, sin difuso o sin AG) | Parcial | `intervencion.py:22` (`opciones_variantes`: rna, difuso); `tests`/`tabla_modos` comparan modos sueltos. Falta «sin AG» como variante del híbrido | 2 h |
| RF-15 | ≥ 20 semillas con métricas y dispersión | Parcial | `docs/TABLA_MODOS.md` (20 semillas, medias y medianas). Falta dispersión (desviación o rango intercuartil) | 1 h |

## 7. Eventos (§6)

| Evento | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Barranco | Cumple | `juego/partida.py:375` (`_evento_barranco`) | — |
| Batería baja | Cumple | `juego/partida.py:399` (`_evento_bateria_baja`) | — |
| Día/noche (tormenta, noche) | Cumple | `juego/partida.py:25` (`EVENTOS_SOPORTADOS`: tormenta, noche) | — |
| Falla de sensor | Cumple | `juego/partida.py:387` (`_evento_falla_sensor`) | — |
| Sismo | Cumple | `juego/partida.py:1117` (`_evento_sismo`, ARX-30a): grietas BARRANCO con replanteo del AG y veto del supervisor; control en la interfaz (ARX-30e) | — |
| Meteorito o impacto próximo | Cumple | `juego/partida.py:1088` (`_evento_meteorito`, ARX-30): zona de riesgo 3×3, cuesta batería | — |
| Señal biológica anómala / objeto alienígena | Falta (opcional narrativo) | No existe en esta rama (ARX-30c, bloqueada por ev3-d49). El PDF lo marca como opcional | 2 h |
| Baja conectividad | Falta | No existe en esta rama (ARX-30b, bloqueada por ev3-d48) | 2 h |
| Ráfaga / viento en modo sonda | Falta | No hay modo sonda | depende de RF-01 |

## 8. Pantalla y laboratorios (§8, §9)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Panel A: mapa con ruta planeada/ejecutada, celdas peligrosas, destino | Parcial | Mapa y ruta en la interfaz; celdas peligrosas como riesgo no se dibujan *(UI)* | 1 h + *(UI)* |
| Panel B: telemetría con unidades y estado de sensor | Parcial | `/estado` (batería, posición, rumbo); sin estado de sensor ni unidades completas *(UI)* | 1 h + *(UI)* |
| Panel C: explicación por algoritmo con valores concretos | Parcial | `/paneles` con valores por técnica; la explicación en lenguaje natural se quita (ARX-19) *(UI)* | — |
| Panel D: historia filtrable y exportable | Cumple | `/historial` y `/historial.csv` (ARX-15, `api/servidor.py`); la vista *(UI)* | — |
| Panel E: controles de simulación y eventos | Cumple | `/paso`, `/evento`, `/partida` | — |
| Laboratorio RNA, Laboratorio Difuso, Laboratorio Genético, Comparación de políticas | Falta | Datos parciales en API (§2, §3, §4); las vistas son *(UI)* | ver §2-§4 |
| Interacciones mínimas §9: elegir planeta; sonda para gigantes; batería inicial; agregar barranco; sismo; forzar noche; prioridades; un paso; seleccionar iteración del AG; inspeccionar regla; reejecutar con semilla | Parcial | Cumplen: un paso, noche, reejecutar con semilla, sismo (control «5 · Eventos» con `POST /evento`, ARX-30e). Parcial: batería inicial (`juego/partida.py` la acepta, la API no), barranco (evento sin colocación manual), regla (solo lectura). Faltan: planeta, sonda, prioridades científicas, iteración del AG | 6 h |

## 9. Condiciones de borde (§12)

| Condición | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Batería = 0 % no mueve y termina | Cumple | `api/servidor.py` (`_turno`, FRACASO al batería ≤ 0); `juego/partida.py` (`mover_jugador`: «sin batería») | — |
| Batería 1 % con refugio lejano: declarar inalcanzable | Falta | No hay comprobación de alcanzabilidad con batería baja | 2 h |
| Sensor 0 / NaN / infinito: validación | Cumple | `integracion.py:42` (`V-SENSOR-NAN`); entradas inválidas → 400 (`api/servidor.py`, `validar_partida`) | — |
| Todos los sensores de navegación fallan: no seguir a ciegas | Parcial | Falla de sensor detiene 3 pasos (`juego/partida.py`); no hay estado de degradación persistente | 1 h |
| Barranco bajo la siguiente casilla: detener y replantear | Cumple | Veto LIDAR por celda (`juego/conduccion.py`, `_motivo_veto`); `integracion.py` (`borde_barranco`) | — |
| No existe ruta: reportar sin solución | Cumple | `SIN_RUTA` (`integracion.py:161,213`) | — |
| Mutación con coordenada inválida: reparar sin detener | Parcial | `genetico.py:120-143` repara al decodificar; no hay prueba que lo cubra por nombre | 1 h |
| AG sin mejora en 10 generaciones: parada temprana | Cumple (API) | `genetico.py` (`optimizar(parada_sin_mejora=n)`, por defecto apagado); `GET /ag?parada_sin_mejora=n` (`test_ag_parada_temprana_corta_las_generaciones`) | — |
| RNA con baja confianza: fusión con sensor determinista | Falta | La confianza no altera la decisión | 2 h |
| Reglas difusas sin activación: salida fallback | Cumple | `difuso.py:107` | — |
| Temperatura excede tolerancia: abortar | Falta | Depende de la temperatura del difuso (ver §3) | 2 h |
| Modo rover en Júpiter: bloquear rodaje | Falta | Depende de RF-01 (planetas y sonda) | 3 h |
| Eventos simultáneos: prioridad determinista | Parcial | Orden de vetos en `integracion.py:42-51` | 1 h |
| Misma semilla y configuración: traza equivalente | Cumple | `tests/test_integracion.py`, `docs/TABLA_MODOS.md` (resultados reproducibles) | — |
| Configuración imposible o NaN: rechazar con mensaje | Cumple | `api/servidor.py` (`validar_partida`, `validar_rumbo`, 400 con motivo) | — |
| Mapa sin sitios científicos: sin dividir por cero | Parcial | `juego/partida.py` (`_quedan_sitios`) | 1 h |

## 10. Casos de aceptación (§13)

| CA | Estado | Evidencia / brecha |
|---|---|---|
| CA-01 Navegación normal (≥ 10 pasos con telemetría e historial) | Cumple | Partidas de 46 a 56 pasos en semilla 11 (`juego/tests/test_conduccion.py`); historial en `/historial` |
| CA-02 Obstáculo imprevisto (se detiene, confianza, reglas, decisión, replanteo) | Parcial | Veto y replanteo existen; confianza y reglas visibles en `/paneles`; falta vista *(UI)* |
| CA-03 Energía crítica al 12 % | Parcial | `juego/partida.py` acepta `bateria=`; la API no la recibe. Falta la prueba |
| CA-04 Generación 5: ≥ 3 cromosomas, fitness, operación de cruce o mutación | Falta | Ver §4 (sin API ni vista) |
| CA-05 Difuso con distancia 10 m → 1 m | Parcial | Entradas y reglas existen; falta el barrido y la vista *(UI)* |
| CA-06 RNA: cambiar rasgos actualiza probabilidades; recall de barrancos | Parcial | Probabilidades en `/paneles`; recall en INFORME §5; falta el endpoint de entrada |
| CA-07 Júpiter + ruedas bloquea y propone sonda | Falta | Depende de RF-01 |
| CA-08 Experimento controlado con técnica desactivada | Cumple | `docs/TABLA_MODOS.md`; `intervencion.py` |

## 11. Evaluación experimental (§14)

| Requisito | Estado | Evidencia / brecha | Esfuerzo |
|---|---|---|---|
| Éxito, colisiones, barrancos, pasos por escenario y ≥ 20 semillas | Cumple | `docs/TABLA_MODOS.md` | — |
| Energía restante, distancia de ruta, ciencia, replanes, tiempo de cómputo | Falta | No están en la tabla | 3 h |
| Promedio, mediana y dispersión | Parcial | Falta la dispersión | 1 h |
| Baseline de menor distancia sin riesgos (control) | Falta | No existe como variante | 2 h |
| AG puro con riesgos fijos | Parcial | Modo `ag` con riesgo estimado, no fijo | 1 h |
| Híbrido completo y dos ablaciones | Cumple | `intervencion.py`, `docs/TABLA_MODOS.md` | — |
| Separar tiempo offline (entrenamiento RNA) y online (decisión) | Falta | No se mide | 1 h |

## 12. Entregables (§15) y rúbrica (§16)

| Entregable | Estado | Evidencia / brecha |
|---|---|---|
| Código modular: PlanetProfile, World, SensorSuite, NeuralPerception, FuzzyController, GeneticPlanner, SafetySupervisor, MissionLogger, Dashboard | Parcial | Cumplen con nombre o equivalente: `simulador.py:22` (PlanetProfile), `:60` (World), `:127` (SensorSuite), `rna.py` (NeuralPerception), `genetico.py:94` (GeneticPlanner), `simulador.py:186` (MissionLogger). Con otro nombre: FuzzyController (`difuso.py`), SafetySupervisor (`integracion.py`). Falta Dashboard como módulo *(UI)* |
| README con instalación, semilla de demostración, límites, supuestos | Cumple | `README.md` (instalación, semilla, límites). Registro de supuestos en `docs/SPEC_MVP_3D.md` |
| Dataset sintético generado por el propio proyecto | Cumple | `rna.py` (`generar_dataset`) |
| Exportación CSV/JSON de una misión | Cumple | `juego/exportar.py:55-91` |
| Informe técnico (decisiones, pruebas, ablaciones, limitaciones, aportes, declaración de IA) | Parcial | INFORME_TECNICO. Pendiente: aportes individuales (borrador §7) y declaración de IA (§8) para revisión del estudiante |
| Video de 6-8 min | Pendiente | Lo graba el estudiante con `juego/GUION_VIDEO.md` (ARX-13) |
| Rúbrica (§16): integración 25 %, RNA 15 %, difuso 15 %, AG 15 %, física 10 %, interactividad 10 %, experimentación 5 %, defensa 5 % | — | La integración y el AG son fuertes en el motor. La interactividad (10 %) depende de los laboratorios *(UI)* y de RF-11 |

## 13. Resumen de brechas por peso de rúbrica

- **Integración (25 %):** replanteo del AG en el automático ante evento grave (§1); estados que faltan (§5); «sin AG» como ablación (RF-14). Esfuerzo: ~8 h.
- **RNA (15 %):** evidencia de activaciones y entrada→probabilidades (§2); endpoint de laboratorio y CA-06. Esfuerzo: ~7 h.
- **Difuso (15 %):** temperatura (§3, decisión de alcance); membresías y curvas en la API. Esfuerzo: ~7 h (+4 h si entra la temperatura).
- **AG (15 %):** exponer candidatos, historial y cromosomas por generación (§4, RF-11, CA-04). Esfuerzo: ~8 h.
- **Física y seguridad (10 %):** eventos conectividad y señal biológica (§7; sismo y meteorito ya cumplen), batería 1 % (§9). Esfuerzo: ~10 h.
- **Interactividad (10 %):** laboratorios y dashboard (§8, *(UI)*), colocación manual de obstáculos (RF-02). Esfuerzo: ~12 h + *(UI)*.
- **Experimentación (5 %):** métricas de §14 y dispersión. Esfuerzo: ~8 h.

## 14. Decisiones que chocan con fichas aprobadas (no resueltas en silencio)

Estas tres piden ficha antes de implementar:

1. **Planetas y modo sonda (RF-01, §3, §9, CA-07, §12).** El PDF exige selección de planeta y sonda para gigantes. La decisión vigente es Marte como único escenario. Opciones: A) mantener Marte y declarar el resto fuera de alcance; B) implementar selección de planeta con modo sonda para gigantes; C) solo selección de planeta sin modo sonda.
2. **Temperatura como entrada del difuso (§2, §4, §10.2).** El PDF la pide; el difuso actual tiene tres entradas. Opciones: A) añadir temperatura como cuarta entrada con sus conjuntos y reglas; B) declararla fuera de alcance con justificación; C) usarla solo como condición de borde de aborto.
3. **Movimiento en 8 direcciones (ev3-d29).** No choca con el PDF: §10.3 permite «ruta contigua». Solo lo registro para que la matriz sea completa.

Además, una pregunta de alcance (no de conflicto): qué eventos extra implementar de §6 (sismo, meteorito, baja conectividad). Propuesta: sismo y meteorito en el juego; conectividad y alienígena como narrativos.
