# Contratos JSON de los gráficos (ARX-17)

Todos los endpoints son GET, responden JSON y requieren una partida activa. Sin partida devuelven 409 con `motivo`.
Errores de entrada: 400 con `motivo` legible. Servidor de desarrollo: `http://127.0.0.1:8765`.

## 1. AG: `GET /ag`

Parámetros opcionales: `parada_sin_mejora` (entero ≥ 1; tras n generaciones sin mejora, se detiene).
Ejecuta el AG sobre los sitios pendientes con los parámetros por defecto (población 30, 30 generaciones).

```json
{
  "parametros": {"poblacion": 30, "generaciones": 30, "k_puntos": 3, "prob_cruce": 0.8,
                 "prob_mutacion": 0.2, "elite": 2, "torneo": 3, "semilla": 11,
                 "pesos": {"ciencia": 1.0, "distancia": 0.3, "energia": 0.2},
                 "parada_sin_mejora": null},
  "generaciones": [
    {"generacion": 0, "mejor": 1.84, "media": 0.92, "peor": -0.30,
     "top": [{"cromosoma": [[6, 4], [12, 21], [0, 29], [0, 29]], "fitness": 1.84}],
     "poblacion": [{"cromosoma": [[6, 4], [12, 21], [0, 29], [0, 29]], "fitness": 1.84,
                    "operacion": "inicial"}],
     "cruces": 0, "mutaciones": 0}
  ],
  "candidatos": [{"cromosoma": [[6, 4], [12, 21], [0, 29], [0, 29]], "fitness": 1.84,
                  "desglose": {"fitness": 1.84, "ciencia": 3.0, "distancia": 25.0, "energia": 12.0,
                               "riesgo": 0.0, "tiempo": 46.0, "inviabilidad": 0.0}}],
  "mejor_ruta": [[19, 0], [18, 0]],
  "mejor_desglose": {"fitness": 1.84, "ciencia": 3.0, "distancia": 25.0, "energia": 12.0,
                     "riesgo": 0.0, "tiempo": 46.0, "inviabilidad": 0.0},
  "cruces": 412, "mutaciones": 317,
  "generaciones_ejecutadas": 30
}
```

Notas para la interfaz:
- `generaciones[g].poblacion` es la generación `g`: 30 cromosomas con fitness y `operacion`. Valores de `operacion`: `inicial`, `elite`, `copia`, `cruce`, `cruce+mutacion`, `copia+mutacion`. CA-04 pide la generación 5: `generaciones[5]`.
- `generaciones[g].mejor`, `media` y `peor` alimentan la curva de fitness.
- `candidatos` son las 3 mejores rutas distintas, con su desglose.
- `mejor_desglose.inviabilidad` es la penalización por restricciones duras.

## 2. Difuso: `GET /difuso`

Parámetros opcionales: `distancia` (0 a 20 m), `bateria` (0 a 100 %), `inclinacion` (0 a 45 °).
Sin parámetros usa el estado actual de la partida.

```json
{
  "entradas": {"distancia": 1.0, "bateria": 90.0, "inclinacion": 2.0},
  "universos": {"distancia": {"min": 0.0, "max": 20.0}, "bateria": {"min": 0.0, "max": 100.0},
                "inclinacion": {"min": 0.0, "max": 45.0}},
  "curvas": {
    "distancia": {"x": [0.0, 0.2, "…", 20.0],
                  "conjuntos": {"cerca": [1.0, "…"], "media": [0.0, "…"], "lejos": [0.0, "…"]}}
  },
  "punto_entrada": {"distancia": {"cerca": 1.0, "media": 0.0, "lejos": 0.0},
                    "bateria": {"critica": 0.0, "baja": 0.0, "alta": 1.0},
                    "inclinacion": {"plana": 1.0, "media": 0.0, "fuerte": 0.0}},
  "reglas_activadas": [{"id": "R1", "fuerza": 1.0, "motivo": "barrera cercana"}],
  "reglas": [{"id": "R1", "si": [["distancia", "cerca"]], "entonces": "parar", "motivo": "..."}],
  "salida": {"velocidad": 0.053, "fallback": false,
             "universo": [0.0, 0.01, "…", 1.0],
             "conjuntos": {"parar": [1.0, "…"], "lenta": [0.0, "…"], "moderada": [0.0, "…"], "rapida": [0.0, "…"]},
             "agregado": [0.0, "…"]}
}
```

