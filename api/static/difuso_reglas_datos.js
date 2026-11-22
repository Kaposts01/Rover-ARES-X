// Edición de las reglas difusas: adaptador del contrato, motor de inferencia local (vista previa al instante), validación y simulacro.
// Funciones puras (sin DOM): se prueban con node (api/tests/test_ui_r23_ui2.py).
//
// CONTRATO que se espera del motor (lo implementa el backend; todo campo ausente se tolera):
//   GET  /difuso/reglas -> { personalizadas:bool,
//                            variables:{ nombre:{ universo:[min,max], etiquetas:{ etiqueta:[puntos…] } } },   // 3 puntos = triángulo, 4 = trapecio
//                            salida:{ universo:[min,max], etiquetas:{…} },
//                            reglas:[{ id, si:{variable:etiqueta,…} | [[variable,etiqueta],…], entonces:etiqueta, peso:0..1, activa:bool, texto }] }
//   PUT  /difuso/reglas  cuerpo { reglas:[{id, si:{…}, entonces, peso, activa}], variables?:{…solo las cambiadas}, salida?:{…solo si cambió} }
//                            -> 400 con { motivo } si es inválido; aplica a la sesión actual (/difuso, /difuso/barrido, /ia/paso y la partida).
//   DELETE /difuso/reglas -> restaura las reglas del planeta.
// Motor local (el mismo Mamdani de difuso.py): fuerza de una regla = mínimo de las pertenencias de su antecedente × peso; por cada
// etiqueta de salida se toma la mayor fuerza, se recorta la etiqueta, se agrega con el máximo y la velocidad es el centroide (201
// puntos). Sin ninguna regla activada la salida es la de respaldo (0). El peso multiplica la fuerza: es la lectura que aquí se hace del
// contrato («peso 0..1»); si el motor lo interpreta distinto, los números de la vista previa y los del motor pueden diferir.
import { EDIT } from "./textos.js?v=r14";

export const RESOLUCION = 201;
const esNum = (v) => typeof v === "number" && Number.isFinite(v);
const clonar = (o) => JSON.parse(JSON.stringify(o));
export { clonar };

// ---------- pertenencia ----------
// Trapecio como difuso.trapecio (con a == b o c == d son hombros); 3 puntos = triángulo
export function pertenencia(puntos, x) {
  const p = puntos.length === 3 ? [puntos[0], puntos[1], puntos[1], puntos[2]] : puntos;
  const [a, b, c, d] = p;
  if (x < a || x > d) return 0;
  const izq = b > a ? (x - a) / Math.max(b - a, 1e-12) : (x >= b ? 1 : 0);
  const der = d > c ? (d - x) / Math.max(d - c, 1e-12) : (x <= c ? 1 : 0);
  return Math.min(1, Math.max(0, Math.min(izq, der)));
}
export const soporte = (puntos) => [puntos[0], puntos[puntos.length - 1]];

// ---------- adaptador ----------
function etiquetasValidas(o) {
  const salida = {};
  if (!o || typeof o !== "object") return salida;
  for (const [nombre, pts] of Object.entries(o)) {
    if (Array.isArray(pts) && (pts.length === 3 || pts.length === 4) && pts.every(esNum)) salida[nombre] = pts.slice();
  }
  return salida;
}
function universoValido(u) { return Array.isArray(u) && u.length >= 2 && esNum(u[0]) && esNum(u[1]) && u[1] > u[0] ? [u[0], u[1]] : null; }
function antecedente(si) {
  if (Array.isArray(si)) return si.filter((p) => Array.isArray(p) && p.length >= 2).map((p) => [String(p[0]), String(p[1])]);
  if (si && typeof si === "object") return Object.entries(si).map(([v, e]) => [String(v), String(e)]);
  return [];
}

