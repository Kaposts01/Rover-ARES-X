# Plan ARX-34 · Animaciones de móviles, meteoritos, polvo, sismo, interferencia y señal biológica

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Rama propuesta: `feat/arx-34-animaciones` (frontend), **solo después de ARX-29**. Aporta a **M15** únicamente (eventos visibles). Parte del lote (`LOTE_medianas.md`).

## 1. Contexto

La nota de la tarea (14/11) dice: «Meteorito con caída, polvo y zona de riesgo visto en Chrome; faltan sismo, conectividad, señal biológica y obstáculos móviles». El Maestro sospecha que es la tarea de menor aporte del lote.

## 2. Estado actual (comprobado en el código): la nota está desactualizada

- Meteorito: caída, estela, polvo y zona 3×3 (`api/static/moviles.js:41-109`). Verificado en Chrome (ronda 14 y 15).
- Sismo: temblor de cámara (`efectos.js:118-135`, aplicado en `app.js:2598`) y grietas pintadas desde el evento (ARX-30d, PR #1).
- Baja conectividad: interferencia del HUD encendida por el evento y apagada por `/estado.enlace` (`efectos.js:159-176`, `app.js:1598-1600`; ARX-30d).
- Señal biológica: anillo pulsante y etiqueta «anomalía, no confirma vida», quitada al visitarla (`efectos.js:178-222`; ARX-30d).
- Obstáculos móviles: la roca animada ya existe en la interfaz (`moviles.js:26-39, 160`), pero el motor manda `obstaculos_moviles: []` (`api/servidor.py`, `/moviles`): **depende de ARX-29**, que no está en este lote.

De los seis elementos del título, **cinco están hechos** por ARX-30 y el sexto espera al motor. Lo que queda de ARX-34 es pulido visual: polvo al pisar una grieta, rastro de la roca móvil, y transiciones.

## 3. Propuesta

Reducir ARX-34 a lo que falta de verdad y encadenarla a ARX-29: (1) cerrar la tarea actual como «hecha por ARX-30 salvo móviles», con evidencia de QA de ARX-30 (`pedidos/2026-11-17_qa_arx30/INFORME.md`); (2) una subtarea de pulido cuando ARX-29 entregue rocas reales. **Se confirma la sospecha del Maestro**: es la de menor aporte (solo M15, ya cubierto en su mayor parte) y la única bloqueada por una tarea externa al lote.

Alternativas descartadas, una línea cada una:
- Animar rocas con datos de prueba (`adaptador.js` `PRUEBA.moviles`): sería mostrar algo que el motor no produce; la regla del adaptador es «el motor decide cuándo ocurren».
- Hacer ARX-29 dentro de este lote: es una mediana de motor (`partida.py`, `servidor.py`, `moviles.js`) que compite por los mismos archivos que la rama del motor; va en la cola (puesto 23 de `META_brechas.md`).

## 4. Componentes afectados

Solo `api/static/moviles.js` y `efectos.js` (pulido); `docs/tareas_sprints.json` lo cierra el Orquestador con la evidencia.

## 5. Tareas

**ARX-34a · Cierre documental (Docs)** — ~0,25 h — M15
- Hecho cuando: la nota de ARX-34 en el árbol dice qué cubrió ARX-30 (con commits y QA) y qué queda; MATRIZ §8 (Panel A) actualizada.

**ARX-34b · Pulido de móviles reales (frontend)** — ~1,5 h — M15 — **bloqueada por ARX-29**
- Hecho cuando: las rocas de `/moviles.obstaculos_moviles` se mueven con interpolación entre pasos, dejan rastro de polvo breve y no rompen el ciclo si una viene mal (regla E5); el meteorito y la grieta conservan su aspecto.
- Pruebas: Chrome con una partida que tenga obstáculos móviles; consola limpia; FPS sin caída apreciable (referencia ARX-43: 120 FPS).

## 6. Paralelismo

| Frente | Archivos | ¿Comparte? | Veredicto |
|---|---|---|---|
| `feat/arx-33-31-83-motor` (`app.js`) | `app.js` | no (`moviles.js`, `efectos.js`) | en paralelo, pero sin contenido hasta ARX-29 |
| ARX-29 (futura, `partida.py`, `servidor.py`, `moviles.js`) | `moviles.js` | **sí** | 34b **en fila** detrás de 29 |
| Resto del lote, `feat/arx-45`, `fix/arx-90`, regeneración | — | no | — |

## 7. Riesgos y decisiones del usuario

Ninguna ficha. Riesgo: ninguno de producto; el único es seguir contando ARX-34 como pendiente cuando ya se hizo.

## 8. Verificación (QA)

34a: la nota y la matriz coinciden con los commits de ARX-30 (PR #1 `2a6bfdd`, PR #2 `029e5cd`) y con `pedidos/2026-11-17_qa_arx30/INFORME.md`. 34b: Chrome, cuando exista ARX-29.

## Dónde quedé
- 17/11 · Plan completo. Siguiente: índice `LOTE_medianas.md`.