Cada curva `x` tiene 101 puntos, igual que cada conjunto de `conjuntos`. Las curvas de salida van en `salida.conjuntos`.

## 3. Barrido de distancia (CA-05): `GET /difuso/barrido`

Parámetros: `desde`, `hasta`, `paso` (metros), `bateria` y `inclinacion` opcionales. Máximo 200 valores.
Para CA-05: `desde=10&hasta=1&paso=1`.

```json
{
  "bateria": 90.0, "inclinacion": 2.0,
  "filas": [
    {"distancia": 10.0, "velocidad": 0.61, "fallback": false, "reglas": [{"id": "R7", "fuerza": 0.4}]},
    {"distancia": 1.0, "velocidad": 0.053, "fallback": false, "reglas": [{"id": "R1", "fuerza": 1.0}]}
  ]
}
```

## 4. RNA: `GET /rna`

Parámetros opcionales: `proximidad` (0 a 20 m), `borde` (0 o 1), `gradiente` (−10 a 10), `vibracion` (−5 a 5).
Sin parámetros usa la celda que tiene enfrente el rover, en su rumbo actual.

```json
{
  "entrada": {"proximidad_frontal_m": 2.0, "borde_barranco": 1.0, "gradiente_altura_m": 0.0, "vibracion": 0.0},
  "normalizada": {"proximidad_frontal_m": -0.8, "borde_barranco": 1.6, "gradiente_altura_m": 0.0, "vibracion": 0.0},
  "activaciones": {"oculta_1": [0.0, "…32 valores"], "oculta_2": [0.0, "…16 valores"],
                   "salida_logits": [1.2, -0.4, -2.1]},
  "probabilidades": {"libre": 0.05, "obstáculo": 0.02, "barranco": 0.93},
  "confianza": 0.93,
  "accion": "replanificar",
  "motivos": ["V-BORDE-BARRANCO"]
}
```

Orden de `salida_logits`: libre, obstáculo, barranco.

## 5. RNA: matriz de confusión y recall (CA-06): `GET /rna/evaluacion?modelo=notebook|juego`

`modelo=notebook` (por defecto) es la cifra reproducible del informe: 60 mapas (42/9/9), 400 muestras por mapa,
prueba en los mapas 51-59. `modelo=juego` evalúa el modelo que usa la partida: 30 mapas (21/4/5), 300 muestras por mapa.
La primera llamada de cada modelo entrena y tarda; después queda en caché.

```json
{
  "configuracion": "notebook: 60 mapas (42/9/9), 400 muestras por mapa, semilla 42",
  "clases": ["libre", "obstáculo", "barranco"],
  "matriz_confusion": [[3090, 0, 0], [2, 196, 12], [0, 2, 33]],
  "macro_f1": 0.928,
  "recall_barranco": 0.943,
  "error_calibracion": 0.011,
  "linea_base_exactitud": 0.927,
  "muestras_prueba": 3335,
  "mapas_prueba": [51, 52, 53, 54, 55, 56, 57, 58, 59]
}
```

Las cifras de este ejemplo son las reproducidas del notebook (`modelo=notebook`). Para `modelo=juego` la respuesta tiene la misma forma, con otros valores (recall de barrancos 0,786 en sus mapas de prueba).

Las filas de `matriz_confusion` son la clase real y las columnas la predicha, en el orden de `clases`.
Las cifras de este ejemplo son ilustrativas: los valores reales salen del endpoint.

## 6. Serie por paso: `GET /serie`

Parámetro opcional: `desde` (número de fila).

