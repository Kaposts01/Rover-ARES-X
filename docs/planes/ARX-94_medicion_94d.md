# ARX-94d · medición de la RNA v2 frente a los umbrales

Umbrales escritos antes de medir en `ARX-94_umbrales.md` (ev3-d83 A); no se ajustó nada después. Una sola corrida con `scripts/medicion_94d.py` (un hilo, 2,7 s): entrena v2 con la partición de 60 mapas (400 muestras por mapa) y evalúa en 20 mapas no vistos (100 a 119), 7440 muestras, 70 de barranco. Falsos positivos = celdas libres predichas como barranco sobre celdas libres.

| Métrica | Umbral | Medido | Resultado |
|---|---|---|---|
| Recall de barrancos | ≥ 0,6 | 0,643 (45 de 70) | cumple |
| Falsos positivos | ≤ 0,2 % | 0,058 % (4 de 6915) | cumple |
| ECE | ≤ 0,03 | 0,008 | cumple |
| Macro-F1 v2 | sin umbral | 0,913 (línea base 0,929) | informativo |

Matriz de confusión (filas = real, columnas = predicho; libre, obstáculo, barranco): [[6902, 9, 4], [3, 452, 0], [25, 0, 45]).

Nota: el plan citaba 0,685 y 0,08 % de una medición previa con otra configuración; esta es la oficial. La macro-F1 de v1 (0,928, notebook de 60 mapas) se publica sin cambios y se verifica en 94f. Pendiente de 94e: la medición M2 (divergencias por RNA-RIESGO o V-RNA-* en 20 semillas, congelado y exigente).
