# R23: contratos de API finales (AG con restricciones, difuso editable, RNA con anticipación)

Contrato exacto de lo que sirve `api/servidor.py` en la rama `r23/ag`. Las diferencias respecto del pedido están en la última sección.

## GET /ag/evolucion

Evolución del AG del **plan inicial** de la partida en curso. Se guarda al calcular el plan (al crear la partida); no se recalcula en cada
llamada. Sin partida o sin plan con restricciones: `404` con `{"hay_plan": false, "motivo": "..."}`.

```
{ hay_plan: true, planeta, inicio:[f,c], refugio:[f,c],
  sitios:[{id, celda:[f,c], valor, ventana:[desde,hasta]|null, unidad_ventana:"pasos", obligatorio:bool}],
  bases:[[f,c],...],
  generaciones:[{n, mejor, media, peor, diversidad, distintos, candidatos:[CANDIDATO...]}],   // 5 a 6 candidatos distintos por generación
  mejor: CANDIDATO,
  parametros_difuso:{nombre:valor,...},      // lo que difiere del difuso por defecto (vacío si no hay parámetros del planeta)
  tiempo_s, evaluaciones, ultima_mejora, capacidad, factor_energia }
CANDIDATO = { orden:[id,...],                // sitios que visita, en orden (los sacrificados no están)
              recargas:[indice,...],         // índices en `orden` TRAS los cuales se para a recargar; -1 = antes del primer sitio
              paradas:[{despues_de:indice, base:[f,c]}],   // lo mismo con la base elegida (mismo orden que `recargas`)
              camino:[[f,c],...]|null,       // ruta celda a celda; null salvo en el mejor de cada generación y en las generaciones 0 y última
              fitness, factible:bool, violaciones:["texto claro",...], sacrificados:[id,...], ciencia, pasos }
```
- `ventana` está en **pasos de la misión**. Dentro de la ventana el sitio vale el 100 %; fuera, el 25 %. No hay espera.
- `diversidad`: distancia media entre pares de la población (fracción de genes distintos, 0 a 1). `distintos` = individuos distintos.
- Los sitios `obligatorio:false` se pueden sacrificar; para ganar hay que visitar los obligatorios y llegar al refugio.
- Un candidato infactible trae en `violaciones` la causa («la batería no alcanza para llegar a el sitio 4, ni recargando»); las ventanas perdidas
  también salen como violaciones («sitio 3: llega en el paso 58, fuera de su ventana 20–45 (vale 25 %)»).

## GET /difuso/reglas

```
{ personalizadas:bool,         // true solo si el usuario editó las reglas de esta partida (los parámetros evolucionados del planeta no cuentan)
  variables:{ distancia|bateria|inclinacion|temperatura : { universo:[min,max], etiquetas:{etiqueta:[puntos...]} } },
  salida:{ universo:[0,1], etiquetas:{parar|lenta|moderada|rapida:[puntos...]} },
  reglas:[{id, si:{variable:etiqueta,...}, entonces:etiqueta, peso:0..1, activa:bool, texto}] }
```
Puntos: 4 = trapecio, 3 = triángulo. Las reglas de fábrica coinciden con `difuso.REGLAS` y `difuso.CONJUNTOS` (R1 a R11). Si el planeta tiene
parámetros evolucionados, el GET devuelve esos puntos y pesos (con `personalizadas:false`).

## PUT /difuso/reglas

Cuerpo `{reglas:[...], variables?:{var:{etiquetas:{et:[puntos]}}}, salida?:{etiquetas:{et:[puntos]}}}`. `variables` y `salida` solo con lo que cambia.
`reglas` es la lista **completa** (se reemplaza); una regla ya conocida puede darse solo con su `id` y lo que cambia (`peso`, `activa`...).
El `peso` multiplica la fuerza de activación de la regla (min de los antecedentes × peso); una regla `activa:false` no dispara. Respuesta: el mismo
formato del GET, con `personalizadas:true`.

Validación (`400`, el texto va en el campo **`motivo`**): variable o etiqueta desconocida, puntos que no son 3 o 4, no crecientes, de ancho cero o fuera del
universo, peso fuera de 0..1, `entonces` desconocido, id repetido o vacío, lista de reglas vacía o sin ninguna regla activa con peso > 0.
Es atómico: si falla no cambia nada.

Desde el PUT, `/difuso`, `/difuso/barrido`, `/ia/paso` y la conducción de la partida en curso usan las reglas editadas (`/difuso` devuelve también
`personalizadas` y las reglas con `peso` y `activa`; sus curvas son las del controlador de la sesión). **No se persiste en disco**, no afecta a otras
partidas, a las evaluaciones ni a los escenarios de comparación, y una partida nueva (`POST /partida`) vuelve a las del planeta.

## DELETE /difuso/reglas

Restaura las reglas del planeta (las evolucionadas si hay, si no las de fábrica). Respuesta: el GET.

## GET /ia/paso (cambios)

- `rna.tramo`: `[{celda:[f,c], probabilidades:{libre, obstáculo, barranco}, distancia, fuente:"rna"|"anticipacion", marcada:bool}]`, ordenado por
  `distancia`, máximo 4. `distancia 1` es la celda siguiente (la RNA de siempre) y `distancia 1` coincide con `celda` de la respuesta; 2 a 4 son las
  celdas de la ruta a esos pasos (RNA de anticipación). `marcada` = la celda quedó como riesgo por esa observación.
- `difuso.tope_conduccion` (solo si aplica): la velocidad con que se avanzó cuando la conducción recortó la del difuso (tope por hielo, viento o pendiente
  del planeta evolucionado, o frenado por un posible barranco a 2 a 4 celdas). `difuso.velocidad_usada` es siempre la velocidad real del paso.
