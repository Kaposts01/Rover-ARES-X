import { coma as comaFormato } from "./formato.js?v=r14";
// Condiciones y aspecto de cada planeta: datos y funciones puras (sin DOM ni THREE). Se prueban con node (api/tests/test_textos_ui.py).
//
// ADAPTADOR ÚNICO de las mecánicas del planeta. El motor (juego/planetas.py) las entrega de dos maneras y aquí se leen las dos:
//
//   GET /estado  ->  planeta_mecanicas = {
//     perfil: { gravedad_g, viento (0..1, base), rumbo_viento ("N","NE","E","SE","S","SO","O","NO": hacia dónde sopla),
//               rafaga_prob, hielo_fraccion (0..1 del mapa), fragilidad_hielo, factor_pendiente, arrastre (% por paso),
//               prob_tormenta_x, resumen, intensidad (del nivel), activa, sobrecosto_medio (% por paso) },
//     estado: { activa, intensidad, viento (actual, ya con ráfaga), rumbo_viento, rafaga (bool), rafaga_restante (pasos),
//               celdas_hielo, resbalones_hielo, desvios_viento, energia_extra (% acumulado en la partida) } }
//   GET /planetas -> planetas[].mecanicas = el mismo `perfil` plano (sin estado vivo): sirve para la ficha del planeta antes de jugar.
//
// Cualquier clave ausente o inválida se tolera: la condición cae al valor de referencia del planeta (solo cuando el motor no manda
// NADA de esa condición) y la fuente («motor» o «referencia») viaja en el resultado. El motor es la fuente de todo lo demás.

const CARDINALES = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SO: 225, O: 270, NO: 315 };
const NOMBRES_CARDINALES = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"];

// Referencia mínima SOLO para cuando no hay respuesta del motor (sin partida y sin /planetas). Son los mismos supuestos del motor.
export const MECANICAS_REFERENCIA = {
  Mercurio: { gravedad_g: 0.38, viento: 0, rumbo_viento: "E", hielo_fraccion: 0 },
  Venus: { gravedad_g: 0.91, viento: 0.2, rumbo_viento: "NO", hielo_fraccion: 0 },
  Tierra: { gravedad_g: 1.0, viento: 0.3, rumbo_viento: "O", hielo_fraccion: 0.08 },
  Marte: { gravedad_g: 0.38, viento: 0.4, rumbo_viento: "E", hielo_fraccion: 0.05 },
  "Júpiter": { gravedad_g: 2.53, viento: 0.9, rumbo_viento: "O", hielo_fraccion: 0 },
  Saturno: { gravedad_g: 1.07, viento: 0.8, rumbo_viento: "NO", hielo_fraccion: 0 },
  Urano: { gravedad_g: 0.89, viento: 0.55, rumbo_viento: "SO", hielo_fraccion: 0.3 },
  Neptuno: { gravedad_g: 1.14, viento: 0.85, rumbo_viento: "SO", hielo_fraccion: 0.3 },
};
const SIN_DATOS = { gravedad_g: 1, viento: 0.2, rumbo_viento: "E", hielo_fraccion: 0 };
export const HIELO_FRACCION_MAXIMA = 0.3;   // la mayor del motor: el brillo del suelo escala contra ella

const acotar = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const esNumero = (v) => typeof v === "number" && Number.isFinite(v);
const numero = (v, defecto) => (esNumero(v) ? v : defecto);

// Dirección a grados (0 = norte, 90 = este) desde un punto cardinal o un número; null si no se entiende
export function gradosDeDireccion(d) {
  if (esNumero(d)) return ((d % 360) + 360) % 360;
  if (typeof d === "string" && d.toUpperCase() in CARDINALES) return CARDINALES[d.toUpperCase()];
  return null;
}
export function nombreDireccion(grados) {
  return NOMBRES_CARDINALES[Math.round((((grados % 360) + 360) % 360) / 45) % 8];
}
// Escala única del viento, la de las descripciones del motor (juego/planetas.py): Marte 0,40 «moderado», Saturno 0,80 «fuerte»,
// Neptuno 0,85 y Júpiter 0,90 «muy fuerte». Se aplica siempre a la intensidad del PERFIL del planeta (no a la del nivel ni a la
// ráfaga), para que la ficha, el HUD y el estado vivo digan lo mismo; la ráfaga se rotula aparte.
export function nombreFuerza(f) {
  if (f < 0.05) return "en calma";
  if (f < 0.35) return "suave";
  if (f < 0.6) return "moderado";
  if (f < 0.85) return "fuerte";
  return "muy fuerte";
}
export function nombreHielo(n) {
  if (n < 0.05) return "sin hielo";
  if (n < 0.3) return "poco";
  if (n < 0.65) return "bastante";
  return "mucho";
}
const f2 = (v) => comaFormato(v, 2);
const f1 = (v) => comaFormato(v, 1);
const pct0 = (v) => `${Math.round(v * 100)} %`;
const veces = (v) => f1(v).replace(",0", "");

