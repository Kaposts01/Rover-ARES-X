# ARX-94e · plan de la medición M2

Preparado el 21/11, sin correr. Script: `scripts/medicion_94e.py`; pruebas ligeras: `tests/test_medicion_94e.py`. Umbrales: `ARX-94_umbrales.md` (escritos antes de medir).

## 1. Procedimiento exacto (con turno del Orquestador, CPU y RAM < 80 %)

1. Rama de 94 integrada (94a–94d) limpia; anotar `git rev-parse --short HEAD`.
2. Anotar el hash vigente del congelado (publicado 17/11: `d6fb907994a30420652391e32b514bf5a4bb31c05f0d15f2f5aea9d1657cdfef`). No regenerar nada de `docs/` antes de 94f.
3. Verificación previa (segundos): `OMP_NUM_THREADS=1 python scripts/medicion_94e.py --rapido --salida <directorio temporal>`.
4. Corrida completa, un solo proceso, 1 hilo: `OMP_NUM_THREADS=1 python scripts/medicion_94e.py > docs/planes/mediciones/medicion_94e.log 2>&1`.
5. Revisar `docs/planes/mediciones/medicion_94e.md` y los dos JSON; publicar tal como salga, sin reintentos ni ajustes de motor o umbrales.
6. Si el conteo M2 es < 5/20 en un escenario, el informe lo dice y la ficha ev3-d83 fija qué sigue (no se abre otra tarea aquí).

## 2. Qué mide y cómo

- 20 semillas (1 a 20), escenarios `congelado` y `exigente` de `juego/comparacion.py` (sin tocarlos); por semilla una partida de `hibrido` y una de `sin_rna` (misma semilla, mismo mundo).
- Divergencia: misma regla que `trazar_divergencias` (firma posición/acción/velocidad/motivos; «directa» = primera divergencia con el mismo estado previo; el resto es «consecuencia»). Tipo: decisión, velocidad, ruta.
- Atribución: motivos de la bitácora del híbrido en el paso divergente (`RNA-RIESGO[-2]:...` y `V-RNA-*`). Cuenta para M2 la semilla cuya primera divergencia directa trae uno de ellos. Aparte, sin contar: semillas con cualquier paso divergente que traiga esos motivos.
- Colisiones y éxito del híbrido y de `sin_rna`, aparte de M2 (total, semillas con colisión, mediana de pasos, batería).
- Complemento opcional, no necesario para M2: `python scripts/traza_divergencias.py 20 exigente` (reescribe `docs/TRAZA_DIVERGENCIAS_exigente.csv`; NO ejecutarlo en 94e, queda para la regeneración de 94f).

## 3. Qué se publica

`docs/planes/mediciones/medicion_94e_congelado.json`, `medicion_94e_exigente.json`, `medicion_94e.md` (conteo X/20 frente a ≥ 5/20, por semilla y por tipo y motivo, colisiones y éxito, hashes) y el `.log`. No se toca `docs/*.json` ni el hash del congelado: es de 94f.

## 4. Estimación de recursos (corrida completa)

Medido en modo rápido: 3 semillas, mapa 12×16, nivel 2, 2 partidas por semilla = 6 partidas en 2,7 s (~0,45 s por partida, 1 hilo). Extrapolación (estimación, no medición): el mapa grande tiene 3,75 veces más celdas y las partidas unos 2–3 veces más pasos, con replanificaciones más caras: ~3–5 s por partida en congelado y algo más en exigente (nivel 5, física de velocidad). Son 80 partidas (2 variantes × 20 semillas × 2 escenarios): **del orden de 5 a 10 minutos en total, tope razonable 15** (coincide con los «~15 min» del plan). Un solo proceso y un hilo (`OMP_NUM_THREADS=1`); RAM esperada < 1 GB (una partida viva a la vez; el JSON final pesa pocos MB). Si el primer escenario pasa de 10 minutos, parar y avisar. El tiempo real queda en el `.md` («duración total»).

## 5. Qué cambia respecto del congelado publicado el 17/11

Todas las cifras pueden cambiar: el mundo es v2 (94a), hay sensores físicos (94b), supervisor y mapa estimado por profundidad (94c) y RNA v2 (94d). El «antes» sale de los JSON publicados en `docs/` de `main` (idénticos en esta rama). La columna «después» se rellena en 94f, tras la regeneración única, con la causa por bloque (mundo v2, sensores, supervisor, RNA v2). Las replanificaciones no están en los JSON publicados: se obtienen de la bitácora en 94f (antes y después). Referencia del antes en la traza exigente: `sin_rna` tiene 3 semillas con divergencia directa (4, 10 y 18), todas con decisión, velocidad y ruta; en la medición M2 sale el equivalente atribuido a la RNA.

**congelado** (`docs/COMPARACION_POLITICAS.json`, 20 semillas)

