# R23: el AG con un problema de verdad, difuso evolucionado por planeta y RNA con anticipación

Segunda parte de la ronda de correcciones del 22/11/2026 (la primera, `R23_dificultad.md`, hizo real la dificultad). Contratos de API en
`R23_contratos_api.md`.

## 1. El problema que resuelve el AG (`planificacion.py`)

Antes: viajante de 3 a 4 sitios (24 órdenes). Ahora, en la partida jugable (`garantia=True`):

- **8 a 12 sitios** (`dificultad.SITIOS_POR_NIVEL`: 8, 8, 9, 10, 11 en el mapa pequeño; mediano +1, grande +2; tope 12), con los valores 1 a 9 de siempre.
- **Ventanas de tiempo** (`dificultad.VENTANAS_POR_NIVEL`): entre los pasos `desde` y `hasta` el sitio vale el 100 %; fuera, el 25 % (poca luz o
  instrumento sin calentar). No hay espera. Se centran en las llegadas de un recorrido de referencia (permutación aleatoria con tres mejoras 2-opt),
  así que existe un plan que las cumple y el recorrido más corto no las cumple todas; más difícil = más sitios con ventana y más estrechas.
- **Recarga obligatoria**: 3 a 4 bases de recarga (3 pasos parado, batería a la capacidad) y una batería que no alcanza para el recorrido
  completo. Tras cada sitio debe quedar batería para llegar a una base (con margen de tormentas) y al refugio la reserva de 15 %.
- **Sacrificio**: la cuarta parte de menor valor son sitios *opcionales*: se pueden descartar. Para ganar hay que visitar los obligatorios y llegar al
  refugio (`Partida.exigidos()`); los opcionales suman puntaje. La ciencia recogida es el valor de cada sitio por la calidad de su ventana
  (`Partida.ciencia()`), y el puntaje de la partida la usa.

### Cromosoma, operadores y fitness

Cromosoma `(orden, sel, paradas)`: permutación de todos los sitios pendientes, un bit de selección por sitio (solo cuenta en los opcionales) y n+1 genes
de parada (base de recarga antes de cada sitio y antes del refugio, o ninguna). **Decodificación con reparación**: se recorre la secuencia gastando
batería; si un tramo deja menos que lo necesario para seguir, se inserta la base que menos desvío cause y la reparación se escribe de vuelta en el
cromosoma (lamarckiano); un opcional inalcanzable se sacrifica, un obligatorio inalcanzable deja el plan infactible.

Fitness (maximizar) = ciencia (valor × calidad de ventana ÷ valor total) − 0,25 · pasos ÷ pasos de referencia − 0,01 · recargas reparadas; un plan
infactible puntúa por debajo de cualquier factible (−1 − 0,05 por parada obligatoria no cubierta).

Operadores: torneo de 3; cruce OX sobre la permutación, uniforme sobre la selección, de un punto sobre las paradas; mutación por intercambio,
inserción, inversión (2-opt), alternancia de selección, alta/baja/cambio de parada y una mutación guiada que recoloca un sitio que perdió su ventana
donde el plan llega cerca de ella. Elitismo 2.

**Control de diversidad**: sin duplicados en la población (el hijo repetido se muta con más fuerza o se sustituye por un inmigrante); mutación y
migración adaptativas cuando la diversidad (distancia media entre pares) cae bajo 0,12; reinicio parcial del 40 % peor si hay 8 generaciones sin mejora
con la población homogénea. Población 60, 60 generaciones en el plan inicial; replanteos con menos (40 × 30, y menos aún con pocos sitios pendientes).

### En la partida

El plan decide también las paradas de recarga: la ruta pasa por las bases. Un replanteo (veto, obstáculo, meteorito) es **barato**: decodifica el mismo
plan con el mapa, la batería y el paso de ahora (la reparación inserta lo que falte); si no es factible, o hay un evento grave, corre el AG con el plan
vigente y las heurísticas como semillas. Cada paso se comprueba que el plan vigente siga llegando con el gasto real observado (media móvil del gasto
por paso; manda sobre la estimación del planeta si es mayor). Las «sin AG» (vecino más cercano, 2-opt, por ventanas) usan **la misma ejecución, la
misma reparación de recargas y la misma poda de opcionales**: solo cambia quién ordena los sitios.

