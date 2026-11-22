// Comparar dos políticas lado a lado: textos y cálculos puros (sin DOM), que se prueban con node.
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
  bateria_pct: { rotulo: "Batería final", f: (v) => `${Number(v).toFixed(1).replace(".", ",")} %` },
  sitios_visitados: { rotulo: "Sitios visitados", f: (v) => String(v) },
  vetos: { rotulo: "Vetos del supervisor", f: (v) => String(v) },
  colisiones: { rotulo: "Choques", f: (v) => String(v) },
};
export const NOTA_TABLA = "Gana la que cumple la misión; entre iguales, más puntaje. En cada fila, gana quien tiene más (sitios, puntaje, batería) o menos (pasos, vetos, choques). Los pasos solo se comparan si las dos terminaron igual.";
export function filasTabla(tabla, nombreA, nombreB) {
  if (!tabla) return [];
  return tabla.filas.map((f) => {
    const def = FILAS_TABLA[f.clave] || { rotulo: f.clave, f: String };
    return {
      clave: f.clave, rotulo: def.rotulo, a: def.f(f.a), b: def.f(f.b), ganador: f.ganador,
      texto: f.ganador === "a" ? nombreA : f.ganador === "b" ? nombreB : f.ganador === "empate" ? "empate" : "—",
    };
  });
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
