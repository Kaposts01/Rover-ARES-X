// ARES-X · escena 3D del rover (ARX-04, ARX-05 y ARX-20: diseño realista). El motor está en Python; aquí solo se dibuja y se envían acciones.
import * as THREE from "three";
import { OrbitControls } from "/static/vendor/OrbitControls.js";
import { iniciarLaboratorios, seguirPasoLaboratorio, reiniciarLaboratorios } from "/static/laboratorio.js?v=r14";
import * as efectos from "/static/efectos.js?v=r14";
import * as adaptador from "/static/adaptador.js?v=r14";
import { aplicarMoviles, reiniciarEventos } from "/static/moviles.js?v=r14";
import { crearEvolucion } from "/static/evolucion3d.js?v=r14";
import { adaptarAG, ROTULO_EVOLUCION } from "/static/evolucion_datos.js?v=r14";
import { tieneObservada, colorCelda, MODOS, AVISO_SIN_OBSERVACION } from "/static/incertidumbre_datos.js?v=r14";
import { crearHolograma } from "/static/holo3d.js?v=r14";
import { adaptarHolo, ROTULO_HOLO } from "/static/holo_datos.js?v=r14";
import { crearPanelIA } from "/static/panel_ia.js?v=r14";
import { crearSonido } from "/static/sonido.js?v=r14";
import { crearDefensa } from "/static/defensa.js?v=r14";
import {
  reglasActivadas, vehiculoDe, Vehiculo, nombreModo, nombreTecnica, nombreEstado, nombreEstadoDron, nombresMotivos, nombreMotivo, limpiarAviso,
  textoBateriaDifuso, resumenMeta, AYUDA_PUNTAJE_SIMPLE, plural, MARCA_EVENTO, celdasDeEvento, avisoEvento, ubicacionEvento,
} from "/static/textos.js?v=r14";
import { crearMarcasEvento } from "/static/marcas_evento.js?v=r14";
import { crearRecords } from "/static/records.js?v=r14";
import { textoNuevoRecord } from "/static/records_datos.js?v=r14";
import { crearComparar } from "/static/comparar.js?v=r14";
import { crearTutorial } from "/static/tutorial.js?v=r14";
import { TEXTO_CAMBIO_MODO } from "/static/tutorial_datos.js?v=r14";
import { condicionesPlaneta, filasCondiciones, deltaPaso, perfilPlaneta, textoQueCambia } from "/static/planeta_datos.js?v=r14";
import { crearAmbientePlaneta, crearObstaculoGigante } from "/static/planeta_escena.js?v=r14";
import { generadorAleatorio, texturaParaPlaneta, normalParaPlaneta, obtenerTexturaSolar, texturaSombraRadial, obtenerTexturaCarbono } from "/static/texturas.js?v=r14";

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
let panelIA = null;         // panel derecho de IA (se crea al final del módulo)
const sonido = crearSonido(); // sonido procedural, apagado hasta que el usuario lo active
let defensa = null;           // defensa guiada (se crea con la barra de control)

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
  await refrescarEstado();     // 22/11: antes el reintento descartaba la respuesta y la pantalla no se repintaba
  await refrescarPaneles();
});
document.getElementById("error-reiniciar").addEventListener("click", async () => {
  document.getElementById("error-motor").classList.add("oculto");
  if (estado && !estado.sin_partida) await conCarga(() => cargarPartida(estado.semilla, estado.nivel), { transicion: true });
});
document.getElementById("error-menu").addEventListener("click", () => { volverAlInicio("salir"); });