Robustez que hubo que añadir al probar con 11 sitios: las bases, los sitios, el inicio y el refugio son libres por construcción y la RNA, el telémetro con
tormenta o el sensor no pueden marcarlos como barranco (un sitio obligatorio inalcanzable dejaba la partida girando); si aun así uno queda inalcanzable se
olvidan las dudas de la RNA (riesgo entre 0,5 y 1; las lecturas firmes se conservan); si no hay plan se va a la base alcanzable más cercana.

### Convergencia y diversidad, antes y después (10 semillas)

| | AG anterior (4 sitios, 24 órdenes) | AG con restricciones (10 a 11 sitios) |
|---|---|---|
| individuos distintos en la generación 0 / 2 / 5 | 17 / 9,5 / 5 de 30 (mediana) | 60 / 60 / 60 de 60 |
| diversidad (distancia media entre pares) gen 0 / 5 / 20 / última | no definida (≤ 5 individuos distintos desde la gen. 5) | 0,50 / 0,42 / 0,30 / 0,29 |
| generación de la última mejora del mejor fitness | 0 (mediana; la semilla del vecino más cercano ya era el óptimo) | 45 (rango 14 a 59); 19 de 20 instancias ≥ 15 |
| fitness del mejor, gen 0 → 10 → 20 → última (mediana) | constante | 0,48 → 0,61 → 0,66 → 0,67 |
| tiempo del plan inicial (mapa pequeño) | ~0,05 s | 0,30 s (0,23 a 0,46) |

## 2. El AG evoluciona el difuso por planeta (`juego/difuso_planetas.py`, `scripts/evolucionar_difuso.py`)

El difuso se parametriza (`difuso.FuzzyController(params=...)`): puntos de las funciones de pertenencia, peso de cada regla (multiplica la fuerza de
activación) y estado de cada regla. El vector evolucionado tiene 30 genes: puntos de pertenencia de distancia, inclinación, batería y salida (con anchuras
para garantizar el orden), los 11 pesos de regla y cinco umbrales de conducción (tope de velocidad sobre hielo, con viento y en pendiente fuerte; factor de
desvío y umbral de batería para ir a una base). Con el vector por defecto el difuso es idéntico al original (prueba).

AG real (torneo 3, BLX-0,3, mutación gaussiana, elitismo 2, población 12, 7 generaciones, semilla 2026). Fitness **por planeta**: media sobre las semillas de
entrenamiento (301 a 308) de partidas jugables en ese planeta (nivel 4, 11 sitios, mecánicas de `juego/planetas.py`): éxito + 0,5 · ciencia + 0,2 · batería
final (si gana). Se mide después en semillas de **validación no vistas** (401 a 420) contra el difuso por defecto. El resultado se guarda en
`juego/difuso_planetas.json`, que la partida carga; `difuso_evolucionado=False` (o la variante `difuso_base`) deja el difuso por defecto como ablación.

Para que la velocidad tenga algo que decidir se añadió a `planetas.costo_extra` un consumo de base por tiempo (`COSTO_TIEMPO_LENTO`, solo por debajo
de velocidad 0,5): sin él ir lo más lento posible era siempre lo mejor, porque la velocidad no cuesta tiempo de partida.

## 3. RNA con anticipación (`anticipacion.py`)

Una segunda red (MLP 32-16) clasifica las celdas de la ruta a 2, 3 y 4 pasos. **Alcance de los sensores**: los actuales solo miden la celda de enfrente;
se supone, y está declarado, que el telémetro inclinado y la cámara alcanzan 4 celdas con ruido creciente (σ_k = σ_1 · (1 + 0,5 · (k − 1))). Rasgos:
desnivel hasta la celda, desnivel hasta la celda anterior de la ruta, contraste óptico y k (no la vibración, que es de la celda actual). Las
probabilidades se corrigen por la proporción real de clases (Bayes: el entrenamiento lleva muchos más barrancos que el mapa). Medido en mapas de prueba
(51 a 59), con p(barranco) ≥ 0,10: recall de barrancos 61 / 47 / 34 % a 2 / 3 / 4 celdas con ~1 % de falsos barrancos entre las celdas libres; con 0,5 solo
36 / 20 / 15 %. **Es una anticipación parcial, no una detección fiable**: a 4 celdas el ruido pesa.

