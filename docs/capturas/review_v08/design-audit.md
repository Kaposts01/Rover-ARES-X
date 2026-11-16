# Design review · ARES-X (escena, HUD, paneles, gráficos, móvil)

Fecha: 2026-11-13 · Ámbito: http://127.0.0.1:8765/ · Navegador: gstack `$B` (Aside no disponible en PATH)
Modo: pase completo sobre el estado de v08 · No es repositorio git: sin commits por hallazgo; cambios en api/static.

## Puntuación (escala A–F, 4 = A; media ponderada según la skill)

| Categoría | Peso | Antes | Ahora | Nota |
|---|---|---|---|---|
| Jerarquía visual | 15 % | B | B | Foco en el rover y la ruta; HUD legible |
| Tipografía | 15 % | B | B | Mono para valores, sans para etiquetas, tamaños >= 11 px |
| Espaciado y layout | 15 % | B | B- | Decisión con scroll; controles con desvanecido |
| Color y contraste | 10 % | B | B | Paleta cálida coherente; semáforo de series con etiqueta |
| Estados de interacción | 10 % | C | C+ | Tooltip de gráfica fijo; leyenda pulsable; falta hover en pads |
| Responsive | 10 % | D | B- | Móvil corregido (ver hallazgo H1) |
| Calidad de contenido | 10 % | C+ | C+ | Textos técnicos en español; ayudas largas en el panel |
| Slop de IA (5 %) | 5 % | C | C | Botones con degradado y vidrio esmerilado (ver L1, L2) |
| Movimiento | 5 % | B | B | Pulso de aviso y transición de barra; suaves |
| Sensación de rendimiento | 5 % | D | D | ~6 FPS en render por software; no concluyente sin GPU |

**Puntuación de diseño: C+ (≈2,6/4)**, antes ≈2,5 (C+). **Puntuación de slop de IA: C** (sin cambio).

## Hallazgos y estado

- **H1 (alto, corregido).** Móvil (375 px) inutilizable: los controles tapaban la escena, el mensaje se montaba sobre el HUD y las gráficas flotaban a mitad de pantalla. Causa: reglas de 1100 px que sobrescribían la regla de 760 px, y `min-height` del panel plegado. Verificado en `resp4-mobile.png`.
- **H2 (alto, corregido).** Panel «Decisión de la IA» cortaba «Supervisor · decisión y motivos» con desvanecido y sin barra visible. Ahora: altura `calc(100vh - 380px)`, barra de desplazamiento visible en WebKit/Chromium y cabeceras más compactas. El contenido sigue necesitando scroll en 720 px (417 px de contenido frente a 338 visibles); está señalado, no eliminado.
- **M1 (medio, corregido).** El tooltip de la gráfica tapaba la línea «libre» al 100 %. Ahora es una franja fija sobre la gráfica.
- **M2 (medio, corregido).** Texto de ayuda de la gráfica repetía el tooltip. Ahora solo indica la leyenda.
- **M3 (medio, corregido).** Cabeceras de panel en estilos distintos. Ahora todas en mayúsculas acento.
- **M4 (medio, parcial).** Controles con contenido recortado en 720 px. Desvanecido de indicación; el panel tiene scroll. Pendiente compactar la sección de intervención.
- **L1 (bajo, no cambiado).** Botones primarios con degradado azul. La skill lo marca como señal de slop. Decisión de estilo: un color sólido de la paleta sería más propio.
- **L2 (bajo, no cambiado).** Vidrio esmerilado (`backdrop-filter`) como superficie por defecto. Conviene reservarlo para donde da profundidad.
- **R1 (medio, corregido).** Rover poco legible en la vista general. Anillo de resalte bajo el rover.
- **R2 (medio, corregido).** Sitio científico como placeholder (gema plana). Ahora cristal hexagonal con puntas y núcleo luminoso (`diseno_v08_e_rover_lado.png`).

## Evidencia

- `panel.png`: panel de decisión y gráficas en escritorio, antes de la barra visible.
- `resp4-desktop.png`, `resp4-tablet.png`, `resp4-mobile.png`: tres tamaños tras las correcciones.
- `docs/capturas/diseno_v08_*`: escena y detalle del rover con cristal nuevo.

## Límites de esta revisión

- Sin flujo Aside: `$B` no tiene las sesiones del usuario; no hubo pruebas de autenticación (la app no tiene login).
- Rendimiento medido solo en render por software (~6 FPS). No se puede juzgar la fluidez real sin GPU.
- Sin pruebas de accesibilidad automatizadas (contraste calculado por página no ejecutado).