| variante | métrica | antes (17/11) | después (94f) | causa |
|---|---|---|---|---|
| hibrido | éxito | 20/20 |  |  |
| hibrido | pasos (mediana) | 43.0 |  |  |
| hibrido | colisiones (media) | 0.0 |  |  |
| hibrido | batería final (media) | 52.8 |  |  |
| hibrido | sitios visitados (media) | 3.0 |  |  |
| sin_rna | éxito | 20/20 |  |  |
| sin_rna | pasos (mediana) | 43.0 |  |  |
| sin_rna | colisiones (media) | 0.0 |  |  |
| sin_rna | batería final (media) | 52.8 |  |  |
| sin_rna | sitios visitados (media) | 3.0 |  |  |
| sin_difuso | éxito | 20/20 |  |  |
| sin_difuso | pasos (mediana) | 43.0 |  |  |
| sin_difuso | colisiones (media) | 0.0 |  |  |
| sin_difuso | batería final (media) | 52.8 |  |  |
| sin_difuso | sitios visitados (media) | 3.0 |  |  |
| sin_ag_vecino | éxito | 20/20 |  |  |
| sin_ag_vecino | pasos (mediana) | 44.0 |  |  |
| sin_ag_vecino | colisiones (media) | 0.0 |  |  |
| sin_ag_vecino | batería final (media) | 51.35 |  |  |
| sin_ag_vecino | sitios visitados (media) | 3.0 |  |  |
| sin_ag_mas_corta | éxito | 20/20 |  |  |
| sin_ag_mas_corta | pasos (mediana) | 43.0 |  |  |
| sin_ag_mas_corta | colisiones (media) | 0.0 |  |  |
| sin_ag_mas_corta | batería final (media) | 52.8 |  |  |
| sin_ag_mas_corta | sitios visitados (media) | 3.0 |  |  |
| sin_ag_2opt | éxito | 20/20 |  |  |
| sin_ag_2opt | pasos (mediana) | 43.0 |  |  |
| sin_ag_2opt | colisiones (media) | 0.0 |  |  |
| sin_ag_2opt | batería final (media) | 52.8 |  |  |
| sin_ag_2opt | sitios visitados (media) | 3.0 |  |  |
| ruta_corta | éxito | 20/20 |  |  |
| ruta_corta | pasos (mediana) | 48.5 |  |  |
| ruta_corta | colisiones (media) | 0.0 |  |  |
| ruta_corta | batería final (media) | 50.6 |  |  |
| ruta_corta | sitios visitados (media) | 3.0 |  |  |
| ag_puro | éxito | 20/20 |  |  |
| ag_puro | pasos (mediana) | 43.0 |  |  |
| ag_puro | colisiones (media) | 0.0 |  |  |
| ag_puro | batería final (media) | 52.8 |  |  |
| ag_puro | sitios visitados (media) | 3.0 |  |  |

**exigente** (`docs/COMPARACION_POLITICAS_exigente.json`, 20 semillas)

| variante | métrica | antes (17/11) | después (94f) | causa |
|---|---|---|---|---|
| hibrido | éxito | 20/20 |  |  |
| hibrido | pasos (mediana) | 53.0 |  |  |
| hibrido | colisiones (media) | 0.0 |  |  |
| hibrido | batería final (media) | 25.3 |  |  |
| hibrido | sitios visitados (media) | 4.0 |  |  |
| sin_rna | éxito | 20/20 |  |  |
| sin_rna | pasos (mediana) | 53.0 |  |  |
| sin_rna | colisiones (media) | 0.0 |  |  |
| sin_rna | batería final (media) | 25.5 |  |  |
| sin_rna | sitios visitados (media) | 4.0 |  |  |
| sin_difuso | éxito | 15/20 |  |  |
| sin_difuso | pasos (mediana) | 53.5 |  |  |
| sin_difuso | colisiones (media) | 0.05 |  |  |
| sin_difuso | batería final (media) | 22.1 |  |  |
| sin_difuso | sitios visitados (media) | 4.0 |  |  |
| sin_ag_vecino | éxito | 19/20 |  |  |
| sin_ag_vecino | pasos (mediana) | 58.0 |  |  |
| sin_ag_vecino | colisiones (media) | 0.0 |  |  |
| sin_ag_vecino | batería final (media) | 21.425 |  |  |
| sin_ag_vecino | sitios visitados (media) | 3.95 |  |  |
| sin_ag_mas_corta | éxito | 20/20 |  |  |
| sin_ag_mas_corta | pasos (mediana) | 53.0 |  |  |
| sin_ag_mas_corta | colisiones (media) | 0.0 |  |  |
| sin_ag_mas_corta | batería final (media) | 25.3 |  |  |
| sin_ag_mas_corta | sitios visitados (media) | 4.0 |  |  |
| sin_ag_2opt | éxito | 20/20 |  |  |
| sin_ag_2opt | pasos (mediana) | 53.0 |  |  |
| sin_ag_2opt | colisiones (media) | 0.0 |  |  |
| sin_ag_2opt | batería final (media) | 25.3 |  |  |
| sin_ag_2opt | sitios visitados (media) | 4.0 |  |  |
| ruta_corta | éxito | 15/20 |  |  |
| ruta_corta | pasos (mediana) | 58.0 |  |  |
| ruta_corta | colisiones (media) | 0.0 |  |  |
| ruta_corta | batería final (media) | 19.0 |  |  |
| ruta_corta | sitios visitados (media) | 3.8 |  |  |
| ag_puro | éxito | 16/20 |  |  |
| ag_puro | pasos (mediana) | 54.0 |  |  |
| ag_puro | colisiones (media) | 0.05 |  |  |
| ag_puro | batería final (media) | 22.7 |  |  |
| ag_puro | sitios visitados (media) | 3.95 |  |  |

