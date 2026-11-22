// Adaptador puro (sin DOM ni THREE) de la capa «Evolución del AG» sobre el mapa.
//
// CONTRATO que se espera de GET /ag/evolucion (lo implementa el motor; aquí todo campo ausente se tolera):
//   { planeta, inicio:[f,c], refugio:[f,c],
//     sitios:[{id, celda:[f,c], valor, ventana:[desde,hasta]|null}], bases:[[f,c],...],
//     generaciones:[{n, mejor, media, peor, diversidad,
//                    candidatos:[{orden:[id,...], recargas:[indice_en_orden TRAS el cual se recarga; -1 = antes del primero], paradas:[{despues_de, base:[f,c]}], camino:[[f,c],...]|null,
//                                 fitness, factible, violaciones:["texto",...]}]}],
//     mejor:{...candidato...}, parametros_difuso:{nombre:valor,...}, tiempo_s }
//   {hay_plan:false} o 404 si no hay partida -> estado vacío.
// Reglas de tolerancia: `camino` nulo = se unen inicio, sitios en orden (y la base de recarga más cercana donde se recarga) y
// refugio con segmentos rectos; `media`/`mejor`/`peor` ausentes se calculan de los candidatos; `diversidad` ausente se estima con la
// fracción de órdenes distintos; un id de `orden` que no está en `sitios` se ignora; `factible` que no es booleano = «sin dato».
//
// RESPALDO (mientras el motor no publique /ag/evolucion): desdeLaboratorio() convierte la respuesta de GET /ag del laboratorio
// genético (generaciones con población de cromosomas = celdas de sitios) a la misma forma, con los sitios y las bases de /mapa.
import { EVO } from "./textos.js?v=r14";

export const MAX_RUTAS_POR_GENERACION = 6;     // las mejores que se dibujan por generación (la población trae ~30)
export const VELOCIDADES_EVO = [[0.5, "×0,5"], [1, "×1"], [2, "×2"], [4, "×4"]];

const esNum = (v) => typeof v === "number" && Number.isFinite(v);
const num = (v) => (esNum(v) ? v : (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)) ? Number(v) : null));
export function celdaValida(c) {
  return Array.isArray(c) && c.length >= 2 && num(c[0]) !== null && num(c[1]) !== null && c[0] !== null && c[1] !== null;
}
const aCelda = (c) => [Number(c[0]), Number(c[1])];
const clave = (c) => `${c[0]},${c[1]}`;
const distancia2 = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;

function vacio(motivo) { return { estado: "vacio", motivo, generaciones: [], sitios: [], bases: [] }; }

function normalizarSitios(lista) {
  const sitios = [];
  const vistos = new Set();
  for (const s of Array.isArray(lista) ? lista : []) {
    if (!s || typeof s !== "object") continue;
    const celda = celdaValida(s.celda) ? aCelda(s.celda) : (celdaValida(s.pos) ? aCelda(s.pos) : null);
    const id = s.id === undefined || s.id === null ? null : String(s.id);
    if (!celda || id === null || vistos.has(id)) continue;
    vistos.add(id);
    const v = Array.isArray(s.ventana) && s.ventana.length >= 2 && num(s.ventana[0]) !== null && num(s.ventana[1]) !== null && s.ventana[0] !== null && s.ventana[1] !== null
      ? [Number(s.ventana[0]), Number(s.ventana[1])] : null;
    sitios.push({ id, celda, valor: num(s.valor), ventana: v });
  }
  return sitios;
}

function baseMasCercana(bases, desde) {
  let mejor = null, dm = Infinity;
  for (const b of bases) { const d = distancia2(b, desde); if (d < dm) { dm = d; mejor = b; } }
  return mejor;
}

