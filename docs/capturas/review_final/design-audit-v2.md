# Design review · vuelta 12 (medición tras el pulido)

Medido en navegador (gstack $B), 1366×768, partida iniciada:
- Familias tipográficas en la página: 2 (sans del sistema y la del navegador para controles, ya heredada).
- Textos por debajo de 12 px: 0.
- Botones por debajo de 34 px: 0.
- FPS con render por software: ~11–12 (no es GPU real).

| Categoría | Peso | Antes | Ahora | Nota |
|---|---|---|---|---|
| Jerarquía visual | 15 % | B | B | Cuatro cajas aún con peso similar |
| Tipografía | 15 % | B- | B | Una familia, nada bajo 12 px |
| Espaciado y layout | 15 % | B | B | Cajas más compactas; panel de controles acotado |
| Color y contraste | 10 % | B | B | Sin cambios |
| Estados de interacción | 10 % | B- | B | Botones de 34 px; inicio deshabilitado con motivo |
| Responsive | 10 % | B- | B- | Sin cambios en esta vuelta |
| Calidad de contenido | 10 % | B | B | Sin cambios |
| Slop de IA | 5 % | C+ | C+ | Quedan las cajas de tarjeta |
| Movimiento | 5 % | B | B | Sin cambios |
| Sensación de rendimiento | 5 % | C | C | Pendiente medir con GPU real |

Media ponderada ≈ 2,9 / 4 → **B.** Sigue sin llegar a B+ (≈3,3).

Guía para medir FPS con GPU real: abre http://127.0.0.1:8765/?fps=1 en tu navegador normal, inicia una partida y mira el contador centrado arriba («FPS»).

Pendiente para B+: fusionar el HUD y la decisión en una sola columna; reducir el número de cajas con borde; medir con GPU real.
