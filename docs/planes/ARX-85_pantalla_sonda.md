# ARX-85 · pantalla de sonda (ev3-d61 A, repliegue C si no cabe)

Decisión: ev3-d61 A (Maestro, por delegación). Base: b84e640. Rama feat/arx-85-pantalla-sonda.

## Qué existe ya (evidencia)
- Modo sonda para los gigantes: `modo_planeta` = `sonda` en /estado (api/servidor.py) y la sonda 3D sustituye al rover en la escena (api/static/app.js:828, `efectos.crearSonda()`, `sondaRover`).
- El rover no puede rodar sobre un gigante: bloqueo con motivo y botón «usar sonda» (app.js:1513–1535).
- La etiqueta del HUD muestra «· sonda» (app.js:1286).
- Datos de la sonda en /estado: `temperatura_interna`, `tolerancia`, `pasos_sobre_tolerancia`, `batería`.

## Qué falta (lectura de «pantalla de sonda sin rodaje»)
- Una pantalla propia de la sonda: un panel con sus lecturas (planeta, temperatura interna y tolerancia, batería, pasos sobre tolerancia y estado de la misión), visible solo en modo sonda.
- «Sin rodaje»: en modo sonda no hay controles de rodaje ni animación de rodadura de la sonda; la sonda se muestra sin ruedas en movimiento.

## Criterio de hecho
1. Con un gigante (p. ej. Júpiter) en modo sonda, el panel de sonda aparece con las lecturas reales de /estado.
2. El panel no aparece en modo rover (Marte).
3. Ningún control de rodaje visible en modo sonda.
4. Hash del congelado d6fb9079… sin cambios; la API no cambia (solo se lee /estado).

## Repliegue C (si no cabe)
Si la pantalla completa no cabe en la ventana, se entrega solo el panel de lecturas (punto 1), sin la sonda 3D animada. **Duda abierta**: el texto de «repliegue C» está en la Bandeja y no lo tengo; esta lectura se confirma con el Orquestador antes de cerrar.
