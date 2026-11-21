// ARES-X · escena 3D del rover (ARX-04, ARX-05 y ARX-20: diseño realista). El motor está en Python; aquí solo se dibuja y se envían acciones.
import * as THREE from "three";
import { OrbitControls } from "/static/vendor/OrbitControls.js";
import { iniciarLaboratorios } from "/static/laboratorio.js?v=r14";
import * as efectos from "/static/efectos.js?v=r14";
import * as adaptador from "/static/adaptador.js?v=r14";
import { aplicarMoviles, reiniciarEventos } from "/static/moviles.js?v=r14";
import { crearEvolucion } from "/static/evolucion3d.js?v=r14";
import { adaptarAG, ROTULO_EVOLUCION } from "/static/evolucion_datos.js?v=r14";
import { tieneObservada, colorCelda, MODOS, AVISO_SIN_OBSERVACION } from "/static/incertidumbre_datos.js?v=r14";
import { crearHolograma } from "/static/holo3d.js?v=r14";
import { adaptarHolo, ROTULO_HOLO } from "/static/holo_datos.js?v=r14";

const TIPO_OBSTACULO = 1;
const TIPO_BARRANCO = 2;
const RUMBO_TECLA = {
  ArrowUp: "N", w: "N", ArrowDown: "S", s: "S", ArrowRight: "E", d: "E", ArrowLeft: "O", a: "O",
  "7": "NO", "9": "NE", "1": "SO", "3": "SE",
  // Numpad con NumLock apagado envía estas teclas en lugar de los dígitos
  Home: "NO", PageUp: "NE", End: "SO", PageDown: "SE",
};
const DELTA = { N: [-1, 0], S: [1, 0], E: [0, 1], O: [0, -1], NE: [-1, 1], NO: [-1, -1], SE: [1, 1], SO: [1, -1] };
const ESTADOS_TERMINALES = ["EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"];

const elMensaje = document.getElementById("mensaje");
const escena = document.getElementById("escena");
let reproduciendo = null;   // id del temporizador de reproducción, o null
let cargando = false;       // true mientras el motor crea una partida nueva

function avisar(texto) {
  elMensaje.textContent = texto;
}

// ---------- API ----------
// Un fallo al dibujar no debe cortar el ciclo de /paso, la pantalla final ni la cadena (E5): se registra una vez
const fallosDibujo = new Set();
function dibujarSeguro(nombre, fn) {
  try {
    fn();
  } catch (err) {
    const clave = `${nombre}:${err.message}`;
    if (!fallosDibujo.has(clave)) {
      fallosDibujo.add(clave);
      console.error(`[${nombre}]`, err);
    }
  }
}

// Pedido al motor. Un 500 (error interno) abre el aviso con tres salidas, en vez de dejar la partida congelada.
async function llamar(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: { "Content-Type": "application/json" } };
  if (cuerpo !== undefined) opciones.body = JSON.stringify(cuerpo);
  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch (err) {
    avisar("No hay conexión con el motor. Revisa que la API esté levantada.");
    return null;
  }
  const datos = await respuesta.json().catch(() => ({ motivo: "respuesta no válida" }));
  if (!respuesta.ok) {
    avisar(datos.motivo || `error ${respuesta.status}`);
    if (respuesta.status === 500) ofrecerErrorMotor(datos.motivo || "error interno", () => llamar(metodo, ruta, cuerpo));
    return null;
  }
  return datos;
}

let reintentarMotor = null;
function ofrecerErrorMotor(motivo, reintentar) {
  reintentarMotor = reintentar;
  document.getElementById("error-motor-texto").textContent =
    `${motivo}. Puedes reintentar la última acción, reiniciar la partida con la misma semilla o volver al menú.`;
  document.getElementById("error-motor").classList.remove("oculto");
}
document.getElementById("error-reintentar").addEventListener("click", async () => {
  document.getElementById("error-motor").classList.add("oculto");
  if (reintentarMotor) await reintentarMotor();
});
document.getElementById("error-reiniciar").addEventListener("click", async () => {
  document.getElementById("error-motor").classList.add("oculto");
  if (estado && !estado.sin_partida) await conCarga(() => cargarPartida(estado.semilla, estado.nivel), { transicion: true });
});
document.getElementById("error-menu").addEventListener("click", () => {
  cerrarAvisos();
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
});

// ---------- utilidades de diseño ----------
// Ruido determinista por celda: el mismo mapa y la misma semilla siempre se ven igual
function azar(f, c, k = 0) {
  const x = Math.sin(f * 127.1 + c * 311.7 + k * 74.7) * 43758.5453;
  return x - Math.floor(x);
}

// Generador pseudoaleatorio (xorshift32) para texturas y guijarros reproducibles
function generadorAleatorio(semilla) {
  let s = (semilla >>> 0) || 1;
  return () => {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

// Rectángulo con esquinas redondeadas en el plano XY (base del casco del rover)
function formaRedondeada(x0, y0, ancho, alto, r) {
  const f = new THREE.Shape();
  f.moveTo(x0 + r, y0);
  f.lineTo(x0 + ancho - r, y0);
  f.quadraticCurveTo(x0 + ancho, y0, x0 + ancho, y0 + r);
  f.lineTo(x0 + ancho, y0 + alto - r);
  f.quadraticCurveTo(x0 + ancho, y0 + alto, x0 + ancho - r, y0 + alto);
  f.lineTo(x0 + r, y0 + alto);
  f.quadraticCurveTo(x0, y0 + alto, x0, y0 + alto - r);
  f.lineTo(x0, y0 + r);
  f.quadraticCurveTo(x0, y0, x0 + r, y0);
  return f;
}

// ---------- escena ----------
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));   // rendimiento: tope de 1,5
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;   // PCF simple: más barato que el suave
escena.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// Niebla del color del horizonte: el terreno lejano se funde con el cielo en lugar de cortarse
const COLOR_HORIZONTE = 0xd9946a;
scene.fog = new THREE.Fog(COLOR_HORIZONTE, 40, 90);

const camara = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 600);
const controles = new OrbitControls(camara, renderer.domElement);
controles.enableDamping = true;
controles.target.set(15, 0, 10);
// Límites de cámara (ARX-16): sin ellos se podía entrar en el terreno, perder la escena al alejarse
// y desplazar el objetivo fuera del mapa con el clic derecho.
controles.minDistance = 6;                     // no se entra en el terreno ni en el rover
controles.maxDistance = 60;                    // la escena no se pierde al alejarse
controles.minPolarAngle = 0.2;                 // no se pasa por encima del cenit
controles.maxPolarAngle = Math.PI / 2 - 0.05;  // la cámara no baja bajo el horizonte del suelo
controles.screenSpacePanning = false;          // el desplazamiento sigue el suelo, no la pantalla
controles.zoomSpeed = 0.35;
controles.addEventListener("start", () => { camaraSiguiendo = false; });   // mover la cámara a mano deja de seguir                    // ARX-23: zoom más fino; el OrbitControls escala con la distancia
const MARGEN_OBJETIVO = 4;                     // el objetivo de la cámara no sale del mapa más de esto
let limitesMapa = null;
let camaraSiguiendo = true;                    // ARX-62: la cámara sigue al rover salvo que el usuario la mueva                        // se fija al construir el mapa
window.__ares = { camara, controles };   // QA del ratón (api/verificar_raton.py); no cambia la escena
// El grupo del rover se expone solo para revisar el diseño en las capturas (se lee cuando ya existe)
window.__ares.rover = () => grupoRover;
window.__ares.renderer = renderer;   // QA de rendimiento; no cambia la escena
window.__ares.scene = scene;
// Efectos de los eventos (QA con datos simulados; el motor decide cuándo ocurren)
window.__ares.efectos = efectos;

// Sol: dirección común a la luz direccional y al brillo del cielo
const DIR_SOL = new THREE.Vector3(14, 26, -8).normalize();

