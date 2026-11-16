# Plan por planeta (ev3-d42 B)

Un plan propio para cada uno de los ocho planetas. Todos los valores son **supuestos de simulación**, aproximados
según las referencias del PDF (§3, §4): no son cotas de diseño ni especificaciones de misión. Lo que el motor
usa hoy está marcado; lo que falta se implementa en ARX-50 y ARX-57.

Datos que expone el motor (hoy): `simulador.PERFILES` (nombre, modo), `validar_compatibilidad`, `GET /planetas`,
`POST /partida` con `planeta` y `modo`, y `GET /estado` (`planeta`, `modo_planeta`).

## Temperatura del rover: interna, no ambiente (revisión del orquestador)

El difuso **no lee la temperatura ambiente**: lee la **temperatura interna del rover** (`T_int`), la que llega al
hardware después del blindaje, de la exposición al sol o al calor del suelo y del tiempo que pasa en cada zona.
Así un planeta con 464 °C de ambiente no aborta por sí solo: el calor es un peligro que se acumula, no un aborto
inmediato.

Cálculo por paso (supuesto de simulación):

- `T_int(t+1) = T_int(t) + k_calor · max(0, T_amb_efectiva − T_int(t)) − k_enfriamiento · max(0, T_int(t) − T_amb_efectiva) · sombra`
- `T_amb_efectiva = T_amb_planeta + ganancia_exposicion` (sol directo o suelo caliente) `− reduccion_blindaje`.
- `sombra` vale 1 en una celda a la sombra o en el refugio, y 0 al sol. Un cráter o un barranco dan sombra.
- Tolerancia del hardware (aborto, §12): `T_int > 60 °C` **durante más de 5 pasos seguidos**. Así el calor es un peligro
  que obliga a buscar sombra, no un aborto instantáneo.
- Valores supuestos: `k_calor = 0,08`, `k_enfriamiento = 0,05`, `reduccion_blindaje = 40 °C`, `ganancia_exposicion = 15 °C`.

Efecto sobre cada planeta jugable:

- **Mercurio:** de día `T_amb_efectiva` pasa de 430 °C; a la sombra de un cráter baja a unos 40 °C. El rover tiene
  que alternar sol y sombra, y el difuso reduce velocidad (R10) al subir `T_int`.
- **Venus:** `T_amb_efectiva` ≈ 464 °C con blindaje. La `T_int` sube de forma sostenida; el rover sobrevive unos
  pocos pasos al sol y necesita refugio o sombra (cráter o pared de roca) para enfriarse. Es un reto, no un aborto seguro.
- **Marte, Tierra, Mercurio nocturno, etc.:** la temperatura interna se mantiene en rango normal la mayor parte del tiempo.

## Tabla resumen

| Planeta | Modo | Superficie | Gravedad (supuesto) | Temperatura media (supuesto) | Clima dominante |
|---|---|---|---|---|---|
| Mercurio | rover | rocosa, sin atmósfera | 0,38 g | −170 a 430 °C (día/noche extremos) | radiación, calor de día y grietas de lava |
| Venus | rover | rocosa, bajo nubes ácidas | 0,91 g | ≈ 464 °C | presión, corrosión y flujos de lava |
| Tierra | rover | variada | 1,00 g | 15 °C | lluvia, deslizamientos |
| Marte | rover | rocosa y polvo | 0,38 g | −60 °C | tormentas de arena densa, hielo polar, noche |
| Júpiter | sonda | sin suelo accesible | 2,53 g (sin suelo) | −110 °C en las nubes | vientos y turbulencia |
| Saturno | sonda | sin suelo accesible | 1,07 g (sin suelo) | −140 °C en las nubes | vientos y presión |
| Urano | sonda | helado, sin suelo | 0,89 g (sin suelo) | −195 °C | frío extremo y energía |
| Neptuno | sonda | helado, sin suelo | 1,14 g (sin suelo) | −200 °C | frío, vientos y latencia |

## Por planeta

### Mercurio (rover)
- **Terreno:** cráteres densos y llanuras lisas; sin atmósfera, la luz del sol es directa.
- **Gravedad:** 0,38 g (supuesto). Afecta al consumo de batería por paso (supuesto).
- **Temperatura:** muy alta de día y muy baja de noche. El sensor térmico marca el aborto por encima de la tolerancia del hardware (§12).
- **Enemigos:** drones de vigilancia que patrullan los cráteres.
- **Peligros:** radiación solar (reduce batería y vida de los drones), calor del mediodía (sube `T_int`, ver arriba), frío nocturno.
- **Lava:** grietas incandescentes en las llanuras de día: celdas que queman batería y suben `T_int` rápido, se evitan con
  el veto de la RNA (la celda se marca como peligrosa).
- **Eventos propios:** cambio día/noche (cada N pasos), pico de radiación, impacto de meteorito, apertura de grieta incandescente.
- **Admite:** rover de ruedas. Sonda: no.
- **Datos del motor:** temperatura, radiación (supuesto, por implementar en ARX-50).

### Venus (rover, especial hipotético)
- **Terreno:** llanuras volcánicas y escarpes; visibilidad reducida por nubes.
- **Gravedad:** 0,91 g (supuesto).
- **Temperatura:** ≈ 464 °C constantes: el hardware tiene una vida útil corta en la superficie; el aborto es casi inmediato si no hay refugio cerca.
- **Enemigos:** drones de corrosión (lentos, de alcance corto).
- **Peligros:** corrosión (desgaste de la batería por paso), presión, calor ambiente que sube `T_int` (ver arriba), lluvia ácida no se presupone (PDF §3).
- **Lava:** flujos y charcos de lava en las llanuras volcánicas. Pisar lava quema la batería en un paso y lleva a
  FRACASO; la RNA debe marcar los charcos como peligro y el supervisor vetar el paso (V-SEGURIDAD).
