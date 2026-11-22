# ARX-100 · Figuras 2D del informe (matriz de confusión y ablación)

**Estado:** implementado en la rama `feat/viz-figuras`; pendiente de integrar.

**Qué hace.** `viz.py` tiene dos funciones puras (`plot_matriz_confusion`, `plot_ablacion`) que reciben datos y devuelven
la figura. `scripts/generar_figuras.py` lee `docs/COMPARACION_POLITICAS_exigente.json`, calcula la evaluación de la RNA
(60 mapas, 400 muestras por mapa, semilla 42, un mapa a la vez y a un hilo) y escribe `docs/figuras/matriz_confusion.png`
y `docs/figuras/ablacion.png`. El notebook las muestra con una celda que solo actúa si los archivos existen.

**Cómo regenerar** (desde `ares_x/`):
`OMP_NUM_THREADS=1 python scripts/generar_figuras.py [escenario] [--version HASH]`.
Sin `--version`, el pie toma `git rev-parse --short main`; sin git, escribe «versión desconocida».

**Regenerar tras 94f.** Las cifras publicadas cambian con el rediseño de sensores (ARX-94f): hay que volver a ejecutar el
script y reemplazar los PNG. Texto alternativo en `docs/figuras/LEYENDA.md`.

**Pruebas:** `python -m pytest tests/test_viz.py`.
