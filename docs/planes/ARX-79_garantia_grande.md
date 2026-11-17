# Plan ARX-79 · Garantía de partida ganable (ARX-66) en el mapa grande

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Rama propuesta: `fix/arx-79-garantia-grande`. Aporta a **M13** (batería y veto físico coherentes con la promesa de partida ganable) y **M14** (ruta inexistente y 0 % de batería como casos de borde, no como derrotas sin causa). Parte del lote de medianas (`docs/planes/LOTE_medianas.md`).

## 1. Contexto

QA (17/11, `pedidos/2026-11-17_qa_arx30bc/VUELTA2.md:26`): en `main ab46b4a`, sin eventos, en el mapa grande (40×60) Muy fácil pierde las semillas 8, 9 y 12 (batería 0 con sitios pendientes) y Medio pierde las semillas 1 a 4 (llega al refugio con «sitios 0/4» y la caza sin batería; la prueba que falla en ARX-78 es el mismo síntoma). `_ganable_con_senal` (ARX-30c, reserva de ev3-d56/d59) hereda el estimador. La nota de la tarea añade el bucle de la caza parada (`repro/fracaso9.py`, semilla 6 · nivel 5 · pequeño). ARX-90 (`pedidos/2026-11-17_qa_arx28/ARX-90_diagnostico.md`) explica un segundo mecanismo de pérdida: un sitio pendiente marcado como riesgo por una lectura ruidosa agota las 5 recuperaciones de `SIN_RUTA`.

## 2. Estado actual (comprobado en el código)

- La garantía corre al construir `Partida` con `garantia=True` (`juego/partida.py:308-323`): hasta 59 variantes del mapa (`semilla + 10007·k`) hasta que `_es_ganable` acepte una. Si ninguna pasa, se queda con la última sin aviso (`:320-323`, no hay rama de «no ganable»).
- `_es_ganable` (`:191-216`) prueba todas las permutaciones de sitios y drones con `_plan_con_paradas` (`:173-189`): tramos BFS **sobre el mapa real** (`mascara = tipo == LIBRE`, `:195`), un paso = una unidad de batería, `MARGEN_ENERGIA = 15` al final (`:189`), `MARGEN_CAZA = 10` pasos por dron (`:65`), `factor` solo con estaciones (`:316`, `AMBIENTE_FACTOR_POR_NIVEL`, apagadas).
- Lo que la misión real gasta y el estimador no cuenta: (1) desvíos por el **mapa estimado** (`riesgo ≥ 0,5`, prior 0,05 y falsos positivos del sensor, `integracion.py:124, 258-262`) frente al mapa real; (2) **ambiente**: tormenta y noche cuestan 1,0 y 0,5 de batería extra por paso durante 6 y 8 pasos, con probabilidad 3 % por paso de empezar (`juego/partida.py:38-40, 1044-1052`); en 300 pasos son unos 9 inicios y 50 de batería extra esperada en grande; (3) **caza**: `MARGEN_CAZA` fijo en 10 pasos no escala con el mapa (la diagonal de 40×60 es 60 celdas); (4) **replanteos y recuperaciones** (`_recuperar_sin_ruta`, tope 5, `:548-568`) que gastan pasos sin avanzar.
- Batería inicial `100 − 4·(nivel − 1)` (`:283`), sin escalar con el tamaño; el mapa grande tiene 4 veces el área y el mismo margen.
- Evidencia de magnitud: ARX-58 (nota) midió Muy fácil grande 80 % de éxito con mediana 77 pasos; en pequeño 100 %.

## 3. Propuesta

Hacer que el estimador sea **pesimista en proporción al tamaño y al nivel**, sin tocar la física ni la dificultad decidida (ev3-d43/45/47): el mismo recorrido estimado, multiplicado por un factor de seguridad que cubra ambiente, desvíos y recuperaciones, y un margen de caza proporcional al mapa. Un mapa que no pase se regenera (ya ocurre) y, si ninguna de las 59 variantes pasa, la partida avisa (`_avisar`) en vez de callar. Los valores se **calibran midiendo**: 20 semillas por nivel en grande antes y después, con el mismo arnés de ARX-58.

Decisiones de diseño que tomo (supuestos de simulación, constantes nombradas):
- `FACTOR_SEGURIDAD_GARANTIA(filas, columnas, nivel) = 1 + 0,15·(escala − 1) + 0,05·(nivel − 1)` con `escala = área / (20·30)`; en pequeño vale 1,0 más el término de nivel (no cambia lo medido en ARX-66: Medio 20/20, Hardcore 20/20 salvo que la calibración diga otra cosa), en grande Muy fácil ≈ 1,45.
- `MARGEN_CAZA` pasa a `max(10, diagonal_del_mapa / 3)` celdas por dron.
- La reserva de la señal (`_ganable_con_senal`) usa el mismo factor: queda cubierta sin tocar ev3-d56.

Alternativas descartadas, una línea cada una:
- Subir la batería inicial en grande: cambia la dificultad decidida por el usuario (ficha) y no corrige el estimador.
- Simular la misión completa para validar el mapa: segundos por partida al crearla; el estimador debe seguir siendo instantáneo.
- Quitar el tope de 5 recuperaciones: ARX-90 muestra que no resuelve el bucle.

## 4. Componentes afectados

`juego/partida.py` (`_es_ganable`, `_plan_con_paradas` por el parámetro `factor`, `MARGEN_CAZA`, aviso final del bucle, `_ganable_con_senal`), `juego/tests/test_garantia_grande_arx79.py` (nuevo), `docs/planes/ARX-79_calibracion.md` (medición). Sin cambios en `integracion.py`, `simulador.py` ni API. Frontera: la evaluación congelada (`garantia=False`) no pasa por aquí.

