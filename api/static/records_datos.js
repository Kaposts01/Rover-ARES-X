// Récords por semilla: textos y formatos puros (sin DOM), que se prueban con node.
import { coma as comaFormato } from "./formato.js?v=r15";
import { nombreModo, nombreEstado, Vehiculo, plural } from "./textos.js?v=r15";

export const NIVELES = ["Muy fácil", "Fácil", "Medio", "Difícil", "Hardcore"];
export const nombreNivel = (n) => NIVELES[Number(n) - 1] || String(n ?? "—");
export const NOMBRE_TAMANO = { pequeno: "Pequeño (20×30)", mediano: "Mediano (30×45)", grande: "Grande (40×60)" };
export const nombreTamano = (t) => NOMBRE_TAMANO[t] || String(t ?? "—");

// Quién jugó la misión. «Asistida» = manual en la que la IA condujo en algún tramo: no cuenta como manual pura.
export const ROTULO_ORIGEN = { manual: "Manual", asistida: "Manual con ayuda de la IA", ia: "IA" };
export const AYUDA_ORIGEN = {
  manual: "Conducida solo por el jugador.",
  asistida: "Conducida por el jugador, pero la IA condujo en algún tramo. No cuenta como manual pura.",
  ia: "Conducida por un modo de la IA desde el principio.",
};
export const rotuloOrigen = (o) => ROTULO_ORIGEN[o] || String(o ?? "—");
export const politicaDe = (r) => (r && r.origen === "ia" ? nombreModo(r.modo) : r && r.origen === "asistida" ? "Manual + IA" : "Manual");

export const textoResultado = (r) => (r && r.resultado ? nombreEstado(r.resultado) : "—");
const coma = (v, d = 1) => (typeof v === "number" ? comaFormato(v, d) : "—");
export const textoBateria = (r) => `${coma(r && r.bateria_pct, 1)} %`;

export function fechaLegible(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(iso || ""));
  return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : "—";
}

// Query string con solo los filtros que tienen valor
export function consultaFiltros(f) {
  const p = new URLSearchParams();
  for (const k of ["planeta", "nivel", "tamano", "semilla", "vehiculo", "origen", "resultado"]) {
    const v = f && f[k];
    if (v !== undefined && v !== null && String(v).trim() !== "") p.set(k, String(v).trim());
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}
export const hayFiltros = (f) => consultaFiltros(f) !== "";

// Qué se le dice al jugador en la pantalla final
export function textoNuevoRecord(resp) {
  if (!resp || !resp.record) return null;
  const r = resp.record;
  const quien = r.origen === "ia" ? "de la IA" : r.origen === "asistida" ? "manual con ayuda de la IA" : "manual";
  if (resp.nuevo_record) {
    const ant = resp.mejor_anterior;
    return {
      nuevo: true,
      titulo: "¡Nuevo récord en esta semilla!",
      detalle: ant
        ? `Récord ${quien} en la semilla ${r.semilla}: ${r.puntaje} puntos en ${plural(r.pasos, "paso", "pasos")}. Antes: ${ant.puntaje} puntos en ${plural(ant.pasos, "paso", "pasos")}.`
        : `Primera marca ${quien} en la semilla ${r.semilla}: ${r.puntaje} puntos en ${plural(r.pasos, "paso", "pasos")}.`,
    };
  }
  if (r.resultado !== "EXITO") {
    // Mismo criterio en título y detalle: el intento queda en la lista, pero no cuenta como récord porque no tuvo éxito
    return { nuevo: false, titulo: "Intento guardado, sin récord", detalle: `La semilla ${r.semilla} no se superó esta vez (${nombreEstado(r.resultado).toLowerCase()}); el intento queda en la lista, pero los récords solo cuentan misiones con éxito.` };
  }
  const mejor = resp.mejor_anterior;
  return {
    nuevo: false,
    titulo: "Misión guardada en los récords",
    detalle: `Puesto ${resp.puesto || "—"} entre las marcas ${quien} de esta semilla${mejor ? `; el récord es de ${mejor.puntaje} puntos en ${plural(mejor.pasos, "paso", "pasos")}` : ""}.`,
  };
}

export const TEXTO_VACIO = "Todavía no hay récords. Termina una misión y su resultado aparecerá aquí.";
export const TEXTO_VACIO_FILTRADO = "Ningún récord coincide con los filtros.";
export const TEXTO_ERROR = "No se pudieron leer los récords: el motor no responde. Revisa que la API esté levantada.";
export const textoBorrado = (n) => `¿Borrar los ${plural(n, "récord", "récords")} guardados? No se puede deshacer.`;

// Datos para volver a jugar una semilla: lo que el asistente del menú necesita
export function configuracionDe(r) {
  return {
    planeta: r.planeta, vehiculo: r.vehiculo || "rover", tamano: r.tamano || "grande", nivel: Number(r.nivel) || 1,
    semilla: r.semilla, control: r.origen === "ia" ? (r.modo || "automatico") : "manual",
  };
}
export { Vehiculo };
