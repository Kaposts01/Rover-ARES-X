# Design review · vuelta 14 (franja con pestañas y controles plegables)

Cambios desde la vuelta 13: la franja inferior (historial y gráficas) es ahora una barra con dos pestañas; solo se ve un panel a la vez, debajo de la barra. La sección de controles de la columna derecha tiene cabecera plegable («Partida y simulación»).

Puntuación (A–F):
- Jerarquía visual: B+ (una pestaña abierta cada vez; la escena domina)
- Tipografía: B
- Espaciado y layout: B
- Color y contraste: B
- Estados de interacción: B
- Responsive: B- (móvil con franja a lo ancho; sin medir en esta vuelta)
- Calidad de contenido: B
- Slop de IA: C+ (aún hay cajas con borde: columna, controles, manual, franja)
- Movimiento: B
- Rendimiento: C (sin medición con GPU real)

Media ponderada ≈ 2,97 / 4 → **B.** No alcanza B+ (≈3,3).

Falta para B+: (1) fundir la caja de controles manuales en la franja inferior (una sola barra de controles); (2) medir con GPU real (?fps=1) para cerrar el apartado de rendimiento; (3) revisar el móvil con la franja nueva.
