// Comprueba que toda función llamada en api/static exista en algún archivo de api/static (N11).
// Uso: node docs/capturas/comprobar_referencias.mjs   (sale con código 1 si falta alguna)
// Es una comprobación de texto, no un analizador completo: puede marcar falsos positivos, que se revisan a mano.
import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "api", "static");
const archivos = readdirSync(raiz).filter((f) => f.endsWith(".js"));
// Se quitan los comentarios de línea y el texto de cadenas (CSS, GLSL, etiquetas), manteniendo los saltos de línea
// para que los números de línea sigan siendo válidos. Dentro de las plantillas se conservan las expresiones ${...}.
function codigoSinTextos(t) {
  const sinComentarios = t.replace(/\/\/.*$/gm, "");
  const plantillas = sinComentarios.replace(/`([^`]*)`/g, (_, cuerpo) => {
    const expresiones = [...cuerpo.matchAll(/\$\{([^}]*)\}/g)].map((m) => `;${m[1]};`).join("");
    return " " + expresiones + "\n".repeat((cuerpo.match(/\n/g) || []).length);
  });
  return plantillas.replace(/"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'/g, '""');
}
const textos = archivos.map((f) => [f, codigoSinTextos(readFileSync(join(raiz, f), "utf8"))]);

const PALABRAS = new Set(["if", "for", "while", "switch", "catch", "function", "return", "typeof", "await", "async", "new", "of", "super"]);
const INTEGRADAS = new Set([
  "Number", "String", "Boolean", "Object", "Array", "Set", "Map", "Promise", "JSON", "Math", "Date", "Error", "RegExp", "Symbol",
  "URLSearchParams", "parseInt", "parseFloat", "isNaN", "setTimeout", "clearTimeout", "setInterval", "clearInterval", "fetch",
  "requestAnimationFrame", "cancelAnimationFrame", "matchMedia", "alert", "encodeURIComponent", "decodeURIComponent",
  "Float32Array", "Float64Array", "Int32Array", "Uint32Array", "Uint8Array", "ArrayBuffer", "structuredClone", "Blob", "Image",
]);

const definidos = new Set();
const parametros = new Set();
for (const [, t] of textos) {
  // Declaraciones: function, const, let, var (también exportadas)
  for (const m of t.matchAll(/\b(?:function\s*\*?\s*|const\s+|let\s+|var\s+)([A-Za-z_$][\w$]*)/g)) definidos.add(m[1]);
  // Importaciones con nombre (import { a, b as c } from ...)
  for (const m of t.matchAll(/import\s*\{([^}]*)\}/g)) {
    for (const n of m[1].split(",")) {
      const nombre = n.trim().split(/\s+as\s+/).pop();
      if (nombre) definidos.add(nombre);
    }
  }
  // Parámetros de funciones y de funciones flecha (aproximado)
  for (const m of t.matchAll(/\(([^()]*)\)\s*(?:=>|\{)/g)) {
    for (const p of m[1].split(",")) {
      const nombre = p.trim().replace(/=.*$/s, "").replace(/[{}[\].\s]/g, "");
      if (/^[A-Za-z_$][\w$]*$/.test(nombre)) parametros.add(nombre);
    }
  }
}

let fallos = 0;
for (const [f, t] of textos) {
  const lineas = t.split("\n");
  lineas.forEach((linea, i) => {
    for (const m of linea.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(/g)) {
      const nombre = m[1];
      if (PALABRAS.has(nombre) || INTEGRADAS.has(nombre)) continue;
      if (definidos.has(nombre) || parametros.has(nombre)) continue;
      console.log(`${f}:${i + 1}: se llama a «${nombre}» y no está definida en api/static`);
      fallos += 1;
    }
  });
}

// Versión de los módulos (O11): los imports de /static/*.js y el script de index.html deben usar la misma ?v=
const html = readFileSync(join(raiz, "index.html"), "utf8");
const versiones = new Set();
for (const [f] of textos) {
  const crudo = readFileSync(join(raiz, f), "utf8");
  for (const m of crudo.matchAll(/["']\/static\/[\w/.-]+\.js(\?v=([^"']*))?["']/g)) {
    if (m[0].includes("/vendor/")) continue;   // código de terceros: sin versión propia
    if (!m[1] || m[2] === "") {
      console.log(`${f}: import sin versión: ${m[0]}`);
      fallos += 1;
    } else {
      versiones.add(m[2]);
    }
  }
}
for (const m of html.matchAll(/src="\/static\/app\.js(\?v=([^"]*))?"/g)) {
  if (!m[1]) {
    console.log("index.html: app.js sin versión");
    fallos += 1;
  } else {
    versiones.add(m[2]);
  }
}
if (versiones.size > 1) {
  console.log(`index.html y los imports usan versiones distintas: ${[...versiones].join(", ")}`);
  fallos += 1;
}

if (fallos) {
  console.log(`\n${fallos} referencia(s) sin definir.`);
  process.exit(1);
}
console.log(`OK: ${archivos.length} archivos, funciones definidas y versión de módulos única (${[...versiones].join(", ")}).`);
