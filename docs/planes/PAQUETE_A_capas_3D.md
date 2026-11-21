# Paquete A · capas 3D de la IA (incertidumbre, evolución, holo)

Rama `feat/paquete-a`, desde `feat/m15-capa-riesgo` (bea5ea6). Solo plan: todavía no hay código. Fuente de las piezas: el proyecto de ejemplo (`vista3d_incertidumbre.js`, `vista3d_evolucion.js`, `vista3d_holo.js`, escritas para three r170 y funciones globales). En el rover van como módulos ES en `api/static/`, con three r160 vendoreado, sin CDN y sin copiar rótulos ni rutas del ejemplo.

Regla de la meta que manda: nada que un rover real no podría saber, y ningún número se ajusta mirando quién gana.

## 1. Incertidumbre frente a la capa de riesgo de M15

**Qué hace cada una.**
- M15 (`construirCapaRiesgo`, `app.js`): una malla de celdas con `riesgo_estimado` ≥ 0,3, rampa amarillo → rojo, opacidad fija 0,45, casilla «Riesgo estimado».
- Ejemplo (`crearIncertidumbre`): una malla de todas las celdas con tres canales por celda: `entropia`, `peligro` y `observada`. Colores: verde = visto y seguro, violeta = duda, rojo = peligro; las celdas sin observar quedan tenues.

**Hallazgo (verificado en `genetico.mapa_estimado` e `integracion.py`).** El rover no tiene hoy ni entropía ni «celdas observadas». Su creencia es una sola matriz `riesgo`: 0,05 de prior en todas las celdas, 1,0 donde el sensor detectó un peligro (p. 0,8), y un peligro no detectado queda en 0,05. Por eso:
- Calcular la entropía a partir de `riesgo` (p. ej. H(p) binaria) no sirve: las celdas detectadas tienen entropía 0 y las libres y las no detectadas casi lo mismo, así que el mapa quedaría uniforme y no informaría nada.
- Inventar `observada` en la interfaz sería política oculta. Hay que exponerla desde el motor.

**Propuesta (recomendada): una sola capa, la de M15, con un segundo canal.** No se crean dos mallas.
1. El motor registra de verdad qué celdas ha mirado el sensor (`mision.observadas`: matriz booleana; se marca en `_actualizar_mapa_estimado` la celda que ve el sensor de proximidad y las celdas del rumbo hasta la distancia leída, y la celda donde está el rover). Es un dato que un rover real tiene: lo que su sensor cubrió.
2. `GET /mapa` suma el campo `observada` (matriz 0/1) al lado de `riesgo_estimado`. Cambio aditivo; no altera partidas, ni el congelado, ni el exigente (se comprueba por hash).
3. La capa de la escena pasa de un solo color a una malla con dos modos, elegidos por la misma casilla (un selector «Riesgo / Incertidumbre»): **Riesgo** (M15 sin cambios) o **Incertidumbre** (celdas no observadas en violeta tenue; observadas y seguras en verde; riesgo ≥ 0,3 en rojo). Un solo `grupoRiesgo`, un solo refresco por paso; nunca se dibujan las dos juntas, así que no se pisan.
4. La «entropía» no se calcula: la incertidumbre es **no observada vs. observada**, que es lo que el rover realmente sabe. Se declara así, sin llamarla entropía.

Alternativas: (B) reemplazar la capa de M15 por la del ejemplo: pierde la rampa que ya pasó QA y obliga a repetirla; (C) no traerla y declarar M15 «riesgo estimado dibujado, sin incertidumbre». Recomiendo la propuesta, con la ficha porque cambia lo que el usuario ve y toca el motor (`integracion.py`, `/mapa`).

Dependencias: va después del merge de M15/M17 (misma zona de `app.js` y del panel). Si se prefiere no tocar el motor, el canal «observada» queda fuera y esta pieza se reduce a la opción C.

## 2. Adaptador de evolución: `/ag` → rutas por celdas

El ejemplo espera `{generaciones: [{generacion, mejor, candidatos: [{puntos: [[fila, col], …], rango, factible}]}], seleccionada}`.

El rover entrega en `GET /ag`: `generaciones[g].poblacion[i] = {cromosoma: [[f, c], …] (orden de visita de sitios), fitness, operacion}`, más `mejor`, `media`, `peor`, `top`. Las rutas por pasos (`pasos`) solo existen para los 3 candidatos finales.