- **Eventos propios:** aumento del desgaste, ráfaga de presión, deterioro del sensor óptico, erupción que abre un flujo nuevo.
- **Admite:** rover especial hipotético con misión breve. Sonda: no.
- **Datos del motor:** temperatura y presión (supuesto, ARX-50).

### Tierra (rover, banco de calibración)
- **Terreno:** variado: llanura, bosque y pendientes; es el escenario de calibración.
- **Gravedad:** 1,00 g (supuesto).
- **Temperatura:** 15 °C de media, con variación moderada.
- **Enemigos:** drones de vigilancia y de deslizamiento.
- **Peligros:** deslizamientos en pendientes fuertes, lluvia que reduce visibilidad.
- **Eventos propios:** lluvia intensa, sismo (ev3-d41), deslizamiento de ladera.
- **Admite:** rover. Sonda: no.
- **Datos del motor:** inclinación y lluvia (supuesto, ARX-50).

### Marte (rover, escenario principal)
- **Terreno:** rocoso con barrancos, dunas de polvo y hielo.
- **Gravedad:** 0,38 g (supuesto).
- **Temperatura:** −60 °C de media, con noche fría.
- **Enemigos:** drones de patrulla y de persecución (los que ya existen en el motor).
- **Peligros:** barrancos, frío nocturno.
- **Tormenta de arena densa:** la tormenta reduce la visión de los sensores (más ruido en la proximidad y en el sensor de borde,
  y menor alcance), y baja la producción solar. Es el evento ya existente de tormenta, con más efecto sobre la RNA y el LIDAR.
- **Hielo (variante polar):** en la zona polar las celdas de hielo deslizan: el rover puede desplazarse una celda más de la
  intentada en una dirección aleatoria (con semilla). El veto de la RNA aprende esas celdas como de riesgo.
- **Eventos propios:** tormenta de arena densa (ya existe, con efecto sobre sensores), noche (ya existe), sismo (marsquake), meteorito, placa de hielo que aparece.
- **Admite:** rover. Sonda: no.
- **Datos del motor:** ya implementados: barrancos, ambiente tormenta y noche, batería, drones.

### Júpiter (sonda)
- **Terreno:** sin suelo accesible: la sonda vuela entre capas de nubes.
- **Gravedad:** 2,53 g en la cima de las nubes (supuesto).
- **Temperatura:** −110 °C en las nubes superiores; sube con la presión.
- **Enemigos:** tormentas de vórtice que empujan la sonda.
- **Peligros:** turbulencia, presión creciente, bloqueo del rodaje (no admite ruedas).
- **Eventos propios:** ráfaga de viento (modo sonda, §6), tormenta de vórtice.
- **Admite:** sonda atmosférica. Rover de ruedas: **no** (CA-07: 400 con sugerencia de sonda).
- **Datos del motor:** viento y presión (supuesto, ARX-50 y ARX-57).

### Saturno (sonda)
- **Terreno:** sin suelo; capas de nubes y anillos como obstáculo visual.
- **Gravedad:** 1,07 g (supuesto, en las nubes).
- **Temperatura:** −140 °C en las nubes.
- **Enemigos:** tormentas de viento zonal.
- **Peligros:** vientos fuertes, presión, comunicación con latencia.
- **Eventos propios:** ráfaga de viento, pérdida de enlace (baja conectividad, ev3-d41).
- **Admite:** sonda. Rover: **no**.
- **Datos del motor:** viento, presión, latencia de enlace (supuesto).

### Urano (sonda)
- **Terreno:** helado, sin suelo sólido de rodadura.
- **Gravedad:** 0,89 g (supuesto).
- **Temperatura:** −195 °C; el frío es el peligro principal.
- **Enemigos:** nubes de hielo que dañan los sensores.
- **Peligros:** frío extremo (reduce la batería), energía limitada.
- **Eventos propios:** descenso de temperatura, avería de sensor.
- **Admite:** sonda. Rover: **no**.
- **Datos del motor:** temperatura y energía (supuesto).

### Neptuno (sonda)
- **Terreno:** helado, con vientos muy rápidos.
- **Gravedad:** 1,14 g (supuesto).
- **Temperatura:** −200 °C.
- **Enemigos:** vientos extremos.
- **Peligros:** frío y vientos, latencia alta de la comunicación.
- **Eventos propios:** ráfaga extrema, pérdida de enlace.
- **Admite:** sonda. Rover: **no**.
- **Datos del motor:** viento, latencia (supuesto).

## Orden de implementación

1. ARX-50 (planeta → escenario, enemigos, eventos y peligros) y ARX-57 (familias de clima): usan esta tabla.
   Incluyen el cálculo de `T_int` y los peligros de lava, hielo y tormenta de arena.
2. ARX-21 (mapa grande configurable) y ARX-66 (condiciones de victoria) entran antes, según el orden del orquestador.
3. Los sensores por planeta (temperatura, viento, radiación) se conectan al motor en ARX-50; hasta entonces el laboratorio del difuso los recibe como entrada manual.
