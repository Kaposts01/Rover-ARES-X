// Condiciones y aspecto de cada planeta: datos y funciones puras (sin DOM ni THREE). Se prueban con node (api/tests/test_textos_ui.py).
//
// ADAPTADOR ÚNICO de las mecánicas del planeta (gravedad, viento, hielo). El motor las está incorporando en otra rama; la interfaz
// las lee de /estado SI EXISTEN y, si no, usa los valores de referencia de aquí. Para conectar el motor basta con que /estado traiga:
//
//   estado.planeta_mecanicas = {
//     gravedad: 0.38,                                   // número, en g terrestres (también vale { g: 0.38 })
//     viento:   { fuerza: 0.6, direccion: "NE" },       // fuerza 0..1 (también vale un número solo); dirección: punto cardinal
//                                                       //   ("N","NE","E","SE","S","SO","O","NO") o grados (0 = norte, 90 = este)
//     hielo:    { nivel: 0.8 },                         // nivel 0..1 (también vale un número, o true/false)
//   }
//
// Cualquier clave ausente o inválida cae al valor de referencia del planeta; la fuente de cada una («motor» o «referencia») viaja en
// el resultado para rotularla en el HUD. Nada de la interfaz depende de que el motor las mande.

const CARDINALES = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SO: 225, O: 270, NO: 315 };
const NOMBRES_CARDINALES = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"];

// Valores de referencia (aproximados y solo ilustrativos) cuando el motor no manda nada
export const MECANICAS_REFERENCIA = {
  Mercurio: { gravedad: 0.38, viento: { fuerza: 0, direccion: 90 }, hielo: { nivel: 0.05 } },
  Venus: { gravedad: 0.9, viento: { fuerza: 0.2, direccion: 270 }, hielo: { nivel: 0 } },
  Tierra: { gravedad: 1.0, viento: { fuerza: 0.3, direccion: 225 }, hielo: { nivel: 0.1 } },
  Marte: { gravedad: 0.38, viento: { fuerza: 0.4, direccion: 45 }, hielo: { nivel: 0.1 } },
  "Júpiter": { gravedad: 2.53, viento: { fuerza: 0.9, direccion: 90 }, hielo: { nivel: 0 } },
  Saturno: { gravedad: 1.07, viento: { fuerza: 0.8, direccion: 90 }, hielo: { nivel: 0.15 } },
  Urano: { gravedad: 0.89, viento: { fuerza: 0.55, direccion: 135 }, hielo: { nivel: 0.8 } },
  Neptuno: { gravedad: 1.14, viento: { fuerza: 1, direccion: 270 }, hielo: { nivel: 0.9 } },
};
const SIN_DATOS = { gravedad: 1, viento: { fuerza: 0.2, direccion: 90 }, hielo: { nivel: 0 } };

const acotar = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const esNumero = (v) => typeof v === "number" && Number.isFinite(v);

// Dirección a grados (0 = norte, 90 = este) desde un punto cardinal o un número; null si no se entiende
export function gradosDeDireccion(d) {
  if (esNumero(d)) return ((d % 360) + 360) % 360;
  if (typeof d === "string" && d.toUpperCase() in CARDINALES) return CARDINALES[d.toUpperCase()];
  return null;
}
export function nombreDireccion(grados) {
  return NOMBRES_CARDINALES[Math.round((((grados % 360) + 360) % 360) / 45) % 8];
}
export function nombreFuerza(f) {
  if (f < 0.05) return "en calma";
  if (f < 0.3) return "suave";
  if (f < 0.65) return "moderado";
  return "fuerte";
}
export function nombreHielo(n) {
  if (n < 0.05) return "sin hielo";
  if (n < 0.3) return "poco";
  if (n < 0.65) return "bastante";
  return "mucho";
}

// planeta: nombre; estado: lo último de /estado (puede ser null). Devuelve las tres condiciones normalizadas.
export function condicionesPlaneta(estado, planeta) {
  const ref = MECANICAS_REFERENCIA[planeta] || SIN_DATOS;
  const m = estado && typeof estado === "object" && estado.planeta_mecanicas && typeof estado.planeta_mecanicas === "object" ? estado.planeta_mecanicas : {};
  // gravedad
  let g = esNumero(m.gravedad) ? m.gravedad : (m.gravedad && esNumero(m.gravedad.g) ? m.gravedad.g : null);
  const gravedad = g != null && g > 0 ? { g: acotar(g, 0.01, 20), fuente: "motor" } : { g: ref.gravedad, fuente: "referencia" };
  // viento
  let fuerza = null, grados = null;
  if (esNumero(m.viento)) fuerza = m.viento;
  else if (m.viento && typeof m.viento === "object") {
    if (esNumero(m.viento.fuerza)) fuerza = m.viento.fuerza;
    else if (esNumero(m.viento.velocidad)) fuerza = m.viento.velocidad;
    grados = gradosDeDireccion(m.viento.direccion);
  }
  const viento = {
    fuerza: fuerza != null ? acotar(fuerza, 0, 1) : ref.viento.fuerza,
    grados: grados != null ? grados : ref.viento.direccion,
    fuente: fuerza != null ? "motor" : "referencia",
  };
  // hielo
  let nivel = null;
  if (esNumero(m.hielo)) nivel = m.hielo;
  else if (typeof m.hielo === "boolean") nivel = m.hielo ? 0.8 : 0;
  else if (m.hielo && typeof m.hielo === "object" && esNumero(m.hielo.nivel)) nivel = m.hielo.nivel;
  const hielo = { nivel: nivel != null ? acotar(nivel, 0, 1) : ref.hielo.nivel, fuente: nivel != null ? "motor" : "referencia" };
  return { gravedad, viento, hielo };
}

// Filas del bloque «Condiciones del planeta» del HUD: [etiqueta, valor, fuente]
export function filasCondiciones(c) {
  const f1 = (v) => v.toFixed(2).replace(".", ",");
  const calma = c.viento.fuerza < 0.05;
  return [
    ["Gravedad", `${f1(c.gravedad.g)} g`, c.gravedad.fuente],
    ["Viento", calma ? "en calma" : `${nombreFuerza(c.viento.fuerza)} · hacia el ${nombreDireccion(c.viento.grados)}`, c.viento.fuente],
    ["Hielo", nombreHielo(c.hielo.nivel), c.hielo.fuente],
  ];
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
