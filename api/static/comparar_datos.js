// Comparar dos políticas lado a lado: textos y cálculos puros (sin DOM), que se prueban con node.
import { coma as comaFormato, porcentaje, grados } from "./formato.js?v=r14";
import { nombreVariante, ayudaVariante, nombreAccion, nombresMotivos, nombreEstado, plural } from "./textos.js?v=r14";

// Políticas que se pueden enfrentar. «solo_*»: una sola técnica conduce, con el supervisor; el resto son variantes del híbrido.
export const ORDEN_POLITICAS = ["hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_mas_corta", "sin_ag_2opt", "ruta_corta", "ag_puro", "solo_rna", "solo_difuso", "solo_ag"];
const SOLO = { solo_rna: ["Solo RNA", "la red neuronal conduce sola, con el supervisor"], solo_difuso: ["Solo difuso", "el control difuso conduce solo, con el supervisor"], solo_ag: ["Solo AG", "el algoritmo genético planifica y conduce solo, con el supervisor"] };
export const nombrePolitica = (k) => (SOLO[k] ? SOLO[k][0] : nombreVariante(k));
export const ayudaPolitica = (k) => (SOLO[k] ? SOLO[k][1] : ayudaVariante(k));
export const opcionesPoliticas = () => ORDEN_POLITICAS.map((k) => [k, nombrePolitica(k)]);

export const ROTULO_LADO = { a: "A", b: "B" };
export const estadoLado = (e) => (e === "LIMITE" ? "Sin terminar (límite de pasos)" : nombreEstado(e));

// Ficha del lado en el paso k (1 = primer paso dado). k = 0: todavía no se movió. Pasado el final, queda la última.
export function fichaEn(lado, k) {
  const p = (lado && lado.pasos) || [];
  if (k <= 0 || !p.length) return null;
  return p[Math.min(k, p.length) - 1];
}
// Ruta recorrida hasta el paso k, empezando en la celda de inicio
export function rutaHasta(inicio, lado, k) {
  const p = (lado && lado.pasos) || [];
  const ruta = [inicio];
  for (let i = 0; i < Math.min(k, p.length); i++) ruta.push(p[i].posicion);
  return ruta;
}
// Pasos que se pueden mostrar: los de la partida más larga conocida
export const pasosDisponibles = (lados) => Math.max(0, ...lados.map((l) => (l.pasos || []).length));
export const ambosTerminados = (lados) => lados.every((l) => l.terminado);

// Qué decidió cada política en el paso en que se separan sus caminos
export function textoDecision(nombre, f) {
  if (!f) return `${nombre}: no hizo nada más (ya había terminado).`;
  const donde = Array.isArray(f.posicion) ? ` · quedó en fila ${f.posicion[0]}, columna ${f.posicion[1]}` : "";
  const m = nombresMotivos(f.motivos);
  return `${nombre}: ${nombreAccion(f.accion)}${donde}${m ? ` · porque ${m}` : " · sin motivo especial registrado"}.`;
}
export function textoDivergencia(div, nombreA, nombreB) {
  if (!div) return null;
  const mismoAccion = div.a.accion === div.b.accion;
  const resumen = mismoAccion
    ? `En el paso ${div.n} las dos hicieron lo mismo (${nombreAccion(div.a.accion)}) pero a celdas distintas.`
    : `En el paso ${div.n} deciden distinto: ${nombreA} ${nombreAccion(div.a.accion)} y ${nombreB} ${nombreAccion(div.b.accion)}.`;
  return { titulo: `Primer paso distinto: el ${div.n}`, resumen, a: textoDecision(nombreA, div.a), b: textoDecision(nombreB, div.b) };
}
export const TEXTO_SIN_DIVERGENCIA_AUN = "Por ahora las dos políticas hacen exactamente lo mismo.";
export const TEXTO_SIN_DIVERGENCIA_FIN = "Las dos políticas hicieron exactamente lo mismo en toda la misión: en este mapa la diferencia entre ellas no cambia nada.";