Uso en la partida: una celda con p ≥ 0,10 frena el paso (tope de velocidad 0,3); la celda con media de al menos 2 observaciones ≥ 0,30 queda como riesgo y se
replantea la ruta antes de llegar. `/ia/paso` expone `rna.tramo`. Las lecturas usan un generador propio (no consumen el azar de la misión).

**Confirmación de la RNA de una celda**: `Partida._riesgo_por_rna_partida` exige 2 observaciones con media de p(barranco) > 0,5 antes de marcar un riesgo
permanente también con el ruido nominal (el veto inmediato de la lectura del paso no cambia), y no marca celdas conocidas. Antes, una sola lectura falsa
podía cerrar para siempre una celda, incluso una base de recarga.

## 4. Resultados

### 4.1 Parámetros evolucionados (entrenamiento frente a validación)

Fitness medio por partida (máximo ≈ 1,7: éxito + 0,5 · ciencia + 0,2 · batería), nivel 4, 11 sitios; validación = semillas 401 a 420 no vistas.

| Planeta | Semillas de entrenamiento | Entrenamiento: defecto → evolucionado | Validación: defecto → evolucionado | Éxito en validación (defecto → evolucionado) |
|---|---|---|---|---|
| Marte | 8 (301–308), pob. 12 × 7 gen. | 1,555 → 1,572 | 1,297 → 1,419 (+0,12) | 80 % → 90 % |
| Neptuno | 16 (301–316), pob. 12 × 6 gen. | 1,352 → 1,505 | 1,392 → 1,375 (−0,02) | 90 % → 90 % |

Neptuno, primer intento con 8 semillas: entrenamiento 1,470 → 1,518, validación 1,392 → 1,330 (éxito 90 → 85 %): **sobreajuste**. Con 16 semillas el entrenamiento
mejora más (+0,15) y la validación no mejora (−0,02, dentro del ruido). **Lectura honesta**: en Marte la mejora de validación (+0,12, 10 puntos de éxito con n = 20)
va en el sentido esperado pero no es concluyente; en Neptuno no se demuestra mejora fuera de las semillas de entrenamiento. Lo evolucionado son retoques chicos del
difuso por defecto (anchuras de los conjuntos, pesos de 0,76 a 0,95 en 5 a 8 reglas, tope de velocidad con viento de 0,88 a 0,90; el tope sobre hielo y en pendiente no actúa
y el factor de desvío queda en 1,29 y 1,38): solo se evaluaron 60 a 71 vectores distintos (población 12), poco para 30 genes.

### 4.2 La IA importa: comparación en la partida jugable difícil

Nivel 4, 11 sitios, mapa pequeño, mismas semillas para todas las variantes: **desarrollo** (1 a 20) y **validación** (101 a 120, no vistas por el diseño ni por la
evolución). Éxito con intervalo de Wilson del 95 %; ciencia = fracción del valor total recogido (con la calidad de la ventana), media ± error estándar.

Marte (viento moderado, polvo, algo de hielo):

| Variante | Éxito desarrollo (IC 95 %) | Ciencia desarrollo | Éxito validación | Ciencia validación | Puntaje validación |
|---|---|---|---|---|---|
| híbrido | 18/20 (70–97) | 0,725 ± 0,046 | 19/20 | 0,770 ± 0,030 | 99 ± 3 |
| sin RNA | 20/20 (84–100) | 0,777 ± 0,041 | 19/20 | 0,767 ± 0,040 | 109 ± 7 |
| sin difuso | 18/20 (70–97) | 0,787 ± 0,041 | 17/20 | 0,758 ± 0,033 | 98 ± 5 |
| sin AG: vecino más cercano | 18/20 (70–97) | 0,532 ± 0,032 | 17/20 | 0,619 ± 0,039 | 78 ± 5 |
| sin AG: 2-opt | 17/20 (64–95) | 0,572 ± 0,033 | 19/20 | 0,636 ± 0,029 | 83 ± 4 |
| sin AG: por ventanas (primero el que vence antes) | 13/20 (43–82) | 0,589 ± 0,053 | 19/20 | 0,758 ± 0,041 | 93 ± 5 |
| difuso sin evolucionar | 18/20 (70–97) | 0,727 ± 0,051 | 17/20 | 0,742 ± 0,042 | 94 ± 6 |

