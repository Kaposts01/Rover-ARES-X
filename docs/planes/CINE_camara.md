# CINE: director de cámara y postproceso, plan de adaptación (diseño, sin código)

Rama `feat/cine-camara` (desde main b27b6c1). Origen: el módulo del director de cámara del ejemplo (220 líneas) y el inventario del ejemplo §2.1. Mismo patrón que `VIAJE_planetas.md` e `INTRO_sistema_solar.md`: módulos ES en `api/static/`, three r160 vendoreado, sin CDN, `import()` perezoso, `try/catch`, probado con node.

## 1. Qué hace el director del ejemplo
- **Director** (`crearDirector(THREE, camara, controles)`): al activarse guarda `controles.enabled`, deshabilita OrbitControls y toma la cámara. Alterna **6 tomas** de 6 a 10 s (duración con `Math.random`): paneo orbital lento, primer plano de tres cuartos, rasante bajo, general alto (altura según tamaño del mapa), travelling lateral y seguimiento desde atrás. Todas se calculan relativas al objetivo (posición y rumbo del rover) y evitan entrar bajo el suelo (`alturaSuelo`).
- **Cortes suaves**: la cámara se acerca a la posición destino con amortiguación exponencial (independiente del FPS), la mirada también; no hay salto al cambiar de toma.
- **Momentos dramáticos** (`momento(tipo, pos)`): barranco vetado, meteorito, despegue, erupción, géiser y éxito. Fijan un plano de 3,2 s sobre el punto del evento y activan **cámara lenta** (`escalaTiempo()`: baja a 0,25 y vuelve en ~2,5 s). El mundo del ejemplo multiplica su `dt` por esa escala.
- Al desactivar: vacía la inercia de OrbitControls, copia la pose de cine y devuelve el control sin salto.
- **Postproceso** (`crearPostpro`): EffectComposer con RenderPass, BokehPass (profundidad de campo), UnrealBloomPass, un ShaderPass de gradación por planeta (tinte, contraste, bruma, viñeta) y OutputPass. Degrada a `renderer.render` si no carga o si se apaga.

## 2. Adaptación módulo por módulo
Dos archivos puros y probados, uno con THREE, uno de postproceso, uno de interfaz.

**`cine_datos.js`** (puro, sin DOM ni THREE; admite `Vector3`-like `{x,y,z}`):
- `TOMAS` (6 descriptores: desplazamiento en ejes locales `frente/derecha/altura`), `duracionToma(n)` **determinista** (6, 7, 8, 9, 10 s en ciclo; sin `Math.random`, para que las capturas de evidencia se repitan).
- `destinoToma(toma, objetivo, rumbo, t, sueloEn, nCeldas)` devuelve `{pos, mira}`; `limitarSobreSuelo(pos, sueloEn)`.
- `mezcla(dt, k)` (amortiguación exponencial), `escalaTiempoCine(dt, estado)` solo para la **cámara**, no para el motor (§5).
- `debeActuar({activado, reducido, enPartida, intro, viaje, pausa})`, `modoCine(reducido)` devuelve `automatico` | `estatico`.
- `evaluarFps(muestras)` (mediana y p5), `decidirPostproceso({fpsCon, fpsSin, umbral})` devuelve `mantener` | `apagar`.
- Eventos dramáticos: solo los que **ya trae** el estado de la API (`/estado`, campo de eventos); el mapa tipo a plano vive aquí, sin tocar el motor.

**`cine3d.js`** (dibujo, recibe `THREE`): `crearDirector({THREE, camara, controles, sueloEn})` devuelve `{activar(v), actualizar(dt, info), momento(tipo, pos), activo, dispose()}`. Misma lógica que el ejemplo, pero (a) sin `Math.random`, (b) **no escribe en el motor ni en el mundo**: solo mueve `camara` y lee `controles`, (c) `dispose()` restaura `controles.enabled` y `enableDamping`.

**`cine_post.js`** (dibujo, recibe `THREE` y las clases cargadas con `import()`): `crearPostproceso({THREE, renderer, clases})` devuelve `{render(escena, camara), activo, setActivo(v), ajustar(w,h), medir(), dispose()}`. Bloom y bokeh con valores moderados (bloom 0,45; bokeh apagado por defecto aunque el interruptor esté encendido). Gradación por planeta: **se omite en v1** (el ejemplo tiene tintes por cuerpo; aquí el cambio de aspecto del planeta ya lo da `PALETAS_PLANETA`; evita un segundo criterio de color). Se conserva la viñeta ligera.

**`cine_ui.js`** (DOM): `crearPanelCine(contenedor)` con casilla «Postproceso (bloom y bokeh)», botón «Cámara de cine» y lectura de FPS. Todo con `textContent`. Clases `cn-*` en el `<style>` de `index.html`.

