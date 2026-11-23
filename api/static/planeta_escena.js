// Escena propia de cada planeta: partículas de viento con dirección, centelleo (hielo, regolito, pavesas) y obstáculos de los gigantes
// (bancos de nubes, bruma, cristales de hielo). Los datos (perfiles y condiciones) viven en planeta_datos.js.
// Rendimiento: dos nubes de puntos de tamaño fijo (≤ 260 y ≤ 170), una sola geometría compartida por obstáculo y nada que liberar por mapa.
import { perfilPlaneta } from "./planeta_datos.js?v=r15";

const MAX_VIENTO = 260, MAX_CENTELLEO = 170;
const MEDIA_CAJA = 15;   // las partículas viven en una caja de 30 × 30 celdas alrededor del vehículo

// ---------- obstáculos de los gigantes (geometrías y materiales compartidos: no se acumulan al reconstruir el mapa) ----------
const comunes = {};
function comun(clave, fabrica) { return comunes[clave] || (comunes[clave] = fabrica()); }

export function crearObstaculoGigante(THREE, tipo, x, y, z, azar) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  if (tipo === "cristal" || (tipo === "nube_o_hielo" && azar(1) >= 0.5)) {
    // Formación de hielo: racimo de prismas facetados, translúcidos, con un núcleo que brilla un poco
    const geo = comun("cristal", () => new THREE.ConeGeometry(0.11, 1, 5));
    const mat = comun("mat-cristal", () => new THREE.MeshStandardMaterial({ color: 0xd6efff, roughness: 0.18, metalness: 0.1, flatShading: true, transparent: true, opacity: 0.82, emissive: 0x2f5f78, emissiveIntensity: 0.55 }));
    const n = 3 + Math.floor(azar(2) * 3);
    for (let k = 0; k < n; k++) {
      const alto = 0.35 + azar(3 + k) * 0.55, m = new THREE.Mesh(geo, mat);
      const a = (k / n) * Math.PI * 2 + azar(10 + k), r = k === 0 ? 0 : 0.12 + azar(20 + k) * 0.12;
      m.scale.set(1 + azar(30 + k) * 0.5, alto, 1 + azar(40 + k) * 0.5);
      m.position.set(Math.cos(a) * r, alto * 0.5 - 0.02, Math.sin(a) * r);
      m.rotation.set((azar(50 + k) - 0.5) * 0.5, azar(60 + k) * 3, (azar(70 + k) - 0.5) * 0.5);
      g.add(m);
    }
    return g;
  }
  // Banco de nubes (Neptuno) o de bruma dorada (Saturno): esferas aplastadas y translúcidas que se solapan
  const dorada = tipo === "bruma";
  const geo = comun("nube", () => new THREE.SphereGeometry(1, 12, 8));
  const mat = comun(dorada ? "mat-bruma" : "mat-nube", () => new THREE.MeshStandardMaterial({
    color: dorada ? 0xf2dfa4 : 0xc3d2ea, roughness: 1, transparent: true, opacity: dorada ? 0.5 : 0.55, depthWrite: false,
    emissive: dorada ? 0x5a4a20 : 0x1c2a44, emissiveIntensity: 0.5 }));
  const n = 4 + Math.floor(azar(4) * 3);
  for (let k = 0; k < n; k++) {
    const r = 0.16 + azar(5 + k) * 0.16, m = new THREE.Mesh(geo, mat);
    m.scale.set(r * 1.5, r * 0.8, r * 1.3);
    m.position.set((azar(15 + k) - 0.5) * 0.55, r * 0.55 + azar(25 + k) * 0.12, (azar(35 + k) - 0.5) * 0.55);
    g.add(m);
  }
  return g;
}

// ---------- partículas de la escena ----------
const VERTICE_CENTELLEO = `
  attribute float fase;
  uniform float uTiempo, uTam, uK;
  varying float vBrillo;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vBrillo = pow(max(0.0, sin(uTiempo * 2.2 + fase * 6.2831)), 5.0);
    gl_PointSize = max(1.0, uTam * uK / -mv.z);
    gl_Position = projectionMatrix * mv;
  }`;
const FRAGMENTO_CENTELLEO = `
  uniform vec3 uColor;
  uniform float uIntensidad;
  varying float vBrillo;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(uColor, a * vBrillo * uIntensidad);
  }`;