Neptuno (viento muy fuerte con ráfagas, hielo muy resbaladizo):

| Variante | Éxito desarrollo (IC 95 %) | Ciencia desarrollo | Éxito validación | Ciencia validación | Puntaje validación |
|---|---|---|---|---|---|
| híbrido | 17/20 (64–95) | 0,743 ± 0,046 | 18/20 | 0,794 ± 0,037 | 108 ± 5 |
| sin RNA | 18/20 (70–97) | 0,776 ± 0,039 | 19/20 | 0,782 ± 0,037 | 113 ± 8 |
| sin difuso | 17/20 (64–95) | 0,792 ± 0,033 | 19/20 | 0,735 ± 0,045 | 100 ± 6 |
| sin AG: vecino más cercano | 17/20 (64–95) | 0,556 ± 0,038 | 15/20 | 0,590 ± 0,036 | 75 ± 5 |
| sin AG: 2-opt | 19/20 (76–99) | 0,572 ± 0,038 | 20/20 | 0,656 ± 0,031 | 96 ± 4 |
| sin AG: por ventanas | 17/20 (64–95) | 0,647 ± 0,050 | 17/20 | 0,710 ± 0,041 | 91 ± 6 |
| difuso sin evolucionar | 19/20 (76–99) | 0,773 ± 0,045 | 17/20 | 0,773 ± 0,046 | 105 ± 6 |

Conclusiones, con cifras:

- **El AG sí aporta, y de forma medible, en ciencia recogida y puntaje**: +0,15 a +0,20 de fracción de ciencia frente al vecino más cercano y al 2-opt en las cuatro
  mediciones (4 a 6 errores estándar) y +15 a +30 puntos de puntaje. En **éxito** no hay diferencia: las ablaciones también ganan (la dificultad viene de la batería y
  las tormentas, no del orden; con IC de ±15 puntos no se distingue). La heurística «por ventanas» (que mira las ventanas) se acerca al AG en la validación
  (0,76 frente a 0,77 en Marte; 0,71 frente a 0,79 en Neptuno) pero con 190 a 200 pasos (el AG, 153 a 174) y más recargas.
- **La RNA no aporta; en desarrollo incluso resta** (sin RNA ≥ híbrido en ciencia y éxito en las cuatro mediciones, diferencias de 0,00 a 0,05 de ciencia, dentro de 1 error
  estándar o poco más: no concluyente, pero sin ninguna señal a favor). Motivo estructural: el supervisor ya veta con el telémetro inclinado (V-BORDE-BARRANCO) y el
  mapa estimado se corrige con lo medido (ARX-93c lo mostró); la RNA añade falsos barrancos (~1,7 % de las celdas libres) y pasos de espera. Con la anticipación hay un
  efecto real sobre una celda con barranco forzado (ver `tests/test_anticipacion_r23.py`) pero no se traduce en más partidas ganadas.
- **El difuso evolucionado no se distingue del de defecto ni de la velocidad fija**: ±5 puntos de ciencia, ±10 de éxito, con signo cambiante entre desarrollo y validación.
  El efecto de la velocidad sobre el resultado es chico (solo entra por viento, hielo y pendiente).

## 5. Cómo reproducir

```
python scripts/evolucionar_difuso.py --planeta Marte           # y Neptuno; escribe juego/difuso_planetas.json
python scripts/comparacion_jugable.py --escenario jugable_dificil
python scripts/comparacion_jugable.py --escenario jugable_dificil_neptuno
python scripts/medir_dificultad.py --tamano pequeno --planetas Marte --semillas 20 --politica hibrido
```


## 6. R23b: el laboratorio con 100 semillas, el puntaje único y la RNA con menos falsas alarmas

Segunda tanda de comentarios del evaluador. Las tablas de 4.2 (20 semillas, puntaje con bono por veto) **ya no valen**: el puntaje es otro (`juego/puntaje.py`,
ver `R23_contratos_api.md`), la RNA se reentrenó con menos refuerzo y las diferencias ahora se miden con 100 semillas y su error estándar.
Cifras reproducibles con `python scripts/comparacion_jugable.py --escenario jugable_dificil` (~25 min por escenario con 100 + 20 semillas, una a la vez).

