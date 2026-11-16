# ARES-X · Especificación del MVP 3D (ARX-02)

Estado: borrador de trabajo, plazo viernes 13/11. Decisiones de base: ev3-d30 A (alcance MVP), ev3-d29 B
(ocho direcciones), ev3-d32 A (prueba de intervención causal).

Nota de método: la skill `/spec` es interactiva y aquí no se puede preguntar en el chat. Esta especificación
se redactó directamente desde la asignación del orquestador y el código existente. Los supuestos están marcados
como **[supuesto]**. Si el usuario corrige alguno, se actualiza este documento antes de ARX-03.

## 1. Alcance

Incluido en el MVP:
- Mundo 3D en el navegador (Three.js) con un mapa de Marte de 20x30 celdas, generado por semilla.
- Motor en Python (FastAPI) que reutiliza `simulador`, `rna`, `difuso`, `genetico` e `integracion` sin
  cambiarlos, a través de `juego/partida.py`.
- Navegación manual en ocho direcciones.
- Modo automático con supervisor que combina RNA, difuso y AG, con motivos visibles (ev3-d07).
- Disparo del rover con cooldown, munición y daño.
- Un tipo de enemigo ficticio con máquina de estados (patrulla, alerta, persecución, ataque).
- Panel de decisiones con las entradas y salidas de cada técnica.
- Prueba de intervención causal (ARX-10, ev3-d32 A).

Fuera del MVP (se documenta como limitación en ARX-08):
- Otros planetas y modo sonda.
- Más de un tipo de enemigo.
- Eventos de sismo y tormenta en el modo 3D (la tormenta y la noche existen en el motor de partida).
- Video y defensa (los graba el estudiante).

## 2. Arquitectura

```
navegador (Three.js, static/index.html)
    │  HTTP JSON
    ▼
backend FastAPI (api/servidor.py)  ──► juego/partida.py (Partida) ──► simulador, rna, difuso, genetico, integracion
    │
    └─► juego/combate.py (disparo y NPC, capa de juego)
```

- Una sola partida por proceso (estado en memoria). Se reinicia con `POST /partida`.
- La capa de combate y la conducción por modo viven en `juego/`. No modifican los módulos congelados.
- **Excepción autorizada (ARX-10, ev3-d32 A):** se agrega un gancho de intervención en `integracion.py`
  (parámetro opcional `intervencion_rna`, por defecto `None`) y, si hace falta, en `difuso.py`. Solo sirve
  para la prueba causal; sin intervención el comportamiento es idéntico al de antes.

## 3. API (JSON)

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| GET | `/estado` | — | `{semilla, nivel, estado, posicion, bateria, puntaje, modo, ambiente, objetivo, rumbo_sugerido, npcs, municion, cooldown}` |
| POST | `/partida` | `{semilla, nivel}` | `/estado` |
| POST | `/mover` | `{rumbo}` con `N,S,E,O,NE,NO,SE,SO` | `{movido, motivo, estado}` |
| POST | `/paso` | — | paso de la IA: `{accion, motivos, estado}` |
| POST | `/modo` | `{modo}` con `manual, rna, difuso, ag, automatico` | `/estado` |
| POST | `/disparo` | `{rumbo}` | `{impacto, npc_golpeado, municion, cooldown}` |
| POST | `/evento` | `{nombre}` con `barranco, falla_sensor, bateria_baja, tormenta, noche` | `{ok, detalle}` |
| GET | `/paneles` | — | entradas y salidas de RNA, difuso, AG y supervisor, con el motivo |
| POST | `/intervencion` | `{tecnica, valor}` (solo ARX-10, para la prueba causal) | `{ok}` |

Códigos de error: 400 si la entrada es inválida; 409 si la partida ya terminó; el cuerpo de la respuesta
siempre trae `motivo`, nunca un traceback.

## 4. Escena 3D

- Terreno: plano de 20x30 celdas; cada celda es un bloque bajo o alto según su tipo.
  Obstáculo: roca (cubo gris rugoso). Barranco: hueco rojo con borde. Sitio científico: cristal azul que gira.
  Refugio: base con un poste verde. Ruta planeada: línea de puntos amarilla sobre el suelo.
- Rover: cuerpo con cuatro ruedas, panel solar y faro hacia el rumbo.
- NPC: dron ficticio (esfera con dos aletas). No representa a ninguna persona ni organización real.
- Cámara: perspectiva desde arriba con inclinación de 55°; el usuario puede girarla con el ratón.
- Paneles 2D superpuestos: estado, batería, puntaje, municion, modo y el panel de decisiones.

## 5. Modos de control