// Saca el perfil y el estado vivo de lo que haya: estado.planeta_mecanicas (con perfil/estado), el perfil plano de /planetas o nada.
function leerMecanicas(origen) {
  const o = origen && typeof origen === "object" ? origen : {};
  const m = o.planeta_mecanicas && typeof o.planeta_mecanicas === "object" ? o.planeta_mecanicas : o;
  const perfil = m.perfil && typeof m.perfil === "object" ? m.perfil : (("gravedad_g" in m || "viento" in m || "hielo_fraccion" in m) ? m : {});
  const vivo = m.estado && typeof m.estado === "object" ? m.estado : {};
  return { perfil, vivo };
}

// origen: lo último de /estado, o el `mecanicas` de un elemento de /planetas, o null. planeta: nombre (para la referencia).
export function condicionesPlaneta(origen, planeta) {
  const ref = MECANICAS_REFERENCIA[planeta] || SIN_DATOS;
  const { perfil: p, vivo } = leerMecanicas(origen);
  const intensidad = numero(vivo.intensidad, numero(p.intensidad, 1));
  // gravedad
  const tieneG = esNumero(p.gravedad_g) && p.gravedad_g > 0;
  const gravedad = { g: acotar(tieneG ? p.gravedad_g : ref.gravedad_g, 0.01, 20), fuente: tieneG ? "motor" : "referencia" };
  // viento: el actual (con ráfaga) si lo manda el motor; si no, la base del planeta por la intensidad del nivel
  const base = esNumero(p.viento) ? p.viento : null;
  const actual = esNumero(vivo.viento) ? vivo.viento : (base != null ? base * intensidad : null);
  const gr = gradosDeDireccion(vivo.rumbo_viento != null ? vivo.rumbo_viento : p.rumbo_viento);
  const tieneV = actual != null;
  const viento = {
    fuerza: acotar(tieneV ? actual : ref.viento, 0, 1),               // para las partículas: nunca más de 1
    actual: tieneV ? actual : ref.viento,                              // sin acotar (la ráfaga puede pasar de 1)
    base: base != null ? base * intensidad : ref.viento,
    perfil: base != null ? base : ref.viento,                          // intensidad del perfil del planeta (sin nivel ni ráfaga): la que se rotula
    grados: gr != null ? gr : gradosDeDireccion(ref.rumbo_viento),
    rafaga: vivo.rafaga === true,
    rafagaPasos: Math.max(0, Math.round(numero(vivo.rafaga_restante, 0))),
    rafagaProb: numero(p.rafaga_prob, null),
    fuente: tieneV ? "motor" : "referencia",
    rotuloPerfil: typeof p.viento_rotulo === "string" && p.viento_rotulo ? p.viento_rotulo : null,   // rótulo del motor (escala única); sin él, nombreFuerza
    rotuloVivo: typeof vivo.viento_rotulo === "string" && vivo.viento_rotulo ? vivo.viento_rotulo : null,
  };
  // hielo: fracción del mapa cubierta (la mide el motor); el brillo del suelo escala contra la mayor fracción de los planetas
  const tieneH = esNumero(p.hielo_fraccion);
  const fraccion = acotar(tieneH ? p.hielo_fraccion : ref.hielo_fraccion, 0, 1);
  const hielo = {
    nivel: acotar(fraccion / HIELO_FRACCION_MAXIMA, 0, 1), fraccion, celdas: Math.max(0, Math.round(numero(vivo.celdas_hielo, 0))),
    fragilidad: numero(p.fragilidad_hielo, 1), fuente: tieneH ? "motor" : "referencia",
  };
  const terreno = { pendiente: numero(p.factor_pendiente, 1), arrastre: numero(p.arrastre, 0), polvo: numero(p.prob_tormenta_x, 1), fuente: esNumero(p.factor_pendiente) ? "motor" : "referencia" };
  const vida = {
    hay: Object.keys(vivo).length > 0, activa: vivo.activa !== false,
    resbalones: Math.max(0, Math.round(numero(vivo.resbalones_hielo, 0))), desvios: Math.max(0, Math.round(numero(vivo.desvios_viento, 0))),
    energiaExtra: numero(vivo.energia_extra, null), intensidad,
  };
  const resumen = typeof p.resumen === "string" ? p.resumen : "";
  return { gravedad, viento, hielo, terreno, vivo: vida, sobrecostoMedio: numero(p.sobrecosto_medio, null), resumen };
}

