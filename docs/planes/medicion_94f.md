# ARX-94f: atribución de las pruebas en rojo, corrección del mapa estimado y regeneración única

Fecha: 2026-11-22. Rama `feat/rediseno-visual`, después de integrar `feat/arx-94-sensores` (94a–94e).
Cierra lo que dejó pendiente [ARX-94_pruebas_en_rojo](ARX-94_pruebas_en_rojo.md) y la regla «no se integra nada de ARX-94 con pruebas en rojo sin su atribución escrita».

## 1. Atribución de las 14 pruebas en rojo

Primero se corrieron las 14 pruebas con `simulador.MUNDO_V1 = True` (mundo anterior), con el resto del código igual:

- **8 pasan con el mundo anterior.** Fallaban solo porque el mundo v2 cambia lo que ocurre en cada semilla. La lógica que prueban no cambió. Se adaptaron conservando las mismas aserciones:

| Prueba | Antes | Ahora | Motivo |
|---|---|---|---|
| `test_historial` ×2, `test_estados_arx33`, `test_replanteo_ag_arx31` (sismo con grieta en la ruta) | semilla 11 | semilla 3 | con v2, ninguna grieta de la 11 cae sobre la ruta |
| `test_triple_orden_de_vetos_y_avisos_fijado_semilla_*` | 3 | 18 | misma secuencia de motivos, avisos y vetos |
| `test_triple_orden_semilla_*_termina_sin_ruta_tras_el_veto` | 7 | 9 | ídem |
| `test_traza_en_vivo_semilla_*_diverge_en_las_tres_tecnicas` | 4 | 1 | divergen las tres técnicas |
| `test_caza_parada_termina_con_causa` | repro de mapa (semilla 6) | causa provocada | con v2, ninguna semilla 1–59 atasca la caza; se fuerza la misma causa (sitios visitados y difuso a 0) |

- **6 fallan también con el mundo anterior.** Las causan los sensores y el supervisor de 94b/94c:
  - **congelado** (filas idénticas y huella): cifras nuevas por diseño de 94a–94c. Se resuelven con la regeneración única (sección 4).
  - **resbalón** ×2: en la semilla 1 la ruta ya no pisa ninguna pendiente mayor a 20° (la máxima es 18°). Con la semilla 5 se reproduce: 3 resbalones a velocidad 1,0 y ninguno a 0,2.
  - **el híbrido gana la semilla 7 exigente**: lo resuelve la corrección de la sección 2.
  - **garantía con señal** (semilla 4, nivel 3): queda como fallo conocido (sección 3).

## 2. Corrección del rendimiento en el escenario exigente

### Causa medida

En el exigente (ruido 0,6) el telémetro de desnivel tiene σ = 0,6 × 5 = 3 m. Con el umbral de barranco en -2 m, una celda llana se lee bajo el umbral en cerca del 25 % de las lecturas, y **una sola lectura** la dejaba en riesgo 1 para siempre.

- En las semillas 7, 1 y 4 el sensor marcó 19, 34 y 37 celdas libres como barranco, y ningún barranco real. La misión acababa en SIN_RUTA: híbrido 0/20.
- Corregido el sensor, la RNA (entrenada con ruido 0,1) hacía lo mismo. Con ruido 0,6 marca como barranco el 18 % de las celdas libres, con ECE 0,195 (mapas de prueba 100–119).

### Cambios en el estimador

No se tocaron el escenario ni los umbrales.

1. **Fusión del desnivel de las vecinas.** Se usa la media de las lecturas de cada celda. Se marca con al menos n_min lecturas cuya media quede bajo el umbral, con n_min = ceil((2,326·σ/2)²) (falso positivo < 1 % en una celda llana). Con ruido nominal n_min = 1 y la regla es la original.
2. **RNA según el ruido del sensor.** Con ruido mayor que el nominal, la misión usa la RNA entrenada con ese mismo ruido, que queda calibrada (ECE 0,017). Además, la marca permanente exige 2 observaciones con p media > 0,5. Los vetos inmediatos (V-BORDE-BARRANCO, V-RNA-BARRANCO) no cambian.
3. **Contacto.** La celda que no se pudo pisar (V-CELDA-BLOQUEADA) pasa a riesgo 1. Antes el planificador insistía: hasta 490 choques en `sin_rna`.
4. **Caza.** El BFS hacia el dron evita primero las celdas con riesgo conocido, igual que el veto de la misión. Sobre el dron se prefiere una vecina sin riesgo (repro: semilla 2, nivel 5).

