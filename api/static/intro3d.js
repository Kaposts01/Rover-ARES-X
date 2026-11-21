// Introducción: sistema solar (Sol y los 8 perfiles) dibujado en el mismo renderer de la partida. Ilustración, no a escala.
// No toca la partida ni el motor: al elegir un cuerpo solo avisa con alElegir(nombre).
import { CUERPOS_INTRO, RADIO_SOL_ESCENA, DURACION_VUELO_S, fasesVuelo, pasoVuelo, posicionOrbital, modoIntro } from "./intro_datos.js?v=r14";

const N_ESTRELLAS = 1200;
const CON_ANILLOS = new Set(["Saturno", "Urano"]);

// opciones: THREE, renderer, OrbitControls, texturaPlaneta(nombre), paleta, alElegir(nombre), alPasar(nombre|null), reducido
export function crearIntro({ THREE, renderer, OrbitControls, texturaPlaneta, paleta, alElegir, alPasar, reducido = false }) {
  const modo = modoIntro(reducido);
  const animado = modo === "animado";
  const escena = new THREE.Scene();
  escena.background = new THREE.Color(0x02030a);
  const cam = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
  const recursos = [];   // geometrías y materiales propios (las texturas son de la app y quedan en su caché: no se liberan aquí)
  const propio = (r) => { recursos.push(r); return r; };
  escena.add(new THREE.AmbientLight(0x8899bb, 0.55));
  const luzSol = new THREE.PointLight(0xfff2d0, 3.2, 0, 0); escena.add(luzSol);

  // Estrellas
  const pe = new Float32Array(N_ESTRELLAS * 3);
  for (let i = 0; i < N_ESTRELLAS; i++) {
    const r = 200 + Math.random() * 80, a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1);
    pe.set([r * Math.sin(b) * Math.cos(a), r * Math.cos(b), r * Math.sin(b) * Math.sin(a)], i * 3);
  }
  const gEst = propio(new THREE.BufferGeometry()); gEst.setAttribute("position", new THREE.BufferAttribute(pe, 3));
  escena.add(new THREE.Points(gEst, propio(new THREE.PointsMaterial({ color: 0xffffff, size: 0.9, sizeAttenuation: false }))));

  // Sol: esfera emisiva con un halo aditivo
  const gSol = propio(new THREE.SphereGeometry(RADIO_SOL_ESCENA, 32, 24));
  const sol = new THREE.Mesh(gSol, propio(new THREE.MeshBasicMaterial({ color: 0xffd36a })));
  const halo = new THREE.Mesh(propio(new THREE.SphereGeometry(RADIO_SOL_ESCENA * 1.35, 24, 16)),
    propio(new THREE.MeshBasicMaterial({ color: 0xffa530, transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending, depthWrite: false })));
  escena.add(sol, halo);

  // Planetas y órbitas
  const geoEsfera = propio(new THREE.SphereGeometry(1, 32, 24));
  const cuerpos = [];   // { datos, grupo, malla, material, etiqueta }
  for (const c of CUERPOS_INTRO) {
    const hor = paleta && paleta[c.nombre] && paleta[c.nombre].horizonte;
    const color = hor ? new THREE.Color(hor[0], hor[1], hor[2]) : new THREE.Color(0x888888);
    const material = propio(new THREE.MeshLambertMaterial({ color }));
    const malla = new THREE.Mesh(geoEsfera, material); malla.scale.setScalar(c.radioEscena); malla.userData.nombre = c.nombre;
    const grupo = new THREE.Group(); grupo.add(malla);
    if (CON_ANILLOS.has(c.nombre)) {
      const ga = propio(new THREE.RingGeometry(c.radioEscena * 1.35, c.radioEscena * 2.1, 64));
      const ma = propio(new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, transparent: true, opacity: 0.5 }));
      const anillo = new THREE.Mesh(ga, ma); anillo.rotation.x = Math.PI / 2.3; grupo.add(anillo);
    }
    const p = posicionOrbital(0, c); grupo.position.set(p[0], p[1], p[2]);
    escena.add(grupo);
    const pts = []; for (let i = 0; i < 128; i++) { const a = (i / 128) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * c.distanciaEscena, 0, Math.sin(a) * c.distanciaEscena)); }
    escena.add(new THREE.LineLoop(propio(new THREE.BufferGeometry().setFromPoints(pts)),
      propio(new THREE.LineBasicMaterial({ color: 0x5a6a90, transparent: true, opacity: 0.4 }))));
    cuerpos.push({ datos: c, grupo, malla, material, etiqueta: null });
  }

  // Etiquetas DOM (botones: Tab recorre los planetas, Intro elige). Solo textContent.
  const capa = document.createElement("div");
  capa.className = "in-etiquetas";
  capa.setAttribute("role", "list");
  for (const k of cuerpos) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "in-etiqueta"; b.textContent = k.datos.nombre; b.setAttribute("role", "listitem");
    b.setAttribute("aria-label", `Elegir ${k.datos.nombre}`);
    b.addEventListener("click", () => elegir(k.datos.nombre));
    b.addEventListener("mouseenter", () => pasar(k.datos.nombre));
    b.addEventListener("mouseleave", () => pasar(null));
    b.addEventListener("focus", () => pasar(k.datos.nombre));
    b.addEventListener("blur", () => pasar(null));
    k.etiqueta = b; capa.append(b);
  }
  document.body.append(capa);

  // Cámara y controles propios sobre el mismo canvas; los de la partida los deshabilita la app mientras dura
  const controles = new OrbitControls(cam, renderer.domElement);
  controles.enableDamping = true; controles.enablePan = false;
  controles.minDistance = 14; controles.maxDistance = 260; controles.enabled = animado;
  let sinMover = true;
  controles.addEventListener("start", () => { sinMover = false; });

  function encuadrar(aspecto) {
    // la distancia crece cuando la pantalla es estrecha para que quepa Neptuno
    const radio = CUERPOS_INTRO[CUERPOS_INTRO.length - 1].distanciaEscena + 6;
    const fov = (cam.fov * Math.PI) / 180;
    const vertical = radio / Math.tan(fov / 2) * 0.62, horizontal = radio / (Math.tan(fov / 2) * aspecto);
    const d = Math.max(vertical, horizontal);
    cam.position.set(0, d * 0.55, d * 0.83); controles.target.set(0, 0, 0); controles.update();
  }

  let activo = false, liberado = false, resolver = null, vuelo = null, aspectoPrevio = 0, t0 = 0, primerCuadro = false;
  const raycaster = new THREE.Raycaster(), puntero = new THREE.Vector2(), v = new THREE.Vector3(), w = new THREE.Vector3();
  let hover = null;

  function pasar(nombre) {
    if (nombre === hover) return;
    hover = nombre;
    try { if (alPasar) alPasar(nombre); } catch (e) { console.warn("intro: fallo al mostrar la tarjeta", e); }
  }
  function cuerpoBajo(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    puntero.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(puntero, cam);
    const hit = raycaster.intersectObjects(cuerpos.map((k) => k.malla), false)[0];
    return hit ? hit.object.userData.nombre : null;
  }
  let abajo = null;
  const onMover = (ev) => { if (!activo || vuelo) return; const n = cuerpoBajo(ev); pasar(n); renderer.domElement.style.cursor = n ? "pointer" : ""; };
  const onAbajo = (ev) => { abajo = { x: ev.clientX, y: ev.clientY }; };
  const onArriba = (ev) => {
    if (!activo || vuelo || !abajo) return;
    const arrastre = Math.hypot(ev.clientX - abajo.x, ev.clientY - abajo.y); abajo = null;
    if (arrastre > 5) return;   // fue un giro de cámara, no una elección
    const n = cuerpoBajo(ev); if (n) elegir(n);
  };
  renderer.domElement.addEventListener("pointermove", onMover);
  renderer.domElement.addEventListener("pointerdown", onAbajo);
  renderer.domElement.addEventListener("pointerup", onArriba);

  function terminar() {
    if (!activo) return;
    activo = false;
    const r = resolver; resolver = null; if (r) r();
  }

  function elegir(nombre) {
    if (!activo || vuelo) return;
    const k = cuerpos.find((x) => x.datos.nombre === nombre); if (!k) return;
    const finalizar = () => { try { if (alElegir) alElegir(nombre); } catch (e) { console.warn("intro: fallo al elegir", e); } terminar(); };
    if (!animado) { finalizar(); return; }   // movimiento reducido: corte directo
    controles.enabled = false;
    k.grupo.getWorldPosition(v);
    const dir = w.copy(v).normalize();
    const cierre = k.datos.radioEscena * 5 + 4;
    vuelo = { t0: performance.now(), k, desde: cam.position.clone(), objDesde: controles.target.clone(),
      hasta: v.clone().add(dir.multiplyScalar(cierre)).add(new THREE.Vector3(0, cierre * 0.35, 0)), finalizar, fases: fasesVuelo(DURACION_VUELO_S) };
  }

  function posicionarEtiquetas() {
    const w2 = renderer.domElement.clientWidth || 800, h2 = renderer.domElement.clientHeight || 600;
    for (const k of cuerpos) {
      k.grupo.getWorldPosition(v);
      v.y += k.datos.radioEscena * 1.15;
      v.project(cam);
      const visible = v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05;
      const x = Math.round(((v.x + 1) / 2) * w2), y = Math.round(((1 - v.y) / 2) * h2);
      if (k.etiqueta._x !== x || k.etiqueta._y !== y || k.etiqueta._vis !== visible) {   // solo si cambió de posición
        k.etiqueta._x = x; k.etiqueta._y = y; k.etiqueta._vis = visible;
        k.etiqueta.style.transform = `translate(${x}px, ${y}px) translate(-50%, -100%)`;
        k.etiqueta.style.visibility = visible ? "visible" : "hidden";
      }
    }
  }

  // Texturas de a una con setTimeout(0): la pantalla aparece enseguida y los planetas se visten en los cuadros siguientes
  async function vestirPlanetas() {
    for (const k of cuerpos) {
      await new Promise((r) => setTimeout(r, 0));
      if (liberado || !activo) return;
      try {
        const mapa = texturaPlaneta ? texturaPlaneta(k.datos.nombre) : null;
        if (mapa) { k.material.map = mapa; k.material.color.set(0xffffff); k.material.needsUpdate = true; }
      } catch (e) { console.warn("intro: textura no disponible", e); }
    }
  }

  function iniciar() {
    if (liberado || activo) return Promise.resolve();
    return new Promise((res) => {
      resolver = res;
      try {
        activo = true; t0 = performance.now();
        const w2 = renderer.domElement.clientWidth || 800, h2 = renderer.domElement.clientHeight || 600;
        cam.aspect = w2 / h2; aspectoPrevio = cam.aspect; cam.updateProjectionMatrix();
        encuadrar(cam.aspect);
        vestirPlanetas();
      } catch (e) {
        console.warn("intro: no se pudo preparar la escena", e);
        activo = true; terminar();
      }
    });
  }

  function render() {
    if (!activo) return;
    try {
      const t = (performance.now() - t0) / 1000;
      const w2 = renderer.domElement.clientWidth || 800, h2 = renderer.domElement.clientHeight || 600;
      const aspecto = w2 / h2;
      if (Math.abs(aspecto - aspectoPrevio) > 1e-3) {
        aspectoPrevio = aspecto; cam.aspect = aspecto; cam.updateProjectionMatrix();
        if (sinMover) encuadrar(aspecto);
      }
      if (animado) {
        for (const k of cuerpos) {
          const p = posicionOrbital(t, k.datos); k.grupo.position.set(p[0], p[1], p[2]);
          k.malla.rotation.y += 0.004;
        }
        sol.rotation.y += 0.002;
      }
      if (vuelo) {
        const u = (performance.now() - vuelo.t0) / 1000 / vuelo.fases.aproximacion;
        const s = pasoVuelo(u);
        vuelo.k.grupo.getWorldPosition(w);
        cam.position.lerpVectors(vuelo.desde, vuelo.hasta, s);
        controles.target.lerpVectors(vuelo.objDesde, w, s);
        cam.lookAt(controles.target);
        if ((performance.now() - vuelo.t0) / 1000 >= vuelo.fases.total) { const f = vuelo.finalizar; vuelo = null; f(); return; }
      } else if (animado) controles.update();
      posicionarEtiquetas();
      renderer.render(escena, cam);
      primerCuadro = true;
    } catch (e) {
      console.warn("intro: fallo al dibujar, se omite", e);
      terminar();
    }
  }

  function dispose() {
    liberado = true; terminar();
    renderer.domElement.removeEventListener("pointermove", onMover);
    renderer.domElement.removeEventListener("pointerdown", onAbajo);
    renderer.domElement.removeEventListener("pointerup", onArriba);
    renderer.domElement.style.cursor = "";
    try { controles.dispose(); } catch (e) { /* ya liberado */ }
    capa.remove();
    for (const r of recursos) { try { r.dispose(); } catch (e) { /* ya liberado */ } }
    recursos.length = 0;
    escena.clear();
  }

  return { iniciar, render, omitir: terminar, get activo() { return activo; }, get primerCuadro() { return primerCuadro; }, modo, dispose };
}
