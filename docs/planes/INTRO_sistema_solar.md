# INTRO del sistema solar: plan de adaptación (diseño, sin código)

Rama `feat/intro-sistema` (desde main d2250bf). Origen: el módulo de intro del ejemplo (más su módulo de pintores de planetas, opcional) y el inventario del ejemplo §2.2. Reutiliza lo del viaje entre planetas (`viaje_datos.js`, `viaje3d.js`, `viaje_tarjeta.js`, `docs/planes/VIAJE_planetas.md`).

## 1. Qué hace la intro del ejemplo
- Pantalla completa sobre la app con un sistema solar 3D orbitable: Sol con corona, 10 planetas, 8 lunas, cinturón de asteroides (1.600 puntos), 3.200 estrellas y órbitas dibujadas.
- Cámara con `OrbitControls`; al pasar el puntero sobre un cuerpo aparece una tarjeta con su ficha; al pulsarlo, la cámara vuela 1,5 s hacia él y la intro se cierra devolviendo el nombre. Botón «Entrar a la misión actual» (omitir). Etiquetas DOM clicables.
- Crea su propio `WebGLRenderer` (segundo contexto), textura de respaldo propia, casi todo el CSS en una cadena JS. La rapidez orbital es una escala comprimida inventada.
- Licencia y recursos: todo procedural (canvas y ruido). No trae audio (el sonido del ejemplo es otro módulo, no se trae), ni imágenes, ni fuentes (usa `system-ui`), ni URLs. Nada de licencia dudosa; tampoco se trae nada de lo anterior.

## 2. Adaptación módulo por módulo (todo en `api/static/`, ES, `three` por el import map, sin CDN, `?v=r14`)

**`intro_datos.js`** (puro, sin DOM ni THREE, probado con node):
- `CUERPOS_INTRO`: solo los 8 perfiles de `/planetas`, en orden al Sol, con `{nombre, distanciaEscena, radioEscena}`. Valores de escena rotulados «no están a escala». Sin Ceres, Plutón, lunas ni cinturón (el cinturón y las lunas no son perfiles del rover).
- Reutiliza de `viaje_datos.js`: `PLANETAS_VIAJE`, `DISTANCIA_SOL_MKM`, `AVISO_TERRENO`, `datosTarjeta` (distancia al Sol constante NASA y «vehículo permitido» salido de `/planetas`). No duplica constantes.
- `ROTULO_INTRO`: «Escena ilustrativa: tamaños, distancias y velocidades no están a escala.»
- `debeMostrarIntro({activada, vistaEnSesion, reducido, webgl})` y `modoIntro(reducido)` (`animado` | `estatico`); `posicionOrbital(t, cuerpo)` (ángulo = base + t·k, k puramente visual); `fasesVuelo(duracion)` y `pasoVuelo(u)` (suavizado); `elegirCuerpo(nombre, catalogo)` devuelve `{planeta, modo}` o `null` si no es perfil. Tarjeta del cuerpo: nombre, tipo de vehículo (`/planetas`), distancia media al Sol (constante), sin «ficha» ni dato curioso.

**`intro3d.js`** (dibujo, recibe `THREE`): `crearIntro({THREE, renderer, camara, OrbitControls, texturaPlaneta, paleta, catalogo, alElegir, alOmitir})` devuelve `{iniciar() → Promise, render(), omitir(), activo, dispose()}`.
- Escena propia, cámara propia y su `OrbitControls` sobre el mismo `renderer.domElement`; los controles de la partida se deshabilitan mientras dura y se restituyen en `finally`. Sin segundo contexto WebGL (a diferencia del ejemplo, igual que el viaje).
- Sol, 8 esferas (32×24), órbitas con `LineLoop`, 1.200 estrellas (no 3.200), anillos solo de Saturno y Urano (rasgo real). `texturaPlaneta` inyectada (`texturaParaPlaneta` de `app.js`), con respaldo de color plano `PALETAS_PLANETA[...].horizonte`. Texturas en caché y `dispose` completo.
- Etiquetas DOM en una capa (con `textContent`, sin `innerHTML`); puntero y teclado: Tab recorre los planetas, Intro elige, Escape omite.
- El vuelo termina y llama `alElegir(nombre)`; la promesa de `iniciar` se resuelve siempre (nunca rechaza).

**`intro_tarjeta.js`** (DOM): cabecera «ARES-X · elige un planeta», tarjeta de cuerpo, rótulo ilustrativo y aviso del terreno siempre visible (no solo al elegir), botón «Omitir» y casilla «No volver a mostrar». Clases `in-*` en el `<style>` de `index.html`. Reutiliza el patrón de `viaje_tarjeta.js` (`role`, `aria-live`, foco al botón Omitir).

**Integración mínima** (solo `app.js` y `index.html` + pruebas nuevas): al final del arranque, tras `poblarPlanetas()`, `correrIntro()` con la misma forma que `correrViaje()` (import() perezoso con `Promise.all`, `try/catch` total, `finally` que restaura menú, controles y render). En `animar()`: `if (intro?.activo) intro.render(); else if (viaje?.activo) ...`. `alElegir(nombre)` solo escribe `menu-planeta` y `menu-modo-planeta` (cada planeta ya fija su vehículo, el gigante pasa a sonda) y muestra el asistente: no inicia la partida. El motor no se toca: ni `POST`, ni `GET`, ni estado. Con la intro elegida y luego «Iniciar» con otro planeta que el de la sesión anterior, el viaje existente sigue funcionando sin cambios.

