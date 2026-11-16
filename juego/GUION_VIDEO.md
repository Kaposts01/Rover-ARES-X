# ARES-X · Guion del video de demostración (MVP 3D)

**Duración objetivo: 7:30** (rango pedido: 6:00 a 8:00). Versión sobre el MVP 3D en navegador (ev3-d34 A). Reemplaza la versión pygame.

## Antes de grabar

- Arrancar el servidor desde `ares_x/`: `python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765` y abrir `http://127.0.0.1:8765/` en una ventana de 1280x720.
- Semilla 11 (la misma del informe). Nivel 1.
- Tener abiertos `ARES_X_ejecutado.ipynb` y `docs/TABLA_MODOS.md` en otra ventana para las escenas 7 y 9.
- Ensayar una vez completa. Si sobra tiempo, alargar la escena 5 (modos sueltos).

## Guion por escenas

| Escena | Minuto | Qué se muestra en pantalla | Qué se dice (texto sugerido, primera persona) | Tema de la materia que cubre |
|---|---|---|---|---|
| 1. Apertura | 0:00 a 0:30 (0:30) | Escena 3D con el mapa de Marte, sin tocar nada. | "Hola, soy [tu nombre] y este es ARES-X, un rover autónomo que explora Marte. Combina una red neuronal, lógica difusa y un algoritmo genético, y un supervisor de seguridad decide qué se hace. Es una simulación ficticia con parámetros de referencia, no una misión real." | Problema: agente que percibe, decide y actúa; IA híbrida. |
| 2. Mapa y escenario | 0:30 a 1:00 (0:30) | Terreno, rocas, cráteres, barrancos (huecos oscuros), cristales, refugio y rover. Señalar inicio y refugio. | "El mapa sale de una semilla: obstáculos, cuatro barrancos y tres sitios científicos. El rover parte de abajo a la izquierda y debe llegar al refugio visitando los sitios. No ve el mapa completo: trabaja con lecturas de sensores que tienen ruido." | Modelado del entorno; mundo real frente a mapa estimado; reproducibilidad por semilla. |
| 3. Control manual | 1:00 a 1:35 (0:35) | Modo `manual`. Flechas o WASD mueven el rover; los diagonales con las teclas del teclado numérico o con el pad de 8 direcciones. Intentar entrar en un barranco: no se mueve y aparece el motivo. | "Yo conduzco. Si intento entrar en un obstáculo o en un barranco, el movimiento se bloquea. Es una regla física del simulador. Cada paso gasta batería." | Ciclo percepción-acción; reglas del entorno. |
| 4. Modo RNA | 1:35 a 2:10 (0:35) | Modo `rna`. Dar un paso con «Paso» y leer el panel de la RNA: probabilidades de libre, obstáculo y barranco; motivo `RNA-MAX-PLIBRE` en la barra inferior. Dejar el veto encendido. | "En este modo la red neuronal conduce sola. Es un MLP de 32 y 16 neuronas, con ReLU y softmax. Elige el vecino de mayor probabilidad de libre que acerca al objetivo. Con el veto encendido, el supervisor no deja avanzar hacia una celda que la RNA o el LIDAR marcan como peligrosa." | RNA (MLP 32-16, ReLU, softmax). Clasificación de peligros. |
| 5. Modos difuso y AG | 2:10 a 3:00 (0:50) | Modo `difuso`: panel con velocidad y reglas activadas; cuando la velocidad es baja aparece `D-VELOCIDAD-BAJA`. Luego modo `ag`: ruta planeada en amarillo y el rover la sigue; si la ruta se bloquea, replantea. | "El difuso convierte la distancia al riesgo, la batería y la inclinación en una velocidad entre 0 y 1, con reglas y centroide. Si la velocidad es baja, el rover espera o rodea. El algoritmo genético planea la ruta con puntos de paso; este modo la sigue y solo la replanea cuando queda bloqueada." | Lógica difusa (conjuntos, Mamdani min-max, centroide). Algoritmos genéticos (cromosoma de puntos de paso, fitness). |
| 6. Automático con supervisor | 3:00 a 3:40 (0:40) | Modo `automatico`, varios pasos con «Reproducir». Motivos `V-…` y `D-…` en el panel de decisiones (plegable). | "En automático las tres técnicas trabajan juntas. El supervisor revisa primero las prohibiciones físicas y después combina las propuestas. Cada decisión deja un código de motivo, que puedo abrir en el panel." | Supervisor de seguridad; códigos de motivo; máquina de estados (EXPLORACION, ALERTA, EXITO, FRACASO, SIN_RUTA, MODO_SEGURO). |
| 7. Veto apagado: cómo falla cada técnica | 3:40 a 4:20 (0:40) | Desactivar el veto con la casilla. Repetir el modo `rna` o `ag` y mostrar un bloqueo con colisión. Abrir `docs/TABLA_MODOS.md` en la otra ventana. | "Ahora apago el veto para ver cómo falla cada técnica sola. Sin veto, el rover intenta la celda y la física la bloquea: cuenta como colisión y la celda pasa a riesgo. En la tabla de 20 semillas, con el veto encendido no hay colisiones; con el veto apagado sí aparecen." | Experimento controlado con ablación; evidencia de cada técnica. |
| 8. Intervención en vivo | 4:20 a 5:00 (0:40) | Panel de intervención: técnica `rna` y valor `barranco`, «Aplicar». Aparece el aviso de prueba causal. Un paso: cambia la decisión. «Apagar» restablece. | "Esta es la prueba causal: fuerzo la salida de la RNA a barranco. La decisión cambia en el paso siguiente, y con el aviso visible sé que la decisión es la de la intervención y no la de la red." | Prueba de intervención; auditoría de causalidad (condición de la pauta). |
| 9. Eventos y combate | 5:00 a 5:40 (0:40) | Dos drones patrullan. Cuando se acercan, el anillo cambia de color y el rover dispara con Espacio (munición 10, cooldown de 2 turnos, alcance 5). Mostrar el impacto en el registro de eventos. | "Los drones patrullan y, si se acercan, pasan a alerta y después a persecución. A una celda atacan la batería. Disparo con Espacio en la dirección del rover; cada disparo gasta munición y tiene cooldown. El supervisor de combate decide en automático; los modos sueltos solo sufren el daño de batería." | Simulación con agentes reactivos (máquina de estados de drones). |
| 10. Experimento y límites | 6:20 a 7:10 (0:50) | Tabla de `INFORME_TECNICO.md` §4 y §5 (cifras del notebook); luego limitaciones en pantalla. | "Con 20 semillas, el híbrido llega al refugio en las 20 sin colisiones. Forzar la RNA a barranco cambia la decisión en 20 de 20; forzar el difuso a cero, también. Quiero ser honesto con lo que no funciona: un falso positivo del sensor puede dejar el rover en SIN_RUTA aunque exista camino; los modos sueltos no reaccionan a los drones; y Qwen puede equivocarse. Todos los parámetros son supuestos de simulación." | Limitaciones; métricas (macro-F1 0,928 frente a línea base 0,927; recall de barrancos 0,943). |
| 11. Cierre | 7:10 a 7:30 (0:20) | Escena 3D. | "En resumen: tres técnicas de IA conectadas por un supervisor de seguridad, probadas con un experimento y con sus límites. Gracias." | Conclusión: integración de RNA, lógica difusa, AG y supervisor. |

