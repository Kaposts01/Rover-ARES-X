# Plan ARX-28c, 28d y 28e · Física de la velocidad, `/comparacion?escenario=` y selector de escenario

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Rama: `feat/arx-28-ablaciones` para 28d y 28e (continuación del frente); 28c según la sección 7. Decisiones: ev3-d54 A (rápido en pendiente puede resbalar, **solo** en el escenario exigente), ev3-d55 A (el escenario exigente se agrega junto al congelado, con selector). Parte del lote (`LOTE_medianas.md`).

## 1. Contexto y pregunta del Orquestador sobre 28c

Medido hoy en `docs/TRAZA_DIVERGENCIAS_exigente.csv` (rama `feat/arx-28-ablaciones`): apagar el difuso altera decisión, velocidad o ruta en **20 de 20** semillas, y **380 filas cambian solo la velocidad**, que hoy no tiene efecto físico (`paso_fisico` con costo fijo 1,0, `integracion.py:214`). Pregunta: ¿qué aporta 28c a M2 que no esté ya demostrado?

**Respuesta:** a **M2 nada nuevo**. M2 pide que variar el difuso altere «una decisión, velocidad o ruta»; la velocidad ya cambia en 20/20 y hay 1 340 filas de traza que lo prueban. Lo que 28c aporta es a **M13** (la física reacciona a la velocidad: un resbalón es un veto físico) y a **M19** (la ablación del difuso se compara en resultados: éxito, colisiones, batería, no solo en velocidad). Y una cosa más, de informe: hoy «sin difuso» puede salir **mejor** que el híbrido (semilla 7, ARX-90), porque ir despacio solo cuesta pasos; con 28c ir despacio compra seguridad y la comparación deja de penalizar al controlador por hacer su trabajo. Es un aporte real pero menor que el de 28d y 28e (que hacen visible el escenario exigente) y que el de ARX-79. Por eso en el lote 28c va al final (ver `LOTE_medianas.md` §1) y se propone una ficha para que el Maestro confirme si se posterga.

## 2. Estado actual

- `juego/comparacion.py` (rama 28): `ESCENARIOS` con `congelado` y `exigente` (y `exigente_rna` si 28f lo dejó), `partida_variante(semilla, variante, escenario)`, `comparar(semillas, escenario)`; JSON `docs/COMPARACION_POLITICAS.json` y `_exigente.json`.
- `GET /comparacion?semillas=` (`api/servidor.py:1033-1050`, `main`): sirve el JSON para 20 semillas y calcula para otros valores; caché por número de semillas; sin parámetro de escenario.
- Panel de comparación: `api/static/laboratorio.js:612-640` (`cargarPoliticas` llama `/comparacion` sin parámetros, `pintarPoliticas`, barras); bloque en `index.html:885`.
- Velocidad: solo en bitácora, estado ALERTA y `D-DIFUSO-LENTO` (`integracion.py:51-52, 203`); la inclinación entra al difuso como `min(45, |gradiente|·GRADOS_POR_GRADIENTE)` (`:180`) y existe por celda (`mundo.elevacion`).

## 3. Propuesta

- **28d (backend):** `GET /comparacion?escenario=congelado|exigente|…&semillas=` valida contra `ESCENARIOS` (400 legible), sirve `docs/COMPARACION_POLITICAS_<escenario>.json` cuando existe para 20 semillas, calcula si no, caché por `(escenario, semillas)`, respuesta con `"escenario"`. Sin parámetro, idéntico a hoy.
- **28e (frontend):** selector «Escenario: congelado | exigente» junto al panel; `cargarPoliticas(escenario)`; título de la tabla con el escenario; nota declarativa del escenario (la que trae el JSON) bajo la tabla.
- **28c (backend, ev3-d54 A):** bandera `fisica_velocidad=False` en `Partida`; el escenario exigente la enciende en `partida_variante`. Con la bandera, tras cada `m.paso_mision()` en `avanzar_ia`, si la última fila fue `avanzar` con velocidad `v` y la inclinación de la celda alcanzada supera `INCLINACION_RESBALON` (p. ej. 20°), hay resbalón con probabilidad `P_RESBALON · v` (generador propio por semilla): el rover vuelve a la celda anterior, gasta `COSTO_RESBALON` de batería y la bitácora anota `D-RESBALON`. Despacio (v < 0,3) no resbala. El congelado no enciende la bandera: cifras intactas.

Alternativas descartadas, una línea cada una:
- 28c en `Mision`: congelada.
- Consumo de batería proporcional a la velocidad (ev3-d54 B): descartada por la ficha.
- Un endpoint nuevo por escenario: duplica caché y contrato; basta el parámetro.

## 4. Componentes afectados

28d: `api/servidor.py`, `api/tests/test_datos_graficos.py`. 28e: `api/static/laboratorio.js`, `api/static/index.html`. 28c: `juego/partida.py`, `juego/comparacion.py`, `juego/tests/test_fisica_velocidad.py` (nuevo). Docs: contrato §7 (parámetro `escenario`), INFORME §4, MATRIZ RF-14/CA-08.

## 5. Tareas