function normalizarCandidato(c, ctx) {
  if (!c || typeof c !== "object") return null;
  const porId = ctx.porId;
  const orden = (Array.isArray(c.orden) ? c.orden : []).map((x) => String(x)).filter((id) => porId.has(id));
  if (!orden.length) return null;
  const n = orden.length;
  // Contrato del motor: `recargas` = índices de `orden` TRAS los cuales se para a recargar; -1 = antes del primer sitio.
  // `paradas` trae lo mismo con la base elegida ({despues_de, base}); sin ella se usa la base más cercana.
  const recargas = [...new Set((Array.isArray(c.recargas) ? c.recargas : []).map(num).filter((i) => i !== null && Number.isInteger(i) && i >= -1 && i < n))].sort((a, b) => a - b);
  const camino = Array.isArray(c.camino) ? c.camino.filter(celdaValida).map(aCelda) : [];
  const baseDelMotor = new Map();
  for (const p of Array.isArray(c.paradas) ? c.paradas : []) {
    if (p && typeof p === "object" && num(p.despues_de) !== null && celdaValida(p.base)) baseDelMotor.set(Number(p.despues_de), aCelda(p.base));
  }
  // Polilínea recta de respaldo: inicio → sitios (con la base de recarga tras el sitio que toca) → refugio
  const puntos = [];
  const paradas = [];
  const base = (i, p) => baseDelMotor.get(i) || (ctx.bases.length && p ? baseMasCercana(ctx.bases, p) : null);
  const parar = (i) => {
    if (!recargas.includes(i)) return;
    const b = base(i, puntos.length ? puntos[puntos.length - 1] : (orden.length ? porId.get(orden[0]).celda : null));
    if (b) { puntos.push(b); paradas.push({ indice: i, celda: b }); }
  };
  if (ctx.inicio) puntos.push(ctx.inicio);
  parar(-1);
  orden.forEach((id, i) => { puntos.push(porId.get(id).celda); parar(i); });
  if (ctx.refugio) puntos.push(ctx.refugio);
  // Con camino real, las bases usadas son las que el camino pisa
  let basesUsadas = paradas.map((p) => p.celda);
  if (camino.length >= 2) {
    const pisadas = new Set(camino.map(clave));
    basesUsadas = ctx.bases.filter((b) => pisadas.has(clave(b)));
  }
  return {
    orden, recargas, camino: camino.length >= 2 ? camino : null,
    puntos: camino.length >= 2 ? camino : puntos,
    rectas: camino.length < 2,          // true = la línea une los sitios en orden, no es el recorrido
    paradas, basesUsadas,
    fitness: num(c.fitness),
    factible: typeof c.factible === "boolean" ? c.factible : null,
    violaciones: (Array.isArray(c.violaciones) ? c.violaciones : []).filter((t) => typeof t === "string" && t.trim()).slice(0, 6),
  };
}

function media(v) { const x = v.filter((y) => y !== null); return x.length ? x.reduce((a, b) => a + b, 0) / x.length : null; }

function normalizarGeneracion(g, i, ctx, max) {
  if (!g || typeof g !== "object") return null;
  const todos = (Array.isArray(g.candidatos) ? g.candidatos : []).map((c) => normalizarCandidato(c, ctx)).filter(Boolean);
  const ordenados = todos.map((c, k) => ({ c, k })).sort((a, b) => {
    const fa = a.c.fitness, fb = b.c.fitness;
    if (fa === null && fb === null) return a.k - b.k;
    if (fa === null) return 1;
    if (fb === null) return -1;
    return fb - fa || a.k - b.k;
  }).map((o) => o.c);
  // órdenes repetidos (la población converge): se dibuja uno solo y se cuenta cuántos eran
  const vistos = new Map();
  for (const c of ordenados) {
    const k = `${c.orden.join(">")}|${c.recargas.join(",")}`;
    if (vistos.has(k)) vistos.get(k).copias += 1; else vistos.set(k, { ...c, copias: 1 });
  }
  const candidatos = [...vistos.values()].slice(0, Math.max(1, max)).map((c, rango) => ({ ...c, rango }));
  const fits = todos.map((c) => c.fitness);
  const distintos = todos.length > 1 ? new Set(todos.map((c) => c.orden.join(">"))).size / todos.length : null;
  const mejor = num(g.mejor) ?? (fits.some((f) => f !== null) ? Math.max(...fits.filter((f) => f !== null)) : null);
  const peor = num(g.peor) ?? (fits.some((f) => f !== null) ? Math.min(...fits.filter((f) => f !== null)) : null);
  return {
    n: num(g.n) ?? num(g.generacion) ?? i,
    mejor, peor, media: num(g.media) ?? media(fits),
    diversidad: num(g.diversidad) ?? distintos,
    candidatos,
  };
}

