# ARX-94e · medición M2 (resumen generado por scripts/medicion_94e.py)

Generado: 2026-11-21 22:15 · semillas: 20 · modo: completo · duración total: 62.2 s.
Se publica tal como salga. Criterio M2 (ARX-94_umbrales.md): al menos 5/20 semillas con divergencia por RNA-RIESGO o V-RNA-*.

## Escenario congelado

**M2: 2/20 semillas** con divergencia atribuida a RNA-RIESGO o V-RNA-* (criterio >= 5/20): NO CUMPLE.

- Semillas que cuentan: [11, 12]
- Semillas con divergencia directa de cualquier origen: [11, 12]; de ellas, no atribuidas a la RNA: ninguna
- Semillas con algún paso divergente (directo o consecuencia) con motivo RNA (dato aparte, no cuenta): [11, 12]
- Por tipo de cambio de la primera divergencia atribuida (una semilla puede sumar en varios): {'decision': 2, 'velocidad': 2, 'ruta': 2}
- Por motivo: {'V-RNA-OBSTACULO': 2}

| escenario | éxito híbrido | éxito sin_rna | colisiones híbrido | colisiones sin_rna | pasos med. híbrido | pasos med. sin_rna |
|---|---|---|---|---|---|---|
| congelado | 20/20 | 20/20 | 0 (0 sem.) | 0 (0 sem.) | 39.0 | 38.5 |

Por semilla (primera divergencia directa; cambio = decisión, velocidad y/o ruta):

| semilla | primera directa (paso, cambio) | motivo RNA | cuenta | col. híbrido | col. sin_rna | estado híbrido | estado sin_rna |
|---|---|---|---|---|---|---|---|
| 1 | - | - | no | 0 | 0 | EXITO | EXITO |
| 2 | - | - | no | 0 | 0 | EXITO | EXITO |
| 3 | - | - | no | 0 | 0 | EXITO | EXITO |
| 4 | - | - | no | 0 | 0 | EXITO | EXITO |
| 5 | - | - | no | 0 | 0 | EXITO | EXITO |
| 6 | - | - | no | 0 | 0 | EXITO | EXITO |
| 7 | - | - | no | 0 | 0 | EXITO | EXITO |
| 8 | - | - | no | 0 | 0 | EXITO | EXITO |
| 9 | - | - | no | 0 | 0 | EXITO | EXITO |
| 10 | - | - | no | 0 | 0 | EXITO | EXITO |
| 11 | 7, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | EXITO | EXITO |
| 12 | 9, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | EXITO | EXITO |
| 13 | - | - | no | 0 | 0 | EXITO | EXITO |
| 14 | - | - | no | 0 | 0 | EXITO | EXITO |
| 15 | - | - | no | 0 | 0 | EXITO | EXITO |
| 16 | - | - | no | 0 | 0 | EXITO | EXITO |
| 17 | - | - | no | 0 | 0 | EXITO | EXITO |
| 18 | - | - | no | 0 | 0 | EXITO | EXITO |
| 19 | - | - | no | 0 | 0 | EXITO | EXITO |
| 20 | - | - | no | 0 | 0 | EXITO | EXITO |

Hash de las cifras de esta corrida (congelado, híbrido + sin_rna): `84bd168df6d2296278675b78944e24aa00269e2de5515a0d60f4fa09166711bb`

## Escenario exigente

**M2: 17/20 semillas** con divergencia atribuida a RNA-RIESGO o V-RNA-* (criterio >= 5/20): CUMPLE.

- Semillas que cuentan: [1, 2, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20]
- Semillas con divergencia directa de cualquier origen: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]; de ellas, no atribuidas a la RNA: [3, 5, 11]
- Semillas con algún paso divergente (directo o consecuencia) con motivo RNA (dato aparte, no cuenta): [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
- Por tipo de cambio de la primera divergencia atribuida (una semilla puede sumar en varios): {'decision': 17, 'velocidad': 17, 'ruta': 17}
- Por motivo: {'RNA-RIESGO': 16, 'V-RNA-BARRANCO': 16, 'V-RNA-OBSTACULO': 1}

| escenario | éxito híbrido | éxito sin_rna | colisiones híbrido | colisiones sin_rna | pasos med. híbrido | pasos med. sin_rna |
|---|---|---|---|---|---|---|
| exigente | 0/20 | 4/20 | 0 (0 sem.) | 1 (1 sem.) | 39.0 | 59.5 |

Por semilla (primera divergencia directa; cambio = decisión, velocidad y/o ruta):

| semilla | primera directa (paso, cambio) | motivo RNA | cuenta | col. híbrido | col. sin_rna | estado híbrido | estado sin_rna |
|---|---|---|---|---|---|---|---|
| 1 | 4, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 1 | SIN_RUTA | EXITO |
| 2 | 13, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 3 | 3, velocidad+ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 4 | 1, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 5 | 4, ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 6 | 5, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 7 | 23, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 8 | 2, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 9 | 1, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 10 | 9, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 11 | 10, decision+velocidad+ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 12 | 6, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 13 | 18, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | EXITO |
| 14 | 4, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | EXITO |
| 15 | 11, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 16 | 4, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 17 | 3, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | EXITO |
| 18 | 6, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 19 | 9, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 20 | 6, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |

Hash de las cifras de esta corrida (exigente, híbrido + sin_rna): `8d79e8332d39b6337be5600bae3866c952435d2db0c3df5bae1af47d78a38ed3`

## Hash del congelado

- Publicado el 17/11 (ev3-d84, test de regresión): `d6fb907994a30420652391e32b514bf5a4bb31c05f0d15f2f5aea9d1657cdfef`
- sha256 del archivo `docs/COMPARACION_POLITICAS.json` de esta rama (antes de 94f): `74b44118730b9de191d789fd87fcf9a9f34c9d377df2f62cce51046a5d761eed`
- Hash de esta corrida: ver cada escenario (solo híbrido y sin_rna, 94e no regenera `docs/`).

94e no escribe nada en `docs/` fuera de `docs/planes/mediciones/`; la regeneración única es 94f.
