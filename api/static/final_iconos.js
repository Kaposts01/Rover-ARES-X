// Pantalla final: iconos SVG propios (sin emoji, sin archivos). Se construyen con createElementNS, nodo a nodo.
// Retícula de 24 unidades, trazo de línea. Cada dibujo es una lista de piezas: ["p", d] camino, ["c", x, y, r] círculo,
// ["e", cx, cy, rx, ry, giro] elipse, ["r", x, y, ancho, alto, radio] rectángulo.
const NS = "http:" + "//www.w3.org/2000/svg";
const p = (d) => ["p", d];
const c = (x, y, r) => ["c", x, y, r];

export const DIBUJOS = {
  planeta: [c(12, 12, 6), ["e", 12, 12, 10, 3.2, -28], p("M10 7.5l2 1M14 15l1.5 1")],
  brujula: [c(12, 12, 9), p("M15.5 8.5l-2 5-5 2 2-5zM12 3v2M21 12h-2M12 21v-2M3 12h2")],
  microscopio: [p("M10 3l5 2-3.5 8-5-2zM13.5 9.5a6 6 0 0 1 2 10.5M5 21h15M8 16v5M4 15h8M10 5l3 1.2")],
  probeta: [p("M8 3h8M10 3v6l-5.5 9a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 9V3M8 14h8M10 17h.01M14 18h.01")],
  bateria: [["r", 3, 7, 16, 10, 2], p("M21 10v4M6 10v4M10 10v4M14 10v4")],
  escudo: [p("M12 3l8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6zM8 12l3 3 5-6")],
  montana: [p("M2 20L9 5l5 9 3-5 5 11zM6.5 10.5L9 12l2.5-1.5M15 13l2 2 2-2")],
  replanificar: [p("M4 9a8 8 0 0 1 13-4l3 3M20 3v5h-5M20 15A8 8 0 0 1 7 19l-3-3M4 21v-5h5M9 12h6")],
  ubicacion: [p("M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0z"), c(12, 10, 2.5)],
  reloj: [c(12, 12, 9), p("M12 6v6l4 2M9 1h6")],
  trofeo: [p("M7 3h10v6a5 5 0 0 1-10 0zM7 5H3v3a4 4 0 0 0 4 4M17 5h4v3a4 4 0 0 1-4 4M12 14v5M8 21h8M10 19h4")],
  camara: [p("M3 7h4l2-3h6l2 3h4v13H3zM17.5 10h.01"), c(12, 13, 4)],
  medalla: [c(12, 9, 6), p("M7.5 13.5L5 22l7-3 7 3-2.5-8.5M10 9l1.5 1.5L14 7.5")],
  cohete: [p("M9 15l-3-3C8 6 13 3 20 3c0 7-3 12-9 14zM7 10H4l-2 6 6-1M13 17v3l-6 2 1-6M5 19l-2 2"), c(15, 8, 2)],
  satelite: [p("M9 8l7 7-4 4-7-7zM7 6l4-4 4 4-4 4M14 13l4-4 4 4-4 4M5 15l-2 2M3 13a6 6 0 0 0 6 6M2 17v5h5")],
  volcan: [p("M3 21l6-12h6l6 12zM7 13l3 2 2-3 2 3 3-2M10 6L9 3M14 6l2-4M12 5V2M7 21l3-4")],
  geiser: [p("M3 21h18M7 21l3-6h4l3 6M10 12V8c0-2-2-3-3-2M14 12V6c0-2 2-3 3-2M12 10V3M5 10v1M19 8v1")],
  meteorito: [p("M6 10l4-2 5 2 2 5-4 5-6 1-4-5zM11 5l3-3M15 7l5-5M18 11l4-4"), c(8, 14, 1.5), p("M12 17h.01")],
  noche: [p("M20 14.5A9 9 0 0 1 9.5 4 8.7 8.7 0 1 0 20 14.5M17 3v4M15 5h4M21 8v2M20 9h2")],
  tormenta: [p("M5 14a4 4 0 0 1 0-8 6 6 0 0 1 11-1 4.5 4.5 0 0 1 2 9M12 11l-4 6h4l-2 5 7-8h-5zM4 18l-1 2M20 18l-1 2")],
  nave: [p("M2 14l7-3 3-8 3 8 7 3-7 3-3 4-3-4zM9 11l3 3 3-3M9 17h6M7 20l-1 2M17 20l1 2")],
  alien: [p("M12 3c-6 0-9 4-8 9 1 4 6 9 8 9s7-5 8-9c1-5-2-9-8-9zM7 10l3 2-1 2-2-1zM17 10l-3 2 1 2 2-1zM10 17h4")],
  senal: [p("M3 8a14 14 0 0 1 18 0M6 11a9 9 0 0 1 12 0M9 14a4.5 4.5 0 0 1 6 0M12 18v3"), c(12, 17, 1)],
  grafico: [p("M3 3v18h18M7 17v-5M12 17V8M17 17V5M6 8l5-4 5 1 4-3")],
  bandera: [p("M5 22V3c5-3 9 3 14 0v10c-5 3-9-3-14 0M3 22h4")],
  cerrar: [p("M6 6l12 12M18 6L6 18")],
  reiniciar: [p("M4 10a8 8 0 1 1 1 7M4 4v6h6M12 8v4l3 2")],
  frio: [p("M12 2v20M3.3 7l17.4 10M3.3 17L20.7 7M9 4l3 3 3-3M9 20l3-3 3 3M4 10l4-1-1-4M17 19l-1-4 4-1M4 14l4 1-1 4M17 5l-1 4 4 1")],
  bloque: [p("M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10")],
  balanza: [p("M12 3v18M7 21h10M4 7h16M6 7l-4 8h8zM18 7l-4 8h8zM2 15c1 4 7 4 8 0M14 15c1 4 7 4 8 0")],
  huella: [["e", 9, 16, 3, 5, -20], c(6, 7, 1.4), c(10, 5, 1.4), c(14, 6, 1.4), c(17, 9, 1.4)],
  punto: [c(12, 12, 2)],
};
export const NOMBRES_ICONOS = Object.freeze(Object.keys(DIBUJOS));

