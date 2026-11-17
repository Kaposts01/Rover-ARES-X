# ARX-58 · línea base por nivel (protocolo de 79)

Base: b84e640. Rama feat/arx-58-linea-base. Decisión del Maestro (triaje de la cola): ARX-58 entra como PR posterior.

## Criterio (escrito antes de medir)
- Protocolo de 79a/79d: grande (40×60) y pequeño (20×30), niveles 1 a 5, semillas 1 a 20 por nivel, garantía activa, eventos por defecto, tope de 500 pasos.
- **Partidas ganadas** por nivel y tamaño: el resultado de `scripts/medir_garantia.py` (EXITO/derrota y causa), tal como salga.
- **Mapas ganables** por nivel y tamaño: la garantía de la semilla pedida (`Partida` sin `sin_garantia`), contada con `scripts/linea_base_58.py`. Se rotula aparte de las partidas ganadas: un mapa ganable no es una partida ganada.
- No se ajusta nada para mejorar cifras. No hay cambio de juego: el hash del congelado d6fb9079… no cambia.
- Esta línea base no compara variantes: es la referencia por nivel contra la que se medirá lo que venga después.

## Datos
- `docs/planes/mediciones/medicion_58_grande.json` y `..._pequeno.json` (partidas, por medir_garantia).
- `docs/planes/mediciones/medicion_58_mapas.json` (mapas ganables de ambos tamaños).