**Aviso del terreno (verificado en el motor).** `juego/partida.py` pasa `planeta` solo a `termico.Termico(planeta)` (temperatura y tolerancia, solo avisa); el mapa, los obstáculos y los eventos no lo usan, y `api/servidor.py` lo declara («el terreno es el de Marte»). Se muestra `AVISO_TERRENO` en la cabecera de la intro (texto reutilizado). Si ARX-50/51/57 cambian el motor, se revisa.

**Cifras que no pasan:** ficha, gravedad, temperatura, presión y dato curioso del ejemplo (sin fuente y no en `/planetas`): no se copian ni se muestran. Radios, órbitas y rapidez de escena: rotulados «no a escala». Sin puntajes, sin narrativa, sin «Centro de Control» ficticio: título «ARES-X · sistema solar». Una prueba de texto sobre los archivos nuevos verifica que no hay nombres del ejemplo, rutas de usuario ni CDN.

## 3. Cuándo se muestra
- Al abrir la app, una sola vez por sesión del navegador (`sessionStorage` `ares.intro.visto`, con try/catch). Recargar la página en la misma sesión no la repite; «Ver intro» en el asistente (botón pequeño) la reabre cuando se quiera.
- Preferencia: casilla «Mostrar la introducción al abrir» (activa por defecto) en el menú de inicio, en `localStorage` `ares.intro` (try/catch, mismo patrón que `ares.viaje`). No toca el motor.
- Duración: interactiva, no cronometrada. Vuelo de cámara al elegir 1,2 s. Omitir (botón y Escape) visible desde el primer cuadro. Temporizador de guarda: si `iniciar` no pinta el primer cuadro en 3 s, se omite; si pasa de 90 s sin interacción, se cierra sola y deja el asistente (sin bloquear).
- `prefers-reduced-motion: reduce`: sin órbitas animadas ni vuelo; vista estática del sistema, planetas elegibles por lista y puntero, corte directo al asistente.
- Fallo: import o WebGL o textura que falle → `console.warn` una línea, `dispose`, asistente normal. Jugar nunca depende de la intro (los 8 planetas siguen en el `<select>`, que no se retira).
- Mientras corre, se oculta `#menu` y se bloquean teclas de conducción con la misma capa `aria-modal` del viaje.

## 4. Riesgos de FPS y cómo medir
- Riesgos: pantalla de inicio con 8 texturas por CPU (generación al abrir); fugas de geometría y textura al abrir y cerrar; etiquetas DOM reposicionadas cada cuadro; dos `OrbitControls` sobre el mismo canvas si no se desactivan.
- Mitigaciones: reutiliza renderer y textura en caché, esferas 32×24, 1.200 estrellas, texturas 256×128 generadas de a una con `setTimeout(0)`, etiquetas solo si cambian de posición más de 1 px, `dispose` al cerrar, y ningún dibujo de la escena principal mientras dura.
- Medir (prueba de juego en Chrome, servidor del worktree): mediana y p5 de FPS durante 10 s con la intro; `renderer.info.memory` antes y después de abrir y cerrar tres veces; tiempo de `iniciar()` al primer cuadro; FPS de la partida antes y después de la intro (no debe empeorar).
- Umbral: mediana ≥ 30 fps (y ≥ la del juego normal menos 15 %), `info.memory` vuelve al valor inicial tras la tercera vez, primer cuadro < 250 ms (8 texturas), contexto WebGL único (`read_console_messages` sin avisos de contextos).

## 5. Criterio de hecho y comprobaciones
1. `python -m pytest api/tests/test_intro_adaptadores.py` (node sobre `intro_datos.js`): solo los 8 perfiles, `debeMostrarIntro` (activada, vista, reducido, sin WebGL), `elegirCuerpo` (perfil, desconocido, gigante → sonda), `posicionOrbital` acotada, `fasesVuelo` suma exacta, textos prohibidos ausentes, `AVISO_TERRENO` presente. La suite `api/tests` completa sigue verde y `git diff --stat` solo muestra `api/static/` y `api/tests/`.
2. Chrome, partida real: (a) primera apertura muestra la intro con rótulo y aviso del terreno; elegir Saturno deja el asistente con Saturno y «sonda»; (b) Omitir y Escape cortan; (c) recargar en la misma sesión no la repite; «Ver intro» sí; (d) casilla apagada: no aparece al abrir una sesión nueva; (e) `prefers-reduced-motion` emulado: vista estática; (f) fallo simulado de `crearIntro` o sin WebGL: el asistente y la partida funcionan, con aviso en consola; (g) tras la intro, Marte→Venus sigue mostrando el viaje; (h) consola limpia y sin peticiones a otros hosts; (i) móvil 375 px sin desborde y con la tarjeta legible; (j) FPS y memoria dentro de §4, informe y capturas en `docs/capturas/`.
3. Sin textos, rutas, nombres o recursos del ejemplo; sin CDN; three r160 vendoreado. Nada commiteado hasta que el usuario lo apruebe.

## 6. Preguntas que solo decide el usuario
1. **¿Cuándo aparece?** A) Una vez por sesión del navegador al abrir, con casilla para apagarla y «Ver intro» (recomendada). B) Cada vez que se abre o recarga la página. C) Solo si se pulsa «Ver intro» (opt-in).
2. **¿Elegir en la intro cambia el planeta del asistente?** A) Sí: rellena el asistente y espera «Iniciar» (recomendada: no lanza partidas por un clic y respeta la validación rover/sonda). B) Inicia la partida directamente. C) Es solo vista decorativa, sin elegir.
3. **¿Cuánto del ejemplo se trae?** A) Solo el Sol y los 8 perfiles con órbitas (recomendada: coherente con el motor). B) A más cinturón de asteroides y la Luna, rotulados como ilustración. C) Lo anterior más el recorrido automático de cámara al abrir (más vistoso, más FPS y más tiempo hasta jugar).