// Cielo con degradado y disco solar: una cúpula que sigue a la cámara y reemplaza el fondo plano
const materialCielo = new THREE.ShaderMaterial({
  side: THREE.BackSide,
  depthWrite: false,
  fog: false,
  uniforms: {
    arriba: { value: new THREE.Vector3(0.09, 0.14, 0.27) },     // azul de crepúsculo (sRGB)
    horizonte: { value: new THREE.Vector3(0.85, 0.58, 0.42) },  // óxido cálido (sRGB)
    sol: { value: DIR_SOL },
  },
  vertexShader: `
    varying vec3 vDir;
    void main() {
      vDir = normalize(position);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: `
    uniform vec3 arriba;
    uniform vec3 horizonte;
    uniform vec3 sol;
    varying vec3 vDir;
    void main() {
      float altura = smoothstep(0.0, 0.5, vDir.y);
      vec3 color = mix(horizonte, arriba, altura);
      float brillo = max(dot(vDir, normalize(sol)), 0.0);
      color += vec3(1.0, 0.72, 0.45) * (0.35 * pow(brillo, 16.0) + 1.2 * pow(brillo, 400.0));
      gl_FragColor = vec4(color, 1.0);
    }`,
});
const cielo = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), materialCielo);
cielo.renderOrder = -1;
scene.add(cielo);

scene.add(new THREE.HemisphereLight(0xb9cfff, 0x4a2818, 0.85));
const sol = new THREE.DirectionalLight(0xffe0bd, 2.6);
sol.castShadow = true;
sol.shadow.mapSize.set(1024, 1024);   // rendimiento: 1024 para las sombras del rover y la sonda
sol.shadow.bias = -0.0006;
sol.shadow.normalBias = 0.02;
scene.add(sol, sol.target);

const grupoMapa = new THREE.Group();
scene.add(grupoMapa);
const grupoRover = new THREE.Group();
scene.add(grupoRover);
const grupoRuta = new THREE.Group();
scene.add(grupoRuta);
const grupoDrones = new THREE.Group();
scene.add(grupoDrones);
const grupoEfectos = new THREE.Group();
scene.add(grupoEfectos);
const grupoRecorrido = new THREE.Group();
scene.add(grupoRecorrido);
const grupoRiesgo = new THREE.Group();   // M15: capa opcional de riesgo estimado (apagada por defecto)
scene.add(grupoRiesgo);
window.__ares.grupoRiesgo = grupoRiesgo;   // QA de la capa de riesgo

let mapa = null;
let estado = null;
let animados = [];      // cristales que giran y oscilan
let halos = [];         // anillos de luz bajo los cristales
let parpadeos = [];     // luces que parpadean (refugio)
let ruedasGiro = [];    // ejes de las 6 ruedas del rover
let cabezaRover = null; // cabeza de cámara del mástil (se mueve sola)
let roverDestino = null;
let planetaActivo = "Marte";     // planeta de la partida actual (aspecto y sonda)
let modoPlanetaActivo = "rover"; // "rover" o "sonda"
let sondaRover = null;           // sonda 3D cuando el modo es sonda (gigantes)// posición y rumbo a los que avanza el rover suavemente

const materiales = {
  roca: new THREE.MeshStandardMaterial({ color: 0x8a5e4a, roughness: 0.92, flatShading: true }),
  borde: new THREE.MeshStandardMaterial({ color: 0x8c3f24, roughness: 0.85, flatShading: true }),
  refugio: new THREE.MeshStandardMaterial({ color: 0xdfe4ec, roughness: 0.38, metalness: 0.35 }),
  cupula: new THREE.MeshStandardMaterial({ color: 0x9cd9ff, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.32, depthWrite: false }),
  cristal: new THREE.MeshStandardMaterial({ color: 0x8fdcff, emissive: 0x2a7fd0, emissiveIntensity: 0.9, roughness: 0.08, metalness: 0.1, flatShading: true, transparent: true, opacity: 0.92 }),
  halo: new THREE.MeshBasicMaterial({ color: 0x5ab4ff, transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }),
  dron: new THREE.MeshStandardMaterial({ color: 0x2a2f3c, roughness: 0.4, metalness: 0.6 }),
  carroceria: new THREE.MeshStandardMaterial({ color: 0xc4cfde, roughness: 0.3, metalness: 0.45 }),   // anodizado
  cubierta: new THREE.MeshStandardMaterial({ color: 0x8390a6, roughness: 0.5, metalness: 0.2 }),
  soporte: new THREE.MeshStandardMaterial({ color: 0x3a4354, roughness: 0.5, metalness: 0.2 }),
  plato: new THREE.MeshStandardMaterial({ color: 0xe9edf3, roughness: 0.3, metalness: 0.4, side: THREE.DoubleSide }),
  rueda: new THREE.MeshStandardMaterial({ color: 0x141418, roughness: 0.95 }),
  llanta: new THREE.MeshStandardMaterial({ color: 0xc9d1dc, roughness: 0.3, metalness: 0.5 }),
  panel: new THREE.MeshStandardMaterial({ color: 0x1f3c76, roughness: 0.35, metalness: 0.1, emissive: 0x0b2350, emissiveIntensity: 0.8 }),
  lente: new THREE.MeshStandardMaterial({ color: 0x06121f, roughness: 0.05, metalness: 0.9 }),
  acento: new THREE.MeshBasicMaterial({ color: 0x3ee0ff, toneMapped: false }),
  faro: new THREE.MeshBasicMaterial({ color: 0xfff3c4, toneMapped: false }),
  piloto: new THREE.MeshBasicMaterial({ color: 0xff3d4d, toneMapped: false }),
  guijarro: new THREE.MeshStandardMaterial({ color: 0x8e5e44, roughness: 0.95, flatShading: true }),
  junta: new THREE.MeshStandardMaterial({ color: 0x5a6474, roughness: 0.5, metalness: 0.5 }),
  tornillo: new THREE.MeshStandardMaterial({ color: 0xaeb8c6, roughness: 0.3, metalness: 0.8 }),
  ventilacion: new THREE.MeshStandardMaterial({ color: 0x0c0e12, roughness: 0.9 }),
  cable: new THREE.MeshStandardMaterial({ color: 0x101216, roughness: 0.8 }),
  buje: new THREE.MeshBasicMaterial({ color: 0xff9a3c, toneMapped: false }),
  acentoOscuro: new THREE.MeshStandardMaterial({ color: 0x3b5f8a, roughness: 0.4, metalness: 0.4 }),
};
const materialRutaPlan = new THREE.MeshBasicMaterial({ color: 0xffc857, toneMapped: false, transparent: true, opacity: 0.9 });
const materialRutaReal = new THREE.MeshBasicMaterial({ color: 0x5fd3ff, toneMapped: false });
let recorridoRover = [];   // celdas visitadas en la partida actual
// Color del dron según su estado de la máquina de estados (ARX-06)
const COLOR_DRON = { patrulla: 0x40c060, alerta: 0xf0d040, persecucion: 0xf08030, ataque: 0xe03030 };

// Texturas procedurales (se crean una vez): suelo marciano y células del panel solar
let texturaSuelo = null;
const vortices = [];   // vórtices de Júpiter: giran lentamente
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

// ---------- capa de riesgo estimado (M15) ----------
const RIESGO_OPACIDAD = 0.45;
let capaRiesgoActiva = false;      // apagada por defecto

let modoCapaRiesgo = "riesgo";     // «riesgo» (M15) o «incertidumbre» (Paquete A): misma malla, mismo grupo

function limpiarCapaRiesgo() {
  for (const o of grupoRiesgo.children) {
    o.geometry.dispose();
    o.material.dispose();
  }
  grupoRiesgo.clear();
}

// Una malla con una celda por celda del mapa, pegada al relieve y con el color del riesgo de /mapa
function construirCapaRiesgo(datos) {
  limpiarCapaRiesgo();
  const rz = datos && datos.riesgo_estimado;
  const valida = Array.isArray(rz) && rz.length === datos.filas
    && rz.every((fila) => Array.isArray(fila) && fila.length === datos.columnas);
  if (!valida) return false;
  const modo = modoCapaRiesgo === "incertidumbre" && tieneObservada(datos) ? "incertidumbre" : "riesgo";
  const SUB = 2;   // cada celda en 2x2 trozos para seguir el relieve
  const pos = [];
  const col = [];
  const idx = [];
  for (let f = 0; f < datos.filas; f++) {
    for (let c = 0; c < datos.columnas; c++) {
      const rgb = colorCelda(modo, rz[f][c], modo === "incertidumbre" ? datos.observada[f][c] : 0);
      if (!rgb) continue;
      const [cr, cg, cb] = rgb;
      const base = pos.length / 3;
      for (let j = 0; j <= SUB; j++) {
        for (let i = 0; i <= SUB; i++) {
          const x = c + i / SUB;
          const z = f + j / SUB;
          pos.push(x, alturaTerreno(x, z) + 0.04, z);
          col.push(cr, cg, cb);
        }
      }
      for (let j = 0; j < SUB; j++) {
        for (let i = 0; i < SUB; i++) {
          const a = base + j * (SUB + 1) + i;
          const b = a + 1;
          const d = a + SUB + 1;
          idx.push(a, d, b, b, d, d + 1);
        }
      }
    }
  }
  if (!idx.length) return true;   // hay dato, pero todo el mapa está por debajo del umbral
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geom.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  geom.setIndex(idx);
  const malla = new THREE.Mesh(geom, new THREE.MeshBasicMaterial({
    vertexColors: true, transparent: true, opacity: RIESGO_OPACIDAD, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, side: THREE.DoubleSide,
  }));
  malla.name = modo === "incertidumbre" ? "capa-incertidumbre" : "capa-riesgo";
  malla.renderOrder = 2;
  grupoRiesgo.add(malla);
  return true;
}

// H-1 (QA 21/11): el riesgo parte de un mapa previo parcial (genetico.mapa_estimado, ≈80 % de detección); se rotula así
const ROTULO_RIESGO = "riesgo estimado: mapa previo orbital (≈80 % de detección) + sensores";
const NOTA_NO_OBSERVADA = "Una celda roja no observada viene del mapa previo, no de lo que el sensor vio.";
function avisoRiesgo(texto) {
  const el = document.getElementById("riesgo-aviso");
  if (el) el.textContent = texto;
}

// Pide /mapa (el riesgo estimado cambia con la partida) y redibuja la capa; si no hay dato, la apaga y lo dice
async function actualizarCapaRiesgo() {
  limpiarCapaRiesgo();
  avisoRiesgo("");
  if (leyendaIncertidumbre) leyendaIncertidumbre.hidden = true;
  if (!capaRiesgoActiva) return;
  const mp = mapa ? await llamar("GET", "/mapa") : null;
  if (!capaRiesgoActiva) return;   // se apagó mientras llegaba la respuesta
  aplicarModoRiesgo(mp);
  if (mp && construirCapaRiesgo(mp)) {
    const el = document.getElementById("riesgo-aviso");
    if (el && !el.textContent) {
      avisoRiesgo(modoCapaRiesgo === "incertidumbre" ? `${ROTULO_RIESGO}. ${NOTA_NO_OBSERVADA}` : ROTULO_RIESGO);
    }
  } else {
    capaRiesgoActiva = false;
    const caja = document.getElementById("riesgo-capa");
    if (caja) caja.checked = false;
    avisoRiesgo(mapa ? "sin datos de riesgo" : "sin partida: no hay riesgo que mostrar");
  }
}

// Refresco por avance del rover con la capa encendida: una sola lectura de /mapa por paso, sin solapar y sin parpadeo
let refrescoRiesgoEnVuelo = false;
async function refrescarCapaRiesgoPorPaso() {
  if (!capaRiesgoActiva || !mapa || refrescoRiesgoEnVuelo) return;
  refrescoRiesgoEnVuelo = true;
  try {
    const mp = await llamar("GET", "/mapa");
    if (capaRiesgoActiva && mp) construirCapaRiesgo(mp);
  } finally {
    refrescoRiesgoEnVuelo = false;
  }
}

// Selector Riesgo / Incertidumbre: sin `observada` en /mapa, Incertidumbre se deshabilita con aviso
const selectorModoRiesgo = document.getElementById("riesgo-modo");
const leyendaIncertidumbre = document.getElementById("riesgo-leyenda");
function aplicarModoRiesgo(mp) {
  const hay = tieneObservada(mp);
  if (selectorModoRiesgo) {
    const opcion = selectorModoRiesgo.querySelector('option[value="incertidumbre"]');
    if (opcion) opcion.disabled = !!mp && !hay;
    if (mp && !hay && modoCapaRiesgo === "incertidumbre") {
      modoCapaRiesgo = "riesgo";
      selectorModoRiesgo.value = "riesgo";
    }
  }
  if (leyendaIncertidumbre) leyendaIncertidumbre.hidden = !(capaRiesgoActiva && modoCapaRiesgo === "incertidumbre");
  if (mp && !hay) avisoRiesgo(AVISO_SIN_OBSERVACION);
}
if (selectorModoRiesgo) {
  selectorModoRiesgo.value = "riesgo";
  selectorModoRiesgo.addEventListener("change", () => {
    modoCapaRiesgo = MODOS.includes(selectorModoRiesgo.value) ? selectorModoRiesgo.value : "riesgo";
    actualizarCapaRiesgo();
  });
}

const cajaRiesgo = document.getElementById("riesgo-capa");
if (cajaRiesgo) {
  cajaRiesgo.checked = false;
  cajaRiesgo.addEventListener("change", () => {
    capaRiesgoActiva = cajaRiesgo.checked;
    actualizarCapaRiesgo();
  });
}

// ---------- evolución del AG en la escena (Paquete A) ----------
// Apagada: no se crea nada en la escena ni se pide nada. Encendida: una lectura de /ag (la que ya calcula el laboratorio)
let evolucion = null;                 // se crea al encender la casilla y se libera al apagarla
let evolucionEnVuelo = false;

function textoEvolucion(extra) {
  const el = document.getElementById("evo-aviso");
  if (el) {
    el.textContent = extra ? `${ROTULO_EVOLUCION}. ${extra}` : ROTULO_EVOLUCION;
    el.scrollIntoView({ block: "nearest" });
  }
}

function apagarEvolucion(motivo) {
  if (evolucion) { evolucion.dispose(); evolucion = null; }
  document.getElementById("evo-controles").classList.add("oculto");
  const caja = document.getElementById("evo-capa");
  if (caja) caja.checked = false;
  const el = document.getElementById("evo-aviso");
  if (el) el.textContent = motivo || "";
}

async function cargarEvolucion() {
  if (!evolucion || evolucionEnVuelo) return;
  evolucionEnVuelo = true;
  const boton = document.getElementById("evo-recalc");
  boton.disabled = true;
  textoEvolucion("Calculando…");
  try {
    const posicion = estado && estado.posicion;
    const ag = await llamar("GET", "/ag");
    if (!evolucion) return;   // se apagó mientras llegaba la respuesta
    const adaptado = adaptarAG(ag, posicion);
    if (!adaptado) { apagarEvolucion(ag && ag.sin_sitios ? "no quedan sitios pendientes: no hay orden que mostrar" : "sin datos del AG"); return; }
    evolucion.cargar(adaptado);
    const sel = document.getElementById("evo-gen");
    sel.replaceChildren();
    adaptado.generaciones.forEach((g, i) => {
      const o = document.createElement("option");
      o.value = String(i);
      o.textContent = `generación ${g.generacion}`;
      sel.appendChild(o);
    });
    sel.value = String(adaptado.seleccionada);
    textoEvolucion(`Calculado desde la posición actual (${posicion ? posicion.join(", ") : "—"}).`);
  } finally {
    evolucionEnVuelo = false;
    boton.disabled = false;
  }
}

const cajaEvolucion = document.getElementById("evo-capa");
if (cajaEvolucion) {
  cajaEvolucion.checked = false;
  cajaEvolucion.addEventListener("change", () => {
    if (!cajaEvolucion.checked) { apagarEvolucion(""); return; }
    if (!mapa) { apagarEvolucion("sin partida: no hay AG que mostrar"); return; }
    evolucion = crearEvolucion(scene, {
      alturaTerreno,
      alCambiar: (i, texto) => {
        const sel = document.getElementById("evo-gen");
        if (sel.options.length > i) sel.value = String(i);
        document.getElementById("evo-generacion").textContent = texto;
      },
    });
    document.getElementById("evo-controles").classList.remove("oculto");
    cargarEvolucion();
  });
  document.getElementById("evo-play").addEventListener("click", () => { if (evolucion) evolucion.reproducir(); });
  document.getElementById("evo-recalc").addEventListener("click", cargarEvolucion);
  document.getElementById("evo-gen").addEventListener("change", (ev) => { if (evolucion) evolucion.irA(Number(ev.target.value)); });
}

// ---------- holograma de IA junto al rover (Paquete A) ----------
// Apagado: no se crea nada ni se pide nada. Encendido: /rna, /difuso y /ag por paso (sin solapar); /estado ya lo pide el paso.
let holograma = null;
let holoDatos = null;
let holoEnVuelo = false;

async function refrescarHolo() {
  if (!holograma || !mapa || holoEnVuelo) return;
  holoEnVuelo = true;
  try {
    const [rna, difuso, ag] = await Promise.all([llamar("GET", "/rna"), llamar("GET", "/difuso"), llamar("GET", "/ag")]);
    if (!holograma) return;
    holoDatos = adaptarHolo({ rna, difuso, ag, estado });
    holograma.actualizar(holoDatos, grupoRover.position, camara);
  } finally {
    holoEnVuelo = false;
  }
}

const cajaHolo = document.getElementById("holo-capa");
if (cajaHolo) {
  cajaHolo.checked = false;
  cajaHolo.addEventListener("change", () => {
    const aviso = document.getElementById("holo-aviso");
    if (!cajaHolo.checked) {
      if (holograma) { holograma.dispose(); holograma = null; holoDatos = null; }
      aviso.textContent = "";
      return;
    }
    if (!mapa) { cajaHolo.checked = false; aviso.textContent = "sin partida: no hay nada que mostrar"; return; }
    holograma = crearHolograma(scene, { alturaTerreno });
    aviso.textContent = ROTULO_HOLO;
    aviso.scrollIntoView({ block: "nearest" });
    refrescarHolo();
  });
}

// ---------- terreno ----------
const RELIEVE = 0.55;            // altura máxima de las ondulaciones (sprint 4: relieve visible)
const PROFUNDIDAD_POZO = 0.5;    // hondura de un barranco
const RADIO_POZO = 0.26;         // ancho de un barranco
const MARGEN_TERRENO = 24;       // el suelo se extiende fuera del mapa para que el horizonte no se corte
let refugioPos = null;           // [x, z] del refugio: el terreno se aplana a su alrededor
let pozos = [];                  // [x, z] de los barrancos

function influenciaPozos(x, z) {
  let s = 0;
  for (const [px, pz] of pozos) {
    s += Math.exp(-((x - px) ** 2 + (z - pz) ** 2) / (2 * RADIO_POZO * RADIO_POZO));
  }
  return Math.min(s, 1);
}

// Altura del terreno en coordenadas de escena: el rover, las rocas y los drones se apoyan en ella
function alturaTerreno(x, z) {
  let h = RELIEVE * (
    Math.sin(x * 0.52 + 1.3) * Math.cos(z * 0.41 - 0.4)
    + 0.6 * Math.sin((x + z) * 0.23 + 2.1)
    + 0.35 * Math.cos(x * 1.31 - z * 0.97)
  );
  if (refugioPos) {
    const d = Math.hypot(x - refugioPos[0], z - refugioPos[1]);
    h *= THREE.MathUtils.smoothstep(d, 1.6, 4);
  }
  return h - PROFUNDIDAD_POZO * influenciaPozos(x, z);
}

// Líneas finas de celdas sobre el terreno: ayudan a leer el mapa y a seguir la ruta
function construirCuadricula(columnas, filas) {
  const paso = 0.5;
  const v = [];
  const punto = (x, z) => v.push(x, alturaTerreno(x, z) + 0.02, z);
  for (let c = 0; c <= columnas; c++) {
    for (let z = 0; z < filas; z += paso) {
      punto(c, z);
      punto(c, z + paso);
    }
  }
  for (let f = 0; f <= filas; f++) {
    for (let x = 0; x < columnas; x += paso) {
      punto(x, f);
      punto(x + paso, f);
    }
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
  const lineas = new THREE.LineSegments(geom, new THREE.LineBasicMaterial({
    color: 0xbfe6ff, transparent: true, opacity: 0.07, depthWrite: false,
  }));
  return lineas;
}

// Suelo con relieve, textura y pequeñas sombras de los barrancos
function construirTerreno(columnas, filas) {
  const ancho = columnas + 2 * MARGEN_TERRENO;
  const alto = filas + 2 * MARGEN_TERRENO;
  const geom = new THREE.PlaneGeometry(ancho, alto, ancho, alto);
  geom.rotateX(-Math.PI / 2);
  geom.translate(columnas / 2, 0, filas / 2);
  const pos = geom.attributes.position;
  const sombra = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    pos.setY(i, alturaTerreno(x, z));
    // Los barrancos se oscurecen por vértice: se leen como agujeros sin texturas nuevas
    const k = 1 - 0.8 * influenciaPozos(x, z);
    sombra[i * 3] = k;
    sombra[i * 3 + 1] = k;
    sombra[i * 3 + 2] = k;
  }
  geom.setAttribute("color", new THREE.BufferAttribute(sombra, 3));
  geom.computeVertexNormals();

  const texturaActual = texturaParaPlaneta(planetaActivo);
  texturaActual.repeat.set(ancho / 10, alto / 10);
  // Material barato (Lambert, sin brillo PBR): menos trabajo por píxel en pantalla completa
  const material = new THREE.MeshLambertMaterial({ map: texturaActual, vertexColors: true });
  const suelo = new THREE.Mesh(geom, material);
  suelo.receiveShadow = true;
  return suelo;
}

// Sitio de recarga: cristal hexagonal con puntas y núcleo luminoso (sustituye a la gema plana)
function crearGema() {
  const g = new THREE.Group();
  const cuerpo = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.13, 0.4, 6), materiales.cristal);
  const punta1 = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.18, 6), materiales.cristal);
  punta1.position.y = 0.29;
  const punta2 = new THREE.Mesh(new THREE.ConeGeometry(0.13, 0.18, 6), materiales.cristal);
  punta2.position.y = -0.29;
  punta2.rotation.x = Math.PI;
  const nucleo = new THREE.Mesh(new THREE.SphereGeometry(0.055, 12, 8), new THREE.MeshBasicMaterial({ color: 0xbff0ff, toneMapped: false }));
  g.add(cuerpo, punta1, punta2, nucleo);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

// Vórtice de Júpiter: tres aros concéntricos que giran (tormenta en las nubes)
function crearVortice(x, y, z) {
  const g = new THREE.Group();
  g.position.set(x, y + 0.05, z);
  const mat = new THREE.MeshStandardMaterial({ color: 0xf2e6cc, roughness: 0.6, transparent: true, opacity: 0.85 });
  for (let k = 0; k < 3; k++) {
    const aro = new THREE.Mesh(new THREE.TorusGeometry(0.2 + k * 0.1, 0.035, 8, 28), mat);
    aro.rotation.x = Math.PI / 2;
    aro.position.y = k * 0.04;
    g.add(aro);
  }
  vortices.push(g);
  return g;
}

// Malla instanciada a partir de una lista de matrices; sin sombra propia (rendimiento)
function instanciar(geom, material, matrices) {
  const im = new THREE.InstancedMesh(geom, material, matrices.length);
  matrices.forEach((m, k) => im.setMatrixAt(k, m));
  im.instanceMatrix.needsUpdate = true;
  im.receiveShadow = true;
  return im;
}

// Sismo (ARX-30d): las celdas nuevas pasan a barranco sin pedir /mapa. Mismo tratamiento que los barrancos
// del terreno: hoyo, oscurecido por vértice y piedras de borde con el material `borde`.
function agregarGrietas(celdas) {
  if (!mapa || !Array.isArray(celdas)) return;
  const nuevas = celdas.filter((c) => Array.isArray(c) && c.length === 2
    && mapa.tipo[c[0]] && mapa.tipo[c[0]][c[1]] !== undefined && mapa.tipo[c[0]][c[1]] !== TIPO_BARRANCO);
  if (!nuevas.length) return;   // sin celdas válidas o ya aplicadas: no se repite nada
  const bordes = [];
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Vector3();
  const p = new THREE.Vector3();
  for (const [f, c] of nuevas) {
    mapa.tipo[f][c] = TIPO_BARRANCO;
    pozos.push([c + 0.5, f + 0.5]);
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + azar(f, c, 70 + k) * 0.5;
      const bx = c + 0.5 + Math.cos(a) * 0.5;
      const bz = f + 0.5 + Math.sin(a) * 0.5;
      e.setScalar(0.6 + azar(f, c, 80 + k) * 0.8);
      q.setFromEuler(new THREE.Euler(azar(f, c, 90 + k) * 3, 0, azar(f, c, 100 + k) * 3));
      bordes.push({ x: bx, z: bz, q: q.clone(), s: e.x });
    }
  }
  const suelo = grupoMapa.children[0];
  if (suelo && suelo.geometry && suelo.geometry.attributes.color) {
    const pos = suelo.geometry.attributes.position;
    const sombra = suelo.geometry.attributes.color;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, alturaTerreno(x, z));
      const k = 1 - 0.8 * influenciaPozos(x, z);
      sombra.setXYZ(i, k, k, k);
    }
    pos.needsUpdate = true;
    sombra.needsUpdate = true;
    suelo.geometry.computeVertexNormals();
  }
  const piedras = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.1, 0), materiales.borde, bordes.length);
  bordes.forEach((b, i) => {
    p.set(b.x, alturaTerreno(b.x, b.z) + 0.02, b.z);
    e.setScalar(b.s);
    piedras.setMatrixAt(i, m.compose(p, b.q, e));
  });
  piedras.instanceMatrix.needsUpdate = true;
  piedras.receiveShadow = true;
  grupoMapa.add(piedras);
  // La cuadrícula copia la altura del terreno: se rehace en su sitio
  const rejilla = grupoMapa.children.find((o) => o.isLineSegments);
  if (rejilla && limitesMapa) {
    grupoMapa.remove(rejilla);
    rejilla.geometry.dispose();
    grupoMapa.add(construirCuadricula(limitesMapa.columnas, limitesMapa.filas));
  }
}

function construirMapa(datos) {
  limitesMapa = { columnas: datos.columnas, filas: datos.filas };
  grupoMapa.clear();
  animados = [];
  halos = [];
  parpadeos = [];
  vortices.length = 0;

  // Primero se fijan refugio y barrancos, porque la altura del terreno depende de ellos
  const [rf, rc] = datos.refugio;
  refugioPos = [rc + 0.5, rf + 0.5];
  pozos = [];
  for (let f = 0; f < datos.filas; f++) {
    for (let c = 0; c < datos.columnas; c++) {
      if (datos.tipo[f][c] === TIPO_BARRANCO) pozos.push([c + 0.5, f + 0.5]);
    }
  }

  grupoMapa.add(construirTerreno(datos.columnas, datos.filas));
  grupoMapa.add(construirCuadricula(datos.columnas, datos.filas));

  // Guijarros dispersos por el suelo (instancias: un solo dibujo para todos)
  const ancho = datos.columnas + 2 * MARGEN_TERRENO;
  const alto = datos.filas + 2 * MARGEN_TERRENO;
  const azarGuijarros = generadorAleatorio(datos.columnas * 31 + datos.filas);
  const cantidad = ES_GIGANTE(planetaActivo) ? 0 : Math.round(ancho * alto * 0.2);   // sin guijarros sobre las nubes
  const guijarros = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0), materiales.guijarro, cantidad);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Vector3();
  const p = new THREE.Vector3();
  let colocados = 0;
  for (let i = 0; i < cantidad; i++) {
    const x = -MARGEN_TERRENO + azarGuijarros() * ancho;
    const z = -MARGEN_TERRENO + azarGuijarros() * alto;
    const tam = 0.04 + azarGuijarros() * 0.09;
    // No se colocan dentro de un barranco
    if (influenciaPozos(x, z) > 0.2) continue;
    q.setFromEuler(new THREE.Euler(azarGuijarros() * 3, azarGuijarros() * 3, 0));
    p.set(x, alturaTerreno(x, z) + tam * 0.3, z);
    e.set(tam * (1 + azarGuijarros() * 0.5), tam, tam);
    m.compose(p, q, e);
    guijarros.setMatrixAt(colocados++, m);
  }
  guijarros.count = colocados;
  guijarros.instanceMatrix.needsUpdate = true;
  guijarros.castShadow = false;   // los guijarros no proyectan sombra: ahorra mucho render
  guijarros.receiveShadow = true;
  grupoMapa.add(guijarros);

  const geomRoca = new THREE.DodecahedronGeometry(1, 0);
  const geomPiedraBorde = new THREE.DodecahedronGeometry(0.1, 0);
  const geomHalo = new THREE.RingGeometry(0.32, 0.46, 32);

  // Rocas y piedras de borde como instancias (rendimiento): un dibujo por tipo en lugar de una malla por piedra
  const rocas = [];
  const bordes = [];
  const mtxX = new THREE.Matrix4();
  const rotX = new THREE.Quaternion();
  const escalaX = new THREE.Vector3();
  const posX = new THREE.Vector3();
  for (let f = 0; f < datos.filas; f++) {
    for (let c = 0; c < datos.columnas; c++) {
      const t = datos.tipo[f][c];
      const x = c + 0.5;
      const z = f + 0.5;
      const y = alturaTerreno(x, z);
      if (t === TIPO_OBSTACULO && ES_GIGANTE(planetaActivo)) {
        grupoMapa.add(crearVortice(x, y, z));
      } else if (t === TIPO_OBSTACULO) {
        // 2 o 3 rocas facetadas por celda
        const n = 2 + Math.floor(azar(f, c, 1) * 2);
        for (let k = 0; k < n; k++) {
          const tam = 0.2 + azar(f, c, 2 + k) * 0.2;
          escalaX.set(tam * (1 + azar(f, c, 10 + k) * 0.4), tam * (0.7 + azar(f, c, 20 + k) * 0.5), tam);
          posX.set(x + (azar(f, c, 30 + k) - 0.5) * 0.35, y + tam * 0.4, z + (azar(f, c, 40 + k) - 0.5) * 0.35);
          rotX.setFromEuler(new THREE.Euler(azar(f, c, 50 + k) * 3, azar(f, c, 60 + k) * 3, 0));
          rocas.push(new THREE.Matrix4().compose(posX, rotX, escalaX));
        }
      } else if (t === TIPO_BARRANCO) {
        // Borde del barranco: 6 piedras rojizas alrededor del hoyo
        for (let k = 0; k < 6; k++) {
          const a = (k / 6) * Math.PI * 2 + azar(f, c, 70 + k) * 0.5;
          const bx = x + Math.cos(a) * 0.5;
          const bz = z + Math.sin(a) * 0.5;
          escalaX.setScalar(0.6 + azar(f, c, 80 + k) * 0.8);
          posX.set(bx, alturaTerreno(bx, bz) + 0.02, bz);
          rotX.setFromEuler(new THREE.Euler(azar(f, c, 90 + k) * 3, 0, azar(f, c, 100 + k) * 3));
          bordes.push(new THREE.Matrix4().compose(posX, rotX, escalaX));
        }
      }
    }
  }
  if (rocas.length) grupoMapa.add(instanciar(geomRoca, materiales.roca, rocas));
  if (bordes.length) grupoMapa.add(instanciar(geomPiedraBorde, materiales.borde, bordes));

  for (const s of datos.sitios) {
    const [f, c] = s.pos;
    const x = c + 0.5;
    const z = f + 0.5;
    const y = alturaTerreno(x, z);
    const cristal = crearGema();
    cristal.position.set(x, y + 0.5, z);
    cristal.userData.base = y + 0.5;
    grupoMapa.add(cristal);
    animados.push(cristal);
    const halo = new THREE.Mesh(geomHalo, materiales.halo);
    halo.rotation.x = -Math.PI / 2;
    halo.position.set(x, y + 0.03, z);
    grupoMapa.add(halo);
    halos.push(halo);
  }

  // Refugio: plataforma metálica, cúpula de cristal y aro de luz
  const refugio = new THREE.Group();
  refugio.position.set(rc + 0.5, alturaTerreno(rc + 0.5, rf + 0.5), rf + 0.5);
  const plataforma = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.56, 0.12, 28), materiales.refugio);
  plataforma.position.y = 0.06;
  plataforma.castShadow = true;
  plataforma.receiveShadow = true;
  const cupula = new THREE.Mesh(new THREE.SphereGeometry(0.4, 28, 16, 0, Math.PI * 2, 0, Math.PI / 2), materiales.cupula);
  cupula.position.y = 0.12;
  const aro = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.018, 8, 40), materiales.acento);
  aro.rotation.x = Math.PI / 2;
  aro.position.y = 0.12;
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.02, 0.5, 8), materiales.soporte);
  mastil.position.set(-0.28, 0.37, 0.28);
  mastil.castShadow = true;
  const luz = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), materiales.piloto);
  luz.position.set(-0.28, 0.63, 0.28);
  refugio.add(plataforma, cupula, aro, mastil, luz);
  grupoMapa.add(refugio);
  parpadeos.push(luz);

  // La cámara y la luz se ajustan al tamaño del mapa (ARX-21: el mapa puede crecer)
  const escala = Math.max(datos.columnas, datos.filas);
  controles.target.set(datos.columnas / 2, 0, datos.filas / 2);
  camara.position.set(datos.columnas / 2, 22, datos.filas / 2 + 16);
  camara.lookAt(controles.target);
  controles.maxDistance = Math.max(60, escala * 1.5);   // mapa grande: que quepa completo sin perder el límite de 60
  scene.fog.near = escala * 0.9;
  scene.fog.far = escala * 2.4;
  sol.target.position.set(datos.columnas / 2, 0, datos.filas / 2);
  sol.position.copy(sol.target.position).addScaledVector(DIR_SOL, 60);
  const lado = escala * 0.75 + 8;
  const sc = sol.shadow.camera;
  sc.left = -lado;
  sc.right = lado;
  sc.top = lado;
  sc.bottom = -lado;
  sc.near = 1;
  sc.far = 160;
  sc.updateProjectionMatrix();
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

// Cilindro entre dos puntos (cables, varillas)
function cilindroEntre(a, b, radio, material) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const largo = dir.length();
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, largo, 6), material);
  m.position.copy(a).addScaledVector(dir, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  return m;
}

// Rueda: neumático con tacos de banda de rodadura, llanta con radios y buje naranja.
// El cuerpo se construye con el eje en y y se gira; el grupo exterior gira sobre su eje para rodar.
const geomTaco = new THREE.BoxGeometry(0.014, 0.082, 0.022);
const geomRadio = new THREE.BoxGeometry(0.1, 0.09, 0.012);
function crearRueda() {
  const eje = new THREE.Group();
  const cuerpo = new THREE.Group();
  cuerpo.rotation.x = Math.PI / 2;   // el eje de la rueda queda en z
  cuerpo.add(new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.08, 24), materiales.rueda));
  for (let k = 0; k < 6; k++) {   // rendimiento: 6 tacos por rueda
    const a = (k / 6) * Math.PI * 2;
    const taco = new THREE.Mesh(geomTaco, materiales.rueda);
    taco.position.set(Math.cos(a) * 0.1, 0, Math.sin(a) * 0.1);
    taco.rotation.y = -a;
    cuerpo.add(taco);
  }
  cuerpo.add(new THREE.Mesh(new THREE.CylinderGeometry(0.064, 0.064, 0.086, 20), materiales.llanta));
  for (let k = 0; k < 5; k++) {
    const radio = new THREE.Mesh(geomRadio, materiales.soporte);
    radio.rotation.y = (k / 5) * Math.PI;
    cuerpo.add(radio);
  }
  cuerpo.add(new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.092, 12), materiales.buje));
  eje.add(cuerpo);
  return eje;
}

// Rover de 6 ruedas con suspensión, mástil con cámara y panel solar.
// Frente = +x local, para que el rumbo coincida con el de las celdas.
function construirRover() {
  grupoRover.clear();
  ruedasGiro = [];
  // Modo sonda (gigantes): la sonda sustituye al rover (sprint 3)
  if (modoPlanetaActivo === "sonda") {
    sondaRover = efectos.crearSonda();
    sondaRover.traverse((o) => { if (o.isMesh) o.castShadow = false; });   // evita la mancha cuadrada del shadow map
    grupoRover.add(sondaRover);
    grupoRover.add(sondaRover.userData.sombra);   // disco de sombra en el suelo, bajo la sonda
    grupoRover.scale.setScalar(1.25);
    return;
  }
  sondaRover = null;

  // Casco anodizado (la base del casco queda en y = 0.2)
  const casco = new THREE.Mesh(
    new THREE.ExtrudeGeometry(formaRedondeada(-0.31, 0, 0.62, 0.1, 0.035), {
      depth: 0.28, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 3, curveSegments: 8,
    }),
    materiales.carroceria,
  );
  casco.geometry.translate(0, 0, -0.14);
  casco.position.y = 0.2;
  grupoRover.add(casco);

  // Juntas y paneles de acceso con tornillos en los costados
  for (const z of [-0.163, 0.163]) {
    for (const x of [-0.2, 0.08]) {
      const placa = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.07, 0.006), materiales.junta);
      placa.position.set(x, 0.245, z);
      grupoRover.add(placa);
      for (const [dx, dy] of [[-0.08, 0.025], [0.08, 0.025], [-0.08, -0.025], [0.08, -0.025]]) {
        const tornillo = new THREE.Mesh(new THREE.SphereGeometry(0.004, 6, 5), materiales.tornillo);
        tornillo.position.set(x + dx, 0.245 + dy, z + Math.sign(z) * 0.004);
        grupoRover.add(tornillo);
      }
    }
  }

  // Cubierta de fibra de carbono
  const cubierta = new THREE.Mesh(
    new THREE.ExtrudeGeometry(formaRedondeada(-0.24, 0, 0.44, 0.04, 0.015), { depth: 0.22, bevelEnabled: false, curveSegments: 6 }),
    materiales.carbono,
  );
  cubierta.geometry.translate(0, 0, -0.11);
  cubierta.position.y = 0.3;
  grupoRover.add(cubierta);

  // Franjas de luz a ambos lados
  for (const z of [-0.168, 0.168]) {
    const franja = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.01, 0.008), materiales.acento);
    franja.position.set(0, 0.287, z);
    grupoRover.add(franja);
  }

  // Parte trasera: rejillas de ventilación y dos pilotos pequeños
  for (const y of [0.222, 0.248, 0.274]) {
    const rejilla = new THREE.Mesh(new THREE.BoxGeometry(0.008, 0.01, 0.13), materiales.ventilacion);
    rejilla.position.set(-0.336, y, 0);
    grupoRover.add(rejilla);
  }
  for (const z of [-0.11, 0.11]) {
    const piloto = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.025, 0.05), materiales.piloto);
    piloto.position.set(-0.338, 0.27, z);
    grupoRover.add(piloto);
  }

  // Faro delantero
  const faro = new THREE.Mesh(new THREE.SphereGeometry(0.034, 10, 8), materiales.faro);
  faro.position.set(0.33, 0.24, 0);
  grupoRover.add(faro);

  // Cables desde la cubierta hacia la parte trasera
  for (const z of [-0.09, -0.13]) {
    grupoRover.add(cilindroEntre(new THREE.Vector3(-0.14, 0.33, z), new THREE.Vector3(-0.26, 0.29, z), 0.006, materiales.cable));
  }

  // Brazo robótico plegado sobre la cubierta, bajo el panel solar
  const brazo = new THREE.Group();
  brazo.position.set(-0.19, 0.355, -0.06);
  const baseBrazo = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.024, 0.03, 10), materiales.soporte);
  baseBrazo.position.y = -0.01;
  const tramo1 = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.02, 0.03), materiales.soporte);
  tramo1.position.set(0.06, 0.005, 0);
  const tramo2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.018, 0.026), materiales.acentoOscuro);
  tramo2.position.set(0.16, 0.005, 0);
  const pinza = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.016, 0.05), materiales.soporte);
  pinza.position.set(0.22, 0.005, 0);
  brazo.add(baseBrazo, tramo1, tramo2, pinza);
  grupoRover.add(brazo);

  // Panel solar inclinado sobre cuatro soportes
  const panel = new THREE.Group();
  panel.position.set(-0.04, 0.43, 0);
  panel.rotation.z = -0.1;
  const marco = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.018, 0.36), materiales.soporte);
  const celdas = new THREE.Mesh(new THREE.PlaneGeometry(0.44, 0.34),
    new THREE.MeshStandardMaterial({ map: obtenerTexturaSolar(), metalness: 0.1, roughness: 0.35, emissive: 0x18448f, emissiveIntensity: 0.9 }));
  celdas.rotation.x = -Math.PI / 2;
  celdas.position.y = 0.0105;
  panel.add(marco, celdas);
  for (const z of [-0.13, 0.13]) {
    for (const x of [-0.2, 0.12]) {
      const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.1, 8), materiales.soporte);
      poste.position.set(x, -0.06, z);
      panel.add(poste);
    }
  }
  grupoRover.add(panel);

  // Mástil con cabeza de cámara que barre el horizonte (se mueve en el bucle)
  const mastilCamara = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.018, 0.38, 10), materiales.soporte);
  mastilCamara.position.set(0.2, 0.52, 0);
  grupoRover.add(mastilCamara);
  cabezaRover = new THREE.Group();
  cabezaRover.position.set(0.2, 0.72, 0);
  const carcasa = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 12), materiales.carroceria);
  carcasa.scale.set(1.2, 0.8, 1);
  const lente = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.022, 0.03, 14), materiales.lente);
  lente.rotation.z = -Math.PI / 2;
  lente.position.set(0.06, 0, 0);
  const anillo = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.005, 6, 16), materiales.acento);
  anillo.rotation.y = Math.PI / 2;
  anillo.position.set(0.075, 0, 0);
  cabezaRover.add(carcasa, lente, anillo);
  grupoRover.add(cabezaRover);

  // Antena parabólica en la parte trasera
  const varilla = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.18, 6), materiales.soporte);
  varilla.position.set(-0.27, 0.42, 0.13);
  const plato = new THREE.Mesh(new THREE.SphereGeometry(0.09, 18, 8, 0, Math.PI * 2, 0, 0.9), materiales.plato);
  plato.position.set(-0.27, 0.52, 0.13);
  plato.rotation.x = Math.PI - 0.35;
  grupoRover.add(varilla, plato);

  // Seis ruedas (tres por lado): cada una cuelga de un brazo y un amortiguador
  for (const x of [-0.24, 0, 0.24]) {
    for (const z of [-0.23, 0.23]) {
      const sentido = Math.sign(z);
      const eje = crearRueda();
      eje.position.set(x, 0.1, z);
      grupoRover.add(eje);
      ruedasGiro.push(eje);

      const brazoRueda = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, 0.1), materiales.soporte);
      brazoRueda.position.set(x, 0.12, z - sentido * 0.05);
      const amortiguador = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.08, 8), materiales.llanta);
      amortiguador.position.set(x, 0.16, sentido * 0.13);
      grupoRover.add(brazoRueda, amortiguador);
    }
  }

  // Anillo de resalte en el suelo bajo el rover: lo localiza de un vistazo en la vista general
  const resalte = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.5, 40),
    new THREE.MeshBasicMaterial({ color: 0x5fd3ff, transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }));
  resalte.rotation.x = -Math.PI / 2;
  resalte.position.y = 0.01;
  grupoRover.add(resalte);

  // Sombra suave de contacto bajo el rover (disco translúcido, no proyectado)
  const sombraRover = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 1.2),
    new THREE.MeshBasicMaterial({ map: texturaSombraRadial(), transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false }));
  sombraRover.rotation.x = -Math.PI / 2;
  sombraRover.position.y = 0.005;
  grupoRover.add(sombraRover);

  // Un poco más grande que la celda para que se lea en mapas grandes; el origen sigue en el suelo
  grupoRover.scale.setScalar(1.25);
  grupoRover.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
}

materiales.carbono = new THREE.MeshStandardMaterial({ map: obtenerTexturaCarbono(), roughness: 0.45, metalness: 0.2 });

// Sitúa el rover en su celda. Con `inmediato` no se anima el avance (al empezar partida).
function ubicarRover(posicion, rumbo, inmediato = false) {
  const [f, c] = posicion;
  const x = c + 0.5;
  const z = f + 0.5;
  let rot = grupoRover.rotation.y;
  if (rumbo && DELTA[rumbo]) {
    const [df, dc] = DELTA[rumbo];
    rot = Math.atan2(-df, dc);
  }
  roverDestino = { pos: new THREE.Vector3(x, alturaTerreno(x, z), z), rot };
  if (inmediato) {
    grupoRover.position.copy(roverDestino.pos);
    grupoRover.rotation.y = roverDestino.rot;
  }
}

// Dron enemigo: fuselaje con sensor, cuatro brazos con motor y rotor, patas y luz de estado
function crearDron(estadoDron) {
  const color = COLOR_DRON[estadoDron] || 0xffffff;
  const dron = new THREE.Group();
  const rotoresDron = [];
  const nucleo = new THREE.Mesh(new THREE.CapsuleGeometry(0.075, 0.16, 4, 12), materiales.dron);
  nucleo.rotation.z = Math.PI / 2;
  const sensor = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 8), materiales.lente);
  sensor.position.set(0.12, 0.02, 0);
  // Luz de estado: LED en la parte superior del fuselaje
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.02, 10, 8), new THREE.MeshBasicMaterial({ color, toneMapped: false }));
  led.position.set(-0.02, 0.09, 0);
  dron.add(nucleo, sensor, led);
  for (const ang of [Math.PI / 4, (3 * Math.PI) / 4, (5 * Math.PI) / 4, (7 * Math.PI) / 4]) {
    const cx = Math.cos(ang) * 0.23;
    const cz = -Math.sin(ang) * 0.23;
    const brazo = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.022, 0.03), materiales.dron);
    brazo.rotation.y = ang;
    brazo.position.y = 0.01;
    const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.036, 0.05, 12), materiales.soporte);
    motor.position.set(cx, 0.03, cz);
    // Rotor: pivote que gira, con dos aspas y un disco translúcido en el color del estado
    const rotor = new THREE.Group();
    rotor.position.set(cx, 0.07, cz);
    const disco = new THREE.Mesh(new THREE.CircleGeometry(0.16, 20),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.2, side: THREE.DoubleSide, depthWrite: false, toneMapped: false }));
    disco.rotation.x = -Math.PI / 2;
    const aspa1 = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.006, 0.02), materiales.soporte);
    const aspa2 = aspa1.clone();
    aspa2.rotation.y = Math.PI / 2;
    rotor.add(disco, aspa1, aspa2);
    dron.add(brazo, motor, rotor);
    rotoresDron.push(rotor);
  }
  // Patas de aterrizaje
  for (const z of [-0.07, 0.07]) {
    const pata = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.012, 0.012), materiales.dron);
    pata.position.set(0, -0.1, z);
    const soporte1 = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.07, 0.012), materiales.dron);
    soporte1.position.set(-0.07, -0.065, z);
    const soporte2 = soporte1.clone();
    soporte2.position.x = 0.07;
    dron.add(pata, soporte1, soporte2);
  }
  // Anillo de estado bajo el dron (visible a distancia)
  const anillo = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.02, 8, 28),
    new THREE.MeshBasicMaterial({ color, toneMapped: false }));
  anillo.rotation.x = Math.PI / 2;
  anillo.position.y = -0.13;
  dron.add(anillo);
  dron.userData.rotores = rotoresDron;
  return dron;
}

// Drones: cada uno conserva su grupo y se desliza hacia su nueva celda en lugar de saltar
const dronesPorId = new Map();   // id -> { grupo, estado }
function pintarDrones(npcs) {
  const vigentes = new Set();
  for (const n of npcs || []) {
    const [f, c] = n.pos;
    const x = c + 0.5;
    const z = f + 0.5;
    const base = alturaTerreno(x, z) + 0.6;
    vigentes.add(n.id);
    let previo = dronesPorId.get(n.id);
    if (!previo || previo.estado !== n.estado) {
      // Dron nuevo, o que cambió de estado: se recrea en su posición actual
      const origen = previo ? previo.grupo.position.clone() : new THREE.Vector3(x, base, z);
      if (previo) grupoDrones.remove(previo.grupo);
      const grupo = crearDron(n.estado);
      grupo.position.copy(origen);
      grupo.userData.fase = azar(f, c, 99) * 6;
      grupoDrones.add(grupo);
      previo = { grupo, estado: n.estado };
      dronesPorId.set(n.id, previo);
    }
    previo.grupo.userData.destino = { x, z, base };
  }
  for (const [id, d] of dronesPorId) {
    if (!vigentes.has(id)) {
      grupoDrones.remove(d.grupo);
      dronesPorId.delete(id);
    }
  }
}

// Disparo: un haz luminoso desde el rover en el rumbo indicado (se borra a los 350 ms)
// Posición en escena del dron más cercano en la dirección del disparo (O9); null si no hay ninguno en línea
function puntoDronEnLinea(rumbo) {
  if (!estado || !DELTA[rumbo]) return null;
  const [df, dc] = DELTA[rumbo];
  let mejor = null;
  for (const n of estado.npcs || []) {
    const fa = n.pos[0] - estado.posicion[0];
    const ca = n.pos[1] - estado.posicion[1];
    const enDireccion = Math.sign(fa) === df && Math.sign(ca) === dc && (fa === 0 || ca === 0 || Math.abs(fa) === Math.abs(ca));
    const distancia = Math.max(Math.abs(fa), Math.abs(ca));
    if (enDireccion && distancia <= 5 && (!mejor || distancia < mejor.distancia)) mejor = { id: n.id, distancia };
  }
  const previo = mejor && dronesPorId.get(mejor.id);
  return previo ? previo.grupo.position.clone() : null;
}
// Posición en escena del dron con ese id (O9), o null
function puntoDronPorId(id) {
  const dron = dronesPorId.get(id);
  return dron ? dron.grupo.position.clone() : null;
}
// Posición en escena del dron que está en una celda (estado previo al paso), o null
function puntoDronEnCelda(celda, previo) {
  const npc = (previo && previo.npcs || []).find((n) => n.pos[0] === celda[0] && n.pos[1] === celda[1]);
  const dron = npc && dronesPorId.get(npc.id);
  return dron ? dron.grupo.position.clone() : null;
}
// Haz del cañón al destino (el dron); sin destino, un tramo horizontal de alcance fijo
function efectoDisparo(rumbo, impacto, destino = null) {
  if (!estado || !DELTA[rumbo]) return;
  const [df, dc] = DELTA[rumbo];
  const alcance = 5;
  const origen = grupoRover.position.clone().add(new THREE.Vector3(0, 0.3, 0));
  const tramo = destino
    ? destino.clone().sub(origen)
    : new THREE.Vector3(dc * alcance, 0, df * alcance);
  const largo = tramo.length();
  if (largo < 0.05) return;
  const dir = tramo.clone().normalize();
  const haz = new THREE.Mesh(
    new THREE.CylinderGeometry(0.03, 0.03, largo, 8),
    new THREE.MeshBasicMaterial({ color: impacto ? 0xffffff : 0xffb070, toneMapped: false, transparent: true, opacity: 0.9 }),
  );
  haz.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  haz.position.copy(origen).addScaledVector(dir, largo / 2);
  grupoEfectos.add(haz);
  setTimeout(() => grupoEfectos.remove(haz), 350);
}

// Ruta planificada por el AG: línea punteada en ámbar sobre el suelo
const geomTramo = new THREE.CylinderGeometry(0.035, 0.035, 1, 8);
function puntoRuta(f, c) {
  return new THREE.Vector3(c + 0.5, alturaTerreno(c + 0.5, f + 0.5) + 0.09, f + 0.5);
}
function dibujarRuta(ruta) {
  grupoRuta.clear();
  if (!ruta || ruta.length < 2) return;
  const puntos = ruta.map(([f, c]) => puntoRuta(f, c));
  const raya = 0.16;   // largo de cada raya; el hueco es igual
  for (let i = 1; i < puntos.length; i++) {
    const a = puntos[i - 1];
    const b = puntos[i];
    const dir = new THREE.Vector3().subVectors(b, a);
    const largo = dir.length();
    dir.normalize();
    for (let t = 0; t < largo; t += 2 * raya) {
      const len = Math.min(raya, largo - t);
      if (len < 0.02) break;
      const m = new THREE.Mesh(geomTramo, materialRutaPlan);
      m.scale.set(1, len, 1);
      m.position.copy(a).addScaledVector(dir, t + len / 2);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      grupoRuta.add(m);
    }
  }
}

// Recorrido real del rover en esta partida: celdas visitadas, sin repetir la última
function registrarRecorrido(posicion) {
  const ultima = recorridoRover[recorridoRover.length - 1];
  if (!ultima || ultima[0] !== posicion[0] || ultima[1] !== posicion[1]) recorridoRover.push([posicion[0], posicion[1]]);
  dibujarRecorrido();
}

function dibujarRecorrido() {
  grupoRecorrido.clear();
  if (recorridoRover.length < 2) return;
  const puntos = recorridoRover.map(([f, c]) => puntoRuta(f, c));
  const camino = new THREE.CurvePath();
  for (let i = 1; i < puntos.length; i++) camino.add(new THREE.LineCurve3(puntos[i - 1], puntos[i]));
  grupoRecorrido.add(new THREE.Mesh(new THREE.TubeGeometry(camino, puntos.length * 8, 0.04, 8, false), materialRutaReal));
}

// ---------- HUD y paneles ----------
// En pantallas estrechas la decisión arranca plegada, para que el HUD y los controles quepan
if (matchMedia("(max-width: 760px)").matches) {
  document.getElementById("decision").classList.add("plegado");
  document.querySelector("#decision-toggle span").textContent = "▸";
}

// Estados del rover (ARX-36): etiqueta, icono y color. El motor manda el código en /estado.estado
const ESTADOS_VISUAL = {
  CONFIGURACION: { etiqueta: "CONFIGURACIÓN", icono: "⚙", color: "#c8d2e4", pulso: false },
  EXPLORACION: { etiqueta: "EXPLORACIÓN", icono: "◎", color: "#5fd3ff", pulso: false },
  ALERTA: { etiqueta: "ALERTA", icono: "▲", color: "#ffb454", pulso: true },
  REPLANIFICACION: { etiqueta: "REPLANIFICACIÓN", icono: "↻", color: "#c39bff", pulso: true },
  REFUGIO: { etiqueta: "REFUGIO", icono: "⌂", color: "#7aa8ff", pulso: false },
  MODO_SEGURO: { etiqueta: "MODO SEGURO", icono: "■", color: "#ff5d6c", pulso: true },
  EXITO: { etiqueta: "ÉXITO", icono: "✓", color: "#6ee7a8", pulso: false },
  FRACASO: { etiqueta: "FRACASO", icono: "✕", color: "#ff5d6c", pulso: false },
  SIN_RUTA: { etiqueta: "SIN RUTA", icono: "⊘", color: "#ffb454", pulso: true },
};
// Datos de prueba para los estados que el motor aún no emite (solo con ?demo=estados en la URL)
const ESTADOS_DEMO = ["CONFIGURACION", "EXPLORACION", "ALERTA", "REPLANIFICACION", "REFUGIO", "MODO_SEGURO", "SIN_RUTA", "EXITO", "FRACASO"];
const modoDemoEstados = new URLSearchParams(location.search).get("demo") === "estados";

function pintarEstadoBadge(codigo) {
  const badge = document.getElementById("estado-badge");
  const conocido = ESTADOS_VISUAL[codigo] || { etiqueta: String(codigo || "-"), icono: "•", color: "#c8d2e4", pulso: false };
  badge.style.setProperty("--color-estado", conocido.color);
  badge.classList.toggle("pulso", conocido.pulso);
  badge.querySelector(".icono").textContent = conocido.icono;
  badge.querySelector(".texto").textContent = conocido.etiqueta;
}

// Con ?demo=estados, el indicador recorre todos los estados cada 2 s (prueba visual)
if (modoDemoEstados) {
  let k = 0;
  setInterval(() => { pintarEstadoBadge(ESTADOS_DEMO[k]); k = (k + 1) % ESTADOS_DEMO.length; }, 2000);
}

// Descripción corta de cada modo (ARX-54)
const MODO_DESC = {
  manual: "Tú conduces; los modelos te recomiendan el siguiente paso.",
  rna: "Solo RNA: la red mira la celda de enfrente y elige la más libre.",
  difuso: "Solo difuso: regula la velocidad según distancia, batería e inclinación.",
  ag: "Solo AG: el algoritmo genético planifica la ruta hasta el objetivo.",
  automatico: "Híbrido: RNA, difuso, AG y supervisor trabajan juntos y conducen solos.",
};
function pintarModoDesc(modo) {
  document.getElementById("modo-desc").textContent = MODO_DESC[modo] || "";
  document.getElementById("menu-modo-desc").textContent = MODO_DESC[document.getElementById("menu-modo").value] || "";
  document.getElementById("det-rec").classList.toggle("oculto", modo !== "manual");   // recomendaciones solo en manual
}
document.getElementById("menu-modo").addEventListener("change", (ev) => {
  document.getElementById("menu-modo-desc").textContent = MODO_DESC[ev.target.value] || "";
});

// Recomendaciones (ARX-54, contrato §12): lo que haría cada modelo, sin mover el rover
const NOMBRE_MODELO = { hibrido: "híbrido", rna: "RNA", difuso: "difuso", ag: "AG" };
async function consultarRecomendacion() {
  const lista = document.getElementById("rec-lista");
  lista.replaceChildren();
  const datos = await deps_recomendacion();
  if (!datos || !datos.propuestas) {
    lista.appendChild(Object.assign(document.createElement("li"), { textContent: "Sin recomendación (revisa que haya partida y modo manual)." }));
    return;
  }
  for (const p of datos.propuestas) {
    const li = document.createElement("li");
    const rumbo = p.rumbo ? ` · rumbo ${p.rumbo}` : " · no mueve el rover";
    li.textContent = `${NOMBRE_MODELO[p.modelo] || p.modelo}: ${p.accion}${rumbo}. ${p.razon}`;
    lista.appendChild(li);
  }
}
function deps_recomendacion() {
  return llamar("GET", "/recomendacion");
}
document.getElementById("rec-consultar").addEventListener("click", consultarRecomendacion);

function pintarHud(e) {
  pintarModoDesc(e.modo);
  const modoSel = document.getElementById("modo");
  const nombreModo = modoSel.options[modoSel.selectedIndex] ? modoSel.options[modoSel.selectedIndex].text : e.modo;
  document.getElementById("resumen-texto").textContent = `semilla ${e.semilla} · nivel ${NIVELES[(e.nivel || 1) - 1]} · ${nombreModo}`;
  if (!modoDemoEstados) pintarEstadoBadge(e.estado);
  // Título con el planeta: /estado.planeta, luego /planetas.activo.planeta, y por último el valor local
  const planetaVisible = e.planeta || (planetasDatos && planetasDatos.activo && planetasDatos.activo.planeta);
  if (planetaVisible) {
    planetaActivo = planetaVisible;
    const modoVisible = e.modo_planeta === "sonda" ? " · sonda" : (e.modo_planeta === "rover" ? " · rover" : "");
    document.querySelector("#hud h1").textContent = `ARES-X · ${planetaVisible}${modoVisible}`;
  }
  // ARX-85 (ev3-d61 A): en modo sonda, pantalla de sonda con sus lecturas y sin controles de rodaje
  const enSonda = e.modo_planeta === "sonda";
  const panelSonda = document.getElementById("sonda-panel");
  const controlesManuales = document.getElementById("manual");
  if (panelSonda) panelSonda.classList.toggle("oculto", !enSonda);
  if (controlesManuales) controlesManuales.style.display = enSonda ? "none" : "";
  if (enSonda) {
    document.getElementById("sonda-planeta").textContent = planetaActivo;
    document.getElementById("sonda-temp").textContent = `${e.temperatura_interna} °C (tolerancia ${e.tolerancia} °C)`;
    document.getElementById("sonda-bateria").textContent = `${e.bateria.toFixed(1)} %`;
    document.getElementById("sonda-sobre").textContent = e.pasos_sobre_tolerancia ?? "-";
    document.getElementById("sonda-estado").textContent = e.estado;
  }
  document.getElementById("h-semilla").textContent = e.semilla;
  document.getElementById("h-estado").textContent = e.estado;
  document.getElementById("h-bateria").textContent = `${e.bateria.toFixed(1)} %`;
  document.getElementById("h-bateria-barra").style.width = `${Math.max(0, Math.min(100, e.bateria))}%`;
  document.getElementById("h-puntaje").textContent = e.puntaje;
  document.getElementById("h-municion").textContent = e.municion;
  document.getElementById("h-modo").textContent = e.modo;
  document.getElementById("h-paso").textContent = e.paso ?? "-";
  document.getElementById("h-cooldown").textContent = e.cooldown ?? "-";
  const vivos = (e.npcs || []).map((n) => n.estado);
  document.getElementById("h-drones").textContent = vivos.length ? vivos.join(", ") : "ninguno";
  document.getElementById("modo").value = e.modo;
  document.getElementById("veto").checked = e.veto !== false;

  const aviso = document.getElementById("intervencion-aviso");
  if (e.intervencion) {
    const v = e.intervencion.tecnica === "rna" ? `RNA a ${e.intervencion.valor}` : `difuso a ${e.intervencion.valor}`;
    aviso.textContent = `INTERVENCIÓN ACTIVA: ${v}`;
    aviso.style.display = "block";
  } else {
    aviso.style.display = "none";
  }
}

function pct(x) {
  return x === null || x === undefined ? "-" : `${(x * 100).toFixed(1).replace(".", ",")} %`;
}

function barra(id, valor) {
  document.getElementById(id).style.width = valor === null || valor === undefined ? "0%" : `${(valor * 100).toFixed(1)}%`;
}

// Las cuatro líneas del porqué de un paso (RNA, difuso, planificador, supervisor), solo con los datos de /paneles
function decisionesDelPaso(p) {
  const lineas = [];
  const r = p.rna || {};
  const probs = [["libre", r.p_libre], ["obstáculo", r.p_obstaculo], ["barranco", r.p_barranco]].filter(([, v]) => v != null);
  if (probs.length) {
    const [clase, valor] = probs.reduce((x, y) => (y[1] > x[1] ? y : x));
    lineas.push(`RNA: predijo ${clase} (${pct(valor)})`);
  } else lineas.push("RNA: sin dato");
  const d = p.difuso || {};
  if (d.usado === false) lineas.push("Difuso: no usado");
  else if (d.velocidad == null && !(d.reglas && d.reglas.length)) lineas.push("Difuso: sin dato");
  else {
    const reglas = (d.reglas || []).map(x => (Array.isArray(x)
      ? `${x[0]} (fuerza ${Number(x[1]).toFixed(2).replace(".", ",")})`
      : String(x))).join(", ") || "sin regla";
    const vel = d.velocidad == null ? "sin dato" : Number(d.velocidad).toFixed(3).replace(".", ",");
    lineas.push(`Difuso: reglas ${reglas}, velocidad ${vel}`);
  }
  const ruta = (p.ag || {}).ruta_planeada || [];
  lineas.push(ruta.length ? `Planificador: ruta de ${ruta.length} celdas` : "Planificador: sin ruta");
  const supv = p.supervisor || {};
  const vetos = (supv.motivos || []).filter(m => String(m).startsWith("V-"));
  lineas.push(`Supervisor: ${supv.accion || "sin dato"}${vetos.length ? ` · veto ${vetos.join(", ")}` : ""}`);
  return lineas;
}

// ARX-36a: tira de decisiones, una fila por paso del automático (la más nueva arriba), con las mismas cuatro líneas
const TIRA_MAX = 12;
let tiraPasos = [];
function registrarTira(p) {
  const ultimo = tiraPasos.length ? tiraPasos[0].paso : null;
  if (p.paso == null || (ultimo != null && p.paso < ultimo)) tiraPasos = [];   // otra misión: se vacía
  if (p.paso != null && (!tiraPasos.length || tiraPasos[0].paso !== p.paso)) {
    tiraPasos.unshift({ paso: p.paso, lineas: decisionesDelPaso(p) });
    tiraPasos.length = Math.min(tiraPasos.length, TIRA_MAX);
  }
  pintarTira();
}
function pintarTira() {
  const caja = document.getElementById("tira-caja");
  if (!caja) return;
  const visible = document.getElementById("modo").value === "automatico" && Boolean(estado);
  caja.classList.toggle("oculto", !visible);
  if (!visible) return;
  const cuerpo = document.getElementById("tira-filas");
  if (!tiraPasos.length) {
    const vacio = document.createElement("div");
    vacio.className = "ayuda";
    vacio.textContent = "sin pasos todavía";
    cuerpo.replaceChildren(vacio);
    return;
  }
  cuerpo.replaceChildren(...tiraPasos.map((f) => {
    const fila = document.createElement("div");
    fila.className = "tira-fila";
    const n = document.createElement("span");
    n.className = "tira-paso";
    n.textContent = `paso ${f.paso}`;
    fila.appendChild(n);
    for (const t of f.lineas) {
      const c = document.createElement("span");
      c.textContent = t;
      fila.appendChild(c);
    }
    return fila;
  }));
}

function pintarPaneles(p) {
  const rna = p.rna || {};
  document.getElementById("rna-libre").textContent = pct(rna.p_libre);
  document.getElementById("rna-obstaculo").textContent = pct(rna.p_obstaculo);
  document.getElementById("rna-barranco").textContent = pct(rna.p_barranco);
  barra("barra-libre", rna.p_libre);
  barra("barra-obstaculo", rna.p_obstaculo);
  barra("barra-barranco", rna.p_barranco);

  const dif = p.difuso || {};
  document.getElementById("dif-velocidad").textContent =
    dif.velocidad === null || dif.velocidad === undefined ? "-" : Number(dif.velocidad).toFixed(3);
  const lista = document.getElementById("dif-reglas");
  lista.innerHTML = "";
  const reglas = dif.reglas || [];
  if (dif.usado === false) {
    document.getElementById("dif-velocidad").textContent = "no usado en este modo";
    lista.innerHTML = "<li>el difuso no mueve el rover en este modo</li>";
  } else if (reglas.length === 0) {
    lista.innerHTML = "<li>sin reglas activadas</li>";
  } else {
    for (const r of reglas) {
      const li = document.createElement("li");
      li.textContent = typeof r === "string" ? r : `${r[0]} (${Number(r[1]).toFixed(2)}): ${r[2]}`;
      lista.appendChild(li);
    }
  }

  const ag = p.ag || {};
  const n = (ag.ruta_planeada || []).length;
  document.getElementById("ag-ruta").textContent = n ? `${n} celdas hasta el objetivo` : "sin ruta";
  document.getElementById("res-ag").textContent = n ? `${n} celdas` : "sin ruta";

  document.getElementById("h-paso").textContent = p.paso ?? "-";
  const sup = p.supervisor || {};
  document.getElementById("sup-accion").textContent = sup.accion || "-";
  document.getElementById("res-rna").textContent = `libre ${pct(rna.p_libre)}`;
  document.getElementById("res-dif").textContent = dif.usado === false ? "no usado" : `velocidad ${dif.velocidad == null ? "-" : Number(dif.velocidad).toFixed(3).replace(".", ",")}`;
  document.getElementById("res-sup").textContent = sup.accion || "-";
  const motivos = document.getElementById("sup-motivos");
  motivos.innerHTML = "";
  for (const m of (sup.motivos || ["-"])) {
    const li = document.createElement("li");
    li.textContent = m;
    motivos.appendChild(li);
  }
  // ARX-88: el porqué del paso con datos reales (M17): RNA, difuso, planificador y supervisor
  const porque = document.getElementById("sup-porque");
  if (porque) {
    porque.replaceChildren(...decisionesDelPaso(p).map(t => { const li = document.createElement("li"); li.textContent = t; return li; }));
  }
  registrarTira(p);
  // ARX-86: lecturas de los sensores en el rumbo actual y riesgo estimado de la celda de enfrente
  const sen = p.sensores;
  const indicador = document.getElementById("sup-sensores");
  // QA ARX-86: sin «null» en pantalla; durante una falla se muestra «falla» en lugar de las lecturas
  const dato = (x) => (x == null ? "—" : x);
  if (indicador) indicador.textContent = !sen ? "-"
    : sen.falla ? `${sen.rumbo}: falla de sensor · riesgo enfrente ${dato(sen.riesgo_enfrente)}`
    : `${sen.rumbo}: proximidad ${dato(sen.proximidad)} · borde ${dato(sen.borde)} · gradiente ${dato(sen.gradiente)} · vibración ${dato(sen.vibracion)} · riesgo enfrente ${dato(sen.riesgo_enfrente)}`;
}

async function refrescarPaneles() {
  const p = await llamar("GET", "/paneles");
  dibujarSeguro("paneles", () => {
    if (p) pintarPaneles(p);
  });
  await refrescarHistorial();
  // Los gráficos solo se piden si el panel está abierto
  if (!document.getElementById("graficos").classList.contains("plegado")) await refrescarGraficos();
  marcarDesbordes();
  await refrescarMovilesYEscenario();
}

// Móviles, eventos y automático continuo (adaptador: motor o datos de prueba)
// Objetivos de misión (ARX-67): bloque en el HUD y resumen en la meta
let ultimosObjetivos = null;
// Medidor de calor interno (ARX-51, ARX-83c): solo para el rover; lee la temperatura interna real de /estado
let calorSobreTolerancia = false;
function pintarCalor(datos) {
  const fila = document.getElementById("fila-calor");
  const caja = document.getElementById("barra-calor-caja");
  const visible = modoPlanetaActivo === "rover" && Boolean(datos) && typeof datos.temperatura_interna === "number";
  fila.classList.toggle("oculto", !visible);
  caja.classList.toggle("oculto", !visible);
  if (!visible) return;
  const t = Math.round(datos.temperatura_interna * 10) / 10;
  document.getElementById("h-calor").textContent = `${t} °C`;
  const barra = document.getElementById("h-calor-barra");
  barra.style.width = `${Math.min(100, (t / (datos.tolerancia * 1.3)) * 100)}%`;
  barra.style.background = t >= datos.tolerancia ? "#ff5d6c" : t >= datos.tolerancia * 0.66 ? "#ffb454" : "#6ee7a8";
  const sobre = t > datos.tolerancia;
  const nota = datos.aborto_termico_activo === false ? " (aborto térmico desactivado)" : "";
  // registro lateral y no avisar(): el aviso del paso lo taparía en el mismo ciclo (C1 de QA)
  if (sobre && !calorSobreTolerancia) registrarEvento(`aviso: Calor interno sobre la tolerancia (${datos.tolerancia} °C)${nota}`);
  calorSobreTolerancia = sobre;
}

function pintarObjetivos(o) {
  ultimosObjetivos = o;
  const caja = document.getElementById("objetivos");
  caja.replaceChildren();
  caja.classList.toggle("oculto", !o || !o.condiciones);
  if (!o || !o.condiciones) return;
  const mision = document.createElement("div");
  mision.className = "mision";
  mision.textContent = o.mision;
  caja.appendChild(mision);
  for (const c of o.condiciones) {
    const fila = document.createElement("div");
    // obligatorio = false: condición opcional (ARX-75). Si el motor no envía el campo, es obligatoria
    const opcional = c.obligatorio === false;
    fila.className = "cond" + (c.cumplido ? " cumplido" : "") + (opcional ? " opcional" : "");
    fila.innerHTML = "";
    const nombre = document.createElement("span");
    nombre.textContent = opcional ? `${c.nombre} (opcional)` : c.nombre;
    const cuenta = document.createElement("span");
    cuenta.textContent = `${c.progreso}/${c.total}`;
    fila.append(nombre, cuenta);
    const barra = document.createElement("div");
    barra.className = "barra-obj";
    const relleno = document.createElement("div");
    relleno.style.width = `${Math.min(100, (c.progreso / Math.max(1, c.total)) * 100)}%`;
    barra.appendChild(relleno);
    caja.append(fila, barra);
  }
  // ARX-30c: /objetivos no trae la señal; /estado.senal = [f,c] solo mientras está activa y sin visitar
  if (estado && Array.isArray(estado.senal)) {
    const fila = document.createElement("div");
    fila.className = "cond";
    const nombre = document.createElement("span");
    nombre.textContent = "Señal biológica";
    const cuenta = document.createElement("span");
    cuenta.textContent = "0/1";
    fila.append(nombre, cuenta);
    caja.appendChild(fila);
  }
}

async function refrescarMovilesYEscenario() {
  if (!estado || estado.sin_partida) return;
  pintarObjetivos(await adaptador.objetivos());
  pintarCalor(estado);
  const datos = await adaptador.moviles();
  aplicarMoviles(datos, scene, alturaTerreno, (texto) => avisar(texto), agregarGrietas);
  aplicarEnlaceYSenal(estado);
  await refrescarEscenarios();
}

async function refrescarEscenarios() {
  const caja = document.getElementById("escenarios-caja");
  const visible = document.getElementById("modo").value === "automatico" && Boolean(cadenaAutomatica) && Boolean(estado);
  caja.classList.toggle("oculto", !visible);
  if (!visible) return;
  const c = cadenaAutomatica;
  document.getElementById("esc-texto").textContent =
    (c.hechas >= c.total
      ? `cadena terminada · ${c.total} de ${c.total} · semilla ${estado.semilla} · nivel ${NIVELES[c.nivel - 1]}`
      : `misión ${c.hechas + 1} de ${c.total} · semilla ${estado.semilla} · nivel ${NIVELES[c.nivel - 1]}`);
  const coma = (x, d) => (x == null ? "—" : x.toFixed(d).replace(".", ","));
  const replanteos = c.replanteos.reduce((x, y) => x + y, 0);
  const metricas = [
    ["éxitos", String(c.exitos), "en esta sesión"],
    ["fracasos", String(c.fracasos), "en esta sesión"],
    ["pasos (mediana)", coma(mediana(c.pasos), 1), ""],
    ["batería final (mediana)", coma(mediana(c.bateriaFinal), 1) + (mediana(c.bateriaFinal) == null ? "" : " %"), ""],
    ["replanteos (total)", String(replanteos), c.replanteos.length ? `por misión: ${c.replanteos.join(" · ")}` : ""],
  ];
  const cont = document.getElementById("esc-metricas");
  cont.replaceChildren();
  for (const [nombre, valor, detalle] of metricas) {
    const m = document.createElement("div");
    m.className = "lab-metrica";
    const v = document.createElement("div");
    v.className = "lab-metrica-valor";
    v.textContent = valor;
    const n = document.createElement("div");
    n.className = "ayuda";
    n.textContent = detalle ? `${nombre} · ${detalle}` : nombre;
    m.append(v, n);
    cont.appendChild(m);
  }
}

// Planetas en el asistente: todos elegibles; el bloqueo es la combinación gigante + rover (CA-07)
let planetasDatos = null;
async function poblarPlanetas() {
  const datos = await adaptador.planetas();
  planetasDatos = datos;
  const sel = document.getElementById("menu-planeta");
  const aviso = document.getElementById("menu-planeta-aviso");
  for (const p of datos.planetas) {
    const opt = document.createElement("option");
    opt.value = p.nombre;
    opt.textContent = p.nombre;
    sel.appendChild(opt);
  }
  // El motor puede devolver activo: null; en ese caso, Marte en rover por defecto
  const activo = datos.activo || { planeta: "Marte", modo: "rover" };
  sel.value = activo.planeta;
  document.getElementById("menu-modo-planeta").value = activo.modo;
  validarPlaneta();
}
function planetaElegido() {
  return planetasDatos && planetasDatos.planetas.find((p) => p.nombre === document.getElementById("menu-planeta").value);
}
// Bloquea solo la combinación gigante + rover, con su motivo y el botón «usar sonda»
function validarPlaneta() {
  const p = planetaElegido();
  const modo = document.getElementById("menu-modo-planeta").value;
  // Cada planeta admite solo su tipo de vehículo: rover en los rocosos, sonda en los gigantes (CA-07)
  const bloqueado = Boolean(p) && modo !== p.modo;
  const aviso = document.getElementById("menu-planeta-aviso");
  aviso.classList.toggle("oculto", !bloqueado);
  document.getElementById("menu-planeta-motivo").textContent = bloqueado
    ? `${p.nombre} no admite ${modo}: ${p.motivo || `solo admite ${p.modo}`}.`
    : "";
  const boton = document.getElementById("menu-usar-sonda");
  boton.textContent = p && p.modo === "sonda" ? "Usar sonda" : "Usar rover";
  boton.dataset.modo = p ? p.modo : "rover";
  document.getElementById("iniciar").disabled = bloqueado;
}
document.getElementById("menu-planeta").addEventListener("change", () => {
  const p = planetaElegido();
  if (p) document.getElementById("menu-modo-planeta").value = p.modo;   // cada planeta admite solo su vehículo
  validarPlaneta();
});
document.getElementById("menu-modo-planeta").addEventListener("change", validarPlaneta);
document.getElementById("menu-usar-sonda").addEventListener("click", (ev) => {
  document.getElementById("menu-modo-planeta").value = ev.currentTarget.dataset.modo || "rover";
  validarPlaneta();
});
poblarPlanetas();

// Historial de decisiones (Panel D, ARX-15): una fila por acción, filtrable y exportable.
function consultaHistorial() {
  const q = new URLSearchParams();
  const modo = document.getElementById("hist-modo").value;
  const tecnica = document.getElementById("hist-tecnica").value;
  const motivo = document.getElementById("hist-motivo").value.trim();
  if (modo) q.set("modo", modo);
  if (tecnica) q.set("tecnica", tecnica);
  if (motivo) q.set("motivo", motivo);
  return q.toString();
}

function valoresClave(f) {
  const partes = [];
  if (f.p_libre != null) partes.push(`libre ${(f.p_libre * 100).toFixed(1).replace(".", ",")} %`);
  if (f.p_barranco != null) partes.push(`barranco ${(f.p_barranco * 100).toFixed(1).replace(".", ",")} %`);
  if (f.velocidad != null) partes.push(`v ${Number(f.velocidad).toFixed(3).replace(".", ",")}`);
  if (f.fitness != null) partes.push(`fitness ${Number(f.fitness).toFixed(2).replace(".", ",")}`);
  if (f.ruta_largo) partes.push(`ruta ${f.ruta_largo}`);
  if (f.evento) partes.push(`evento ${f.evento}`);
  if (f.intervencion) partes.push(`intervención ${f.intervencion}`);
  return partes.join(" · ");
}

async function refrescarHistorial() {
  if (!estado || estado.sin_partida) return;
  const q = consultaHistorial();
  const datos = await llamar("GET", "/historial" + (q ? "?" + q : ""));
  if (!datos) return;
  document.getElementById("hist-csv").href = "/historial.csv" + (q ? "?" + q : "");
  document.getElementById("hist-total").textContent = `${datos.total} filas`;
  const cuerpo = document.getElementById("hist-cuerpo");
  cuerpo.replaceChildren();
  for (const f of datos.filas.slice(-200)) {
    const tr = document.createElement("tr");
    for (const texto of [f.n, f.modo, f.accion, f.tecnica, f.motivo || "-", valoresClave(f)]) {
      const td = document.createElement("td");
      td.textContent = String(texto);
      tr.appendChild(td);
    }
    cuerpo.appendChild(tr);
  }
}

async function refrescarEstado() {
  const datos = await llamar("GET", "/estado");
  if (!datos) return;
  estado = datos;
  dibujarSeguro("estado", () => {
    registrarRecorrido(datos.posicion);
    ubicarRover(datos.posicion, datos.rumbo_sugerido);
    dibujarRuta(datos.ruta);
    pintarDrones(datos.npcs);
    pintarHud(datos);
    actualizarControlEvento();
    aplicarEnlaceYSenal(datos);
  });
  refrescarCapaRiesgoPorPaso();   // M15: apagada no pide nada
  refrescarHolo();                // Paquete A: apagado no pide nada
}

// ARX-30d: lectura defensiva de /estado. Solo apaga si el campo existe y lo dice; sin campo (motor sin ARX-30b/30c) no hace nada.
function aplicarEnlaceYSenal(datos) {
  if (!datos || typeof datos !== "object") return;
  if (datos.enlace && datos.enlace.activo === false) efectos.activarInterferencia(false);
  // ARX-30c: tras recargar en mitad de un corte, el enlace caído enciende la interferencia sin esperar al evento de /moviles
  if (datos.enlace && datos.enlace.activo === true) efectos.activarInterferencia(true);
  if ("senal" in datos && datos.senal === null) efectos.quitarSenalBiologica(scene);
  if ("senal" in datos && ultimosObjetivos) pintarObjetivos(ultimosObjetivos);   // la línea de señal sigue a /estado
}

// Control de eventos (ARX-30e): mismo orden que EVENTOS de la API; solo con partida en curso
function actualizarControlEvento() {
  const boton = document.getElementById("evento-disparar");
  if (!boton) return;
  boton.disabled = !mapa || !estado || estado.sin_partida || ESTADOS_TERMINALES.includes(estado.estado);
}
async function dispararEvento() {
  if (!mapa || ocupado() || !estado || estado.sin_partida || ESTADOS_TERMINALES.includes(estado.estado)) return;
  const nombre = document.getElementById("evento-nombre").value;
  const r = await llamar("POST", "/evento", { nombre });
  if (!r) return;
  const detalle = r.detalle || (r.ok ? "hecho" : "sin efecto");
  avisar(`Evento ${nombre}: ${detalle}`);
  registrarEvento(`evento ${nombre}: ${detalle}`);
  await refrescarEstado();
  await refrescarPaneles();
}
document.getElementById("evento-disparar").addEventListener("click", dispararEvento);

// Encuadre inicial (sprint 4): la cámara mira al rover desde detrás y arriba, con el horizonte visible
function encuadrarInicio() {
  const p = grupoRover.position;
  controles.target.set(p.x, p.y + 0.25, p.z);
  camara.position.set(p.x - 4.5, p.y + 3.2, p.z + 5.5);
  camara.lookAt(controles.target);
}

// Aspecto por planeta (sprint 3): color del suelo, cielo, niebla y luz del sol
const ES_GIGANTE = (p) => ["Júpiter", "Saturno", "Urano", "Neptuno"].includes(p);
const PALETAS_PLANETA = {
  Marte: { suelo: 0xffffff, arriba: [0.09, 0.14, 0.27], horizonte: [0.85, 0.58, 0.42], niebla: 0xd9946a, sol: 0xffe0bd, roca: 0x8a5e4a, borde: 0x8c3f24, guijarro: 0x8e5e44 },
  Mercurio: { suelo: 0xb4b4b8, arriba: [0.02, 0.02, 0.04], horizonte: [0.22, 0.22, 0.25], niebla: 0x3a3a40, sol: 0xfff4e6, roca: 0x6e6e72, borde: 0x5a5a5e, guijarro: 0x7c7c80 },
  Venus: { suelo: 0xffffff, arriba: [0.35, 0.22, 0.08], horizonte: [0.95, 0.75, 0.4], niebla: 0xd9a24a, sol: 0xffe9b0, roca: 0x4a3424, borde: 0x6b2a12, guijarro: 0x5a4030 },
  Tierra: { suelo: 0xffffff, arriba: [0.25, 0.45, 0.75], horizonte: [0.7, 0.8, 0.9], niebla: 0xaac8e0, sol: 0xfff2dc, roca: 0x6b6b5a, borde: 0x5a4a3a, guijarro: 0x7a7a68 },
  Saturno: { suelo: 0xe9d8a6, arriba: [0.4, 0.34, 0.2], horizonte: [0.95, 0.88, 0.65], niebla: 0xead9aa, sol: 0xfff0c8, roca: 0xd8c890, borde: 0xd8c890, guijarro: 0xe6dab0 },
  Urano: { suelo: 0x9fdde0, arriba: [0.12, 0.3, 0.34], horizonte: [0.55, 0.85, 0.88], niebla: 0x8fd0d4, sol: 0xdff7ff, roca: 0xb8e4e6, borde: 0xb8e4e6, guijarro: 0xcdeef0 },
  Neptuno: { suelo: 0x3f6fd6, arriba: [0.04, 0.08, 0.25], horizonte: [0.2, 0.35, 0.75], niebla: 0x2d4fa6, sol: 0xbcd4ff, roca: 0x6f8fd0, borde: 0x6f8fd0, guijarro: 0x8aa6e0 },
  "Júpiter": { suelo: 0xe6cba2, arriba: [0.34, 0.24, 0.12], horizonte: [0.9, 0.74, 0.5], niebla: 0xe6c896, sol: 0xffe6c0, roca: 0xe6d6b8, borde: 0xe6d6b8, guijarro: 0xf2e6cc },
};
function aplicarAspecto(planeta) {
  const p = PALETAS_PLANETA[planeta] || PALETAS_PLANETA.Marte;
  document.querySelector("#hud h1").textContent = `ARES-X · ${planeta}`;
  if (grupoMapa.children[0] && grupoMapa.children[0].material) grupoMapa.children[0].material.color.setHex(p.suelo);
  materiales.roca.color.setHex(p.roca);      // rocas del planeta: Marte café rojizo, Mercurio gris
  materiales.borde.color.setHex(p.borde);
  materiales.guijarro.color.setHex(p.guijarro);
  materialCielo.uniforms.arriba.value.set(...p.arriba);
  materialCielo.uniforms.horizonte.value.set(...p.horizonte);
  scene.fog.color.setHex(p.niebla);
  sol.color.setHex(p.sol);
}

// Lo último que confirmó el motor: planeta y tipo de vehículo
let vigente = { planeta: null, vehiculo: null };
// Configuración para crear o reiniciar una partida: el planeta y vehículo confirmados, y el modo de control del panel
function configuracionVigente() {
  return {
    planeta: vigente.planeta,
    vehiculo: vigente.vehiculo,
    control: document.getElementById("modo").value,
    veto: document.getElementById("veto").checked,
  };
}
// Tamaño del mapa (ARX-21): pequeno 20×30, mediano 30×45, grande 40×60 (por defecto: grande)
async function cargarPartida(semilla, nivel, tamano = document.getElementById("tamano").value || "grande", config = configuracionVigente(), bateria = null) {
  detenerReproduccion();
  cerrarAvisos();
  reiniciarEventos();
  cargando = true;
  try {
    const cuerpo = { nivel, tamano, planeta: config.planeta, modo: config.vehiculo };
    if (semilla != null) cuerpo.semilla = semilla;
    if (bateria != null) cuerpo.bateria = bateria;   // ARX-87: solo llega desde el botón «Nueva» del panel
    for (const clave of Object.keys(cuerpo)) if (cuerpo[clave] == null) delete cuerpo[clave];   // sin planeta, el motor usa Marte y rover
    let datos = await llamar("POST", "/partida", cuerpo);
    if (!datos) return false;
    // Manda el motor: el planeta y el vehículo que responde son los que se muestran
    vigente = { planeta: datos.planeta, vehiculo: datos.modo_planeta };
    planetaActivo = datos.planeta;
    modoPlanetaActivo = datos.modo_planeta;
    // Una partida nueva arranca en manual: se reaplica el modo de control elegido (si no es el manual simple)
    if (config.control && (config.control !== "manual" || config.veto)) {
      const control = await llamar("POST", "/modo", { modo: config.control, veto: config.veto });
      if (!control) return false;
      datos = control;
    }
    estado = datos;
    document.getElementById("registro").replaceChildren();
    recorridoRover = [];
    avisosVistos.clear();
    const mp = await llamar("GET", "/mapa");
    if (!mp) return false;
    mapa = mp;
    construirMapa(mapa);
    if (capaRiesgoActiva) construirCapaRiesgo(mapa) || actualizarCapaRiesgo();   // M15: la capa sigue al mapa nuevo
    if (evolucion) cargarEvolucion();   // Paquete A: el AG de la partida nueva
    aplicarAspecto(planetaActivo);
    construirRover();
    ubicarRover(datos.posicion, datos.rumbo_sugerido, true);
    encuadrarInicio();
    dibujarRuta(datos.ruta);
    registrarRecorrido(datos.posicion);
    pintarDrones(datos.npcs);
    pintarHud(datos);
    actualizarControlEvento();
    await refrescarPaneles();
    await refrescarEscenarios();
    avisar(`Partida nueva en ${planetaActivo}${modoPlanetaActivo === "sonda" ? " (sonda)" : ""}: semilla ${estado.semilla}, nivel ${NIVELES[nivel - 1]}.`);
    return true;
  } finally {
    cargando = false;
  }
}

// Campo vacío = semilla aleatoria real (1 a 999999); un número escrito se repite tal cual
const NIVELES = ["Muy fácil", "Fácil", "Medio", "Difícil", "Hardcore"];
function semillaDesdeCampo(id) {
  const texto = document.getElementById(id).value.trim();
  if (texto === "") return null;   // vacío: el servidor elige la semilla (§11)
  return Number(texto);
}

// Semilla aleatoria real (ARX-23): entre 1 y 999999, nunca 0
document.getElementById("menu-aleatoria").addEventListener("click", () => {
  const v = crypto.getRandomValues(new Uint32Array(1))[0];
  document.getElementById("menu-semilla").value = 1 + (v % 999999);
});

// Una sola configuración: el asistente central. Tras iniciar, el panel derecho muestra el resumen.
function mostrarMision(semilla, nivel) {
  document.getElementById("controles").classList.remove("oculto");
  document.getElementById("manual").classList.remove("oculto");
  document.getElementById("semilla").value = "";
  document.getElementById("nivel").value = nivel;
  const modo = document.getElementById("modo");
  document.getElementById("resumen-texto").textContent =
    `semilla ${semilla} · nivel ${NIVELES[nivel - 1]} · ${modo.options[modo.selectedIndex].text}`;
}
document.getElementById("reconfigurar").addEventListener("click", () => {
  document.getElementById("menu").classList.remove("oculto");
});

// Controles manuales plegables (en móvil quedan plegados por defecto)
document.getElementById("manual-toggle").addEventListener("click", (ev) => {
  const manual = document.getElementById("manual");
  manual.classList.toggle("plegado");
  manual.classList.toggle("abierto");
  ev.currentTarget.setAttribute("aria-expanded", String(!manual.classList.contains("plegado")));
});

// Pantalla de carga (ARX-60): cuenta 3-2-1 y barra; con transición del vehículo al pulsar «Nueva» o reiniciar
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
function escalarRover(desde, hasta, ms) {
  return new Promise((resolver) => {
    const t0 = performance.now();
    const paso = () => {
      const t = Math.min(1, (performance.now() - t0) / ms);
      grupoRover.scale.setScalar((desde + (hasta - desde) * t) * 1.25 || 0.0001);
      if (t < 1) requestAnimationFrame(paso); else resolver();
    };
    requestAnimationFrame(paso);
  });
}
async function conCarga(fn, { transicion = false } = {}) {
  cerrarAvisos();
  const caja = document.getElementById("carga");
  const texto = document.getElementById("carga-texto");
  const numero = document.getElementById("carga-numero");
  const relleno = document.getElementById("carga-relleno");
  caja.classList.remove("oculto");
  texto.textContent = "Preparando el mapa…";
  numero.textContent = "…";
  relleno.style.width = "30%";
  if (transicion && grupoRover.children.length) await escalarRover(1, 0, 400);   // el vehículo se encoge
  let ok = false;
  try {
    ok = await fn();
    if (ok) await cuentaAtras(2100);
  } catch (err) {
    ok = false;
    avisar("No se pudo iniciar la partida.");
  } finally {
    caja.classList.add("oculto");   // siempre se cierra, también si POST /partida falla
  }
  if (transicion && ok && grupoRover.children.length) await escalarRover(0, 1, 400);   // el nuevo vehículo crece
  return ok;
}
// Cuenta atrás 3-2-1 y «¡Comenzamos!» solo cuando el motor ya ha respondido
async function cuentaAtras(TOTAL) {
  const texto = document.getElementById("carga-texto");
  const numero = document.getElementById("carga-numero");
  const relleno = document.getElementById("carga-relleno");
  const cuenta = ["3", "2", "1"];
  texto.textContent = "Comenzamos en";
  const inicio = performance.now();
  const timer = setInterval(() => {
    const t = performance.now() - inicio;
    numero.textContent = t < TOTAL ? cuenta[Math.min(2, Math.floor(t / 700))] : "¡Comenzamos!";
    relleno.style.width = `${Math.min(100, (t / TOTAL) * 100)}%`;
  }, 50);
  try {
    await esperar(TOTAL);
  } finally {
    clearInterval(timer);
    numero.textContent = "¡Comenzamos!";
  }
}

// Pantalla de meta (ARX-64) y encadenado del automático (ARX-65)
// Encadenado automático: se fija al arrancar desde el asistente con «automatico» y lleva su nivel y sus misiones restantes
let cadenaAutomatica = null;   // { nivel, total, hechas, exitos, fracasos, misiones } o null
function nuevaCadena(nivel, total, veto) {
  // pasos, bateriaFinal y replanteos: un valor por misión terminada (ARX-77)
  return { nivel, total, veto, hechas: 0, exitos: 0, fracasos: 0, misiones: Math.max(0, total - 1),
    pasos: [], bateriaFinal: [], replanteos: [], replanteosActual: 0 };
}
// Número del último paso de /paso (pasos de la misión en curso) y de replanteos de la misión actual
let ultimoPasoNumero = null;

// Mediana y resumen de la cadena (ARX-77)
function mediana(valores) {
  if (!valores.length) return null;
  const orden = [...valores].sort((x, y) => x - y);
  const m = Math.floor(orden.length / 2);
  return orden.length % 2 ? orden[m] : (orden[m - 1] + orden[m]) / 2;
}
function textoCadena(c) {
  const coma = (x, d) => (x == null ? "—" : x.toFixed(d).replace(".", ","));
  const total = c.replanteos.reduce((x, y) => x + y, 0);
  const porMision = c.replanteos.length ? c.replanteos.join(" · ") : "—";
  const bateria = mediana(c.bateriaFinal);
  return `pasos (mediana) ${coma(mediana(c.pasos), 1)} · batería final (mediana) ${coma(bateria, 1)}${bateria == null ? "" : " %"} · replanteos ${total} (por misión: ${porMision})`;
}
const semillaAleatoria = () => 1 + (crypto.getRandomValues(new Uint32Array(1))[0] % 999999);

async function alFinDeMision(codigo) {
  detenerReproduccion();
  cerrarAvisos();
  if (cadenaAutomatica) {
    cadenaAutomatica.hechas += 1;
    if (codigo === "EXITO") cadenaAutomatica.exitos += 1;
    else cadenaAutomatica.fracasos += 1;
    if (ultimoPasoNumero != null) cadenaAutomatica.pasos.push(ultimoPasoNumero);
    if (estado && typeof estado.bateria === "number") cadenaAutomatica.bateriaFinal.push(estado.bateria);
    cadenaAutomatica.replanteos.push(cadenaAutomatica.replanteosActual);
    cadenaAutomatica.replanteosActual = 0;
    await refrescarEscenarios();   // el bloque ya muestra la misión que acaba de terminar
  }
  if (cadenaAutomatica && cadenaAutomatica.misiones > 0) {
    cadenaAutomatica.misiones -= 1;
    avisar(`Misión terminada (${codigo}). La siguiente empieza en 3 s…`);
    await esperar(3000);   // sin preguntar: espera 3 s y sigue con la siguiente
    const { nivel, veto } = cadenaAutomatica;
    // Misma configuración con la que se arrancó la cadena, no la que muestre el panel en ese momento
    const config = { planeta: vigente.planeta, vehiculo: vigente.vehiculo, control: "automatico", veto };
    const ok = await conCarga(() => cargarPartida(null, nivel, undefined, config));
    if (ok) {
      mostrarMision(estado.semilla, nivel);
      alternarReproduccion();
    } else {
      cadenaAutomatica = null;
    }
    await refrescarEscenarios();
    return;
  }
  // La pantalla final usa la cadena; se anula después, para que el bloque conserve los datos de la última misión
  const cadenaTerminada = cadenaAutomatica;
  mostrarMeta(codigo, cadenaTerminada);
  cadenaAutomatica = null;
}

// Confirmar en la meta: cierra la meta y todos los avisos, y crea la partida con lo elegido (planeta, vehículo, tamaño y modo vigentes)
async function nuevaDesdeMeta(semilla, nivel) {
  cerrarAvisos();
  cadenaAutomatica = null;
  const ok = await conCarga(() => cargarPartida(semilla, nivel), { transicion: true });
  if (ok) mostrarMision(estado.semilla, nivel);
}

// Pantalla de meta combinada (ARX-74): mapa y dificultad se eligen sin actuar; «Confirmar» arranca lo elegido
let metaMapa = "repetir";
let metaNivel = 1;
function pintarMetaElecciones() {
  document.getElementById("meta-repetir").setAttribute("aria-pressed", String(metaMapa === "repetir"));
  document.getElementById("meta-otro").setAttribute("aria-pressed", String(metaMapa === "otro"));
  for (const b of document.querySelectorAll("#meta-dificultad button")) {
    b.setAttribute("aria-pressed", String(Number(b.dataset.nivel) === metaNivel));
  }
}
function mostrarMeta(codigo, cadena = null) {
  // Al terminar la última misión de una cadena automática, el resumen de la cadena va arriba
  const resumen = document.getElementById("meta-cadena");
  resumen.classList.toggle("oculto", !cadena);
  resumen.textContent = cadena ? `Cadena automática: ${cadena.hechas} ${cadena.hechas === 1 ? "misión" : "misiones"} · ${cadena.exitos} ${cadena.exitos === 1 ? "éxito" : "éxitos"} · ${cadena.fracasos} ${cadena.fracasos === 1 ? "fracaso" : "fracasos"} · ${textoCadena(cadena)}` : "";
  const lista = document.getElementById("meta-objetivos");
  lista.replaceChildren();
  for (const c of (ultimosObjetivos && ultimosObjetivos.condiciones) || []) {
    const li = document.createElement("li");
    const opcional = c.obligatorio === false;
    li.textContent = `${c.nombre}${opcional ? " (opcional)" : ""}: ${c.progreso}/${c.total}${c.cumplido ? " ✓" : ""}`;
    if (opcional) li.className = "opcional";
    lista.appendChild(li);
  }
  document.getElementById("meta-titulo").textContent = cadena
    ? "Cadena automática terminada"
    : codigo === "EXITO" ? "¡Meta alcanzada!" : `Misión terminada: ${codigo}`;
  metaMapa = "repetir";
  metaNivel = estado.nivel;
  pintarMetaElecciones();
  document.getElementById("meta").classList.remove("oculto");
}
document.getElementById("meta-repetir").addEventListener("click", () => {
  metaMapa = "repetir";
  pintarMetaElecciones();
});
document.getElementById("meta-otro").addEventListener("click", () => {
  metaMapa = "otro";
  pintarMetaElecciones();
});
for (const b of document.querySelectorAll("#meta-dificultad button")) {
  b.addEventListener("click", () => {
    metaNivel = Number(b.dataset.nivel);
    pintarMetaElecciones();
  });
}
document.getElementById("meta-confirmar").addEventListener("click", () => {
  nuevaDesdeMeta(metaMapa === "otro" ? null : estado.semilla, metaNivel);
});
document.getElementById("meta-salir").addEventListener("click", () => {
  document.getElementById("meta").classList.add("oculto");
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
});

// Menú de pausa (ARX-61): Esc abre y cierra; los controles de juego quedan bloqueados mientras está abierto
let pausaActiva = false;
function abrirPausa() {
  pausaActiva = true;
  detenerReproduccion();
  document.getElementById("pausa").classList.remove("oculto");
}
function cerrarPausa() {
  pausaActiva = false;
  document.getElementById("pausa").classList.add("oculto");
}
document.getElementById("pausa-continuar").addEventListener("click", cerrarPausa);
document.getElementById("pausa-reiniciar").addEventListener("click", async () => {
  cerrarPausa();
  cadenaAutomatica = null;
  if (estado) await conCarga(() => cargarPartida(estado.semilla, estado.nivel), { transicion: true });   // misma semilla y nivel
});
document.getElementById("pausa-opciones").addEventListener("click", (ev) => {
  const panel = document.getElementById("pausa-opciones-panel");
  panel.classList.toggle("oculto");
  ev.currentTarget.setAttribute("aria-expanded", String(!panel.classList.contains("oculto")));
});
document.getElementById("pausa-velocidad").addEventListener("change", (ev) => {
  document.getElementById("velocidad").value = ev.target.value;
});
document.getElementById("pausa-camara").addEventListener("change", (ev) => {
  camaraSiguiendo = ev.target.checked;
});
document.getElementById("pausa-salir").addEventListener("click", () => {
  cerrarPausa();
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
});

document.getElementById("menu-modo").addEventListener("change", (ev) => {
  document.getElementById("menu-misiones-fila").classList.toggle("oculto", ev.target.value !== "automatico");
});

// Menú de inicio (ARX-14): hasta que el jugador inicia una partida, la página no crea ninguna.
// Aplica la configuración del asistente: semilla, nivel, modo y veto.
document.getElementById("iniciar").addEventListener("click", async () => {
  const semilla = semillaDesdeCampo("menu-semilla");
  const nivel = Number(document.getElementById("menu-nivel").value);
  const tamano = document.getElementById("menu-tamano").value;
  const config = {
    planeta: document.getElementById("menu-planeta").value,
    vehiculo: document.getElementById("menu-modo-planeta").value,
    control: document.getElementById("menu-modo").value,
    veto: document.getElementById("menu-veto").checked,
  };
  document.getElementById("tamano").value = tamano;
  const ok = await conCarga(() => cargarPartida(semilla, nivel, tamano, config));
  if (!ok) return;
  // El panel queda con la partida que acaba de crearse, para que «Nueva» no cambie la configuración en silencio
  document.getElementById("nivel").value = String(nivel);
  document.getElementById("modo").value = config.control;
  document.getElementById("veto").checked = config.veto;
  cadenaAutomatica = config.control === "automatico" && Number(document.getElementById("menu-misiones").value) > 1 ? nuevaCadena(nivel, Number(document.getElementById("menu-misiones").value), config.veto) : null;
  await refrescarEscenarios();
  mostrarMision(estado.semilla, nivel);
  document.getElementById("menu").classList.add("oculto");
  document.getElementById("menu-semilla").value = "";   // el siguiente inicio vuelve a ser aleatorio, salvo que se escriba una
});
["hist-modo", "hist-tecnica", "hist-motivo"].forEach((id) =>
  document.getElementById(id).addEventListener("change", () => refrescarHistorial()));
// Franja inferior con pestañas: solo un panel abierto a la vez
function abrirPanelDock(nombre) {
  for (const n of ["historial", "graficos"]) {
    const abierto = n === nombre;
    document.getElementById(n).classList.toggle("plegado", !abierto);
    document.getElementById(`${n}-toggle`).setAttribute("aria-expanded", String(abierto));
  }
  if (nombre === "historial") refrescarHistorial();
  if (nombre === "graficos") {
    renderLeyenda();
    refrescarGraficos();
  }
}
function alternarPanelDock(nombre) {
  const estabaAbierto = !document.getElementById(nombre).classList.contains("plegado");
  abrirPanelDock(estabaAbierto ? null : nombre);
}
document.getElementById("historial-toggle").addEventListener("click", () => alternarPanelDock("historial"));
document.getElementById("controles-toggle").addEventListener("click", (ev) => {
  const c = document.getElementById("controles");
  c.classList.toggle("plegado");
  const abierto = !c.classList.contains("plegado");
  ev.currentTarget.setAttribute("aria-expanded", String(abierto));
  ev.currentTarget.querySelector("span").textContent = abierto ? "▾" : "▸";
});

// Mientras se crea una partida, las acciones se bloquean: la sesión del motor cambia al terminar.
function ocupado() {
  if (pausaActiva) return true;   // con la pausa abierta no se mueve nada
  if (cargando) {
    avisar("Cargando partida, espera un momento…");
    return true;
  }
  return false;
}

async function mover(rumbo) {
  if (!mapa || ocupado()) return;
  const r = await llamar("POST", "/mover", { rumbo });
  if (!r) return;
  avisar((r.movido ? `Movimiento ${rumbo}.` : `Movimiento ${rumbo} rechazado: ${r.motivo}`) + eventosTexto(r.eventos_combate));
  registrarEvento(r.movido ? `mover ${rumbo}` : `mover ${rumbo} rechazado: ${r.motivo}`);
  await refrescarEstado();
  await refrescarPaneles();
}

// Cierra todos los avisos y capas: se llama al crear una partida o al entrar en cualquier carga (N9)
function cerrarAvisos() {
  for (const id of ["motor-lento", "error-motor", "sin-resultado", "meta", "pausa"]) {
    document.getElementById(id).classList.add("oculto");
  }
  pausaActiva = false;
}

// Vigilancia de /paso: aviso solo por timeout real (más de 2 s sin respuesta); cada paso arma y cancela su propio temporizador
let pasoEnVuelo = false;   // evita pasos solapados, que dejaban temporizadores armados

// Avisos del motor (/estado.avisos, O12): cada aviso se muestra al aparecer, no en cada paso
const avisosVistos = new Set();
function mostrarAvisosNuevos(lista) {
  const vigentes = Array.isArray(lista) ? lista : [];
  for (const aviso of vigentes) {
    if (avisosVistos.has(aviso)) continue;
    avisosVistos.add(aviso);
    avisar(aviso);
    registrarEvento(`aviso: ${aviso}`);
  }
  // Un aviso que deja de estar vigente se olvida: si vuelve, se muestra otra vez
  for (const aviso of [...avisosVistos]) if (!vigentes.includes(aviso)) avisosVistos.delete(aviso);
}
// Número de paso para los mensajes (O6): en un disparo, /paso manda "ultimo": {} y se usa el último conocido
function pasoDe(r) {
  return r.ultimo && r.ultimo.paso != null ? r.ultimo.paso : (ultimoPasoNumero ?? "");
}
// Disparo automático (O5): el motor no manda el rumbo; se deduce del dron que nombran los eventos y de la posición previa
function rumboDelDisparo(eventos, previo) {
  if (!previo || !previo.posicion) return null;
  const texto = (eventos || []).join(" ");
  const id = (texto.match(/dron (\d+)/) || [])[1];
  const dron = id === undefined ? null : (previo.npcs || []).find((n) => String(n.id) === id);
  if (!dron) return previo.rumbo || null;
  const df = dron.pos[0] - previo.posicion[0];
  const dc = dron.pos[1] - previo.posicion[1];
  const enLinea = df === 0 || dc === 0 || Math.abs(df) === Math.abs(dc);
  if (!enLinea || (df === 0 && dc === 0)) return null;
  return Object.keys(DELTA).find((k) => DELTA[k][0] === Math.sign(df) && DELTA[k][1] === Math.sign(dc)) || null;
}
function efectoDisparoAutomatico(r, previo) {
  const rumbo = rumboDelDisparo(r.eventos_combate, previo);
  if (!rumbo) return;
  const impacto = (r.eventos_combate || []).some((e) => /impacto|destruido/.test(e));
  // Si /paso manda el dron objetivo (celda), el haz va a su posición real; si no, al dron en línea
  // /paso manda el id del dron objetivo (número, o «dron-N»); también se admite una celda o {pos}
  const objetivo = r.ultimo && r.ultimo.objetivo;
  const celda = Array.isArray(objetivo) ? objetivo : objetivo && Array.isArray(objetivo.pos) ? objetivo.pos : null;
  const digitos = objetivo != null && typeof objetivo !== "object" ? String(objetivo).match(/(\d+)/) : null;
  const dronId = digitos ? Number(digitos[1]) : objetivo && objetivo.id != null ? Number(objetivo.id) : null;
  const destino = (dronId != null && puntoDronPorId(dronId)) || (celda && puntoDronEnCelda(celda, previo)) || puntoDronEnLinea(rumbo);
  efectoDisparo(rumbo, impacto, destino);
}
function avisarMotorLento() {
  detenerReproduccion();
  document.getElementById("motor-lento").classList.remove("oculto");
}
document.getElementById("motor-reintentar").addEventListener("click", () => {
  document.getElementById("motor-lento").classList.add("oculto");
  alternarReproduccion();
});
document.getElementById("motor-detener").addEventListener("click", () => {
  document.getElementById("motor-lento").classList.add("oculto");
  detenerReproduccion();
});
document.getElementById("motor-menu").addEventListener("click", () => {
  cerrarAvisos();
  detenerReproduccion();
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
});

// Un paso de la IA: el rover avanza en la escena y los paneles muestran lo que decidió.
async function paso() {
  if (!mapa || ocupado() || pasoEnVuelo) return false;
  // Partida ya terminada: no se envía nada (evita respuestas 409 en la consola)
  if (estado && ESTADOS_TERMINALES.includes(estado.estado)) {
    detenerReproduccion();
    return false;
  }
  const estadoPrevio = estado;
  let r;
  pasoEnVuelo = true;
  const temporizador = setTimeout(avisarMotorLento, 2000);   // más de 2 s sin respuesta: aviso
  try {
    r = await llamar("POST", "/paso");
  } finally {
    clearTimeout(temporizador);
    pasoEnVuelo = false;
  }
  if (!r) {
    detenerReproduccion();
    return false;
  }
  const terminada = ESTADOS_TERMINALES.includes(r.estado);
  const fin = r.accion === "fin";
  if (r.ultimo && r.ultimo.paso != null) ultimoPasoNumero = r.ultimo.paso;
  if (r.accion === "disparar") efectoDisparoAutomatico(r, estadoPrevio);
  if (cadenaAutomatica && r.accion === "replanificar") cadenaAutomatica.replanteosActual += 1;
  await refrescarEstado();
  await refrescarPaneles();
  const motivos = (r.motivos || []).join(", ");
  avisar(`Paso ${pasoDe(r)}: ${r.accion} · ${motivos}` + eventosTexto(r.eventos_combate));
  registrarEvento(`paso ${pasoDe(r)}: ${r.accion} · ${motivos}`);
  mostrarAvisosNuevos(estado && estado.avisos);   // después del aviso del paso, para que no lo tape
  (r.eventos_combate || []).forEach((e) => registrarEvento(`combate: ${e}`));
  if (terminada) {
    detenerReproduccion();
    avisar(`Fin de la partida: ${r.estado}.`);
    alFinDeMision(r.estado);
    return false;
  }
  if (fin) {
    detenerReproduccion();
    avisar("La misión terminó sin resultado.");
    mostrarSinResultado();
    return false;
  }
  return true;
}

// «fin» sin ÉXITO ni FRACASO: la misión no tiene resultado; se ofrece reintentar o volver al menú
function mostrarSinResultado() {
  cadenaAutomatica = null;
  refrescarEscenarios();
  document.getElementById("sin-resultado").classList.remove("oculto");
}
document.getElementById("sin-resultado-reintentar").addEventListener("click", async () => {
  document.getElementById("sin-resultado").classList.add("oculto");
  if (estado) await conCarga(() => cargarPartida(estado.semilla, estado.nivel), { transicion: true });
});
document.getElementById("sin-resultado-menu").addEventListener("click", () => {
  cerrarAvisos();
  detenerReproduccion();
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
});

// Registro lateral (ARX-63): últimos 10 eventos, el más nuevo arriba. El 11 saca al más antiguo.
const REGISTRO_MAX = 10;
function registrarEvento(texto) {
  const lista = document.getElementById("registro");
  const li = document.createElement("li");
  li.textContent = texto;
  li.className = "nueva";
  lista.prepend(li);
  const activos = [...lista.children].filter((e) => !e.classList.contains("saliendo"));
  if (activos.length > REGISTRO_MAX) {
    const viejo = activos[activos.length - 1];
    viejo.classList.add("saliendo");
    setTimeout(() => viejo.remove(), 300);
  }
}

function eventosTexto(eventos) {
  return eventos && eventos.length ? ` · combate: ${eventos.join("; ")}` : "";
}

// Disparo hacia donde mira el rover (tecla Espacio o botón)
async function disparar() {
  if (!mapa || ocupado() || !estado) return;
  const rumbo = estado.rumbo || "N";
  const r = await llamar("POST", "/disparo", { rumbo });
  if (!r) return;
  efectoDisparo(rumbo, r.impacto, puntoDronEnLinea(rumbo));
  avisar((r.impacto ? "¡Impacto!" : "Disparo sin impacto.") + eventosTexto(r.eventos_combate));
  registrarEvento(r.impacto ? "disparo: impacto" : "disparo sin impacto");
  await refrescarEstado();
  await refrescarPaneles();
}

function detenerReproduccion() {
  if (reproduciendo !== null) {
    clearInterval(reproduciendo);
    reproduciendo = null;
    document.getElementById("reproducir").textContent = "Iniciar";
  }
}

function alternarReproduccion() {
  if (reproduciendo !== null) {
    detenerReproduccion();
    return;
  }
  const ms = Number(document.getElementById("velocidad").value);
  document.getElementById("reproducir").textContent = "Detener";
  reproduciendo = setInterval(() => { paso(); }, ms);
}

// ---------- intervención (ARX-10) ----------
function actualizarCampoIntervencion() {
  const tecnica = document.getElementById("int-tecnica").value;
  document.getElementById("int-valor-fila").style.display = tecnica === "difuso" ? "block" : "none";
}

async function aplicarIntervencion() {
  if (ocupado()) return;
  const tecnica = document.getElementById("int-tecnica").value;
  let cuerpo = null;
  if (tecnica === "rna-barranco") cuerpo = { tecnica: "rna", valor: "barranco" };
  if (tecnica === "rna-libre") cuerpo = { tecnica: "rna", valor: "libre" };
  if (tecnica === "difuso") cuerpo = { tecnica: "difuso", valor: Number(document.getElementById("int-valor").value) };
  if (cuerpo === null) {
    avisar("Elige una técnica para intervenir o usa Apagar.");
    return;
  }
  const r = await llamar("POST", "/intervencion", cuerpo);
  if (r) {
    avisar("Intervención aplicada. Pulsa Paso para ver el cambio de decisión.");
    await refrescarEstado();
  }
}

async function apagarIntervencion() {
  const r = await llamar("POST", "/intervencion", { tecnica: "apagar" });
  if (r) {
    document.getElementById("int-tecnica").value = "ninguna";
    actualizarCampoIntervencion();
    avisar("Intervención apagada.");
    await refrescarEstado();
  }
}

// ---------- gráficos de los modelos (ARX-17, parte visual) ----------
// Series tomadas de /historial: cada modelo tiene sus líneas y su escala.
const SERIES = {
  rna: { prob: true, decimales: 2, escala: "fija", lineas: [
    { clave: "p_libre", nombre: "libre", color: "#5fd3ff" },
    { clave: "p_obstaculo", nombre: "obstáculo", color: "#ffb454" },
    { clave: "p_barranco", nombre: "barranco", color: "#ff5d6c" },
  ] },
  difuso: { prob: false, decimales: 3, escala: "fija", lineas: [
    { clave: "velocidad", nombre: "velocidad", color: "#6ee7a8" },
  ] },
  ag: { prob: false, decimales: 2, escala: "auto", lineas: [
    { clave: "fitness", nombre: "fitness", color: "#c39bff" },
  ] },
};
let filasGraficos = [];          // filas del historial sin filtrar
let serieGrafico = "rna";        // pestaña activa
const ocultas = new Set();       // claves de líneas ocultas con la leyenda
let cursorGrafico = null;        // fila bajo el ratón
let geometriaGrafico = null;     // última geometría dibujada (para el cursor)

function formatoValor(v) {
  const cfg = SERIES[serieGrafico];
  if (cfg.prob) return `${(v * 100).toFixed(1).replace(".", ",")} %`;
  return Number(v).toFixed(cfg.decimales).replace(".", ",");
}

// Series por paso desde /serie (contrato CONTRATOS_GRAFICOS.md, §6). Ese endpoint no trae
// p_libre ni p_obstaculo: se completan desde /historial por número de paso.
async function refrescarGraficos() {
  if (!estado || estado.sin_partida) return;
  const [serie, historial] = await Promise.all([llamar("GET", "/serie"), llamar("GET", "/historial")]);
  if (!serie) return;
  const extra = new Map((historial ? historial.filas : []).map((f) => [f.n, f]));
  filasGraficos = serie.filas.map((f) => ({
    ...f,
    p_libre: extra.get(f.n)?.p_libre ?? null,
    p_obstaculo: extra.get(f.n)?.p_obstaculo ?? null,
  }));
  dibujarGrafico();
}

function dibujarGrafico() {
  const lienzoGrafico = document.getElementById("grafico");
  const ancho = lienzoGrafico.clientWidth;
  const alto = lienzoGrafico.clientHeight;
  if (!ancho) return;   // panel plegado: sin tamaño
  const dpr = window.devicePixelRatio || 1;
  lienzoGrafico.width = Math.round(ancho * dpr);
  lienzoGrafico.height = Math.round(alto * dpr);
  const ctx = lienzoGrafico.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, ancho, alto);

  const cfg = SERIES[serieGrafico];
  const lineas = cfg.lineas.filter((l) => !ocultas.has(l.clave));
  const x0 = 46, x1 = ancho - 12, y0 = 10, y1 = alto - 24;
  ctx.font = "12px 'Segoe UI', system-ui, sans-serif";

  if (!filasGraficos.length) {
    ctx.fillStyle = "#98a4bb";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Sin datos todavía: pulsa Paso o Reproducir.", ancho / 2, alto / 2);
    geometriaGrafico = null;
    return;
  }

  const filas = filasGraficos.filter((f) => lineas.some((l) => f[l.clave] != null));
  const ns = filasGraficos.map((f) => f.n);
  const nMin = Math.min(...ns);
  const nMax = Math.max(...ns);
  let yMin = 0;
  let yMax = 1;
  if (cfg.escala === "auto") {
    const vals = filas.flatMap((f) => lineas.map((l) => f[l.clave]).filter((v) => v != null));
    yMin = vals.length ? Math.min(...vals) : 0;
    yMax = vals.length ? Math.max(...vals) : 1;
    if (yMax - yMin < 1e-9) yMax = yMin + 1;
    const margen = (yMax - yMin) * 0.08;
    yMin -= margen;
    yMax += margen;
  }
  const xDe = (n) => x0 + ((n - nMin) / Math.max(1, nMax - nMin)) * (x1 - x0);
  const yDe = (v) => y1 - ((v - yMin) / (yMax - yMin)) * (y1 - y0);
  const etiqueta = (v) => (cfg.prob ? `${Math.round(v * 100)} %` : Number(v).toFixed(cfg.escala === "auto" ? 1 : 2).replace(".", ","));

  // Rejilla horizontal y etiquetas del eje Y
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(150, 200, 255, 0.12)";
  ctx.fillStyle = "#98a4bb";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = yMin + ((yMax - yMin) * i) / 4;
    const y = Math.round(yDe(v)) + 0.5;
    ctx.beginPath();
    ctx.moveTo(x0, y);
    ctx.lineTo(x1, y);
    ctx.stroke();
    ctx.fillText(etiqueta(v), x0 - 8, y);
  }
  // Eje X: primer y último paso
  ctx.textBaseline = "top";
  ctx.textAlign = "left";
  ctx.fillText(`paso ${nMin}`, x0, y1 + 8);
  ctx.textAlign = "right";
  ctx.fillText(`paso ${nMax}`, x1, y1 + 8);

  // Series: un trazo luminoso por línea; los huecos (valor nulo) cortan el trazo
  for (const l of lineas) {
    ctx.strokeStyle = l.color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.shadowColor = l.color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    let abierto = false;
    for (const f of filas) {
      const v = f[l.clave];
      if (v == null) { abierto = false; continue; }
      const x = xDe(f.n);
      const y = yDe(v);
      if (abierto) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      abierto = true;
    }
    ctx.stroke();
  }
  ctx.shadowBlur = 0;

  // Cursor: línea vertical y puntos en los valores de la fila señalada
  if (cursorGrafico) {
    const x = xDe(cursorGrafico.n);
    ctx.strokeStyle = "rgba(231, 237, 247, 0.35)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, y0);
    ctx.lineTo(x, y1);
    ctx.stroke();
    ctx.setLineDash([]);
    for (const l of lineas) {
      const v = cursorGrafico[l.clave];
      if (v == null) continue;
      ctx.fillStyle = "#0b0f1a";
      ctx.strokeStyle = l.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, yDe(v), 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }

  geometriaGrafico = { x0, x1, nMin, nMax, filas, lineas };
}

function renderLeyenda() {
  const contenedor = document.getElementById("graficos-leyenda");
  contenedor.replaceChildren();
  for (const l of SERIES[serieGrafico].lineas) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "chip";
    boton.style.setProperty("--c", l.color);
    boton.setAttribute("aria-pressed", String(!ocultas.has(l.clave)));
    boton.appendChild(document.createElement("i"));
    boton.append(l.nombre);
    boton.addEventListener("click", () => {
      if (ocultas.has(l.clave)) ocultas.delete(l.clave);
      else ocultas.add(l.clave);
      renderLeyenda();
      dibujarGrafico();
    });
    contenedor.appendChild(boton);
  }
}

function ocultarTip() {
  document.getElementById("grafico-tip").textContent = "Pasa el ratón sobre la gráfica para ver cada paso.";
}

// Marca los paneles con scroll que tienen contenido recortado (desvanecido en el borde)
function marcarDesbordes() {
  for (const id of ["controles"]) {
    const el = document.getElementById(id);
    el.classList.toggle("desborda", el.scrollHeight > el.clientHeight + 4 && !el.classList.contains("plegado"));
  }
}

document.getElementById("graficos-toggle").addEventListener("click", () => alternarPanelDock("graficos"));
document.querySelectorAll(".tab[data-serie]").forEach((boton) => {
  boton.addEventListener("click", () => {
    serieGrafico = boton.dataset.serie;
    document.querySelectorAll(".tab[data-serie]").forEach((b) => b.classList.toggle("activa", b === boton));
    cursorGrafico = null;
    ocultarTip();
    renderLeyenda();
    dibujarGrafico();
  });
});
const lienzoGrafico = document.getElementById("grafico");
lienzoGrafico.addEventListener("mousemove", (ev) => {
  const g = geometriaGrafico;
  if (!g || !g.filas.length) return;
  const rect = lienzoGrafico.getBoundingClientRect();
  const mx = ev.clientX - rect.left;
  const nApuntado = g.nMin + ((mx - g.x0) / Math.max(1, g.x1 - g.x0)) * (g.nMax - g.nMin);
  let mejor = null;
  let distancia = Infinity;
  for (const f of g.filas) {
    const d = Math.abs(f.n - nApuntado);
    if (d < distancia) { distancia = d; mejor = f; }
  }
  cursorGrafico = mejor;
  dibujarGrafico();
  const tip = document.getElementById("grafico-tip");
  const partes = g.lineas
    .filter((l) => mejor[l.clave] != null)
    .map((l) => `${l.nombre} ${formatoValor(mejor[l.clave])}`);
  tip.textContent = `paso ${mejor.n} · ${mejor.modo} · ${partes.join(" · ") || "sin valores"}`;
});
lienzoGrafico.addEventListener("mouseleave", () => {
  cursorGrafico = null;
  ocultarTip();
  dibujarGrafico();
  marcarDesbordes();
});

// ---------- entrada ----------
window.addEventListener("keydown", (ev) => {
  // Esc: pausa (si no hay un laboratorio abierto, que cierra con Esc por su cuenta)
  if (ev.key === "Escape") {
    if (!document.getElementById("laboratorio").classList.contains("oculto")) return;
    // Esc solo es pausa durante una partida: con el menú o la configuración visibles, no hace nada
    const enPartida = document.getElementById("menu").classList.contains("oculto") && estado && !estado.sin_partida;
    if (!enPartida && !pausaActiva) return;
    if (pausaActiva) cerrarPausa(); else abrirPausa();
    return;
  }
  if (pausaActiva) return;
  // H: modo cine, oculta los paneles y deja la escena (no actúa mientras se escribe en un campo)
  if ((ev.key === "h" || ev.key === "H") && !["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName)) {
    document.body.classList.toggle("cine");
    return;
  }
  if (ev.key === " ") {
    ev.preventDefault();
    disparar();
    return;
  }
  const rumbo = RUMBO_TECLA[ev.key];
  if (rumbo) {
    ev.preventDefault();
    mover(rumbo);
  }
});
document.querySelectorAll("#pad button[data-r]").forEach((b) => {
  b.addEventListener("click", () => mover(b.dataset.r));
});
// ARX-87: batería inicial opcional del panel (vacío = por defecto); se pasa solo desde «Nueva»
function bateriaDelCampo() {
  const campo = document.getElementById("bateria-inicial");
  return campo && campo.value.trim() !== "" ? Number(campo.value) : null;
}
// ARX-87 (QA): el rango visible del campo sigue la misma fórmula que el servidor (50–150 % del valor por defecto)
function actualizarRangoBateria() {
  const campo = document.getElementById("bateria-inicial");
  if (!campo) return;
  const nivel = Number(document.getElementById("nivel").value);
  const tamanoSel = document.getElementById("tamano").value;
  const [filas, columnas] = { pequeno: [20, 30], mediano: [30, 45], grande: [40, 60] }[tamanoSel] || [40, 60];
  const defecto = (100 - 4 * (nivel - 1)) * (filas * columnas > 600 ? 1.49 : 1);
  campo.min = String(Math.round(0.5 * defecto));
  campo.max = String(Math.round(1.5 * defecto));
}
document.getElementById("nivel").addEventListener("change", actualizarRangoBateria);
document.getElementById("tamano").addEventListener("change", actualizarRangoBateria);
actualizarRangoBateria();
document.getElementById("nueva").addEventListener("click", async () => {
  const semilla = semillaDesdeCampo("semilla");
  const nivel = Number(document.getElementById("nivel").value);
  const ok = await conCarga(() => cargarPartida(semilla, nivel, undefined, configuracionVigente(), bateriaDelCampo()), { transicion: true });
  if (!ok) return;
  cadenaAutomatica = document.getElementById("modo").value === "automatico" && Number(document.getElementById("menu-misiones").value) > 1 ? nuevaCadena(nivel, Number(document.getElementById("menu-misiones").value), document.getElementById("veto").checked) : null;
  await refrescarEscenarios();
  mostrarMision(estado.semilla, nivel);
});
document.getElementById("paso").addEventListener("click", () => paso());
document.getElementById("disparar").addEventListener("click", () => disparar());
document.getElementById("reproducir").addEventListener("click", () => alternarReproduccion());
document.getElementById("modo").addEventListener("change", async (ev) => {
  if (ocupado()) return;
  const datos = await llamar("POST", "/modo", { modo: ev.target.value, veto: document.getElementById("veto").checked });
  if (datos) {
    estado = datos;
    pintarHud(datos);
    avisar(`Modo ${datos.modo}.`);
    await refrescarPaneles();
    }
});
document.getElementById("veto").addEventListener("change", async (ev) => {
  if (ocupado()) return;
  const datos = await llamar("POST", "/modo", { modo: document.getElementById("modo").value, veto: ev.target.checked });
  if (datos) {
    estado = datos;
    pintarHud(datos);
    avisar(`Veto de seguridad ${datos.veto ? "encendido" : "apagado"}.`);
  }
});
document.getElementById("decision-toggle").addEventListener("click", () => {
  const panel = document.getElementById("decision");
  panel.classList.toggle("plegado");
  const abierto = !panel.classList.contains("plegado");
  document.querySelector("#decision-toggle span").textContent = abierto ? "▾" : "▸";
  marcarDesbordes();
});
document.getElementById("int-tecnica").addEventListener("change", actualizarCampoIntervencion);
document.getElementById("int-aplicar").addEventListener("click", aplicarIntervencion);
document.getElementById("int-apagar").addEventListener("click", apagarIntervencion);

// Zoom por botones (pasos proporcionales a la distancia) y vistas de encuadre (ARX-23)
const PASO_ZOOM = 1.2;
// Acerca (factor > 1) o aleja (factor < 1) la cámara a lo largo de su dirección, dentro de los límites del control
function zoomPaso(factor) {
  const d = camara.position.clone().sub(controles.target);
  const distancia = THREE.MathUtils.clamp(d.length() / factor, controles.minDistance, controles.maxDistance);
  camara.position.copy(controles.target).add(d.setLength(distancia));
}
document.getElementById("zoom-mas").addEventListener("click", () => zoomPaso(PASO_ZOOM));
document.getElementById("zoom-menos").addEventListener("click", () => zoomPaso(1 / PASO_ZOOM));
document.getElementById("encuadrar").addEventListener("click", () => {
  if (!grupoRover.children.length) return;
  camaraSiguiendo = true;
  const p = grupoRover.position;
  const desplazamiento = camara.position.clone().sub(controles.target);
  const distancia = THREE.MathUtils.clamp(desplazamiento.length(), 8, 18);
  controles.target.set(p.x, p.y, p.z);
  camara.position.copy(controles.target).add(desplazamiento.setLength(distancia));
});
// Mapa completo (todo el terreno y la ruta planificada): vista fija, sin seguir al rover
document.getElementById("mapa-completo").addEventListener("click", () => {
  if (!mapa) return;
  camaraSiguiendo = false;
  const cx = mapa.columnas / 2;
  const cz = mapa.filas / 2;
  const distancia = Math.max(mapa.columnas, mapa.filas) * 1.05;
  controles.target.set(cx, 0, cz);
  camara.position.set(cx, distancia * 0.8, cz + distancia * 0.6);
  camara.lookAt(controles.target);
});

document.getElementById("ver-mapa").addEventListener("click", () => {
  // Vista de mapa: desde arriba, siguiendo al rover (el giro libre sigue disponible)
  if (!grupoRover.children.length) return;
  camaraSiguiendo = true;
  const p = grupoRover.position;
  controles.target.set(p.x, p.y + 0.25, p.z);
  camara.position.set(p.x, p.y + 16, p.z + 9);
  camara.lookAt(controles.target);
});

window.addEventListener("resize", () => {
  camara.aspect = window.innerWidth / window.innerHeight;
  camara.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  dibujarGrafico();
});

// ---------- bucle ----------
// Contador de FPS (?fps=1): para medir el rendimiento en el propio navegador y GPU
if (new URLSearchParams(location.search).get("fps") === "1") {
  const fpsEl = document.createElement("div");
  fpsEl.id = "fps";
  fpsEl.style.cssText = "position:fixed;left:50%;top:60px;transform:translateX(-50%);z-index:70;background:rgba(0,0,0,.6);color:#fff;padding:4px 8px;border-radius:6px;font:600 12px system-ui,sans-serif";
  document.body.appendChild(fpsEl);
  let cuadros = 0;
  let inicio = performance.now();
  const contar = () => {
    cuadros++;
    const t = performance.now();
    if (t - inicio >= 1000) {
      fpsEl.textContent = `${Math.round((cuadros * 1000) / (t - inicio))} FPS`;
      cuadros = 0;
      inicio = t;
    }
    requestAnimationFrame(contar);
  };
  requestAnimationFrame(contar);
}

const reloj = new THREE.Clock();
let tiempo = 0;
function animar() {
  const dt = Math.min(reloj.getDelta(), 0.1);
  tiempo += dt;
  cielo.position.copy(camara.position);

  // El rover avanza suavemente hacia su celda; las ruedas ruedan según la distancia recorrida
  if (roverDestino) {
    const k = 1 - Math.exp(-dt * 9);
    const antes = grupoRover.position.clone();
    grupoRover.position.lerp(roverDestino.pos, k);
    let d = roverDestino.rot - grupoRover.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    grupoRover.rotation.y += d * k;
    const avance = grupoRover.position.distanceTo(antes);
    for (const eje of ruedasGiro) eje.rotation.z -= avance / 0.1;
  }
  if (evolucion) evolucion.animar(dt);
  if (holograma && holoDatos) holograma.anclar(grupoRover.position, camara);
  if (cabezaRover) cabezaRover.rotation.y = Math.sin(tiempo * 0.5) * 0.6;

  for (const cristal of animados) {
    cristal.rotation.y = tiempo * 1.2;
    cristal.position.y = cristal.userData.base + Math.sin(tiempo * 2 + cristal.position.x) * 0.04;
  }
  for (const halo of halos) {
    halo.scale.setScalar(1 + 0.08 * Math.sin(tiempo * 2 + halo.position.x));
  }
  for (const luz of parpadeos) {
    luz.visible = Math.sin(tiempo * 3) > -0.3;
  }
  if (sondaRover) efectos.actualizarSonda(sondaRover, tiempo, dt, 0, 1.1);
  for (const v of vortices) v.rotation.y += dt * 1.2;
  for (const { grupo } of dronesPorId.values()) {
    const d = grupo.userData;
    const k = 1 - Math.exp(-dt * 3);   // deslizamiento suave hacia la nueva celda
    grupo.position.x += (d.destino.x - grupo.position.x) * k;
    grupo.position.z += (d.destino.z - grupo.position.z) * k;
    grupo.position.y = d.destino.base + Math.sin(tiempo * 2 + d.fase) * 0.05;
    for (const r of d.rotores) r.rotation.y += dt * 14;
  }

  if (camaraSiguiendo && grupoRover.children.length) {
    const p = grupoRover.position;
    const delta = new THREE.Vector3(p.x, p.y + 0.25, p.z).sub(controles.target).multiplyScalar(1 - Math.exp(-dt * 5));
    controles.target.add(delta);
    camara.position.add(delta);
  }
  if (limitesMapa) {
    const t = controles.target;
    t.x = Math.min(limitesMapa.columnas + MARGEN_OBJETIVO, Math.max(-MARGEN_OBJETIVO, t.x));
    t.z = Math.min(limitesMapa.filas + MARGEN_OBJETIVO, Math.max(-MARGEN_OBJETIVO, t.z));
  }
  controles.update();
  // Temblor de sismo (ev3-d41): se suma a la cámara solo para dibujar y se resta después
  const desplazamiento = efectos.desplazamientoTemblor(dt);
  camara.position.add(desplazamiento);
  efectos.actualizarMarcadores(tiempo, camara);
  efectos.actualizarMovibles(tiempo, dt);
  renderer.render(scene, camara);
  camara.position.sub(desplazamiento);
  requestAnimationFrame(animar);
}
animar();

iniciarLaboratorios({ llamar, avisar });

// Arranque (ARX-14): sin partida; el menú pide semilla y nivel. No se crea nada hasta pulsar Iniciar.
