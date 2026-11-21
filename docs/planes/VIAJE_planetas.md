# VIAJE entre planetas: plan de adaptación (diseño, sin código)

Rama `feat/viaje-planetas` (desde main f486fb0). Origen: `ARES-X_proyecto_2026-11-10/ares-x/ares_x/` (`vista3d.js` L439-672 y L585-661, `vista3d_tarjeta_viaje.js`, `vista3d_planetas.js`) más `INVENTARIO_EJEMPLO.md` §2.3.

## 1. Qué hace cada pieza del ejemplo

| Pieza | Qué hace | Se trae |
|---|---|---|
| `vista3d.js` · cinemática (`iniciarViaje`, `FASES_VIAJE`, `animarViaje`) | 7 fases (aterriza una nave junto al robot, el robot sube, despega, espacio, llega, baja, la nave se va), 12,6 s en total. Mueve cámara, robot, polvo, sonido y velo. Se llama al iniciar una misión en otro cuerpo. | Solo la fase «espacio». El resto depende del robot, el sonido y el entorno del ejemplo. |
| `vista3d.js` · escena de espacio (`prepararEspacio`, `planetaEspacio`, `animarEspacio`, `limpiarEspacio`) | Segunda `THREE.Scene` con 2500 estrellas, dos esferas de planeta (textura, halo, anillos de Saturno y Urano), nave en curva Bézier y estela de 160 puntos aditivos. Se dibuja en el mismo renderer en lugar de la escena principal. | Sí, reducida y reescrita. |
| `vista3d_tarjeta_viaje.js` | Tarjeta DOM con título «Viajando de A a B», miniatura, gravedad, temperatura, presión, distancia al Sol, dato curioso y barra de 12 s. | Sí, con cambios de datos (§2). |
| `vista3d_planetas.js` | 18 pintores procedurales de textura equirectangular y miniaturas por canvas. | No. Se reutiliza `texturaParaPlaneta` y `PALETAS_PLANETA` de `app.js`. Con datos de los 8 perfiles, no de 18 cuerpos. |
| `vista3d_base.js`, `vista3d_senales.js`, `vista3d_cine.js` | Base de utilidades, señales de nave y director de cámara. | No hacen falta para el viaje; `cine` es otra decisión (inventario P1). |

## 2. Diseño de adaptación

Todo en `api/static/`, módulos ES, `three` por el import map (r160 vendoreado), sin CDN, cadena `?v=r14` como el resto. Funciones puras separadas del dibujo, para probarlas con node.

**`viaje_datos.js`** (puro, sin DOM ni THREE):
- `DISTANCIA_SOL_MKM`: constantes de los 8 perfiles (NASA Planetary Fact Sheet, millones de km: 57,9 / 108,2 / 149,6 / 228,0 / 778,5 / 1.432 / 2.867 / 4.515). Rotuladas «distancia media al Sol».
- `datosTarjeta(desde, hacia, catalogo)` devuelve filas `{etiqueta, valor, tipo}` con `tipo` = `real` | `supuesto` | `sin_dato`. Solo usa lo que traiga `/planetas`, más las constantes. Lo que falte sale «Sin dato».
- `AVISO_TERRENO`, `ROTULO_ILUSTRATIVO` (textos fijos, ver más abajo).
- `debeViajar({previo, nuevo, activado, omitidoEnCadena})`: verdadero solo si `previo` y `nuevo` son perfiles distintos de los 8, y la casilla está activa.
- `fasesViaje(duracion)` reparte la duración en `salida`, `travesia`, `llegada` (15 %, 70 %, 15 %). `faseActual(t, fases)` devuelve `[fase, u]`.
- `trayectoria(u, ancho)` devuelve posición y tangente en la Bézier. `actualizarEstela(historial, p, n)` es la cola circular de puntos. `modoMovimiento(reducido, activado)` devuelve `animado` | `tarjeta` | `ninguno`.

**`viaje3d.js`** (dibujo, recibe `THREE`): `crearViaje({THREE, renderer, camara, texturaPlaneta, paleta})` devuelve `{iniciar(desde, hacia) → Promise, render(), omitir(), activo, dispose()}`.
- Escena propia con estrellas (1.200 puntos, no 2.500), dos esferas (48×32), nave procedural mínima (cuerpo, cono y llama; el rover no tiene `crearNave`) y estela de 120 puntos.
- `texturaPlaneta(nombre)` se inyecta desde `app.js` (`texturaParaPlaneta`). Si falla, esfera de color plano con `PALETAS_PLANETA[...].horizonte`. Anillos solo para Saturno y Urano (rasgo real). Sin lunas.
- La promesa de `iniciar` se resuelve al terminar, omitir o fallar (nunca rechaza).

