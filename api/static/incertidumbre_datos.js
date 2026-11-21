// Adaptador puro (sin three ni DOM) de la capa «Incertidumbre» sobre la de riesgo de M15 (Paquete A).
// La incertidumbre es observada / no observada: lo que el sensor del rover realmente cubrió (`observada` de GET /mapa).
// No se calcula entropía. `observada` es solo de registro en el motor: aquí solo se dibuja.

export const UMBRAL_RIESGO = 0.3;   // el mismo de la capa de riesgo de M15
export const ROTULOS = { noObservada: "no observada", seguro: "observada y segura", riesgo: "riesgo ≥ 0,3" };
export const MODOS = ["riesgo", "incertidumbre"];
export const AVISO_SIN_OBSERVACION = "sin datos de observación";

// Colores RGB 0-1. El violeta va oscuro (tenue) porque la malla tiene opacidad fija.
export const COLOR_NO_OBSERVADA = [0.36, 0.28, 0.62];
export const COLOR_SEGURA = [0.18, 0.78, 0.45];

// Amarillo (en el umbral) -> rojo (1): la rampa de M15
export function colorRiesgo(r) {
  const t = Math.min(1, Math.max(0, (r - UMBRAL_RIESGO) / (1 - UMBRAL_RIESGO)));
  return [1, 0.9 * (1 - t), 0.1];
}

const matrizValida = (m, filas, columnas) => Array.isArray(m) && m.length === filas
  && m.every((fila) => Array.isArray(fila) && fila.length === columnas);

// ¿Trae /mapa la matriz `observada` con las mismas dimensiones que el riesgo?
export function tieneObservada(datos) {
  return !!datos && matrizValida(datos.observada, datos.filas, datos.columnas)
    && matrizValida(datos.riesgo_estimado, datos.filas, datos.columnas);
}

// Color y estado de una celda en modo Incertidumbre. riesgo >= umbral gana; luego observada; si no, no observada.
export function colorCeldaIncertidumbre(riesgo, observada) {
  if (Number(riesgo) >= UMBRAL_RIESGO) return { estado: "riesgo", rgb: colorRiesgo(Number(riesgo)) };
  if (Number(observada) === 1 || observada === true) return { estado: "seguro", rgb: COLOR_SEGURA };
  return { estado: "noObservada", rgb: COLOR_NO_OBSERVADA };
}

// Color de una celda según el modo, o null si no se pinta (modo Riesgo no pinta lo que está bajo el umbral)
export function colorCelda(modo, riesgo, observada) {
  if (modo === "incertidumbre") return colorCeldaIncertidumbre(riesgo, observada).rgb;
  return Number(riesgo) >= UMBRAL_RIESGO ? colorRiesgo(Number(riesgo)) : null;
}

// Cuántas celdas hay de cada estado (para la leyenda y las pruebas)
export function contarEstados(datos) {
  const n = { noObservada: 0, seguro: 0, riesgo: 0 };
  if (!tieneObservada(datos)) return n;
  for (let f = 0; f < datos.filas; f++) {
    for (let c = 0; c < datos.columnas; c++) n[colorCeldaIncertidumbre(datos.riesgo_estimado[f][c], datos.observada[f][c]).estado]++;
  }
  return n;
}