**Integración en `app.js` / `index.html`** (los únicos existentes que se tocan):
1. **Vistas.** Conducción manual: el director no actúa (el usuario manda), solo el postproceso si está activo. Automático: el director puede activarse con el botón. Modo cine con **H**: hoy solo oculta paneles (`body.cine`); H pasa a ocultar paneles **y** activar el director si la casilla «Cámara de cine» está marcada; H otra vez lo desactiva. Sin casilla, H se comporta como hoy.
2. **Conflicto con OrbitControls y `camaraSiguiendo`** (`app.js:139-153`, `animar()` líneas 3242-3258): ambos escriben la cámara. Con el director activo se salta el bloque de seguimiento y `controles.update()`, y el director escribe la cámara después del temblor de sismo (`efectos.desplazamientoTemblor` se sigue sumando y restando como hoy). Un gesto del usuario (clic, rueda, arrastre) o **Esc** o **H** desactiva el director y devuelve el control sin salto, con `camaraSiguiendo = false` como ya hace `start` de los controles. Los límites (`minDistance`, `maxPolarAngle`, `limitesMapa`) no valen para el director: él mismo acota (suelo, mapa +4 celdas).
3. **Render**: `if (intro?.activo) ... else if (viaje?.activo) ... else if (post?.activo) post.render(scene, camara); else renderer.render(...)`. Intro y viaje tienen prioridad: mientras corren, el cine no actúa.
4. **Carga perezosa**: `import()` solo cuando el usuario marca la casilla o pulsa el botón. Falla de carga: aviso en consola, casilla vuelve a apagada, juego intacto.
5. **Teclas**: mientras el director o el postproceso de bienvenida estén «en directo» (director activo) los atajos del juego (espacio dispara, flechas/WASD conducen, 7/9/1/3) **no disparan nada**, igual que se corrigió en intro y viaje; solo valen Esc, H y el botón Desactivar. Esc primero detiene el cine y no abre la pausa.
6. **Reducción de movimiento**: con `prefers-reduced-motion: reduce` no hay tomas automáticas ni cámara lenta; el botón cae a una sola pose de plano general fija; el postproceso sí puede usarse (no se mueve nada).
7. Preferencias en `localStorage` (`ares.cine`, `ares.cine.post`) con `try/catch`. **Postproceso APAGADO por defecto** (aunque el director esté disponible).

## 3. Postproceso y vendoreo de passes (three r160, MIT)
r160 trae todo en `examples/jsm`. Se vendorea con la estructura de carpetas original, para no reescribir los `import` relativos (los passes importan `three` por el import map ya existente):
| Carpeta | Archivos |
|---|---|
| `vendor/postprocessing/` | `EffectComposer.js`, `Pass.js`, `RenderPass.js`, `ShaderPass.js`, `MaskPass.js`, `UnrealBloomPass.js`, `BokehPass.js`, `OutputPass.js` |
| `vendor/shaders/` | `CopyShader.js`, `LuminosityHighPassShader.js`, `BokehShader.js`, `OutputShader.js` |
Peso estimado: 55 a 75 KB sin minificar (estimación; se mide al copiar con `ls -l`). El repositorio actual ya tiene ~1,36 MB de vendor, así que sube ~5 %. Hay que conservar las cabeceras y añadir la licencia MIT de three (`vendor/LICENSE-three.txt`). `BokehPass` de r160 ya limpia `overrideMaterial`: se preserva igual y se prueba. Con composer, `RenderPass` sale lineal y `OutputPass` aplica el ACES y sRGB del renderer; se comprueba que el brillo no cambia al encender el interruptor.

## 4. FPS y criterio de hecho
**Medición** (prueba de juego en Chrome con la skill, servidor del worktree, partida real, misma escena y cámara): 300 cuadros de `requestAnimationFrame` sin postproceso y 300 con él; se reporta **mediana y p5** de FPS (el p5 es el peor 5 %); `renderer.info.memory` (geometrías, texturas) y `performance.memory.usedJSHeapSize` (si existe) antes de activar y tras 3 ciclos activar/desactivar. Misma medición con el director activo.
**Umbral mínimo**: mediana ≥ 30 fps y no más de 15 % por debajo del juego sin postproceso; memoria de `info` vuelve al valor inicial ±0.
**Si baja**: el módulo mide solo (rolling de 120 cuadros) y, si la mediana cae bajo el umbral 2 veces seguidas, **apaga el postproceso solo**, desmarca la casilla, deja un aviso corto («Postproceso apagado: el equipo no rinde») y hace `dispose()`. El director no depende de ello.
**No comprobable con GPU por software** (Chrome en este equipo puede usar SwiftShader): los FPS con bloom y bokeh no representan una GPU real ni integrada; solo se puede probar la lógica (cambios de estado, apagado automático forzado con umbral artificial, memoria, ausencia de errores y de peticiones externas). La cifra final se toma en el equipo de la defensa y la lleva el usuario.
**Hecho cuando**: (a) `python -m pytest api/tests/test_cine_adaptadores.py` pasa (node sobre `cine_datos.js`: tomas deterministas, suelo, `debeActuar`, mediana/p5, `decidirPostproceso`, sin rutas de usuario ni nombres del ejemplo ni CDN) y la suite existente sigue verde; (b) `git diff --stat` solo muestra `api/static/` y `api/tests/` (nada en `juego/` ni motor); (c) Chrome: casilla apagada = imagen idéntica a hoy; encendida = bloom visible; H, Esc y clic devuelven el control; teclas inertes con cine; reduced-motion sin tomas; falla simulada sin romper la partida; consola limpia; móvil 375 px; (d) informe y capturas en `docs/capturas/`; (e) nada commiteado sin aprobación.

