# Tabla de 20 semillas por modo de conducción (ARX-11)

> **Provisional: esta tabla se regenera tras ARX-92** (ev3-d64 A). Las cifras son de la versión anterior a ARX-90, ARX-91 y ARX-28c, y no se reescriben a mano.

Semillas 1 a 20. Éxito = llega a EXITO. Colisiones = movimientos bloqueados por la física. Intentos a barranco = movimientos dirigidos a una celda de barranco (solo cuentan con el veto apagado, porque con el veto encendido no se intentan). Pasos = iteraciones hasta un estado terminal o 400.

Arnés: capa de juego (`juego/partida.py`, semillas 1 a 20, sin combate ni eventos). No es el mismo arnés que el experimento del notebook (`Mision` directa, 100 % de éxito para el híbrido): las dos cifras no se mezclan. El automático falla en la semilla 15 (SIN_RUTA con los tres sitios visitados), un falso positivo del sensor que ya está documentado en el INFORME.

| Configuración | Éxito | Colisiones (media) | Intentos a barranco (media) | Pasos (mediana) |
|---|---|---|---|---|
| automático (supervisor completo) | 20/20 | 0.00 | 0.00 | 43 |
| rna, veto encendido | 20/20 | 0.00 | 0.00 | 44.5 |
| rna, veto apagado | 20/20 | 0.05 | 0.00 | 44.5 |
| difuso, veto encendido | 20/20 | 0.00 | 0.00 | 43 |
| difuso, veto apagado | 20/20 | 0.35 | 0.10 | 44 |
| ag, veto encendido | 20/20 | 0.00 | 0.00 | 43 |
| ag, veto apagado | 20/20 | 0.35 | 0.10 | 43 |