// opciones: THREE, escena, altura(x, z), camara, renderer
export function crearAmbientePlaneta({ THREE, escena, altura, camara, renderer }) {
  // Viento: puntos que derivan con la dirección y la fuerza del planeta
  const posV = new Float32Array(MAX_VIENTO * 3), velV = new Float32Array(MAX_VIENTO * 3);
  const geoV = new THREE.BufferGeometry();
  geoV.setAttribute("position", new THREE.BufferAttribute(posV, 3));
  // punto redondo y suave (con la textura por defecto los puntos salen cuadrados)
  const lienzo = document.createElement("canvas"); lienzo.width = lienzo.height = 32;
  const cx = lienzo.getContext("2d"), grad = cx.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, "rgba(255,255,255,1)"); grad.addColorStop(0.5, "rgba(255,255,255,0.6)"); grad.addColorStop(1, "rgba(255,255,255,0)");
  cx.fillStyle = grad; cx.fillRect(0, 0, 32, 32);
  const texPunto = new THREE.CanvasTexture(lienzo);
  const matV = new THREE.PointsMaterial({ color: 0xffffff, size: 0.07, map: texPunto, transparent: true, opacity: 0.7, depthWrite: false });
  const viento = new THREE.Points(geoV, matV);
  viento.frustumCulled = false; viento.visible = false;
  // Centelleo: brillos fijos sobre el suelo que titilan (hielo, regolito, pavesas)
  const posC = new Float32Array(MAX_CENTELLEO * 3), faseC = new Float32Array(MAX_CENTELLEO), altC = new Float32Array(MAX_CENTELLEO);
  const geoC = new THREE.BufferGeometry();
  geoC.setAttribute("position", new THREE.BufferAttribute(posC, 3));
  geoC.setAttribute("fase", new THREE.BufferAttribute(faseC, 1));
  const matC = new THREE.ShaderMaterial({
    vertexShader: VERTICE_CENTELLEO, fragmentShader: FRAGMENTO_CENTELLEO, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTiempo: { value: 0 }, uTam: { value: 0.1 }, uK: { value: 600 }, uColor: { value: new THREE.Color(0xffffff) }, uIntensidad: { value: 1 } },
  });
  const centelleo = new THREE.Points(geoC, matC);
  centelleo.frustumCulled = false; centelleo.visible = false;
  escena.add(viento, centelleo);

  let nViento = 0, nCentelleo = 0, sube = 0, vx = 0, vz = 0, fuerza = 0, impulso = 1;
  let semilla = 12345;
  const azar = () => { semilla = (semilla * 1664525 + 1013904223) >>> 0; return semilla / 4294967296; };
  const centro = new THREE.Vector3();
  let colocado = false;

  function repartir(c) {
    for (let i = 0; i < MAX_VIENTO; i++) {
      posV[i * 3] = c.x + (azar() * 2 - 1) * MEDIA_CAJA; posV[i * 3 + 1] = 0.15 + azar() * 3.2; posV[i * 3 + 2] = c.z + (azar() * 2 - 1) * MEDIA_CAJA;
      const v = 0.6 + azar() * 0.8;   // cada partícula con su propia velocidad relativa
      velV[i * 3] = v; velV[i * 3 + 1] = (azar() - 0.5) * 0.15; velV[i * 3 + 2] = v;
    }
    for (let i = 0; i < MAX_CENTELLEO; i++) {
      posC[i * 3] = c.x + (azar() * 2 - 1) * MEDIA_CAJA; posC[i * 3 + 2] = c.z + (azar() * 2 - 1) * MEDIA_CAJA;
      faseC[i] = azar(); altC[i] = 0.02 + azar() * 0.06;
      posC[i * 3 + 1] = altura(posC[i * 3], posC[i * 3 + 2]) + altC[i];
    }
    geoC.attributes.fase.needsUpdate = true;
    colocado = true;
  }

  // planeta: nombre; cond: condicionesPlaneta(...). Se llama al cargar la partida y cuando cambian las condiciones.
  // opciones.conservar: solo cambió el estado vivo (ráfaga, etc.) del mismo mapa: no se reparten de nuevo las partículas (sin saltos).
  function configurar(planeta, cond, opciones) {
    if (!(opciones && opciones.conservar)) colocado = false;   // el mapa cambió: los brillos se reparten de nuevo sobre el suelo nuevo
    const p = perfilPlaneta(planeta), rv = p.rasgos.viento, rc = p.rasgos.centelleo;
    fuerza = cond.viento.fuerza;
    const rad = (cond.viento.grados * Math.PI) / 180;   // 0 = norte (−z), 90 = este (+x)
    vx = Math.sin(rad); vz = -Math.cos(rad);
    sube = rv && rv.sube ? rv.sube : 0;
    // el viento solo se ve si el planeta tiene partículas y la fuerza no es nula; nunca por encima de su tope
    nViento = rv && fuerza > 0.04 ? Math.min(MAX_VIENTO, Math.round(rv.n * (0.45 + 0.55 * fuerza))) : 0;
    viento.visible = nViento > 0;
    geoV.setDrawRange(0, nViento);
    if (rv) { matV.color.setHex(rv.color); matV.size = rv.tam; }
    // el hielo suma brillos al suelo; los planetas con centelleo propio lo tienen siempre
    const base = rc ? rc.n : 0, extra = Math.round(MAX_CENTELLEO * 0.6 * cond.hielo.nivel);
    nCentelleo = Math.min(MAX_CENTELLEO, base + extra);
    centelleo.visible = nCentelleo > 0;
    geoC.setDrawRange(0, nCentelleo);
    matC.uniforms.uColor.value.setHex(rc ? rc.color : 0xeaf6ff);
    matC.uniforms.uTam.value = rc ? rc.tam : 0.1;
    matC.uniforms.uIntensidad.value = rc ? 1 : 0.35 + 0.65 * cond.hielo.nivel;
    impulso = 1.2 + 4.5 * fuerza;   // celdas por segundo a fuerza máxima: se nota la dirección sin marear
  }

  // tormenta: refuerza el viento mientras dura (la lee la app de /estado.ambiente)
  let refuerzo = 1;
  function reforzar(k) { refuerzo = k; }

  const caja = 2 * MEDIA_CAJA;
  function actualizar(dt, tiempo, foco) {
    if (!viento.visible && !centelleo.visible) return;
    centro.copy(foco);
    if (!colocado) repartir(centro);
    matC.uniforms.uTiempo.value = tiempo;
    const alto = renderer.domElement.height || 720, tanMitad = Math.tan((camara.fov * Math.PI) / 360);
    matC.uniforms.uK.value = alto / (2 * tanMitad);
    if (viento.visible) {
      const k = dt * impulso * refuerzo;
      for (let i = 0; i < nViento; i++) {
        const j = i * 3, v = velV[j];
        posV[j] += vx * v * k; posV[j + 2] += vz * v * k;
        posV[j + 1] += (velV[j + 1] + sube * v) * dt * (1 + fuerza);
        if (posV[j + 1] > 3.6) posV[j + 1] = 0.15;
        else if (posV[j + 1] < 0.1) posV[j + 1] = 3.4;
        // al salir de la caja, reaparece por el lado opuesto: siempre hay partículas cerca del vehículo
        if (posV[j] > centro.x + MEDIA_CAJA) posV[j] -= caja; else if (posV[j] < centro.x - MEDIA_CAJA) posV[j] += caja;
        if (posV[j + 2] > centro.z + MEDIA_CAJA) posV[j + 2] -= caja; else if (posV[j + 2] < centro.z - MEDIA_CAJA) posV[j + 2] += caja;
      }
      geoV.attributes.position.needsUpdate = true;
    }
    if (centelleo.visible) {
      let cambio = false;
      for (let i = 0; i < nCentelleo; i++) {
        const j = i * 3;
        let mover = false;
        if (posC[j] > centro.x + MEDIA_CAJA) { posC[j] -= caja; mover = true; } else if (posC[j] < centro.x - MEDIA_CAJA) { posC[j] += caja; mover = true; }
        if (posC[j + 2] > centro.z + MEDIA_CAJA) { posC[j + 2] -= caja; mover = true; } else if (posC[j + 2] < centro.z - MEDIA_CAJA) { posC[j + 2] += caja; mover = true; }
        if (mover) { posC[j + 1] = altura(posC[j], posC[j + 2]) + altC[i]; cambio = true; }
      }
      if (cambio) geoC.attributes.position.needsUpdate = true;
    }
  }

  function dispose() {
    escena.remove(viento, centelleo);
    geoV.dispose(); matV.dispose(); texPunto.dispose(); geoC.dispose(); matC.dispose();
  }
  return { configurar, actualizar, reforzar, dispose, get viento() { return { n: nViento, fuerza, vx, vz }; }, get centelleos() { return nCentelleo; } };
}
