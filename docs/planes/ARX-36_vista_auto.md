# Plan ARX-36 · Vista del automático continuo e indicador de estados

Planner: `Esp_Planner`, 2026-11-17. Base `main` en `029e5cd`. Rama propuesta: `feat/arx-36-vista-auto` (frontend). Aporta a **M15** (estado visible) y **M17** (vista del automático y explicación por decisión). Parte del lote (`LOTE_medianas.md`).

## 1. Contexto

La nota de la tarea dice: «Indicador con los estados del motor más SIN_RUTA; faltan los estados de ARX-33». Hoy ARX-33 está en la rama del motor (`feat/arx-33-31-83-motor`), con `estado_visible` completo y la subtarea 33c (CONFIGURACION en la interfaz) todavía pendiente ahí.

## 2. Estado actual (comprobado en el código)

- Indicador: `api/static/app.js:1205-1218` ya tiene EXPLORACION, ALERTA, REPLANIFICACION, REFUGIO, MODO_SEGURO, SIN_RUTA, EXITO y FRACASO con etiqueta, icono, color y pulso; falta CONFIGURACION (lo agrega 33c). Modo demo `?demo=estados` (`:1230`).
- Automático continuo: `cadenaAutomatica` (`:1812-1832`) con pasos, batería final y replanteos por misión; el bloque «escenarios-caja» ya muestra mediana de pasos, mediana de batería y total de replanteos (`:1452-1468`): **ev3-d46 A está implementada**.
- Lo que no existe: (1) la cadena no registra **qué estados** atravesó cada misión ni cuántos pasos estuvo en cada uno; (2) no muestra el **último replanteo** y su motivo (lo expondrá 31b en `/estado.ultimo_replanteo`); (3) no hay una **línea de explicación por paso** (ARX-88, aparte).

## 3. Propuesta

Completar la vista del automático con lo que el motor ya da o dará: una **tira de estados por misión** (secuencia compacta de los estados de `/estado.estado` con el número de pasos en cada tramo, p. ej. «EXPLORACIÓN 23 · ALERTA 4 · REPLANIFICACIÓN 2 · REFUGIO 9 · ÉXITO») y, en el bloque de la cadena, el **último replanteo** con motivo. Todo se deriva de lo que la interfaz ya recibe en cada paso: no hay endpoint nuevo.

Alternativas descartadas, una línea cada una:
- Un endpoint `/cadena` en el motor: ev3-d46 A decidió calcular en la interfaz.
- Reemplazar el indicador por una máquina de estados dibujada: más diseño que información; la tira por misión da lo mismo en menos espacio.

## 4. Componentes afectados

`api/static/app.js` (`nuevaCadena`, registro de estados por paso, `textoCadena`, bloque de la cadena), `api/static/index.html` (contenedor de la tira), `api/static/App.css` o estilos en línea según `DESIGN.md`. Sin motor. Docs: `docs/SPEC_MVP_3D.md` o la sección de interfaz que corresponda.

## 5. Tareas

**ARX-36a · Tira de estados por misión en la cadena (frontend)** — ~1,5 h — M15, M17
- Hecho cuando: cada misión terminada de la cadena guarda la secuencia de estados visibles con sus pasos; el bloque muestra la tira de la misión en curso y la de las terminadas (plegadas); con `?demo=estados` la tira recorre los ocho estados; los colores son los del indicador.
- Pruebas: en Chrome, cadena de 3 misiones en Muy fácil; la tira coincide con el indicador paso a paso; consola limpia.

**ARX-36b · Último replanteo y motivo (frontend)** — ~0,5 h — M17 — depende de 31b (`/estado.ultimo_replanteo`)
- Hecho cuando: el bloque muestra «último replanteo: paso N · REPLAN-AG-SISMO» cuando existe, y nada si es `null`.
- Pruebas: disparar un sismo con el selector de eventos; el texto aparece.

Orden: 36a ahora; 36b cuando 31b esté en `main`.

## 6. Paralelismo

| Frente | Archivos | ¿Comparte? | Veredicto |
|---|---|---|---|
| `feat/arx-33-31-83-motor` (33c y 83c tocan `app.js`) | `app.js` | **sí** | 36a toca zonas distintas (`:1452-1468`, `:1812-1832`) frente a 33c (`:1205-1218`) y 83c (`:1386-1444`): **puede correr en paralelo si el líder acepta resolver el merge de `app.js`**; si no, en fila detrás de 33c/83c. Regla del protocolo: comparten archivo → **en fila** |
| ARX-88 (explicación por paso, `app.js`) | `app.js` | sí | en fila; conviene que 88 vaya después de 36a y reutilice la tira |
| Resto del lote y `feat/arx-45`, `fix/arx-90`, regeneración | motor y datos | no | en paralelo |

Conclusión: **en fila** detrás de 33c y 83c por `app.js`, salvo que el líder decida llevar 33c, 83c y 36a en la misma rama de interfaz.

## 7. Riesgos y decisiones del usuario

Ninguna ficha: es presentación de datos que ya existen. Riesgo: la cadena automática salta cada 3 s; el registro de estados debe hacerse en el mismo `refrescar` que ya cuenta pasos, no con un temporizador aparte.

## 8. Verificación (QA)

Prueba en Chrome: cadena de 3 misiones, tira por misión visible y coherente con el indicador, `?demo=estados` recorre los ocho, consola limpia, sin regresión del bloque de medianas (ev3-d46 A).

## Dónde quedé
- 17/11 · Plan completo. Siguiente: `ARX-34_animaciones.md`.
