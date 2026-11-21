# ev3-d88 B · aborto térmico: constante de tiempo y tolerancia (criterio escrito ANTES de medir)

Rama feat/m13-termico desde a0bf109. Frente propio: no toca `simulador.py` ni genetico.py. Toca solo `juego/termico.py` (constantes y la bandera). Funciones que usan el aborto, sin cambios de código en ellas:
- `juego/partida.py`: `Partida._tick_termico` (aborto: `termico.ABORTO_TERMICO_ACTIVO and self.termico.debe_abortar`), `Partida.__init__` (inyección de T_int al difuso, `_inferir_con_temperatura`) y `Partida.t_int` / `pasos_sobre_tolerancia`.
- `juego/termico.py`: `Termico.paso`, `Termico.debe_abortar`, `es_sombra`.
La B de la AG (envoltorio de `_ag_con_todos_los_sitios`) queda intacta: no se toca ninguna de sus funciones.

## Supuestos de escala (declarados)
- 1 paso de simulación = 1 celda recorrida = **10 s** de tiempo real (rover a ~0,1 m/s, celda de 1 m). Supuesto de simulación.
- **Orden de escritura (declarado):** este plan se escribió DESPUÉS de ver la línea base M13 (53637e0: con K_CALOR 0,08, las partidas que se ganan abortan en los pasos 7 a 10). El supuesto «1 paso = 10 s» es un supuesto de escala nuevo, no derivado del código: de él sale τ = 100 pasos y, con eso, K_CALOR = 0,01.
- **Secuencia real:** línea base a las 23:04; plan a las 23:08, con el supuesto de 10 s nuevo.

## Constantes y justificación física
1. **Constante de tiempo térmica (inercia del chasis)**: τ = 1/K_CALOR, medida en pasos. La masa térmica del chasis (aluminio con aislamiento, alguna decena de kilos de estructura y electrónica) tarda del orden de **15 a 20 minutos** en acercarse a la temperatura de su entorno. Con 10 s por paso, eso son ~100 pasos: **τ = 100 pasos ⇒ K_CALOR = 0,01**. Hoy K_CALOR = 0,08 (τ = 12,5 pasos ≈ 2 min): en Mercurio de día el chasis pasaría de 20 °C a 60 °C en ~1–2 pasos, algo que una masa de esa escala no hace. **Esta es la única corrección**, y su criterio es físico, no de resultados.
2. **Tolerancia del equipo por planeta**: el equipo es el mismo en ambos planetas, así que la tolerancia es la del fabricante del hardware: **60 °C** (igual que `difuso.TEMPERATURA_TOLERANCIA`). Se deja como tabla `TOLERANCIA_POR_PLANETA = {"Mercurio": 60, "Venus": 60}` para que un planeta con otro equipo se pueda declarar después; no se cambia hoy.
3. **Exceso sostenido**: el aborto exige **más de 5 pasos seguidos** por encima de la tolerancia (`PASOS_MAXIMOS_SOBRE_TOLERANCIA = 5`, ya vigente). Eso es ~50 s sostenidos; un pico breve no aborta porque el contador se reinicia al bajar de la tolerancia. **Sin cambios.**
4. **Aborto activo**: `ABORTO_TERMICO_ACTIVO = True` (decisión ev3-d88 B). Sin cambios en `T_AMB_POR_PLANETA` (430 °C Mercurio de día, 464 °C Venus) ni en `T_SOMBRA`, `GANANCIA_EXPOSICION`, `REDUCCION_BLINDAJE`.

## Única corrección, declarada
- `K_CALOR`: 0,08 → **0,01**. Es la única constante que cambia de valor respecto a hoy (además de activar la bandera).

## Qué cuenta como «se gana hoy» y «abortada» (el mismo criterio del barrido M13)
- Se gana hoy: EXITO con la bandera apagada, con la configuración de hoy (K_CALOR = 0,08).
- Abortada: con la nueva configuración, la misma partida (semilla, planeta, nivel, tamaño 40×60) termina en `MODO_SEGURO`.
- Si no queda ninguna partida ganable con la nueva configuración, se repliega a **A** (solo aviso, bandera apagada), y se declara.

## Medición
- El mismo barrido que M13 (40×60, 20 semillas por nivel, Mercurio y Venus), con turno. Se publica tal como salga, incluidas las cifras antes (M13) y después.

