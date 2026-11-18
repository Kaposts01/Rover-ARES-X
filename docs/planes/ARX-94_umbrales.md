# ARX-94 · umbrales confirmados ANTES de medir (ev3-d83 A)

Confirmados por el Orquestador para 94d y 94e. Se fijan aquí, en commit propio, antes de cualquier medición del rediseño.

- **94d (RNA v2, 20 mapas no vistos):** recall de barrancos v2 ≥ 0,6; falsos positivos (FP) ≤ 0,2 %; ECE ≤ 0,03. La macro-F1 de v1 se publica sin cambios.
- **94e (medición M2, 20 semillas, congelado y exigente):** se publica tal como salga; criterio de aceptación de M2: ≥ 5/20 semillas con divergencia por RNA-RIESGO o V-RNA-*. Si es < 5/20, el informe lo dice y la ficha que sigue se abre aparte.
- **Mapa orbital (ev3-d83):** barrancos de menos de 2 m de profundidad se detectan con p_detectar = 0,3; los de 2 m o más, con 0,8. No ve las grietas de menos de 2 m.
- **Congelado (ev3-d84 A):** regeneración única con atribución, al cerrar el bloque 1 (94f). Antes y después del cierre, el hash del congelado se anota en el plan; no se regenera nada antes.
