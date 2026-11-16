# ARES-X · Juego interactivo del rover

Juego de escritorio (pygame) en el que conduces un rover en Marte mientras la IA sugiere cada paso.
Usa las mismas técnicas del proyecto: red neuronal de percepción, lógica difusa, algoritmo genético
y supervisor de seguridad. Todos los valores son supuestos de simulación, no especificaciones de misión.

## Instalación

Desde la carpeta `ares_x/`:

```bash
pip install -r requirements.txt
pip install pygame-ce
```

`pygame-ce` es la versión de pygame que tiene instalador para Python 3.14. Funciona con `import pygame`.

## Ejecutar el juego

```bash
python juego/main.py
```

Se abre una ventana de 1280x720 con el mapa de Marte a la izquierda y cuatro paneles a la derecha
(RNA, difuso, algoritmo genético y supervisor). Los paneles siempre muestran la decisión de la IA
(ev3-d18); TAB solo muestra u oculta la flecha de sugerencia en el mapa.

## Controles

| Tecla | Acción |
|---|---|
| Flechas o WASD | Mueves el rover una celda. Un barranco o un obstáculo bloquea el movimiento. |
| ESPACIO | La IA avanza un paso por su cuenta. |
| TAB | Muestra u oculta la flecha de sugerencia de la IA. |
| B | Coloca un barranco junto al rover. |
| F | Provoca una falla de sensor (ver limitaciones). |
| E | Pone la batería en 15 %. |
| R | Nueva partida con una semilla nueva. |
| C | Compara las variantes con 20 semillas (tarda unos 70 segundos). |
| X | Exporta la partida a CSV y JSON en `juego/exportaciones/`. |
| ESC | Sale. |

## Pruebas

```bash
python -m pytest -q juego/tests tests -p no:warnings
```

Resultado esperado: 112 pruebas en verde. Las 45 de `tests/` cubren los módulos de IA y la integración;
las demás cubren la partida, la interfaz y la exportación.

## Estructura

| Archivo | Qué hace |
|---|---|
| `juego/partida.py` | Partida jugable: movimiento del jugador, paso de la IA, eventos, sugerencia y bitácora. |
| `juego/ui.py` | Ventana pygame, mapeo de teclas y paneles. |
| `juego/main.py` | Arranca la ventana. |
| `juego/exportar.py` | Exporta la bitácora (CSV) y la configuración con el resumen (JSON). |
| `juego/experimento.py` | Compara híbrido, sin RNA y sin difuso con 20 semillas. |
| `juego/GUION_VIDEO.md` | Guion del video de demostración. |
| `simulador.py`, `rna.py`, `difuso.py`, `genetico.py`, `integracion.py` | Módulos de IA y simulación, congelados (ev3-d08). |

## Supuestos y limitaciones conocidas

- **Falla de sensor:** hoy termina la partida en el primer paso (estado MODO_SEGURO), porque el supervisor
  congelado lo exige. La decisión sobre este comportamiento está pendiente en la Bandeja (`ev3-d23`).
- **Lectura NaN en la RNA:** el clasificador de scikit-learn no acepta valores NaN. `partida.py` lo resuelve
  con un envoltorio que devuelve probabilidades neutras solo cuando hay NaN. `rna.py` no se modifica.
- **Comparación bloqueante:** la tecla C congela la ventana unos 70 segundos, porque corre 60 misiones.
- **Desglose del AG en la sugerencia:** se calcula con los objetivos pendientes desde la posición actual,
  no con la ruta exacta. Es una aproximación.
- **Sitios científicos:** en una partida normal el jugador visita pocos de los sitios planeados, porque el plan
  prioriza llegar al refugio con la batería disponible. Esto se documenta como resultado, no como fallo.
- **Mapa estimado:** el rover puede marcar como obstáculo una celda libre por el ruido del sensor. Ese bloqueo
  no se libera, y es la limitación principal del proyecto.
- **Parámetros:** pesos del fitness, costos de batería y rangos de sensores son supuestos de simulación.
