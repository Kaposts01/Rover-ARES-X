// Introducción: sistema solar en estilo «sala de control» (holograma) dibujado en el mismo renderer de la partida. Ilustración, no a escala.
// No toca la partida ni el motor: al elegir un cuerpo solo avisa con alElegir(nombre).
import { CUERPOS_INTRO, RADIO_SOL_ESCENA, DURACION_VUELO_S, fasesVuelo, pasoVuelo, posicionOrbital, modoIntro } from "./intro_datos.js?v=r14";
import { CIAN_HOLO, materialPlanetaHolo, materialHaloHolo, materialSolHolo, materialOrbitaHolo, geometriaOrbita,
  materialBarridoHolo, materialEstrellasHolo, geometriaEstrellas, crearReticula } from "./holo_material.js?v=r14";

const N_ESTRELLAS_CERCA = 900, N_ESTRELLAS_LEJOS = 1800;
const CON_ANILLOS = new Set(["Saturno", "Urano"]);
const ZONA_FACTOR = 1.9;       // la zona de clic mide 1,9 veces el radio del planeta
const ZONA_MIN_PX = 26;        // y nunca baja de 26 px de radio en pantalla (Mercurio, Tierra y Marte son diminutos)

// opciones: THREE, renderer, OrbitControls, texturaPlaneta(nombre), paleta, alElegir(nombre), alPasar(nombre|null), reducido
export function crearIntro({ THREE, renderer, OrbitControls, texturaPlaneta, paleta, alElegir, alPasar, reducido = false }) {
  const modo = modoIntro(reducido);
  const animado = modo === "animado";
  const escena = new THREE.Scene();
  escena.background = new THREE.Color(0x020611);
  const cam = new THREE.PerspectiveCamera(50, 1, 0.1, 600);
  const recursos = [];   // geometrías y materiales propios (las texturas son de la app y quedan en su caché: no se liberan aquí)
  const propio = (r) => { recursos.push(r); return r; };
  const animables = [];  // materiales con uTiempo

  // Estrellas en dos capas (la cercana gira un poco más rápido: da profundidad)
  const matCerca = propio(materialEstrellasHolo(THREE, { tam: 2.2, color: 0xd8f4ff }));
  const matLejos = propio(materialEstrellasHolo(THREE, { tam: 1.4, color: 0x8fb4ff }));
  const estrellasCerca = new THREE.Points(propio(geometriaEstrellas(THREE, N_ESTRELLAS_CERCA, 120, 170)), matCerca);
  const estrellasLejos = new THREE.Points(propio(geometriaEstrellas(THREE, N_ESTRELLAS_LEJOS, 260, 320)), matLejos);
  escena.add(estrellasCerca, estrellasLejos);
  animables.push(matCerca, matLejos);

  // Plano orbital: rejilla polar tenue y barrido de radar
  const radioSistema = CUERPOS_INTRO[CUERPOS_INTRO.length - 1].distanciaEscena + 8;
  const rejilla = new THREE.PolarGridHelper(radioSistema, 24, 10, 128, 0x1d4f66, 0x0f2c3d);
  for (const m of [].concat(rejilla.material)) { m.transparent = true; m.opacity = 0.35; m.depthWrite = false; propio(m); }
  propio(rejilla.geometry);
  rejilla.position.y = -0.05;
  escena.add(rejilla);
  const matBarrido = propio(materialBarridoHolo(THREE));
  const barrido = new THREE.Mesh(propio(new THREE.CircleGeometry(radioSistema, 96)), matBarrido);
  barrido.rotation.x = -Math.PI / 2; barrido.position.y = -0.02;
  escena.add(barrido);

  // Sol: plasma animado, halo y anillos de escaneo que se expanden
  const matSol = propio(materialSolHolo(THREE)); animables.push(matSol);
  const sol = new THREE.Mesh(propio(new THREE.SphereGeometry(RADIO_SOL_ESCENA, 48, 32)), matSol);
  const halo = new THREE.Mesh(propio(new THREE.SphereGeometry(RADIO_SOL_ESCENA * 1.5, 32, 24)), propio(materialHaloHolo(THREE, 0xffb347, 1.1)));
  escena.add(sol, halo);
  const ondas = [];
  const geoOnda = propio(new THREE.RingGeometry(0.97, 1, 96));
  for (let i = 0; i < 3; i++) {
    const m = propio(new THREE.MeshBasicMaterial({ color: CIAN_HOLO, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }));
    const o = new THREE.Mesh(geoOnda, m); o.rotation.x = -Math.PI / 2; o.userData.fase = i / 3;
    ondas.push(o); escena.add(o);
  }

  // Planetas holográficos, halo de borde y órbitas discontinuas
  const geoEsfera = propio(new THREE.SphereGeometry(1, 48, 32));
  const geoHalo = propio(new THREE.SphereGeometry(1.18, 32, 24));
  const cuerpos = [];   // { datos, grupo, malla, material, orbita, etiqueta }
  for (const c of CUERPOS_INTRO) {
    const hor = paleta && paleta[c.nombre] && paleta[c.nombre].horizonte;
    const color = hor ? new THREE.Color(hor[0], hor[1], hor[2]) : new THREE.Color(0x888888);
    const material = propio(materialPlanetaHolo(THREE, { color })); animables.push(material);
    const malla = new THREE.Mesh(geoEsfera, material); malla.scale.setScalar(c.radioEscena); malla.userData.nombre = c.nombre;
    const haloP = new THREE.Mesh(geoHalo, propio(materialHaloHolo(THREE, CIAN_HOLO, 0.55))); haloP.scale.setScalar(c.radioEscena);
    // Zona de clic invisible y más grande que el planeta (su escala se ajusta en cada cuadro para no bajar de ZONA_MIN_PX)
    const zona = new THREE.Mesh(geoEsfera, propio(new THREE.MeshBasicMaterial({ visible: false }))); zona.visible = false; zona.userData.nombre = c.nombre;
    const grupo = new THREE.Group(); grupo.add(malla, haloP, zona);
    if (CON_ANILLOS.has(c.nombre)) {
      const ga = propio(new THREE.RingGeometry(c.radioEscena * 1.35, c.radioEscena * 2.1, 96, 4));
      const ma = propio(new THREE.MeshBasicMaterial({ color: color.clone().lerp(new THREE.Color(CIAN_HOLO), 0.45), side: THREE.DoubleSide, transparent: true, opacity: 0.45, depthWrite: false, blending: THREE.AdditiveBlending }));
      const anillo = new THREE.Mesh(ga, ma); anillo.rotation.x = Math.PI / 2.3; grupo.add(anillo);
      const ma2 = propio(new THREE.MeshBasicMaterial({ color: CIAN_HOLO, wireframe: true, transparent: true, opacity: 0.18, depthWrite: false }));
      const trama = new THREE.Mesh(ga, ma2); trama.rotation.x = Math.PI / 2.3; grupo.add(trama);
    }
    const p = posicionOrbital(0, c); grupo.position.set(p[0], p[1], p[2]);
    escena.add(grupo);
    const matOrbita = propio(materialOrbitaHolo(THREE)); animables.push(matOrbita);
    matOrbita.uniforms.uTramos.value = Math.round(c.distanciaEscena * 3);
    const orbita = new THREE.LineLoop(propio(geometriaOrbita(THREE, c.distanciaEscena)), matOrbita);
    escena.add(orbita);
    cuerpos.push({ datos: c, grupo, malla, zona, material, orbita, etiqueta: null, boton: null });
  }

  // Retícula sobre el planeta señalado
  const reticula = crearReticula(THREE);
  for (const r of reticula.userData.recursos) propio(r);
  escena.add(reticula);
  function actualizarResaltes(t) {
    const k = hover ? cuerpos.find((x) => x.datos.nombre === hover) : null;
    for (const x of cuerpos) {
      if (x.boton) x.boton.classList.toggle("activo", x === k);
      if (x.etiqueta) x.etiqueta.classList.toggle("activo", x === k);
      const u = x.material.uniforms.uResalte;
      u.value += ((x === k ? 1 : 0) - u.value) * 0.15;
      x.orbita.material.uniforms.uResalte.value = u.value;
    }
    reticula.visible = !!k;
    if (k) {
      k.grupo.getWorldPosition(reticula.position);
      reticula.scale.setScalar(k.datos.radioEscena * (1.25 + 0.05 * Math.sin(t * 4)));
      reticula.quaternion.copy(cam.quaternion);
      reticula.rotateZ(t * 0.8);
    }
  }
  function animarDecorado(t) {
    for (const m of animables) m.uniforms.uTiempo.value = t;
    matBarrido.uniforms.uAngulo.value = animado ? t * 0.6 : 0.8;
    for (const o of ondas) {
      const f = animado ? (t * 0.18 + o.userData.fase) % 1 : o.userData.fase;
      o.scale.setScalar(RADIO_SOL_ESCENA * 1.3 + f * radioSistema * 0.9);
      o.material.opacity = 0.35 * (1 - f) * (1 - f);
    }
    if (animado) { estrellasCerca.rotation.y = t * 0.004; estrellasLejos.rotation.y = t * 0.0015; }
    const escala = renderer.getPixelRatio ? renderer.getPixelRatio() : 1;
    matCerca.uniforms.uEscala.value = escala; matLejos.uniforms.uEscala.value = escala;
  }

  // Etiquetas DOM (botones: Tab recorre los planetas, Intro elige). Solo textContent.
  const capa = document.createElement("div");
  capa.className = "in-etiquetas";
  capa.setAttribute("role", "list");
  for (const k of cuerpos) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "in-etiqueta"; b.textContent = k.datos.nombre; b.setAttribute("role", "listitem");
    b.setAttribute("aria-label", `Elegir ${k.datos.nombre}`);
    b.tabIndex = -1;   // el teclado usa la lista fija de abajo; estas etiquetas siguen el planeta y solo sirven al ratón
    b.addEventListener("click", () => elegir(k.datos.nombre));
    b.addEventListener("mouseenter", () => pasar(k.datos.nombre));
    b.addEventListener("mouseleave", () => pasar(null));
    k.etiqueta = b; capa.append(b);
  }
  // Lista fija de planetas (alternativa al clic en 3D): Tab recorre, Intro elige, y al enfocar se ve la ficha
  const lista = document.createElement("nav");
  lista.className = "in-lista"; lista.setAttribute("aria-label", "Elegir un planeta");
  for (const k of cuerpos) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "in-lista-boton"; b.textContent = k.datos.nombre;
    b.addEventListener("click", () => elegir(k.datos.nombre));
    b.addEventListener("mouseenter", () => pasar(k.datos.nombre));
    b.addEventListener("mouseleave", () => pasar(null));
    b.addEventListener("focus", () => pasar(k.datos.nombre));
    b.addEventListener("blur", () => pasar(null));
    k.boton = b; lista.append(b);
  }
  const dialogo = document.querySelector(".in-capa");   // las etiquetas viven dentro del diálogo aria-modal (foco y lectores de pantalla)
  capa.setAttribute("aria-label", "Planetas del sistema solar");
  (dialogo || document.body).append(capa, lista);

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
  let tOrbital = 0, velOrbital = 1, ultimoCuadro = performance.now();   // reloj de las órbitas: se detiene sin afectar al resto de la animación

  function pasar(nombre) {
    if (nombre === hover) return;
    hover = nombre;
    try { if (alPasar) alPasar(nombre); } catch (e) { console.warn("intro: fallo al mostrar la tarjeta", e); }
  }
  function cuerpoBajo(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    puntero.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(puntero, cam);
    const hit = raycaster.intersectObjects(cuerpos.map((k) => k.zona), false)[0];   // zonas generosas: el rayo usa el tamaño real del canvas, sin depender del devicePixelRatio
    return hit ? hit.object.userData.nombre : null;
  }
  let abajo = null;
  const onMover = (ev) => { if (!activo || vuelo) return; const n = cuerpoBajo(ev); pasar(n); renderer.domElement.style.cursor = n ? "pointer" : ""; };
  const onSalir = () => { if (!activo || vuelo) return; pasar(null); renderer.domElement.style.cursor = ""; };   // el puntero salió del lienzo: la órbita sigue
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
  renderer.domElement.addEventListener("pointerleave", onSalir);

  // Ajusta cada zona de clic: 1,9 veces el radio y, como mínimo, ZONA_MIN_PX de radio en pantalla
  function ajustarZonas() {
    const alto = renderer.domElement.clientHeight || 600, tanMitad = Math.tan((cam.fov * Math.PI) / 360);
    for (const k of cuerpos) {
      k.grupo.getWorldPosition(v);
      const mundoPorPx = (2 * cam.position.distanceTo(v) * tanMitad) / alto;
      const r = Math.max(k.datos.radioEscena * ZONA_FACTOR, ZONA_MIN_PX * mundoPorPx);
      k.zona.scale.setScalar(r);   // geoEsfera tiene radio 1 y el grupo escala 1
    }
  }

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
        if (mapa) { k.material.uniforms.uMapa.value = mapa; k.material.uniforms.uConMapa.value = 1; }
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
      const ahora = performance.now(), dt = Math.min(0.1, (ahora - ultimoCuadro) / 1000); ultimoCuadro = ahora;
      if (animado) {
        // Con un planeta señalado (ratón, lista o etiqueta) las órbitas se frenan con suavidad hasta detenerse; al soltarlo, retoman
        velOrbital += ((hover ? 0 : 1) - velOrbital) * (1 - Math.exp(-dt * 7));
        tOrbital += dt * velOrbital;
        for (const k of cuerpos) {
          const p = posicionOrbital(tOrbital, k.datos); k.grupo.position.set(p[0], p[1], p[2]);
          k.malla.rotation.y += 0.004 * velOrbital;
        }
        sol.rotation.y += 0.002;
      }
      ajustarZonas();
      if (vuelo) {
        const u = (performance.now() - vuelo.t0) / 1000 / vuelo.fases.aproximacion;
        const s = pasoVuelo(u);
        vuelo.k.grupo.getWorldPosition(w);
        cam.position.lerpVectors(vuelo.desde, vuelo.hasta, s);
        controles.target.lerpVectors(vuelo.objDesde, w, s);
        cam.lookAt(controles.target);
        if ((performance.now() - vuelo.t0) / 1000 >= vuelo.fases.total) { const f = vuelo.finalizar; vuelo = null; f(); return; }
      } else if (animado) controles.update();
      animarDecorado(t);
      actualizarResaltes(t);
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
    renderer.domElement.removeEventListener("pointerleave", onSalir);
    renderer.domElement.style.cursor = "";
    try { controles.dispose(); } catch (e) { /* ya liberado */ }
    capa.remove(); lista.remove();
    for (const r of recursos) { try { r.dispose(); } catch (e) { /* ya liberado */ } }
    recursos.length = 0;
    escena.clear();
  }

  return { iniciar, render, omitir: terminar, get activo() { return activo; }, get primerCuadro() { return primerCuadro; }, modo, dispose };
}
