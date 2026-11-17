# ARX-87 · batería inicial en POST /partida

Decisión: ev3-d82 A (Maestro, por delegación). Base: b84e640. Rama feat/arx-87-bateria-inicial.

## Criterio de hecho
1. POST /partida acepta un campo opcional `bateria` (número). Sin el campo, el juego es idéntico al de hoy (mismo hash del congelado).
2. Rango: entre el 50 % y el 150 % de la batería por defecto del nivel y el tamaño pedidos (`bateria_por_defecto(nivel, filas, columnas)`, la misma fórmula que usa Partida). Fuera de rango, o si no es un número, la respuesta es **422** con un motivo que dice el rango («batería inicial fuera del 50–150 % del valor por defecto: X–Y»).
3. La garantía (ARX-66) se calcula con la batería elegida. Si ninguna variante del mapa es ganable con esa batería, la partida avisa «sin garantía» como hoy.
4. El valor usado va a la configuración exportada (`bateria_inicial`, que ya sale de la misión).
5. La interfaz tiene un campo «Batería inicial» opcional, vacío por defecto, con el rango visible; un 422 se muestra como aviso.

## Pruebas
- Sin campo: /partida con y sin `bateria` nulo da la misma batería por defecto.
- Dentro del rango: la batería de la partida y la exportación son la elegida.
- Fuera del rango (bajo, alto, no numérico): 422 con el motivo.
- Garantía con batería baja: sin variante ganable, aviso «sin garantía».
- Hash del congelado d6fb9079… sin cambios.
