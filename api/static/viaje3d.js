// Viaje entre planetas: escena propia (estrellas, dos planetas, nave y estela) dibujada en el mismo renderer.
// No toca la partida ni el motor. Ilustrativa, no a escala.
import { DURACION_VIAJE_S, fasesViaje, faseActual, trayectoria, actualizarEstela } from "/static/viaje_datos.js?v=r14";

const N_ESTRELLAS = 1200, N_ESTELA = 120, ANCHO = 20, RADIO = 6;
const CON_ANILLOS = new Set(["Saturno", "Urano"]);

export function crearViaje({ THREE, renderer, camara, texturaPlaneta, paleta, duracion = DURACION_VIAJE_S }) {
  const escena = new THREE.Scene();
  escena.background = new THREE.Color(0x02030a);
  const cam = new THREE.PerspectiveCamera(55, 1, 0.1, 400);
  const recursos = [];            // geometrías y materiales propios (las texturas del planeta son de app.js: no se liberan aquí)
  const propio = (r) => { recursos.push(r); return r; };
  escena.add(new THREE.AmbientLight(0x8899bb, 0.7));
  const luz = new THREE.DirectionalLight(0xffffff, 1.6); luz.position.set(-30, 40, 30); escena.add(luz);

  // Estrellas
  const pe = new Float32Array(N_ESTRELLAS * 3);
  for (let i = 0; i < N_ESTRELLAS; i++) {
    const r = 120 + Math.random() * 60, a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1);
    pe.set([r * Math.sin(b) * Math.cos(a), r * Math.cos(b), r * Math.sin(b) * Math.sin(a)], i * 3);
  }
  const gEst = propio(new THREE.BufferGeometry()); gEst.setAttribute("position", new THREE.BufferAttribute(pe, 3));
  escena.add(new THREE.Points(gEst, propio(new THREE.PointsMaterial({ color: 0xffffff, size: 0.9, sizeAttenuation: false }))));

  const geoEsfera = propio(new THREE.SphereGeometry(RADIO, 48, 32));
  function planeta(nombre) {
    let mapa = null;
    try { mapa = texturaPlaneta ? texturaPlaneta(nombre) : null; } catch (e) { console.warn("viaje: textura no disponible", e); }
    const hor = paleta && paleta[nombre] && paleta[nombre].horizonte;
    const color = hor ? new THREE.Color(hor[0], hor[1], hor[2]) : new THREE.Color(0x888888);
    const mat = propio(new THREE.MeshLambertMaterial(mapa ? { map: mapa } : { color }));
    const g = new THREE.Group(); g.add(new THREE.Mesh(geoEsfera, mat));
    if (CON_ANILLOS.has(nombre)) {
      const ga = propio(new THREE.RingGeometry(RADIO * 1.3, RADIO * 2, 64));
      const ma = propio(new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, transparent: true, opacity: 0.55 }));
      const anillo = new THREE.Mesh(ga, ma); anillo.rotation.x = Math.PI / 2.3; g.add(anillo);
    }
    escena.add(g); return g;
  }

  // Nave mínima: cuerpo, cono y llama
  const nave = new THREE.Group();
  const gCuerpo = propio(new THREE.CylinderGeometry(0.35, 0.35, 1.6, 12)), mCuerpo = propio(new THREE.MeshLambertMaterial({ color: 0xdddddd }));
  const gCono = propio(new THREE.ConeGeometry(0.35, 0.8, 12)), mCono = propio(new THREE.MeshLambertMaterial({ color: 0xcc4422 }));
  const gLlama = propio(new THREE.ConeGeometry(0.25, 1, 10)), mLlama = propio(new THREE.MeshBasicMaterial({ color: 0xffaa33 }));
  const cuerpo = new THREE.Mesh(gCuerpo, mCuerpo), cono = new THREE.Mesh(gCono, mCono), llama = new THREE.Mesh(gLlama, mLlama);
  cono.position.y = 1.2; llama.position.y = -1.2; llama.rotation.x = Math.PI;
  nave.add(cuerpo, cono, llama);
  escena.add(nave);

  // Estela
  const pEst = new Float32Array(N_ESTELA * 3);
  const gEstela = propio(new THREE.BufferGeometry()); gEstela.setAttribute("position", new THREE.BufferAttribute(pEst, 3));
  gEstela.setDrawRange(0, 0);
  const estela = new THREE.Points(gEstela, propio(new THREE.PointsMaterial({ color: 0xffbb66, size: 3, sizeAttenuation: false, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false })));
  estela.frustumCulled = false; escena.add(estela);

  let pA = null, pB = null, historial = [], t0 = 0, activo = false, resolver = null, liberado = false;
  const fases = fasesViaje(duracion);
  const v = new THREE.Vector3(), eje = new THREE.Vector3(0, 1, 0);

  function terminar() {
    if (!activo) return;
    activo = false;
    const r = resolver; resolver = null; if (r) r();
  }

  function iniciar(desde, hacia) {
    if (liberado || activo) return Promise.resolve();
    return new Promise((res) => {
      resolver = res;
      try {
        pA = planeta(desde); pB = planeta(hacia);
        pA.position.set(-ANCHO - 7, 0, 0); pB.position.set(ANCHO + 8, 0, 0);
        historial = []; t0 = performance.now(); activo = true;
        const w = renderer.domElement.clientWidth || 800, h = renderer.domElement.clientHeight || 600;
        cam.aspect = w / h; cam.updateProjectionMatrix();
      } catch (e) {
        console.warn("viaje: no se pudo preparar la escena", e);
        activo = true; terminar();
      }
    });
  }

  function render() {
    if (!activo) return;
    try {
      const t = (performance.now() - t0) / 1000;
      if (t >= fases.total) { terminar(); return; }
      const [fase, u] = faseActual(t, fases);
      const global = t / fases.total;
      const tr = trayectoria(global, ANCHO);
      nave.position.set(tr.pos[0], tr.pos[1], tr.pos[2]);
      v.set(tr.tangente[0], tr.tangente[1], tr.tangente[2]);
      nave.quaternion.setFromUnitVectors(eje, v);
      llama.scale.y = 0.8 + 0.4 * Math.sin(t * 30);
      pA.rotation.y += 0.002; pB.rotation.y += 0.003;
      pA.scale.setScalar(1 - 0.35 * global); pB.scale.setScalar(0.65 + 0.35 * global);
      historial = actualizarEstela(historial, tr.pos, N_ESTELA);
      for (let i = 0; i < historial.length; i++) pEst.set(historial[i], i * 3);
      gEstela.setDrawRange(0, historial.length); gEstela.attributes.position.needsUpdate = true;
      const cercania = fase === "llegada" ? u : 0;
      cam.position.set(tr.pos[0] * 0.5, 6 - 2 * cercania, 30 - 8 * cercania);
      cam.lookAt(tr.pos[0] * 0.8, tr.pos[1] * 0.6, 0);
      renderer.render(escena, cam);
    } catch (e) {
      console.warn("viaje: fallo al dibujar, se omite", e);
      terminar();
    }
  }

  function dispose() {
    liberado = true; terminar();
    for (const r of recursos) { try { r.dispose(); } catch (e) { /* ya liberado */ } }
    recursos.length = 0;
    escena.clear();
  }

  return { iniciar, render, omitir: terminar, get activo() { return activo; }, dispose };
}