## Condición de revisión (Orquestador, antes de codificar)
- `K_CALOR` y `ABORTO_TERMICO_ACTIVO` son GLOBALES. T_int alimenta al difuso (`_inferir_con_temperatura`, cuarta entrada de ev3-d40), así que cambiar `K_CALOR` puede mover las velocidades del difuso también en Marte, y con eso el congelado y el exigente.
- Criterio: el **congelado (`d6fb9079…`) y el exigente de 4 sitios deben quedar IDÉNTICOS por hash**. Se comprueba al codificar, antes de pedir turno.
- Si cambian, **se para** y se trae la fila afectada. **No se restringe `K_CALOR` por planeta** para esquivarlo: eso sería una segunda decisión.

## Resultados (medición con turno, Esp_QA libre a 23:36; inicio 23:38, fin 00:09)
Script: `scripts/barrido_termico_B.py` (variante de M13: línea base con K_CALOR 0,08 y bandera apagada; encendida con K_CALOR 0,01 y aborto activo). Datos: `docs/planes/mediciones/barrido_termico_B.json` y `.log`.
Control: la línea base reproduce la tabla M13 de 53637e0, rotulada **modelo anterior, K_CALOR 0,08** (20/20, 20/20, 19/20, 17/20, 15/20 en Mercurio; igual en Venus).

Se gana hoy · abortadas con la configuración nueva · paso medio del aborto · T interna media y máxima:
| Planeta | Nivel | Gana hoy | Abortadas | Siguen ganando | Paso medio aborto | T media | T máx |
|---|---|---|---|---|---|---|---|
| Mercurio | 1 | 20/20 | 20 | 0 | 22,8 | 72,8 | 79,8 |
| Mercurio | 2 | 20/20 | 20 | 0 | 24,4 | 74,4 | 79,9 |
| Mercurio | 3 | 19/20 | 19 | 0 | 25,4 | 74,7 | 80,0 |
| Mercurio | 4 | 17/20 | 17 | 0 | 24,5 | 74,4 | 80,1 |
| Mercurio | 5 | 15/20 | 15 | 0 | 30,4 | 73,7 | 79,5 |
| Venus | 1 | 20/20 | 20 | 0 | 20,6 | 73,2 | 82,1 |
| Venus | 2 | 20/20 | 20 | 0 | 22,6 | 74,8 | 81,4 |
| Venus | 3 | 19/20 | 19 | 0 | 23,5 | 75,2 | 81,8 |
| Venus | 4 | 17/20 | 17 | 0 | 22,9 | 74,5 | 81,7 |
| Venus | 5 | 15/20 | 15 | 0 | 27,0 | 74,1 | 81,5 |

Lectura: el resultado fue contrario a cualquier ajuste a favor: **0 de 10 casos siguen ganando** con el aborto activo. Todas las partidas que se ganan hoy abortan con la configuración nueva, entre los pasos 20 y 30. Por el criterio del plan aplica el repliegue a A (sección «Repliegue a A»).

## Repliegue a A (declarado)
Criterio del plan: si con la nueva configuración no queda ninguna partida ganable, se repliega a A. Con K_CALOR 0,01 y el aborto activo quedan **0 ganadas** en los diez casos (Mercurio y Venus, niveles 1–5). Se aplica el repliegue.
- `ABORTO_TERMICO_ACTIVO = False` (sin aborto). `K_CALOR = 0,01` se queda: es la corrección física declarada, y el congelado y el exigente de 4 sitios salen idénticos por hash y por fila (20 semillas).
- **Opción A (solo aviso):** cuando T_int supera la tolerancia de forma sostenida (más de 5 pasos seguidos), se añade el aviso con código `T-SOBRE-TOLERANCIA` a los avisos de la partida y a la bitácora (motivo `T-SOBRE-TOLERANCIA`), una vez por episodio. Sin MODO_SEGURO. Lo fijan `test_bandera_apagada_por_defecto_sin_aborto_y_con_aviso`.
- Limitación: el aviso llega a la interfaz por la lista de avisos (`/estado.avisos`), que la app muestra al aparecer; no hay un elemento nuevo en el panel.
- Resultado que lo motiva (con aborto): paso medio del aborto 20,6–30,4; T máxima 79,5–82,1 °C.
- Sin el aborto, el rover no tiene cómo enfriarse. Queda como trabajo futuro: sombra, refugio o ciclo día-noche.
- Efecto de la corrección: K_CALOR pasa de 0,08 a 0,01 (factor 8). La serie de `/estado.temperatura_interna` y el medidor del HUD suben unas 8 veces más lento.

Corrección de una lectura: en un mensaje previo se dijo que no hacía falta repliegue. Era incorrecto: el criterio aplica cuando no queda ninguna ganable con la nueva configuración, y con el aborto no queda ninguna.
