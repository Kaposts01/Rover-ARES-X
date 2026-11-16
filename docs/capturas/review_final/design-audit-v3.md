# Design review · vuelta 13 (columna única)

Cambios desde la vuelta 12: HUD y decisión son ahora una sola columna izquierda con filetes entre bloques (sin tarjetas separadas).

Puntuación (A–F):
- Jerarquía visual: B (la columna se lee como un bloque; la escena domina)
- Tipografía: B (una familia; nada bajo 12 px)
- Espaciado y layout: B
- Color y contraste: B
- Estados de interacción: B
- Responsive: B- (móvil apilado, sin solapes)
- Calidad de contenido: B
- Slop de IA: C+ (quedan cajas de controles y de bandas inferiores)
- Movimiento: B
- Rendimiento: C (sin medición con GPU real)

Media ponderada ≈ 2,95 / 4 → **B.** No alcanza B+ (≈3,3).

Para B+: (1) reducir a una caja la franja inferior (historial y gráficas como pestañas); (2) el panel de controles como sección plegable de la columna derecha, sin caja propia; (3) medir con GPU real (?fps=1).
