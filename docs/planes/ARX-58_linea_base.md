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

## Resultados (medidos 18:07–18:32, sin cambios de código)

Datos: `mediciones/medicion_58_grande.json`, `medicion_58_pequeno.json` (partidas) y `medicion_58_mapas.json` (mapas ganables), log en `mediciones/medicion_58.log`.

**Partidas ganadas (EXITO / 20), rotuladas aparte de los mapas**

| Nivel | Pequeño (20×30) | Grande (40×60) |
|---|---|---|
| 1 | 20/20 | 20/20 |
| 2 | 20/20 | 20/20 |
| 3 | 20/20 | 10/20 |
| 4 | 20/20 | 6/20 |
| 5 | 20/20 | 4/20 |

**Mapas ganables (garantía de la semilla pedida, 20 por nivel)**

| Nivel | Pequeño | Grande |
|---|---|---|
| 1 | 20/20 | 20/20 |
| 2 | 20/20 | 20/20 |
| 3 | 20/20 | 4/20 |
| 4 | 20/20 | 0/20 |
| 5 | 20/20 | 0/20 |

**Lectura.** Un mapa ganable no es una partida ganada: en el grande de nivel 3 hay 10 partidas EXITO sobre 4 mapas ganables, y en niveles 4 y 5 hay partidas EXITO sin mapa ganable. Las cifras de partidas grandes coinciden con las de 79d (20, 20, 10, 6, 4). Esta es la línea base por nivel. No se ha ajustado nada.