### 6.1 Escenarios jugables, 100 semillas (1 a 100)

Éxito con intervalo de Wilson del 95 %; ciencia, puntaje y pasos con media ± error estándar. «Diferencia» = variante − híbrido en las mismas semillas, ± su
error estándar; **distinguible** si |diferencia ÷ error estándar| ≥ 1,96 (95 %).

Marte (`jugable_dificil`):

| Variante | Éxito (IC 95 %) | Ciencia | Puntaje | Pasos |
|---|---|---|---|---|
| híbrido | 75/100 (66–82) | 0,712 ± 0,018 | 634 ± 24 | 160 ± 5,4 |
| sin RNA | 78/100 (69–85) | 0,742 ± 0,018 | 647 ± 23 | 160 ± 5,0 |
| sin difuso | 81/100 (72–88) | 0,730 ± 0,018 | 675 ± 22 | 164 ± 5,6 |
| sin AG: vecino más cercano | 77/100 (68–84) | 0,588 ± 0,016 | 600 ± 22 | 148 ± 4,4 |
| sin AG: 2-opt | 85/100 (77–91) | 0,590 ± 0,014 | 632 ± 18 | 141 ± 4,1 |
| sin AG: por ventanas | 60/100 (50–69) | 0,673 ± 0,023 | 543 ± 29 | 189 ± 7,2 |
| difuso sin evolucionar | 77/100 (68–84) | 0,734 ± 0,016 | 655 ± 23 | 162 ± 5,6 |

| Diferencia con el híbrido | Éxito (pp) | Ciencia | Puntaje | Pasos (si ganan las dos) |
|---|---|---|---|---|
| sin RNA | +3,0 ± 3,9 (ruido) | +0,031 ± 0,012 (distinguible) | +14 ± 20 (ruido) | −0,3 ± 3,9 (ruido) |
| sin difuso | +6,0 ± 4,2 (ruido) | +0,019 ± 0,014 (ruido) | +42 ± 22 (ruido) | −6,0 ± 3,6 (ruido) |
| sin AG: vecino | +2,0 ± 5,1 (ruido) | −0,123 ± 0,020 (distinguible) | −34 ± 26 (ruido) | −15,2 ± 6,3 (distinguible) |
| sin AG: 2-opt | +10,0 ± 4,6 (distinguible) | −0,122 ± 0,019 (distinguible) | −1 ± 24 (ruido) | −30,2 ± 6,4 (distinguible) |
| sin AG: por ventanas | −15,0 ± 5,8 (distinguible) | −0,039 ± 0,025 (ruido) | −90 ± 32 (distinguible) | +38,4 ± 6,8 (distinguible) |
| difuso sin evolucionar | +2,0 ± 3,2 (ruido) | +0,022 ± 0,009 (distinguible) | +21 ± 17 (ruido) | −0,5 ± 1,4 (ruido) |

Neptuno (`jugable_dificil_neptuno`):

| Variante | Éxito (IC 95 %) | Ciencia | Puntaje | Pasos |
|---|---|---|---|---|
| híbrido | 84/100 (76–90) | 0,728 ± 0,018 | 676 ± 21 | 162 ± 5,3 |
| sin RNA | 88/100 (80–93) | 0,740 ± 0,018 | 682 ± 19 | 156 ± 4,6 |
| sin difuso | 78/100 (69–85) | 0,711 ± 0,018 | 639 ± 24 | 159 ± 5,1 |
| sin AG: vecino más cercano | 79/100 (70–86) | 0,591 ± 0,015 | 593 ± 21 | 149 ± 3,7 |
| sin AG: 2-opt | 86/100 (78–92) | 0,588 ± 0,016 | 630 ± 19 | 144 ± 4,6 |
| sin AG: por ventanas | 76/100 (67–83) | 0,710 ± 0,020 | 617 ± 24 | 208 ± 6,1 |
| difuso sin evolucionar | 79/100 (70–86) | 0,724 ± 0,018 | 646 ± 23 | 160 ± 5,1 |