```json
{
  "total": 2,
  "filas": [
    {"n": 1, "modo": "difuso", "accion": "avanzar", "tecnica": "difuso", "bateria": 99.2,
     "velocidad": 0.61, "p_barranco": 0.01, "fitness": null},
    {"n": 2, "modo": "difuso", "accion": "avanzar", "tecnica": "difuso", "bateria": 98.7,
     "velocidad": 0.58, "p_barranco": 0.02, "fitness": null}
  ],
  "nota": "fitness por paso: solo en modo ag; los demás modos devuelven null"
}
```

Para la curva de fitness de la ruta vigente en cada paso, `fitness` solo está disponible en modo `ag`. Los demás modos no lo registran todavía; queda como brecha abierta.

## 7. Comparación de políticas: `GET /comparacion`

Parámetro opcional: `semillas` (entero de 1 a 40; por defecto 20). Con 20 semillas sirve `docs/COMPARACION_POLITICAS.json`
(generado por `scripts/comparacion_politicas.py`). Otros valores calculan en la petición y tardan.

```json
{
  "semillas": [1, 2, "…", 20],
  "variantes": {
    "hibrido": {"exitos": 19, "n": 20, "tasa_exito": 95.0, "pasos": {"media": 44.5, "mediana": 41.0, "desviacion": 11.019, "rango_intercuartil": 12.75}, "colisiones": {"media": 0.0, "mediana": 0.0, "desviacion": 0.0, "rango_intercuartil": 0.0}, "bateria_final": {"media": 52.05, "mediana": 53.0, "desviacion": 12.15, "rango_intercuartil": 18.5}, "sitios_visitados": {"media": 1.9, "mediana": 2.0, "desviacion": 0.852, "rango_intercuartil": 1.25}},
    "sin_rna": {"…": "misma forma"},
    "sin_difuso": {"…": "misma forma"},
    "sin_ag": {"…": "misma forma"}
  },
  "filas": [{"semilla": 1, "variante": "hibrido", "estado": "EXITO", "exito": true, "pasos": 46,
             "colisiones": 0, "bateria_final": 36.0, "sitios_visitados": 3}],
  "nota": "Arnés: capa de juego (juego/partida.py), misma semilla por variante. Sin atribución causal fuera de estas condiciones (§14). Los intentos a barranco no se miden en el híbrido."
}
```

Cifras reales de la ejecución de 20 semillas (tasa de éxito, mediana de pasos y colisiones media): híbrido 19/20 (41), sin RNA 19/20 (41), sin difuso 19/20 (41), sin AG 19/20 (44). Las cuatro tienen 0 colisiones. El bloque «hibrido» de arriba es el real (copiado del archivo); las demás variantes siguen la misma forma y sus valores reales están en el archivo.

---

# BORRADORES (sprint 2 y 3): datos de prueba para Diseño


Los valores de ejemplo son ilustrativos.

## 8. Planetas: `GET /planetas` (ev3-d39 B)

**Campos de `GET /estado` para el HUD:** `planeta` (texto: `Marte`, `Mercurio`, `Venus`, `Tierra`, `Júpiter`, `Saturno`, `Urano` o `Neptuno`) y `modo_planeta` (`rover` o `sonda`). Por defecto `Marte` y `rover`. La grilla, las rocas y las reglas del motor siguen siendo las de Marte hasta el sprint 3; la interfaz ya dibuja el aspecto de cada planeta (ARX-40). El campo indica el escenario elegido en `POST /partida`.

Lista de planetas (forma real del endpoint):

Sin parámetros. Lista los planetas, su modo y si la partida actual puede usarlos.

```json
{
  "planetas": [
    {"nombre": "Marte", "modo": "rover", "viable": true, "motivo": null},
    {"nombre": "Mercurio", "modo": "rover", "viable": true, "motivo": null},
    {"nombre": "Júpiter", "modo": "sonda", "viable": false,
     "motivo": "Gigante gaseoso sin suelo accesible: no admite rodaje; usa modo sonda"}
  ],
  "modos": ["rover", "sonda"],
  "activo": {"planeta": "Marte", "modo": "rover"}
}
```

