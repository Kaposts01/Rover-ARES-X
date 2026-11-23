// Adaptador puro (sin DOM ni THREE) del tramo de la ruta que clasificó la RNA, para el panel «Red neuronal».
//
// El motor puede mandar en GET /ia/paso, dentro de `rna` (o al nivel de la respuesta), una lista con una fila por celda de la ruta
// a 1-4 pasos: { celda:[fila,columna], probabilidades:{libre, obstáculo, barranco}, distancia: n_pasos }. Se aceptan estos nombres
// para la lista: rna.tramo, rna.celdas, rna.ruta, rna_tramo, tramo_rna (el primero que sea una lista con filas válidas); las
// probabilidades pueden llamarse `probabilidades`, `probs` o `p`, y las claves «obstaculo»/«obstáculo» valen las dos.
// Si el motor aún no manda el tramo, se muestra la celda que de verdad clasificó la RNA en el paso (`celda` de /ia/paso) con su coordenada
// explícita: nunca una clasificación sin decir de qué celda es.
import { fraccionAPorcentaje } from "./formato.js?v=r15";
import { ubicacionEvento } from "./textos.js?v=r15";

export const CLASES_RNA = ["libre", "obstáculo", "barranco"];
export const MAX_TRAMO = 4;
export const NOTA_SIN_TRAMO = "La RNA clasifica una celda por paso: la de enfrente. Cuando el motor entregue más celdas de la ruta, aparecerán aquí una por fila.";

const esNum = (v) => typeof v === "number" && Number.isFinite(v);
const esCelda = (c) => Array.isArray(c) && c.length >= 2 && esNum(Number(c[0])) && esNum(Number(c[1])) && c[0] !== null && c[1] !== null;

function normalizarProbs(p) {
  if (!p || typeof p !== "object") return null;
  const salida = {};
  let alguna = false;
  for (const c of CLASES_RNA) {
    const v = p[c] !== undefined ? p[c] : (c === "obstáculo" ? p.obstaculo : undefined);
    salida[c] = esNum(v) ? Math.min(1, Math.max(0, v)) : 0;
    if (esNum(v)) alguna = true;
  }
  return alguna ? salida : null;
}

function claseGanadora(p) {
  return CLASES_RNA.reduce((a, c) => (p[c] > p[a] ? c : a), CLASES_RNA[0]);
}

function filaDe(x, posicion, vehiculo) {
  if (!x || typeof x !== "object" || !esCelda(x.celda)) return null;
  const probs = normalizarProbs(x.probabilidades || x.probs || x.p);
  if (!probs) return null;
  const celda = [Number(x.celda[0]), Number(x.celda[1])];
  const distancia = esNum(x.distancia) && x.distancia >= 1 ? Math.round(x.distancia) : null;
  return { celda, distancia, probabilidades: probs, clase: claseGanadora(probs), confianza: probs[claseGanadora(probs)], lugar: ubicacionEvento(celda, esCelda(posicion) ? posicion : null, vehiculo) };
}

// d = respuesta de GET /ia/paso. Devuelve { filas:[...], real:bool } o null si no hay paso de la RNA.
// real = true cuando las filas vienen del tramo que mandó el motor; false = la celda de enfrente (respaldo).
export function adaptarTramoRNA(d, vehiculo = "rover") {
  if (!d || typeof d !== "object") return null;
  const posicion = Array.isArray(d.posicion) ? d.posicion : null;
  const rna = d.rna && typeof d.rna === "object" ? d.rna : null;
  const candidatos = [rna && rna.tramo, rna && rna.celdas, rna && rna.ruta, d.rna_tramo, d.tramo_rna];
  for (const lista of candidatos) {
    if (!Array.isArray(lista)) continue;
    const filas = lista.map((x) => filaDe(x, posicion, vehiculo)).filter(Boolean).slice(0, MAX_TRAMO);
    if (!filas.length) continue;
    filas.sort((a, b) => (a.distancia ?? 99) - (b.distancia ?? 99));
    filas.forEach((f, i) => { if (f.distancia == null) f.distancia = i + 1; });
    return { filas, real: true };
  }
  const probs = normalizarProbs(rna && (rna.probabilidades_usadas || rna.probabilidades));
  if (!probs || !esCelda(d.celda)) return null;
  const celda = [Number(d.celda[0]), Number(d.celda[1])];
  const clase = claseGanadora(probs);
  return { real: false, filas: [{ celda, distancia: 1, probabilidades: probs, clase, confianza: probs[clase], lugar: ubicacionEvento(celda, esCelda(posicion) ? posicion : null, vehiculo) }] };
}

// Frase de cabecera de la decisión: siempre dice de qué celda habla
export function titularRNA(f) {
  const pct = fraccionAPorcentaje(f.confianza);
  return `${f.clase} ${pct} · celda (${f.celda[0]}, ${f.celda[1]})`;
}

// Celdas a marcar en la escena: [{celda, riesgo}] con riesgo = la clasificación no es «libre»
export function celdasAMarcar(tramo) {
  if (!tramo) return [];
  return tramo.filas.map((f) => ({ celda: f.celda, riesgo: f.clase !== "libre" }));
}
