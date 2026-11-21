// Adaptador puro (sin three ni DOM) de /rna, /difuso, /ag y /estado al contenido del holograma.
// Paquete A, pieza «holo»: solo muestra lo que el rover calcula; no hay cautela ni retorno porque el motor no los produce.

export const CLASES_RNA = ["libre", "obstáculo", "barranco"];   // rna.CLASES
export const ROTULO_HOLO = "Holograma · lo que decide el rover: RNA, difuso (velocidad) y orden del AG";

// Quita marcas y caracteres de control; el texto va al canvas, pero igual se sanea
export function limpiar(valor, max = 80) {
  return String(valor === null || valor === undefined ? "" : valor)
    .replace(/[<>&"'`\u0000-\u001f\u007f]/g, "")
    .slice(0, max);
}

const acota01 = (v) => Math.max(0, Math.min(1, Number(v) || 0));

const esNum = (v) => typeof v === "number" ? Number.isFinite(v) : (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)));

function celdas(lista) {
  return Array.isArray(lista)
    ? lista.filter((c) => Array.isArray(c) && esNum(c[0]) && esNum(c[1]))
      .map((c) => [Number(c[0]), Number(c[1])])
    : [];
}

// Cada argumento puede ser null si su petición falló: el panel dice «sin dato» en vez de inventar.
export function adaptarHolo({ rna, difuso, ag, estado } = {}) {
  const prob = (rna && rna.probabilidades) || {};
  const clases = CLASES_RNA.map((nombre) => ({ nombre, prob: acota01(prob[nombre]) }));
  const hayRna = Boolean(rna && rna.probabilidades);
  const velocidad = difuso && difuso.salida && esNum(difuso.salida.velocidad)
    ? acota01(difuso.salida.velocidad) : null;
  const motivos = rna && Array.isArray(rna.motivos) ? rna.motivos : [];
  const vetos = motivos.filter((m) => String(m).startsWith("V-")).map((m) => limpiar(m, 60));
  const mejorRuta = celdas(ag && ag.mejor_ruta);
  return {
    hayRna,
    clases,
    confianza: hayRna ? acota01(rna.confianza) : null,
    prediccion: hayRna ? (clases.reduce((a, b) => (b.prob > a.prob ? b : a)).nombre) : null,
    accion: rna && rna.accion ? limpiar(rna.accion, 40) : null,
    velocidad,
    fallbackDifuso: Boolean(difuso && difuso.salida && difuso.salida.fallback),
    metodo: ag && ag.orden_en_juego && ag.orden_en_juego.metodo ? limpiar(ag.orden_en_juego.metodo, 90) : null,
    mejorRuta,
    estado: estado && estado.estado ? limpiar(estado.estado, 40) : null,
    vetoActivo: estado && typeof estado.veto === "boolean" ? estado.veto : null,
    vetos,
  };
}

export function porcentaje(v) {
  return `${Math.round(acota01(v) * 100)} %`;
}