- `difuso.entradas.bateria` sigue en unidades del motor y `bateria_pct` es el % de la capacidad que **usó** el difuso (se convierte una sola vez).

## GET /comparacion

`escenario=jugable_dificil` (Marte) y `jugable_dificil_neptuno` (hielo y viento fuertes), 20 semillas del JSON `docs/COMPARACION_POLITICAS_<escenario>.json`.
La respuesta añade `escenario_recomendado: "jugable_dificil"` y `escenarios_disponibles`. El valor por defecto de `escenario` sigue siendo `congelado`
(cambiarlo rompería el contrato). Cada variante lleva además `ic95_exito` y `ciencia`, `puntaje`, `recargas` con `media` y `error_estandar`; la validación
(semillas 101–120) va en `validacion` con la misma forma que `variantes` y `filas`.

## Diferencias respecto de lo pedido

- `recargas` es el índice del sitio **tras** el cual se recarga (pedido del coordinador de interfaz); `-1` = antes del primero. Se añade `paradas` con la base.
- `camino` solo viene en el mejor de cada generación y en las generaciones 0 y última (el resto `null`), para que el JSON no pase de ~160 KB.
- ~~`/ag` sigue siendo el del AG de orden anterior~~ (corregido tras el QA final, ver «Correcciones tras el QA final»): en la partida jugable `/ag` corre el AG con restricciones.
- `salida` del GET lleva `universo:[0,1]` y `etiquetas` (misma forma que cada variable).


## Correcciones tras el QA final (rama `r23/fix-motor`)

### GET /ag (laboratorio genético)
En la partida jugable (`plan_activo`) corre `planificacion.AGRestringido` (60 × 60, ~1 s en el mapa pequeño) sobre el estado de ahora: posición, batería,
paso, mapa estimado, sitios pendientes con ventanas y opcionales, y bases. Sin plan restringido (escenarios congelados) sigue el AG de orden anterior.
Se conserva todo lo que lee la interfaz: `parametros.{poblacion,generaciones,pesos,parada_sin_mejora}`, `generaciones[]` con `generacion`, `mejor`,
`media`, `peor`, `cruces`, `mutaciones` (de esa generación) y `poblacion` (`[{cromosoma:[[f,c]...], fitness, operacion}]`: los 5 a 6 mejores
**distintos** de la generación, no los 60 individuos), `candidatos[]` con `orden`, `cromosoma` (celdas), `pasos` (lista de `null`: no hay punto de paso por
tramo), `fitness`, `desglose`, más `mejor_ruta`, `mejor_desglose`, `cruces`, `mutaciones`, `generaciones_ejecutadas`, `viable`, `ordenes_evaluados`.
Campos nuevos: `modo:"restricciones"`, `tiempo_s`, `evaluaciones`, `ultima_mejora`, `inicio`, `refugio`, `bases`, `sitios` (id, celda, valor, ventana,
obligatorio), `bateria`, `capacidad`, `factor_energia`, `paso`; por generación `diversidad` y `distintos`; por candidato `ids` (orden por id de sitio),
`recargas`, `paradas`, `camino` (solo el mejor), `violaciones`, `sacrificados`, `ciencia`, `pasos_recorridos`, `ventanas_perdidas`, `recargas_hechas`;
`operacion` ∈ {heuristica, inicial, elite, copia, cruce, copia+mutacion, cruce+mutacion, inmigrante}; `parametros.fitness` y `parametros.nota_pesos`.
Pesos: sin tocarlos el fitness es el del juego; con pesos distintos del defecto, ciencia, distancia y riesgo escalan los términos del juego por
(peso ÷ peso por defecto) y energía y tiempo entran con un coeficiente base de 0,02 (`Problema.fitness_pesos`). `desglose`: ciencia (valor × calidad de
ventana ÷ total), distancia (pasos ÷ pasos de referencia), energía (recargas ÷ (sitios + 1)), riesgo (recargas reparadas ÷ (sitios + 1)), tiempo (ventanas
perdidas ÷ sitios con ventana), inviabilidad (0 o 1).

### GET /comparar (ficha y tabla)
Cada ficha de paso lleva `ciencia_recogida` (valor × calidad de ventana), `ciencia_maxima` y **`ciencia_fraccion`** (0 a 1). La tabla final añade la fila
`{"clave":"ciencia_fraccion","a":..,"b":..,"ganador":..}` entre `puntaje` y `bateria_pct`.

### Planetas: `viento_rotulo`
`GET /planetas` (`mecanicas.viento_rotulo`), `estado.planeta_mecanicas.perfil.viento_rotulo` y `estado.planeta_mecanicas.estado.viento_rotulo` traen el rótulo del viento con la misma escala
(`planetas.ESCALA_VIENTO`: < 0,05 en calma, < 0,25 suave, < 0,50 moderado, < 0,75 fuerte, si no muy fuerte) sobre la intensidad nominal del perfil
(con la ráfaga, sin la escala del nivel). Antes la interfaz rotulaba el viento vivo (0,85 × 0,75 de nivel = 0,64) como «moderado» y el perfil decía «muy fuerte».

### Otros
- `rna.tramo[].marcada` también sale en la celda de distancia 1 (riesgo ≥ 0,5 tras el paso); las celdas con riesgo conocido siguen en el tramo (antes se saltaban).
- El evento `barranco` solo cambia el mundo real: el mapa estimado lo marca la percepción (anticipación de la RNA o sensores), no el evento.
- Las respuestas de más de 4 KB se comprimen con gzip si el cliente manda `Accept-Encoding: gzip` (`/ag/evolucion`: 354 KB → ~12 KB en mapa grande).
