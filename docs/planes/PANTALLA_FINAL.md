# PANTALLA FINAL: plan de adaptación (diseño, sin código)

Rama `feat/pantalla-final` (desde `feat/ensayo-intro`, la intro aún sin integrar a main). Origen: el módulo de pantalla final del ejemplo, más sus módulos de logros e iconos (inventario del ejemplo §2.4 y §3). **Decisión del usuario: «Todo, puntaje y logros», como en el ejemplo**, con la fórmula y los logros de ficción incluidos. Este plan los documenta tal cual y solo adapta la fuente de los datos. Mismo patrón que `VIAJE_planetas.md` e `INTRO_sistema_solar.md`.

## 1. Qué hace la pantalla final del ejemplo
- Capa a pantalla completa con el resultado: título (cumplida, abortada, fallida), **0 a 3 estrellas animadas**, **puntaje con cuenta ascendente**, rejilla de 10 estadísticas (cuerpo, modo, ciencia, objetivos muestreados, batería final, violaciones y vetos, barrancos evitados, replanificaciones, distancia, paso final), **logros nuevos**, hasta 3 capturas de «mejores momentos» con visor ampliado, **confeti** si hay 3 estrellas y botones Volver a jugar, Explorar otro cuerpo y Cerrar. Escape cierra; el movimiento se apaga con `prefers-reduced-motion`.
- **Puntaje:** `ciencia×1000 + barrancos evitados×50 + batería(%)×5 − violaciones×500`, redondeado y con mínimo 0, donde `ciencia` es la fracción de objetivos científicos cumplidos (0 a 1).
- **Estrellas:** 1 si hay éxito sin violaciones; 2 si además ciencia ≥ 60 %; 3 si ciencia ≥ 85 % y batería ≥ 20 %. Confeti 2,6 s solo con 3 estrellas.
- **Logros (22)** guardados en el navegador, con aviso emergente al desbloquear. Lista y estado de cada uno en §4.
- Recursos: iconos SVG en línea propios del ejemplo (sin archivos binarios); sin audio, imágenes, fuentes ni URLs. Los emoji que acompañan a los logros dependen de la fuente del sistema: se sustituyen por los iconos SVG, sin emoji.

## 2. Adaptación módulo por módulo (`api/static/`, ES, `?v=r14`, sin three ni CDN: solo DOM y canvas 2D)
**`final_datos.js`** (puro, sin DOM, probado con node):
- Constantes con nombre, iguales a las del ejemplo: `PESO_CIENCIA = 1000`, `PESO_BARRANCOS_EVITADOS = 50`, `PESO_BATERIA = 5`, `PENALIZACION_VIOLACION = 500`, `UMBRAL_2_ESTRELLAS = 0.6`, `UMBRAL_3_CIENCIA = 0.85`, `UMBRAL_3_BATERIA = 20`, y `ROTULO_PUNTAJE = «Puntaje de juego, no es un criterio de evaluación.»`.
- `normalizarResultado(estado, extra)`: convierte lo que sirve `/estado` (y el conteo de §3) a los nombres del ejemplo: `ciencia` (fracción), `bateria_pct`, `violaciones`, `barrancos_evitados`, `vetos`, `replanificaciones`, `distancia`, `paso`, `planeta`, `modo`. Dato ausente = `null`, mostrado «—», nunca un cero inventado.
- `puntajeFinal(r)`, `desglosePuntaje(r)` (cuatro términos y total, para mostrarlos), `estrellas(r)`, `tituloFinal(codigo)`.
- `LOGROS` (22 definiciones: id, nombre, descripción, `estado`: `directo` | `adaptacion`) y `evaluarLogros(evento, memoria)` (reglas de §4); `leerLogros(texto)` y `serializarLogros(obj)` tolerantes a datos corruptos; `debeMostrarFinal({activada, reducido, terminal})`.

**`final_iconos.js`** (puro, devuelve cadenas SVG): los iconos propios del ejemplo (estrella llena y vacía, insignias de logro, símbolos de estadística), construidos con `createElementNS` en el DOM, sin `innerHTML`.