Validación al crear partida: `POST /partida` aceptará `planeta` y `modo` (opcionales). Con un planeta no viable para el modo pedido, responde 400 con `motivo` explicando el bloqueo (CA-07).

## 9. Escenarios: `GET /escenarios` (descartado por ev3-d46)

Descartado por ev3-d46 (opción A del usuario): ARX-32 queda cerrada y no se implementa `GET /escenarios`. No hay ruta en el servidor.

Texto original, solo como referencia: estado del modo automático continuo y el resumen acumulado; sirve también para RF-15.

```json
{
  "activo": true,
  "misiones_terminadas": 12,
  "semilla_actual": 406161,
  "dificultad_actual": 2,
  "resumen": {
    "exitos": 9, "fracasos": 3,
    "pasos": {"media": 44.5, "mediana": 41.0, "desviacion": 11.0},
    "bateria_final": {"media": 52.0, "mediana": 53.0, "desviacion": 12.1},
    "replanteos_por_evento": {"media": 1.8, "mediana": 2.0}
  },
  "historial": [
    {"mision": 1, "semilla": 406161, "dificultad": 1, "estado": "EXITO", "pasos": 46,
     "bateria_final": 36.0, "replanteos": 2, "eventos": ["barranco"]}
  ]
}
```

Controles: `POST /escenarios/iniciar` y `POST /escenarios/detener`. Respuesta: el mismo objeto de estado.

## 10. Móviles y eventos: `GET /moviles` (ARX-29: drones; ARX-30: meteoritos)

Ya devuelve drones reales con su trayectoria por turno (últimas 50 posiciones), los eventos del último turno y la ruta planificada frente a la ejecutada. `obstaculos_moviles` va vacía hasta ARX-30; es una clave aparte (no se mezcla con `moviles`), con la misma forma que un elemento de `moviles` y tipo `obstaculo_movil`. Cada dron trae `vida` (puntos de vida, 3 al inicio; un impacto le resta 1). Ejemplo de la forma real:

```json
{"paso": 12, "moviles": [{"id": "dron-1", "tipo": "dron", "pos": [12, 7], "trayectoria": [[11, 7], [12, 7]], "estado": "persecucion", "vida": 3}], "obstaculos_moviles": [], "eventos_del_paso": [{"texto": "dron 1: persecución"}], "ruta": {"planificada": [[19, 0], [18, 0]], "ejecutada": [[19, 0], [18, 0]]}}
```

Borrador original (obstáculos, meteoritos y señales, sin implementar):

Posiciones y trayectorias de los elementos móviles por paso, para animarlos. Incluye los eventos del paso y la ruta planificada frente a la ejecutada.

```json
{
  "paso": 37,
  "moviles": [
    {"id": "dron-1", "tipo": "dron", "pos": [12, 7], "trayectoria": [[11, 7], [12, 7]], "estado": "persecucion"},
    {"id": "obst-2", "tipo": "obstaculo_movil", "pos": [9, 14], "trayectoria": [[9, 13], [9, 14]], "estado": "patrulla"},
    {"id": "meteorito-1", "tipo": "meteorito", "pos": [4, 20], "impacto": false,
     "trayectoria": [[0, 25], [2, 23], [4, 20]], "zona_riesgo": [[3, 19], [3, 20], [4, 19], [4, 20]]}
  ],
  "eventos_del_paso": [
    {"nombre": "meteorito", "efecto": "zona_riesgo", "celdas": [[3, 19], [3, 20]]},
    {"nombre": "senal_biologica", "efecto": "lectura_anomala", "celda": [5, 12], "afirma_vida": false}
  ],
  "ruta": {"planificada": [[19, 0], [18, 0]], "ejecutada": [[19, 0]]}
}
```

Reglas de los contratos:
- `afirma_vida` es siempre `false` en la señal biológica: el sistema nunca confirma vida (PDF §3).
- `impacto` del meteorito indica si ya cayó; si cayó, la celda queda como cráter u obstáculo nuevo.
- `pos` y `trayectoria` son (fila, columna), como en el resto de la API.
- Todo evento de `eventos_del_paso` que actúa sobre el terreno trae `celda` (fila, columna), incluida la señal biológica.

