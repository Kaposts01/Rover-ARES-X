// Visualización de los elementos móviles y de los eventos del paso (CONTRATOS_GRAFICOS.md §10).
// Recibe el objeto de /moviles (o de prueba) y lo dibuja en la escena. No decide nada: solo muestra.
import * as THREE from "three";
import * as efectos from "/static/efectos.js?v=r14";

const TEXTO_BIO = "anomalía, no confirma vida";
const visuales = new Map();   // id -> { objeto, tipo, estela? }
const grupoZonas = new THREE.Group();
const grupoPolvo = new THREE.Group();
let escenaRef = null;

const geomRoca = new THREE.DodecahedronGeometry(0.28, 0);
const matRoca = new THREE.MeshStandardMaterial({ color: 0x8a6250, roughness: 0.92, flatShading: true });
const matMeteoro = new THREE.MeshStandardMaterial({ color: 0x5a3a2c, roughness: 0.9, flatShading: true, emissive: 0x3a1204 });
const matEstela = new THREE.MeshBasicMaterial({ color: 0xffb070, transparent: true, opacity: 0.85, toneMapped: false });
const matZona = new THREE.MeshBasicMaterial({ color: 0xff5d6c, transparent: true, opacity: 0.22, depthWrite: false, toneMapped: false, side: THREE.DoubleSide });

// Celda (fila, columna) a coordenadas de escena, con la altura del terreno de la función `suelo`
function aEscena(celda, suelo) {
  const [f, c] = celda;
  const x = c + 0.5;
  const z = f + 0.5;
  return new THREE.Vector3(x, suelo(x, z), z);
}

function actualizarRoca(m, escena, suelo) {
  let v = visuales.get(m.id);
  if (!v) {
    const roca = new THREE.Mesh(geomRoca, matRoca);
    roca.castShadow = true;
    roca.receiveShadow = true;
    escena.add(roca);
    v = { objeto: roca, tipo: m.tipo };
    visuales.set(m.id, v);
  }
  const p = aEscena(m.pos, suelo);
  v.objeto.position.set(p.x, p.y + 0.2, p.z);
  v.objeto.rotation.y += 0.02;
}

function actualizarMeteoro(m, escena, suelo) {
  let v = visuales.get(m.id);
  if (!v) {
    const grupo = new THREE.Group();
    const roca = new THREE.Mesh(new THREE.DodecahedronGeometry(0.2, 0), matMeteoro);
    grupo.add(roca);
    const halo = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 8),
      new THREE.MeshBasicMaterial({ color: 0xff8a3c, transparent: true, opacity: 0.3, depthWrite: false, toneMapped: false }));
    grupo.add(halo);
    escena.add(grupo);
    v = { objeto: grupo, tipo: m.tipo, estela: null };
    visuales.set(m.id, v);
  }
  // Altura: el meteorito cae hacia el suelo; la trayectoria va de alto a bajo
  // Sin trayectoria, el meteorito cae vertical sobre su posición (E5)
  const trayectoria = Array.isArray(m.trayectoria) && m.trayectoria.length ? m.trayectoria : [m.pos];
  const puntos = trayectoria.map((celda, i) => {
    const p = aEscena(celda, suelo);
    p.y += 3 * (1 - i / Math.max(1, trayectoria.length - 1)) + 0.4;
    return p;
  });
  const ultimo = puntos[puntos.length - 1];
  v.objeto.position.copy(ultimo);
  if (v.estela) escena.remove(v.estela);
  if (puntos.length > 1) {
    const camino = new THREE.CurvePath();
    for (let i = 1; i < puntos.length; i++) camino.add(new THREE.LineCurve3(puntos[i - 1], puntos[i]));
    v.estela = new THREE.Mesh(new THREE.TubeGeometry(camino, puntos.length * 8, 0.06, 8, false), matEstela);
    escena.add(v.estela);
  }
  // Zona de riesgo: celdas marcadas en rojo translúcido
  for (const celda of m.zona_riesgo || []) {
    const p = aEscena(celda, suelo);
    const marca = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), matZona);
    marca.rotation.x = -Math.PI / 2;
    marca.position.set(p.x, p.y + 0.03, p.z);
    grupoZonas.add(marca);
  }
  const impactado = Array.isArray(m.impacto) || m.impacto === true;   // el motor manda la celda del impacto
  if (impactado) polvo(escena, ultimo);
}

