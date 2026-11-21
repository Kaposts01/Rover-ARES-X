# Verificación visual del S6 y estado de la interfaz (al 14/11/2026)

Documento para retomar la interfaz 3D de ARES-X. Solo lo que la interfaz hace hoy; lo que espera al motor va marcado como tal.

## Estado al 14/11 (cierre del día)

- **Primer paso de mañana:** con turno del Orquestador, comprobar `http://127.0.0.1:8899/api/estado` (RAM y CPU por debajo del 80 %) y después mi turno de navegador: pasada completa de **ARX-43** (design-review) y la verificación visual de todo el S6 a 960×540 (tabla de abajo). Antes: `node docs/capturas/comprobar_referencias.mjs` (OK, versión `r14`).
- **Verificado en Chrome por Maestro New:** E5, O1, O2, O5, O6, O7, O8, O9 (incluido el apuntado al id del dron), ARX-77.
- **Sin verificar en Chrome:** ARX-41 (laboratorio), O12 (avisos del motor), O11 (versión `r14`; la recarga depende de que el motor envíe `Cache-Control: no-cache` en `/static/`).

- **Cómo retomar:** abrir una sesión nueva en la carpeta `ares_x`.

- **Código:** `api/static/index.html`, `app.js`, `adaptador.js`, `laboratorio.js`, `efectos.js`, `moviles.js`. Sintaxis OK con `node`; referencias OK con `node docs/capturas/comprobar_referencias.mjs`.
- **Rendimiento:** Maestro New midió 120 FPS con RTX 4060 a 1080p en las rondas 1 a 5 (mínimo 118). Las lecturas bajas fueron con la ventana oculta, no por el juego.
- **Verificado en Chrome del usuario** (rondas 1 a 7, informe interno de la ronda de FPS): selector de planeta solo con el nombre; «Escenario» quitado; «Misiones seguidas»; «Tamaño del mapa»; bloque automático con la cadena real; cadena automática ×3 con veto en las tres misiones; pantalla de meta combinada; salto de 3 s entre misiones; aviso de motor lento sin falsos positivos por «fin»; aviso de avisos cerrados al crear partida (N9).
- **Pendiente de verificación en Chrome:** lo que no aparece como verificado arriba: N11 («Confirmar» de la meta), el residual de N8 (aviso tras «replanificar»), E4 (error del motor). ARX-76 (objetivos opcionales) pasó en la ronda 11, como ARX-75.

## Interruptores de datos (`api/static/adaptador.js`)

| Interruptor | Valor | Qué significa |
|---|---|---|
| `FUENTE_MOTOR.planetas` | `true` | `GET /planetas` real |
| `FUENTE_MOTOR.moviles` | `true` | `GET /moviles` real |
| `FUENTE_MOTOR.objetivos` | `true` | `GET /objetivos` real. Sin partida (409), el bloque se oculta |
| `FUENTE_MOTOR.escenarios` | `false` | `/escenarios` responde 404. La interfaz no lo usa para el bloque automático |
| `TEMPERATURA_PRUEBA` | `true` | Cuarta variable del laboratorio del difuso (temperatura) con datos de prueba |

Regla: los datos de prueba solo se muestran con `?demo=estados` (estados del indicador). Ver trampas.

## Lista de comprobación del S6

Hacerla de una sola vez, a **960×540**, con el turno del navegador. Script: `docs/capturas/s6_verificacion.py` (regenera las capturas; no ejecutar sin turno).

Los nombres de captura de la tabla son orientativos: el script actual no tiene una captura por cada fila. Si una fila no tiene captura, se verifica leyendo la pantalla y se anota en el informe.