**`final_tarjeta.js`** (DOM, solo `textContent`): `crearFinal({contenedor, alContinuar, alCerrar, alRepetir, alOtroPlaneta})` devuelve `{mostrar(resultado, momentos), ocultar(), visible, dispose()}`. Clases `fn-*` en el `<style>` de `index.html`. `role="dialog"`, `aria-modal`, `aria-live` en el puntaje, foco al primer botón, Escape. Contiene el **rótulo de puntaje siempre visible junto a la cifra**, el desglose de la fórmula, el aviso del terreno de Marte (texto reutilizado de `viaje_datos.js`), la casilla «Mostrar la pantalla final» y Omitir.

**`final_logros.js`** (DOM + almacén): `crearLogros({almacen, alDesbloquear})`, aviso emergente (`aria-live="polite"`), `revisar(evento)`, `lista()`. Almacén `localStorage` clave `ares.logros` con try/catch (si falla, funciona en memoria) y botón «Borrar logros» en el menú de pausa.

**`final_momentos.js`**: captura 3 imágenes del canvas del renderer (`toDataURL` justo después de un `render`, sin `preserveDrawingBuffer`) en tres momentos de la partida: primer veto, mayor riesgo y final. Tope de 3 imágenes y 960 px de ancho, liberadas al cerrar.

**Integración** (`app.js`, `index.html`, `servidor.py`, pruebas): en `terminarMision`, antes de `mostrarMeta(codigo, cadenaTerminada)`, `correrFinal(codigo, estado)` con `import()` perezoso, `try/catch` total y `finally` que abre la meta. Con la cadena automática solo aparece al terminar la última misión. «Volver a jugar» y «Explorar otro cuerpo» reutilizan `nuevaDesdeMeta` y el asistente; no duplican lógica. `servidor.py` solo añade a `/estado` claves de solo lectura que el motor ya calcula (`vetos`, `replanes`, `sitios_visitados`, `sitios_totales`, `distancia_recorrida`, `recargas`); el motor no se toca.

## 3. Cuándo aparece y cómo se sale
- Al llegar a un estado terminal (EXITO, FRACASO, MODO_SEGURO, SIN_RUTA), antes de la meta actual. «Continuar»/«Cerrar» abre la meta (repetir, otro mapa, dificultad, salir), sin cambios.
- Omitir y Escape visibles desde el primer cuadro. Preferencia `ares.final` (try/catch, activa por defecto). Guarda de 120 s sin interacción: se cierra sola y deja la meta.
- `prefers-reduced-motion`: sin cuenta ascendente, sin entrada animada, sin confeti, estrellas fijas.
- Fallo (import, dato, captura, logros): `console.warn` de una línea y se salta lo que falló; si falla la capa entera, se abre la meta. **El resultado nunca depende de esta pantalla** (HUD, meta y `/estado` ya lo muestran).
- Capa `aria-modal` que bloquea las teclas de conducción, como viaje e intro.

## 4. Fuente de cada dato y de cada logro
**Puntaje y estadísticas.** Cada término se conserva; esto es lo que el rover entrega hoy:
| Término del ejemplo | Dato del rover | Estado |
|---|---|---|
| `ciencia` (fracción) y objetivos muestreados | `sitios_visitados / sitios_totales` | directo |
| `bateria_pct` | `bateria` | directo |
| `vetos`, `replanificaciones`, `paso`, `planeta`, `modo`, estado | `vetos`, `replanes`, `paso`, `planeta`, `modo_planeta`, `estado` | directo |
| `barrancos_evitados` | no existe como contador | **requiere adaptación** (A1) |
| `violaciones` | no existe con ese nombre | **requiere adaptación** (A2) |
| `distancia_m` | `distancia_recorrida` en celdas, sin escala en metros | **requiere adaptación** (A3) |
| `motivo_final` | `estado` y `avisos` | directo, texto corto |
Nota: el motor ya tiene un puntaje propio y simple (HUD, `juego/CONTRATO_V2.md`). No se toca. La pantalla final rotula el suyo como «puntaje de juego» y el HUD recibe el mismo rótulo corto, para que no se confundan entre sí, con el fitness del AG ni con la rúbrica.