// Polvo al impactar: partículas que se expanden y se desvanecen
function polvo(escena, centro) {
  const nube = new THREE.Group();
  const materiales = [];
  for (let i = 0; i < 14; i++) {
    const mat = new THREE.MeshBasicMaterial({ color: 0xc89a78, transparent: true, opacity: 0.8, depthWrite: false });
    const bola = new THREE.Mesh(new THREE.SphereGeometry(0.12, 6, 5), mat);
    const a = (i / 14) * Math.PI * 2;
    bola.userData.dir = new THREE.Vector3(Math.cos(a), 0.6 + 0.4 * ((i * 37) % 5) / 5, Math.sin(a));
    nube.add(bola);
    materiales.push(mat);
  }
  nube.position.copy(centro);
  escena.add(nube);
  const inicio = performance.now();
  const paso = () => {
    const t = (performance.now() - inicio) / 1000;
    if (t > 1.4) { escena.remove(nube); return; }
    nube.children.forEach((b) => {
      b.position.addScaledVector(b.userData.dir, 0.02);
      b.scale.setScalar(1 + t * 1.5);
    });
    materiales.forEach((m) => { m.opacity = Math.max(0, 0.8 * (1 - t / 1.4)); });
    requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// Eventos del paso: sismo, meteorito, baja conectividad y señal biológica (siempre con la cautela)
// Último paso del motor en que se sacudió la cámara: /moviles repite el evento mientras el paso sea el actual
let pasoSacudido = null;
// Una partida nueva vuelve al paso 0: se olvida el último temblor para que un sismo en ese paso vuelva a sacudir
export function reiniciarEventos() {
  pasoSacudido = null;
}
function aplicarEvento(e, escena, suelo, avisar, alGrietas, paso) {
  const nombre = (e.nombre || "").toLowerCase();
  if (nombre.includes("sismo")) {
    if (paso == null || paso !== pasoSacudido) {
      pasoSacudido = paso;
      efectos.sacudir(0.12, 1.5);
    }
    // Grietas: el llamador las pinta como barrancos del terreno, sin volver a pedir /mapa
    if (e.efecto === "grietas" && Array.isArray(e.celdas) && alGrietas) alGrietas(e.celdas);
  }
  if (nombre.includes("conectividad")) efectos.activarInterferencia(true);
  if (nombre.includes("senal") || nombre.includes("señal")) {
    const celda = (e.celdas && e.celdas[0]) || null;
    if (celda) {
      const p = aEscena(celda, suelo);
      efectos.marcarSenalBiologica(escena, [p.x, p.y, p.z]);
    }
    // El sistema nunca confirma vida: el texto de cautela va siempre, aunque el contrato dijera otra cosa
    if (avisar) avisar(TEXTO_BIO);
  }
}

// Punto de entrada: se llama tras cada paso o consulta de estado
// Un fallo con un móvil se registra una sola vez en consola, por identificador y mensaje
const fallosMovil = new Set();
function registrarFalloMovil(movil, err) {
  const clave = `${movil && movil.id}:${err.message}`;
  if (fallosMovil.has(clave)) return;
  fallosMovil.add(clave);
  console.error(`[movil ${movil && movil.id}]`, err);
}
export function aplicarMoviles(datos, escena, suelo, avisar, alGrietas) {
  if (!escenaRef) {
    escenaRef = escena;
    escena.add(grupoZonas);
    escena.add(grupoPolvo);
  }
  grupoZonas.clear();
  const vistos = new Set();
  for (const m of datos.moviles || []) {
    vistos.add(m.id);
    try {
      if (m.tipo === "obstaculo_movil") actualizarRoca(m, escena, suelo);
      if (m.tipo === "meteorito") actualizarMeteoro(m, escena, suelo);
    } catch (err) {
      registrarFalloMovil(m, err);   // un móvil malo no corta el resto del ciclo (E5)
    }
  }
  for (const [id, v] of visuales) {
    if (!vistos.has(id)) {
      escena.remove(v.objeto);
      if (v.estela) escena.remove(v.estela);
      visuales.delete(id);
    }
  }
  for (const e of datos.eventos_del_paso || []) {
    try {
      aplicarEvento(e, escena, suelo, avisar, alGrietas, datos.paso);
    } catch (err) {
      registrarFalloMovil(e, err);   // un evento malo tampoco corta el ciclo (E5)
    }
  }
}

export const TEXTO_CAUTELA = TEXTO_BIO;
