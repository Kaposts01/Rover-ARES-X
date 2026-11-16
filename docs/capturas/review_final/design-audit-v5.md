# Design review · vuelta 15 (barra única y móvil)

Cambios desde la vuelta 14: la barra inferior reúne las pestañas (historial y gráficas) y los controles manuales (pad, zoom, encuadre). Ya no hay caja de controles manuales separada. En móvil (375×812) la cabecera, la decisión plegada, la sección de controles y la barra quedan separadas.

Puntuación (A–F):
- Jerarquía visual: B+ (una barra de control, una columna de estado, escena dominante)
- Tipografía: B
- Espaciado y layout: B
- Color y contraste: B
- Estados de interacción: B
- Responsive: B (móvil apilado y sin solapes en la carga directa a 375 px)
- Calidad de contenido: B
- Slop de IA: C+ (quedan cajas: columna, controles y barra)
- Movimiento: B
- Rendimiento: C (pendiente de medir con GPU; lo mide el usuario con ?fps=1)

Media ponderada ≈ 2,96 / 4 → **B.** No llega a B+ (≈3,3). Con el dato de GPU todavía sin medir, la auditoría no puede cerrarse como B+.