// ---------- utilidades de diseño ----------
// Ruido determinista por celda: el mismo mapa y la misma semilla siempre se ven igual
function azar(f, c, k = 0) {
  const x = Math.sin(f * 127.1 + c * 311.7 + k * 74.7) * 43758.5453;
  return x - Math.floor(x);
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
renderer.shadowMap.type = THREE.PCFSoftShadowMap;   // bordes de sombra suaves (rover y rocas)
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
    float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
    void main() {
      vec3 d = normalize(vDir);
      float altura = smoothstep(0.0, 0.5, d.y);
      vec3 color = mix(horizonte, arriba, altura);
      // velo de bruma pegado al horizonte (polvo en suspensión)
      color = mix(color, horizonte * 1.12, 0.35 * exp(-abs(d.y) * 14.0));
      // estrellas: solo visibles cuando el cielo es oscuro (Mercurio, noche) y por encima del horizonte
      float oscuridad = 1.0 - smoothstep(0.06, 0.22, dot(arriba, vec3(0.3, 0.59, 0.11)));
      vec3 celda = floor(d * 700.0);
      float e = step(0.9986, hash(celda)) * (0.5 + 0.5 * hash(celda + 3.1));
      color += vec3(0.9, 0.95, 1.0) * e * oscuridad * smoothstep(0.02, 0.2, d.y);
      float brillo = max(dot(d, normalize(sol)), 0.0);
      color += vec3(1.0, 0.72, 0.45) * (0.35 * pow(brillo, 16.0) + 1.2 * pow(brillo, 400.0) + 0.12 * pow(brillo, 3.0));
      gl_FragColor = vec4(color, 1.0);
    }`,
});
const cielo = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), materialCielo);
cielo.renderOrder = -1;
scene.add(cielo);

const luzCielo = new THREE.HemisphereLight(0xb9cfff, 0x4a2818, 0.85);   // el suelo rebota la luz con el color del planeta
scene.add(luzCielo);
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
const vehiculoActual = () => vehiculoDe(modoPlanetaActivo);   // nombre para los textos: «rover» o «sonda»
let sondaRover = null;           // sonda 3D cuando el modo es sonda (gigantes)// posición y rumbo a los que avanza el rover suavemente

const materiales = {
  roca: new THREE.MeshStandardMaterial({ color: 0x8a5e4a, roughness: 0.9, metalness: 0.02 }),
  borde: new THREE.MeshStandardMaterial({ color: 0x8c3f24, roughness: 0.88 }),
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
  guijarro: new THREE.MeshStandardMaterial({ color: 0x8e5e44, roughness: 0.95 }),
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

const vortices = [];   // vórtices de Júpiter: giran lentamente

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
// Apagado: no se crea nada ni se pide nada. Encendido: /rna y /difuso por paso (sin solapar); /estado ya lo pide el paso.
// /ag (el costo más alto) solo se pide al cambiar el plan o cada HOLO_AG_CADA_N pasos; entre medias se reutiliza el último.
// El plan cambia si cambia el siguiente sitio objetivo (/estado.objetivo, que cambia al visitar un sitio), si cambia el
// último replanteo del AG (/estado.ultimo_replanteo) o si la misión pasa a REFUGIO (ya no quedan sitios pendientes).
const HOLO_AG_CADA_N = 5;
let holograma = null;
let holoDatos = null;
let holoEnVuelo = false;
let holoAg = null;                 // último /ag recibido
let holoFirmaPlan = null;          // firma del plan con el que se pidió holoAg
let holoPasosDesdeAg = 0;

function firmaPlanHolo(est) {
  if (!est) return null;
  return JSON.stringify([est.semilla, est.nivel, est.objetivo || null, est.ultimo_replanteo || null, est.estado === "REFUGIO"]);
}

async function refrescarHolo() {
  if (!holograma || !mapa || holoEnVuelo) return;
  holoEnVuelo = true;
  try {
    const firma = firmaPlanHolo(estado);
    const pedirAg = holoAg === null || firma !== holoFirmaPlan || holoPasosDesdeAg >= HOLO_AG_CADA_N;
    const [rna, difuso, ag] = await Promise.all([
      llamar("GET", "/rna"), llamar("GET", "/difuso"), pedirAg ? llamar("GET", "/ag") : Promise.resolve(holoAg)]);
    if (!holograma) return;
    if (pedirAg) { holoAg = ag; holoFirmaPlan = firma; holoPasosDesdeAg = 0; } else holoPasosDesdeAg += 1;
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
      holoAg = null; holoFirmaPlan = null; holoPasosDesdeAg = 0;
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
  for (const [px, pz, peso = 1] of pozos) {   // peso < 1: barranco que se está hundiendo (animación del evento)
    s += peso * Math.exp(-((x - px) ** 2 + (z - pz) ** 2) / (2 * RADIO_POZO * RADIO_POZO));
  }
  return Math.min(s, 1);
}

// Ruido de valor suave (determinista) para el micro relieve del suelo
const RELIEVE_FINO = 0.16;
function ruidoSuelo(x, z) {
  const ix = Math.floor(x), iz = Math.floor(z), fx = x - ix, fz = z - iz;
  const sx = fx * fx * (3 - 2 * fx), sz = fz * fz * (3 - 2 * fz);
  const a = azar(ix, iz, 7), b = azar(ix + 1, iz, 7), c = azar(ix, iz + 1, 7), d = azar(ix + 1, iz + 1, 7);
  return a + (b - a) * sx + (c - a) * sz + (a - b - c + d) * sx * sz;
}
// Altura del terreno en coordenadas de escena: el rover, las rocas y los drones se apoyan en ella
function alturaTerreno(x, z) {
  let h = RELIEVE * (
    Math.sin(x * 0.52 + 1.3) * Math.cos(z * 0.41 - 0.4)
    + 0.6 * Math.sin((x + z) * 0.23 + 2.1)
    + 0.35 * Math.cos(x * 1.31 - z * 0.97)
  ) + RELIEVE_FINO * (ruidoSuelo(x * 0.9, z * 0.9) * 0.65 + ruidoSuelo(x * 2.3 + 17, z * 2.3 + 5) * 0.35 - 0.5);
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
  const geom = new THREE.PlaneGeometry(ancho, alto, ancho * 2, alto * 2);   // dos segmentos por celda: se ve el micro relieve
  geom.rotateX(-Math.PI / 2);
  geom.translate(columnas / 2, 0, filas / 2);
  const pos = geom.attributes.position;
  const sombra = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    pos.setY(i, alturaTerreno(x, z));
    // Los barrancos se oscurecen por vértice; además, manchas grandes de color (el suelo no se ve repetido)
    const k = (1 - 0.8 * influenciaPozos(x, z)) * (0.84 + 0.3 * ruidoSuelo(x * 0.11 + 3, z * 0.11 + 9));
    const tinte = ruidoSuelo(x * 0.07 + 40, z * 0.07 + 11) - 0.5;
    sombra[i * 3] = k * (1 + tinte * 0.12);
    sombra[i * 3 + 1] = k;
    sombra[i * 3 + 2] = k * (1 - tinte * 0.12);
  }
  geom.computeVertexNormals();
  // Laderas más oscuras (oclusión barata): cuanto más inclinada la normal, menos luz recibe
  const nor = geom.attributes.normal;
  for (let i = 0; i < pos.count; i++) {
    const f = 0.72 + 0.28 * THREE.MathUtils.smoothstep(nor.getY(i), 0.8, 0.99);
    sombra[i * 3] *= f; sombra[i * 3 + 1] *= f; sombra[i * 3 + 2] *= f;
  }
  geom.setAttribute("color", new THREE.BufferAttribute(sombra, 3));

  const texturaActual = texturaParaPlaneta(planetaActivo);
  texturaActual.repeat.set(ancho / 12, alto / 12);   // 12 unidades por repetición: el patrón casi no se nota
  const normalActual = normalParaPlaneta(planetaActivo);
  if (normalActual) normalActual.repeat.copy(texturaActual.repeat);
  // PBR mate con mapa de normales: el relieve fino recoge la luz rasante del sol
  const material = new THREE.MeshStandardMaterial({
    map: texturaActual, vertexColors: true, roughness: 0.95, metalness: 0,
    normalMap: normalActual || null, normalScale: new THREE.Vector2(0.9, 0.9),
  });
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
// Libera lo propio del mapa anterior: el suelo (geometría y material) y los búferes de instancias.
// Los materiales compartidos (materiales.*) y las geometrías de roca cacheadas se reutilizan y no se liberan.
function liberarMapa() {
  const suelo = grupoMapa.children[0];
  if (suelo && suelo.isMesh && !suelo.isInstancedMesh) {
    try { suelo.geometry.dispose(); suelo.material.dispose(); } catch (e) { /* ya liberado */ }
  }
  grupoMapa.traverse((o) => { if (o.isInstancedMesh) { try { o.dispose(); } catch (e) { /* ya liberado */ } } });
}
// Arbustos de la Tierra y piedras o cristales de borde: material y geometría únicos (no se crean de nuevo en cada evento ni mapa)
const matArbusto = new THREE.MeshStandardMaterial({ color: 0x4f7a3a, roughness: 0.95 });
const geoBordeRoca = new THREE.DodecahedronGeometry(0.1, 0);
const geoBordeCristal = new THREE.ConeGeometry(0.06, 0.34, 5);   // en los gigantes el borde de un sumidero es de hielo, no de roca
const matBordeCristal = new THREE.MeshStandardMaterial({ color: 0xd6efff, roughness: 0.2, flatShading: true, transparent: true, opacity: 0.85, emissive: 0x2f5f78, emissiveIntensity: 0.5 });
// Canto rodado: icosaedro deformado por una función de la posición (los vértices repetidos se mueven igual y no se abren
// grietas) y con la base aplanada para que apoye en el suelo. Caras planas a propósito: se lee como roca fracturada.
const geometriasRoca = new Map();
function geometriaRoca(variante, detalle = 2) {
  const clave = `${variante}:${detalle}`;
  if (geometriasRoca.has(clave)) return geometriasRoca.get(clave);
  const g = new THREE.IcosahedronGeometry(1, detalle);
  const pos = g.attributes.position, s0 = 1.7 + variante * 2.3;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const d = 1 + 0.22 * Math.sin(x * 2.3 + s0) * Math.sin(y * 1.9 + s0 * 1.3) * Math.sin(z * 2.7 + s0 * 0.7)
      + 0.09 * Math.sin(x * 6.1 + y * 4.3 + s0) + 0.05 * Math.sin(z * 9.7 - x * 7.3 + s0 * 2);
    x *= d; y *= d * 0.82; z *= d;
    if (y < -0.3) y = -0.3 + (y + 0.3) * 0.25;
    pos.setXYZ(i, x, y, z);
  }
  g.computeVertexNormals();
  geometriasRoca.set(clave, g);
  return g;
}
// Rocas instanciadas repartidas en las variantes, con un tono distinto por roca (el color base es el del planeta)
function instanciarRocas(material, matrices, { detalle = 2, sombra = true, semilla = 1 } = {}) {
  const grupo = new THREE.Group();
  const azarTono = generadorAleatorio(semilla);
  const color = new THREE.Color();
  for (let v = 0; v < 3; v++) {
    const propias = matrices.filter((_, k) => k % 3 === v);
    if (!propias.length) continue;
    const im = new THREE.InstancedMesh(geometriaRoca(v, detalle), material, propias.length);
    propias.forEach((m, k) => {
      im.setMatrixAt(k, m);
      const t = 0.78 + azarTono() * 0.4;
      im.setColorAt(k, color.setRGB(t * (0.97 + azarTono() * 0.06), t, t * (0.95 + azarTono() * 0.06)));
    });
    im.instanceMatrix.needsUpdate = true;
    if (im.instanceColor) im.instanceColor.needsUpdate = true;
    im.castShadow = sombra; im.receiveShadow = true;
    grupo.add(im);
  }
  return grupo;
}
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
  const gigante = ES_GIGANTE(planetaActivo);
  const piedras = new THREE.InstancedMesh(gigante ? geoBordeCristal : geoBordeRoca, gigante ? matBordeCristal : materiales.borde, bordes.length);
  bordes.forEach((b, i) => {
    p.set(b.x, alturaTerreno(b.x, b.z) + (gigante ? 0.12 : 0.02), b.z);
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

// ---------- bases de recarga y pilas (22/11) ----------
// Las bases son fijas en la partida; las pilas desaparecen al recogerlas (con un destello). Vienen de /estado.
const grupoEnergia = new THREE.Group();
scene.add(grupoEnergia);
const energiaMalla = new Map();   // "b:f,c" o "p:f,c" -> objeto 3D
const matBase = new THREE.MeshStandardMaterial({ color: 0x2b3446, metalness: 0.6, roughness: 0.4 });
const matBaseLuz = new THREE.MeshBasicMaterial({ color: 0x6ee7a8, toneMapped: false });
const matPilaCuerpo = new THREE.MeshStandardMaterial({ color: 0x1d2633, metalness: 0.5, roughness: 0.35 });
const matPilaBanda = new THREE.MeshBasicMaterial({ color: 0x9cff57, toneMapped: false });
function crearBaseRecarga() {
  const g = new THREE.Group();
  const plataforma = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.46, 0.08, 6), matBase);
  const anillo = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.025, 8, 36), matBaseLuz); anillo.rotation.x = Math.PI / 2; anillo.position.y = 0.05;
  const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.6, 8), matBase); poste.position.set(0.32, 0.3, 0);
  const foco = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 8), matBaseLuz); foco.position.set(0.32, 0.62, 0);
  const rayo = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.16, 3), matBaseLuz); rayo.position.y = 0.2; rayo.rotation.z = 0.4;
  g.add(plataforma, anillo, poste, foco, rayo);
  g.userData.anim = (t) => { anillo.scale.setScalar(1 + 0.06 * Math.sin(t * 3)); rayo.rotation.y = t * 1.5; foco.visible = Math.sin(t * 4) > -0.6; };
  return g;
}
function crearPila() {
  const g = new THREE.Group();
  const cuerpo = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.26, 16), matPilaCuerpo);
  const banda = new THREE.Mesh(new THREE.CylinderGeometry(0.093, 0.093, 0.08, 16), matPilaBanda); banda.position.y = 0.04;
  const polo = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.04, 12), matPilaBanda); polo.position.y = 0.15;
  const pila = new THREE.Group(); pila.add(cuerpo, banda, polo); pila.position.y = 0.3; pila.rotation.z = 0.35;
  g.add(pila);
  g.userData.anim = (t) => { pila.rotation.y = t * 1.6; pila.position.y = 0.3 + Math.sin(t * 2.2) * 0.05; };
  return g;
}
function destelloPila(pos) {
  const m = new THREE.Mesh(new THREE.RingGeometry(0.1, 0.16, 32), new THREE.MeshBasicMaterial({ color: 0x9cff57, transparent: true, side: THREE.DoubleSide, toneMapped: false }));
  m.rotation.x = -Math.PI / 2; m.position.copy(pos).add(new THREE.Vector3(0, 0.05, 0)); scene.add(m);
  const t0 = performance.now();
  const cuadro = () => {
    const u = (performance.now() - t0) / 700;
    m.scale.setScalar(1 + u * 6); m.material.opacity = Math.max(0, 1 - u);
    if (u < 1) requestAnimationFrame(cuadro); else { scene.remove(m); m.geometry.dispose(); m.material.dispose(); }
  };
  requestAnimationFrame(cuadro);
}
function pintarEnergia(e) {
  if (!mapa || !e || e.sin_partida) return;
  const deseadas = new Map();
  for (const [f, c] of e.estaciones || []) deseadas.set(`b:${f},${c}`, [f, c, "base"]);
  for (const [f, c] of e.pilas || []) deseadas.set(`p:${f},${c}`, [f, c, "pila"]);
  for (const [k, obj] of energiaMalla) {
    if (deseadas.has(k)) continue;
    if (k.startsWith("p:")) destelloPila(obj.position);   // recogida
    grupoEnergia.remove(obj); energiaMalla.delete(k);
  }
  for (const [k, [f, c, tipo]] of deseadas) {
    if (energiaMalla.has(k)) continue;
    const obj = tipo === "base" ? crearBaseRecarga() : crearPila();
    const x = c + 0.5, z = f + 0.5;
    obj.position.set(x, alturaTerreno(x, z), z);
    grupoEnergia.add(obj); energiaMalla.set(k, obj);
  }
}
function limpiarEnergia() { for (const obj of energiaMalla.values()) grupoEnergia.remove(obj); energiaMalla.clear(); }

// 22/11: el barranco del evento se hunde a la vista (1,2 s) con polvo y rocas, y luego queda como las grietas del sismo
function animarBarranco(celdas) {
  const suelo = grupoMapa.children[0];
  for (const [f, c] of celdas) {
    if (!mapa || !mapa.tipo[f] || mapa.tipo[f][c] === TIPO_BARRANCO) continue;
    const cx = c + 0.5, cz = f + 0.5, y0 = alturaTerreno(cx, cz);
    const pozo = [cx, cz, 0];
    pozos.push(pozo);
    // vértices del suelo cerca del hoyo (los únicos que se recalculan cada cuadro)
    const cerca = [];
    if (suelo && suelo.geometry) {
      const pos = suelo.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) if (Math.hypot(pos.getX(i) - cx, pos.getZ(i) - cz) < 1.6) cerca.push(i);
    }
    // polvo y rocas
    const N = 110, pp = new Float32Array(N * 3), vel = [];
    for (let i = 0; i < N; i++) {
      pp.set([cx + (Math.random() - 0.5) * 0.6, y0 + 0.05, cz + (Math.random() - 0.5) * 0.6], i * 3);
      vel.push([(Math.random() - 0.5) * 1.6, 0.8 + Math.random() * 1.6, (Math.random() - 0.5) * 1.6]);
    }
    const gPolvo = new THREE.BufferGeometry(); gPolvo.setAttribute("position", new THREE.BufferAttribute(pp, 3));
    const mPolvo = new THREE.PointsMaterial({ color: 0xe6d2b4, size: 0.24, transparent: true, opacity: 0.95, depthWrite: false });   // claro: se ve también sobre suelos oscuros o azules
    const polvo = new THREE.Points(gPolvo, mPolvo); scene.add(polvo);
    const rocas = [];
    for (let k = 0; k < 5; k++) {
      const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.05 + Math.random() * 0.05, 0), materiales.borde);
      r.position.set(cx + (Math.random() - 0.5) * 0.5, y0 + 0.1, cz + (Math.random() - 0.5) * 0.5);
      r.userData.v = new THREE.Vector3((cx - r.position.x) * 0.8, 0.6, (cz - r.position.z) * 0.8);
      scene.add(r); rocas.push(r);
    }
    efectos.sacudir(0.06, 0.8);
    const t0 = performance.now(), DURA = 1200;
    const cuadro = () => {
      const u = Math.min(1, (performance.now() - t0) / DURA);
      pozo[2] = u * u * (3 - 2 * u);
      if (suelo && cerca.length) {
        const pos = suelo.geometry.attributes.position;
        for (const i of cerca) pos.setY(i, alturaTerreno(pos.getX(i), pos.getZ(i)));
        pos.needsUpdate = true;
      }
      const dt = 1 / 60;
      for (let i = 0; i < N; i++) { pp[i * 3] += vel[i][0] * dt; pp[i * 3 + 1] += vel[i][1] * dt; pp[i * 3 + 2] += vel[i][2] * dt; vel[i][1] -= 1.6 * dt; }
      gPolvo.attributes.position.needsUpdate = true; mPolvo.opacity = 0.95 * (1 - u);
      for (const r of rocas) { r.userData.v.y -= 4 * dt; r.position.addScaledVector(r.userData.v, dt); r.rotation.x += 0.2; }
      if (u < 1) { requestAnimationFrame(cuadro); return; }
      scene.remove(polvo); gPolvo.dispose(); mPolvo.dispose();
      for (const r of rocas) { scene.remove(r); r.geometry.dispose(); }
      pozos.splice(pozos.indexOf(pozo), 1);
      agregarGrietas([[f, c]]);       // estado final: barranco con piedras de borde y la cuadrícula rehecha
    };
    requestAnimationFrame(cuadro);
  }
}

function construirMapa(datos) {
  reiniciarCondiciones();   // mapa nuevo: las condiciones vivas y las celdas de hielo se leen de nuevo
  limitesMapa = { columnas: datos.columnas, filas: datos.filas };
  liberarMapa();
  limpiarEnergia();
  marcasEvento.limpiar(); encuadreEvento = null;   // las marcas de eventos de la partida anterior no pasan a la nueva
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
  const matricesGuijarros = [];
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
    matricesGuijarros.push(m.clone()); colocados++;
  }
  // los guijarros no proyectan sombra: ahorra mucho render
  if (matricesGuijarros.length) grupoMapa.add(instanciarRocas(materiales.guijarro, matricesGuijarros, { detalle: 1, sombra: false, semilla: 11 }));

  const geomHalo = new THREE.RingGeometry(0.32, 0.46, 32);

  // Rocas y piedras de borde como instancias (rendimiento): un dibujo por tipo en lugar de una malla por piedra
  const rocas = [];
  const arbustos = [];
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
      const rasgoObstaculo = perfilPlaneta(planetaActivo).rasgos.obstaculo;
      if (t === TIPO_OBSTACULO && ES_GIGANTE(planetaActivo)) {
        // cada gigante tiene lo suyo: Júpiter vórtices; Saturno bruma dorada; Urano cristales; Neptuno nubes y formaciones de hielo (ninguna roca)
        grupoMapa.add(rasgoObstaculo === "vortice" ? crearVortice(x, y, z) : crearObstaculoGigante(THREE, rasgoObstaculo, x, y, z, (k) => azar(f, c, 200 + k)));
      } else if (t === TIPO_OBSTACULO && rasgoObstaculo === "arbusto" && azar(f, c, 300) < 0.6) {
        // Tierra: la mayoría de los obstáculos son arbustos (blobs verdes), el resto rocas
        const tam = 0.26 + azar(f, c, 301) * 0.2;
        escalaX.set(tam * 1.5, tam * 0.9, tam * 1.4);
        posX.set(x + (azar(f, c, 302) - 0.5) * 0.3, y + tam * 0.45, z + (azar(f, c, 303) - 0.5) * 0.3);
        rotX.setFromEuler(new THREE.Euler(0, azar(f, c, 304) * 6, 0));
        arbustos.push(new THREE.Matrix4().compose(posX, rotX, escalaX));
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
  if (rocas.length) grupoMapa.add(instanciarRocas(materiales.roca, rocas, { semilla: datos.columnas * 7 + datos.filas }));
  if (arbustos.length) grupoMapa.add(instanciarRocas(matArbusto, arbustos, { detalle: 1, semilla: 17 }));
  if (bordes.length && ES_GIGANTE(planetaActivo)) grupoMapa.add(instanciar(geoBordeCristal, matBordeCristal, bordes.map((mb) => mb.clone().scale(new THREE.Vector3(1.4, 1.4, 1.4)))));
  else if (bordes.length) grupoMapa.add(instanciarRocas(materiales.borde, bordes.map((mb) => mb.clone().scale(new THREE.Vector3(0.1, 0.1, 0.1))), { detalle: 1, sombra: false, semilla: 5 }));

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
  const lejosNiebla = perfilPlaneta(planetaActivo).nieblaLejos;   // Venus y los gigantes: bruma densa; Mercurio: sin atmósfera
  scene.fog.near = escala * 0.9 * Math.min(1, lejosNiebla / 2.4);
  scene.fog.far = escala * lejosNiebla;
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
  pintarRotulosReproduccion();
}
document.getElementById("menu-modo").addEventListener("change", (ev) => {
  document.getElementById("menu-modo-desc").textContent = MODO_DESC[ev.target.value] || "";
});

// Recomendaciones (ARX-54, contrato §12): lo que haría cada modelo, sin mover el rover
const NOMBRE_MODELO = { hibrido: "Híbrido", rna: "RNA", difuso: "Difuso", ag: "AG" };
const TEXTO_REC_VACIO = "Pulsa el botón para ver qué haría cada modelo en esta celda.";
let recomendacionEpoca = 0;   // sube con cada paso o partida: una respuesta tardía de una celda anterior no se muestra
// Las recomendaciones valen para UNA celda: tras cada movimiento o paso se recalculan (si el cuadro está abierto) o se
// borran y se pide consultar de nuevo, para que nunca se vea el «rumbo» de una posición anterior.
function actualizarRecomendacion() {
  recomendacionEpoca += 1;
  const caja = document.getElementById("det-rec");
  const modoManual = document.getElementById("modo").value === "manual";
  if (modoManual && caja && caja.open && estado && !estado.sin_partida && !ESTADOS_TERMINALES.includes(estado.estado)) { consultarRecomendacion(); return; }
  const lista = document.getElementById("rec-lista");
  lista.replaceChildren(Object.assign(document.createElement("li"), { textContent: TEXTO_REC_VACIO }));
}
async function consultarRecomendacion() {
  avisarAccion("recomendacion");
  const lista = document.getElementById("rec-lista");
  const epoca = ++recomendacionEpoca;
  lista.replaceChildren();
  const datos = await deps_recomendacion();
  if (epoca !== recomendacionEpoca) return;   // el rover ya se movió: esta respuesta es de otra celda
  if (!datos || !datos.propuestas) {
    lista.appendChild(Object.assign(document.createElement("li"), { textContent: "Sin recomendación (revisa que haya partida y modo manual)." }));
    return;
  }
  if (Array.isArray(datos.posicion)) lista.appendChild(Object.assign(document.createElement("li"), { textContent: `Para la celda (${datos.posicion.join(", ")})` }));
  for (const p of datos.propuestas) {
    const li = document.createElement("li");
    const rumbo = p.rumbo ? ` · rumbo ${p.rumbo}` : ` · no mueve el ${vehiculoActual()}`;
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
  const textoModo = modoSel.options[modoSel.selectedIndex] ? modoSel.options[modoSel.selectedIndex].text : nombreModo(e.modo);
  document.getElementById("resumen-texto").textContent = `semilla ${e.semilla} · nivel ${NIVELES[(e.nivel || 1) - 1]} · ${textoModo}`;
  if (!modoDemoEstados) pintarEstadoBadge(e.estado);
  // Título con el planeta: /estado.planeta, luego /planetas.activo.planeta, y por último el valor local
  const planetaVisible = e.planeta || (planetasDatos && planetasDatos.activo && planetasDatos.activo.planeta);
  if (planetaVisible) {
    planetaActivo = planetaVisible;
    const modoVisible = e.modo_planeta === "sonda" || e.modo_planeta === "rover" ? ` · ${Vehiculo(e.modo_planeta)}` : "";
    document.querySelector("#hud h1").textContent = `ARES-X · ${planetaVisible}${modoVisible}`;
  }
  // ARX-85 (ev3-d61 A): en modo sonda, pantalla de sonda con sus lecturas y sin controles de rodaje
  const enSonda = e.modo_planeta === "sonda";
  const panelSonda = document.getElementById("sonda-panel");
  const padConduccion = document.getElementById("pad");
  if (panelSonda) panelSonda.classList.toggle("oculto", !enSonda);
  // 22/11: la sonda no se conduce a mano, pero sí se puede encuadrar y ver capas: solo se oculta el pad de conducción
  // (antes se ocultaba todo el bloque y con la sonda no había forma de recentrar la cámara)
  if (padConduccion) padConduccion.style.display = enSonda ? "none" : "";
  document.getElementById("manual").classList.toggle("sin-pad", enSonda);   // sin pad, los botones de vista se reparten en dos filas
  const botonRover = document.getElementById("encuadrar");
  if (botonRover) { botonRover.textContent = enSonda ? "Sonda" : "Rover"; botonRover.title = enSonda ? "Centrar en la sonda" : "Centrar en el rover"; }
  if (enSonda) {
    document.getElementById("sonda-planeta").textContent = planetaActivo;
    document.getElementById("sonda-temp").textContent = `${e.temperatura_interna} °C (tolerancia ${e.tolerancia} °C)`;
    document.getElementById("sonda-bateria").textContent = `${(e.bateria_pct ?? e.bateria).toFixed(1)} %`;
    document.getElementById("sonda-sobre").textContent = e.pasos_sobre_tolerancia ?? "-";
    document.getElementById("sonda-estado").textContent = nombreEstado(e.estado);
  }
  const velo = document.getElementById("ambiente-velo");   // noche o tormenta en curso: el velo de la escena (el motor cuenta los pasos que quedan)
  if (velo) { velo.className = e.ambiente === "noche" || e.ambiente === "tormenta" ? e.ambiente : ""; }
  ambientePlaneta.reforzar(e.ambiente === "tormenta" ? 2.2 : 1);   // la tormenta levanta el viento mientras dura
  aplicarCondiciones(e);
  document.getElementById("h-semilla").textContent = e.semilla;
  document.getElementById("h-estado").textContent = nombreEstado(e.estado);
  // 22/11: porcentaje de la capacidad del rover (nunca más de 100 %); el motor sigue en sus unidades
  const bpct = e.bateria_pct ?? e.bateria;
  document.getElementById("h-bateria").textContent = `${bpct.toFixed(1)} %`;
  document.getElementById("h-bateria-barra").style.width = `${Math.max(0, Math.min(100, bpct))}%`;
  try { pintarEnergia(e); } catch (err) { console.warn("bases y pilas: no se pudieron dibujar", err); }
  document.getElementById("h-puntaje").textContent = e.puntaje;
  document.getElementById("h-municion").textContent = e.municion;
  document.getElementById("h-modo").textContent = nombreModo(e.modo);
  document.getElementById("h-paso").textContent = e.paso ?? "-";
  document.getElementById("h-cooldown").textContent = e.cooldown ?? "-";
  const vivos = (e.npcs || []).map((n) => nombreEstadoDron(n.estado));
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
  lineas.push(ruta.length ? `Planificador: ruta de ${plural(ruta.length, "celda", "celdas")}` : "Planificador: sin ruta");
  const supv = p.supervisor || {};
  const vetos = (supv.motivos || []).filter(m => String(m).startsWith("V-"));
  lineas.push(`Supervisor: ${supv.accion || "sin dato"}${vetos.length ? ` · veto: ${nombresMotivos(vetos)}` : ""}`);
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
    lista.innerHTML = `<li>el difuso no mueve el ${vehiculoActual()} en este modo</li>`;
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
  document.getElementById("ag-ruta").textContent = n ? `${plural(n, "celda", "celdas")} hasta el objetivo` : "sin ruta";
  document.getElementById("res-ag").textContent = n ? plural(n, "celda", "celdas") : "sin ruta";

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
    li.textContent = m === "-" ? m : nombreMotivo(m);
    if (m !== "-") li.title = `Código del motor: ${m}`;
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
  // QA O-5: el rótulo sigue al modelo activo (v2: desnivel/contraste); sin nombres, los de v1
  const rotulo = (i, porDefecto) => ((sen && sen.rasgos_nombres && sen.rasgos_nombres[i]) || porDefecto).replace(/_/g, " ");
  if (indicador) indicador.textContent = !sen ? "-"
    : sen.falla ? `${sen.rumbo}: falla de sensor · riesgo enfrente ${dato(sen.riesgo_enfrente)}`
    : `${sen.rumbo}: proximidad ${dato(sen.proximidad)} · ${rotulo(1, "borde")} ${dato(sen.borde)} · ${rotulo(2, "gradiente")} ${dato(sen.gradiente)} · vibración ${dato(sen.vibracion)} · riesgo enfrente ${dato(sen.riesgo_enfrente)}`;
}

async function refrescarPaneles() {
  const p = await llamar("GET", "/paneles");
  dibujarSeguro("paneles", () => {
    if (p) pintarPaneles(p);
  });
  await refrescarHistorial();
  actualizarRecomendacion();                            // las recomendaciones eran de la celda anterior
  // Los gráficos solo se piden si el panel está abierto
  if (!document.getElementById("graficos").classList.contains("plegado")) await refrescarGraficos();
  marcarDesbordes();
  if (panelIA) panelIA.actualizar();                    // el panel de IA muestra la decisión real del paso (/ia/paso)
  if (defensa) defensa.alPaso();                         // la defensa guiada actualiza sus cifras en vivo
  seguirPasoLaboratorio();                               // y el laboratorio abierto la sigue en vivo si su casilla está marcada
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
  if (sobre && !calorSobreTolerancia) registrarEvento(`aviso: temperatura interna sobre la tolerancia (${datos.tolerancia} °C)${nota}`);
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
  if (datos && Array.isArray(datos.eventos_del_paso) && datos.eventos_del_paso.some((x) => x && x.nombre === "meteorito")) revisarLogro({ tipo: "meteorito" });
  aplicarMoviles(datos, scene, alturaTerreno, (texto) => avisar(texto), agregarGrietas);
  señalarEventosDelPaso(datos);
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
  // «qué cambia al jugar aquí»: los datos del motor de este planeta (GET /planetas → mecanicas)
  const ficha = document.getElementById("menu-planeta-ficha");
  if (ficha) ficha.textContent = p && p.mecanicas ? textoQueCambia(p.mecanicas, p.nombre) : "";
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
const planetasListos = poblarPlanetas();   // la intro espera a /planetas para rellenar el asistente

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
  document.getElementById("hist-total").textContent = plural(datos.total, "fila", "filas");
  const cuerpo = document.getElementById("hist-cuerpo");
  cuerpo.replaceChildren();
  for (const f of datos.filas.slice(-200)) {
    const tr = document.createElement("tr");
    for (const texto of [f.n, nombreModo(f.modo), f.accion, nombreTecnica(f.tecnica), nombresMotivos((f.motivo || "").split(";")) || "-", valoresClave(f)]) {
      const td = document.createElement("td");
      td.textContent = String(texto);
      if (texto === nombresMotivos((f.motivo || "").split(";")) && f.motivo) td.title = `Códigos del motor: ${f.motivo}`;
      tr.appendChild(td);
    }
    cuerpo.appendChild(tr);
  }
}

async function refrescarEstado() {
  const datos = await llamar("GET", "/estado");
  if (!datos) return;
  estado = datos;
  revisarEstadoLogros(datos);   // logros: solo lee el estado, no bloquea
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
  // 22/11: el anillo solo llegaba con el evento de /moviles del mismo paso; si se lo saltó (reproducción en marcha o
  // recarga de la página), se dibuja aquí desde /estado.senal
  if (Array.isArray(datos.senal) && !efectos.senalDibujada()) {
    const [f, c] = datos.senal, x = c + 0.5, z = f + 0.5;
    efectos.marcarSenalBiologica(scene, [x, alturaTerreno(x, z), z]);
  }
  if ("senal" in datos && ultimosObjetivos) pintarObjetivos(ultimosObjetivos);   // la línea de señal sigue a /estado
}

// Control de eventos (ARX-30e): mismo orden que EVENTOS de la API; solo con partida en curso
function actualizarControlEvento() {
  const boton = document.getElementById("evento-disparar");
  if (!boton) return;
  boton.disabled = !mapa || !estado || estado.sin_partida || ESTADOS_TERMINALES.includes(estado.estado);
}
// ---------- señal visible de cada evento (ronda 23) ----------
// Todo evento lanzado deja: una marca en la celda afectada (o sobre el vehículo si es global), un aviso con su ubicación y, si
// queda fuera de cuadro, una flecha en el borde del hueco libre y un breve encuadre de la cámara.
const marcasEvento = crearMarcasEvento({ THREE, escena: scene, altura: (x, z) => alturaTerreno(x, z) });
const etiquetaEvento = document.getElementById("evento-etiqueta");
let textoEtiquetaEvento = "";
let encuadreEvento = null;   // { punto, hasta }: mientras dura, la cámara sigue este punto y no al vehículo
const _vEvento = new THREE.Vector3();
function celdaVehiculo() { return estado && Array.isArray(estado.posicion) ? estado.posicion : null; }
// Zona de la pantalla que dejan libre la columna, el panel de IA y la franja inferior (la misma que usa encuadrarVista)
function huecoLibre() {
  const W = window.innerWidth, H = window.innerHeight;
  let l = 8, r = W - 8, t = 60, b = H - 8;
  if (!document.body.classList.contains("cine")) {
    const col = document.getElementById("columna"), dock = document.getElementById("dock");
    if (col && col.getClientRects().length > 0 && W > 760) l = col.getBoundingClientRect().right + 8;
    if (panelIA && !panelIA.elemento.classList.contains("oculto") && W > 760) r = W - panelIA.ancho - 20;
    if (dock && dock.getClientRects().length > 0) b = Math.min(b, dock.getBoundingClientRect().top - 8);
  }
  if (r - l < 120 || b - t < 120) return { l: 8, r: W - 8, t: 8, b: H - 8 };
  return { l, r, t, b };
}
// Posición en pantalla de un punto del mundo y si queda fuera del hueco libre (o detrás de la cámara)
function proyectarEvento(pos) {
  _vEvento.copy(pos).project(camara);
  const W = window.innerWidth, H = window.innerHeight, h = huecoLibre();
  const x = ((_vEvento.x + 1) / 2) * W, y = ((1 - _vEvento.y) / 2) * H, detras = _vEvento.z > 1;
  return { x, y, detras, h, fuera: detras || x < h.l || x > h.r || y < h.t || y > h.b };
}
function encuadrarEventoEn(punto, ms) {
  if (modoCamara !== "orbita" || cineVivo()) return;   // los modos con el vehículo y el director mandan sobre la cámara
  encuadreEvento = { punto: punto.clone(), hasta: performance.now() + ms };
  camaraSiguiendo = true;
}
// Marca el evento en la escena. celdas: [[fila, columna]]; sin celdas, sobre el vehículo
function señalarEvento(nombre, celdas, { encuadrar = true, renovar = true } = {}) {
  const info = MARCA_EVENTO[nombre];
  if (!info) return;
  const enCelda = info.sobre === "celda" && celdas.length > 0;
  const n = marcasEvento.marcar({ celdas: enCelda ? celdas : [], puntos: enCelda ? [] : [grupoRover.position], rotulo: info.rotulo, color: info.color, renovar });
  if (!n) return;
  const donde = enCelda ? ubicacionEvento(celdas[0], celdaVehiculo(), vehiculoDe(estado && estado.modo_planeta)) : "";
  textoEtiquetaEvento = donde ? `${info.rotulo} · ${donde.replace(/^fila \d+, columna \d+ · /, "")}` : info.rotulo;
  const m = marcasEvento.principal();
  if (encuadrar && enCelda && m && proyectarEvento(m.base).fuera) encuadrarEventoEn(m.base.clone().lerp(grupoRover.position, 0.35), 2600);
}
// Rótulo y flecha: sobre la marca si se ve; en el borde del hueco libre apuntando hacia ella si queda fuera de cuadro
function actualizarEtiquetaEvento() {
  if (!etiquetaEvento) return;
  const m = marcasEvento.principal();
  if (!m || document.body.classList.contains("cine")) { if (!etiquetaEvento.classList.contains("oculto")) etiquetaEvento.classList.add("oculto"); return; }
  const base = proyectarEvento(m.base), arriba = proyectarEvento(m.pos);
  const p = base.fuera ? base : arriba;
  let x = p.x, y = p.y, ang = 0;
  if (base.fuera) {
    const h = base.h, cx = (h.l + h.r) / 2, cy = (h.t + h.b) / 2;
    let dx = base.x - cx, dy = base.y - cy;
    if (base.detras) { dx = -dx; dy = -dy; }
    if (Math.abs(dx) < 1e-3 && Math.abs(dy) < 1e-3) dy = 1;
    const k = Math.min(((h.r - h.l) / 2 - 70) / Math.max(Math.abs(dx), 1e-3), ((h.b - h.t) / 2 - 18) / Math.max(Math.abs(dy), 1e-3));
    x = cx + dx * k; y = cy + dy * k; ang = Math.atan2(dy, dx);
  }
  etiquetaEvento.classList.remove("oculto");
  etiquetaEvento.classList.toggle("fuera", base.fuera);
  etiquetaEvento.style.setProperty("--ang", `${ang}rad`);
  etiquetaEvento.style.setProperty("--color", `#${m.color.toString(16).padStart(6, "0")}`);
  etiquetaEvento.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, ${base.fuera ? "-50%" : "-100%"})`;
  const texto = etiquetaEvento.querySelector(".ev-texto");
  if (texto.textContent !== textoEtiquetaEvento) texto.textContent = textoEtiquetaEvento;
}
etiquetaEvento.addEventListener("click", () => {
  const m = marcasEvento.principal();
  if (m) encuadrarEventoEn(m.base, 3500);
});
// Meteorito y sismo que genera la propia partida (no solo los del panel): también llevan marca
function señalarEventosDelPaso(datos) {
  if (!datos || !Array.isArray(datos.eventos_del_paso)) return;
  for (const ev of datos.eventos_del_paso) {
    const nombre = ev && typeof ev.nombre === "string" ? ev.nombre : "";
    if ((nombre === "meteorito" || nombre === "sismo") && MARCA_EVENTO[nombre]) {
      const celdas = celdasDeEvento(nombre, { celdas: ev.celdas });
      if (celdas.length) señalarEvento(nombre, celdas, { encuadrar: false, renovar: false });
    }
  }
}
function destellarBateria() {
  const b = document.getElementById("h-bateria-barra");
  if (!b) return;
  b.classList.remove("destello"); void b.offsetWidth; b.classList.add("destello");
}

async function dispararEvento(nombreForzado = null) {
  if (finActiva()) return;
  const nombre = typeof nombreForzado === "string" ? nombreForzado : document.getElementById("evento-nombre").value;
  const opcion = [...document.getElementById("evento-nombre").options].find((o) => o.value === nombre);
  const rotuloEvento = opcion ? opcion.textContent : nombre;   // «falla de sensor», no «falla_sensor»
  // Antes un evento ignorado no decía nada: ahora se explica por qué no se lanzó
  if (!mapa || !estado || estado.sin_partida) { avisar(`Evento ${rotuloEvento} sin efecto: no hay una partida en curso.`); return; }
  if (ESTADOS_TERMINALES.includes(estado.estado)) { avisar(`Evento ${rotuloEvento} sin efecto: la misión ya terminó.`); return; }
  if (ocupado()) { avisar(`Evento ${rotuloEvento} sin efecto: ${pausaActiva ? "la partida está en pausa" : "hay una operación en curso"}; inténtalo de nuevo.`); return; }
  const r = await llamar("POST", "/evento", { nombre });
  if (!r) return;
  const texto = avisoEvento(nombre, rotuloEvento, r, celdaVehiculo(), vehiculoDe(estado.modo_planeta));
  if (nombre === "barranco" && r.ok) revisarLogro({ tipo: "barranco" });
  if (r.ok) {
    const celdas = celdasDeEvento(nombre, r);
    if (nombre === "barranco" && celdas.length) animarBarranco(celdas);
    if (nombre !== "senal_biologica") señalarEvento(nombre, celdas);   // la señal se marca con su celda real al refrescar el estado
    if (nombre === "bateria_baja") destellarBateria();
  }
  avisar(texto);
  if (r.ok) avisarAccion("evento");
  registrarEvento(texto.charAt(0).toLowerCase() + texto.slice(1));
  await refrescarEstado();
  if (r.ok && nombre === "senal_biologica" && estado && Array.isArray(estado.senal)) señalarEvento(nombre, [estado.senal]);
  await refrescarPaneles();
}
document.getElementById("evento-disparar").addEventListener("click", () => dispararEvento());

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
  const p = perfilPlaneta(planeta);   // aspecto de la escena (planeta_datos.js); PALETAS_PLANETA solo queda para el color de los planetas de la intro
  document.querySelector("#hud h1").textContent = `ARES-X · ${planeta}`;
  if (grupoMapa.children[0] && grupoMapa.children[0].material) grupoMapa.children[0].material.color.setHex(p.suelo);
  materiales.roca.color.setHex(p.roca);      // rocas del planeta: Marte café rojizo, Mercurio gris
  materiales.borde.color.setHex(p.borde);
  materiales.guijarro.color.setHex(p.guijarro);
  materialCielo.uniforms.arriba.value.set(...p.arriba);
  materialCielo.uniforms.horizonte.value.set(...p.horizonte);
  scene.fog.color.setHex(p.niebla);
  sol.color.setHex(p.sol);
  sol.intensity = p.intensidadSol;
  luzCielo.groundColor.setHex(p.niebla).multiplyScalar(0.55);
  luzCielo.color.setRGB(p.arriba[0], p.arriba[1], p.arriba[2]).lerp(new THREE.Color(0xdfe8ff), 0.6);
  aplicarCondiciones(estado, true);
}

// ---------- condiciones del planeta (gravedad, viento, hielo) ----------
// Único punto donde se leen: planeta_datos.condicionesPlaneta(/estado.planeta_mecanicas: perfil + estado vivo del motor).
// De aquí salen el bloque del HUD (ráfaga actual, dirección, resbalones, batería extra), las partículas de viento, los
// centelleos y las celdas de hielo reales (GET /hielo) pintadas sobre el suelo.
const ambientePlaneta = crearAmbientePlaneta({ THREE, escena: scene, altura: (x, z) => alturaTerreno(x, z), camara, renderer });
let condicionesActuales = null, firmaCondiciones = "", planetaCondiciones = "";
let capaHielo = null, claveHielo = "", hieloEnVuelo = false;
function reiniciarCondiciones() { firmaCondiciones = ""; planetaCondiciones = ""; condicionesActuales = null; claveHielo = ""; }
function liberarCapaHielo() {
  if (!capaHielo) return;
  scene.remove(capaHielo); capaHielo.geometry.dispose(); capaHielo.material.dispose(); capaHielo.dispose(); capaHielo = null;
}
// Celdas de hielo del motor (parches fijos por partida) como baldosas translúcidas sobre el suelo
async function cargarCapaHielo(clave) {
  if (hieloEnVuelo || clave === claveHielo) return;
  hieloEnVuelo = true; claveHielo = clave;
  try {
    const h = await llamar("GET", "/hielo");
    if (clave !== claveHielo) return;
    liberarCapaHielo();
    const celdas = h && Array.isArray(h.celdas) ? h.celdas.filter((c) => Array.isArray(c) && c.length >= 2) : [];
    if (!celdas.length) return;
    const geo = new THREE.PlaneGeometry(0.94, 0.94); geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({ color: 0xcdf3ff, transparent: true, opacity: 0.34, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, toneMapped: false });
    const malla = new THREE.InstancedMesh(geo, mat, celdas.length);
    const m4 = new THREE.Matrix4();
    celdas.forEach(([f, c], i) => { const x = c + 0.5, z = f + 0.5; m4.makeTranslation(x, alturaTerreno(x, z) + 0.07, z); malla.setMatrixAt(i, m4); });
    malla.instanceMatrix.needsUpdate = true; malla.renderOrder = 2; malla.name = "capa-hielo"; malla.frustumCulled = false;
    capaHielo = malla; scene.add(malla);
  } catch (err) { console.warn("hielo: no se pudieron dibujar las celdas", err); }
  finally { hieloEnVuelo = false; if (clave !== claveHielo) cargarCapaHielo(claveHielo); }
}
function aplicarCondiciones(e, forzar = false) {
  const planeta = (e && e.planeta) || planetaActivo;
  const c = condicionesPlaneta(e, planeta);
  const firma = `${planeta}|${e && e.paso}|${JSON.stringify(c)}`;   // el paso entra en la firma: «este paso +x %» no queda viejo
  if (!forzar && firma === firmaCondiciones) return;
  const delta = deltaPaso(planeta === planetaCondiciones ? condicionesActuales : null, c);   // sobrecoste del paso y resbalón: dos lecturas del mismo mapa
  const mismoMapa = planeta === planetaCondiciones && !forzar;
  firmaCondiciones = firma; condicionesActuales = c; planetaCondiciones = planeta;
  ambientePlaneta.configurar(planeta, c, { conservar: mismoMapa });
  const suelo = grupoMapa.children[0];   // hielo: el suelo se vuelve más liso y brilla bajo el sol
  if (suelo && suelo.material && suelo.material.isMeshStandardMaterial) {
    suelo.material.roughness = 0.95 - 0.5 * c.hielo.nivel;
    suelo.material.metalness = 0.12 * c.hielo.nivel;
  }
  if (mapa && c.vivo.hay) cargarCapaHielo(`${e && e.semilla}|${planeta}|${mapa.filas}x${mapa.columnas}|${c.hielo.fraccion}`);
  if (capaHielo) capaHielo.visible = c.hielo.fraccion > 0;
  const caja = document.getElementById("condiciones");
  if (!caja) return;
  const filas = caja.querySelector(".cond-filas");
  filas.replaceChildren(...filasCondiciones(c, delta).map(([etiqueta, valor, fuente]) => {
    const f = document.createElement("div"); f.className = "fila";
    const a = document.createElement("span"); a.textContent = etiqueta;
    const v = document.createElement("span"); v.className = "valor"; v.textContent = valor;
    v.title = fuente === "motor" ? "Dato del motor" : "Valor aproximado: todavía no hay partida que lo confirme";
    f.append(a, v);
    if (etiqueta === "¡Resbaló!") f.classList.add("cond-alerta");
    if (fuente !== "motor") { const r = document.createElement("small"); r.className = "cond-ref"; r.textContent = "aprox."; v.append(" ", r); }
    return f;
  }));
  const firma2 = caja.querySelector(".cond-firma");
  if (firma2) firma2.textContent = perfilPlaneta(planeta).firma;
}

// Lo último que confirmó el motor: planeta y tipo de vehículo
let vigente = { planeta: null, vehiculo: null };
// Viaje entre planetas (solo cliente: no escribe nada en el motor). Preferencia en localStorage («ares.viaje»), activado por defecto
let viaje = null;
let viajePendiente = null;   // { desde, hacia } cuando la partida nueva cambió de planeta
function viajeActivado() {
  try { return localStorage.getItem("ares.viaje") !== "0"; } catch (e) { return true; }
}
function fijarViajeActivado(on) {
  try { localStorage.setItem("ares.viaje", on ? "1" : "0"); } catch (e) { /* sin almacenamiento */ }
  document.querySelectorAll(".casilla-viaje").forEach((c) => { c.checked = on; });
}
document.querySelectorAll(".casilla-viaje").forEach((c) => {
  c.checked = viajeActivado();
  c.addEventListener("change", () => fijarViajeActivado(c.checked));
});
let tarjetaViaje = null;
// Vuelo de carga: el cohete despega antes de pedir la partida y aterriza cuando el motor responde (avance ligado a la carga real).
// Devuelve un control { terminar(ok) } o null si la animación está apagada o no se pudo preparar (la carga sigue con la barra simple).
// Nunca lanza: si algo falla, la partida sigue igual.
async function abrirVuelo(destino, { alOmitir = null } = {}) {
  if (!viajeActivado()) return null;
  try {
    // Carga perezosa: si un módulo del vuelo no carga, la partida sigue igual (con import estático rompería toda la app)
    const [datosV, { crearViaje }, { crearTarjetaViaje }] = await Promise.all([
      import("/static/viaje_datos.js?v=r14"), import("/static/viaje3d.js?v=r14"), import("/static/viaje_tarjeta.js?v=r14")]);
    const { datosTarjeta, modoMovimiento, origenVuelo, pasoCarga, etapaCarga, textoEtapa, CIERRE_ESTATICO_S } = datosV;
    const reducido = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const modo = modoMovimiento(reducido, true);
    if (modo === "ninguno") return null;
    const desde = origenVuelo(vigente.planeta, destino);
    if (!tarjetaViaje) tarjetaViaje = crearTarjetaViaje(document.body);
    const datos = datosTarjeta(desde, destino, planetasDatos);
    let omitido = false, aterrizaje = null, intervalo = null, listoReducido = false;
    const alProgreso = (d, etapa) => tarjetaViaje.progreso(d, textoEtapa(etapa, desde, destino));
    document.body.classList.add("vuelo-activo");
    if (modo === "tarjeta") {
      // Movimiento reducido: sin 3D; la barra sigue la carga real y la tarjeta se cierra al terminar
      tarjetaViaje.mostrar(datos, { manual: true, alOmitir: () => omitir() });
      const t0 = performance.now(); let d = 0, tPrev = t0;
      intervalo = setInterval(() => {
        const ahora = performance.now(); d = pasoCarga(d, (ahora - t0) / 1000, listoReducido, (ahora - tPrev) / 1000); tPrev = ahora;
        alProgreso(d, etapaCarga(d));
      }, 100);
    } else {
      viaje = crearViaje({ THREE, renderer, texturaPlaneta: texturaParaPlaneta, paleta: PALETAS_PLANETA, alProgreso });
      tarjetaViaje.mostrar(datos, { manual: true, alOmitir: () => omitir() });
      aterrizaje = viaje.iniciar(desde, destino);
    }
    // Omitir: se cierra el vuelo enseguida y la app muestra la barra simple hasta que el motor responda
    function omitir() {
      if (omitido) return;
      omitido = true;
      try { if (viaje) viaje.omitir(); } catch (e) { /* ya terminado */ }
      cerrar();
      try { if (alOmitir) alOmitir(); } catch (e) { /* sin barra */ }
    }
    function cerrar() {
      clearInterval(intervalo);
      document.body.classList.remove("vuelo-activo");
      try { tarjetaViaje.ocultar(); } catch (e) { /* ya oculta */ }
      try { if (viaje) viaje.dispose(); } catch (e) { /* ya liberado */ }
      viaje = null;
    }
    return {
      get omitido() { return omitido; },
      async terminar(ok) {
        try {
          if (!ok || omitido) return;
          revisarLogro({ tipo: "viaje", desde, hacia: vigente.planeta || destino });
          if (aterrizaje && viaje) {
            viaje.listo();
            let guarda = null;
            await Promise.race([aterrizaje, new Promise((r) => { guarda = setTimeout(() => { console.warn("viaje: temporizador de guarda"); r(); }, 8000); })]);
            clearTimeout(guarda);
          } else if (modo === "tarjeta") {
            listoReducido = true;
            await new Promise((r) => { const fin = setTimeout(r, Math.min(CIERRE_ESTATICO_S * 1000, 1200)); tarjetaViaje.mostrar(datos, { manual: true, alOmitir: () => { clearTimeout(fin); r(); } }); tarjetaViaje.progreso(1, textoEtapa("aterrizado", desde, destino)); });
          }
        } catch (e) {
          console.warn("viaje: fallo al aterrizar, sigue la partida", e);
        } finally {
          cerrar();
        }
      },
    };
  } catch (e) {
    console.warn("viaje: fallo, sigue la partida normal", e);
    document.body.classList.remove("vuelo-activo");
    try { if (viaje) viaje.dispose(); } catch (e2) { /* ya liberado */ }
    viaje = null;
    return null;
  }
}
// Introducción con el sistema solar = pantalla de inicio (solo cliente: no escribe nada en el motor). Aparece al abrir la app, al volver al inicio
// y al salir de una partida. Preferencia en localStorage («ares.intro», activada por defecto; apagada = se va directo al asistente).
// Elegir un planeta solo rellena el asistente: la partida empieza con «Iniciar».
let intro = null;
let introCorriendo = false;
let tarjetaIntro = null;
let generacionInicio = 0;   // sube al salir de una partida: un /paso en vuelo que llegue después no pinta nada
function introActivada() {
  try { return localStorage.getItem("ares.intro") !== "0"; } catch (e) { return true; }
}
function fijarIntroActivada(on) {
  try { localStorage.setItem("ares.intro", on ? "1" : "0"); } catch (e) { /* sin almacenamiento */ }
  document.querySelectorAll(".casilla-intro").forEach((c) => { c.checked = on; });
}
document.querySelectorAll(".casilla-intro").forEach((c) => {
  c.checked = introActivada();
  c.addEventListener("change", () => fijarIntroActivada(c.checked));
});
// Todos los caminos que llevan al asistente de inicio pasan por aquí: deja la partida en pausa y limpia, abre el asistente y muestra el sistema solar.
function volverAlInicio(motivo = "salir") {
  generacionInicio += 1;
  cerrarAvisos();            // meta, pausa, avisos; con pausaActiva = false
  detenerReproduccion();
  cadenaAutomatica = null;
  document.getElementById("controles").classList.add("oculto");
  document.getElementById("manual").classList.add("oculto");
  document.getElementById("menu").classList.remove("oculto");
  tutorial.cerrar(); tutorial.cerrarOferta();
  if (panelIA) panelIA.mostrar(false);
  correrIntro({ motivo });
}
// motivo: «abrir» | «inicio» | «salir» | «manual» («Ver intro», ignora la casilla). Si algo falla, el asistente sigue igual (nunca lanza ni se queda colgado).
async function correrIntro({ motivo = "abrir" } = {}) {
  if (introCorriendo) return;
  let guarda = null, inactividad = null, limpiarActividad = null;
  const controlesAntes = controles.enabled;
  introCorriendo = true;
  try {
    const reducido = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    const webgl = !!(renderer && renderer.getContext && renderer.getContext());
    const { debeMostrarIntro, elegirCuerpo, datosCuerpo, GUARDA_PRIMER_CUADRO_S, CIERRE_INACTIVIDAD_S } = await import("/static/intro_datos.js?v=r14");
    if (!debeMostrarIntro({ motivo, activada: introActivada(), reducido, webgl })) return;
    if (!webgl || !planetasDatos) return;
    const [{ crearIntro }, { crearTarjetaIntro }] = await Promise.all([import("/static/intro3d.js?v=r14"), import("/static/intro_tarjeta.js?v=r14")]);
    if (!tarjetaIntro) tarjetaIntro = crearTarjetaIntro(document.body);
    controles.enabled = false;   // la cámara de la partida no se mueve mientras dura la intro
    document.body.classList.add("intro-activa");   // oculta los paneles de la app mientras dura (CSS)
    await new Promise((resolver) => {
      let hecho = false;
      const fin = () => { if (hecho) return; hecho = true; resolver(); };
      try {
        intro = crearIntro({
          THREE, renderer, OrbitControls, texturaPlaneta: texturaParaPlaneta, paleta: PALETAS_PLANETA, reducido,
          alElegir: (nombre) => {
            const r = elegirCuerpo(nombre, planetasDatos);
            if (r) {
              document.getElementById("menu-planeta").value = r.planeta;
              document.getElementById("menu-modo-planeta").value = r.modo;
              validarPlaneta();
            }
          },
          alPasar: (nombre) => tarjetaIntro.cuerpo(nombre ? datosCuerpo(nombre, planetasDatos) : null),
        });
      } catch (e) { console.warn("intro: no se pudo crear la escena; sigue el asistente", e); fin(); return; }
      tarjetaIntro.mostrar({ activada: introActivada(), alOmitir: () => { if (intro) intro.omitir(); fin(); }, alCambiarCasilla: fijarIntroActivada });
      intro.iniciar().then(fin, fin);
      guarda = setTimeout(() => { if (intro && !intro.primerCuadro) { console.warn("intro: temporizador de guarda"); intro.omitir(); fin(); } }, GUARDA_PRIMER_CUADRO_S * 1000);
      const reiniciarInactividad = () => {
        clearTimeout(inactividad);
        inactividad = setTimeout(() => { console.warn("intro: cierre por inactividad"); if (intro) intro.omitir(); fin(); }, CIERRE_INACTIVIDAD_S * 1000);
      };
      reiniciarInactividad();
      window.addEventListener("pointermove", reiniciarInactividad); window.addEventListener("keydown", reiniciarInactividad);
      limpiarActividad = () => { window.removeEventListener("pointermove", reiniciarInactividad); window.removeEventListener("keydown", reiniciarInactividad); };
    });
  } catch (e) {
    console.warn("intro: fallo, sigue el asistente", e);
  } finally {
    clearTimeout(guarda); clearTimeout(inactividad);
    if (limpiarActividad) limpiarActividad();
    controles.enabled = controlesAntes;
    document.body.classList.remove("intro-activa");
    try { if (tarjetaIntro) tarjetaIntro.ocultar(); } catch (e) { /* ya oculta */ }
    try { if (intro) intro.dispose(); } catch (e) { /* ya liberado */ }
    intro = null;
    introCorriendo = false;
  }
}
const botonVerIntro = document.getElementById("menu-ver-intro");
if (botonVerIntro) botonVerIntro.addEventListener("click", () => { correrIntro({ motivo: "manual" }); });

// Pantalla final (solo cliente: no escribe nada en el motor). Preferencia en localStorage («ares.final», activada por defecto).
// Puntaje de juego, estrellas, logros y mejores momentos; si algo falla, se abre la meta como siempre.
let tarjetaFinal = null;
let finCorriendo = false;
let cerrarFinal = null;                    // cierra la pantalla abierta con la acción pedida (null = continuar a la meta)
let accionFinal = null;                    // «repetir» | «otro» | null, según el botón con que se cerró
let logrosPantalla = null;                 // módulo de logros ya creado (carga perezosa)
let promesaLogros = null;
let colaLogros = Promise.resolve();        // los eventos de logros se evalúan en orden
let logrosNuevos = [];                     // desbloqueados desde la última pantalla final
let momentosPantalla = null;               // capturas de la partida en curso
let promesaMomentos = null;
function finActiva() { return document.body.classList.contains("final-activa"); }   // con la pantalla final abierta, los atajos de la partida no responden
function finActivada() {
  try { return localStorage.getItem("ares.final") !== "0"; } catch (e) { return true; }
}
function fijarFinActivada(on) {
  try { localStorage.setItem("ares.final", on ? "1" : "0"); } catch (e) { /* sin almacenamiento */ }
  document.querySelectorAll(".casilla-final").forEach((c) => { c.checked = on; });
}
document.querySelectorAll(".casilla-final").forEach((c) => {
  c.checked = finActivada();
  c.addEventListener("change", () => fijarFinActivada(c.checked));
});
function cargarLogros() {
  if (!promesaLogros) {
    promesaLogros = import("/static/final_logros.js?v=r14").then(({ crearLogros }) => {
      logrosPantalla = crearLogros({ contenedor: document.body, alDesbloquear: (l) => { logrosNuevos.push(l); } });
      return logrosPantalla;
    }).catch((e) => { console.warn("logros: no se pudo cargar el módulo", e); return null; });
  }
  return promesaLogros;
}
// Evalúa un evento de logro sin bloquear nada: si el módulo falla, el juego sigue igual.
function revisarLogro(evento) {
  colaLogros = colaLogros.then(() => cargarLogros()).then((l) => { if (l) l.revisar(evento); }).catch(() => { /* el juego no depende de los logros */ });
}
function revisarEstadoLogros(datos) {
  colaLogros = colaLogros.then(() => cargarLogros()).then((l) => { if (l) l.revisarEstado(datos); }).catch(() => { /* idem */ });
}
function cargarMomentos() {
  if (!promesaMomentos) {
    promesaMomentos = import("/static/final_momentos.js?v=r14").then(({ crearMomentos }) => {
      momentosPantalla = crearMomentos({ canvas: renderer.domElement, dibujar: () => renderer.render(scene, camara) });
      return momentosPantalla;
    }).catch((e) => { console.warn("momentos: no se pudo cargar el módulo", e); return null; });
  }
  return promesaMomentos;
}
function momentosEnPaso(r) {
  if (!finActivada() || (intro && intro.activo) || (viaje && viaje.activo)) return;
  cargarMomentos().then((m) => {
    if (!m) return;
    const riesgo = estado && estado.sensores ? estado.sensores.riesgo_enfrente : null;
    m.alPaso({ paso: ultimoPasoNumero, motivos: r && r.motivos, riesgo });
  }).catch(() => { /* sin capturas */ });
}
document.getElementById("pausa-borrar-logros").addEventListener("click", async () => {
  const l = await cargarLogros();
  if (l) { l.borrar(); logrosNuevos = []; avisar("Logros borrados de este navegador."); }
});
// Laboratorios y comparación de políticas: solo se cuentan las aperturas
document.getElementById("abrir-laboratorio").addEventListener("click", () => revisarLogro({ tipo: "laboratorio", id: "ag" }));
document.querySelectorAll(".lab-tab").forEach((b) => b.addEventListener("click", () => revisarLogro({ tipo: "laboratorio", id: b.dataset.lab })));

// Muestra la pantalla final antes de la meta. Nunca lanza ni se queda colgada: la meta se abre siempre (la llama alFinDeMision).
async function correrFinal(codigo) {
  if (finCorriendo) return;
  accionFinal = null;
  let inactividad = null, limpiarActividad = null;
  try {
    const { debeMostrarFinal, normalizarResultado, CIERRE_INACTIVIDAD_S } = await import("/static/final_datos.js?v=r14");
    const reducido = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    if (!debeMostrarFinal({ activada: finActivada(), reducido, terminal: ESTADOS_TERMINALES.includes(codigo) })) return;
    finCorriendo = true;
    const { crearFinal } = await import("/static/final_tarjeta.js?v=r14");
    await colaLogros;                                 // los logros del último paso ya están evaluados
    const m = await cargarMomentos();
    if (m && estado) m.alFinal({ paso: ultimoPasoNumero, codigo });
    const logros = await cargarLogros();
    const resultado = normalizarResultado(estado);
    await new Promise((resolver) => {
      let hecho = false;
      const fin = (accion = null) => { if (hecho) return; hecho = true; accionFinal = accion; resolver(); };
      // «Volver a jugar» y «Explorar otro cuerpo» reutilizan la lógica de la meta y del asistente (se ejecutan después de cerrar la pantalla)
      cerrarFinal = fin;
      if (!tarjetaFinal) {
        tarjetaFinal = crearFinal({
          contenedor: document.body,
          alContinuar: () => cerrarFinal && cerrarFinal(null),
          alCerrar: () => cerrarFinal && cerrarFinal(null),
          alRepetir: () => cerrarFinal && cerrarFinal("repetir"),
          alOtroPlaneta: () => cerrarFinal && cerrarFinal("otro"),
          alVerRecords: () => abrirRecords({ semilla: estado ? estado.semilla : "" }),
        });
      }
      document.body.classList.add("final-activa");
      tarjetaFinal.mostrar(resultado, m ? m.lista() : [], {
        logrosNuevos: [...logrosNuevos], logros: logros ? logros.lista() : [], activada: finActivada(), alCambiarCasilla: fijarFinActivada,
        record: textoNuevoRecord(ultimoRecord),
      });
      const reiniciarInactividad = () => {
        clearTimeout(inactividad);
        inactividad = setTimeout(() => { console.warn("final: cierre por inactividad"); fin(); }, CIERRE_INACTIVIDAD_S * 1000);
      };
      reiniciarInactividad();
      window.addEventListener("pointermove", reiniciarInactividad); window.addEventListener("keydown", reiniciarInactividad);
      limpiarActividad = () => { window.removeEventListener("pointermove", reiniciarInactividad); window.removeEventListener("keydown", reiniciarInactividad); };
    });
  } catch (e) {
    accionFinal = null;
    console.warn("final: fallo, se abre la meta", e);
  } finally {
    clearTimeout(inactividad);
    if (limpiarActividad) limpiarActividad();
    document.body.classList.remove("final-activa");
    try { if (tarjetaFinal) tarjetaFinal.ocultar(); } catch (e) { /* ya oculta */ }
    logrosNuevos = [];
    try { if (momentosPantalla) momentosPantalla.reiniciar(); } catch (e) { /* sin capturas */ }
    finCorriendo = false;
  }
}

// Configuración para crear o reiniciar una partida: el planeta y vehículo confirmados, y el modo de control del panel
function configuracionVigente() {
  return {
    planeta: vigente.planeta,
    vehiculo: vigente.vehiculo,
    control: document.getElementById("modo").value,
    veto: document.getElementById("veto").checked,
  };
}
// Una partida nueva vacía TODO el estado derivado de la anterior: bitácora lateral, historial y gráficos, tira de
// decisiones, recomendaciones, panel de IA (gráficos «últimos pasos», decisión y narración), laboratorios y contadores.
function reiniciarEstadoDerivado() {
  document.getElementById("registro").replaceChildren();
  document.getElementById("hist-cuerpo").replaceChildren();
  document.getElementById("hist-total").textContent = "";
  tiraPasos = []; pintarTira();
  filasGraficos = []; cursorGrafico = null; geometriaGrafico = null;
  try { dibujarGrafico(); } catch (e) { /* panel plegado */ }
  recomendacionEpoca += 1;
  document.getElementById("rec-lista").replaceChildren(Object.assign(document.createElement("li"), { textContent: TEXTO_REC_VACIO }));
  ultimoPasoNumero = null; calorSobreTolerancia = false; ultimosObjetivos = null;
  try { reiniciarLaboratorios(); } catch (e) { console.warn("laboratorios: no se pudieron reiniciar", e); }
  try { if (panelIA) panelIA.reiniciar(); } catch (e) { console.warn("panel de IA: no se pudo reiniciar", e); }
  try { document.getElementById("subtitulo-ia") && (document.getElementById("subtitulo-ia").textContent = ""); } catch (e) { /* sin subtítulo */ }
}
// Tamaño del mapa (ARX-21): pequeno 20×30, mediano 30×45, grande 40×60 (por defecto: grande)
async function cargarPartida(semilla, nivel, tamano = document.getElementById("tamano").value || "grande", config = configuracionVigente(), bateria = null) {
  detenerReproduccion();
  finAtendido = false; ultimoRecord = null;
  cerrarAvisos();
  reiniciarEventos();
  cargando = true;
  try {
    const previo = vigente.planeta;   // para el viaje: el planeta de la partida anterior
    viajePendiente = null;
    const cuerpo = { nivel, tamano, planeta: config.planeta, modo: config.vehiculo };
    if (semilla != null) cuerpo.semilla = semilla;
    if (bateria != null) cuerpo.bateria = bateria;   // ARX-87: solo llega desde el botón «Nueva» del panel
    for (const clave of Object.keys(cuerpo)) if (cuerpo[clave] == null) delete cuerpo[clave];   // sin planeta, el motor usa Marte y rover
    let datos = await llamar("POST", "/partida", cuerpo);
    if (!datos) return false;
    // Manda el motor: el planeta y el vehículo que responde son los que se muestran
    vigente = { planeta: datos.planeta, vehiculo: datos.modo_planeta };
    if (previo && datos.planeta && datos.planeta !== previo) viajePendiente = { desde: previo, hacia: datos.planeta };
    planetaActivo = datos.planeta;
    modoPlanetaActivo = datos.modo_planeta;
    // Una partida nueva arranca en manual: se reaplica el modo de control elegido (si no es el manual simple)
    if (config.control && (config.control !== "manual" || config.veto)) {
      const control = await llamar("POST", "/modo", { modo: config.control, veto: config.veto });
      if (!control) return false;
      datos = control;
    }
    estado = datos;
    revisarLogro({ tipo: "inicio", planeta: datos.planeta, modo: datos.modo_planeta });
    if (momentosPantalla) momentosPantalla.reiniciar();
    reiniciarEstadoDerivado();   // lo que se calculó con la misión anterior no puede verse en la nueva
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
    avisar(`Partida nueva en ${planetaActivo}${modoPlanetaActivo === "sonda" ? " (Sonda)" : ""}: semilla ${estado.semilla}, nivel ${NIVELES[nivel - 1]}.`);
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
  if (panelIA) panelIA.mostrar(true);
  document.getElementById("manual").classList.remove("oculto");
  document.getElementById("semilla").value = "";
  document.getElementById("nivel").value = nivel;
  const modo = document.getElementById("modo");
  document.getElementById("resumen-texto").textContent =
    `semilla ${semilla} · nivel ${NIVELES[nivel - 1]} · ${modo.options[modo.selectedIndex].text}`;
}
document.getElementById("reconfigurar").addEventListener("click", () => { volverAlInicio("salir"); });

// Controles manuales plegables (en móvil quedan plegados por defecto)
document.getElementById("manual-toggle").addEventListener("click", (ev) => {
  const manual = document.getElementById("manual");
  manual.classList.toggle("plegado");
  manual.classList.toggle("abierto");
  ev.currentTarget.setAttribute("aria-expanded", String(!manual.classList.contains("plegado")));
});

// Pantalla de carga (ARX-60): vuelo del cohete ligado a la carga real; sin animación, una barra simple. Con transición del vehículo al pulsar «Nueva» o reiniciar
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
// destino: planeta pedido (el del asistente); sin él, el de la partida en curso
async function conCarga(fn, { transicion = false, destino = null } = {}) {
  cerrarAvisos();
  const caja = document.getElementById("carga");
  const texto = document.getElementById("carga-texto");
  const relleno = document.getElementById("carga-relleno");
  if (transicion && grupoRover.children.length) await escalarRover(1, 0, 400);   // el vehículo se encoge
  const barraSimple = () => { texto.textContent = "Preparando la misión…"; relleno.style.width = "45%"; caja.classList.remove("oculto"); };
  const vuelo = await abrirVuelo(destino || vigente.planeta || "Marte", { alOmitir: barraSimple });
  if (!vuelo) barraSimple();
  let ok = false;
  try {
    ok = await fn();
  } catch (err) {
    ok = false;
    avisar("No se pudo iniciar la partida.");
  } finally {
    viajePendiente = null;   // el vuelo de la carga ya mostró el cambio de planeta
    if (vuelo) await vuelo.terminar(ok);
    caja.classList.add("oculto");   // siempre se cierra, también si POST /partida falla
  }
  if (transicion && ok && grupoRover.children.length) await escalarRover(0, 1, 400);   // el nuevo vehículo crece
  return ok;
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
  if (finAtendido) return;
  finAtendido = true;
  detenerReproduccion();
  cerrarAvisos();
  await registrarRecord();   // ronda 23: queda en los récords por semilla (el servidor decide si es nuevo récord)
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
    avisar(`Misión terminada (${nombreEstado(codigo)}). La siguiente empieza en 3 s…`);
    await esperar(3000);   // sin preguntar: espera 3 s y sigue con la siguiente
    const { nivel, veto } = cadenaAutomatica;
    // Misma configuración con la que se arrancó la cadena, no la que muestre el panel en ese momento
    const config = { planeta: vigente.planeta, vehiculo: vigente.vehiculo, control: "automatico", veto };
    const ok = await conCarga(() => cargarPartida(null, nivel, undefined, config), { destino: config.planeta });
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
  await correrFinal(codigo);   // la pantalla final va antes de la meta; nunca lanza y, si falla o se omite, sigue la meta
  const pedido = accionFinal; accionFinal = null;
  if (pedido === "jugar" && configPendiente) { const c = configPendiente; configPendiente = null; cadenaAutomatica = null; await jugarConfiguracion(c); return; }
  if (pedido === "repetir") { cadenaAutomatica = null; await nuevaDesdeMeta(estado.semilla, estado.nivel); return; }
  if (pedido === "otro") {
    volverAlInicio("salir");   // «Explorar otro cuerpo»: de vuelta al sistema solar
    return;
  }
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

// Pantalla de meta combinada: mapa y dificultad se eligen sin actuar; «Iniciar la misión elegida» arranca lo elegido
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
  // Resumen de la misión que acaba de terminar: pasos, puntaje y batería (el puntaje explica cómo se calcula)
  const resumenLista = document.getElementById("meta-resumen");
  resumenLista.replaceChildren(...resumenMeta(estado).map(([nombre, valor]) => {
    const li = document.createElement("li");
    li.textContent = `${nombre}: ${valor}`;
    return li;
  }));
  const rec = textoNuevoRecord(ultimoRecord);
  if (rec) { const li = document.createElement("li"); li.textContent = `${rec.nuevo ? "★ " : ""}${rec.titulo}`; if (rec.nuevo) li.className = "nuevo-record"; li.title = rec.detalle; resumenLista.appendChild(li); }
  document.getElementById("meta-puntaje-ayuda").textContent = AYUDA_PUNTAJE_SIMPLE;
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
    : codigo === "EXITO" ? "¡Meta alcanzada!" : `Misión terminada: ${nombreEstado(codigo)}`;
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
document.getElementById("meta-salir").addEventListener("click", () => { volverAlInicio("salir"); });

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
document.getElementById("pausa-salir").addEventListener("click", () => { volverAlInicio("salir"); });

document.getElementById("menu-modo").addEventListener("change", (ev) => {
  document.getElementById("menu-misiones-fila").classList.toggle("oculto", ev.target.value !== "automatico");
});

// ---------- ronda 23: récords por semilla, comparar políticas y tutorial del modo manual ----------
let ultimoRecord = null;        // respuesta de /records/registrar de la misión que acaba de terminar
let finAtendido = false;        // la misión actual ya pasó por alFinDeMision (los pasos manuales también la terminan)
let configPendiente = null;     // «Jugar esta semilla» pedido desde la pantalla final
let tutorialPendiente = false;  // el botón «Tutorial» del menú arranca una partida manual y abre el recorrido

async function registrarRecord() {
  ultimoRecord = null;
  try {
    const r = await fetch("/records/registrar", { method: "POST" });
    if (r.ok) ultimoRecord = await r.json();
  } catch (e) { /* sin récord: la misión sigue su curso */ }
}
// La misión se puede terminar con un movimiento o un disparo del jugador, no solo con un paso de la IA
function revisarFinManual() {
  if (finAtendido || !estado || !ESTADOS_TERMINALES.includes(estado.estado)) return;
  alFinDeMision(estado.estado);
}

const vistaRecords = crearRecords({ alJugar: (cfg) => jugarConfiguracion(cfg) });
function abrirRecords(opciones = {}) { vistaRecords.abrir(opciones); }
// Empieza una misión con la semilla y las condiciones de un récord, usando el mismo camino que el asistente del menú
async function jugarConfiguracion(cfg) {
  if (finActiva() && cerrarFinal) { configPendiente = cfg; cerrarFinal("jugar"); return; }   // la pantalla final se cierra y después arranca
  const poner = (id, valor) => { const c = document.getElementById(id); c.value = String(valor); c.dispatchEvent(new Event("change")); };
  poner("menu-planeta", cfg.planeta); poner("menu-modo-planeta", cfg.vehiculo); poner("menu-tamano", cfg.tamano);
  poner("menu-nivel", cfg.nivel); poner("menu-modo", cfg.control);
  document.getElementById("menu-semilla").value = String(cfg.semilla);
  cadenaAutomatica = null;
  document.getElementById("iniciar").click();
}

const vistaComparar = crearComparar({
  valores: () => {
    const enPartida = document.getElementById("menu").classList.contains("oculto") && estado && !estado.sin_partida;
    if (enPartida) return { planeta: vigente.planeta, vehiculo: vigente.vehiculo, tamano: document.getElementById("tamano").value, nivel: estado.nivel, semilla: estado.semilla };
    return { planeta: document.getElementById("menu-planeta").value, vehiculo: document.getElementById("menu-modo-planeta").value, nivel: document.getElementById("menu-nivel").value };
  },
  planetas: () => [...document.getElementById("menu-planeta").options].map((o) => [o.value, o.textContent]),
});

// Tutorial: cada paso deja visible el panel que necesita
const tutorial = crearTutorial({
  vehiculo: () => vehiculoDe(vigente.vehiculo || (estado && estado.modo_planeta)),
  preparar: (clave) => {
    const abrir = (id, boton) => { const c = document.getElementById(id); if (c && c.classList.contains("plegado")) document.getElementById(boton).click(); };
    if (clave === "controles") { abrir("manual", "manual-toggle"); abrir("controles", "controles-toggle"); }
    if (clave === "misión" && panelIA) panelIA.abrir("mision");   // los eventos viven en la pestaña Misión del panel derecho
    if (clave === "recomendaciones") {
      abrir("decision", "decision-toggle");
      const d = document.getElementById("det-rec"); if (d) d.open = true;
    }
  },
});
const avisarAccion = (tipo) => window.dispatchEvent(new CustomEvent("ares:accion", { detail: { tipo } }));

async function asegurarModoManual() {
  if (document.getElementById("modo").value === "manual") return;
  avisar(TEXTO_CAMBIO_MODO);
  detenerReproduccion();
  document.getElementById("modo").value = "manual";
  const datos = await llamar("POST", "/modo", { modo: "manual", veto: document.getElementById("veto").checked });
  if (datos) { estado = datos; pintarHud(datos); await refrescarPaneles(); }
}
document.querySelectorAll(".tutorial-abrir").forEach((b) => b.addEventListener("click", async () => {
  if (!estado || estado.sin_partida || ocupado()) return;
  await asegurarModoManual();
  tutorial.cerrarOferta();
  tutorial.iniciar();
}));
document.getElementById("menu-tutorial").addEventListener("click", () => {
  const modo = document.getElementById("menu-modo");
  modo.value = "manual"; modo.dispatchEvent(new Event("change"));
  tutorialPendiente = true;
  document.getElementById("iniciar").click();
});
document.getElementById("menu-records").addEventListener("click", () => abrirRecords());
document.getElementById("menu-comparar").addEventListener("click", () => vistaComparar.abrir());
document.getElementById("pol-comparar-vivo").addEventListener("click", () => vistaComparar.abrir());
document.getElementById("meta-records").addEventListener("click", () => abrirRecords({ semilla: estado ? estado.semilla : "" }));

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
  const ok = await conCarga(() => cargarPartida(semilla, nivel, tamano, config), { destino: config.planeta });
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
  if (tutorialPendiente) { tutorialPendiente = false; tutorial.iniciar(); }
  else if (config.control === "manual") setTimeout(() => tutorial.ofrecer(), 700);   // la primera vez en manual se ofrece el recorrido
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
  if (pausaActiva) return true;
  if (cineRepitiendo) return true;   // repetición visual del cine: no se envía ningún paso al motor mientras dura   // con la pausa abierta no se mueve nada
  if (cargando) {
    avisar("Cargando partida, espera un momento…");
    return true;
  }
  return false;
}

async function mover(rumbo) {
  if (finActiva()) return;
  if (!mapa || ocupado()) return;
  if (enModoManual() && reproduciendo !== null) { detenerReproduccion(); avisar("Control retomado: conduces tú."); }   // mover a mano es retomar el control
  const r = await llamar("POST", "/mover", { rumbo });
  if (!r) return;
  avisar((r.movido ? `Movimiento ${rumbo}.` : `Movimiento ${rumbo} rechazado: ${r.motivo}`) + eventosTexto(r.eventos_combate));
  registrarEvento(r.movido ? `mover ${rumbo}` : `mover ${rumbo} rechazado: ${r.motivo}`);
  if (r.movido) avisarAccion("mover");
  await refrescarEstado();
  await refrescarPaneles();
  revisarFinManual();
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
    const claro = limpiarAviso(aviso, vehiculoActual());   // sin el código interno delante y con el vehículo real
    avisar(claro);
    registrarEvento(`aviso: ${claro}`);
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
function mostrarCalculando(si) {
  let n = document.getElementById("motor-calculando");
  if (!n) { n = document.createElement("div"); n.id = "motor-calculando"; n.setAttribute("role", "status");
    n.textContent = "El motor está calculando (replanteo del AG)… la partida sigue"; document.body.append(n); }
  n.classList.toggle("visible", !!si);
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
document.getElementById("motor-menu").addEventListener("click", () => { volverAlInicio("salir"); });

// Un paso de la IA: el rover avanza en la escena y los paneles muestran lo que decidió.
async function paso() {
  if (finActiva()) return false;   // con la pantalla final abierta, los atajos de la partida no responden
  if (!mapa || ocupado() || pasoEnVuelo) return false;
  // Partida ya terminada: no se envía nada (evita respuestas 409 en la consola)
  if (estado && ESTADOS_TERMINALES.includes(estado.estado)) {
    detenerReproduccion();
    return false;
  }
  const estadoPrevio = estado;
  let r;
  pasoEnVuelo = true;
  const generacion = generacionInicio;
  // 22/11: un replanteo del AG en mapa grande puede tardar varios segundos. Antes, a los 2 s se abría un diálogo que
  // detenía la reproducción y parecía el fin de la partida («Reintentar» la continuaba). Ahora: aviso suave que no
  // detiene nada a los 1,5 s, y el diálogo solo si el motor no responde en 25 s.
  const avisoSuave = setTimeout(() => mostrarCalculando(true), 1500);
  const temporizador = setTimeout(avisarMotorLento, 25000);
  try {
    r = await llamar("POST", "/paso");
  } finally {
    clearTimeout(temporizador);
    clearTimeout(avisoSuave);
    mostrarCalculando(false);
    pasoEnVuelo = false;
  }
  if (generacion !== generacionInicio) return false;   // se salió de la partida con el paso en vuelo: no se pinta nada ni se abre la pantalla final
  if (!r) {
    detenerReproduccion();
    return false;
  }
  const terminada = ESTADOS_TERMINALES.includes(r.estado);
  const fin = r.accion === "fin";
  if (terminada || fin) detenerReproduccion();   // antes de esperar al refresco: otro tick del reloj enviaba un /paso más y el motor respondía 409
  if (r.ultimo && r.ultimo.paso != null) ultimoPasoNumero = r.ultimo.paso;
  if (r.accion === "disparar") efectoDisparoAutomatico(r, estadoPrevio);
  if (cadenaAutomatica && r.accion === "replanificar") cadenaAutomatica.replanteosActual += 1;
  const estadoAntesSonido = estadoPrevio;
  await refrescarEstado();
  sonido.paso(r, estadoAntesSonido, estado);
  if (terminada) sonido.fin(r.estado === "EXITO");
  await refrescarPaneles();
  momentosEnPaso(r);
  const motivos = nombresMotivos(r.motivos);
  avisar(`Paso ${pasoDe(r)}: ${r.accion}${motivos ? ` · ${motivos}` : ""}` + eventosTexto(r.eventos_combate));
  registrarEvento(`paso ${pasoDe(r)}: ${r.accion}${motivos ? ` · ${motivos}` : ""}`);
  mostrarAvisosNuevos(estado && estado.avisos);   // después del aviso del paso, para que no lo tape
  (r.eventos_combate || []).forEach((e) => registrarEvento(`combate: ${e}`));
  if (cine && cineVivo() && !terminada && !fin) {
    const tipoCine = cine.datos.tipoMomento({ motivos: r.motivos, eventos: r.eventos_combate, estado: r.estado });
    if (tipoCine) cineMomento(tipoCine);
    else if (reproduciendo === null) cineCortePaso();   // «Un paso»: cada paso es un plano corto distinto
  }
  if (terminada) {
    detenerReproduccion();
    avisar(`Fin de la partida: ${nombreEstado(r.estado)}.`);
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
document.getElementById("sin-resultado-menu").addEventListener("click", () => { volverAlInicio("salir"); });

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
  if (document.body.classList.contains("intro-activa")) return;   // la intro no dispara (QA ARX-97)
  if (finActiva()) return;   // la pantalla final tampoco
  if (!mapa || ocupado() || !estado) return;
  const rumbo = estado.rumbo || "N";
  const r = await llamar("POST", "/disparo", { rumbo });
  if (!r) return;
  efectoDisparo(rumbo, r.impacto, puntoDronEnLinea(rumbo));
  avisar((r.impacto ? "¡Impacto!" : "Disparo sin impacto.") + eventosTexto(r.eventos_combate));
  registrarEvento(r.impacto ? "disparo: impacto" : "disparo sin impacto");
  await refrescarEstado();
  await refrescarPaneles();
  revisarFinManual();
}

// En manual, «Reproducir» pone a la IA a conducir: el botón lo dice, y mientras conduce hay un aviso fijo para retomar el control.
// (Ronda 23.) El servidor ve esos pasos como de la IA en una partida manual y la marca como asistida para los récords.
const enModoManual = () => document.getElementById("modo").value === "manual";
function pintarRotulosReproduccion() {
  const manual = enModoManual(), corre = reproduciendo !== null;
  const r = document.getElementById("reproducir"), un = document.getElementById("paso"), cp = document.getElementById("cine-play");
  if (r) r.textContent = corre ? (manual ? "❚❚ Retomar el control" : "❚❚ Pausa") : (manual ? "▶ Dejar que la IA conduzca" : "▶ Reproducir");
  if (r) r.title = manual ? "En modo manual, la IA conduce sola hasta que retomes el control. La misión contará como asistida por la IA en los récords." : "";
  if (un) { un.textContent = manual ? "⏭ Un paso de la IA" : "⏭ Un paso"; un.title = manual ? "La IA da un paso por ti; la misión contará como asistida por la IA" : "Avanza un paso de la IA"; }
  if (cp) { cp.textContent = corre ? "⏸" : "▶"; cp.setAttribute("aria-label", corre ? "Pausar la simulación (barra espaciadora)" : "Reanudar la simulación (barra espaciadora)"); cp.title = cp.getAttribute("aria-label"); }
  const aviso = document.getElementById("ia-conduce");
  if (aviso) aviso.classList.toggle("oculto", !(manual && corre));
}
function detenerReproduccion() {
  if (reproduciendo !== null) {
    clearInterval(reproduciendo);
    reproduciendo = null;
  }
  pintarRotulosReproduccion();
}

function alternarReproduccion() {
  if (reproduciendo !== null) {
    detenerReproduccion();
    return;
  }
  const ms = Number(document.getElementById("velocidad").value);
  reproduciendo = setInterval(() => { paso(); }, ms);
  pintarRotulosReproduccion();
}

// ---------- intervención (ARX-10) ----------
// Qué se espera ver con cada intervención (22/11: la sección se explicaba mal)
const EXPLICACION_INTERVENCION = {
  ninguna: "",
  "rna-barranco": "Qué mirar: aunque el terreno esté libre, el supervisor vetará el avance por el barranco que cree ver la RNA y el vehículo replanificará. Prueba que la RNA puede frenarlo.",
  "rna-libre": "Qué mirar: la RNA ya no avisa de barrancos; si el vehículo se sigue frenando ante uno, es el telémetro del supervisor, que mide el desnivel. Prueba qué protección depende de la RNA y cuál no.",
  difuso: "Qué mirar: la velocidad queda fija en el valor elegido (0 = el vehículo se detiene). Prueba que el difuso es quien decide la velocidad.",
};
function actualizarCampoIntervencion() {
  const tecnica = document.getElementById("int-tecnica").value;
  document.getElementById("int-valor-fila").style.display = tecnica === "difuso" ? "block" : "none";
  const ex = document.getElementById("int-explicacion");
  if (ex) ex.textContent = EXPLICACION_INTERVENCION[tecnica] || "";
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

// Series por paso desde /serie (contrato CONTRATOS_GRAFICOS.md, §6). /serie ya trae p_libre y p_obstaculo
// (auditoría 22/11: antes se pedía además /historial en cada refresco solo para completarlos).
async function refrescarGraficos() {
  if (!estado || estado.sin_partida) return;
  const serie = await llamar("GET", "/serie");
  if (!serie) return;
  filasGraficos = serie.filas.map((f) => ({ ...f, p_libre: f.p_libre ?? null, p_obstaculo: f.p_obstaculo ?? null }));
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

// ---------- Cine: director de cámara y postproceso (solo cámara y render; no escribe en la partida ni en el motor) ----------
// Módulos cargados con import() solo al marcar una casilla o pulsar H; si algo falla, la escena y la partida siguen igual.
let cine = null;               // { datos, director, panel, cinta }
let cineCarga = null;
let cinePost = null;
let cinePostCarga = null;
let cineRepitiendo = false;
let cineOcultoPorH = false;
let cineForzado = false;       // el botón «Cine» de la barra: el director actúa también en conducción manual
let cineTomaPaso = 0;          // turno de las tomas cortas de «Un paso»
let cineFpsAcum = 0, cineFpsEma = 0;
const cineReducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
function cinePref(clave) { try { return localStorage.getItem(clave) === "1"; } catch (e) { return false; } }
function cineFijarPref(clave, on) { try { localStorage.setItem(clave, on ? "1" : "0"); } catch (e) { /* sin almacenamiento */ } }
const cineVivo = () => Boolean(cine && cine.director.activo);
function cineAvisar(texto) {
  console.warn("cine:", texto);
  try { if (cine) { cine.cinta.aviso(texto); cine.panel.aviso(texto); } else avisar(texto); } catch (e) { /* sin interfaz */ }
}
function cineCargar() {
  if (!cineCarga) {
    cineCarga = (async () => {
      const [datos, { crearDirector }, ui] = await Promise.all([
        import("/static/cine_datos.js?v=r14"), import("/static/cine3d.js?v=r14"), import("/static/cine_ui.js?v=r14")]);
      const director = crearDirector({
        THREE, escena: scene, camara, controles, sueloEn: alturaTerreno, reducido: cineReducido(),
        celdas: () => limitesMapa || { columnas: 60, filas: 40 },
        objetivo: () => ({ pos: grupoRover.position, rot: grupoRover.rotation.y }),
      });
      const panel = ui.crearPanelCine(document.getElementById("cine-lecturas"));
      const cinta = ui.crearCintaCine(document.body, { alDesactivar: () => cineActivar(false) });
      cine = { datos, director, panel, cinta };
    })().catch((e) => { cineCarga = null; cine = null; console.warn("cine: no se pudo cargar; la partida sigue igual", e); throw e; });
  }
  return cineCarga;
}
// ¿Puede actuar el director ahora? Intro, viaje, pausa, pantalla final y conducción manual tienen preferencia.
function cinePuede() {
  if (!(estado && !estado.sin_partida && mapa) || !cine) return false;
  const oculto = (id) => document.getElementById(id).classList.contains("oculto");
  return cine.datos.debeActuar({
    activado: true, enPartida: oculto("menu"), intro: Boolean(introCorriendo || (intro && intro.activo)), viaje: Boolean(viaje && viaje.activo),
    pausa: pausaActiva, final: !oculto("meta") || !oculto("sin-resultado") || !oculto("error-motor"),
    manual: document.getElementById("modo").value !== "automatico" && !cineForzado,
  });
}
// Devuelve true si el director quedó en marcha
async function cineActivar(on) {
  if (!on) {
    cineForzado = false;
    if (cine) { cine.director.activar(false); cine.cinta.director(false); cineRepitiendo = false; }
    if (cineOcultoPorH) { document.body.classList.remove("cine"); cineOcultoPorH = false; }
    return false;
  }
  try {
    await cineCargar();
    if (!cinePuede() || cine.director.activo) return cine.director.activo;
    cine.director.reducido = cineReducido();
    camaraSiguiendo = false;
    cine.director.activar(true);
    cine.cinta.director(true);
    return true;
  } catch (e) {
    document.getElementById("cine-director").checked = false; cineFijarPref("ares.cine", false);
    cineAvisar("Cine no disponible: la partida sigue igual");
    return false;
  }
}
async function cinePostActivar(on) {
  const casilla = document.getElementById("cine-post");
  if (!on) {
    if (cinePost) { try { cinePost.dispose(); } catch (e) { /* ya liberado */ } cinePost = null; }
    casilla.checked = false; cineFijarPref("ares.cine.post", false);
    return;
  }
  try {
    if (!cinePostCarga) {
      const base = "/static/vendor/postprocessing/";
      cinePostCarga = Promise.all([
        import("/static/cine_post.js?v=r14"), import(base + "EffectComposer.js"), import(base + "RenderPass.js"), import(base + "UnrealBloomPass.js"),
        import(base + "BokehPass.js"), import(base + "ShaderPass.js"), import(base + "OutputPass.js"), cineCargar()]).catch((e) => { cinePostCarga = null; throw e; });
    }
    const [{ crearPostproceso }, a, b, c, d, f, g] = await cinePostCarga;
    if (!casilla.checked || cinePost) return;
    cinePost = crearPostproceso({
      THREE, renderer,
      clases: { EffectComposer: a.EffectComposer, RenderPass: b.RenderPass, UnrealBloomPass: c.UnrealBloomPass, BokehPass: d.BokehPass, ShaderPass: f.ShaderPass, OutputPass: g.OutputPass },
      alApagarSolo: () => { cinePostActivar(false); cineAvisar(cine.datos.AVISO_POST_APAGADO); },
    });
    cinePost.setBokeh(true, scene, camara);
    cineFijarPref("ares.cine.post", true);
  } catch (e) {
    console.warn("cine: no se pudo cargar el postproceso; sigue el render normal", e);
    cinePost = null; casilla.checked = false; cineFijarPref("ares.cine.post", false);
    cineAvisar("Cine no disponible: la partida sigue igual");
  }
}
// «Un paso» con el cine: alterna planos cercanos (primer plano, rasante, travelling y seguimiento)
const TOMAS_PASO = ["primer", "rasante", "travelling", "seguimiento"];
function cineCortePaso() {
  if (!cineVivo() || cineRepitiendo) return;
  const id = TOMAS_PASO[cineTomaPaso % TOMAS_PASO.length]; cineTomaPaso += 1;
  const n = cine.datos.TOMAS.findIndex((t) => t.id === id);
  if (n >= 0) cine.director.cortar(n);
}
// Botón «Cine» de la barra: oculta los paneles (como H) y enciende el director en cualquier modo de conducción.
// Reproducir encadena tomas automáticas; Un paso corta a un plano cercano; H, Esc, el botón o tocar la escena salen.
async function cineDesdeBarra() {
  if (cineVivo()) { salirCine(); return; }
  cineForzado = true;
  const yaOculto = document.body.classList.contains("cine");
  document.body.classList.add("cine"); cineOcultoPorH = !yaOculto;
  const actuo = await cineActivar(true);
  if (!actuo) {
    cineForzado = false;
    if (!yaOculto) document.body.classList.remove("cine");
    cineOcultoPorH = false;
    avisar("El modo cine necesita una partida en curso (sin pausa, viaje ni pantalla final).");
  }
  sincronizarCine();
}
// Salida única del modo cine (botón «Salir», Esc, H, «Seguir»): apaga el director, quita la clase y deja cada panel como estaba
function salirCine() {
  if (cine && cineVivo()) cineActivar(false);
  document.body.classList.remove("cine");
  cineOcultoPorH = false; cineForzado = false;
  sincronizarCine();
}
document.getElementById("cine-salir").addEventListener("click", () => salirCine());
document.getElementById("cine-play").addEventListener("click", (ev) => { alternarReproduccion(); ev.currentTarget.blur(); });   // arranca o pausa sin salir del cine
document.getElementById("ia-retomar").addEventListener("click", () => { detenerReproduccion(); avisar("Control retomado: conduces tú."); });
// Estado visible del cine: bandas negras y botón pulsado mientras el director está en vivo
let cineVivoAntes = null;
function sincronizarCine() {
  const vivo = cineVivo();
  if (vivo === cineVivoAntes) return;
  cineVivoAntes = vivo;
  document.body.classList.toggle("cine-director", vivo);
  const b = document.getElementById("boton-cine");
  if (b) { b.setAttribute("aria-pressed", String(vivo)); b.textContent = vivo ? "✕ Salir del cine" : "🎬 Cine"; }
}
setInterval(sincronizarCine, 250);   // el director también se apaga con H, Esc o un gesto sobre la escena

// Momento dramático: repetición visual lenta con la simulación en pausa (el cliente no envía ningún paso mientras dura)
function cineMomento(tipo) {
  if (!cineVivo() || cineRepitiendo || cineReducido()) return false;
  cineRepitiendo = true;
  const ok = cine.director.empezarRepeticion(tipo, () => { cineRepitiendo = false; cine.cinta.repeticion(false); });
  if (ok) cine.cinta.repeticion(true); else cineRepitiendo = false;
  return ok;
}
document.getElementById("cine-director").addEventListener("change", (ev) => {
  cineFijarPref("ares.cine", ev.target.checked);
  cineActivar(ev.target.checked);
});
document.getElementById("cine-post").addEventListener("change", (ev) => cinePostActivar(ev.target.checked));
document.getElementById("cine-director").checked = cinePref("ares.cine");
document.getElementById("cine-post").checked = cinePref("ares.cine.post");
if (cinePref("ares.cine.post")) cinePostActivar(true);   // preferencia guardada: carga perezosa al abrir
// Cualquier gesto del usuario sobre la escena le devuelve la cámara, sin salto
for (const tipo of ["pointerdown", "wheel"]) {
  window.addEventListener(tipo, (ev) => {
    if (cineVivo() && ev.target === renderer.domElement) { cineActivar(false); camaraSiguiendo = false; }
  }, { capture: true, passive: true });
}
// ---------- entrada ----------
window.addEventListener("keydown", (ev) => {
  if (finActiva()) return;   // con la pantalla final abierta no responde ningún atajo de la partida
  // Con el director en vivo solo valen Esc y H; el resto de atajos del juego (espacio, flechas, WASD, zoom) no hacen nada
  if (ev.key === "Escape" && !pausaActiva && document.body.classList.contains("cine") && document.getElementById("laboratorio").classList.contains("oculto")) { ev.preventDefault(); salirCine(); return; }   // Esc sale del cine (con o sin director) antes de abrir la pausa
  if (cineVivo()) {
    if (ev.key === "Escape") { cineActivar(false); return; }
    if (!(ev.key === "h" || ev.key === "H") || ["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName)) {
      if (ev.key === " " && ev.target === document.body) { ev.preventDefault(); alternarReproduccion(); }   // en el cine, la barra espaciadora arranca o pausa
      return;
    }
  }
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
    if (cineVivo()) { salirCine(); return; }   // H otra vez: el director se desactiva
    document.body.classList.toggle("cine");
    if (document.body.classList.contains("cine") && document.getElementById("cine-director").checked) {
      cineOcultoPorH = true;
      cineActivar(true).then((actuo) => { if (!actuo) cineOcultoPorH = false; });   // sin casilla o en manual, H es solo el modo cine de paneles
    }
    return;
  }
  if (ev.key === " ") {
    ev.preventDefault();
    if (document.body.classList.contains("cine")) alternarReproduccion(); else disparar();   // en el cine (sin director) también arranca o pausa
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
    avisar(`Modo ${nombreModo(datos.modo)}.`);
    await refrescarPaneles();
    pintarTira();   // H-7: la tira aparece u oculta según el modo, sin esperar un paso nuevo
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
document.getElementById("zoom-mas").addEventListener("click", () => { if (modoCamara !== "orbita") fijarModoCamara("orbita"); zoomPaso(PASO_ZOOM); });
document.getElementById("zoom-menos").addEventListener("click", () => { if (modoCamara !== "orbita") fijarModoCamara("orbita"); zoomPaso(1 / PASO_ZOOM); });
document.getElementById("encuadrar").addEventListener("click", () => {
  if (modoCamara !== "orbita") fijarModoCamara("orbita");   // las vistas fijas son de la órbita
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
  if (modoCamara !== "orbita") fijarModoCamara("orbita");   // las vistas fijas son de la órbita
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
  if (modoCamara !== "orbita") fijarModoCamara("orbita");   // las vistas fijas son de la órbita
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
  encuadrarVista();
  renderer.setSize(window.innerWidth, window.innerHeight);
  if (cinePost) cinePost.ajustar(window.innerWidth, window.innerHeight);
  dibujarGrafico();
});

// Subtítulos del narrador: solo se ven en el modo cine (dentro de la banda negra inferior)
let subtituloTimer = null;
function mostrarSubtitulo(texto) {
  let sub = document.getElementById("subtitulo-ia");
  if (!sub) { sub = document.createElement("div"); sub.id = "subtitulo-ia"; sub.setAttribute("aria-live", "polite"); document.body.append(sub); }
  sub.textContent = texto || "";
  sub.classList.toggle("visible", !!texto);
  clearTimeout(subtituloTimer);
  subtituloTimer = setTimeout(() => sub.classList.remove("visible"), 9000);
}
// ---------- panel derecho de IA y encuadre de la escena ----------
// La escena ocupa toda la ventana, pero el centro óptico se corre al centro del hueco que dejan los paneles,
// para que el rover no quede tapado por la columna izquierda ni por el panel de IA.
function encuadrarVista() {
  const W = window.innerWidth, H = window.innerHeight;
  let izq = 0, der = 0;
  if (!document.body.classList.contains("cine") && W > 760) {
    const col = document.getElementById("columna");
    // (offsetParent es siempre null en elementos fixed: con él la columna nunca contaba y el vehículo quedaba detrás de ella)
    if (col && col.getClientRects().length > 0) izq = col.getBoundingClientRect().right;
    if (panelIA && !panelIA.elemento.classList.contains("oculto")) der = panelIA.ancho + 12;
    // la zona de vista (ficha de la sonda y controles) ocupa el borde derecho del hueco: el centro óptico se corre para que el vehículo no quede detrás
    const zona = document.getElementById("zona-vista");
    if (zona && zona.getClientRects().length > 0 && !document.getElementById("manual").classList.contains("oculto")) der += zona.getBoundingClientRect().width + 12;
  }
  const desplazamiento = Math.round((der - izq) / 2);
  if (desplazamiento) camara.setViewOffset(W, H, desplazamiento, 0, W, H); else camara.clearViewOffset();
  camara.updateProjectionMatrix();
}
try {
  panelIA = crearPanelIA({
    controles: document.getElementById("controles"),
    alCambiarAncho: () => encuadrarVista(),
    alAmpliar: (seccion) => {
      document.getElementById("abrir-laboratorio").click();
      if (seccion) { const b = document.querySelector(`.lab-tab[data-lab="${seccion}"]`); if (b) b.click(); }
    },
    alMaximizar: () => window.dispatchEvent(new KeyboardEvent("keydown", { key: "h" })),   // lo mismo que la tecla H
    alNarrar: (texto) => mostrarSubtitulo(texto),                                         // subtítulos en el modo cine
  });
  if (!document.getElementById("menu").classList.contains("oculto")) panelIA.mostrar(false);
} catch (e) { console.warn("panel de IA: no se pudo crear; la partida sigue sin él", e); panelIA = null; }
// Barra de control fija (Reproducir, Un paso, velocidad): siempre a la vista durante la partida, sea cual sea la pestaña del panel
function montarBarraMision() {
  const dock = document.getElementById("dock");
  const rep = document.getElementById("reproducir"), un = document.getElementById("paso"), vel = document.getElementById("velocidad");
  if (!dock || !rep || !un || !vel) return;
  const barra = document.createElement("div");
  barra.id = "barra-mision"; barra.className = "barra-mision"; barra.setAttribute("role", "toolbar"); barra.setAttribute("aria-label", "Control de la simulación");
  const viejaSim = document.getElementById("simulacion"), viejaRep = rep.closest("section");
  pintarRotulosReproduccion();
  const cineB = document.createElement("button");
  cineB.id = "boton-cine"; cineB.type = "button"; cineB.className = "boton-cine"; cineB.textContent = "🎬 Cine";
  cineB.title = "Modo cine: cámara de director sin paneles. Reproducir encadena tomas; Un paso corta a un plano cercano. H o Esc para salir.";
  cineB.setAttribute("aria-pressed", "false");
  cineB.addEventListener("click", () => cineDesdeBarra());
  const sonidoB = document.createElement("button");
  sonidoB.id = "boton-sonido"; sonidoB.type = "button"; sonidoB.className = "boton-sonido"; sonidoB.textContent = "🔇 Sonido";
  sonidoB.title = "Sonido procedural: motor, vetos, replanteos, choques, sitios y eventos";
  sonidoB.setAttribute("aria-pressed", "false");
  sonidoB.addEventListener("click", () => {
    const on = sonido.alternar();
    sonidoB.textContent = on ? "🔊 Sonido" : "🔇 Sonido"; sonidoB.setAttribute("aria-pressed", String(on));
  });
  const seguirB = document.createElement("button");
  seguirB.id = "boton-seguir"; seguirB.type = "button"; seguirB.className = "boton-seguir"; seguirB.textContent = "⌖ Seguir";
  seguirB.title = "Vuelve a seguir al vehículo con la cámara (rover o sonda). Tecla F";
  seguirB.addEventListener("click", () => seguirVehiculo());
  const defensaB = document.createElement("button");
  defensaB.id = "boton-defensa"; defensaB.type = "button"; defensaB.className = "boton-defensa"; defensaB.textContent = "🎓 Defensa";
  defensaB.title = "Recorrido guiado de 11 pasos para presentar el trabajo, con cifras en vivo y los criterios de la consigna";
  defensaB.addEventListener("click", () => {
    if (!defensa) defensa = crearDefensa({
      paso: () => paso(),
      evento: (nombre) => dispararEvento(nombre),
      abrirLab: (seccion) => { document.getElementById("abrir-laboratorio").click(); const b = document.querySelector(`.lab-tab[data-lab="${seccion}"]`); if (b) b.click(); },
      abrirPestana: (id) => { if (panelIA) panelIA.abrir(id); },
      reporte: () => window.open("/reporte.html", "_blank", "noopener"),
    });
    if (defensa.abierta) defensa.cerrar(); else defensa.abrir();
  });
  barra.append(rep, un, vel.closest("label") || vel, seguirB, cineB, sonidoB, defensaB);
  dock.prepend(barra);
  if (viejaSim) viejaSim.hidden = true;
  if (viejaRep && viejaRep !== viejaSim && !viejaRep.querySelector("button")) viejaRep.hidden = true;
}
try { montarBarraMision(); } catch (e) { console.warn("barra de control: se quedan los botones en el panel", e); }
// El aviso «La IA está conduciendo» vive en la franja inferior, justo sobre la barra de control, para que no tape el mensaje ni la bitácora
try { const dock = document.getElementById("dock"), aviso = document.getElementById("ia-conduce"), barra = document.getElementById("barra-mision"); if (dock && aviso) dock.insertBefore(aviso, barra || dock.firstChild); } catch (e) { /* queda flotando arriba */ }
new MutationObserver(encuadrarVista).observe(document.body, { attributes: true, attributeFilter: ["class"] });
for (const id of ["manual", "menu"]) new MutationObserver(encuadrarVista).observe(document.getElementById(id), { attributes: true, attributeFilter: ["class"] });   // los controles aparecen al iniciar la partida
encuadrarVista();

// 22/11: «⌖ Seguir» / tecla F: la cámara vuelve a seguir al vehículo (rover o sonda) en cualquier modo y momento
function seguirVehiculo() {
  if (cineVivo()) salirCine();
  if (modoCamara === "orbita") document.getElementById("encuadrar").click();   // recentra y deja el seguimiento activo
  camaraSiguiendo = true;
}
window.addEventListener("keydown", (ev) => {
  if ((ev.key === "f" || ev.key === "F") && !["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName) && !finActiva()) seguirVehiculo();
});

// ---------- modos de cámara (auditoría 22/11) ----------
// Órbita (la de siempre, con OrbitControls), persecución, primera persona desde el mástil y cenital. El cine tiene
// prioridad. Los modos con el rover escriben la cámara con amortiguación y nunca bajan del terreno.
const MODOS_CAMARA = [["orbita", "Órbita"], ["persecucion", "Persecución"], ["primera", "Primera persona"], ["cenital", "Cenital"]];
let modoCamara = "orbita";
const _camDestino = new THREE.Vector3(), _camMira = new THREE.Vector3(), _camMiraSuave = new THREE.Vector3();
let _camMiraIniciada = false;
function camaraDeModo(dt) {
  const p = grupoRover.position, r = grupoRover.rotation.y;
  const fx = Math.cos(r), fz = -Math.sin(r);          // avance del rover: +x local (como el director de cine)
  if (modoCamara === "persecucion") {
    _camDestino.set(p.x - fx * 4.2, p.y + 2.2, p.z - fz * 4.2);
    _camMira.set(p.x + fx * 3, p.y + 0.5, p.z + fz * 3);
  } else if (modoCamara === "primera") {
    _camDestino.set(p.x + fx * 0.35, p.y + 1.05, p.z + fz * 0.35);
    _camMira.set(p.x + fx * 8, p.y + 0.6, p.z + fz * 8);
  } else {                                           // cenital: desde arriba, con el avance hacia arriba de la pantalla
    _camDestino.set(p.x - fx * 0.01, p.y + 26, p.z - fz * 0.01);
    _camMira.set(p.x, p.y, p.z);
  }
  _camDestino.y = Math.max(_camDestino.y, alturaTerreno(_camDestino.x, _camDestino.z) + 0.35);
  const k = modoCamara === "primera" ? 1 - Math.exp(-dt * 12) : 1 - Math.exp(-dt * 4);
  camara.position.lerp(_camDestino, k);
  if (!_camMiraIniciada) { _camMiraSuave.copy(_camMira); _camMiraIniciada = true; }
  _camMiraSuave.lerp(_camMira, k);
  camara.lookAt(_camMiraSuave);
  controles.target.copy(_camMiraSuave);              // al volver a órbita no hay salto
}
function fijarModoCamara(modo) {
  if (!MODOS_CAMARA.some(([m]) => m === modo)) modo = "orbita";
  modoCamara = modo;
  _camMiraIniciada = false;
  controles.enabled = modo === "orbita";
  if (modo === "orbita") { camaraSiguiendo = true; controles.update(); }
  document.body.classList.toggle("camara-primera", modo === "primera");
  const sel = document.getElementById("modo-camara");
  if (sel && sel.value !== modo) sel.value = modo;
  try { localStorage.setItem("ares.camara", modo); } catch (e) { /* sin almacenamiento */ }
}
function montarSelectorCamara() {
  const barra = document.getElementById("barra-mision");
  if (!barra) return;
  const etiqueta = document.createElement("label");
  etiqueta.title = "Modo de cámara (tecla C para cambiar)";
  etiqueta.append(document.createTextNode("Cámara "));
  const sel = document.createElement("select"); sel.id = "modo-camara";
  for (const [v, t] of MODOS_CAMARA) { const o = document.createElement("option"); o.value = v; o.textContent = t; sel.append(o); }
  sel.addEventListener("change", () => fijarModoCamara(sel.value));
  etiqueta.append(sel);
  const cineB = document.getElementById("boton-cine");
  barra.insertBefore(etiqueta, cineB || null);
  // HUD de la cámara de navegación (primera persona)
  const hud = document.createElement("div"); hud.id = "hud-navegacion"; hud.setAttribute("aria-hidden", "true");
  for (const c of ["si", "sd", "ii", "id"]) { const e = document.createElement("span"); e.className = `hn-esquina hn-${c}`; hud.append(e); }
  const mira = document.createElement("span"); mira.className = "hn-mira"; hud.append(mira);
  const rot = document.createElement("span"); rot.className = "hn-rotulo"; rot.textContent = "CÁMARA DE NAVEGACIÓN · MÁSTIL"; hud.append(rot);
  document.body.append(hud);
  let guardado = "orbita";
  try { guardado = localStorage.getItem("ares.camara") || "orbita"; } catch (e) { /* sin almacenamiento */ }
  fijarModoCamara(guardado);
}
try { montarSelectorCamara(); } catch (e) { console.warn("modos de cámara: no se pudo montar el selector", e); }
// Tecla C: recorre los modos (no actúa mientras se escribe en un campo ni con el director de cine)
window.addEventListener("keydown", (ev) => {
  if ((ev.key === "c" || ev.key === "C") && !["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName) && !cineVivo() && !finActiva()) {
    const i = MODOS_CAMARA.findIndex(([m]) => m === modoCamara);
    fijarModoCamara(MODOS_CAMARA[(i + 1) % MODOS_CAMARA.length][0]);
  }
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
  for (const obj of energiaMalla.values()) if (obj.userData.anim) obj.userData.anim(tiempo);
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

  const cineEnVivo = cineVivo();
  if (cineEnVivo && !cinePuede()) cineActivar(false);   // intro, viaje, pausa, pantalla final o manual: el cine cede
  if (cineEnVivo && cineVivo()) {
    cine.director.actualizar(dt);   // el director escribe la cámara; OrbitControls y el seguimiento no actúan
  } else if (modoCamara !== "orbita" && grupoRover.children.length) {
    camaraDeModo(dt);               // persecución, primera persona o cenital: la cámara va con el rover
  } else {
  if (camaraSiguiendo && grupoRover.children.length) {
    if (encuadreEvento && performance.now() > encuadreEvento.hasta) encuadreEvento = null;
    const p = encuadreEvento ? encuadreEvento.punto : grupoRover.position;   // breve encuadre de un evento fuera de cuadro
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
  }
  // Temblor de sismo (ev3-d41): se suma a la cámara solo para dibujar y se resta después
  const desplazamiento = efectos.desplazamientoTemblor(dt);
  camara.position.add(desplazamiento);
  efectos.actualizarMarcadores(tiempo, camara);
  efectos.actualizarMovibles(tiempo, dt);
  marcasEvento.actualizar(tiempo);
  actualizarEtiquetaEvento();
  if (mapa && grupoRover.children.length) ambientePlaneta.actualizar(dt, tiempo, grupoRover.position);
  if (intro && intro.activo) intro.render(); else if (viaje && viaje.activo) viaje.render();
  else if (cinePost && cinePost.activo) {
    try { cinePost.render(scene, camara, camara.position.distanceTo(grupoRover.position)); }
    catch (e) { console.warn("cine: fallo del postproceso; vuelve el render normal", e); cinePostActivar(false); renderer.render(scene, camara); }
  } else renderer.render(scene, camara);   // durante la intro o el viaje no se dibuja la escena principal
  camara.position.sub(desplazamiento);
  if (cine) {   // lectura de FPS del cine (media móvil, cada 0,5 s)
    cineFpsEma = cineFpsEma ? cineFpsEma * 0.9 + (1 / Math.max(dt, 0.001)) * 0.1 : 1 / Math.max(dt, 0.001);
    cineFpsAcum += dt;
    if (cineFpsAcum >= 0.5) { cineFpsAcum = 0; cine.panel.fps(`FPS: ${Math.round(cineFpsEma)}${cinePost ? " (con postproceso)" : ""}`); }
  }
  requestAnimationFrame(animar);
}
animar();

iniciarLaboratorios({ llamar, avisar });

// Al abrir: la intro (pantalla de inicio) cuando ya se conocen los planetas; si falla, el asistente queda tal cual
planetasListos.then(() => correrIntro({ motivo: "abrir" }), () => { /* sin /planetas no hay intro */ });

// Arranque (ARX-14): sin partida; el menú pide semilla y nivel. No se crea nada hasta pulsar Iniciar.