// datos = cuerpo de GET /ag/evolucion (o null/undefined si no hubo respuesta)
export function adaptarEvolucion(datos, { fuente = "motor", max = MAX_RUTAS_POR_GENERACION } = {}) {
  if (!datos || typeof datos !== "object") return vacio(EVO.sinRespuesta);
  if (datos.hay_plan === false) return vacio(EVO.sinPlan);
  if (datos.sin_sitios) return vacio(EVO.sinSitios);
  const sitios = normalizarSitios(datos.sitios);
  if (!sitios.length) return vacio(EVO.sinSitiosEnDatos);
  const ctx = {
    porId: new Map(sitios.map((s) => [s.id, s])),
    inicio: celdaValida(datos.inicio) ? aCelda(datos.inicio) : null,
    refugio: celdaValida(datos.refugio) ? aCelda(datos.refugio) : null,
    bases: (Array.isArray(datos.bases) ? datos.bases : []).filter(celdaValida).map(aCelda),
  };
  const generaciones = (Array.isArray(datos.generaciones) ? datos.generaciones : []).map((g, i) => normalizarGeneracion(g, i, ctx, max)).filter((g) => g && g.candidatos.length);
  if (!generaciones.length) return vacio(EVO.sinGeneraciones);
  const ultima = generaciones[generaciones.length - 1];
  const mejor = normalizarCandidato(datos.mejor, ctx) || ultima.candidatos[0];
  const pd = datos.parametros_difuso && typeof datos.parametros_difuso === "object" ? Object.entries(datos.parametros_difuso).filter(([, v]) => esNum(v) || typeof v === "string") : [];
  return {
    estado: "ok", fuente, planeta: typeof datos.planeta === "string" ? datos.planeta : null,
    inicio: ctx.inicio, refugio: ctx.refugio, sitios, bases: ctx.bases,
    generaciones, seleccionada: generaciones.length - 1, mejor,
    parametrosDifuso: pd, tiempoS: num(datos.tiempo_s),
    hayVentanas: sitios.some((s) => s.ventana), hayRecargas: generaciones.some((g) => g.candidatos.some((c) => c.recargas.length)),
  };
}

// ctx = { inicio:[f,c], refugio:[f,c], sitios:[{pos|celda, valor}], bases:[[f,c]] } (de /estado y /mapa). ag = cuerpo de GET /ag.
export function desdeLaboratorio(ag, ctx = {}, opciones = {}) {
  if (!ag || typeof ag !== "object") return vacio(EVO.sinRespuesta);
  if (ag.sin_sitios) return vacio(EVO.sinSitios);
  const gens = Array.isArray(ag.generaciones) ? ag.generaciones : [];
  if (!gens.length) return vacio(EVO.sinGeneraciones);
  const conocidos = (Array.isArray(ctx.sitios) ? ctx.sitios : []).filter((s) => s && (celdaValida(s.pos) || celdaValida(s.celda)));
  const idDeCelda = new Map();
  const sitios = [];
  const registrar = (celda, valor) => {
    const k = clave(celda);
    if (idDeCelda.has(k)) return idDeCelda.get(k);
    const id = `S${sitios.length + 1}`;
    idDeCelda.set(k, id);
    sitios.push({ id, celda, valor: num(valor), ventana: null });
    return id;
  };
  for (const s of conocidos) registrar(aCelda(celdaValida(s.pos) ? s.pos : s.celda), s.valor);
  const candidato = (cromosoma, fitness) => (Array.isArray(cromosoma) && cromosoma.every(celdaValida) && cromosoma.length
    ? { orden: cromosoma.map((c) => registrar(aCelda(c), null)), recargas: [], camino: null, fitness, factible: null, violaciones: [] } : null);
  const generaciones = gens.map((g, i) => {
    const pob = (Array.isArray(g && g.poblacion) ? g.poblacion : []).map((p) => (p && esNum(p.fitness) ? candidato(p.cromosoma, p.fitness) : null)).filter(Boolean);
    return { n: num(g && g.generacion) ?? i, mejor: num(g && g.mejor), media: num(g && g.media), peor: num(g && g.peor), candidatos: pob };
  });
  // el mejor del laboratorio trae el desglose: la inviabilidad dice si el orden es viable
  let mejor = null;
  const c0 = Array.isArray(ag.candidatos) ? ag.candidatos[0] : null;
  if (c0) {
    mejor = candidato(c0.cromosoma || c0.orden, num(c0.fitness));
    const inv = c0.desglose && num(c0.desglose.inviabilidad);
    if (mejor && inv !== null && inv !== undefined) { mejor.factible = inv === 0; if (inv !== 0) mejor.violaciones = [EVO.inviableLab]; }
  }
  const crudo = {
    planeta: ctx.planeta, inicio: ctx.inicio, refugio: ctx.refugio, bases: ctx.bases || [], sitios,
    generaciones: generaciones.map((g) => ({ ...g })), mejor, tiempo_s: null,
  };
  // sin los sitios pendientes de /mapa (ya visitados) solo se dibujan los que aparecen en la población
  const usados = new Set(generaciones.flatMap((g) => g.candidatos.flatMap((c) => c.orden)));
  crudo.sitios = sitios.filter((s) => usados.has(s.id));
  return adaptarEvolucion(crudo, { fuente: "laboratorio", ...opciones });
}

