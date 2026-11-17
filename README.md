# ARES-X · rover autónomo con IA híbrida

Simulación de un rover en Marte que combina una red neuronal (RNA), lógica difusa y un algoritmo genético (AG), con un supervisor de seguridad. Incluye un juego de escritorio y una interfaz en el navegador servida por una API FastAPI. Es una simulación ficticia con parámetros de referencia, no una misión real.

## Instalación y arranque

Requisitos: Python 3.14 o superior (probado con 3.14.5) y CPU. No necesita claves ni Docker.

```bash
python -m pip install -r requirements.txt
```

Arranque con el script (crea `.venv-ares`, instala `requirements.txt` y arranca la API en `http://127.0.0.1:8765/`):

- Windows: `.\arrancar.bat` (en PowerShell o cmd; también se puede hacer doble clic en arrancar.bat). Pruebas: `.\arrancar.bat pruebas`.
- bash: `./arrancar.sh`. Pruebas: `./arrancar.sh pruebas`.
- Otro puerto: `ARES_PUERTO=8790` (en bash: `ARES_PUERTO=8790 ./arrancar.sh`; en Windows, `set ARES_PUERTO=8790` antes de `.\arrancar.bat`).

Para las pruebas y el notebook: `python -m pip install -r requirements-dev.txt`.

- Juego de escritorio: `python juego/main.py`. Necesita `pygame-ce` con versión fija, instalado aparte: `python -m pip install pygame-ce==2.5.8`. Solo lo usa el juego de escritorio; la demo web, con `arrancar`, no lo necesita.
- Sin ventana: `python -m juego --headless --semilla 11 --pasos 300 --nivel 3`.

## Técnicas

- **RNA:** perceptrón multicapa de dos capas ocultas (32 y 16 neuronas), ReLU, tres clases (libre, obstáculo, barranco). Se entrena con mapas separados por semilla.
- **Lógica difusa:** controlador Mamdani (min-max, centroide). Entradas: distancia al riesgo, batería e inclinación. Salida: velocidad en [0, 1].
- **Algoritmo genético:** cromosoma de K puntos de paso, decodificado en una ruta con BFS. En el juego, el AG decide el orden de visita de los sitios, con la misma restricción de energía que la ejecución (entrega 2, ARX-92c). La búsqueda exhaustiva de la ruta más corta queda como respaldo, para cuando el AG no encuentra un orden viable (`juego/partida.py`, `_ag_con_todos_los_sitios`).
- **Supervisor:** aplica vetos con código de motivo (`V-…`) y replantea con BFS si el rover queda parado varios pasos.

## Mapa sin garantía

Si al generar la partida ninguna de las 59 variantes del mapa pasa la comprobación de ganabilidad, la partida muestra el aviso **«Mapa sin garantía de victoria para este nivel y tamaño»**. Se puede jugar igual, pero no hay garantía de que sea ganable.

## Ganabilidad por nivel

El mapa es ganable si hay una ruta por el terreno real que visita todos los sitios, cumple con los drones obligatorios y llega al refugio con la batería inicial. Se demuestra con cualquier semilla: no hay mapa especial.

Dos cifras distintas, y las dos son ciertas.

**Mapas con variante ganable según el estimador de garantía** (de 20 semillas):

| Nivel | Pequeño (20×30) | Grande (40×60) |
|---|---|---|
| Muy fácil | 20 | 20 |
| Fácil | 20 | 20 |
| Medio | 20 | 4 |
| Difícil | 20 | 0 |
| Hardcore | 20 | 0 |

**Partidas ganadas por el piloto automático** (de 20 semillas):

| Nivel | Pequeño (20×30) | Grande (40×60) | Batería inicial, grande |
|---|---|---|---|
| Muy fácil | 20 | 20 | 149 |
| Fácil | 20 | 20 | 143 |
| Medio | 20 | 10 | 137 |
| Difícil | 20 | 6 | 131 |
| Hardcore | 20 | 4 | 125 |

El mapa grande arranca con 1,49 veces la batería del pequeño, porque su ruta es más larga. En el grande, de Medio a Hardcore, la mayoría de las semillas nacen con el aviso «Mapa sin garantía» (16, 20 y 20 de 20 semillas, respectivamente).

**Pendiente declarado:** en los niveles Medio a Hardcore del grande, el estimador de garantía es conservador: el piloto automático gana partidas en mapas que no pasan la comprobación. Por ejemplo, en Difícil el estimador no halla variante ganable en ninguna semilla, y el piloto gana 6 de 20.

## Límites

- Solo Marte (modo rover). Los otros planetas no están implementados.
- Con 10 sitios (escenario exigente), el híbrido gana 12 de 20 semillas, frente a 14 con el vecino más cercano y 17 con 2-opt. Es una falla de búsqueda del AG, declarada en `INFORME_TECNICO.md` (§4.3); el juego normal no la tiene.
- Los valores sin fuente son supuestos de simulación, no especificaciones de misión.
- En el escenario normal la RNA es redundante con el supervisor. El detalle y las demás limitaciones están en `INFORME_TECNICO.md`.

## Documentación

- `INFORME_TECNICO.md`: arquitectura, experimentos, resultados y limitaciones. El trabajo futuro del diseño del juego está en su sección 9.
- `ARES_X_entregable.ipynb`: notebook de la entrega (se regenera con `python construir_notebook.py`).