---

## 11. Partida: `POST /partida` (ARX-53)

Cuerpo JSON, todos los campos opcionales:
- `semilla`: entero de 0 a 2147483647. **Ausente, vacía, `null`, `"aleatoria"`, `"aleatorio"` o `"random"`**: el backend elige una semilla aleatoria de 0 a 999999 y la devuelve.
- `nivel`: nombre o número. Nombres: `muy_facil` (1), `facil` (2), `medio` (3), `dificil` (4), `hardcore` (5). También se aceptan con tilde (`fácil`, `difícil`) y en cualquier mayúscula. Los números 1 a 5 siguen valiendo. Por defecto `1`.
- `planeta` y `modo` (ver §8).

La respuesta incluye `semilla` (la usada) y `nivel` como número 1 a 5. `GET /estado` devuelve la misma semilla. Entrada inválida: 400 con `motivo` legible.

```json
{"semilla": 406161, "nivel": 1, "planeta": "Marte", "modo_planeta": "rover", "estado": "EXPLORACION"}
```

## 12. Recomendación: `GET /recomendacion` (ARX-55)

Propone, para la posición actual, el paso que daría cada modelo. Cada modelo corre sobre una copia de la partida: **la partida real no cambia**. Sirve en modo manual, para que los modelos actúen como recomendadores.

```json
{
  "posicion": [19, 0],
  "modo_actual": "manual",
  "propuestas": [
    {"modelo": "hibrido", "accion": "avanzar", "rumbo": "N", "razon": "no hay peligro en la siguiente celda", "motivos": ["OK"]},
    {"modelo": "rna", "accion": "avanzar", "rumbo": "N", "razon": "la RNA ve la celda de enfrente como la más libre", "motivos": ["RNA-MAX-PLIBRE"]},
    {"modelo": "difuso", "accion": "avanzar", "rumbo": "N", "razon": "el difuso da velocidad suficiente", "motivos": ["D-VELOCIDAD-OK"]},
    {"modelo": "ag", "accion": "avanzar", "rumbo": "N", "razon": "el AG sigue la ruta que planificó", "motivos": ["AG-SIGUE-RUTA"]}
  ]
}
```

`rumbo` es el nombre del movimiento (N, NE, E…) o `null` si el modelo no mueve el rover. Cada propuesta puede tardar: el modo `ag` puede replanificar con el algoritmo genético.

---

## 13. Objetivos de la misión: `GET /objetivos` (ARX-66, parcial)

Esquema acordado con Diseño (adaptador.js). Progreso real del motor hoy: sitios científicos visitados (recolectar y
encontrar), drones destruidos y llegar al refugio. Las condiciones por escalón y por planeta quedan para ARX-50.

```json
{
  "mision": "Visitar 3 sitios científicos y llegar al refugio (nivel muy fácil).",
  "condiciones": [
    {"nombre": "Sitios científicos", "progreso": 2, "total": 3, "cumplido": false},
    {"nombre": "Drones destruidos", "progreso": 0, "total": 2, "cumplido": false},
    {"nombre": "Llegar al refugio", "progreso": 0, "total": 1, "cumplido": false}
  ]
}
```

`cumplido` es `true` cuando `progreso` alcanza `total`.

`obligatorio` (bool): decide si la condición bloquea la victoria. Decisión del usuario (14/11): los sitios científicos y el refugio son siempre obligatorios; los drones destruidos son obligatorios desde el nivel Medio (3) y opcionales en Muy fácil y Fácil. La victoria exige solo las condiciones con `obligatorio: true`. Si en Medio o superior faltan drones al llegar al refugio, el refugio queda bloqueado y el objetivo pasa al dron vivo más cercano con ruta real (el aviso dice «Faltan drones»). La caza por BFS aplica a los modos con IA (automático, rna, difuso y ag): el BFS mueve el rover y el disparo lo decide el supervisor con veto (ARX-75). La partida termina en FRACASO solo si no hay forma de cumplirlo: el manual no caza solo, no queda munición, no hay ruta o la batería no alcanza, o pasan más de 300 pasos sin alcanzarlo.