| Modo | Quién decide el movimiento | Qué se muestra |
|---|---|---|
| manual | El jugador (teclas y ratón) | Sugerencia de la IA como flecha (TAB) |
| rna | La RNA: el vecino de mayor p_libre que acerca al objetivo (ARX-11) | Probabilidades de libre, obstáculo y barranco |
| difuso | El difuso: avanza por BFS con la velocidad difusa; espera y rodea si la velocidad es baja (ARX-11) | Velocidad y reglas activadas |
| ag | El AG: sigue su ruta y replanifica solo si queda bloqueada (ARX-11) | Ruta candidata y desglose del fitness |
| automatico | La IA: pseudociclo completo con supervisor | Motivos `V-…` / `D-…` por paso |

**Veto de seguridad (ARX-11, ev3-d35 pendiente de confirmación):** interruptor, encendido por defecto. Con él, los modos rna, difuso y ag no avanzan hacia una celda que la RNA (barranco u obstáculo > 0,5) o el LIDAR marcan como peligrosa (motivos `V-SEGURIDAD-BARRANCO` / `V-SEGURIDAD-OBSTACULO`). Con él apagado, el movimiento se intenta igual y los bloqueos cuentan como colisión. Se controla con el campo `veto` de `POST /modo`.

El modo automático mantiene la regla de ev3-d07: el AG planifica una vez; el supervisor veta; el replanteo
es con BFS. **[supuesto]** El AG solo se vuelve a correr si el objetivo cambia.

## 6. Combate

- **Disparo del rover:** tecla de disparo (Espacio en el modo manual) lanza un proyectil en el rumbo actual.
  Alcance de 5 celdas. Cooldown de 2 turnos (pasos de la partida; ver nota). Munición inicial de 10 disparos. Daño de 1 por impacto.
  **Unidad de tiempo (ARX-06):** el juego es por turnos, así que el cooldown se mide en pasos, no en segundos.
  Cada acción del jugador o de la IA que consume un turno (mover, paso, disparo) descuenta 1 del cooldown.
- **NPC dron:** 3 puntos de vida. Máquina de estados:
  - `patrulla`: recorre dos celdas fijas. Pasa a `alerta` si el rover está a 6 celdas o menos.
  - `alerta`: se gira hacia el rover durante 2 s. Pasa a `persecucion` si el rover sigue a 6 o menos y
    vuelve a `patrulla` si no.
  - `persecucion`: avanza una celda por paso hacia el rover. Pasa a `ataque` si está a 1 celda.
  - `ataque`: daña 1 de batería al rover cada 2 pasos. Vuelve a `persecucion` si el rover se aleja.
- Un dron destruido (0 puntos de vida) no vuelve a aparecer en la partida.
- **[supuesto]** Los drones no atraviesan obstáculos ni barrancos.

## 7. Criterios de aceptación

1. `POST /partida` con semilla 11 devuelve un estado con posición en el inicio y batería 100.
2. Con el modo `automatico`, una partida de semilla 11 llega a `EXITO` sin colisiones ni barrancos pisados.
3. `POST /mover` con un rumbo diagonal bloqueado devuelve `movido: false` con un motivo legible.
4. Un disparo respeta el cooldown: dos disparos seguidos, sin turno intermedio, solo producen uno (el segundo devuelve 409).
5. Un dron pasa de patrulla a persecución al acercarse el rover a 6 celdas, y a ataque a 1 celda.
6. `GET /paneles` devuelve, para cada técnica, sus entradas y sus salidas con los valores actuales.
8. Todas las rutas de la API tienen pruebas pytest y ninguna devuelve un traceback al cliente.
9. Con la intervención activa (ARX-10), la prueba pytest muestra un cambio en la decisión.
10. La escena se carga en el navegador sin errores de consola en los modos manual y automático.

## 8. Plan de pruebas

| Capa | Qué | Herramienta |
|---|---|---|
| Unidad | combate (cooldown, munición, máquina de estados),  | pytest |
| API | cada ruta de la tabla, errores 400 y 409 | pytest con `TestClient` de FastAPI |
| Integración | modo automático de semilla 11 llega a EXITO | pytest |
| Interfaz | carga de la escena, modos y disparo | `/qa` o `/browse` con capturas (ARX-08) |

## 9. Riesgos y recorte

- **Plazo:** el viernes 13/11 es el límite. Si el frontend 3D no está listo, se entrega la API con una vista
  2D de respaldo (el juego pygame ya existe).
- **Qwen:** retirado del proyecto por decisión del estudiante (ev3-d37).
- **Combate:** si el tiempo no alcanza, se mantiene el disparo y el dron con patrulla y persecución; el ataque
  se deja como limitación.

## 10. Fuera de alcance (lista para el README)

Otros planetas, modo sonda, varios tipos de enemigos, eventos de sismo en 3D, video, defensa, despliegue en
internet y cuentas de usuario.
