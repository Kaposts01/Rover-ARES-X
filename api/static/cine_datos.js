// Cine: datos y funciones puras (sin DOM ni THREE) del director de cámara y del postproceso. Se prueban con node.
// El cine solo mueve la cámara y el render: no escribe en la partida ni en el motor.
export const UMBRAL_FPS = 30;
export const VENTANA_FPS = 120;          // cuadros de la mediana móvil
export const VECES_BAJO_UMBRAL = 2;      // ventanas seguidas bajo el umbral antes de apagar el postproceso
export const AVISO_POST_APAGADO = "Postproceso apagado: el equipo no rinde";
export const AVISO_CARGA_FALLIDA = "Cine no disponible: la partida sigue igual";
export const ETIQUETA_DIRECTOR = "Director de cámara";
export const ETIQUETA_POST = "Postproceso (bloom y bokeh)";
export const ROTULO_REPETICION = "Repetición visual (la simulación está en pausa)";
export const MARGEN_MAPA = 4;            // el director acota la cámara al mapa más 4 celdas
export const ALTURA_MINIMA = 0.8;        // por encima del suelo
export const TECLAS_CINE = ["h", "H", "Escape"];   // las únicas que responden con el director activo
export const DURACIONES_TOMA_S = [6, 7, 8, 9, 10];

// Seis tomas: desplazamientos en ejes locales del rover (frente, derecha, altura) y altura de la mirada.
export const TOMAS = [
  { id: "paneo", nombre: "Paneo orbital", frente: 0, derecha: 0, altura: 4, radio: 8, giro: 0.25, mira: 0.4 },
  { id: "primer", nombre: "Primer plano 3/4", frente: 3.5, derecha: 2.5, altura: 1.6, mira: 0.5 },
  { id: "rasante", nombre: "Rasante bajo", frente: 5, derecha: 1.5, altura: 0.9, mira: 0.6 },
  { id: "general", nombre: "General alto", frente: -6, derecha: 0, altura: 14, mira: 0 },
  { id: "travelling", nombre: "Travelling lateral", frente: 0, derecha: 6, altura: 2.2, barrido: 5, mira: 0.5 },
  { id: "seguimiento", nombre: "Seguimiento", frente: -5, derecha: 0, altura: 2.6, mira: 0.8 },
];

export function duracionToma(n) { const i = ((Math.trunc(n) % 5) + 5) % 5; return DURACIONES_TOMA_S[i]; }
export function siguienteToma(n) { return (Math.trunc(n) + 1) % TOMAS.length; }

// Amortiguación exponencial independiente de los FPS: fracción del camino al destino en este cuadro.
export function mezcla(dt, k) { return 1 - Math.exp(-Math.max(0, dt) * k); }

const limitar = (v, a, b) => Math.min(b, Math.max(a, v));

export function limitarSobreSuelo(pos, sueloEn, nCeldas) {
  let { x, y, z } = pos;
  if (nCeldas) {
    x = limitar(x, -MARGEN_MAPA, nCeldas.columnas + MARGEN_MAPA);
    z = limitar(z, -MARGEN_MAPA, nCeldas.filas + MARGEN_MAPA);
  }
  const suelo = typeof sueloEn === "function" ? sueloEn(x, z) : 0;
  return { x, y: Math.max(y, (Number.isFinite(suelo) ? suelo : 0) + ALTURA_MINIMA), z };
}

// Destino de la cámara en la toma `n`. `rumbo` es la rotación en Y del rover (el avance local es +X) y `t` los segundos de la toma.
export function destinoToma(n, objetivo, rumbo, t, sueloEn, nCeldas) {
  const toma = TOMAS[((Math.trunc(n) % TOMAS.length) + TOMAS.length) % TOMAS.length];
  const fx = Math.cos(rumbo), fz = -Math.sin(rumbo);   // avance del rover en el plano
  const dx = -fz, dz = fx;                              // lado derecho
  let frente = toma.frente, derecha = toma.derecha;
  let pos;
  if (toma.radio) {   // paneo orbital: gira alrededor del rover
    const a = rumbo + t * toma.giro;
    pos = { x: objetivo.x + Math.cos(a) * toma.radio, y: objetivo.y + toma.altura, z: objetivo.z + Math.sin(a) * toma.radio };
  } else {
    if (toma.barrido) frente += (t - 4) * (toma.barrido / 4) * 0.5;   // travelling: avanza paralelo al rover
    pos = {
      x: objetivo.x + fx * frente + dx * derecha,
      y: objetivo.y + toma.altura,
      z: objetivo.z + fz * frente + dz * derecha,
    };
  }
  return { pos: limitarSobreSuelo(pos, sueloEn, nCeldas), mira: { x: objetivo.x, y: objetivo.y + toma.mira, z: objetivo.z } };
}