// Qué cambia al jugar en ese planeta: frases cortas a partir de los datos del motor (ficha del planeta, sin estado vivo).
export function queCambia(origen, planeta) {
  const c = condicionesPlaneta(origen, planeta);
  const frases = [];
  const g = c.gravedad.g;
  if (g >= 1.5) frases.push(`gravedad enorme (${f2(g)} g): todo cuesta mucha más batería`);
  else if (g > 0.5) frases.push(`gravedad de ${f2(g)} g: se gasta más batería por paso y al subir`);
  else frases.push(`gravedad baja (${f2(g)} g): subir cuesta poco`);
  if (c.viento.base < 0.05) frases.push("sin viento");
  else frases.push(`viento ${c.viento.rotuloPerfil || nombreFuerza(c.viento.perfil)} hacia el ${nombreDireccion(c.viento.grados)}${c.viento.rafagaProb ? ", con ráfagas" : ""}: de cara gasta más batería y de costado puede desviar`);
  if (c.hielo.fraccion > 0) frases.push(`hielo en el ${pct0(c.hielo.fraccion)} del mapa${c.hielo.fragilidad > 1.05 ? " (muy resbaladizo)" : ""}: a velocidad alta el vehículo resbala`);
  if (c.terreno.pendiente > 1.05) frases.push("regolito suelto: las subidas cuestan más");
  if (c.terreno.arrastre > 0) frases.push("atmósfera densa: frena en cada paso");
  if (c.terreno.polvo > 1.05) frases.push(`tormentas de polvo ${veces(c.terreno.polvo)} veces más frecuentes`);
  return frases;
}
export const textoQueCambia = (origen, planeta) => `Al jugar aquí: ${queCambia(origen, planeta).join("; ")}.`;

// Filas de la ficha del planeta (sistema solar de inicio): datos cortos del motor y, al final, la frase «qué cambia al jugar aquí».
// Sin datos del motor (catálogo sin `mecanicas`) devuelve [] y la ficha queda como estaba.
export function filasFicha(mecanicas, planeta) {
  if (!mecanicas || typeof mecanicas !== "object" || !esNumero(mecanicas.gravedad_g)) return [];
  const c = condicionesPlaneta(mecanicas, planeta);
  const filas = [
    { etiqueta: "Gravedad", valor: `${f2(c.gravedad.g)} g`, tipo: "mecanica" },
    { etiqueta: "Viento", valor: c.viento.base < 0.05 ? "en calma" : `${c.viento.rotuloPerfil || nombreFuerza(c.viento.perfil)} · ${nombreDireccion(c.viento.grados)}`, tipo: "mecanica" },
    { etiqueta: "Hielo", valor: c.hielo.fraccion > 0 ? `${pct0(c.hielo.fraccion)} del mapa` : "sin hielo", tipo: "mecanica" },
  ];
  filas.push({ etiqueta: "Al jugar aquí", valor: queCambia(mecanicas, planeta).join("; ") + ".", tipo: "mecanica-nota" });
  return filas;
}

