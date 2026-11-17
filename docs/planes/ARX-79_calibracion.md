# ARX-79 · Calibración de la garantía en el mapa grande

Plan: `docs/planes/ARX-79_garantia_grande.md` (worktree de interfaz). Rama `feat/arx-79-garantia`, base `22dc129` (con ARX-90, ARX-91 y ARX-28c integrados).

## 79a · Medición base (garantía actual, `garantia=True`)

Estado: **medida** (script `scripts/medir_garantia.py`, rama `feat/arx-79-garantia` en `fb7d3f2`/`c418073`, código de `22dc129`, sin cambios en `juego/partida.py`). Log: `docs/planes/mediciones/medicion_79a.log`. Datos por partida: `docs/planes/mediciones/medicion_garantia_grande.json` y `..._pequeno.json` (100 partidas cada uno).

Condiciones: **con eventos espontáneos por defecto** (ev3-d66; la partida del juego tal cual; `--sin-eventos` los desactiva, para comparar), modo automático por la API en proceso (`TestClient`, sin servidores), semillas 1 a 20 por nivel, tope de 500 pasos, la misma semilla en ambos tamaños. Tiempos: grande 1077 s, pequeño 188 s, un proceso.

Columnas: **Éxito** = victorias/20; **Pasos** = media y mediana solo de las victorias; **Causa de la derrota** = la que asigna `causa()` en el script (ver nota de método).

### Mapa grande (40×60)

| Nivel | Éxito | Pasos (media) | Pasos (mediana) | Causa de la derrota (número de partidas; semillas cuando el log las da) |
|---|---|---|---|---|
| 1 Muy fácil | 14/20 | 78,9 | 79,5 | batería 0 con sitios pendientes: 6 (semillas 5, 8, 9, 15, 18, 19) |
| 2 Fácil | 12/20 | 74,9 | 74,5 | batería 0 con sitios pendientes: 6; FRACASO (otra): 1; caza sin batería: 1 (semillas 1, 4, 6, 8, 9, 11, 13, 19) |
| 3 Medio | 0/20 | - | - | batería insuficiente para sitios restantes: 15; batería 0 con sitios pendientes: 3; caza sin batería: 2 |
| 4 Difícil | 0/20 | - | - | batería insuficiente para sitios restantes: 18; batería 0 con sitios pendientes: 2 |
| 5 Hardcore | 0/20 | - | - | batería insuficiente para sitios restantes: 18; batería 0 con sitios pendientes: 1; SIN_RUTA: 1 |

En los niveles 3 a 5 el log no lista las semillas; cada partida está en el JSON con su causa.

### Mapa pequeño (20×30), control

| Nivel | Éxito | Pasos (media) | Pasos (mediana) | Causa de la derrota |
|---|---|---|---|---|
| 1 Muy fácil | 20/20 | 48,2 | 48,0 | - |
| 2 Fácil | 20/20 | 49,0 | 49,0 | - |
| 3 Medio | 20/20 | 57,1 | 56,0 | - |
| 4 Difícil | 20/20 | 53,5 | 52,0 | - |
| 5 Hardcore | 20/20 | 54,5 | 54,5 | - |

### Método de la causa y lectura

- La causa sale del estado final de la partida y del aviso del motor. «Batería insuficiente para sitios restantes» es el aviso que emite el motor en `juego/partida.py:581`: el mapa real tiene ruta a los sitios pendientes, pero su longitud más el margen de 15 % supera la batería. El script solo clasifica ese aviso; no lo inventa.
- Semilla 1 de Medio (grande): FRACASO en el paso 68, batería 19, 0 de 4 sitios visitados, 0 drones vivos al final, con el aviso «Batería insuficiente…». Semilla 2 de Medio (grande): FRACASO en el paso 71, batería 25, 0 de 4 sitios, 0 drones vivos, mismo aviso.
- ¿Afecta la caza de drones obligatorios desde el nivel 3? En estas dos semillas no hay drones vivos al final, así que la caza terminó; no está medido en qué paso gastó la batería. La caza solo aparece como causa directa en 2 partidas de Medio y ninguna de Difícil ni Hardcore. No lo afirmamos más allá de eso.
- ¿La línea base está mal medida? No se ve en los datos: la medición corre la partida del juego (mismo bucle de `/paso`), y el fracaso lo declara el motor. Lo que muestra es que la garantía actual no garantiza ganar en el grande desde Medio, que es el problema que ARX-79 quiere atacar. Las cifras del pequeño (20/20 en todos los niveles) son el control.

Referencias previas (no son esta medición): QA 17/11 en `ab46b4a`: Muy fácil grande pierde las semillas 8, 9 y 12; Medio grande las 1 a 4 (la tabla de hoy da 6 derrotas en Muy fácil y 8 en Fácil, con otras semillas). ARX-58: Muy fácil grande 80 % con mediana 77 pasos (hoy 70 %, mediana 79,5).

## 79d · Medición final

Pendiente (tras 79b y 79c). Criterio: Muy fácil y Fácil grande ≥ 95 %; Medio ≥ 85 %; pequeño sin empeorar.