Adaptador (en el cliente, función pura y con prueba):
- `puntos` = posición actual del rover + `cromosoma` en orden. Es la **línea del orden de visita** (segmentos rectos entre sitios), no el camino recorrido; el rótulo de la capa lo dice («orden de visita del AG»). Para los candidatos finales se pueden usar los `pasos` reales.
- `rango` = posición por fitness dentro de la generación (0 = mejor).
- `factible` = `true` salvo que el fitness sea el de una solución penalizada por inviable (se confirma con `_desglose_fitness`; si el desglose no lo dice, se deja siempre `true` y no se dibujan rayas rojas).
- `seleccionada` = índice de la generación elegida (la última salvo parada por falta de mejora).
- Para no dibujar 30 tubos por generación se limita a los 8 primeros por rango (parámetro con nombre, declarado).
- Datos: solo `/ag`, que ya existe. Sin cambios de API.

Ayuda a M11 (curva y selección de generación vistas en la escena) y a M17 (vista del AG); la animación de convergencia no cambia ninguna decisión.

## 3. Adaptador de holo: 5 clases → 3

El panel del ejemplo muestra 5 clases (liso, arenoso, rugoso, rocoso, peligro), `difuso.salidas.{velocidad, cautela, retorno}`, `plan.{orden, tecnica}`, `vetos` y `estado`.

El rover tiene 3 clases en la RNA (`libre`, `obstáculo`, `barranco`; `rna.CLASES`) y una única salida difusa, `velocidad` (más el `fallback`). Adaptador:
- RNA: `GET /rna` → `probabilidades` por nombre de clase (3 barras, no 5); `confianza` y `accion` ya vienen.
- Difuso: `GET /difuso` → `salida.velocidad` (un solo medidor). Se **quitan** «cautela» y «retorno»: el rover no los produce y mostrarlos sería inventar datos.
- Plan: `GET /ag` → `orden_en_juego.metodo` y `mejor_ruta`; `/estado` → `estado`, `veto` y avisos del supervisor para la franja roja.
- Ruta luminosa: `mejor_ruta` convertida a puntos 3D con `alturaTerreno`.
- El panel se dibuja en un `canvas` (sin recursos externos); el texto se sanea como en el ejemplo.
- Una petición por paso, solo con el holograma encendido (mismo criterio que la capa de riesgo).

Ayuda a M17 (explicación por decisión) y M7 (entrada, probabilidades, acción) en la escena.

## 4. Orden de trabajo en la rama

1. Plan aprobado (este documento) y ficha de la incertidumbre (cambia lo visible y toca el motor).
2. Evolución (solo cliente, sin tocar el motor): módulo ES, adaptador con prueba, casilla en la vista del AG.
3. Holo (solo cliente).
4. Incertidumbre, según lo que responda la ficha.
5. Cada pieza: prueba del adaptador, comprobación en Chrome con captura, FPS antes y después, consola limpia.
6. Rama de ensayo con suite completa, hashes del congelado y del exigente, arranque desde clon limpio y búsqueda de claves y rutas.

## 5. Lo que no se trae

Del ejemplo no se trae nada más que las tres piezas adaptadas: ni sus herramientas de prueba, ni su documentación de estado, ni rutas ni rótulos propios, ni recursos cargados por CDN.

## 6. Riesgos y no comprobado

- Rendimiento de las capas con mapa grande (40×60): se mide en Chrome antes de dar la pieza por buena.
- Todavía no se probó nada de esto en el navegador; este documento es solo diseño.
- `factible` y el tope de 8 candidatos son supuestos hasta ver `_desglose_fitness` y la escena.

## 7. Observaciones de la QA (21/11) anotadas, sin implementar

- **H-1 (alta):** el riesgo estimado parte con ~80 % de los peligros reales ya marcados (`genetico.mapa_estimado`). Decisión del usuario en la ficha ev3-d91; no se toca hasta que se responda.
- **H-2 (media):** con el holograma encendido cada paso pide `/ag` y el AG se vuelve a correr casi siempre (la clave de caché incluye posición y riesgo). No altera la partida. Pendiente: medir los ms por paso y, si pesa, pedir `/ag` cada N pasos.
- **H-3 (media):** el panel del holograma va con `depthTest: false`; con la cámara muy cerca puede solapar al rover. Falta comprobarlo en el navegador.
- **H-5 (baja):** los avisos `.capa-nota` no tienen `aria-live` y el holograma no tiene alternativa de texto (los mismos datos están en los paneles de RNA, difuso y AG).
- **H-7 (baja):** la tira de decisiones solo se repinta con un paso nuevo.
- **H-8 (baja):** sin pruebas automáticas de los módulos three ni del selector; las capturas cubren lo visual.
- Resueltas: **H-4** (el rótulo aclara que la curva solo une los sitios) y **H-9** (el plan ya no nombra los recursos del ejemplo).
