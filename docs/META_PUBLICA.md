# Meta pública de ARES-X

Resumen de los criterios de «hecho» del rover. Las frases son propias: no reproducen el texto de la rúbrica. Cada criterio tiene un identificador M1 a M20. Los números entre paréntesis son la numeración de la rúbrica original.

Las dimensiones M8 a M11 corresponden al algoritmo genético. La dimensión del sistema difuso sigue pendiente de confirmar por el autor del proyecto.

| ID | Dimensión | Resumen del criterio |
|---|---|---|
| M1 | Integración (1) | El flujo completo va de mundo a sensores, RNA, difuso o AG, supervisor, acción y bitácora, con entradas y salidas reales. |
| M2 | Integración (2) | Hay pruebas controladas en las que cambiar RNA, difuso o AG modifica una decisión, una velocidad o una ruta, sin política oculta. |
| M3 | Integración (3) | El supervisor veta acciones peligrosas con código de motivo, y la bitácora guarda por paso la predicción, las reglas, el fitness, la acción y el estado. |
| M4 | RNA (4) | Las etiquetas están justificadas, el ruido y el preprocesamiento se documentan, y la partición por mapas o escenarios evita la fuga de datos. |
| M5 | RNA (5) | Se demuestra una red neuronal con dos capas ocultas (o una arquitectura equivalente acordada), entrenable en CPU; la validación y la línea base se repiten con la misma semilla. |
| M6 | RNA (6) | Se muestran métricas de clasificación completas (matriz de confusión, F1 macro, sensibilidad a barrancos, confianza por predicción) y un análisis de errores sobre el conjunto de test. |
| M7 | RNA (7) | La entrada va normalizada y la salida son probabilidades con un vínculo observable hacia riesgo, ruta y seguridad. |
| M8 | AG (8) | Los cromosomas se decodifican en rutas, las rutas son contiguas y las soluciones inviables se reparan. |
| M9 | AG (9) | Población y generaciones son al menos 30, y torneo, cruce, mutación y elitismo se ejecutan de verdad. |
| M10 | AG (10) | Cada puntuación se descompone en sus componentes (ciencia, recorrido, batería, peligro, duración y castigos), con pesos documentados y editables. |
| M11 | AG (11) | Se comparan tres soluciones candidatas, cada operación genética se puede verificar, hay una gráfica de evolución del fitness y dos problemas clásicos resueltos (laberinto y viajante o mochila). |
| M12 | Simulación (12) | Terreno bidimensional con obstáculos, recursos y refugios; sensores con ruido, gasto de batería según el entorno y parámetros propios de cada planeta. |
| M13 | Simulación (13) | La máquina de estados, los límites térmicos, las colisiones, la batería y el veto físico funcionan, y la ruta se replanifica ante eventos. |
| M14 | Simulación (14) | Pruebas de situaciones límite: valores no numéricos, fallos de sensor, batería agotada, ausencia de ruta, borde de barranco, eventos a la vez y modo sonda. |
| M15 | Interactividad (15) | Se ven la ruta planeada y la real, los peligros, los objetivos, el rover, los eventos, las unidades y el estado de los sensores. |
| M16 | Interactividad (16) | Controles para arrancar, detener, dar un paso, volver al inicio, cambiar parámetros y disparar eventos, con efecto visible en el motor. |
| M17 | Interactividad (17) | Hay vistas de RNA, difuso, AG y comparación, un historial filtrable y una explicación concreta de cada decisión. |
| M18 | Experimentación (15) | Al menos 20 semillas por escenario, con media, mediana y dispersión; repetir la misma semilla da el mismo resultado. |
| M19 | Experimentación (16) | Se comparan con una referencia de ruta corta, el AG solo, el sistema híbrido y dos o más versiones sin una técnica, en el mismo escenario. |
| M20 | Experimentación (17) | Se exportan una traza en CSV y los resultados y configuración en JSON, con semillas, versiones y métricas completas. |
