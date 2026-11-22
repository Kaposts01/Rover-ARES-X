// Texturas procedurales de la escena (suelo por planeta, panel solar, sombra de contacto, fibra de carbono).
// Se crean una vez y quedan en caché. Movidas desde app.js sin cambios de comportamiento.
import * as THREE from "three";

// Generador pseudoaleatorio (xorshift32) para texturas y guijarros reproducibles
function generadorAleatorio(semilla) {
  let s = (semilla >>> 0) || 1;
  return () => {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

// Texturas procedurales (se crean una vez): suelo marciano y células del panel solar
let texturaSuelo = null;
let texturaSolar = null;
const texturasPorPlaneta = new Map();

// Textura del suelo de Júpiter (bandas de nubes) y de Mercurio (cráteres); Marte usa la suya
function crearTexturaPlaneta(planeta) {
  const tam = 512;
  const c = lienzo(tam);
  const x = c.getContext("2d");
  const rnd = generadorAleatorio(planeta.length * 97 + 3);
  // Gigantes gaseosos: bandas de nubes con su paleta
  const BANDAS_GIGANTE = {
    Saturno: ["#e9d8a6", "#f5ead0", "#c9b07a", "#efe0b0"],
    Urano: ["#a7d6d8", "#c8e8ea", "#86c0c4", "#bcdfe0"],
    // Neptuno: azules grisáceos y de media luminosidad (antes un azul puro saturado que se comía el contraste del HUD)
    Neptuno: ["#6a86ad", "#5a7499", "#7f9bc0", "#4f678c"],
  };
  if (planeta === "Venus") {
    // Venus: llanuras ocres con grietas de lava incandescente y charcos
    x.fillStyle = "#8a5a2a";
    x.fillRect(0, 0, tam, tam);
    for (let i = 0; i < 500; i++) {
      x.fillStyle = `rgba(190, 130, 60, ${(0.08 + rnd() * 0.1).toFixed(3)})`;
      x.beginPath(); x.arc(rnd() * tam, rnd() * tam, 6 + rnd() * 30, 0, Math.PI * 2); x.fill();
    }
    for (let i = 0; i < 60; i++) {
      x.strokeStyle = `rgba(255, 110, 30, ${(0.5 + rnd() * 0.4).toFixed(3)})`;
      x.lineWidth = 1 + rnd() * 2.5;
      x.beginPath(); x.moveTo(rnd() * tam, rnd() * tam);
      x.quadraticCurveTo(rnd() * tam, rnd() * tam, rnd() * tam, rnd() * tam); x.stroke();
    }
  } else if (planeta === "Tierra") {
    // Tierra: manchas de hierba, tierra y agua
    x.fillStyle = "#6f8f4a";
    x.fillRect(0, 0, tam, tam);
    const cols = ["#557a3a", "#8a7a4a", "#4a6f8f", "#9aa870"];
    for (let i = 0; i < 380; i++) {
      x.fillStyle = cols[i % cols.length];
      x.globalAlpha = 0.25 + rnd() * 0.25;
      x.beginPath(); x.arc(rnd() * tam, rnd() * tam, 8 + rnd() * 36, 0, Math.PI * 2); x.fill();
    }
    x.globalAlpha = 1;
  } else if (BANDAS_GIGANTE[planeta]) {
    const bandas = BANDAS_GIGANTE[planeta];
    const alto = tam / 24;
    for (let i = 0; i < 24; i++) {
      x.fillStyle = bandas[i % bandas.length];
      x.fillRect(0, i * alto, tam, alto + 1);
    }
    for (let i = 0; i < 600; i++) {
      x.fillStyle = `rgba(255, 255, 255, ${(0.04 + rnd() * 0.07).toFixed(3)})`;
      x.beginPath(); x.ellipse(rnd() * tam, rnd() * tam, 8 + rnd() * 30, 2 + rnd() * 4, 0, 0, Math.PI * 2); x.fill();
    }
  } else if (planeta === "Júpiter") {
    const bandas = ["#c9a06a", "#efe3c8", "#8a5a3a", "#dcb98a", "#f4ead2", "#a0704a"];
    const alto = tam / 24;
    for (let i = 0; i < 24; i++) {
      x.fillStyle = bandas[i % bandas.length];
      x.fillRect(0, i * alto, tam, alto + 1);
    }
    for (let i = 0; i < 900; i++) {
      x.fillStyle = `rgba(255, 255, 255, ${(0.05 + rnd() * 0.08).toFixed(3)})`;
      x.beginPath();
      x.ellipse(rnd() * tam, rnd() * tam, 8 + rnd() * 30, 2 + rnd() * 4, 0, 0, Math.PI * 2);
      x.fill();
    }
  } else {
    // Mercurio: gris con cráteres (sombra oscura y borde claro)
    x.fillStyle = "#8c8c90";
    x.fillRect(0, 0, tam, tam);
    for (let i = 0; i < 700; i++) {
      const r = 3 + rnd() * 24;
      const cx = rnd() * tam;
      const cy = rnd() * tam;
      x.fillStyle = "rgba(40, 40, 44, 0.35)";
      x.beginPath(); x.arc(cx, cy, r, 0, Math.PI * 2); x.fill();
      x.fillStyle = "rgba(200, 200, 205, 0.18)";
      x.beginPath(); x.arc(cx + r * 0.25, cy + r * 0.25, r * 0.85, 0, Math.PI * 2); x.fill();
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

function texturaParaPlaneta(planeta) {
  if (!texturasPorPlaneta.has(planeta)) {
    // Planetas rocosos: suelo fbm con relieve (color + normales); gigantes: bandas de nubes; si falla, la textura anterior
    let t = null;
    try { const suelo = sueloProcedural(planeta); if (suelo) t = suelo.mapa; } catch (e) { console.warn("texturas: suelo procedural no disponible", e); }
    if (!t) t = planeta === "Marte" ? (texturaSuelo || (texturaSuelo = crearTexturaSuelo())) : crearTexturaPlaneta(planeta);
    texturasPorPlaneta.set(planeta, t);
  }
  return texturasPorPlaneta.get(planeta);
}

function lienzo(tam) {
  const c = document.createElement("canvas");
  c.width = tam;
  c.height = tam;
  return c;
}

function crearTexturaSuelo() {
  const tam = 512;
  const azarTex = generadorAleatorio(7);
  const color = lienzo(tam);
  const cc = color.getContext("2d");
  cc.fillStyle = "#b8704a";
  cc.fillRect(0, 0, tam, tam);
  // Manchas grandes de óxido más oscuro y más claro
  for (let i = 0; i < 900; i++) {
    const x = azarTex() * tam;
    const y = azarTex() * tam;
    const r = 4 + azarTex() * 26;
    cc.fillStyle = azarTex() < 0.5 ? "rgba(90, 40, 22, 0.10)" : "rgba(235, 170, 120, 0.09)";
    cc.beginPath();
    cc.arc(x, y, r, 0, Math.PI * 2);
    cc.fill();
  }
  // Grano fino
  for (let i = 0; i < 9000; i++) {
    const x = azarTex() * tam;
    const y = azarTex() * tam;
    const v = 80 + azarTex() * 120;
    cc.fillStyle = `rgba(${(v * 0.6) | 0}, ${(v * 0.3) | 0}, ${(v * 0.2) | 0}, 0.35)`;
    cc.fillRect(x, y, 1.5, 1.5);
  }
  const mapa = new THREE.CanvasTexture(color);
  mapa.colorSpace = THREE.SRGBColorSpace;
  mapa.wrapS = mapa.wrapT = THREE.RepeatWrapping;
  return mapa;
}

function obtenerTexturaSolar() {
  if (texturaSolar) return texturaSolar;
  const c = lienzo(256);
  const x = c.getContext("2d");
  x.fillStyle = "#2f63b8";
  x.fillRect(0, 0, 256, 256);
  x.strokeStyle = "rgba(200, 225, 255, 0.8)";
  x.lineWidth = 2;
  for (let i = 0; i <= 6; i++) {        // 6 columnas de celdas
    x.beginPath(); x.moveTo(i * 256 / 6, 0); x.lineTo(i * 256 / 6, 256); x.stroke();
  }
  for (let j = 0; j <= 4; j++) {        // 4 filas de celdas
    x.beginPath(); x.moveTo(0, j * 64); x.lineTo(256, j * 64); x.stroke();
  }
  texturaSolar = new THREE.CanvasTexture(c);
  texturaSolar.colorSpace = THREE.SRGBColorSpace;
  return texturaSolar;
}

// Degradado radial para las sombras de contacto (rover)
let texturaSombraCache = null;
function texturaSombraRadial() {
  if (texturaSombraCache) return texturaSombraCache;
  const c = lienzo(128);
  const x = c.getContext("2d");
  const g = x.createRadialGradient(64, 64, 4, 64, 64, 64);
  g.addColorStop(0, "rgba(0, 0, 0, 0.85)");
  g.addColorStop(1, "rgba(0, 0, 0, 0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
  texturaSombraCache = new THREE.CanvasTexture(c);
  return texturaSombraCache;
}

// Textura de fibra de carbono (tejido diagonal) para la cubierta
let texturaCarbonoCache = null;
function obtenerTexturaCarbono() {
  if (texturaCarbonoCache) return texturaCarbonoCache;
  const c = lienzo(128);
  const x = c.getContext("2d");
  x.fillStyle = "#1a1d24";
  x.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 128; i += 8) {
    for (let j = 0; j < 128; j += 8) {
      x.fillStyle = (i + j) % 16 === 0 ? "#2e3440" : "#14161c";
      x.fillRect(i, j, 8, 8);
    }
  }
  texturaCarbonoCache = new THREE.CanvasTexture(c);
  texturaCarbonoCache.colorSpace = THREE.SRGBColorSpace;
  texturaCarbonoCache.wrapS = texturaCarbonoCache.wrapT = THREE.RepeatWrapping;
  texturaCarbonoCache.repeat.set(2, 2);
  return texturaCarbonoCache;
}

// ---------- Suelo procedural con relieve (Fase 6): color y mapa de normales del mismo campo de alturas ----------
// Ruido de valor periódico (la textura se repite sin costuras) y fbm de varias octavas. Determinista por planeta.
function ruidoPeriodico(semilla) {
  const P = 256, tabla = new Float32Array(P * P), rnd = generadorAleatorio(semilla);
  for (let i = 0; i < tabla.length; i++) tabla[i] = rnd();
  const v = (ix, iy, per) => tabla[(((iy % per) + per) % per) * P + (((ix % per) + per) % per)];
  // x, y en [0, per): periodo entero por octava
  return (x, y, per) => {
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const a = v(ix, iy, per), b = v(ix + 1, iy, per), c = v(ix, iy + 1, per), d = v(ix + 1, iy + 1, per);
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  };
}

// Estilo del suelo por planeta rocoso: rampa de color (de lo hondo a lo alto), cráteres, grietas y fuerza del relieve
const ESTILO_SUELO = {
  Marte: { rampa: ["#5a2a18", "#8e4a2c", "#b8704a", "#d29466", "#e2b088"], crateres: 12, tamCrater: 0.55, grietas: 0, relieve: 2.2, grano: 0.22 },
  Mercurio: { rampa: ["#3c3c40", "#626266", "#8c8c90", "#a9a9ad", "#c4c4c8"], crateres: 90, tamCrater: 1, grietas: 0, relieve: 3.0, grano: 0.18 },
  Venus: { rampa: ["#2b1a10", "#4a3020", "#6e4a2c", "#8a6238", "#a8804a"], crateres: 5, tamCrater: 0.6, grietas: 1, relieve: 2.4, grano: 0.2 },
  Tierra: { rampa: ["#3e5a2c", "#557a3a", "#6f8f4a", "#8a7a4a", "#a39a6a"], crateres: 0, grietas: 0, relieve: 1.6, grano: 0.25 },
};

function hexARgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function rampa(colores, t) {
  const k = Math.min(0.9999, Math.max(0, t)) * (colores.length - 1), i = Math.floor(k), f = k - i;
  const a = colores[i], b = colores[i + 1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

function crearSueloProcedural(planeta, tam = 512) {
  const est = ESTILO_SUELO[planeta];
  const semilla = [...planeta].reduce((s, ch) => s * 31 + ch.charCodeAt(0), 7) >>> 0;
  const ruido = ruidoPeriodico(semilla), rnd = generadorAleatorio(semilla ^ 0x9e3779b9);
  const H = new Float32Array(tam * tam);
  // fbm de 6 octavas, periodo base 4 celdas de ruido sobre la textura
  for (let y = 0; y < tam; y++) {
    for (let x = 0; x < tam; x++) {
      let h = 0, amp = 0.5, per = 4, sum = 0;
      for (let o = 0; o < 6; o++) {
        h += amp * ruido((x / tam) * per, (y / tam) * per, per); sum += amp;
        amp *= 0.5; per *= 2;
      }
      H[y * tam + x] = h / sum;
    }
  }
  // Grietas (Venus): crestas del ruido, finas y hundidas
  const grieta = new Float32Array(tam * tam);
  if (est.grietas) {
    for (let y = 0; y < tam; y++) for (let x = 0; x < tam; x++) {
      const n = ruido((x / tam) * 8 + 50, (y / tam) * 8 + 50, 8) * 0.65 + ruido((x / tam) * 16 + 9, (y / tam) * 16 + 9, 16) * 0.35;
      const g = Math.max(0, 1 - Math.abs(n - 0.5) * 32);
      grieta[y * tam + x] = g; H[y * tam + x] -= g * 0.12;
    }
  }
  // Cráteres: cuenco hundido con borde levantado (con envoltura: la textura sigue repitiéndose sin costura)
  for (let k = 0; k < est.crateres; k++) {
    const grande = k % 9 === 0 && est.tamCrater >= 1;   // los cráteres grandes solo en los cuerpos muy craterizados
    const cx = rnd() * tam, cy = rnd() * tam, r = ((grande ? 34 : 6) + rnd() * (grande ? 30 : 16)) * (est.tamCrater || 1);
    const fuerza = est.tamCrater >= 1 ? 1 : 0.55;
    const x0 = Math.floor(cx - r * 1.5), x1 = Math.ceil(cx + r * 1.5), y0 = Math.floor(cy - r * 1.5), y1 = Math.ceil(cy + r * 1.5);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const d = Math.hypot(x - cx, y - cy) / r; if (d > 1.5) continue;
      const cuenco = d < 1 ? -(1 - d * d) * 0.16 * fuerza : 0;
      const borde = Math.exp(-((d - 1) ** 2) / 0.04) * 0.05 * fuerza;
      const i = (((y % tam) + tam) % tam) * tam + (((x % tam) + tam) % tam);
      H[i] += cuenco + borde;
    }
  }
  // Normalizar alturas a [0, 1]
  let lo = Infinity, hi = -Infinity;
  for (const v of H) { if (v < lo) lo = v; if (v > hi) hi = v; }
  const rango = hi - lo || 1;
  for (let i = 0; i < H.length; i++) H[i] = (H[i] - lo) / rango;

  const colores = est.rampa.map(hexARgb);
  const color = lienzo(tam), cc = color.getContext("2d"), img = cc.createImageData(tam, tam);
  const normal = lienzo(tam), cn = normal.getContext("2d"), imgN = cn.createImageData(tam, tam);
  const at = (x, y) => H[(((y % tam) + tam) % tam) * tam + (((x % tam) + tam) % tam)];
  for (let y = 0; y < tam; y++) {
    for (let x = 0; x < tam; x++) {
      const i = y * tam + x, h = H[i];
      // pendiente local para oscurecer laderas y la normal por diferencias centrales
      const dx = (at(x + 1, y) - at(x - 1, y)) * est.relieve * tam / 64, dy = (at(x, y + 1) - at(x, y - 1)) * est.relieve * tam / 64;
      const grano = (rnd() - 0.5) * est.grano;
      let [r, g, b] = rampa(colores, h * 0.85 + 0.1 + grano * 0.25);
      const sombreado = 1 - Math.min(0.35, Math.hypot(dx, dy) * 0.12);
      r *= sombreado; g *= sombreado; b *= sombreado;
      if (grieta[i] > 0) {   // lava incandescente en las grietas de Venus
        const k = grieta[i];
        r = r + (255 - r) * k; g = g + (120 - g) * k; b = b + (30 - b) * k * 0.6;
      }
      const j = i * 4;
      img.data[j] = r; img.data[j + 1] = g; img.data[j + 2] = b; img.data[j + 3] = 255;
      const n = Math.hypot(dx, dy, 1);
      imgN.data[j] = (-dx / n * 0.5 + 0.5) * 255; imgN.data[j + 1] = (dy / n * 0.5 + 0.5) * 255; imgN.data[j + 2] = (1 / n * 0.5 + 0.5) * 255; imgN.data[j + 3] = 255;
    }
  }
  cc.putImageData(img, 0, 0); cn.putImageData(imgN, 0, 0);
  const mapa = new THREE.CanvasTexture(color);
  mapa.colorSpace = THREE.SRGBColorSpace; mapa.wrapS = mapa.wrapT = THREE.RepeatWrapping; mapa.anisotropy = 4;
  const mapaNormal = new THREE.CanvasTexture(normal);
  mapaNormal.wrapS = mapaNormal.wrapT = THREE.RepeatWrapping;
  return { mapa, normal: mapaNormal };
}

const suelosProcedurales = new Map();   // planeta -> { mapa, normal }
function sueloProcedural(planeta) {
  if (!ESTILO_SUELO[planeta]) return null;
  if (!suelosProcedurales.has(planeta)) suelosProcedurales.set(planeta, crearSueloProcedural(planeta));
  return suelosProcedurales.get(planeta);
}
// Mapa de normales del suelo (null en los gigantes gaseosos: sus «suelos» son nubes)
function normalParaPlaneta(planeta) {
  const s = sueloProcedural(planeta);
  return s ? s.normal : null;
}

export { generadorAleatorio, lienzo, texturaParaPlaneta, normalParaPlaneta, obtenerTexturaSolar, texturaSombraRadial, obtenerTexturaCarbono };
