# Leyenda y texto alternativo de las figuras

Se regeneran con `python scripts/generar_figuras.py` (desde `ares_x/`).

## matriz_confusion.png

Matriz de confusión de la RNA de percepción en los mapas de prueba (9 mapas, 3 535 muestras). Filas: clase real (libre,
obstáculo, barranco); columnas: clase predicha. Cada celda trae el conteo y el porcentaje de su fila; el color azul más
oscuro indica mayor fracción de la clase real. Lectura: la clase libre se acierta en 3 090 de 3 090 casos; el obstáculo
en 196 de 210 (93,3 %), con 12 confundidos con barranco y 2 con libre; el barranco en 33 de 35 (94,3 %), con 2
confundidos con obstáculo y ninguno con libre. Cifras de la ejecución con semilla 42 y 400 muestras por mapa.

## ablacion.png

Comparación de políticas en el escenario exigente (20 semillas por variante), en tres paneles que comparten las
variantes en el eje vertical: tasa de éxito (%), pasos por misión (media con barra de desviación) y colisiones por misión
(media). El híbrido es la barra naranja con trama diagonal; las demás variantes son azules, con su valor escrito al lado.
Lectura: el híbrido logra 100 % de éxito con 54,3 pasos y 0 colisiones; quitar el difuso baja el éxito a 75 % y la ruta
corta voraz también a 75 %; sin la RNA se mantiene en 100 %.

Colores: paleta Okabe-Ito (naranja `#E69F00` y azul `#0072B2`), distinguible con daltonismo; ningún dato depende solo
del color.

## Versión de los datos

Cada PNG lleva al pie «Datos publicados de main <hash>; regenerar tras ARX-94f». Hay que regenerarlas tras ARX-94f,
porque las cifras publicadas cambian con el rediseño de sensores. Ver `docs/planes/ARX-100_figuras.md`.
