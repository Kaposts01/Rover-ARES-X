# Plan ARX-47 · Pesos del fitness modificables en vivo (§17 del PDF)

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Rama propuesta: `feat/arx-47-pesos`. Aporta a **M10** (pesos justificados y **ajustables**) y a **M16** (ajustar parámetros con efecto); de paso a M11 (los tres candidatos cambian con los pesos). Parte del lote (`LOTE_medianas.md`).

## 1. Contexto

M10 pide pesos «justificados y ajustables». Hoy son constantes del módulo y la pantalla solo los muestra. El PDF §17 pide poder modificarlos en vivo.

## 2. Estado actual (comprobado en el código)

- `PESOS_POR_DEFECTO` (`genetico.py:18-19`): ciencia 1,0, distancia 0,3, energía 0,2, riesgo 0,8, tiempo 0,1; el constructor acepta `pesos` (`:103`) y el desglose los aplica (`:176-178`).
- `GET /ag` (`api/servidor.py:808-846`) construye un `GeneticPlanner` **sin pesos** (`:826-828`) y los devuelve en `parametros.pesos` (`:831`); la pantalla los pinta de solo lectura (`laboratorio.js:140, 223-234`).
- La misión construye su AG también sin pesos (`integracion.py:142-144`).
- **Hallazgo que acota la tarea:** en el juego, `Partida` envuelve `_optimizar_ag` con `_ag_con_todos_los_sitios` (`juego/partida.py:218-275`): el AG corre (`ruta_ag`, `:225`), pero el orden de visita que usa la misión es la **permutación más corta por el mapa** (`:264-275`), validada por la garantía. Con 6 sitios o menos, los pesos del fitness **no cambian la ruta del juego**; solo cambian lo que muestra `/ag`. Esto también explica por qué «sin AG» (vecino más cercano) y «híbrido» se parecen en el arnés. Es una contradicción con M2 y M10 tal como se enuncian; la señalo para Docs y para el Maestro, no la resuelvo aquí.

## 3. Propuesta

Pesos ajustables en dos lugares, declarados: (1) en `/ag` como parámetros de consulta (`?w_ciencia=…&w_riesgo=…`), que recalculan candidatos, historial y mejor ruta del laboratorio y quedan guardados en la sesión; (2) en la partida, `Partida.pesos_ag` que el envoltorio pasa al `GeneticPlanner` **y que decide el orden de visita solo cuando varias permutaciones empatan en largo o cuando hay más de 6 sitios** (hoy el AG ya es el único criterio con más de 6). Así el ajuste tiene efecto real y medible en el laboratorio y un efecto acotado y honesto en el juego, sin tocar la garantía.

Alternativas descartadas, una línea cada una:
- Que el AG vuelva a decidir el orden en el juego: deshace ARX-66 (garantía) y la decisión N12 de la caza; cambio de regla, no de parámetro.
- Pesos solo en la pantalla sin pasar al motor: sería política oculta.
- Un endpoint `POST /ag/pesos`: una sesión ya guarda estado; basta con parámetros de consulta y persistencia en `Sesion`.

## 4. Componentes afectados

`api/servidor.py` (`/ag`, `Sesion.pesos_ag`, `/estado` expone `pesos_ag`), `juego/partida.py` (`pesos_ag`, envoltorio `_ag_con_todos_los_sitios`), `genetico.py` solo lectura, `api/static/laboratorio.js` (cinco deslizadores y «Aplicar»), `api/tests/test_datos_graficos.py`, `juego/tests/test_pesos_ag_arx47.py` (nuevo). Docs: contrato §1 (`/ag` con pesos), MATRIZ §4, INFORME (justificación de los pesos por defecto).

## 5. Tareas

**ARX-47a · Pesos en `/ag` y en la sesión (backend)** — ~1 h — M10, M11
- Hecho cuando: `GET /ag?w_ciencia=2&w_riesgo=0.2` devuelve `parametros.pesos` con esos valores y candidatos distintos a los de por defecto en al menos una semilla de prueba; valores fuera de [0, 5] → 400; los pesos quedan en `Sesion` y se reutilizan en llamadas siguientes; la caché de `/ag` incluye los pesos en la clave.
- Pruebas (3).

**ARX-47b · Pesos en la partida con efecto declarado (backend)** — ~1,5 h — M10, M16 — comparte `partida.py` con la rama del motor
- Hecho cuando: `Partida(pesos_ag=…)` pasa los pesos al `GeneticPlanner` del envoltorio; con dos permutaciones de igual largo, el orden elegido es el de mejor fitness con esos pesos (prueba construida); con pesos por defecto, 20 semillas del congelado producen las mismas filas (regresión).
- Pruebas (3).

**ARX-47c · Deslizadores en el laboratorio del AG (frontend)** — ~1 h — M16 — depende de 47a
- Hecho cuando: cinco deslizadores con el valor numérico, botón «Aplicar» que recarga `/ag` con los pesos, y «Por defecto»; la tabla de desglose y la curva de fitness cambian; el texto explica que en el juego los pesos solo desempatan órdenes de igual largo (la frase sale del motor, `parametros.nota`).
- Pruebas: en Chrome, mover «riesgo» a 2,0 cambia los candidatos; consola limpia.

## 6. Paralelismo

| Frente | Archivos | ¿Comparte? | Veredicto |
|---|---|---|---|
| `feat/arx-33-31-83-motor` | `partida.py`, `servidor.py`, `app.js` | **sí** (47a `servidor.py`, 47b `partida.py`) | **en fila** detrás de la rama del motor; 47c (`laboratorio.js`) puede ir antes contra el contrato |
| `feat/arx-45-baselines` | `comparacion.py`, scripts | no | en paralelo |
| `fix/arx-90-percepcion` | `partida.py` | sí (47b) | en fila |
| Regeneración ev3-d64 | JSON, TABLA | no (pesos por defecto no cambian cifras; prueba de regresión) | en paralelo |

## 7. Riesgos y decisiones del usuario

- **Contradicción M2/M10 frente a ARX-66.** No propongo ficha: ARX-66 y N12 son decisiones tomadas y este plan no las toca; pero el informe debe decir que en el juego el AG optimiza dentro de la garantía (orden más corto que visita todo) y que los pesos deciden el laboratorio y los empates. Si el Maestro quiere devolverle al AG la decisión del orden, es una ficha aparte con evidencia de ARX-66 (Difícil 19/20, Medio 20/20) y costo de rehacer la garantía (~1 día).
- **Caché de `/ag`.** La clave debe incluir los pesos o la pantalla mostrará resultados viejos.
- **Rangos.** Pesos negativos invierten el sentido del fitness; se limitan a [0, 5].

## 8. Verificación (QA)

1. `python -m pytest -q api/tests/test_datos_graficos.py -k ag juego/tests/test_pesos_ag_arx47.py`.
2. Instancia de prueba: `/ag` con y sin pesos devuelve candidatos distintos; `/estado.pesos_ag` refleja el último ajuste.
3. Chrome: deslizadores, «Aplicar», «Por defecto»; consola limpia.
4. Regresión del congelado con pesos por defecto (3 semillas).

## Dónde quedé
- 17/11 · Plan completo. Siguiente: `ARX-36_vista_auto.md`.