| ID | Qué mirar | Captura esperada |
|---|---|---|
| ARX-52 | Asistente: «Tipo de vehículo»; semilla vacía con «aleatoria»; niveles con nombre (Muy fácil, Fácil, Medio, Difícil, Hardcore) | `s6_01_asistente.png` |
| ARX-52 | Tras iniciar sin semilla: resumen y HUD muestran la semilla que eligió el servidor | `s6_02_partida.png` |
| ARX-56 | Panel: 1 · Mapa, 2 · Modo de control, 3 · Simulación, 4 · Intervención; botón verde «Iniciar» al final | `s6_02_partida.png` |
| ARX-54 | Descripción corta bajo «Modo de control». Opciones: Manual (con recomendaciones), Solo RNA, Solo difuso, Solo AG, Híbrido (valor `automatico`) | `s6_03_manual_recomendaciones.png` |
| ARX-62 | Cámara en 3.ª persona; «Mapa» desde arriba; «Todo» muestra el mapa completo; arrastrar la suelta | `s6_04_camara.png` |
| ARX-63 | Registro lateral con 10 entradas; con 11, sale la primera (animación) | `s6_05_registro.png` |
| Solape | Con intervención activa, el aviso (top 300 px) no tapa el registro (top 56 px) | `s6_06_intervencion.png` |
| ARX-61 | Esc abre la pausa solo durante una partida; en la configuración no hace nada | `s6_07_pausa.png` |
| ARX-60 | Carga: «Preparando el mapa…» hasta la respuesta del motor; después 3, 2, 1 y «¡Comenzamos!» | `s6_08_carga.png` |
| ARX-74 | Selector «Planeta» solo con el nombre; el vehículo cambia solo al elegir planeta. Sin selector «Escenario» | `s6_01_asistente.png` |
| ARX-74 | Meta combinada: grupos «Mapa» (Repetir mapa / Otro mapa) y «Dificultad» (5 escalones con ícono). Nada actúa al pulsar; «Confirmar» verde; «Salir al menú inicial» rojo | `s6_09_meta.png` |
| N11 | «Confirmar» crea la partida con lo elegido y cierra la meta y los avisos | `s6_09_meta.png` (antes y después) |
| ARX-67 | HUD «Objetivos» con progreso real; sin partida, el bloque no aparece | `s6_02_partida.png` |
| ARX-41 | Laboratorio difuso: cuarta curva (temperatura) con la curva real del motor; el deslizador va de −80 a 80 °C; sin la curva, el universo se oculta | `s6_13_difuso.png` |
| ARX-76 | Condiciones con `obligatorio: false` como «(opcional)» en tono suave. El motor ya lo envía: false en Muy fácil y Fácil, true en Medio. Sin el campo, obligatorias | `s6_09_meta.png` |
| ARX-77 | Bloque automático: pasos (mediana), batería final (mediana) y replanteos (total y por misión) de la cadena; la pantalla final muestra lo mismo | `s6_10_automatico.png` |
| ARX-65 | Automático ×3: intermedias saltan a los 3 s sin meta; la última abre la meta con el resumen de la cadena arriba | `s6_10_automatico.png` |
| N6 / N8 | Aviso «El motor no responde a tiempo» solo con timeout real (más de 2 s). No sale en pasos «replanificar» ni al terminar una misión | `s6_11_motor_lento.png` (solo si sale) |
| N8 residual | Tras «replanificar» no hay aviso; al terminar una misión no parpadea nada antes de la carga | — |
| E4 | Error 500 del motor: «El motor no respondió» con Reintentar, Reiniciar partida y Volver al menú | — (provocar el 500 solo si el motor lo permite sin afectar a 8765) |
| N10 | Cadena con veto: cada misión manda `{"modo":"automatico","veto":true}` | — (ver peticiones) |
| N9 | Con un aviso abierto, crear una partida lo cierra | — |
| Tamaño | Pequeño 20×30, Mediano 30×45, Grande 40×60 (por defecto). Escena y «Todo» escalan | `s6_12_tamano.png` |
| Calor | Sin `?demo=estados` el medidor no aparece en el HUD | — |

## Antes de empezar

- Regla de turnos unificada: lo pesado empieza solo con RAM y CPU por debajo del 80 % en `http://127.0.0.1:8899/api/estado`, y siempre con turno del Orquestador. Cuidado propio: CPU por debajo del 60 % antes de abrir el navegador.
- Un solo navegador sin ventana; cerrarlo al terminar (`$B stop`) y comprobar 0 procesos headless.
- Pedir confirmación del Orquestador de que OPS-11 terminó (turno de navegador).
- No crear partidas en 8765 mientras el usuario prueba. Las pruebas que las creen van en otra instancia (otro puerto, nunca 8000).
- Medir FPS con la ventana visible (Chrome frena a 1 FPS una ventana oculta).

## Trampas conocidas

