# ARX-88 (b) · el porqué de cada paso, versión reducida

Decisión: ev3-d82 A (Maestro, por delegación). Base: b84e640. Rama feat/arx-88-porque-paso. Sin la tira de ARX-36a (pendiente declarado).

## Qué falta en b84e640 (evidencia)
- El panel de supervisión muestra motivos y acción, pero no dice qué predijo la RNA, qué regla difusa disparó y con qué velocidad, ni qué ruta fijó el planificador en ese mismo paso.
- Ya existe: `/paneles` con `rna`, `difuso`, `ag` y `supervisor` del último paso (`_paneles`, api/servidor.py).

## Criterio de hecho
1. Por cada paso, el panel de supervisión muestra cuatro líneas, con datos del paso:
   - **RNA**: la clase más probable y su probabilidad (de `rna.p_libre/p_obstaculo/p_barranco`).
   - **Difuso**: las reglas disparadas y la velocidad; «no usado» si el modo no usa el difuso.
   - **Planificador**: la ruta planeada en celdas (`ag.ruta_planeada`).
   - **Supervisor**: la acción y los motivos con su código (los que empiezan por V- son vetos).
2. El texto sale de los datos del paso, no de frases fijas: si un dato no existe, la línea dice «sin dato» (M17).
3. Sin cambios en el juego: hash del congelado d6fb9079… sin cambios.

## Pruebas
- Función pura en JS (si la hay) o comprobación en Chrome en 8766 (no en 8765) de que las cuatro líneas cambian con el paso.
- API: /paneles sigue devolviendo las mismas claves (no se quitan campos).