## 14. Paso: `POST /paso` y el `ultimo` de un disparo (ARX-75, ARX-30)

Respuesta de un paso: `{accion, motivos, estado, ultimo, eventos_combate}`.

- **Movimiento:** `ultimo` es el último paso de la bitácora: `paso`, `accion`, `velocidad`, `p_barranco`, `p_obstaculo`,
  `p_libre`, `reglas` y `motivos`.
- **Disparo** (modo automático, o rna, difuso y ag con un dron en línea y en alcance): `accion` es `"disparar"`, `motivos`
  incluye `D-DISPARO-DRON` (o el motivo del veto, ver abajo) y `ultimo` tiene el mismo formato que un movimiento, más
  `rumbo` (dirección del disparo, p. ej. `"N"`) y `objetivo` (id del dron que recibe el disparo). `paso` es el de la
  misión; un disparo no avanza la misión. Los sensores van en `null`.
- **Veto del disparo** (ARX-75, solo rna, difuso y ag, con `veto` encendido): el disparo se bloquea y el motivo queda en
  `motivos` y en el registro. Motivos: `V-DISPARO-MODO-SEGURO`, `V-DISPARO-BATERIA-CRITICA` (batería < 15),
  `V-DISPARO-RIESGO` (celda de riesgo ≥ 0,5). Con `veto` apagado, dispara igual.
- **Meteoritos** (`POST /evento {"nombre": "meteorito"}`, ARX-30): impacto a 2–3 celdas del rover; la celda queda con
  riesgo 1,0 y su entorno con 0,6; el impacto cuesta 5 de batería. La misión evita la zona y puede disparar `V-DISPARO-RIESGO`
  si el rover queda dentro.

Pendiente de §13: su texto dice que rna, difuso y ag no disparan. Desde ARX-75 disparan a un dron en línea; la caza por BFS
de los drones obligatorios sigue siendo solo del modo automático.

### Meteoritos en §10 (ARX-30)

- En `moviles` aparece un elemento por impacto: `{id, tipo: "meteorito", pos, trayectoria, impacto, zona_riesgo}`.
  `pos` es la celda del impacto (la última de la `trayectoria`). `trayectoria` son 2–3 puntos de la caída que terminan en
  `pos`. `impacto` es `true` cuando ya cayó (todos los meteoritos listados han caído). `zona_riesgo` lista las celdas
  libres de la zona (el impacto y sus vecinas).
- Ejemplo real con todos los parámetros explícitos (`POST /partida` con `semilla` 5, `nivel` "medio", `tamano` "pequeno",
  `planeta` "Marte", `modo` "rover"; luego `POST /modo` con `modo` "automatico" y `veto` true; el meteorito cae en el paso 20,
  impacto en (16, 12), igual que en la interfaz):
  `{"id": "meteorito-20", "tipo": "meteorito", "pos": [16, 12], "trayectoria": [[14, 10], [15, 11], [16, 12]], "impacto": true, "zona_riesgo": [[16, 12], [15, 12], [17, 12], [16, 13], [16, 11], [15, 13], [15, 11], [17, 13], [17, 11]]}`
- En `eventos_del_paso`, en el paso del impacto: `{nombre: "meteorito", efecto: "zona_riesgo", celdas}`, con las mismas celdas.
- Caída: solo en partidas jugables (garantía encendida), con probabilidad por paso según el nivel (0,4 % en Muy fácil a
  1,2 % en Hardcore). Las evaluaciones congeladas no tienen meteoritos. El impacto cuesta 5 de batería.
- Ejemplo para probar: Medio, mapa pequeño (20×30), semilla 5, con los parámetros de arriba: meteorito en el paso 20, impacto en (16, 12).
- El disparo queda vetado (`V-DISPARO-RIESGO`) mientras el rover esté en la zona de riesgo (ver §14).
