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
    Urano: ["#9fdde0", "#c4eef0", "#7fc8cc", "#b6e6e8"],
    Neptuno: ["#3f6fd6", "#2f58b0", "#5a86e0", "#24459a"],
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
    const t = planeta === "Marte"
      ? (texturaSuelo || (texturaSuelo = crearTexturaSuelo()))
      : crearTexturaPlaneta(planeta);
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

export { generadorAleatorio, lienzo, texturaParaPlaneta, obtenerTexturaSolar, texturaSombraRadial, obtenerTexturaCarbono };