### Resultado

Medido con `scripts/medicion_94e.py`, híbrido frente a `sin_rna`:

| Exigente | Híbrido antes | Híbrido ahora | `sin_rna` ahora |
|---|---|---|---|
| Semillas 1–20 | 0/20 | **19/20** (6 choques) | 19/20 (7 choques) |
| Semillas 101–120 (no vistas) | 0/20 | **17/20** (9 choques) | 17/20 (10 choques) |

El congelado no cambia: 20/20 y el mismo hash de cifras que la 94e publicada (`84bd168d…`).

**Lectura honesta.** Con σ = 3 m la RNA no puede detectar barrancos con una sola observación: el recall es 0 incluso entrenándola con ese ruido. Calibrada, deja de inventarlos. Por eso el M2 exigente baja a 3/20, por debajo del criterio de 5/20. En el congelado sigue en 2/20, igual que en la 94e.

## 3. Fallo conocido (xfail estricto)

`test_ninguna_senal_aceptada_con_drones_deja_sin_ganar[3]`: semilla 4, nivel 3, mapa pequeño, todos los eventos activos.

- **Qué pasa:** el rover visita los 4 sitios y destruye los drones, pero un meteorito (-5 % de batería) lo deja sin batería a 2 celdas del refugio. Ocurre también sin la señal.
- **Por qué no se corrigió:** reservar el daño del meteorito en la garantía lo arregla, pero cambia el mapa elegido en muchas semillas y deja sin mapa ganable al nivel 5 pequeño (5 pruebas nuevas en rojo). Hay que rebalancear la garantía (margen, batería por nivel o estaciones, hoy apagadas), y eso es una decisión de diseño.

## 4. Regeneración única de cifras

Se corrió `scripts/regenerar_todo.py`, que regenera `COMPARACION_POLITICAS*.json`, `TRAZA_DIVERGENCIAS_exigente.csv`, `TABLA_MODOS.md`, `tabla_modos.csv` y `REJILLA_RESBALON_exigente.*`. La huella del congelado en `test_fisica_velocidad.py` pasa de `d6fb9079…` (mundo v1) a `fec4500d…`. Esa huella ya salía así antes de los cambios de la sección 2, así que el cambio viene de 94a–94c.

| Escenario | Variante | Publicado (mundo v1) | Regenerado |
|---|---|---|---|
| exigente | híbrido | 20/20, 0 choques | 19/20, 6 choques |
| exigente | `sin_rna` | 20/20, 0 | 19/20, 7 |
| exigente | `sin_difuso` | 15/20, 1 | 18/20, 6 |
| exigente | `ruta_corta` | 15/20, 0 | 18/20, 18 |
| exigente | `ag_puro` | 16/20, 1 | 18/20, 13 |
| exigente10 | híbrido | 17/20, 0 | 17/20, 10 |
| exigente10 | `sin_ag_vecino` | 14/20, 0 | 11/20, 8 |
| congelado | todas | 20/20 | 20/20 (`ruta_corta`: 1 choque) |

## 5. Textos que citan cifras anteriores (pendiente de revisión del autor)

- `INFORME_TECNICO.md`: secciones de ablaciones y contribución de cada técnica (líneas ~67–130). Entre otras, «Difuso: cumple, con efecto en el resultado», las derrotas del híbrido y las cifras de 10 sitios.
- `README.md:68`: 10 sitios, híbrido 17/20 frente a 14 con el vecino más cercano (ahora 17 frente a 11).
- `docs/MATRIZ_REQUISITOS_PDF.md:210`: «20 de 20 con difuso y 15 de 20 sin él» (ahora 19/20 y 18/20).
- `docs/OPERACION_MOTOR.md:79`: «el híbrido gana 20/20 … sin difuso, 15/20».
