# ARX-94e · medición M2 (resumen generado por scripts/medicion_94e.py)

Generado: 2026-11-21 22:17 · semillas: 20 · modo: completo · duración total: 56.5 s.
Se publica tal como salga. Criterio M2 (ARX-94_umbrales.md): al menos 5/20 semillas con divergencia por RNA-RIESGO o V-RNA-*.

## Escenario congelado

**M2: 1/20 semillas** con divergencia atribuida a RNA-RIESGO o V-RNA-* (criterio >= 5/20): NO CUMPLE.

- Semillas que cuentan: [110]
- Semillas con divergencia directa de cualquier origen: [110, 112]; de ellas, no atribuidas a la RNA: [112]
- Semillas con algún paso divergente (directo o consecuencia) con motivo RNA (dato aparte, no cuenta): [110, 112]
- Por tipo de cambio de la primera divergencia atribuida (una semilla puede sumar en varios): {'decision': 1, 'velocidad': 1, 'ruta': 0}
- Por motivo: {'RNA-RIESGO': 1, 'V-RNA-BARRANCO': 1}

| escenario | éxito híbrido | éxito sin_rna | colisiones híbrido | colisiones sin_rna | pasos med. híbrido | pasos med. sin_rna |
|---|---|---|---|---|---|---|
| congelado | 20/20 | 20/20 | 0 (0 sem.) | 0 (0 sem.) | 45.5 | 46.0 |

Por semilla (primera divergencia directa; cambio = decisión, velocidad y/o ruta):

| semilla | primera directa (paso, cambio) | motivo RNA | cuenta | col. híbrido | col. sin_rna | estado híbrido | estado sin_rna |
|---|---|---|---|---|---|---|---|
| 101 | - | - | no | 0 | 0 | EXITO | EXITO |
| 102 | - | - | no | 0 | 0 | EXITO | EXITO |
| 103 | - | - | no | 0 | 0 | EXITO | EXITO |
| 104 | - | - | no | 0 | 0 | EXITO | EXITO |
| 105 | - | - | no | 0 | 0 | EXITO | EXITO |
| 106 | - | - | no | 0 | 0 | EXITO | EXITO |
| 107 | - | - | no | 0 | 0 | EXITO | EXITO |
| 108 | - | - | no | 0 | 0 | EXITO | EXITO |
| 109 | - | - | no | 0 | 0 | EXITO | EXITO |
| 110 | 32, decision+velocidad | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | EXITO | EXITO |
| 111 | - | - | no | 0 | 0 | EXITO | EXITO |
| 112 | 34, velocidad+ruta | - | no | 0 | 0 | EXITO | EXITO |
| 113 | - | - | no | 0 | 0 | EXITO | EXITO |
| 114 | - | - | no | 0 | 0 | EXITO | EXITO |
| 115 | - | - | no | 0 | 0 | EXITO | EXITO |
| 116 | - | - | no | 0 | 0 | EXITO | EXITO |
| 117 | - | - | no | 0 | 0 | EXITO | EXITO |
| 118 | - | - | no | 0 | 0 | EXITO | EXITO |
| 119 | - | - | no | 0 | 0 | EXITO | EXITO |
| 120 | - | - | no | 0 | 0 | EXITO | EXITO |

Hash de las cifras de esta corrida (congelado, híbrido + sin_rna): `a2eccee9bc99cd737d19982cacdab4c7e328172e8bd29b51ddda59baaface9d5`

## Escenario exigente

**M2: 14/20 semillas** con divergencia atribuida a RNA-RIESGO o V-RNA-* (criterio >= 5/20): CUMPLE.

- Semillas que cuentan: [102, 103, 104, 105, 106, 107, 109, 110, 111, 112, 113, 117, 118, 120]
- Semillas con divergencia directa de cualquier origen: [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 116, 117, 118, 119, 120]; de ellas, no atribuidas a la RNA: [101, 108, 114, 116, 119]
- Semillas con algún paso divergente (directo o consecuencia) con motivo RNA (dato aparte, no cuenta): [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120]
- Por tipo de cambio de la primera divergencia atribuida (una semilla puede sumar en varios): {'decision': 14, 'velocidad': 14, 'ruta': 13}
- Por motivo: {'V-RNA-OBSTACULO': 3, 'RNA-RIESGO': 11, 'V-RNA-BARRANCO': 11}

| escenario | éxito híbrido | éxito sin_rna | colisiones híbrido | colisiones sin_rna | pasos med. híbrido | pasos med. sin_rna |
|---|---|---|---|---|---|---|
| exigente | 0/20 | 2/20 | 1 (1 sem.) | 0 (0 sem.) | 33.5 | 77.5 |

Por semilla (primera divergencia directa; cambio = decisión, velocidad y/o ruta):

| semilla | primera directa (paso, cambio) | motivo RNA | cuenta | col. híbrido | col. sin_rna | estado híbrido | estado sin_rna |
|---|---|---|---|---|---|---|---|
| 101 | 10, decision+velocidad+ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 102 | 12, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 103 | 12, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 104 | 11, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 105 | 17, decision+velocidad | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 106 | 9, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 107 | 13, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 108 | 25, velocidad+ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 109 | 2, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 110 | 11, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 111 | 8, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 112 | 6, decision+velocidad+ruta | V-RNA-OBSTACULO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 113 | 15, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | EXITO |
| 114 | 5, decision+velocidad+ruta | - | no | 1 | 0 | SIN_RUTA | SIN_RUTA |
| 115 | - | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 116 | 7, decision+velocidad+ruta | - | no | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 117 | 7, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 118 | 7, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |
| 119 | 12, ruta | - | no | 0 | 0 | SIN_RUTA | EXITO |
| 120 | 1, decision+velocidad+ruta | RNA-RIESGO, V-RNA-BARRANCO | sí | 0 | 0 | SIN_RUTA | SIN_RUTA |

Hash de las cifras de esta corrida (exigente, híbrido + sin_rna): `c823c5c056bb5b1fd10e54648df4d6e17c29ecc022b415611786262726d256c6`

## Hash del congelado

- Publicado el 17/11 (ev3-d84, test de regresión): `d6fb907994a30420652391e32b514bf5a4bb31c05f0d15f2f5aea9d1657cdfef`
- sha256 del archivo `docs/COMPARACION_POLITICAS.json` de esta rama (antes de 94f): `74b44118730b9de191d789fd87fcf9a9f34c9d377df2f62cce51046a5d761eed`
- Hash de esta corrida: ver cada escenario (solo híbrido y sin_rna, 94e no regenera `docs/`).

94e no escribe nada en `docs/` fuera de `docs/planes/mediciones/`; la regeneración única es 94f.
