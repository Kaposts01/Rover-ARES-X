# M13 · barrido térmico: Mercurio de día y Venus (criterio escrito antes de medir)

Rama feat/m13-barrido-termico desde a0bf109. No cambia el juego: la bandera `termico.ABORTO_TERMICO_ACTIVO` se enciende SOLO dentro del script, por atributo del módulo, y se restaura al terminar.

## Escenarios
- Planetas: **Mercurio** (de día: `T_AMB_POR_PLANETA["Mercurio"] = 430 °C`) y **Venus** (`464 °C`).
- Tamaño: el **por defecto de la interfaz, grande (40×60)**.
- Niveles 1 a 5; semillas 1 a 20 por nivel; garantía activa; control automático (`avanzar_ia`); tope de 500 pasos por partida.

## Qué cuenta como «se gana hoy»
Una partida con la bandera APAGADA que termina en `EXITO`. Es la referencia de hoy.

## Qué cuenta como «abortada»
Una partida que se gana hoy (bandera apagada) y que, con la misma semilla, planeta, nivel y tamaño, con la bandera ENCENDIDA termina en `MODO_SEGURO` (aborto térmico, estado terminal). Si con la bandera encendida termina en otro estado (`EXITO`, `FRACASO`, `SIN_RUTA`), no cuenta como abortada: se publica aparte.

## Qué se publica, por planeta y nivel
- Partidas que se ganan hoy (bandera apagada).
- De ellas, cuántas se abortan (bandera encendida, `MODO_SEGURO`).
- Paso medio del aborto (media del paso en el que entra en `MODO_SEGURO`).
- Temperatura interna máxima alcanzada en la partida con la bandera encendida (°C).
- Cuántas partidas que se ganan hoy siguen ganándose con la bandera encendida.

## Nota de diseño que se publica tal cual
Con la bandera encendida, el difuso también recibe T_int (`_inferir_con_temperatura` en `partida.py`), así que la ruta puede cambiar aunque no haya aborto. Por eso se publica cuántas partidas cambian de resultado y no solo cuántas abortan.

## Reglas
- Se publica tal como sale; no se ajusta nada para mejorar cifras.
- Una medición, con turno, en segundo plano y en un proceso.
- El congelado (`d6fb9079…`) no se toca: el script no altera la evaluación congelada.