// Filas del bloque «Condiciones del planeta» del HUD: [etiqueta, valor, fuente]. `paso` = { extra, resbalo } del último paso (opcional).
export function filasCondiciones(c, paso) {
  const calma = c.viento.base < 0.05 && !c.viento.rafaga;
  const dir = nombreDireccion(c.viento.grados);
  let textoViento = calma ? "en calma" : `${c.viento.rafaga ? (c.viento.rotuloVivo || nombreFuerza(c.viento.fuerza)) : (c.viento.rotuloPerfil || nombreFuerza(c.viento.perfil))} · hacia el ${dir}`;   // en ráfaga, la fuerza de la ráfaga en la misma escala;
  if (c.viento.rafaga) textoViento = `ráfaga ${textoViento}${c.viento.rafagaPasos ? ` (${c.viento.rafagaPasos} ${c.viento.rafagaPasos === 1 ? "paso" : "pasos"})` : ""}`;
  const filas = [
    ["Gravedad", `${f2(c.gravedad.g)} g`, c.gravedad.fuente],
    ["Viento", textoViento, c.viento.fuente],
    ["Hielo", c.hielo.fraccion > 0 ? `${pct0(c.hielo.fraccion)} del mapa${c.hielo.fragilidad > 1.05 ? " · muy resbaladizo" : ""}` : "sin hielo", c.hielo.fuente],
  ];
  if (c.terreno.pendiente > 1.05) filas.push(["Pendiente", `las subidas cuestan ×${veces(c.terreno.pendiente)}`, c.terreno.fuente]);
  if (c.terreno.arrastre > 0) filas.push(["Atmósfera", `frena +${f2(c.terreno.arrastre)} % por paso`, c.terreno.fuente]);
  if (c.terreno.polvo > 1.05) filas.push(["Polvo", `tormentas ×${veces(c.terreno.polvo)}`, c.terreno.fuente]);
  if (c.vivo.hay) {
    if (c.vivo.energiaExtra != null) {
      const extra = paso && esNumero(paso.extra) && paso.extra > 0.004 ? ` · este paso +${f2(paso.extra)} %` : "";
      filas.push(["Batería extra", `+${f2(c.vivo.energiaExtra)} % en la partida${extra}`, "motor"]);
    }
    if (c.vivo.resbalones || c.vivo.desvios || (paso && paso.resbalo)) {
      const partes = [];
      if (c.vivo.resbalones) partes.push(`${c.vivo.resbalones} ${c.vivo.resbalones === 1 ? "resbalón" : "resbalones"}`);
      if (c.vivo.desvios) partes.push(`${c.vivo.desvios} ${c.vivo.desvios === 1 ? "desvío" : "desvíos"} por viento`);
      filas.push([paso && paso.resbalo ? "¡Resbaló!" : "Incidentes", partes.join(" · ") || "este paso", "motor"]);
    }
  }
  return filas;
}

// Qué pasó en el último paso comparando dos lecturas vivas consecutivas (aviso de resbalón y sobrecoste del paso)
export function deltaPaso(antes, ahora) {
  if (!antes || !ahora || !antes.vivo.hay || !ahora.vivo.hay) return { extra: 0, resbalo: false, desvio: false };
  const extra = ahora.vivo.energiaExtra != null && antes.vivo.energiaExtra != null ? Math.max(0, ahora.vivo.energiaExtra - antes.vivo.energiaExtra) : 0;
  return { extra, resbalo: ahora.vivo.resbalones > antes.vivo.resbalones, desvio: ahora.vivo.desvios > antes.vivo.desvios };
}