// ---------- lecturas para la interfaz ----------
const f2 = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(2).replace(".", ","));
export const textoGeneracionEvo = (g, i, total) => `Generación ${g ? g.n : i} de ${total - 1} · mejor ${f2(g && g.mejor)} · media ${f2(g && g.media)}`;

export const textoVentana = (s) => (s.ventana ? `ventana ${s.ventana[0]}–${s.ventana[1]}` : "sin ventana de tiempo");

// Lectura del candidato bajo el puntero: orden de sitios, paradas de recarga, fitness, factibilidad y restricción violada
export function lecturaCandidato(c, evo, g) {
  if (!c) return null;
  const porId = new Map((evo.sitios || []).map((s) => [s.id, s]));
  const recargaTras = new Set(c.recargas);   // índices de `orden` tras los cuales se recarga; -1 = antes del primer sitio
  const pasos = c.orden.map((id, i) => `${id}${recargaTras.has(i) ? ` → ${EVO.recarga}` : ""}`);
  if (recargaTras.has(-1)) pasos.unshift(EVO.recarga);
  const lineas = [
    { clave: EVO.orden, valor: pasos.join(" → ") },
    { clave: EVO.recargas, valor: c.recargas.length ? c.recargas.map((i) => (i < 0 ? EVO.antesDelPrimero : `${EVO.despuesDe} ${c.orden[i]}`)).join(", ") : EVO.sinRecargas },
    { clave: EVO.fitness, valor: `${f2(c.fitness)}${c.rango === 0 ? ` (${EVO.mejorDeLaGeneracion})` : ""}${c.copias > 1 ? ` · ${EVO.copias(c.copias)}` : ""}` },
    { clave: EVO.factible, valor: c.factible === true ? EVO.si : c.factible === false ? EVO.no : EVO.sinDato, tipo: c.factible === false ? "mal" : c.factible === true ? "bien" : "" },
  ];
  if (c.factible === false) lineas.push({ clave: EVO.restriccion, valor: c.violaciones.length ? c.violaciones.join("; ") : EVO.sinDetalle, tipo: "mal" });
  else if (c.violaciones.length) lineas.push({ clave: EVO.penalizaciones, valor: c.violaciones.join("; ") });   // factible, pero pierde ventanas o sacrifica sitios opcionales
  const ventanas = c.orden.map((id) => porId.get(id)).filter((s) => s && s.ventana).map((s) => `${s.id}: ${s.ventana[0]}–${s.ventana[1]}`);
  if (ventanas.length) lineas.push({ clave: EVO.ventanas, valor: ventanas.join(" · ") });
  return { titulo: `${EVO.candidato} ${c.rango + 1}${g ? ` · ${EVO.generacion} ${g.n}` : ""}`, lineas, rectas: c.rectas };
}

// Series para las curvas del panel: [{x, y}] sin huecos raros
export function seriesEvolucion(evo) {
  const g = evo.generaciones;
  const par = (campo) => g.map((x, i) => [i, x[campo]]);
  return { mejor: par("mejor"), media: par("media"), diversidad: par("diversidad") };
}
