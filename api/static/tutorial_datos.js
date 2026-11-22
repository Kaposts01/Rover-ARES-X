// Tutorial del modo manual: pasos y memoria de «ya lo vi» (puro, sin DOM; se prueba con node).
export const CLAVE_VISTO = "ares.tutorial.manual";

// Las funciones de almacenamiento reciben el storage para poder probarlas; siempre con try/catch (modo privado, bloqueado...)
export function yaVisto(almacen) {
  try { return almacen.getItem(CLAVE_VISTO) === "1"; } catch (e) { return false; }
}
export function marcarVisto(almacen) {
  try { almacen.setItem(CLAVE_VISTO, "1"); return true; } catch (e) { return false; }
}
export function olvidarVisto(almacen) {
  try { almacen.removeItem(CLAVE_VISTO); } catch (e) { /* sin almacenamiento */ }
}

// Cada paso: qué se resalta (selector o varios, el primero que exista y se vea), qué espera del jugador (acción) y la pista mientras espera.
// Las acciones las avisa app.js con el evento «ares:accion»: mover, recomendacion, evento.
export function pasosTutorial(vehiculo = "rover") {
  const el = vehiculo === "sonda" ? "la sonda" : "el rover";
  return [
    {
      id: "mover", objetivo: ["#pad"], preparar: "controles", accion: "mover",
      titulo: "Muévete",
      texto: `Con las flechas del teclado (o W, A, S, D), o con los botones de este pad, mueves ${el} una celda por turno. Las diagonales están en las esquinas del pad. Prueba a dar un paso ahora.`,
      pista: "Esperando que muevas el vehículo…", hecho: "¡Bien! Cada movimiento es un turno: los drones, si hay, también actúan.",
    },
    {
      id: "bateria", objetivo: ["#hud"], accion: null,
      titulo: "Batería y temperatura",
      texto: `Cada paso gasta batería. Si llega a cero, la misión fracasa. La temperatura interna también cuenta: si pasa la tolerancia del planeta durante varios pasos, ${el} entra en riesgo. Vigila estas dos lecturas.`,
    },
    {
      id: "sitios", objetivo: ["#objetivos", "#hud"], accion: null,
      titulo: "Sitios y refugio",
      texto: `Los sitios son los puntos de interés científico del mapa: hay que visitarlos todos pasando por su celda. El refugio es la base: ahí empieza la misión y ahí hay que terminarla. La lista de objetivos cuenta cuántos sitios llevas.`,
    },
    {
      id: "ia", objetivo: ["#det-rec", "#decision"], preparar: "recomendaciones", accion: "recomendacion",
      titulo: "Pide consejo a la IA",
      texto: `En manual conduces tú, pero puedes preguntar qué haría cada modelo (híbrido, RNA, difuso y AG) desde la celda actual, sin que ${el} se mueva. Pulsa «Consultar a los modelos».`,
      pista: "Esperando que consultes a los modelos…", hecho: "Así lees la opinión de cada modelo antes de decidir. Solo es un consejo: tú manejas.",
    },
    {
      id: "evento", objetivo: [".fila-compacta:has(#evento-nombre)", "#controles"], preparar: "misión", accion: "evento",
      titulo: "Lanza un evento",
      texto: "Los eventos ponen a prueba la misión: un barranco nuevo, una tormenta, un meteorito… Elige uno y pulsa «Lanzar». Es práctica: puedes saltarte este paso si prefieres no complicarte la partida.",
      pista: "Esperando que lances un evento…", hecho: "Listo. Los eventos quedan anotados en el registro de la partida.",
    },
    {
      id: "ganar", objetivo: ["#objetivos", "#hud"], accion: null,
      titulo: "Cómo se gana",
      texto: `Ganas cuando has visitado todos los sitios (y destruido los drones obligatorios, si los hay) y ${el} termina la misión en el refugio con batería. Pierdes si te quedas sin batería o sin una ruta posible. Al terminar verás tu resultado y, si es una buena marca, quedará en Récords.`,
    },
  ];
}

export const TEXTO_OFERTA = "Es tu primera vez en el modo manual. ¿Quieres un recorrido de un minuto por los controles?";
export const TEXTO_CAMBIO_MODO = "El tutorial es del modo manual: se cambia el modo a Manual para practicar.";