// ---- Momentos dramáticos: solo con lo que ya trae la respuesta del paso (motivos del supervisor y eventos de combate) ----
export const REPETICION = { ventana_s: 1.2, duracion_s: 3, factor: 0.4, intervalo_s: 0.1 };   // 1,2 s reales se ven en 3 s
export const MOMENTOS = {
  veto: { plano: "primer", titulo: "Veto de seguridad" },
  impacto: { plano: "rasante", titulo: "Impacto" },
};
export function tipoMomento({ motivos, eventos, estado } = {}) {
  if (estado === "EXITO" || estado === "FRACASO" || estado === "SIN_RUTA" || estado === "MODO_SEGURO") return null;   // la pantalla final manda
  if ((motivos || []).some((m) => String(m).startsWith("V-"))) return "veto";
  if ((eventos || []).some((e) => /destruid|colisi/i.test(String(e)))) return "impacto";
  return null;
}

// ---- Buffer de repetición: últimas posiciones del rover guardadas en el cliente ----
export function nuevoBuffer() { return { muestras: [], ultima: -Infinity }; }
export function empujarMuestra(buf, t, pos, rot) {
  if (t - buf.ultima < REPETICION.intervalo_s) return buf;
  buf.ultima = t;
  buf.muestras.push({ t, x: pos.x, y: pos.y, z: pos.z, rot });
  const minimo = t - (REPETICION.ventana_s + 0.5);
  while (buf.muestras.length && buf.muestras[0].t < minimo) buf.muestras.shift();
  return buf;
}
// Muestras de la ventana más reciente, con tiempo relativo (0 = la más antigua de la ventana).
export function recortarRepeticion(buf) {
  const m = buf.muestras;
  if (m.length < 2) return [];
  const fin = m[m.length - 1].t, ini = fin - REPETICION.ventana_s;
  const sel = m.filter((s) => s.t >= ini);
  if (sel.length < 2) return [];
  const t0 = sel[0].t;
  return sel.map((s) => ({ ...s, t: s.t - t0 }));
}
// Pose interpolada en `u` entre 0 y 1 de la repetición.
export function poseRepeticion(sel, u) {
  if (!sel.length) return null;
  const total = sel[sel.length - 1].t;
  const tt = limitar(u, 0, 1) * total;
  let i = 0;
  while (i < sel.length - 2 && sel[i + 1].t < tt) i++;
  const a = sel[i], b = sel[i + 1] || a;
  const k = b.t > a.t ? limitar((tt - a.t) / (b.t - a.t), 0, 1) : 0;
  return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, z: a.z + (b.z - a.z) * k, rot: a.rot + (b.rot - a.rot) * k };
}

// ---- Prioridad y modos ----
export function debeActuar({ activado, enPartida, intro, viaje, pausa, final, manual } = {}) {
  return !!activado && !!enPartida && !intro && !viaje && !pausa && !final && !manual;
}
export function modoCine(reducido) { return reducido ? "estatico" : "automatico"; }
export function permiteRepeticion(reducido) { return !reducido; }
export function teclaPermitida(tecla, cineActivo) { return !cineActivo || TECLAS_CINE.includes(tecla); }

// ---- FPS ----
function ordenar(a) { return [...a].sort((x, y) => x - y); }
export function mediana(v) { if (!v.length) return 0; const s = ordenar(v), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
export function percentil(v, p) { if (!v.length) return 0; const s = ordenar(v); return s[Math.min(s.length - 1, Math.max(0, Math.floor(p * (s.length - 1))))]; }
export function fpsDeIntervalos(ms) { return ms.filter((d) => d > 0).map((d) => 1000 / d); }
export function evaluarFps(fps) { return { mediana: mediana(fps), p5: percentil(fps, 0.05), n: fps.length }; }
export function decidirPostproceso({ fpsCon, fpsSin, umbral = UMBRAL_FPS }) {
  if (fpsCon < umbral) return "apagar";
  if (fpsSin > 0 && fpsCon < fpsSin * 0.85) return "apagar";
  return "mantener";
}
// Monitor con ventana móvil: devuelve "apagar" cuando la mediana de dos ventanas completas seguidas queda bajo el umbral.
export function crearMonitorFps({ ventana = VENTANA_FPS, umbral = UMBRAL_FPS, veces = VECES_BAJO_UMBRAL } = {}) {
  let buf = [], seguidas = 0;
  return {
    empujar(dtMs) {
      if (!(dtMs > 0)) return "mantener";
      buf.push(1000 / dtMs);
      if (buf.length < ventana) return "mantener";
      const med = mediana(buf); buf = [];
      seguidas = med < umbral ? seguidas + 1 : 0;
      return seguidas >= veces ? "apagar" : "mantener";
    },
    reiniciar() { buf = []; seguidas = 0; },
  };
}