## Criterio de la batería proporcional al tamaño (ev3-d75 A) · escrito ANTES de medir 79d

Decisión del Maestro: la batería inicial del mapa grande pasa a ser proporcional al tamaño del mapa. Este criterio se fija antes de cualquier medición nueva.

- **Razón de longitud de ruta R** = mediana de pasos de las victorias del grande (todos los niveles con victorias: 1 y 2) ÷ mediana de pasos de las victorias del pequeño (todos los niveles). Datos: `docs/planes/mediciones/medicion_garantia_grande.json` y `..._pequeno.json` (79a).
  - Grande: 26 victorias, mediana 77,5 pasos. Pequeño: 100 victorias, mediana 52,0 pasos.
  - **R = 77,5 ÷ 52,0 = 1,49** (la media da 1,47; se usa la mediana, como en 79a).
- **Batería inicial del grande** = batería del nivel (100 − 4·(nivel − 1), como hoy) × R. Por nivel (100, 96, 92, 88, 84 × 1,49): 149 (nivel 1), 143 (2), 137 (3), 131 (4), 125 (5).
- **Pequeño y congelado no cambian**: R solo se aplica al tamaño grande (40×60); el pequeño (20×30) y el congelado (garantia=False, 20×30) quedan con su batería actual. Se verifica por hash.
- **Aviso «Mapa sin garantía de victoria»**: se queda.
- **Límite conocido de R**: sale de victorias, y las del grande son solo de niveles 1 y 2 (lo fácil). Por eso R puede subestimar lo que hace falta en niveles 3 a 5; no se ajusta hasta llegar al 100 %.
- **Regla de medición (79d)**: 20 semillas por nivel en el grande, tasa publicada tal como salga. No se ajusta R hasta llegar al 100 %. Si a las 15:00 no está aprobada por QA, se aplica el repliegue D (mapa pequeño por defecto).

## 79d · medición final con batería proporcional (ev3-d75 A) · código fc9693a

Medido con `scripts/medir_garantia.py` (20 semillas por nivel, niveles 1 a 5, con eventos por defecto, tope de 500 pasos). Ficheros: `docs/planes/mediciones/medicion_79d_grande.json` y `..._79d_pequeno.json`. Las cifras se leen de esos JSON; no se han ajustado.

**Grande (40×60), batería inicial 149, 143, 137, 131, 125 por nivel**

| Nivel | Éxito | Causas de las derrotas |
|---|---|---|
| 1 | 20/20 | — |
| 2 | 20/20 | — |
| 3 | 10/20 | caza sin batería 4, batería 0 con sitios pendientes 2, batería insuficiente 2, 12 pasos parado (regla 79c) 2 |
| 4 | 6/20 | caza sin batería, batería 0, batería insuficiente, faltan drones |
| 5 | 4/20 | caza sin batería, batería 0, batería insuficiente, faltan drones, SIN_RUTA |

Totales de derrotas grande: caza sin batería 22, batería 0 con sitios pendientes 7, batería insuficiente 4, faltan drones (el refugio queda bloqueado) 2, impacto de meteorito 2, 12 pasos parado 2, SIN_RUTA 1. Suman 40.

**Pequeño (20×30), batería 100, 96, 92, 88, 84 (sin cambios)**: 20/20 en todos los niveles, igual que 79a.

**Regla de 79c (límite de 12 pasos parado cazando, ev3-d76 condicionada)**
- Partidas que terminan por «12 pasos parado»: **2 de 200** (1 % del total), las dos en el nivel 3 del grande (semillas 13 y 16). Sobre el grande solo, 2 de 100 (2 %).
- Umbral de ev3-d76: 2 % o menos. **Queda dentro del umbral**, por lo que la regla se mantiene como está. Con más de 2 %, la alternativa era abandonar la caza, replanificar y no volver a ese dron durante N pasos, con FRACASO solo tras K abandonos.

**Aviso «Mapa sin garantía de victoria»** (las filas guardan los últimos 3 avisos, así que es un mínimo): nivel 3, 7 partidas; nivel 4, 12; nivel 5, 8.

**Lectura.** La dificultad crece con el nivel en el grande (100 % en 1 y 2, 50 % en 3, 30 % en 4, 20 % en 5), y el pequeño no cambia. La tasa se publica tal como sale, sin ajustar R hasta llegar al 100 %, según la regla del criterio. Cada derrota del grande tiene causa registrada. La batería proporcional sí da victorias en el grande (en 79a, 0/20 en niveles 3 a 5).

**Límites conocidos**
- R (1,49) sale de victorias de niveles 1 y 2; puede subestimar lo que hace falta en niveles 3 a 5.
- La regla de 79c es un límite de tiempo de la caza: 12 pasos seguidos con el rover en la misma celda, sin contar fallos de sensor. Corta un bucle, no resuelve la caza. Un arreglo de fondo (rodear o forzar el avance) cambia el juego y queda como decisión del Maestro.
- El aviso «sin garantía» se queda, como pidió el Maestro.