**`viaje_tarjeta.js`** (DOM): `crearTarjetaViaje(contenedor)` con `mostrar(datos)`, `ocultar()`, `dispose()`. Todo con `textContent` (sin `innerHTML`). Barra de progreso con `role="progressbar"`. Botón «Omitir viaje». Clases `vj-*` en el `<style>` de `index.html` (como las del resto del panel). Sin miniatura en v1.

**Integración mínima en `app.js`** (único archivo existente que se toca, más `index.html` para el contenedor, la casilla y el CSS):
1. Cuándo se dispara: el cambio de planeta ya es «partida nueva» (`POST /partida` en `cargarPartida`; el rover no cambia de planeta en caliente). Se guarda `previo = vigente.planeta` antes del POST. Si `datos.planeta !== previo` y `previo` no es nulo, se marca `viajePendiente`. El arranque inicial, la recarga de página y la cadena automática (mismo planeta) no viajan.
2. Dónde corre: dentro de `conCarga`, con la partida ya creada y en pausa, justo antes de `cuentaAtras`. El motor ya respondió; el viaje no escribe nada en él: ni `POST`, ni `GET`, ni estado.
3. Render: en `animar()`, `if (viaje?.activo) viaje.render(); else renderer.render(scene, camara)`. Mientras viaja no se dibuja la escena principal (ahorra FPS).
4. Duración: valor de la pregunta 1. Botón «Omitir viaje» y tecla Escape (visibles desde el primer segundo).
5. `prefers-reduced-motion: reduce`: no hay escena 3D. Solo la tarjeta estática (sin barra animada), con «Continuar», o se cierra a los 5 s.
6. Casilla «Animación de viaje entre planetas» en el menú de inicio y en el panel. Se guarda en `localStorage` (`ares.viaje`, con try/catch) y no afecta al motor.
7. Seguridad: todo el uso va en `try/catch`. Un temporizador de guarda (duración + 2 s) fuerza `omitir()`. Si falla la creación de la escena, la textura o el contexto WebGL, se registra una línea en consola y se sigue con la partida normal (`dispose` + `renderer.render(scene, camara)`). Mientras corre se bloquean las teclas de conducción y los botones de partida con una capa `aria-modal`.

**Textos que debe mostrar la tarjeta (fijos, en español con tildes):**
- `AVISO_TERRENO`: «En todos los planetas el terreno, los obstáculos y los eventos de la partida son los de Marte. El planeta cambia el aspecto, la temperatura interna del rover (solo avisa) y el vehículo permitido.»
- `ROTULO_ILUSTRATIVO`: «Escena ilustrativa: no está a escala ni representa un traslado real.»

**Verificación del aviso en el motor.** `api/servidor.py:89` dice que el terreno es el de Marte. En `juego/` y `api/`, `planeta` solo entra en `Termico` (`T_AMB_POR_PLANETA`, tolerancia) y en la validación rover/sonda. El mapa, los obstáculos y los eventos no dependen del planeta, así que M12 queda parcial y el aviso es verdadero. Si ARX-50 o ARX-57 cambian eso, el aviso se vuelve a revisar.

**Cifras del ejemplo que el rover no puede sostener (y qué hacer):**
| Cifra del ejemplo | Problema | Propuesta |
|---|---|---|
| Gravedad, temperatura día/noche, presión y `dato_curioso` (de `fichas_planetas.json`, 18 cuerpos, sin fuente) | `/planetas` no los devuelve; el catálogo del ejemplo no existe aquí. | No copiar el JSON. Mostrarlos solo si salen de `/planetas` ampliado (pregunta 3); si no, «Sin dato». Sin «dato curioso». |
| Gravedad y temperatura de `docs/PLAN_PLANETAS.md` | Son «supuestos de simulación», no constantes. | Si se muestran, con rótulo «supuesto de simulación». Presión: no hay cifra, «Sin dato». |
| `distanciaSol` (9 cuerpos, incluye Europa) | Valores con otra fuente; Europa no es perfil. | Solo los 8 perfiles, valores NASA, rotulados como constante real aproximada. |
| 12 s de la barra, tiempos de fase (1,7 a 3,6 s) | Duración de cine, no un tiempo de viaje. | Nunca rotularlos como tiempo de viaje. Sin tiempos de viaje reales, sin distancia entre planetas (varía mucho). |
| Posiciones y radios de la escena (radio 7 a distancias 26-44) | No es escala. | Rotular «no está a escala». |
| Robot que sube a una nave | Un rover real no se embarca así. | Fuera de v1 (solo viaja la nave). Rótulo ilustrativo. |
| Rótulos y recursos propios del ejemplo | Prohibidos por el usuario. | Una prueba de texto sobre los archivos nuevos comprueba que no aparecen nombres del ejemplo, rutas de usuario ni CDN. |