**Logros (22).** Condición del ejemplo, con el dato del rover:
| Logro | Condición | Dato / estado |
|---|---|---|
| Primera muestra | primer sitio visitado | `sitios_visitados ≥ 1`, directo |
| Científico | todos los objetivos muestreados | visitados = totales, directo |
| Misión cumplida | estado EXITO | directo |
| Al límite | EXITO con batería < 15 % | directo |
| Ingeniero cauto | ≥ 5 vetos y sin fracaso | `vetos`, directo |
| Aeronauta | EXITO en modo sonda | `modo_planeta`, directo |
| Primer despliegue | iniciar una partida | directo |
| Ojo de la tormenta | sobrevivir 10 pasos seguidos con tormenta | el motor tiene evento `tormenta`; necesita contar pasos con el evento activo (bitácora o `ambiente`) — verificar |
| Noctámbulo | sobrevivir una noche completa | evento `noche` del motor; igual, contar pasos — verificar |
| Impacto | presenciar un meteorito | evento `meteorito` en `eventos_del_paso`, directo |
| Señal anómala investigada | muestrear una señal anómala | el motor tiene `senal_biologica` con `afirma_vida: false`; falta la noción de «muestrear la señal» — **adaptación B1** |
| Primer contacto | aceptar un contacto ficticio | no existe «contacto»; **adaptación B1**, ficción |
| Géiser a la vista | géiser | no hay géiseres — **adaptación B2**, ficción |
| Bajo el volcán | erupción en Ío | no hay Ío ni volcanes — **adaptación B2**, ficción |
| Frío extremo | misión en Plutón o Tritón | no hay esos cuerpos — **adaptación B3** |
| Viajero | primer viaje entre cuerpos | el viaje existe en el cliente, directo |
| Trotamundos | 5 cuerpos distintos | cuerpos del rover: 8, directo |
| Gran explorador | los 18 cuerpos | solo hay 8 — **adaptación B3** |
| Científico de datos | abrir los 3 laboratorios | enganche en el cliente (`laboratorio.js`), directo |
| Comparador | comparar políticas | enganche en el cliente, directo |
| Arquitecto del terreno | colocar un barranco | enganche en el cliente, directo |
| Ojos del robot | cámara en primera persona | enganche en el cliente, directo |
Todos los de ficción se rotulan en pantalla «Ficción, no evidencia» y se declaran en el informe (§5.3).

**Requiere adaptación (propuestas para ficha; recomendación primero):**
- **A1 barrancos evitados:** a) contar en la bitácora las filas con motivos `V-BORDE-BARRANCO` o `V-RNA-BARRANCO` (veto por barranco, dato real); b) usar los vetos totales; c) contador nuevo en el motor (toca el motor, no recomendable).
- **A2 violaciones:** a) `colisiones` + pasos sobre la tolerancia térmica (`pasos_sobre_tolerancia`), ambos ya expuestos; b) solo `colisiones`; c) cero y rotulado «sin violaciones registradas».
- **A3 distancia:** a) mostrar «N celdas» sin convertir; b) convertir con una escala fija documentada (supuesto de simulación); c) ocultar la estadística.
- **B1 señal y contacto:** a) «Señal anómala» al visitar la celda de una `senal_biologica` y «Primer contacto» al desbloquear esa misma señal; ambos con el aviso de que no afirman vida; b) dejarlos bloqueados con la nota «requiere un evento que el rover no tiene»; c) un botón de demostración que los desbloquee (no recomendable).
- **B2 géiser y volcán:** a) mostrarlos bloqueados con la nota «no hay géiseres ni volcanes en este terreno» (el terreno es el de Marte); b) dispararlos con un evento de ficción nuevo en la interfaz (sin tocar el motor); c) renombrarlos como sismo (el motor tiene `sismo`).
- **B3 Plutón, Tritón y los 18 cuerpos:** a) bloqueados con nota, y «Gran explorador» pasa a «los 8 cuerpos» (la cifra la fija `/planetas`); b) mantenerlos tal cual; c) ocultarlos.