- **Reemplazos por marcas de texto** (`s.index(...)`) pueden borrar funciones enteras. Tras cada parche: `node` de sintaxis y `comprobar_referencias.mjs`. Así se rompieron `adaptador.js` y `nuevaDesdeMeta` (N11).
- **Temporizadores globales** se solapan con el intervalo de reproducción (450 ms). Un solo `/paso` en vuelo (`pasoEnVuelo`); cada paso arma y cancela su propio temporizador.
- **Ids que ya no existen:** `menu-escenario` (sección «Escenario» quitada), `meta-nivel` y `meta-cambiar` (sustituidos por la meta combinada). Los scripts de prueba que los usen fallarán. `#error-menu` (aviso de error del motor) y `#motor-menu` (aviso de motor lento) son avisos distintos; cada botón cierra su propio aviso, y N9 hace que crear una partida cierre todos.
- **Medidor de calor (ARX-51):** oculto fuera de `?demo=estados` (interruptor `CALOR_MOTOR = false` en `app.js`). Cuando ARX-50 publique la temperatura interna, poner `CALOR_MOTOR = true` y cambiar `calorPrueba()` por el campo real de `/estado`.
- **Clic por coordenadas** falla tras un cambio de zoom o de ventana. Hacer clic por identificador.
- **Lecturas de la página con `fetch` encadenados** pueden colgarse si el motor está atascado. Consultar el motor por fuera con `curl -m 8`.
- **`?demo=estados`** es la única ruta con datos de prueba del indicador de estados.

## Pendientes

- **ARX-43 (diseño B+) y verificación visual del S6:** en mi turno de navegador (primer paso de mañana).
- **O11:** el motor debe enviar `Cache-Control: no-cache` en `/static/`. Mientras tanto, la versión `?v=r14` ya fuerza los archivos nuevos al cambiar la versión.
- **ARX-34 y ARX-36:** el código está; falta el motor (eventos en `/moviles` y estados nuevos).
- Verificación visual de todo el S6 (tabla de arriba) en el turno de navegador.
- **Medidor de calor (ARX-51):** oculto hasta que ARX-50 exponga la temperatura (`CALOR_MOTOR`).
- **Peligros por planeta (ARX-51):** lava, hielo, arena densa y lluvia dependen de ARX-50 y ARX-57 (`docs/PLAN_PLANETAS.md`). Hoy solo está el aspecto de los ocho planetas.
- **Objetivos opcionales (ARX-76):** el motor ya envía `obligatorio` en `/objetivos` (Maestro lo vio a las 15:55: false en Muy fácil y Fácil, true en Medio). Falta verlo en el navegador. Sin el campo, la interfaz lo trata como obligatorio.
- **N1 verificado:** Maestro New, sexta ronda: el verde en la primera reproducción tras cargar desde la pantalla de inicio mantuvo la partida (831245) y no salió ningún `POST` nuevo.
- **N7 (motor):** la misión se queda sin final al llegar al refugio con objetivos pendientes (acción «fin», estado EXPLORACION). La interfaz muestra «La misión terminó sin resultado» y no encadena.
- **ARX-43 (diseño B+):** última auditoría 2,98 (B). Sin cerrar.
- **ARX-41 (cuarta curva del difuso):** cerrada en código. El motor publica la curva de temperatura (universo −80…80 °C, reglas R10 y R11; comprobado con `GET /difuso`). La curva de prueba solo se usa con `?demo`. Falta verla en el laboratorio del navegador.
- **ARX-77 (estadísticas de la cadena):** mediana de pasos, mediana de batería final y replanteos (los «replanificar» de `/paso`). Sin `/escenarios`: el adaptador ya no lo pide. Falta verlo en el navegador.
- **ARX-36 (indicador de estados):** cubre los estados del motor, incluido `SIN_RUTA` (añadido). Falta verlo en el navegador.
- **ARX-34 (animaciones de móviles y eventos):** `moviles.js` ya consume `eventos_del_paso`; la muestra actual viene vacía, así que no hay evento que animar todavía.
- **ARX-51 (peligros y medidor de calor):** esperan ARX-50/57. Comprobado con `GET /estado`: aún no hay temperatura interna. El medidor sigue oculto.
- **Estaciones de recarga (ev3-d45):** esperan al motor. Comprobado con `GET /mapa`: aún no hay campo de recargas.
- **`/escenarios` (404):** la interfaz no lo usa. Cuando el motor lo publique, cambiar `FUENTE_MOTOR.escenarios` solo si el bloque lo necesita.