export function adaptarReglas(datos) {
  if (!datos || typeof datos !== "object") return { estado: "vacio", motivo: EDIT.sinRespuesta };
  const variables = {};
  for (const [nombre, v] of Object.entries(datos.variables && typeof datos.variables === "object" ? datos.variables : {})) {
    const universo = universoValido(v && v.universo);
    const etiquetas = etiquetasValidas(v && v.etiquetas);
    if (universo && Object.keys(etiquetas).length) variables[nombre] = { universo, etiquetas };
  }
  if (!Object.keys(variables).length) return { estado: "vacio", motivo: EDIT.sinVariables };
  const su = universoValido(datos.salida && datos.salida.universo) || [0, 1];
  const salida = { universo: su, etiquetas: etiquetasValidas(datos.salida && datos.salida.etiquetas) };
  const reglas = (Array.isArray(datos.reglas) ? datos.reglas : []).map((r, i) => {
    if (!r || typeof r !== "object") return null;
    return {
      id: r.id === undefined || r.id === null ? `R${i + 1}` : String(r.id),
      si: antecedente(r.si), entonces: String(r.entonces ?? ""),
      peso: esNum(r.peso) ? r.peso : 1, activa: r.activa !== false,
      texto: typeof r.texto === "string" ? r.texto : (typeof r.motivo === "string" ? r.motivo : ""),
    };
  }).filter(Boolean);
  if (!reglas.length) return { estado: "vacio", motivo: EDIT.sinReglas };
  return { estado: "ok", personalizadas: datos.personalizadas === true, variables, salida, reglas };
}

// ---------- inferencia local ----------
function universoSalida(m, n = RESOLUCION) {
  const [a, b] = m.salida.universo;
  return Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
}
// entradas: { distancia, bateria, inclinacion, temperatura } en las unidades del difuso (la batería, de 0 a 100)
export function inferir(m, entradas, { resolucion = RESOLUCION } = {}) {
  const grados = {};
  for (const [nombre, v] of Object.entries(m.variables)) {
    const x = esNum(entradas[nombre]) ? Math.min(v.universo[1], Math.max(v.universo[0], entradas[nombre])) : v.universo[0];
    grados[nombre] = Object.fromEntries(Object.entries(v.etiquetas).map(([e, pts]) => [e, pertenencia(pts, x)]));
  }
  const porSalida = new Map();
  const reglas = m.reglas.map((r) => {
    const g = r.si.map(([v, e]) => (grados[v] && grados[v][e] !== undefined ? grados[v][e] : 0));
    const fuerza = r.activa && g.length ? Math.min(...g) * Math.min(1, Math.max(0, r.peso)) : 0;
    if (fuerza > 0) porSalida.set(r.entonces, Math.max(porSalida.get(r.entonces) || 0, fuerza));
    return { id: r.id, fuerza };
  });
  const universo = universoSalida(m, resolucion);
  const agregado = new Array(universo.length).fill(0);
  for (const [et, f] of porSalida) {
    const pts = m.salida.etiquetas[et];
    if (!pts) continue;
    for (let i = 0; i < universo.length; i++) agregado[i] = Math.max(agregado[i], Math.min(f, pertenencia(pts, universo[i])));
  }
  let sa = 0, sxa = 0;
  for (let i = 0; i < universo.length; i++) { sa += agregado[i]; sxa += universo[i] * agregado[i]; }
  const fallback = sa === 0;
  return { velocidad: fallback ? 0 : sxa / sa, fallback, grados, reglas, universo, agregado };
}

// Barrido de la distancia (de `desde` a `hasta`) con el resto de entradas fijas
export function barrido(m, entradas, { desde = 10, hasta = 1, paso = 1 } = {}) {
  const n = Math.max(1, Math.round(Math.abs(desde - hasta) / paso)) + 1;
  return Array.from({ length: n }, (_, k) => {
    const d = n === 1 ? desde : desde + ((hasta - desde) * k) / (n - 1);
    const r = inferir(m, { ...entradas, distancia: d }, { resolucion: 101 });
    return { distancia: d, velocidad: r.velocidad, reglas: r.reglas.filter((x) => x.fuerza > 0) };
  });
}

// Superficie de la velocidad: distancia (x) por batería (y), el resto de entradas fijas
export function superficie(m, entradas, { nx = 28, ny = 14 } = {}) {
  const dv = m.variables.distancia, bv = m.variables.bateria;
  if (!dv || !bv) return null;
  const xs = Array.from({ length: nx }, (_, i) => dv.universo[0] + ((dv.universo[1] - dv.universo[0]) * i) / (nx - 1));
  const ys = Array.from({ length: ny }, (_, j) => bv.universo[0] + ((bv.universo[1] - bv.universo[0]) * j) / (ny - 1));
  const z = ys.map((y) => xs.map((x) => inferir(m, { ...entradas, distancia: x, bateria: y }, { resolucion: 51 }).velocidad));
  return { xs, ys, z };
}