## Cifras verificadas (para el coordinador)

Cada cifra del guion debe coincidir con el notebook o con `docs/TABLA_MODOS.md`. Fuentes:

- **Experimento del notebook (20 semillas, `Mision` directa):** híbrido con éxito 100 %, colisiones 0, sitios 1,7 en las tres variantes, mediana de pasos 39,5, batería media 61,1 %. Fuente: celda del experimento de `ARES_X_ejecutado.ipynb`.
- **Tabla de modos (ARX-11, 20 semillas, capa `Partida`):** automático 19/20; RNA con veto 20/20 y 0 colisiones; RNA sin veto 20/20 y 0,10 colisiones; difuso con veto 20/20 y 0 colisiones; difuso sin veto 20/20, 0,40 colisiones y 0,15 intentos a barranco; AG con veto 20/20 y 0 colisiones; AG sin veto 20/20, 0,55 colisiones y 0,15 intentos a barranco. Fuente: `docs/TABLA_MODOS.md`.
- **Discrepancia a decir en el video si se muestra la tabla:** el automático falla en la semilla 15 (`SIN_RUTA`, con los tres sitios visitados) en la capa `Partida`, mientras que el experimento del notebook da 100 % para el híbrido. Son arneses distintos (`Partida` frente a `Mision`). El video debe citar la tabla de cada arnés por separado y no mezclarlas.
- **Prueba causal (notebook y `INFORME_TECNICO.md` §4.1):** RNA a barranco cambia la decisión en 20 de 20 y el éxito cae a 0 %; RNA a libre no cambia nada; difuso a 0 cambia en 20 de 20 con éxito 0 %; difuso a 1 cambia en 20 de 20 con éxito 100 %.
- **RNA en prueba:** macro-F1 0,928; línea base 0,927; recall de barrancos 0,943 (33 de 35); ECE 0,011.

## Lista de comprobación de funciones del juego (MVP 3D)

Marcar cada punto antes de grabar.

- [ ] La página carga sin errores en la consola y la escena 3D se ve.
- [ ] Flechas y WASD mueven el rover; el pad de 8 direcciones también.
- [ ] Un intento de entrar en barranco o en obstáculo muestra el motivo en el aviso.
- [ ] Cada modo (`manual`, `rna`, `difuso`, `ag`, `automatico`) se puede elegir y el HUD lo muestra.
- [ ] La casilla «Veto de seguridad» cambia el estado (`veto` en `GET /estado`).
- [ ] «Paso» y «Reproducir» funcionan; «Reproducir» se detiene al llegar a un estado final.
- [ ] El panel de decisiones se pliega y despliega con su botón.
- [ ] La intervención con «Aplicar» muestra el aviso; «Apagar» lo quita.
- [ ] Espacio dispara; el cooldown y la munición se actualizan en el HUD.
- [ ] La captura `docs/capturas/modo_rna_veto_on.png` coincide con lo que se muestra al grabar.

## Cambios respecto de la versión pygame

- Se eliminan las teclas de pygame (TAB para la sugerencia, C para la comparación, B/F/E/R/X y ESC).
- La comparación de 20 semillas sale del notebook y de `docs/TABLA_MODOS.md`, no de una tecla.
- Se añaden los modos sueltos, el veto, la intervención en vivo y el combate con drones.
