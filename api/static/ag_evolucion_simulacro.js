// SIMULACRO de GET /ag/evolucion (solo para probar la capa mientras el motor no publica el endpoint; se usa con ?demo en la URL y en las
// pruebas con node). Es un pequeño algoritmo genético de verdad sobre el orden de visita, con datos sintéticos: la distancia es en línea
// recta (en celdas), el tiempo de llegada es la distancia acumulada, las ventanas se reparten alrededor de lo que tardaría cada sitio, la
// batería alcanza para un tramo máximo y hay que pasar por una base de recarga para seguir. Devuelve exactamente la forma del contrato
// que documenta ag_evolucion_datos.js. Determinista por semilla. NO son datos del motor.

function azar(semilla) {
  let s = (semilla >>> 0) || 1;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
}
const dist = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

// ctx = { planeta, inicio, refugio, sitios:[{pos|celda, valor}], bases:[[f,c]] }
export function simularEvolucion(ctx, { generaciones = 24, poblacion = 24, semilla = 7, autonomia = 40 } = {}) {
  const r = azar(semilla);
  const inicio = ctx.inicio || [0, 0], refugio = ctx.refugio || inicio, bases = ctx.bases || [];
  const sitios = (ctx.sitios || []).map((s, i) => ({ id: `S${i + 1}`, celda: s.pos || s.celda, valor: s.valor ?? 1, ventana: null }));
  if (!sitios.length) return { hay_plan: false };
  // ventanas: alrededor del tiempo que tardaría en ir directo; la mitad de los sitios tienen una ventana más estrecha
  sitios.forEach((s, i) => { const t = dist(inicio, s.celda); s.ventana = i % 2 === 0 ? [Math.max(0, t - 4), t + 14 + 3 * i] : [t + 6, t + 30 + 4 * i]; });
  const baseCerca = (p) => bases.reduce((m, b) => (!m || dist(b, p) < dist(m, p) ? b : m), null);

  // Evalúa un orden: recarga antes del sitio cuando el tramo supera la autonomía restante (si hay base). Como en el contrato,
  // `recargas` guarda el índice del sitio TRAS el cual se recarga (-1 = antes del primero)
  function evaluar(orden) {
    let pos = inicio, t = 0, bateria = autonomia, valor = 0, largo = 0;
    const recargas = [], violaciones = [];
    orden.forEach((id, i) => {
      const s = sitios.find((x) => x.id === id);
      let d = dist(pos, s.celda);
      if (d > bateria) {
        const b = baseCerca(pos);
        if (b) { const dd = dist(pos, b) + dist(b, s.celda); recargas.push(i - 1); t += dd; largo += dd; bateria = autonomia - dist(b, s.celda); pos = s.celda; d = 0; }
        else { violaciones.push(`no alcanza la batería para llegar a ${id}`); t += d; largo += d; bateria = 0; pos = s.celda; d = 0; }
      } else { t += d; largo += d; bateria -= d; pos = s.celda; }
      if (t < s.ventana[0]) t = s.ventana[0];                 // espera a que abra la ventana
      else if (t > s.ventana[1]) violaciones.push(`llega a ${id} a las ${Math.round(t)}, fuera de su ventana ${s.ventana[0]}–${s.ventana[1]}`);
      valor += s.valor;
    });
    largo += dist(pos, refugio);
    const fitness = valor - 0.05 * largo - 3 * violaciones.length;
    return { orden: [...orden], recargas, camino: null, fitness, factible: violaciones.length === 0, violaciones };
  }

  const barajar = (a) => { const b = [...a]; for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
  const ids = sitios.map((s) => s.id);
  let pob = Array.from({ length: poblacion }, () => barajar(ids));
  const salida = [];
  for (let g = 0; g < generaciones; g++) {
    const evaluados = pob.map(evaluar).sort((a, b) => b.fitness - a.fitness);
    const f = evaluados.map((c) => c.fitness);
    const unicos = new Set(evaluados.map((c) => c.orden.join(">"))).size;
    salida.push({ n: g, mejor: f[0], media: f.reduce((a, b) => a + b, 0) / f.length, peor: f[f.length - 1], diversidad: unicos / evaluados.length, candidatos: evaluados.slice(0, 8) });
    // siguiente generación: élite + hijos por torneo, cruce de orden y mutación por intercambio
    const torneo = () => { const a = evaluados[Math.floor(r() * evaluados.length)], b = evaluados[Math.floor(r() * evaluados.length)]; return a.fitness >= b.fitness ? a.orden : b.orden; };
    const nueva = evaluados.slice(0, 2).map((c) => c.orden);
    while (nueva.length < poblacion) {
      const p1 = torneo(), p2 = torneo(), corte = 1 + Math.floor(r() * Math.max(1, ids.length - 1));
      let hijo = p1.slice(0, corte); for (const id of p2) if (!hijo.includes(id)) hijo.push(id);
      if (r() < 0.25 && hijo.length > 1) { const i = Math.floor(r() * hijo.length), j = Math.floor(r() * hijo.length); [hijo[i], hijo[j]] = [hijo[j], hijo[i]]; }
      nueva.push(hijo);
    }
    pob = nueva;
  }
  return {
    planeta: ctx.planeta || "Marte", inicio, refugio, sitios, bases, generaciones: salida, mejor: salida[salida.length - 1].candidatos[0],
    parametros_difuso: { umbral_cerca_m: 3, umbral_bateria_baja_pct: 20 }, tiempo_s: 0.1,
  };
}
