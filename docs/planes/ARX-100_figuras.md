# ARX-100 · Figuras 2D del informe (matriz de confusión y ablación)

**Estado:** implementado en la rama `feat/viz-figuras`; pendiente de integrar.

**Qué hace.** `viz.py` tiene dos funciones puras (`plot_matriz_confusion`, `plot_ablacion`) que reciben datos y devuelven
la figura. `scripts/generar_figuras.py` lee `docs/COMPARACION_POLITICAS_exigente.json`, calcula la evaluación de la RNA
(60 mapas, 400 muestras por mapa, semilla 42, un mapa a la vez y a un hilo) y escribe `docs/figuras/matriz_confusion.png`
y `docs/figuras/ablacion.png`. El notebook las muestra con una celda que solo actúa si los archivos existen.

**Pies de figura.** Matriz: «Calculado con el código de main <hash>», RNA v1, 60 mapas (semillas 0-59), prueba en 51-59, no es la evaluación v2 de ARX-94. Ablación: «Datos publicados de main <hash>», semillas 1-20 (ya vistas). La celda del notebook busca `docs/figuras` o `ares_x/docs/figuras` y avisa si no está.

**Cómo regenerar** (desde `ares_x/`):
`OMP_NUM_THREADS=1 python scripts/generar_figuras.py [escenario] [--version HASH]`.
Sin `--version`, el pie toma `git rev-parse --short main`; sin git, escribe «versión desconocida».

**Regenerar tras 94f.** Las cifras publicadas cambian con el rediseño de sensores (ARX-94f): hay que volver a ejecutar el
script y reemplazar los PNG. Texto alternativo en `docs/figuras/LEYENDA.md`.

**Pruebas:** `python -m pytest tests/test_viz.py`.
