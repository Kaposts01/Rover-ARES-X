# Lote de medianas · ARX-79, ARX-28c/d/e, ARX-47, ARX-36, ARX-34 — índice, orden y paralelismo

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Planes por tarea: `ARX-79_garantia_grande.md`, `ARX-28cde.md`, `ARX-47_pesos.md`, `ARX-36_vista_auto.md`, `ARX-34_animaciones.md` (todos en `docs/planes/`). Solo lectura; nada versionado por el Planner.

## 1. Aporte a la meta y orden recomendado

| # | Tarea | Aporta a | Por qué en este puesto | Esfuerzo |
|---|---|---|---|---|
| 1 | **ARX-79** garantía en mapa grande | **M13, M14** | Corrige derrotas reales ya medidas (Muy fácil grande 3 de 12 semillas, Medio 4 de 4 en 1–4; VUELTA2.md:26) y el estimador que hereda la señal biológica. Es la única del lote que arregla un fallo del juego, no una vista | ~4,5 h con dos turnos pesados |
| 2 | **ARX-28d + 28e** `/comparacion?escenario=` y selector | **M17, M19** | Hace visible el escenario exigente ya medido (ev3-d55 A); sin ellos, el trabajo de 28a/28b/28f no llega al informe ni a la pantalla | ~2 h |
| 3 | **ARX-47** pesos del fitness en vivo | **M10, M16**, M11 | Único criterio de la dimensión del AG que sigue parcial (M10 «ajustables»); efecto real en el laboratorio y acotado en el juego (ver hallazgo abajo) | ~3,5 h |
| 4 | **ARX-36** vista del automático | **M15, M17** | ev3-d46 A ya está implementada (medianas y replanteos en pantalla); queda la tira de estados por misión y el último replanteo. Aporte real pero pequeño | ~2 h |
| 5 | **ARX-28c** física de la velocidad | M13, M19 (**a M2 nada nuevo**) | El difuso ya altera 20/20 semillas y 380 filas de velocidad; 28c convierte velocidad en consecuencia física. Útil para la defensa («lento = seguro»), no para M2. Ficha ev3-d66 para posponerla | ~2 h + regenerar el JSON exigente |
| 6 | **ARX-34** animaciones | M15 (ya cubierto en su mayor parte) | **Confirmado lo que sospecha el Maestro:** de los seis elementos del título, cinco los hizo ARX-30 (evidencia en `ARX-34_animaciones.md` §2 con archivo:línea); el sexto (rocas móviles) depende de ARX-29, fuera del lote | 0,25 h cierre + 1,5 h bloqueadas |

**Si el tiempo no alcanza, se dejan fuera en este orden:** ARX-34 (se cierra como hecha por ARX-30 y 34b espera a ARX-29), ARX-28c (ficha ev3-d66: posponer), ARX-36b (espera a 31b de todos modos). Las tres primeras del orden (79, 28d/e, 47) son las que mueven criterios M que hoy están parciales.

## 2. Respuesta sobre ARX-28c

A M2 no aporta nada que no esté demostrado: M2 pide que variar el difuso altere «decisión, velocidad o ruta», y la velocidad cambia en 20 de 20 semillas (`docs/TRAZA_DIVERGENCIAS_exigente.csv`, 380 filas). 28c aporta a M13 (un resbalón es un veto físico que responde a la velocidad) y a M19 (la ablación del difuso se compara en éxito, colisiones y batería, no solo en velocidad), y corrige una paradoja del informe: hoy «sin difuso» puede ganar donde el híbrido pierde (semilla 7, ARX-90), porque ir despacio solo cuesta pasos. Detalle y ficha en `ARX-28cde.md` §1 y §7.

## 3. Hallazgo transversal para Docs y el Maestro

En el juego, `Partida` envuelve el AG con `_ag_con_todos_los_sitios` (`juego/partida.py:218-275`): el AG corre, pero el orden de visita es la permutación más corta por el mapa que la garantía validó (`:264-275`). Con 6 sitios o menos, los pesos del fitness **no cambian la ruta del juego**; cambian el laboratorio (`/ag`) y los empates. Afecta a cómo se enuncian M2 y M10 en el informe y explica la cercanía entre «sin AG» e «híbrido». No se resuelve en este lote (ARX-66 y N12 son decisiones tomadas); ARX-47 lo declara en la pantalla y el informe debe decirlo.

## 4. Paralelismo, por lista de archivos

Frentes en curso y sus archivos: **motor** `feat/arx-33-31-83-motor` (`partida.py`, `integracion.py`, `juego/termico.py`, `servidor.py` en 33b/31b/83b, `app.js` en 33c/83c, `partida.py` en 89b); **45** `feat/arx-45-baselines` (`juego/comparacion.py`, su prueba, `scripts/comparacion_politicas.py`); **90** `fix/arx-90-percepcion` (`partida.py`); **regeneración ev3-d64** (`docs/COMPARACION_POLITICAS*.json`, `TABLA_MODOS`, `scripts/tabla_modos.py`).