## 3. Riesgos de FPS y cómo medir
- Riesgos: segunda escena en el mismo renderer (sin segundo contexto WebGL, bien); texturas por CPU de los dos planetas (la primera vez); fugas de geometría o textura entre viajes; estela con `needsUpdate` por cuadro; la tarjeta DOM sobre WebGL.
- Mitigaciones: sin dibujar la escena principal durante el viaje, esferas de 48×32, 1.200 estrellas, estela de 120 puntos, texturas de 256×128 en caché por planeta, `dispose` de geometrías, materiales y texturas al terminar, `renderer.setPixelRatio` sin tocar.
- Cómo medir (skill `prueba-juego-chrome`, servidor del worktree): FPS con y sin viaje (mediana y p5 de `requestAnimationFrame`) en un viaje Marte→Venus y otro Marte→Neptuno; `renderer.info.memory` (geometrías, texturas) antes y después de tres viajes seguidos; tiempo de `iniciar()` hasta el primer cuadro con `performance.now()`.
- Umbral: mediana ≥ 30 fps en el equipo de la defensa (y ≥ la del juego normal menos 15 %); `info.memory` vuelve al valor inicial ±0 tras el tercer viaje; primer cuadro < 150 ms.

## 4. Criterio de hecho y comprobaciones en Chrome
1. `python -m pytest api/tests/test_viaje_adaptadores.py` pasa (node sobre `viaje_datos.js`). Cubre: `debeViajar` (mismo planeta, previo nulo, casilla apagada, perfil desconocido), `datosTarjeta` («Sin dato» con catálogo vacío), las 8 distancias, `fasesViaje` suma exacta, `trayectoria` en u=0 y u=1, cola de estela acotada, textos prohibidos ausentes. La suite existente `api/tests` sigue verde (sin tocar el motor: `git diff --stat` solo muestra `api/static/` y `api/tests/` nuevos).
2. En Chrome (claude-in-chrome, partida real): (a) Marte→Venus muestra el viaje, la tarjeta con el aviso del terreno y el rótulo ilustrativo; termina y la partida nueva queda en Venus con el mismo mapa de Marte. (b) «Omitir viaje» y Escape cortan el viaje y la partida sigue normal. (c) Casilla apagada: no hay viaje, solo la cuenta atrás de siempre. (d) Con `prefers-reduced-motion` emulado: sin escena 3D, solo tarjeta estática. (e) Marte→Júpiter (sonda): viaja y el modo sonda sigue funcionando. (f) Primer inicio, recarga de página y cadena automática: no hay viaje. (g) Falla simulada (lanzar excepción en `crearViaje` desde la consola): el cambio de planeta funciona igual y queda un aviso en consola. (h) Consola sin errores y sin peticiones a otros hosts (`read_network_requests`). (i) Móvil 375 px: la tarjeta no desborda.
3. FPS y memoria dentro del umbral de §3, con el informe y capturas en `docs/capturas/` según la regla de la skill.
4. Sin rótulos ni recursos propios del ejemplo, ni rutas de usuario, ni CDN en lo traído.
5. Nada commiteado hasta que el usuario lo apruebe.

## 5. Preguntas que solo decide el usuario

1. **Duración del viaje.** A) 5 s. B) 8 s (recomendada: da tiempo a leer el aviso del terreno y la tarjeta, con omitir siempre visible). C) 12 s (la del ejemplo).
2. **¿Se activa por defecto?** A) Sí, con casilla para apagarlo y botón omitir (recomendada: es lo que se pide traer y no cambia el motor). B) No, opt-in (casilla apagada por defecto). C) Solo la primera vez por planeta en cada sesión del navegador.
3. **Datos de la tarjeta.** A) Solo nombre, modo, distancia media al Sol (constante real) y los avisos; sin tocar el backend. B) A más gravedad y temperatura «supuesto de simulación», leídas de un `/planetas` ampliado con `ficha` (es una tarea aparte de backend, solo lectura, sin cambiar el motor) (recomendada). C) B más una línea de «por qué sonda» para los gigantes.