// Filas de la tabla final
export const FILAS_TABLA = {
  resultado: { rotulo: "Resultado", f: (v) => estadoLado(v) },
  pasos: { rotulo: "Pasos", f: (v) => String(v) },
  puntaje: { rotulo: "Puntaje de juego", f: (v) => String(v) },
  bateria_pct: { rotulo: "Batería final", f: (v) => porcentaje(v) },
  sitios_visitados: { rotulo: "Sitios visitados", f: (v) => String(v) },
  vetos: { rotulo: "Vetos del supervisor", f: (v) => String(v) },
  colisiones: { rotulo: "Choques", f: (v) => String(v) },
  ciencia: { rotulo: "Ciencia recogida", f: (v) => (leerCiencia({ ciencia: v }) || { texto: "—" }).texto },
  ciencia_pct: { rotulo: "Ciencia recogida", f: (v) => (leerCiencia({ ciencia_pct: v }) || { texto: "—" }).texto },
  ciencia_recogida: { rotulo: "Ciencia recogida", f: (v) => (leerCiencia({ ciencia_recogida: v }) || { texto: "—" }).texto },
};
// Ciencia recogida (métrica propia de cada lado, la añade el motor). Se lee con tolerancia de nombres y de forma:
// un número (fracción 0..1, porcentaje 0..100 en `ciencia_pct`, o puntos) o un objeto {fraccion, recogida, maxima}. Sin dato: null.
export const CLAVES_CIENCIA = ["ciencia", "ciencia_pct", "ciencia_recogida"];
const esNum = (v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));
export function leerCiencia(origen) {
  if (!origen || typeof origen !== "object") return null;
  for (const clave of CLAVES_CIENCIA) {
    const v = origen[clave];
    if (v && typeof v === "object") {
      const frac = esNum(v.fraccion) ? Number(v.fraccion) : esNum(v.recogida) && esNum(v.maxima) && Number(v.maxima) > 0 ? Number(v.recogida) / Number(v.maxima) : null;
      if (frac !== null) return { orden: frac, texto: `${comaFormato(frac * 100, 1)} %${esNum(v.recogida) && esNum(v.maxima) ? ` (${comaFormato(v.recogida, 1)} de ${comaFormato(v.maxima, 0)})` : ""}` };
    } else if (esNum(v)) {
      const n = Number(v);
      if (clave === "ciencia_pct") return { orden: n / 100, texto: porcentaje(n) };
      return n >= 0 && n <= 1 ? { orden: n, texto: porcentaje(n * 100) } : { orden: n, texto: `${comaFormato(n, 1)} puntos` };
    }
  }
  return null;
}
export const hayCiencia = (lados) => (lados || []).some((l) => leerCiencia(l) || ((l && l.pasos) || []).some((p) => leerCiencia(p)));
// Ciencia del lado en el paso k: la de la ficha de ese paso o, si el lado ya terminó, la del resumen final
export function cienciaEn(lado, k) {
  const f = fichaEn(lado, k);
  return leerCiencia(f) || (lado && lado.terminado && k >= ((lado.pasos || []).length) ? leerCiencia(lado) : null);
}
export const NOTA_TABLA = "Gana la que cumple la misión; entre iguales, más puntaje. En cada fila, gana quien tiene más (sitios, puntaje, batería) o menos (pasos, vetos, choques). Los pasos solo se comparan si las dos terminaron igual.";
// `lados` (opcional): si la tabla del motor no trae la fila de ciencia pero los dos lados sí la traen, se añade; sin dato, no hay fila.
export function filasTabla(tabla, nombreA, nombreB, lados = null) {
  if (!tabla) return [];
  const filas = tabla.filas.map((f) => {
    const def = FILAS_TABLA[f.clave] || { rotulo: f.clave, f: String };
    return {
      clave: f.clave, rotulo: def.rotulo, a: def.f(f.a), b: def.f(f.b), ganador: f.ganador,
      texto: f.ganador === "a" ? nombreA : f.ganador === "b" ? nombreB : f.ganador === "empate" ? "empate" : "—",
    };
  });
  if (lados && lados.length === 2 && !filas.some((f) => CLAVES_CIENCIA.includes(f.clave))) {
    const ca = leerCiencia(lados[0]) || cienciaEn(lados[0], Infinity), cb = leerCiencia(lados[1]) || cienciaEn(lados[1], Infinity);
    if (ca && cb) {
      const ganador = Math.abs(ca.orden - cb.orden) < 1e-9 ? "empate" : ca.orden > cb.orden ? "a" : "b";
      filas.push({ clave: "ciencia", rotulo: "Ciencia recogida", a: ca.texto, b: cb.texto, ganador, texto: ganador === "a" ? nombreA : ganador === "b" ? nombreB : "empate" });
    }
  }
  return filas;
}
export function veredicto(tabla, nombreA, nombreB) {
  if (!tabla) return "";
  if (tabla.ganador === "a") return `Gana ${nombreA}.`;
  if (tabla.ganador === "b") return `Gana ${nombreB}.`;
  return "Empate: las dos llegaron al mismo resultado y puntaje.";
}

// Validación del formulario antes de pedir nada al servidor
export function validarFormulario({ semilla, politicaA, politicaB }) {
  const t = String(semilla ?? "").trim();
  if (t !== "" && !/^\d+$/.test(t)) return "La semilla debe ser un número entero, o déjala vacía para una aleatoria.";
  if (politicaA === politicaB) return "Elige dos políticas distintas para compararlas (si son iguales, el resultado es idéntico).";
  return null;
}

// Velocidades de la reproducción común (ms por paso)
export const VELOCIDADES = [["800", "lenta"], ["350", "normal"], ["120", "rápida"], ["40", "muy rápida"]];

// Tamaño de celda del minimapa para que el mapa quepa en el ancho y alto disponibles
export function tamanoCelda(filas, columnas, anchoMax, altoMax) {
  const c = Math.floor(Math.min(anchoMax / Math.max(1, columnas), altoMax / Math.max(1, filas)));
  return Math.max(3, Math.min(16, c));
}
export const resumenLado = (nombre, estado, pasos) => `${nombre}: ${estadoLado(estado)} en ${plural(pasos, "paso", "pasos")}`;