| Tarea del lote | Archivos | Motor | 45 | 90 | Regeneración | Entre sí | Veredicto |
|---|---|---|---|---|---|---|---|
| ARX-79 | `partida.py` (garantía), pruebas, `ARX-79_calibracion.md` | **sí** | no | **sí** | no | con 47b y 28c (`partida.py`) | **en fila**: tras 90 y la rama del motor; 79a (medición) en cuanto 90 esté en `main` |
| ARX-28d | `servidor.py`, `test_datos_graficos.py` | **sí** (`servidor.py`) | no | no | lee los JSON | con 47a (`servidor.py`) | **en fila** con el motor por `servidor.py`; 20 líneas: coordinar quién va primero |
| ARX-28e | `laboratorio.js`, `index.html` | no | no | no | no | con 47c (`laboratorio.js`) | **puede abrirse ahora** |
| ARX-28c | `partida.py`, `comparacion.py`, pruebas | **sí** | **sí** | **sí** | cambia el JSON exigente | con 79 y 47b | **en fila** al final: tras 45, 90, motor; antes de regenerar el exigente |
| ARX-47a | `servidor.py` | **sí** | no | no | no | con 28d | en fila con el motor |
| ARX-47b | `partida.py` | **sí** | no | **sí** | no (regresión con pesos por defecto) | con 79, 28c | en fila |
| ARX-47c | `laboratorio.js` | no | no | no | no | con 28e | **puede abrirse ahora** contra el contrato de 47a |
| ARX-36a | `app.js`, `index.html` | **sí** (`app.js`, zonas distintas) | no | no | no | con 28e/47c (`index.html`) | **en fila** detrás de 33c/83c por regla; o misma rama de interfaz |
| ARX-36b | `app.js` | sí | no | no | no | — | tras 31b |
| ARX-34a | docs | no | no | no | no | — | ahora (Docs) |
| ARX-34b | `moviles.js`, `efectos.js` | no | no | no | no | — | bloqueada por ARX-29 |

**Pares de frentes propuestos** (dos a la vez, sin archivos en común):
1. Ahora: **motor (33b/31b/83b/89b)** ‖ **interfaz: 28e + 47c** (`laboratorio.js`, `index.html`); 34a lo hace Docs.
2. Al integrarse 90 y el motor: **ARX-79** (motor) ‖ **28d + 47a** (`servidor.py`; ambas en una rama corta de API) → después **36a** (interfaz) ‖ **47b** (motor).
3. Al final: **28c** (si ev3-d66 dice hacerla) → regeneración ev3-d64 del JSON exigente.

La regeneración de cifras (ev3-d64) va **después** de 45, 90 y 28c, porque las tres cambian resultados; 28d puede servir los JSON viejos y QA repite su prueba tras regenerar.

## 5. Fichas propuestas (evidencia medida, criterios M por opción, costo)

- **ev3-d65 · ARX-79: ¿factor de seguridad por tamaño y nivel en la garantía?** Evidencia: VUELTA2.md:26 (Muy fácil grande pierde 8, 9 y 12 de 12 semillas; Medio grande pierde 1–4), ARX-58 (80 % en grande frente a 100 % en pequeño), causas con archivo:línea en `ARX-79_garantia_grande.md` §2. A) factor de seguridad y margen de caza proporcional, calibrados con 20 semillas por nivel (M13, M14; ~4,5 h con dos turnos) **recomendada**; B) más batería inicial en grande (M13; ~1 h; cambia la dificultad decidida en ev3-d43/45/47); C) aceptar y documentar (0 h; M13 parcial). Sin duda entre opciones.
- **ev3-d66 · ARX-28c: ¿ahora, al final del lote, o cerrar?** Evidencia: `TRAZA_DIVERGENCIAS_exigente.csv` (20/20; 380 filas solo de velocidad), ARX-90 (semilla 7). A) posponer al final del lote (M13, M19 cuando llegue; 0 h ahora) **recomendada**; B) hacerla ahora en fila (~2 h + turno para regenerar el exigente); C) cerrar y declarar la limitación (0 h; revierte ev3-d54 A). Duda declarada entre A y B: si el Maestro quiere evidencia de «lento = seguro» para la defensa, B.

Ninguna otra tarea del lote necesita ficha.

## Dónde quedé
- 17/11 · Lote completo: 5 planes + este índice. Pendiente solo que el Orquestador cargue subtareas y fichas, y que `Lider_Rover` versione los archivos.