## 5. Tareas

**ARX-79a · Medición base en grande (backend)** — ~1 h con turno pesado (20 semillas × 5 niveles, sin eventos, en 40×60; precedente ARX-58: minutos)
- Archivos: script temporal en la carpeta de la sesión; `docs/planes/ARX-79_calibracion.md` (nuevo).
- Hecho cuando: tabla por nivel con éxito, pasos y causa de la derrota (batería 0 con sitios pendientes, sitios 0/n, caza sin batería, SIN_RUTA) en `main` actual, y la misma tabla en pequeño como control.

**ARX-79b · Factor de seguridad y margen de caza (backend)** — ~2 h — depende de 79a
- Archivos: `juego/partida.py`, `juego/tests/test_garantia_grande_arx79.py`.
- Hecho cuando: las constantes existen y se aplican en `_es_ganable` y en `_ganable_con_senal`; si ninguna variante pasa, `avisos` recibe «Mapa sin garantía de victoria para este nivel y tamaño»; con las semillas 8, 9 y 12 de Muy fácil grande y 1 a 4 de Medio grande la partida gana sin eventos; en pequeño las 20 semillas de Medio y Hardcore de ARX-66 siguen ganando; la generación no tarda más de 2 s en grande (medir).
- Pruebas (5): las semillas de QA ganan; regresión en pequeño (muestra de 5 semillas por nivel); el aviso aparece con un mapa imposible forzado (batería 5); `MARGEN_CAZA` escala; determinismo del mapa elegido por semilla.

**ARX-79c · Bucle de la caza parada (backend)** — ~1 h — independiente de 79b
- Archivos: `juego/partida.py` (`_seguir_caza`, `_cazar_drones`, `:564-669`), prueba con la receta de `repro/fracaso9.py` (semilla 6 · nivel 5 · pequeño, señal + 3 meteoritos).
- Hecho cuando: una caza sin avance durante N pasos termina con aviso y FRACASO con causa, en vez de quedarse parada; la receta reproduce y pasa.

**ARX-79d · Medición final (backend)** — ~0,5 h con turno — tras 79b y 79c
- Repite 79a y anota la diferencia en `ARX-79_calibracion.md`. Criterio: Muy fácil y Fácil grande ≥ 95 % de éxito sin eventos; Medio ≥ 85 %; sin empeorar pequeño.

## 6. Paralelismo

| Frente en curso | Archivos | ¿Comparte? | Veredicto |
|---|---|---|---|
| `feat/arx-33-31-83-motor` | `juego/partida.py`, `integracion.py`, `juego/termico.py`, `api/servidor.py`, `app.js` | **sí: `partida.py`** (zonas distintas: garantía `:160-323` frente a estados, eventos y térmico) | **en fila** detrás de la rama del motor, o la misma rama si el líder prefiere un solo frente de motor |
| `fix/arx-90-percepcion` | `juego/partida.py` (`_actualizar_mapa_percepcion`) | **sí** | **en fila**; ARX-90 va primero (es pequeña y cambia la causa 1 de la sección 2: 79a debe medirse **con** ARX-90 integrado) |
| `feat/arx-45-baselines` | `juego/comparacion.py`, pruebas, `scripts/comparacion_politicas.py` | no | en paralelo |
| Regeneración ev3-d64 | JSON, `TABLA_MODOS`, `scripts/tabla_modos.py` | no (la garantía no actúa con `garantia=False`) | en paralelo |

Conclusión: ARX-79 **va en fila** detrás de ARX-90 y de la rama del motor; 79a puede medirse antes, en cuanto ARX-90 esté en `main`.

## 7. Riesgos y decisiones del usuario

- **Dificultad.** Un factor de seguridad más alto rechaza más mapas y hace las partidas algo más fáciles en grande. No cambia batería ni objetivos (ev3-d43/45/47), pero el Maestro puede querer confirmarlo. **Ficha propuesta ev3-d65** (si el Maestro la pide): evidencia medida = VUELTA2.md:26 (Muy fácil grande pierde 3 de 12, Medio 4 de 4 en semillas 1–4) y ARX-58 (80 % en grande frente a 100 % en pequeño); opciones A) factor de seguridad por tamaño y nivel (M13, M14; ~3,5 h con medición), B) más batería inicial en grande (M13; ~1 h; cambia la dificultad decidida), C) aceptar las pérdidas y documentarlas (0 h; M13 parcial); recomendada A.
- **Tiempo de generación.** Más variantes rechazadas = más llamadas a `_es_ganable` (permutaciones de hasta 6 puntos): medir en 79b; tope 2 s.
- **ARX-90 primero.** Sin su corrección, la medición de 79a mezcla dos causas.

## 8. Verificación (QA)

1. `python -m pytest -q juego/tests/test_garantia_grande_arx79.py juego/tests/test_partida.py`.
2. Las semillas de QA (Muy fácil grande 8, 9, 12; Medio grande 1–4) ganan sin eventos con `TestClient`.
3. `docs/planes/ARX-79_calibracion.md` con las dos tablas y los criterios de 79d cumplidos o el resultado negativo declarado.
4. Pequeño sin regresión: muestra de ARX-66 (Medio 20/20, Hardcore 20/20) con turno.

## Dónde quedé
- 17/11 · Plan completo. Siguiente archivo del lote: `ARX-28cde.md`.
