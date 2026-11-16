# ARES-X · rover autónomo con IA híbrida (RNA + lógica difusa + AG)

Entrega individual de la evaluación ev3. Simulación ficticia con parámetros de referencia; no es una misión real.

## Instalación desde cero

Requisitos: Python 3.11 o superior, CPU. Sin claves, sin pagos y sin Google Colab.

```bash
cd ares_x
pip install -r requirements.txt
pip install pygame-ce                 # solo para el juego de escritorio
python -m pytest -q                   # pruebas: juego, módulos de IA y API
```

Ejecutar la API y la escena 3D (desde `ares_x/`):

```bash
python -m uvicorn api.servidor:app --port 8765
# abrir http://127.0.0.1:8765/ en el navegador
```

Juego de escritorio: `python juego/main.py`. Sin ventana: `python -m juego --headless --semilla 11 --pasos 300 --salida salida_juego`.

Notebook de entrega: `ARES_X_entregable.ipynb` (regenerable con `python construir_notebook.py`).

## Semilla de demostración

`semilla = 11` (mapa de Marte con 20 obstáculos, 4 barrancos y 3 sitios científicos). Con esa semilla la misión termina en `EXITO` en 60 pasos, según la sección 6 del notebook.

## Uso

- `simulador.py`: mapa 2D, rover, sensores con ruido y bitácora (`MissionLogger`).
- `rna.py`: MLP 32-16 (ReLU, 3 clases) entrenado con mapas separados por semilla.
- `difuso.py`: controlador Mamdani con 9 reglas; conjuntos de 3 niveles en distancia, batería e inclinación.
- `genetico.py`: AG con K puntos de paso, elitismo y desglose del fitness.
- `integracion.py`: supervisor de seguridad con códigos de motivo (`V-…`), replanteo con BFS y máquina de estados.

## Experimento

`ARES_X_ejecutado.ipynb` es la versión ejecutada del notebook: 20 semillas por variante, con media, mediana y dispersión.

- Híbrido, sin RNA y sin difuso: 100 % de éxito cada uno (movimiento en 8 direcciones).
- RNA forzada a «barranco»: la decisión cambia en 20 de 20 semillas; el éxito cae a 0 % (vetos).
- RNA forzada a «libre»: ninguna decisión cambia (0 de 20).

## Exportación

La última celda del notebook escribe `mision_traza.csv` (una fila por paso) y `mision_resumen.json` (configuración, semilla y resultado).

## Límites del modelo

- Solo Marte (modo rover). Júpiter, Saturno, Urano y Neptuno, Venus, Mercurio y Tierra no están implementados.
- Sin interfaz interactiva (ipywidgets multipaso); solo bitácora y tablas.
- Sin eventos de sismo, tormenta ni falla de sensor en la misión.
- La RNA es redundante con los sensores en el escenario normal: su efecto se demuestra con la intervención, no con la ablación.
- El plan omite sitios científicos por energía (en promedio se visitan menos de 3).

## Supuestos de simulación

- Gradiente de altura a grados: 20 °/unidad (`GRADOS_POR_GRADIENTE`).
- Vibración media por clase de terreno (`VIBRACION_MEDIA`).
- Margen de batería de 15 % sobre el camino al refugio (`MARGEN_ENERGIA`).
- Todos los valores numéricos sin fuente son supuestos de simulación, no especificaciones NASA.

## Uso de IA generativa

Se usaron asistentes de IA: Claude (Anthropic) para generar y depurar código y redactar documentación; y una imagen de fondo del menú generada con IA (Google Gemini) por el estudiante. La imagen es ilustrativa y no tiene carácter oficial ni respaldo de ninguna agencia espacial. La defensa individual cubre explicar una predicción de la RNA, una regla difusa y una operación genética.

## Desarrollo: API (ARX-03)

La API FastAPI sirve la partida en JSON. Desde `ares_x/`:

```bash
pip install -r requirements.txt
python -m uvicorn api.servidor:app --host 127.0.0.1 --port 8765   # http://127.0.0.1:8765/docs (sin --reload)
python -m pytest -q api/tests              # pruebas de la API
```

Operación del motor, reinicio del 8765 y estado para retomar: `docs/OPERACION_MOTOR.md`.

Modos `rna`, `difuso` y `ag` conducen solos (ARX-11); `POST /modo` acepta `veto` (true por defecto).
Rutas principales: `GET /estado`, `POST /partida`, `POST /mover`, `POST /paso`, `POST /modo`,
`POST /disparo`, `POST /evento`, `GET /paneles`. `POST /intervencion` queda como esqueleto hasta ARX-10.
Los errores devuelven 400 (entrada inválida), 409 (partida terminada o acción no permitida) o 501 (pendiente),
siempre con el campo `motivo`.