// Aspecto de escena por planeta: colores del cielo, niebla y luz, y los rasgos propios (partículas, centelleos, obstáculos).
// Los colores están pensados para dar contraste con el HUD (texto claro sobre paneles oscuros): sin azules saturados puros.
// `suelo` multiplica la textura (blanco = la textura tal cual). rasgos.viento y rasgos.centelleo se describen en planeta_escena.js.
export const PERFILES = {
  Marte: {
    suelo: 0xffffff, arriba: [0.09, 0.14, 0.27], horizonte: [0.85, 0.58, 0.42], niebla: 0xd9946a, sol: 0xffe0bd, roca: 0x8a5e4a, borde: 0x8c3f24, guijarro: 0x8e5e44,
    intensidadSol: 2.6, nieblaLejos: 2.4,
    rasgos: { obstaculo: "roca", viento: { color: 0xd8a074, tam: 0.07, n: 200 }, centelleo: null },
    firma: "Polvo rojo en suspensión y cráteres",
  },
  Mercurio: {
    suelo: 0xb4b4b8, arriba: [0.02, 0.02, 0.04], horizonte: [0.22, 0.22, 0.25], niebla: 0x3a3a40, sol: 0xfff4e6, roca: 0x6e6e72, borde: 0x5a5a5e, guijarro: 0x7c7c80,
    intensidadSol: 3.3, nieblaLejos: 4.5,
    rasgos: { obstaculo: "roca", viento: null, centelleo: { color: 0xe8e8f4, tam: 0.1, n: 130, alto: 0.05 } },
    firma: "Sin atmósfera: sombras duras y regolito que centellea",
  },
  Venus: {
    suelo: 0xffffff, arriba: [0.35, 0.22, 0.08], horizonte: [0.95, 0.75, 0.4], niebla: 0xd9a24a, sol: 0xffe9b0, roca: 0x4a3424, borde: 0x6b2a12, guijarro: 0x5a4030,
    intensidadSol: 2.0, nieblaLejos: 1.5,
    rasgos: { obstaculo: "roca", viento: { color: 0xffa040, tam: 0.06, n: 140, sube: 0.35 }, centelleo: { color: 0xff7a2a, tam: 0.14, n: 90, alto: 0.04 } },
    firma: "Bruma ácida, grietas de lava y pavesas",
  },
  Tierra: {
    suelo: 0xffffff, arriba: [0.25, 0.45, 0.75], horizonte: [0.7, 0.8, 0.9], niebla: 0xaac8e0, sol: 0xfff2dc, roca: 0x6b6b5a, borde: 0x5a4a3a, guijarro: 0x7a7a68,
    intensidadSol: 2.6, nieblaLejos: 2.6,
    rasgos: { obstaculo: "arbusto", viento: { color: 0xf0f4d8, tam: 0.05, n: 110 }, centelleo: null },
    firma: "Hierba, arbustos y polen al viento",
  },
  Saturno: {
    suelo: 0xe6dcc0, arriba: [0.30, 0.26, 0.18], horizonte: [0.86, 0.78, 0.58], niebla: 0xb9a878, sol: 0xfff0c8, roca: 0xd8c890, borde: 0xd8c890, guijarro: 0xe6dab0,
    intensidadSol: 1.9, nieblaLejos: 1.5,
    rasgos: { obstaculo: "bruma", viento: { color: 0xf3e2b0, tam: 0.08, n: 220 }, centelleo: { color: 0xfff3cc, tam: 0.07, n: 60, alto: 0.15 } },
    firma: "Bancos de bruma dorada y vientos de bandas",
  },
  Urano: {
    suelo: 0xd6ecee, arriba: [0.12, 0.28, 0.32], horizonte: [0.50, 0.76, 0.80], niebla: 0x6fa3a8, sol: 0xdff7ff, roca: 0xb8e4e6, borde: 0xb8e4e6, guijarro: 0xcdeef0,
    intensidadSol: 1.9, nieblaLejos: 1.5,
    rasgos: { obstaculo: "cristal", viento: { color: 0xdff8ff, tam: 0.06, n: 170 }, centelleo: { color: 0xeaffff, tam: 0.1, n: 150, alto: 0.04 } },
    firma: "Cristales de hielo y metano, bruma turquesa",
  },
  Neptuno: {
    suelo: 0xe3ebf6, arriba: [0.09, 0.15, 0.30], horizonte: [0.46, 0.58, 0.78], niebla: 0x62789f, sol: 0xdbe6ff, roca: 0x9db4d6, borde: 0xcfe0f5, guijarro: 0xb4c6e2,
    intensidadSol: 1.9, nieblaLejos: 1.35,
    rasgos: { obstaculo: "nube_o_hielo", viento: { color: 0xd8e6ff, tam: 0.075, n: 260 }, centelleo: { color: 0xf2f8ff, tam: 0.11, n: 170, alto: 0.04 } },
    firma: "Bancos de nubes, formaciones de hielo y vientos violentos",
  },
  "Júpiter": {
    suelo: 0xe6cba2, arriba: [0.34, 0.24, 0.12], horizonte: [0.9, 0.74, 0.5], niebla: 0xc9a77a, sol: 0xffe6c0, roca: 0xe6d6b8, borde: 0xe6d6b8, guijarro: 0xf2e6cc,
    intensidadSol: 1.9, nieblaLejos: 1.5,
    rasgos: { obstaculo: "vortice", viento: { color: 0xf3dcb4, tam: 0.08, n: 240 }, centelleo: null },
    firma: "Vórtices de tormenta y franjas de nubes en movimiento",
  },
};
export function perfilPlaneta(planeta) { return PERFILES[planeta] || PERFILES.Marte; }
export const ES_GIGANTE_PLANETA = (p) => ["Júpiter", "Saturno", "Urano", "Neptuno"].includes(p);