// ---------- viabilidad y validación ----------
// ¿Puede activarse el antecedente? Cada etiqueta debe existir y cubrir algo dentro del universo de su variable
export function viabilidadAntecedente(regla, m) {
  if (!regla.si.length) return { viable: false, motivo: EDIT.sinCondicion };
  const vistas = new Set();
  for (const [v, e] of regla.si) {
    const variable = m.variables[v];
    if (!variable) return { viable: false, motivo: EDIT.variableDesconocida(v) };
    const pts = variable.etiquetas[e];
    if (!pts) return { viable: false, motivo: EDIT.etiquetaDesconocida(e, v) };
    if (vistas.has(v)) return { viable: false, motivo: EDIT.variableRepetida(v) };
    vistas.add(v);
    let cubre = false;
    for (let i = 0; i <= 40 && !cubre; i++) cubre = pertenencia(pts, variable.universo[0] + ((variable.universo[1] - variable.universo[0]) * i) / 40) > 0;
    if (!cubre) return { viable: false, motivo: EDIT.sinCobertura(e, v) };
  }
  return { viable: true, motivo: "" };
}

const f1 = (v) => Number(v).toFixed(2).replace(/\.?0+$/, "").replace(".", ",");
function validarPuntos(nombre, et, pts, universo, mensajes) {
  const donde = `«${et}» de ${nombre}`;
  for (let i = 1; i < pts.length; i++) {
    if (pts[i] < pts[i - 1]) { mensajes.push({ tipo: "error", donde, texto: EDIT.puntosDesordenados(donde, pts.map(f1).join(", ")) }); return; }
  }
  if (pts[0] === pts[pts.length - 1]) { mensajes.push({ tipo: "error", donde, texto: EDIT.puntosIguales(donde) }); return; }
  if (pts[0] < universo[0] || pts[pts.length - 1] > universo[1]) mensajes.push({ tipo: "error", donde, texto: EDIT.puntosFuera(donde, f1(universo[0]), f1(universo[1])) });
}
// Devuelve [{tipo:"error"|"aviso", donde, texto}]; los errores impiden aplicar
export function validar(m) {
  const mensajes = [];
  for (const [nombre, v] of Object.entries(m.variables)) {
    for (const [et, pts] of Object.entries(v.etiquetas)) validarPuntos(nombre, et, pts, v.universo, mensajes);
    // huecos: valores del universo que ninguna etiqueta cubre
    let hueco = null;
    for (let i = 0; i <= 100; i++) {
      const x = v.universo[0] + ((v.universo[1] - v.universo[0]) * i) / 100;
      const cubierto = Object.values(v.etiquetas).some((pts) => pertenencia(pts, x) > 0);
      if (!cubierto) { hueco = hueco || [x, x]; hueco[1] = x; } else if (hueco) break;
    }
    if (hueco) mensajes.push({ tipo: "aviso", donde: nombre, texto: EDIT.hueco(nombre, f1(hueco[0]), f1(hueco[1])) });
  }
  for (const [et, pts] of Object.entries(m.salida.etiquetas)) validarPuntos("la velocidad", et, pts, m.salida.universo, mensajes);
  for (const r of m.reglas) {
    if (!esNum(r.peso) || r.peso < 0 || r.peso > 1) mensajes.push({ tipo: "error", donde: r.id, texto: EDIT.pesoFuera(r.id) });
    if (!m.salida.etiquetas[r.entonces]) mensajes.push({ tipo: "error", donde: r.id, texto: EDIT.consecuenteDesconocido(r.id, r.entonces) });
    const via = viabilidadAntecedente(r, m);
    if (!via.viable && r.activa) mensajes.push({ tipo: "aviso", donde: r.id, texto: EDIT.noViable(r.id, via.motivo) });
  }
  if (!m.reglas.some((r) => r.activa)) mensajes.push({ tipo: "error", donde: "reglas", texto: EDIT.ningunaActiva });
  return mensajes;
}