| Diferencia con el híbrido | Éxito (pp) | Ciencia | Puntaje | Pasos (si ganan las dos) |
|---|---|---|---|---|
| sin RNA | +4,0 ± 3,2 (ruido) | +0,012 ± 0,013 (ruido) | +5 ± 17 (ruido) | −6,3 ± 2,2 (distinguible) |
| sin difuso | −6,0 ± 4,5 (ruido) | −0,017 ± 0,011 (ruido) | −37 ± 23 (ruido) | −0,2 ± 2,8 (ruido) |
| sin AG: vecino | −5,0 ± 5,2 (ruido) | −0,137 ± 0,019 (distinguible) | −83 ± 27 (distinguible) | −11,6 ± 4,5 (distinguible) |
| sin AG: 2-opt | +2,0 ± 4,7 (ruido) | −0,140 ± 0,018 (distinguible) | −47 ± 26 (ruido) | −23,5 ± 4,7 (distinguible) |
| sin AG: por ventanas | −8,0 ± 5,3 (ruido) | −0,018 ± 0,021 (ruido) | −59 ± 28 (distinguible) | +47,7 ± 5,0 (distinguible) |
| difuso sin evolucionar | −5,0 ± 3,6 (ruido) | −0,004 ± 0,010 (ruido) | −30 ± 18 (ruido) | −0,7 ± 1,7 (ruido) |

La validación (semillas 101 a 120, solo 20) va en los JSON (`validacion`); con 20 semillas casi nada se distingue del ruido y no cambia la lectura.

### 6.2 Lectura honesta

- **El AG aporta ciencia, no éxito.** Frente al vecino más cercano y al 2-opt recoge +0,12 a +0,14 de fracción de ciencia (6 a 7 errores estándar) y camina 15 a 30 pasos
  más (visita más sitios opcionales dentro de su ventana). **Pero no gana más misiones**: en Marte el 2-opt gana 85 % frente al 75 % del híbrido (+10 pp,
  distinguible); en Neptuno la diferencia es ruido. En puntaje el AG no se distingue del 2-opt (−1 ± 24 y −47 ± 26): lo que gana en ciencia lo pierde en
  misiones fallidas. Con 20 semillas, el 22/11 anterior, se leyó «el AG sí aporta +15 a +30 de puntaje»; con 100 semillas y el puntaje sin bono por veto eso no se sostiene.
- La heurística «por ventanas» llega a una ciencia parecida a la del AG (−0,04 y −0,02, ruido) pero con 38 a 48 pasos más y, en Marte, 15 pp menos de éxito (distinguible).
- **La RNA no aporta.** Sin RNA el éxito es igual o mayor (+3 y +4 pp, ruido) y la ciencia no baja (en Marte sube +0,031, distinguible). Es coherente con el diseño: el supervisor
  ya veta con el telémetro y la RNA solo añade falsas alarmas (ver 6.4).
- **El difuso no se distingue del ruido** en éxito ni en ciencia; el evolucionado frente al de defecto tampoco (|z| < 2 salvo +0,022 de ciencia en Marte).
- Las tasas de éxito de los híbridos (75 % Marte, 84 % Neptuno) son más bajas que las de 20 semillas de 4.2 (90 %/85 %): aquel era un error de muestreo de ±15 puntos. Parte de los fracasos
  son batería agotada con planes que dejan poco margen; no se tocó la dificultad.
- **Qué no se midió:** el laboratorio corre la partida sin combate (sin drones); el juego real con drones (nivel ≥ 3) cambia las cifras absolutas.

### 6.3 «AG igual a 2-opt» en el escenario exigente

El `exigente` (nivel 5 con sensor ruidoso) usa 3 a 4 sitios, sin ventanas ni recargas: con tan pocos sitios el 2-opt halla el mismo orden óptimo que el AG. Con 100 semillas el
híbrido y «sin AG (2-opt)» tienen **la misma trayectoria exacta en 92 de 100 semillas** (éxito 94 % y 94 %, pasos 67,00 y 67,06). **El escenario no ejercita al AG restringido**: no es un fallo del AG
sino de qué mide el escenario. No se forzó una diferencia: su descripción lo dice (`INFO_ESCENARIOS`, publicada por `/comparacion` en `info`) y el escenario que mide al AG con el plan real es el jugable
(`jugable_dificil*`: 0 de 100 trayectorias iguales entre híbrido y 2-opt, diferencias de ciencia de 6 a 7 errores estándar). `exigente10` (10 sitios) ejercita el orden pero tampoco las ventanas.
El `congelado` queda como **histórico (versión anterior del juego)** en datos y descripción; ya no es el escenario por defecto.