**ARX-28d · `/comparacion?escenario=` (backend)** — ~1 h — M17, M19
- Hecho cuando: sin parámetro responde lo de hoy; `escenario=exigente&semillas=20` sirve el JSON exigente; `escenario=otro` → 400; `semillas=3&escenario=exigente` calcula y trae las cuatro variantes y `"escenario"`; la caché distingue escenarios.
- Pruebas (4) en `api/tests/test_datos_graficos.py`.

**ARX-28e · Selector de escenario (frontend)** — ~1 h — M17 — depende de 28d
- Hecho cuando: el selector cambia la consulta y la tabla; el congelado no cambia sus cifras; sin JSON del escenario, se muestra el aviso del motor y no hay error en consola; el texto declarativo del escenario aparece.
- Pruebas: en Chrome, alternar el selector; consola limpia.

**ARX-28c · Resbalón por velocidad en pendiente (backend)** — ~2 h — M13, M19 — **bloqueada hasta la ficha ev3-d66 de la sección 7**
- Hecho cuando: bandera apagada por defecto; con `fisica_velocidad=True` y velocidad forzada alta (`intervencion_difuso = 1,0`) en una celda con pendiente, aparece al menos un `D-RESBALON` en 50 pasos de la semilla 1 del exigente y ninguno con velocidad 0,2; `comparar(range(1, 4))` del congelado no cambia; `sin_difuso` (velocidad fija 0,5) y `hibrido` difieren en colisiones, batería o éxito en el exigente de 20 semillas (se informa el conteo, sin criterio de éxito propio: 28c no es una medición, es una mecánica).
- Pruebas (4).

## 6. Paralelismo

| Frente | Archivos | 28d | 28e | 28c |
|---|---|---|---|---|
| `feat/arx-33-31-83-motor` (faltan 33b, 31b, 83b en `servidor.py`; 33c, 83c en `app.js`; 89b en `partida.py`) | `partida.py`, `integracion.py`, `termico.py`, `servidor.py`, `app.js` | **comparte `servidor.py`** → en fila, o 28d primero y la rama del motor trae `main` | no comparte (`laboratorio.js`, `index.html`) → en paralelo | **comparte `partida.py`** → en fila |
| `feat/arx-45-baselines` | `juego/comparacion.py`, su prueba, `scripts/comparacion_politicas.py` | no | no | **comparte `comparacion.py`** → en fila tras 45 |
| `fix/arx-90-percepcion` | `partida.py` | no | no | comparte → en fila |
| Regeneración ev3-d64 | `COMPARACION_POLITICAS*.json`, `TABLA_MODOS`, `scripts/tabla_modos.py` | 28d solo lee los JSON: en paralelo, pero QA de 28d se repite tras regenerar | no | 28c cambia resultados del exigente → **regenerar el JSON exigente después de 28c**, no antes |

Conclusión: **28e puede abrirse ahora** como frente de interfaz; **28d en fila** con la rama del motor por `servidor.py` (coordinar quién va primero; es un cambio de 20 líneas); **28c en fila** detrás de 45, 90, la rama del motor y la regeneración de cifras.

## 7. Riesgos y decisiones del usuario

- **Ficha propuesta ev3-d66 · ¿Hacemos ARX-28c ahora, al final del lote o la cerramos?** Evidencia medida: `TRAZA_DIVERGENCIAS_exigente.csv` (20/20 semillas con cambios al apagar el difuso; 380 filas solo de velocidad); ARX-90 (semilla 7: sin difuso gana y el híbrido pierde por paradas). Opciones: **A) posponer al final del lote** (M13, M19 cuando llegue; 0 h ahora; recomendada: su aporte a M2 ya está demostrado y no bloquea nada), B) hacerla ahora en fila (M13, M19; ~2 h más regenerar el JSON exigente con turno), C) cerrarla y declarar en el informe que la velocidad no tiene efecto físico (0 h; M13 queda con esa limitación y ev3-d54 A se revierte). Recomendada A. Duda declarada: entre A y B solo cambia el orden; si el Maestro quiere evidencia de «lento = seguro» para la defensa, B.
- **Regeneración de cifras.** 28c mueve las cifras del exigente; debe ir antes de la regeneración final o forzar una segunda.
- **Semilla 7.** Con 28c, el híbrido podría ganar o perder por otra causa; ARX-90 corrige la raíz, 28c no la tapa.

## 8. Verificación (QA)

1. `python -m pytest -q api/tests/test_datos_graficos.py -k comparacion` (28d); `juego/tests/test_fisica_velocidad.py` (28c).
2. Instancia de prueba (puerto ≠ 8765): `/comparacion` sin parámetro idéntico a `docs/COMPARACION_POLITICAS.json`; `?escenario=exigente` con `"escenario": "exigente"`; `?escenario=otro` → 400.
3. Chrome: selector alterna las tablas; consola limpia; cifras del congelado iguales a las del archivo.
4. 28c: `D-RESBALON` presente en la bitácora del exigente y ausente en el congelado.

## Dónde quedé
- 17/11 · Plan completo. Siguiente: `ARX-47_pesos.md`.
