// Carga con cohete: escena propia (estrellas, planeta de origen y de destino holográficos, cohete, estela) dibujada en el mismo renderer.
// El avance del vuelo sigue a la carga real de la partida: la app avisa con listo() cuando el motor responde.
// No toca la partida ni el motor. Ilustrativa, no a escala.
import { pasoCarga, etapaCarga, GUARDA_CARGA_S } from "/static/viaje_datos.js?v=r15";
import { CIAN_HOLO, materialPlanetaHolo, materialHaloHolo, materialEstrellasHolo, geometriaEstrellas } from "/static/holo_material.js?v=r15";

const N_ESTELA = 220, RADIO = 6, SEPARACION = 26, ALTURA_ARCO = 15;
const CON_ANILLOS = new Set(["Saturno", "Urano"]);

// Silueta del cohete (radio, altura) girada con LatheGeometry: tobera, cuerpo largo y ojiva afilada.
const PERFIL = [[0.0, -1.5], [0.42, -1.5], [0.36, -1.25], [0.5, -1.1], [0.55, -0.6], [0.55, 0.9], [0.5, 1.3], [0.36, 1.75], [0.16, 2.1], [0.0, 2.3]];

export function crearViaje({ THREE, renderer, texturaPlaneta, paleta, alProgreso = null }) {
  const escena = new THREE.Scene();
  escena.background = new THREE.Color(0x020611);
  const cam = new THREE.PerspectiveCamera(52, 1, 0.1, 600);
  const recursos = [];            // geometrías y materiales propios (las texturas del planeta son de app.js: no se liberan aquí)
  const propio = (r) => { recursos.push(r); return r; };
  const animables = [];
  escena.add(new THREE.AmbientLight(0x6688aa, 0.6));
  const luz = new THREE.DirectionalLight(0xffffff, 2.2); luz.position.set(-20, 30, 25); escena.add(luz);

  // Estrellas en dos capas
  const mE1 = propio(materialEstrellasHolo(THREE, { tam: 2.0 })), mE2 = propio(materialEstrellasHolo(THREE, { tam: 1.3, color: 0x8fb4ff }));
  escena.add(new THREE.Points(propio(geometriaEstrellas(THREE, 900, 110, 160)), mE1), new THREE.Points(propio(geometriaEstrellas(THREE, 1600, 240, 300)), mE2));
  animables.push(mE1, mE2);

  const geoEsfera = propio(new THREE.SphereGeometry(RADIO, 64, 40));
  const geoHalo = propio(new THREE.SphereGeometry(RADIO * 1.16, 40, 24));
  function planeta(nombre) {
    const hor = paleta && paleta[nombre] && paleta[nombre].horizonte;
    const color = hor ? new THREE.Color(hor[0], hor[1], hor[2]) : new THREE.Color(0x888888);
    let mapa = null;
    try { mapa = texturaPlaneta ? texturaPlaneta(nombre) : null; } catch (e) { console.warn("viaje: textura no disponible", e); }
    const mat = propio(materialPlanetaHolo(THREE, { color, mapa })); animables.push(mat);
    const g = new THREE.Group();
    const malla = new THREE.Mesh(geoEsfera, mat);
    g.add(malla, new THREE.Mesh(geoHalo, propio(materialHaloHolo(THREE, CIAN_HOLO, 0.6))));
    if (CON_ANILLOS.has(nombre)) {
      const ga = propio(new THREE.RingGeometry(RADIO * 1.35, RADIO * 2.05, 96, 4));
      const ma = propio(new THREE.MeshBasicMaterial({ color: color.clone().lerp(new THREE.Color(CIAN_HOLO), 0.45), side: THREE.DoubleSide, transparent: true, opacity: 0.45, depthWrite: false, blending: THREE.AdditiveBlending }));
      const anillo = new THREE.Mesh(ga, ma); anillo.rotation.x = Math.PI / 2.3; g.add(anillo);
    }
    g.userData.malla = malla;
    escena.add(g); return g;
  }

  // Cohete: cuerpo blanco con franjas cian, ventanilla, tres aletas, tobera y dos llamas aditivas
  const cohete = new THREE.Group();
  const gCuerpo = propio(new THREE.LatheGeometry(PERFIL.map(([r, y]) => new THREE.Vector2(r, y)), 40));
  const mCuerpo = propio(new THREE.MeshStandardMaterial({ color: 0xe9eef5, metalness: 0.35, roughness: 0.35 }));
  cohete.add(new THREE.Mesh(gCuerpo, mCuerpo));
  const mFranja = propio(new THREE.MeshStandardMaterial({ color: 0x0f2c3d, emissive: CIAN_HOLO, emissiveIntensity: 1.4 }));
  for (const y of [-0.45, 1.05]) {
    const f = new THREE.Mesh(propio(new THREE.CylinderGeometry(0.565, 0.565, 0.1, 40, 1, true)), mFranja); f.position.y = y; cohete.add(f);
  }
  const ventana = new THREE.Mesh(propio(new THREE.CircleGeometry(0.16, 24)), propio(new THREE.MeshBasicMaterial({ color: 0xbff4ff })));
  ventana.position.set(0, 0.55, 0.56); cohete.add(ventana);
  const formaAleta = new THREE.Shape(); formaAleta.moveTo(0, 0); formaAleta.lineTo(0.75, -0.55); formaAleta.lineTo(0.75, -0.95); formaAleta.lineTo(0, -0.55); formaAleta.closePath();
  const gAleta = propio(new THREE.ExtrudeGeometry(formaAleta, { depth: 0.06, bevelEnabled: false }));
  const mAleta = propio(new THREE.MeshStandardMaterial({ color: 0x1b3a52, metalness: 0.5, roughness: 0.4, emissive: 0x062a3a }));
  for (let i = 0; i < 3; i++) {
    const a = new THREE.Mesh(gAleta, mAleta); const piv = new THREE.Group();
    a.position.set(0.5, -0.35, -0.03); piv.add(a); piv.rotation.y = (i / 3) * Math.PI * 2; cohete.add(piv);
  }
  const mLlama = propio(new THREE.MeshBasicMaterial({ color: 0xffb347, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
  const mNucleo = propio(new THREE.MeshBasicMaterial({ color: 0xcff8ff, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }));
  const llama = new THREE.Mesh(propio(new THREE.ConeGeometry(0.36, 2.2, 20, 1, true)), mLlama); llama.rotation.x = Math.PI; llama.position.y = -2.55;
  const nucleo = new THREE.Mesh(propio(new THREE.ConeGeometry(0.2, 1.2, 16, 1, true)), mNucleo); nucleo.rotation.x = Math.PI; nucleo.position.y = -2.05;
  cohete.add(llama, nucleo);
  const luzMotor = new THREE.PointLight(0xffa040, 6, 14, 2); luzMotor.position.y = -2; cohete.add(luzMotor);
  escena.add(cohete);

  // Estela: puntos que se apagan con la edad (color por vértice)
  const pEst = new Float32Array(N_ESTELA * 3), cEst = new Float32Array(N_ESTELA * 3);
  const gEstela = propio(new THREE.BufferGeometry());
  gEstela.setAttribute("position", new THREE.BufferAttribute(pEst, 3)); gEstela.setAttribute("color", new THREE.BufferAttribute(cEst, 3));
  gEstela.setDrawRange(0, 0);
  // punto suave (degradado radial) para que la estela sea un humo luminoso y no cuadrados
  const lienzoPunto = document.createElement("canvas"); lienzoPunto.width = lienzoPunto.height = 64;
  const cx = lienzoPunto.getContext("2d"), grad = cx.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)"); grad.addColorStop(0.35, "rgba(255,255,255,0.45)"); grad.addColorStop(1, "rgba(255,255,255,0)");
  cx.fillStyle = grad; cx.fillRect(0, 0, 64, 64);
  const texPunto = propio(new THREE.CanvasTexture(lienzoPunto));
  const estela = new THREE.Points(gEstela, propio(new THREE.PointsMaterial({ size: 1.1, map: texPunto, vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })));
  estela.frustumCulled = false; escena.add(estela);

  // Onda de polvo al despegar y al aterrizar
  const mOnda = propio(new THREE.MeshBasicMaterial({ color: CIAN_HOLO, transparent: true, opacity: 0, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
  const onda = new THREE.Mesh(propio(new THREE.RingGeometry(0.9, 1, 64)), mOnda); escena.add(onda);

  let pA = null, pB = null, activo = false, liberado = false, resolver = null, listoMotor = false;
  let t0 = 0, tPrev = 0, d = 0, cola = [], ondaT = -1, ondaEn = null, tFin = -1, ultimaEtapa = "";
  const P = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
  const pos = new THREE.Vector3(), tg = new THREE.Vector3(), arriba = new THREE.Vector3(0, 1, 0), qVuelo = new THREE.Quaternion(), qVertical = new THREE.Quaternion();
  const camPos = new THREE.Vector3(), camMira = new THREE.Vector3(), tmp = new THREE.Vector3();

  // Bézier cúbica: de la superficie del origen, arco por encima, a la superficie del destino
  function bezier(u, out) {
    const a = 1 - u;
    return out.set(0, 0, 0).addScaledVector(P[0], a * a * a).addScaledVector(P[1], 3 * a * a * u).addScaledVector(P[2], 3 * a * u * u).addScaledVector(P[3], u * u * u);
  }
  function tangente(u, out) {
    const a = 1 - u;
    out.set(0, 0, 0).addScaledVector(tmp.subVectors(P[1], P[0]), 3 * a * a).addScaledVector(tmp.subVectors(P[2], P[1]), 6 * a * u).addScaledVector(tmp.subVectors(P[3], P[2]), 3 * u * u);
    return out.lengthSq() > 1e-8 ? out.normalize() : out.set(0, 1, 0);
  }
  function lanzarOnda(en) { ondaT = 0; ondaEn = en; }

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
        pA.position.set(-SEPARACION, -4, 0); pB.position.set(SEPARACION, -4, -6);
        P[0].copy(pA.position).add(new THREE.Vector3(0, RADIO + 1.5, 0));
        P[1].copy(P[0]).add(new THREE.Vector3(4, ALTURA_ARCO, 4));
        P[3].copy(pB.position).add(new THREE.Vector3(0, RADIO + 1.5, 0));
        P[2].copy(P[3]).add(new THREE.Vector3(-4, ALTURA_ARCO, 4));
        cola = []; d = 0; listoMotor = false; tFin = -1; ultimaEtapa = "";
        t0 = tPrev = performance.now(); activo = true;
        bezier(0, pos); camPos.set(pos.x + 4, pos.y + 4, pos.z + 22); camMira.copy(pos);
        lanzarOnda(P[0]);
        const w = renderer.domElement.clientWidth || 800, h = renderer.domElement.clientHeight || 600;
        cam.aspect = w / h; cam.updateProjectionMatrix();
      } catch (e) {
        console.warn("viaje: no se pudo preparar la escena", e);
        activo = true; terminar();
      }
    });
  }

  // La app avisa cuando el motor respondió: el cohete termina el vuelo y aterriza
  function listo() { listoMotor = true; }

  function render() {
    if (!activo) return;
    try {
      const ahora = performance.now();
      const t = (ahora - t0) / 1000, dt = Math.min(0.05, (ahora - tPrev) / 1000); tPrev = ahora;
      const w2 = renderer.domElement.clientWidth || 800, h2 = renderer.domElement.clientHeight || 600;
      if (Math.abs(cam.aspect - w2 / h2) > 1e-3) { cam.aspect = w2 / h2; cam.updateProjectionMatrix(); }
      d = pasoCarga(d, t, listoMotor || t > GUARDA_CARGA_S, dt);
      const etapa = etapaCarga(d);
      if (etapa !== ultimaEtapa) { if (etapa === "aterrizado") lanzarOnda(P[3]); ultimaEtapa = etapa; }
      try { if (alProgreso) alProgreso(d, etapa); } catch (e) { /* la tarjeta no debe cortar el vuelo */ }

      // Posición y orientación: nariz según la tangente; al final se endereza (aterriza de cola, con retropropulsión)
      const u = d * d * (3 - 2 * d) * 0.85 + d * 0.15;
      bezier(u, pos); tangente(u, tg);
      cohete.position.copy(pos);
      qVuelo.setFromUnitVectors(arriba, tg);
      const enderezar = Math.min(1, Math.max(0, (d - 0.86) / 0.12));
      qVertical.identity();
      cohete.quaternion.copy(qVuelo).slerp(qVertical, enderezar);
      const empuje = etapa === "aterrizado" ? Math.max(0, 1 - (t - tFin) * 2) : 1;
      if (etapa === "aterrizado" && tFin < 0) tFin = t;
      const pulso = 0.85 + 0.25 * Math.sin(t * 38) + 0.1 * Math.sin(t * 91);
      llama.scale.set(1, pulso * empuje * (enderezar > 0 ? 0.7 : 1) + 0.001, 1); nucleo.scale.set(1, pulso * empuje + 0.001, 1);
      luzMotor.intensity = 6 * empuje;

      // Estela con el color de la llama, que se apaga con la edad
      if (empuje > 0.05) { tmp.set(0, -1.9, 0).applyQuaternion(cohete.quaternion).add(pos); cola.push([tmp.x, tmp.y, tmp.z]); }
      if (cola.length > N_ESTELA) cola.splice(0, cola.length - N_ESTELA);
      for (let i = 0; i < cola.length; i++) {
        const edad = 1 - i / cola.length, k = Math.pow(1 - edad, 1.6);
        pEst.set(cola[i], i * 3); cEst.set([1.0 * k, 0.62 * k, 0.28 * k + 0.25 * k * edad], i * 3);
      }
      gEstela.setDrawRange(0, cola.length); gEstela.attributes.position.needsUpdate = true; gEstela.attributes.color.needsUpdate = true;

      // Onda en la superficie
      if (ondaT >= 0) {
        ondaT += dt; const k = Math.min(1, ondaT / 1.2);
        onda.position.copy(ondaEn).add(tmp.set(0, -1.4, 0)); onda.rotation.x = -Math.PI / 2;
        onda.scale.setScalar(0.5 + k * 7); mOnda.opacity = 0.7 * (1 - k);
        if (k >= 1) { ondaT = -1; mOnda.opacity = 0; }
      }

      for (const m of animables) m.uniforms.uTiempo.value = t;
      pA.userData.malla.rotation.y += 0.002; pB.userData.malla.rotation.y += 0.003;

      // Cámara de seguimiento suave: lateral y algo por delante del cohete
      tmp.set(pos.x + 3 - (u - 0.5) * 10, pos.y + 3.5, pos.z + 20 - Math.sin(u * Math.PI) * 4);
      camPos.lerp(tmp, Math.min(1, dt * 2.2));
      tmp.copy(pos).lerp(pB.position, 0.18 + 0.25 * u);
      camMira.lerp(tmp, Math.min(1, dt * 3));
      cam.position.copy(camPos); cam.lookAt(camMira);
      renderer.render(escena, cam);

      if (tFin >= 0 && t - tFin > 0.6) terminar();   // un instante en superficie antes de entrar a la partida
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

  return { iniciar, listo, render, omitir: terminar, get activo() { return activo; }, get progreso() { return d; }, dispose };
}
