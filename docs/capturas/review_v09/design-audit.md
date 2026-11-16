# Design review v09 · ARES-X (escena, HUD, paneles, gráficos, laboratorios, móvil)

Fecha: 2026-11-13 · Ámbito: http://127.0.0.1:8765/ · Navegador: gstack `$B`
Cambios desde v08: botones primarios sólidos (sin degradado y sin sombra de brillo); eliminado el desenfoque de vidrio en paneles y en la superposición de laboratorios; laboratorios (genético, difuso, RNA) con cabeceras y tablas uniformes; indicador de progreso del AG.

## Puntuación (A–F; 4 = A)

| Categoría | Peso | v08 | v09 | Nota |
|---|---|---|---|---|
| Jerarquía visual | 15 % | B | B | Sin cambio |
| Tipografía | 15 % | B | B | Sin cambio |
| Espaciado y layout | 15 % | B- | B- | Decisión IA sigue con scroll en 720 px (435 px de contenido frente a 338 visibles) |
| Color y contraste | 10 % | B | B | Botones sólidos, más consistente |
| Estados de interacción | 10 % | C+ | B- | Progreso visible en el AG; estados de laboratorio con etiqueta |
| Responsive | 10 % | B- | B- | Sin cambio desde v08 |
| Calidad de contenido | 10 % | C+ | B- | Textos de laboratorio explicados; motivos y fuentes visibles |
| Slop de IA (5 %) | 5 % | C | C+ | Degradados y vidrio eliminados; quedan tarjetas de borde redondeado |
| Movimiento | 5 % | B | B | Barra de progreso sobria |
| Sensación de rendimiento | 5 % | D | D | Sin medición real fuera de render por software |

**Puntuación de diseño: B- (≈2,7/4)**, antes C+ (≈2,6/4). **Slop de IA: C+**, antes C.

## Pendientes conocidos
- Panel «Decisión de la IA» aún requiere scroll en 720 px (scroll visible).
- Comparación de políticas: esperando el contrato de Trabajo (GET /comparacion aún responde 404).
- Rendimiento: solo medible en render por software.
