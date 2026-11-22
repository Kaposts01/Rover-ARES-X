// Viaje entre planetas: datos y funciones puras (sin DOM ni THREE). Se prueban con node.
export const DURACION_VIAJE_S = 8;
export const GUARDA_EXTRA_S = 2;
export const CIERRE_ESTATICO_S = 20;   // movimiento reducido: la tarjeta estática se cierra sola a los 20 s (o con «Continuar» / Escape)
export const PLANETAS_VIAJE = ["Mercurio", "Venus", "Tierra", "Marte", "Júpiter", "Saturno", "Urano", "Neptuno"];
// Distancia media al Sol, en millones de km. Fuente: NASA Planetary Fact Sheet (valores aproximados).
export const DISTANCIA_SOL_MKM = {
  Mercurio: 57.9, Venus: 108.2, Tierra: 149.6, Marte: 228.0, "Júpiter": 778.5, Saturno: 1432, Urano: 2867, Neptuno: 4515,
};
export const FUENTE_DISTANCIA = "NASA Planetary Fact Sheet";
export const AVISO_TERRENO = "En todos los planetas el terreno, los obstáculos y los eventos de la partida son los de Marte. El planeta cambia el aspecto, la temperatura interna del rover (solo avisa) y el vehículo permitido.";
export const ROTULO_ILUSTRATIVO = "Escena ilustrativa: no está a escala ni representa un traslado real.";
export const ROTULO_DISTANCIA = "Distancia media al Sol (constante real aproximada)";

export function esPerfil(p) { return PLANETAS_VIAJE.includes(p); }

export function debeViajar({ previo, nuevo, activado }) {
  return !!activado && esPerfil(previo) && esPerfil(nuevo) && previo !== nuevo;
}

function formatoMkm(v) {
  const entero = Number.isInteger(v);
  const [e, d] = v.toFixed(entero ? 0 : 1).split(".");
  const miles = e.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${d ? `${miles},${d}` : miles} millones de km`;
}

// Filas de la tarjeta: solo distancia al Sol (constante rotulada) y, si /planetas lo trae, el modo viable.
export function datosTarjeta(desde, hacia, catalogo) {
  const lista = (catalogo && Array.isArray(catalogo.planetas)) ? catalogo.planetas : [];
  const fila = (p) => {
    const d = DISTANCIA_SOL_MKM[p];
    const en = lista.find((x) => x && x.nombre === p);
    const filas = [{
      etiqueta: ROTULO_DISTANCIA,
      valor: d == null ? "Sin dato" : formatoMkm(d),
      tipo: d == null ? "sin_dato" : "real",
    }];
    filas.push({ etiqueta: "Vehículo permitido", valor: en && en.modo ? en.modo : "Sin dato", tipo: en && en.modo ? "real" : "sin_dato" });
    return filas;
  };
  return { titulo: `Viajando de ${desde} a ${hacia}`, desde, hacia, origen: fila(desde), destino: fila(hacia),
    avisos: [ROTULO_ILUSTRATIVO, AVISO_TERRENO] };
}

export function fasesViaje(duracion = DURACION_VIAJE_S) {
  const salida = duracion * 0.15, llegada = duracion * 0.15;
  return { salida, travesia: duracion - salida - llegada, llegada, total: duracion };
}
export function faseActual(t, fases) {
  if (t <= 0) return ["salida", 0];
  if (t >= fases.total) return ["llegada", 1];
  if (t < fases.salida) return ["salida", t / fases.salida];
  if (t < fases.salida + fases.travesia) return ["travesia", (t - fases.salida) / fases.travesia];
  return ["llegada", (t - fases.salida - fases.travesia) / fases.llegada];
}

// Bézier cuadrática de A=(-ancho,0,0) a B=(ancho,0,0) con control elevado; devuelve posición y tangente normalizada.
export function trayectoria(u, ancho = 20) {
  const k = Math.min(1, Math.max(0, u));
  const P0 = [-ancho, 0, 0], P1 = [0, ancho * 0.35, -ancho * 0.4], P2 = [ancho, 0, 0];
  const a = (1 - k) * (1 - k), b = 2 * (1 - k) * k, c = k * k;
  const pos = [0, 1, 2].map((i) => a * P0[i] + b * P1[i] + c * P2[i]);
  const tg = [0, 1, 2].map((i) => 2 * (1 - k) * (P1[i] - P0[i]) + 2 * k * (P2[i] - P1[i]));
  const n = Math.hypot(...tg) || 1;
  return { pos, tangente: tg.map((x) => x / n) };
}

// Cola acotada: añade p y descarta lo que pase de n puntos.
export function actualizarEstela(historial, p, n = 120) {
  const h = historial.concat([p]);
  return h.length > n ? h.slice(h.length - n) : h;
}

// animado | tarjeta (movimiento reducido: solo tarjeta estática) | ninguno
export function modoMovimiento(reducido, activado) {
  if (!activado) return "ninguno";
  return reducido ? "tarjeta" : "animado";
}

// ---------- Carga con cohete: el avance sigue a la carga real ----------
// Mientras el motor no responde, el avance tiende a TOPE_ESPERA sin llegar nunca; al responder sube a 1.
// La subida está limitada (VELOCIDAD_MAX por segundo) para que el aterrizaje siempre se vea, y hay una duración mínima.
export const TOPE_ESPERA = 0.85;
export const CONSTANTE_ESPERA_S = 1.8;
export const VELOCIDAD_MAX = 0.7;
export const DURACION_MIN_CARGA_S = 2.4;
export const GUARDA_CARGA_S = 30;   // si el motor no responde en 30 s, el cohete deja de esperar (la carga sigue su curso)

export function objetivoCarga(t, listo) {
  if (listo) return 1;
  return TOPE_ESPERA * (1 - Math.exp(-Math.max(0, t) / CONSTANTE_ESPERA_S));
}
// Un paso del avance mostrado d hacia el objetivo, con dt en segundos. Nunca retrocede ni pasa de 1.
export function pasoCarga(d, t, listo, dt) {
  const obj = objetivoCarga(t, listo);
  if (obj <= d) return d;
  let nd = d + Math.min((obj - d) * Math.min(1, dt * 5), VELOCIDAD_MAX * dt);
  if (listo && t < DURACION_MIN_CARGA_S) nd = Math.min(nd, t / DURACION_MIN_CARGA_S);   // el aterrizaje no se salta aunque el motor sea rápido
  if (listo && obj - nd < 0.01) nd = 1;
  return Math.min(1, Math.max(d, nd));
}
export function etapaCarga(d) {
  if (d >= 0.999) return "aterrizado";
  if (d < 0.14) return "despegue";
  if (d < TOPE_ESPERA) return "crucero";
  return "aterrizaje";
}
export function textoEtapa(etapa, desde, hacia) {
  return {
    despegue: `Despegue desde ${desde}`,
    crucero: `Crucero hacia ${hacia} · esperando al motor`,
    aterrizaje: `Aproximación y aterrizaje en ${hacia}`,
    aterrizado: `En superficie de ${hacia} · misión lista`,
  }[etapa] || "";
}
// Origen del vuelo: el planeta anterior; si no hay o es el mismo, se sale de la Tierra (o de Marte si el destino es la Tierra).
export function origenVuelo(previo, destino) {
  if (esPerfil(previo) && previo !== destino) return previo;
  return destino === "Tierra" ? "Marte" : "Tierra";
}