**exigente10** (`docs/COMPARACION_POLITICAS_exigente10.json`, 20 semillas)

| variante | métrica | antes (17/11) | después (94f) | causa |
|---|---|---|---|---|
| hibrido | éxito | 17/20 |  |  |
| hibrido | pasos (mediana) | 75.0 |  |  |
| hibrido | colisiones (media) | 0.0 |  |  |
| hibrido | batería final (media) | 20.55 |  |  |
| hibrido | sitios visitados (media) | 9.9 |  |  |
| sin_rna | éxito | 17/20 |  |  |
| sin_rna | pasos (mediana) | 75.0 |  |  |
| sin_rna | colisiones (media) | 0.0 |  |  |
| sin_rna | batería final (media) | 20.55 |  |  |
| sin_rna | sitios visitados (media) | 9.9 |  |  |
| sin_difuso | éxito | 14/20 |  |  |
| sin_difuso | pasos (mediana) | 75.0 |  |  |
| sin_difuso | colisiones (media) | 0.05 |  |  |
| sin_difuso | batería final (media) | 16.7 |  |  |
| sin_difuso | sitios visitados (media) | 9.9 |  |  |
| sin_ag_vecino | éxito | 14/20 |  |  |
| sin_ag_vecino | pasos (mediana) | 83.0 |  |  |
| sin_ag_vecino | colisiones (media) | 0.0 |  |  |
| sin_ag_vecino | batería final (media) | 7.75 |  |  |
| sin_ag_vecino | sitios visitados (media) | 9.7 |  |  |
| sin_ag_mas_corta | éxito | 17/20 |  |  |
| sin_ag_mas_corta | pasos (mediana) | 75.0 |  |  |
| sin_ag_mas_corta | colisiones (media) | 0.0 |  |  |
| sin_ag_mas_corta | batería final (media) | 21.425 |  |  |
| sin_ag_mas_corta | sitios visitados (media) | 9.9 |  |  |
| sin_ag_2opt | éxito | 17/20 |  |  |
| sin_ag_2opt | pasos (mediana) | 72.5 |  |  |
| sin_ag_2opt | colisiones (media) | 0.0 |  |  |
| sin_ag_2opt | batería final (media) | 21.2 |  |  |
| sin_ag_2opt | sitios visitados (media) | 9.9 |  |  |
| ruta_corta | éxito | 7/20 |  |  |
| ruta_corta | pasos (mediana) | 82.0 |  |  |
| ruta_corta | colisiones (media) | 0.1 |  |  |
| ruta_corta | batería final (media) | 3.85 |  |  |
| ruta_corta | sitios visitados (media) | 9.45 |  |  |
| ag_puro | éxito | 15/20 |  |  |
| ag_puro | pasos (mediana) | 75.5 |  |  |
| ag_puro | colisiones (media) | 0.3 |  |  |
| ag_puro | batería final (media) | 17.05 |  |  |
| ag_puro | sitios visitados (media) | 9.85 |  |  |

## 6. Pruebas en rojo tras 94c (a atribuir en 94f)

Tomadas de `ARX-94_pruebas_en_rojo.md`; no se relajan ni se editan. Pendiente de verificar en 94f si alguna ya fallaba con solo 94a y 94b (punta 2fc2daf).

| Archivo | Prueba | causa | antes → después |
|---|---|---|---|
| `tests/test_eventos_simultaneos.py` | `test_triple_orden_de_vetos_y_avisos_fijado_semilla_3` |  |  |
| `tests/test_eventos_simultaneos.py` | `test_triple_orden_semilla_7_termina_sin_ruta_tras_el_veto` |  |  |
| `juego/tests/test_caza_parada_arx79c.py` | `test_caza_parada_termina_con_causa` |  |  |
| `juego/tests/test_comparacion_escenarios.py` | `test_regresion_congelado_filas_identicas` |  |  |
| `juego/tests/test_fisica_velocidad.py` | `test_resbalon_a_velocidad_alta` |  |  |
| `juego/tests/test_fisica_velocidad.py` | `test_resbalon_vuelve_a_la_celda_anterior_y_gasta_bateria` |  |  |
| `juego/tests/test_fisica_velocidad.py` | `test_congelado_no_cambia` |  |  |
| `juego/tests/test_percepcion_arx90.py` | `test_regresion_semilla_7_exigente_el_hibrido_gana` |  |  |
| `juego/tests/test_trazas_divergencia.py` | `test_traza_en_vivo_semilla_4_diverge_en_las_tres_tecnicas` |  |  |
