# ARES-X · rover autónomo con IA híbrida

Simulación de un rover en Marte que combina una red neuronal (RNA), lógica difusa y un algoritmo genético (AG), con un supervisor de seguridad. Incluye un juego de escritorio y una interfaz en el navegador servida por una API FastAPI. Es una simulación ficticia con parámetros de referencia, no una misión real.

## Instalación y arranque

Requisitos: Python 3.11 o superior y CPU. No necesita claves ni Docker.

```bash
# TODO-PAQUETE: requirements.txt con versiones fijas (incluir pygame-ce para el juego de escritorio)
pip install -r requirements.txt

# TODO-PAQUETE: script de arranque
python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765
```

Abre `http://127.0.0.1:8765/` en el navegador.

- Juego de escritorio: `python juego/main.py`.
- Sin ventana: `python -m juego --headless --semilla 11 --pasos 300 --nivel 3`.
- Pruebas: `python -m pytest -q` (la suite completa tarda varios minutos).

## Técnicas

- **RNA:** perceptrón multicapa de dos capas ocultas (32 y 16 neuronas), ReLU, tres clases (libre, obstáculo, barranco). Se entrena con mapas separados por semilla.
- **Lógica difusa:** controlador Mamdani (min-max, centroide). Entradas: distancia al riesgo, batería e inclinación. Salida: velocidad en [0, 1].
- **Algoritmo genético:** cromosoma de K puntos de paso, decodificado en una ruta con BFS. En el juego el AG corre, pero no decide el orden de visita de los sitios: lo fija la búsqueda exhaustiva de la ruta más corta (con hasta 6 sitios; con más, la voraz). TODO-ENTREGA2: actualizar si entra ARX-92.
- **Supervisor:** aplica vetos con código de motivo (`V-…`) y replantea con BFS si el rover queda parado varios pasos.

## Mapa sin garantía

Si al generar la partida ninguna de las 59 variantes del mapa pasa la comprobación de ganabilidad, la partida muestra el aviso **«Mapa sin garantía de victoria para este nivel y tamaño»**. Se puede jugar igual, pero no hay garantía de que sea ganable.

## Ganabilidad por nivel

El mapa es ganable si hay una ruta por el terreno real que visita todos los sitios, cumple con los drones obligatorios y llega al refugio con la batería inicial. Se demuestra con cualquier semilla: no hay mapa especial.

Resultados con 20 semillas por nivel (partidas ganables de 20):

| Nivel | Pequeño (20×30) | Grande (40×60) | Batería inicial, grande |
|---|---|---|---|
| Muy fácil | 20/20 | 20/20 | 149 |
| Fácil | 20/20 | 20/20 | 143 |
| Medio | 20/20 | 10/20 | 137 |
| Difícil | 20/20 | 6/20 | 131 |
| Hardcore | 20/20 | 4/20 | 125 |

El mapa grande arranca con 1,49 veces la batería del pequeño, porque su ruta es más larga. En el grande, de Medio a Hardcore, algunas semillas no tienen variante ganable y muestran el aviso de arriba.

## Límites

- Solo Marte (modo rover). Los otros planetas no están implementados.
- Los valores sin fuente son supuestos de simulación, no especificaciones de misión.
- En el escenario normal la RNA es redundante con el supervisor. El detalle y las demás limitaciones están en `INFORME_TECNICO.md`.

## Documentación

- `INFORME_TECNICO.md`: arquitectura, experimentos, resultados y limitaciones.
- `ARES_X_entregable.ipynb`: notebook de la entrega (se regenera con `python construir_notebook.py`).
