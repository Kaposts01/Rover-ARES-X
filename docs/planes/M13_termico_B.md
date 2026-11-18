# ev3-d88 B · aborto térmico: constante de tiempo y tolerancia (criterio escrito ANTES de medir)

Rama feat/m13-termico desde a0bf109. Frente propio: no toca `simulador.py` ni genetico.py. Toca solo `juego/termico.py` (constantes y la bandera). Funciones que usan el aborto, sin cambios de código en ellas:
- `juego/partida.py`: `Partida._tick_termico` (aborto: `termico.ABORTO_TERMICO_ACTIVO and self.termico.debe_abortar`), `Partida.__init__` (inyección de T_int al difuso, `_inferir_con_temperatura`) y `Partida.t_int` / `pasos_sobre_tolerancia`.
- `juego/termico.py`: `Termico.paso`, `Termico.debe_abortar`, `es_sombra`.
La B de la AG (envoltorio de `_ag_con_todos_los_sitios`) queda intacta: no se toca ninguna de sus funciones.

## Supuestos de escala (declarados)
- 1 paso de simulación = 1 celda recorrida = **10 s** de tiempo real (rover a ~0,1 m/s, celda de 1 m). Supuesto de simulación.

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