const SILUETA = "M12 2.5l2.9 6 6.6.9-4.8 4.7 1.1 6.6-5.8-3.1-5.8 3.1 1.1-6.6-4.8-4.7 6.6-.9z";

function nodo(tag, attrs) {
  const e = document.createElementNS(NS, tag);
  for (const k of Object.keys(attrs)) e.setAttribute(k, String(attrs[k]));
  return e;
}
function pieza(d) {
  switch (d[0]) {
    case "p": return nodo("path", { d: d[1] });
    case "c": return nodo("circle", { cx: d[1], cy: d[2], r: d[3] });
    case "e": return nodo("ellipse", { cx: d[1], cy: d[2], rx: d[3], ry: d[4], transform: `rotate(${d[5]} ${d[1]} ${d[2]})` });
    default: return nodo("rect", { x: d[1], y: d[2], width: d[3], height: d[4], rx: d[5] });
  }
}
function dibujo(nombre) { return DIBUJOS[nombre] || DIBUJOS.punto; }
function svgBase(tam, vista) {
  return nodo("svg", { width: tam, height: tam, viewBox: vista, fill: "none", "aria-hidden": "true", focusable: "false" });
}

// Icono de línea; el color lo da `currentColor`.
export function icono(nombre, { tam = 20, trazo = 1.75 } = {}) {
  const s = svgBase(tam, "0 0 24 24");
  const g = nodo("g", { stroke: "currentColor", "stroke-width": trazo, "stroke-linecap": "round", "stroke-linejoin": "round" });
  for (const d of dibujo(nombre)) g.append(pieza(d));
  s.append(g);
  return s;
}

// Insignia de logro: hexágono con el icono dentro. Bloqueada o sin obtener: gris y más tenue.
export function insignia(nombre, { tam = 40, obtenido = true } = {}) {
  const tono = obtenido ? "#68d9ca" : "#7b8995";
  const s = svgBase(tam, "0 0 64 64");
  const g = nodo("g", { stroke: tono, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: obtenido ? 1 : 0.55 });
  g.append(nodo("path", { d: "M32 3L57 17V47L32 61 7 47V17Z", fill: tono, "fill-opacity": 0.12, "stroke-width": 1.25 }));
  g.append(nodo("path", { d: "M32 8L52.5 19.5V44.5L32 56 11.5 44.5V19.5Z", "stroke-width": 0.75, opacity: 0.5 }));
  const dentro = nodo("g", { transform: "translate(18 18) scale(1.166667)", "stroke-width": 1.75 });
  for (const d of dibujo(nombre)) dentro.append(pieza(d));
  g.append(dentro);
  s.append(g);
  return s;
}

// Estrella llena (dorada) o vacía (contorno).
export function estrella({ tam = 52, llena = true } = {}) {
  const s = svgBase(tam, "0 0 24 24");
  s.setAttribute("class", "fn-estrella-svg");
  if (!llena) {
    s.append(nodo("path", { d: SILUETA, stroke: "#718493", "stroke-width": 0.8, "stroke-linejoin": "round", fill: "#8ca6b6", "fill-opacity": 0.05 }));
    return s;
  }
  s.append(nodo("path", { d: SILUETA, fill: "#f5b53d", stroke: "#fff0ba", "stroke-width": 0.65, "stroke-linejoin": "round" }));
  s.append(nodo("path", { d: "M3 9l9-6-2 8-7 2z", fill: "#fff9df", "fill-opacity": 0.35 }));
  return s;
}