// ---------- diferencias y cuerpo del PUT ----------
const mismos = (a, b) => JSON.stringify(a) === JSON.stringify(b);
export function diferencias(base, actual) {
  const reglas = [], variables = [];
  for (const r of actual.reglas) {
    const o = base.reglas.find((x) => x.id === r.id);
    if (!o || o.activa !== r.activa || o.peso !== r.peso || o.entonces !== r.entonces || !mismos(o.si, r.si)) reglas.push(r.id);
  }
  for (const [n, v] of Object.entries(actual.variables)) if (!mismos(v.etiquetas, base.variables[n] && base.variables[n].etiquetas)) variables.push(n);
  const salida = !mismos(actual.salida.etiquetas, base.salida.etiquetas);
  return { reglas, variables, salida, total: reglas.length + variables.length + (salida ? 1 : 0) };
}
export function cuerpoPUT(m, base) {
  const cuerpo = { reglas: m.reglas.map((r) => ({ id: r.id, si: Object.fromEntries(r.si), entonces: r.entonces, peso: r.peso, activa: r.activa })) };
  const d = diferencias(base, m);
  if (d.variables.length) cuerpo.variables = Object.fromEntries(d.variables.map((n) => [n, { universo: m.variables[n].universo, etiquetas: m.variables[n].etiquetas }]));
  if (d.salida) cuerpo.salida = { universo: m.salida.universo, etiquetas: m.salida.etiquetas };
  return cuerpo;
}

// ---------- simulacro: las reglas de fábrica del motor (difuso.py), con la forma del contrato ----------
export function modeloDeFabrica() {
  const si = (...p) => Object.fromEntries(p);
  return adaptarReglas({
    personalizadas: false,
    variables: {
      distancia: { universo: [0, 20], etiquetas: { cerca: [0, 0, 3, 6], media: [4, 10, 16], lejos: [12, 17, 20, 20] } },
      bateria: { universo: [0, 100], etiquetas: { critica: [0, 0, 15, 30], baja: [20, 40, 60], alta: [50, 70, 100, 100] } },
      inclinacion: { universo: [0, 45], etiquetas: { plana: [0, 0, 5, 12], media: [8, 18, 28], fuerte: [24, 32, 45, 45] } },
      temperatura: { universo: [-80, 80], etiquetas: { fria: [-80, -80, -40, -20], templada: [-40, -5, 30], caliente: [10, 35, 80, 80] } },
    },
    salida: { universo: [0, 1], etiquetas: { parar: [0, 0, 0.05, 0.15], lenta: [0.1, 0.25, 0.4], moderada: [0.35, 0.5, 0.65], rapida: [0.6, 0.8, 1, 1] } },
    reglas: [
      { id: "R1", si: si(["distancia", "cerca"]), entonces: "parar", peso: 1, activa: true, texto: "Obstáculo o barranco muy cerca: detenerse." },
      { id: "R2", si: si(["bateria", "critica"]), entonces: "lenta", peso: 1, activa: true, texto: "Batería crítica: avanzar lento para ahorrar energía." },
      { id: "R3", si: si(["inclinacion", "fuerte"], ["distancia", "media"]), entonces: "lenta", peso: 1, activa: true, texto: "Pendiente fuerte con riesgo a distancia media: cautela." },
      { id: "R4", si: si(["bateria", "alta"], ["inclinacion", "plana"], ["distancia", "lejos"]), entonces: "rapida", peso: 1, activa: true, texto: "Condiciones ideales: velocidad máxima." },
      { id: "R5", si: si(["bateria", "baja"], ["distancia", "lejos"]), entonces: "moderada", peso: 1, activa: true, texto: "Batería baja pero camino libre: velocidad media." },
      { id: "R6", si: si(["inclinacion", "media"], ["distancia", "lejos"]), entonces: "moderada", peso: 1, activa: true, texto: "Pendiente media con camino libre." },
      { id: "R7", si: si(["bateria", "alta"], ["distancia", "media"]), entonces: "moderada", peso: 1, activa: true, texto: "Energía suficiente con riesgo a distancia media." },
      { id: "R8", si: si(["inclinacion", "fuerte"]), entonces: "lenta", peso: 1, activa: true, texto: "Pendiente fuerte: velocidad lenta para evitar vuelco." },
      { id: "R9", si: si(["distancia", "media"], ["inclinacion", "plana"]), entonces: "moderada", peso: 1, activa: true, texto: "Terreno plano con riesgo a distancia media." },
      { id: "R10", si: si(["temperatura", "caliente"]), entonces: "moderada", peso: 1, activa: true, texto: "Temperatura alta: el sobrecalentamiento obliga a moderar la marcha." },
      { id: "R11", si: si(["temperatura", "fria"], ["bateria", "baja"]), entonces: "lenta", peso: 1, activa: true, texto: "Frío con batería baja: se reduce la marcha para cuidar la energía." },
    ],
  });
}