## 5. Riesgos
- **Cine fuera del motor.** El director solo lee el estado ya recibido (posición, rumbo, eventos) y escribe `camara`; no hace `POST`, no pausa, no cambia el `dt` del juego. La «cámara lenta» del ejemplo escala el mundo; aquí se **descarta** (afectaría la partida): equivale a un acercamiento corto en el plano dramático.
- FPS en GPU integrada (bokeh con profundidad es el más caro): bokeh apagado por defecto y autoapagado.
- Fugas de render targets del composer: `dispose` al apagar y prueba de memoria.
- Carrera entre cine, intro, viaje y pausa: prioridad fija y `debeActuar` probada.
- Mareo o conflicto con quien conduce a mano: sin director en manual, Omitir/Desactivar siempre visible, reduced-motion.
- Colisión con `controles.addEventListener("start")` y los límites del mapa: el director no usa `limitesMapa`.
- Licencia y peso de vendor: MIT, ~5 % más.

## Paralelismo
Archivos nuevos: `api/static/cine_datos.js`, `cine3d.js`, `cine_post.js`, `cine_ui.js`, `vendor/postprocessing/*`, `vendor/shaders/*`, `api/tests/test_cine_adaptadores.py`. Existentes que se tocan: `app.js` (`animar()`, tecla H y atajos, carga perezosa) e `index.html` (contenedor, casilla, CSS `cn-*`). Los mismos puntos de `animar()` y del `keydown` los tocaron intro y viaje: se integra **después** de que su rama esté en main (o rebasando) para evitar conflictos. No toca `juego/` ni `api/servidor.py`. Puede hacerse en paralelo con trabajo de motor.

## 6. Preguntas que solo decide el usuario
1. **Alcance de v1.** A) Director + postproceso (recomendada: es lo pedido; el postproceso va apagado). B) Solo director, postproceso en una segunda entrega. C) Solo postproceso.
2. **Quién arranca el director.** A) Casilla «Cámara de cine» y tecla H en automático (recomendada). B) Solo tecla H, sin casilla. C) Se activa solo en la demo del modo automático, con Omitir siempre.
3. **Postproceso si baja de 30 fps.** A) Se apaga solo con aviso (recomendada). B) Solo avisa y el usuario decide. C) Sin medición automática; solo se reporta en la prueba.

## 7. Decisiones del usuario e implementación (ev3-d101 A, d102 A, d103 A)
- **Alcance A**: director y postproceso. **Arranque A**: casilla «Director de cámara» (en Opciones de la pausa) y tecla H en automático; H sin casilla o en manual sigue siendo solo el modo cine de paneles. **Fps A**: el postproceso se apaga solo con aviso visible («Postproceso apagado: el equipo no rinde») si la mediana de 120 cuadros baja de 30 fps dos ventanas seguidas.
- **Postproceso**: una casilla («Postproceso (bloom y bokeh)») enciende bloom moderado, bokeh leve y viñeta; apagado por defecto. Esto sustituye lo dicho en §2 sobre bokeh apagado aunque el interruptor esté encendido.
- **Cámara lenta (cambia §5)**: no escala el tiempo del mundo. Es una **repetición visual** de 3 s (1,2 s reales a 0,4x) del momento dramático (veto de seguridad `V-*` o dron destruido; nunca en el estado final, que tiene su pantalla). El cliente guarda las últimas posiciones del rover (buffer de unos 1,7 s, sin peticiones nuevas) y las reproduce con un marcador y la cámara del director; mientras dura, `ocupado()` bloquea todo paso hacia el motor y luego la simulación sigue. Con movimiento reducido no hay repetición.
- **Teclas con el director activo**: solo Esc y H; el espacio y el resto de atajos no hacen nada. Un clic, arrastre o rueda sobre la escena devuelve la cámara.
- **Vendoreo**: passes y shaders de three r160 descargados de la distribución r160 publicada (unpkg, versión fijada), con `vendor/LICENSE-three.txt`; los archivos de ejemplos de r160 no traen cabecera propia, la licencia MIT del paquete los cubre.