## 5. Criterio de hecho y comprobaciones
1. **Pruebas con node** (`api/tests/test_final_adaptadores.py`): `puntajeFinal` con la fórmula del ejemplo en casos límite (mínimo 0, ciencia 0 y 1, batería 0 y 100, violaciones altas); `estrellas` en los umbrales exactos (0,6; 0,85 y 20 %); `evaluarLogros` caso por caso (cumple y no cumple) para los 22; `leerLogros` con datos corruptos; campos ausentes dan «—»; `debeMostrarFinal`; el rótulo de puntaje presente; textos prohibidos ausentes (nombres del ejemplo, rutas de usuario, `http`, `cdn`, `innerHTML`). Prueba de API: `/estado` trae las claves nuevas sin cambiar las existentes. Suites `api/tests` y `tests/` verdes; `git diff --stat` solo en `api/`, `INFORME_TECNICO.md`, `docs/`.
2. **Chrome, partida real** (servidor del worktree): (a) EXITO y FRACASO muestran la pantalla antes de la meta, con rótulo visible junto al puntaje; (b) la cifra coincide con la fórmula aplicada a los datos de `/estado`; (c) Omitir y Escape abren la meta; (d) casilla apagada: directo a la meta; (e) `prefers-reduced-motion`: sin cuenta, sin confeti; (f) fallo simulado del import o de la captura: la meta aparece y hay aviso en consola; (g) cadena automática: solo al final; (h) un logro desbloqueado aparece y persiste tras recargar; «Borrar logros» lo limpia; (i) móvil 375 px sin desborde; (j) consola limpia, sin peticiones a otros hosts, FPS de la partida sin cambio; capturas en `docs/capturas/`.
3. **INFORME_TECNICO.md (tarea del plan):** subsección nueva en §6, «Pantalla final: puntaje y logros», con: la fórmula y sus constantes; el rótulo «puntaje de juego, no es un criterio de evaluación» y que no es el fitness del AG ni una métrica de la rúbrica; que los logros de ficción (contacto, señal anómala, géiser, volcán de Ío, frío extremo) son ficción del juego y no evidencia de vida ni dato de misión; y la lista de adaptaciones A1 a B3 con la opción elegida.
4. Sin textos, rutas ni nombres del ejemplo; sin CDN, audio ni imagen nuevos. Nada commiteado hasta que el usuario lo apruebe.

## 6. Preguntas que solo decide el usuario
1. **¿Cómo se cuentan «barrancos evitados» y «violaciones» (A1, A2)?** A) Con datos ya expuestos: vetos por barranco, y colisiones más pasos sobre la tolerancia (recomendada). B) Con vetos totales y solo colisiones. C) Contadores nuevos en el motor.
2. **¿Qué pasa con los logros sin equivalente en el rover (B1 a B3)?** A) Se muestran bloqueados con la nota de por qué, y los de ficción rotulados (recomendada). B) Se crean eventos de ficción en la interfaz para poder desbloquearlos. C) Se ocultan hasta que el motor los tenga.
3. **¿Convive con el puntaje que ya muestra el HUD?** A) Sí, con rótulos distintos y el mismo aviso de «puntaje de juego» (recomendada). B) El HUD pasa a mostrar el de la pantalla final. C) La pantalla final muestra ambos.

## Paralelismo
Este frente toca solo cliente: `api/static/app.js`, `api/static/index.html`, módulos nuevos `final_*.js`, y en `api/servidor.py` únicamente claves de lectura nuevas en `/estado`. No toca `integracion.py`, `genetico.py`, `simulador.py` ni `rna.py` (frente ARX-94). Si alguno de los dos llegara a tocar los archivos del otro (por ejemplo ARX-94d en `api/servidor.py` por `/rna`), van en fila.
