# Meta pública de ARES-X

Resumen de los criterios de «hecho» del rover. Las frases son propias: no reproducen el texto de la rúbrica. Cada criterio tiene un identificador M1 a M20. Los números entre paréntesis son la numeración de la rúbrica original.

Las dimensiones M8 a M11 corresponden al algoritmo genético. La dimensión del sistema difuso sigue pendiente de confirmar por el autor del proyecto.

| ID | Dimensión | Resumen del criterio |
|---|---|---|
| M1 | Integración (1) | El flujo completo va de mundo a sensores, RNA, difuso o AG, supervisor, acción y bitácora, con entradas y salidas reales. |
| M2 | Integración (2) | Hay pruebas controladas en las que cambiar RNA, difuso o AG modifica una decisión, una velocidad o una ruta, sin política oculta. |
| M3 | Integración (3) | El supervisor veta acciones peligrosas con código de motivo, y la bitácora guarda por paso la predicción, las reglas, el fitness, la acción y el estado. |
| M4 | RNA (4) | Las etiquetas están justificadas, el ruido y el preprocesamiento se documentan, y la partición por mapas o escenarios evita la fuga de datos. |
| M5 | RNA (5) | El modelo es un MLP de dos capas ocultas o su equivalente exigido, con entrenamiento en CPU, validación y línea base reproducibles. |
| M6 | RNA (6) | Hay matriz de confusión, macro-F1, recall de barrancos, confianza y errores, con resultados de test. |
| M7 | RNA (7) | La entrada va normalizada y la salida son probabilidades con un vínculo observable hacia riesgo, ruta y seguridad. |
| M8 | AG (8) | Los cromosomas se decodifican en rutas, las rutas son contiguas y las soluciones inviables se reparan. |
| M9 | AG (9) | Población y generaciones son al menos 30, y torneo, cruce, mutación y elitismo se ejecutan de verdad. |
| M10 | AG (10) | La función de aptitud desglosa ciencia, distancia, energía, riesgo, tiempo y penalizaciones, con pesos justificados y ajustables. |
| M11 | AG (11) | Hay tres candidatos con operaciones verificables, curva de aptitud, selección de generación y dos subproblemas de laberinto, viajante o mochila. |
| M12 | Simulación (12) | El mapa 2D tiene obstáculos, recursos y refugios, sensores ruidosos, consumo energético y perfiles planetarios correctos. |
| M13 | Simulación (13) | La máquina de estados, los límites térmicos, las colisiones, la batería y el veto físico funcionan, y la ruta se replanifica ante eventos. |
| M14 | Simulación (14) | Los casos límite están cubiertos: NaN, sensores caídos, batería en cero, ruta inexistente, precipicio, eventos simultáneos y modo sonda. |
| M15 | Interactividad (15) | Se ven la ruta planeada y la real, los peligros, los objetivos, el rover, los eventos, las unidades y el estado de los sensores. |
| M16 | Interactividad (16) | Se puede iniciar, pausar, avanzar un paso, reiniciar, ajustar parámetros e inyectar eventos con efecto real. |
| M17 | Interactividad (17) | Hay vistas de RNA, difuso, AG y comparación, un historial filtrable y una explicación concreta de cada decisión. |
| M18 | Experimentación (15) | Se corren al menos 20 semillas por escenario, con promedio, mediana, dispersión y repetición determinista. |
| M19 | Experimentación (16) | Hay una línea base de ruta corta, AG puro, híbrido y al menos dos ablaciones comparables en el mismo escenario. |
| M20 | Experimentación (17) | Se exportan una traza en CSV y los resultados y configuración en JSON, con semillas, versiones y métricas completas. |