### 6.4 RNA: falsas alarmas (refuerzo de barrancos)

El refuerzo de 100 muestras de barranco por mapa subió el recall pero marcaba 52 libres como barranco (macro-F1 0,819). Barrido (mapas de prueba 51–59 del notebook: 3 128 celdas libres,
30 barrancos; «grande» = 60 mapas no vistos 100–159: 20 637 libres, 209 barrancos). Decisión por argmax (umbral 0,5, el del veto); con un umbral propio para la clase barranco el efecto es parecido,
pero habría que cambiar el umbral de veto de todo el motor:

| Refuerzo / umbral | Macro-F1 | Recall barranco | Precisión barranco | Libres marcadas barranco | Macro-F1 grande | Recall grande | Libres marcadas (grande) |
|---|---|---|---|---|---|---|---|
| 0 | 0,906 | 19/30 (0,63) | 0,90 | 2 | 0,913 | 0,66 | 15 |
| 10 | 0,925 | 21/30 (0,70) | 0,88 | 3 | 0,921 | 0,71 | 29 |
| **15** | **0,890** | **23/30 (0,77)** | 0,62 | **14** | 0,908 | 0,77 | 65 |
| 20 | 0,863 | 23/30 (0,77) | 0,51 | 22 | 0,885 | 0,79 | 104 |
| 25 | 0,855 | 23/30 (0,77) | 0,46 | 27 | 0,885 | 0,81 | 132 |
| 50 | 0,836 | 24/30 (0,80) | 0,38 | 39 | 0,879 | 0,85 | 166 |
| 100 (antes) | 0,819 | 25/30 (0,83) | 0,32 | 52 | 0,849 | 0,88 | 265 |
| 20, umbral 0,7 | 0,912 | 22/30 (0,73) | 0,79 | 6 | 0,912 | 0,74 | 39 |
| 25, umbral 0,7 | 0,901 | 22/30 (0,73) | 0,69 | 10 | 0,920 | 0,77 | 48 |
| 100, umbral 0,7 | 0,870 | 23/30 (0,77) | 0,51 | 22 | 0,891 | 0,81 | 121 |

Elegido **refuerzo 15 con el umbral de veto de siempre (0,5)**: macro-F1 0,890 (≥ 0,88), recall 77 % (≥ 0,75) y 14 libres marcadas (de 52), sin tocar `UMBRAL_RIESGO_RNA`. En el modelo del juego
(30 mapas, 300 por mapa; 3 semillas de red) el macro-F1 queda en 0,87–0,89, recall 12/18 en prueba y 76 % en 60 mapas no vistos, y las libres marcadas bajan de 27–34 a 3–5 sobre 1 272. **Coste:** el
barranco somero (1,0 a 1,5 m), indistinguible de la pendiente natural, vuelve a poder quedar en «libre» con confianza alta (un caso de nueve en la regresión de R23): ese lo veta el telémetro del
supervisor. Los de 1,5 m o más se siguen marcando todos. El refuerzo 10 tiene el mejor macro-F1 pero un recall de 70 % (< 0,75).

### 6.5 Escenarios de 3 a 10 sitios sin plan restringido, 100 semillas

`exigente` (3 a 4 sitios): híbrido 94/100, sin RNA 94, sin difuso 93, sin AG 2-opt 94, sin AG vecino 85 (−9 pp, distinguible), ruta corta 84 (−10 pp, distinguible), AG puro 87 (−7 pp, distinguible).
`exigente10` (10 sitios, batería ajustada): híbrido 84/100, sin RNA 84, sin difuso 83, sin AG 2-opt 88 (+4 pp, ruido; 3,1 pasos menos, distinguible), sin AG orden más corto 86, sin AG vecino 58 (−26 pp, distinguible),
ruta corta 58, AG puro 72 (−12 pp, distinguible). Con orden de sitios y sin ventanas, el AG supera con claridad al vecino más cercano, pero **no al 2-opt**. Detalle en `estadistica` de cada JSON.
