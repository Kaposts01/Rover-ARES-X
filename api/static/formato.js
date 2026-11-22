// Formato numérico único de la interfaz: coma decimal en todas partes, 1 decimal para % y °C.
// Sin DOM ni dependencias: se prueba con node.

// Número con coma decimal y `d` decimales; null, undefined o no numérico dan `vacio`.
export function coma(v, d = 2, vacio = "—") {
  if (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) return vacio;
  return Number(v).toFixed(d).replace(".", ",");
}
// Porcentaje ya expresado en % (91,9 %), con 1 decimal.
export const porcentaje = (v, vacio = "—") => (Number.isFinite(Number(v)) && v !== null && v !== "" ? `${coma(v, 1)} %` : vacio);
// Fracción 0..1 como porcentaje con 1 decimal (0,919 -> 91,9 %).
export const fraccionAPorcentaje = (v, vacio = "—") => (Number.isFinite(Number(v)) && v !== null && v !== "" ? `${coma(Number(v) * 100, 1)} %` : vacio);
// Temperatura en °C con 1 decimal.
export const grados = (v, vacio = "—") => (Number.isFinite(Number(v)) && v !== null && v !== "" ? `${coma(v, 1)} °C` : vacio);
