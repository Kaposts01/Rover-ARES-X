// Adaptador puro (sin three ni DOM) de GET /ag a la forma que dibuja evolucion3d.js.
// Paquete A, pieza «evolución»: solo usa datos que el rover ya entrega en /ag.

export const MAX_CANDIDATOS_POR_GENERACION = 8;   // tope de rutas dibujadas por generación (la población trae 30)
export const ROTULO_EVOLUCION = "Evolución del AG · orden de visita de los sitios, no el camino recorrido";

// Celda [fila, columna] a coordenadas de escena: misma convención que puntoRuta/construirCapaRiesgo (x = columna + 0,5; z = fila + 0,5)
export function celdaAEscena(celda) {
  if (!celdaValida(celda)) return null;
  const f = Number(celda[0]);
  const c = Number(celda[1]);
  return { x: c + 0.5, z: f + 0.5 };
}

// Número finito de verdad: null, "" y booleanos no cuentan (Number(null) sería 0)
const esNum = (v) => typeof v === "number" ? Number.isFinite(v) : (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)));

function celdaValida(c) {
  return Array.isArray(c) && c.length >= 2 && esNum(c[0]) && esNum(c[1]);
}

// `ag` = respuesta de GET /ag; `posicion` = [fila, columna] del rover cuando se pidió.
// Devuelve null si /ag no trae historial (por ejemplo {sin_sitios: true}).
// `factible` es siempre true: la población de /ag no trae el desglose, y la penalización por inviable no se puede
// distinguir del fitness sin inventarla; por eso no se dibujan rayas rojas.
export function adaptarAG(ag, posicion, max = MAX_CANDIDATOS_POR_GENERACION) {
  const gens = ag && Array.isArray(ag.generaciones) ? ag.generaciones : null;
  if (!gens || !gens.length) return null;
  const tope = Math.max(1, Math.floor(Number(max)) || MAX_CANDIDATOS_POR_GENERACION);
  const inicio = celdaValida(posicion) ? [Number(posicion[0]), Number(posicion[1])] : null;
  const generaciones = gens.map((g, i) => {
    const poblacion = Array.isArray(g && g.poblacion) ? g.poblacion : [];
    const validos = poblacion
      .filter((ind) => ind && Array.isArray(ind.cromosoma) && ind.cromosoma.length && ind.cromosoma.every(celdaValida))
      .filter((ind) => esNum(ind.fitness))
      .map((ind) => ({ ind, fitness: Number(ind.fitness) }));
    validos.sort((a, b) => b.fitness - a.fitness);   // estable: los empates conservan el orden de /ag
    const candidatos = validos.slice(0, tope).map((o, rango) => ({
      puntos: (inicio ? [inicio] : []).concat(o.ind.cromosoma.map((c) => [Number(c[0]), Number(c[1])])),
      rango,
      factible: true,
      fitness: o.fitness,
    }));
    const mejor = g && esNum(g.mejor) ? Number(g.mejor) : (candidatos[0] ? candidatos[0].fitness : 0);
    return { generacion: g && esNum(g.generacion) ? Number(g.generacion) : i, mejor, candidatos };
  });
  // El AG ya corta por falta de mejora: la generación elegida es la última que ejecutó.
  return { generaciones, seleccionada: generaciones.length - 1 };
}

export function textoGeneracion(g, i) {
  const mejor = Number(g && g.mejor);
  return `Generación ${g && Number.isFinite(g.generacion) ? g.generacion : i} · mejor fitness ${Number.isFinite(mejor) ? mejor.toFixed(2).replace(".", ",") : "—"}`;
}
