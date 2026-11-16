// Efectos visuales de los eventos del entorno (ev3-d41) y modelo de la sonda (ev3-d39, planetas gigantes).
// Todo es visual: el motor decide los eventos. Los disparadores de aquí son para QA con datos simulados.
import * as THREE from "three";

// ---------- sonda atmosférica (en gigantes sustituye al rover) ----------
// Cuerpo lenticular con estabilizadores en cola, paneles y antena integrados, y cuatro rotores de
// sustentación bajo las alas. Frente = +x, igual que el rover. La sombra es un disco aparte (userData.sombra).
const TEXTURA_SOMBRA = (() => {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 128;
  const x = c.getContext("2d");
  const g = x.createRadialGradient(64, 64, 4, 64, 64, 64);
  g.addColorStop(0, "rgba(0,0,0,0.85)");
  g.addColorStop(1, "rgba(0,0,0,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();

export function crearSonda() {
  const grupo = new THREE.Group();
  const casco = new THREE.MeshStandardMaterial({ color: 0xd9dfe8, roughness: 0.3, metalness: 0.45 });
  const negro = new THREE.MeshStandardMaterial({ color: 0x1d2330, roughness: 0.45, metalness: 0.5 });
  const panel = new THREE.MeshStandardMaterial({ color: 0x1f3c76, roughness: 0.3, metalness: 0.2, emissive: 0x0b2350, emissiveIntensity: 0.6 });
  const led = new THREE.MeshBasicMaterial({ color: 0x5fd3ff, toneMapped: false });
  const aire = new THREE.MeshStandardMaterial({ color: 0x9fd8ff, transparent: true, opacity: 0.35, depthWrite: false });

  // Cuerpo lenticular: esfera aplanada y alargada
  const cuerpo = new THREE.Mesh(new THREE.SphereGeometry(0.25, 32, 16), casco);
  cuerpo.scale.set(1.6, 0.42, 1.0);
  grupo.add(cuerpo);
  // Morro con sensor de presión y temperatura
  const morro = new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 10), aire);
  morro.position.set(0.4, 0.02, 0);
  grupo.add(morro);
  // Estabilizadores en cola: horizontal y vertical en cruz
  const aletaH = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.012, 0.16), negro);
  aletaH.position.set(-0.36, 0, 0);
  const aletaV = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.16, 0.012), negro);
  aletaV.position.set(-0.36, 0, 0);
  const deriva = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.2, 0.012), negro);
  deriva.position.set(-0.36, 0.09, 0);
  grupo.add(aletaH, aletaV, deriva);

  // Alas con paneles solares integrados y diedro suave
  grupo.userData.rotores = [];
  for (const z of [-1, 1]) {
    // Ala fuera del cuerpo: el panel va en su propio plano, con diedro suave
    const ala = new THREE.Group();
    ala.position.set(0, 0.0, z * 0.2);
    ala.rotation.x = z * -0.12;
    const marco = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.012, 0.2), negro);
    const celdas = new THREE.Mesh(new THREE.PlaneGeometry(0.46, 0.16), panel);
    celdas.rotation.x = -Math.PI / 2;
    celdas.position.y = 0.007;
    ala.add(marco, celdas);
    // Rotor de sustentación sobre el extremo de cada ala
    const brazo = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.03, 0.02), negro);
    brazo.position.set(0.12, 0.02, 0);
    const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.035, 0.03, 12), negro);
    motor.position.set(0.12, 0.045, 0);
    const rotor = new THREE.Group();
    rotor.position.set(0.12, 0.07, 0);
    const disco = new THREE.Mesh(new THREE.CircleGeometry(0.14, 20),
      new THREE.MeshBasicMaterial({ color: 0x9fd8ff, transparent: true, opacity: 0.18, side: THREE.DoubleSide, depthWrite: false, toneMapped: false }));
    disco.rotation.x = -Math.PI / 2;
    const aspa = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.004, 0.02), negro);
    rotor.add(disco, aspa);
    grupo.userData.rotores.push(rotor);
    ala.add(brazo, motor, rotor);
    grupo.add(ala);
  }

  // Antena integrada en el lomo, con punta luminosa
  const antena = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.012, 0.2, 8), negro);
  antena.position.set(-0.05, 0.19, 0);
  const punta = new THREE.Mesh(new THREE.SphereGeometry(0.02, 10, 8), led);
  punta.position.set(-0.05, 0.3, 0);
  grupo.add(antena, punta);

  // Góndola de instrumentos bajo el vientre, con luz de estado
  const gondola = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.12, 4, 10), negro);
  gondola.rotation.z = Math.PI / 2;
  gondola.position.set(0.02, -0.12, 0);
  const estado = new THREE.Mesh(new THREE.SphereGeometry(0.018, 10, 8), led);
  estado.position.set(0.02, -0.17, 0);
  grupo.add(gondola, estado);

  grupo.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

  // Sombra sobre el suelo: disco translúcido que se encoge y se aclara con la altura
  const sombra = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.0),
    new THREE.MeshBasicMaterial({ map: TEXTURA_SOMBRA, transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false }));
  sombra.rotation.x = -Math.PI / 2;
  grupo.userData.sombra = sombra;
  return grupo;
}

// Vaivén de flotación, giro de rotores y sombra sobre el suelo. Llamar en cada fotograma.
// `suelo` es la altura del terreno bajo la sonda; `altura` la altura sobre el suelo.
export function actualizarSonda(grupo, tiempo, dt, suelo, altura = 1.2) {
  const x = grupo.position.x;
  const z = grupo.position.z;
  const vaiven = Math.sin(tiempo * 1.1) * 0.05;
  grupo.position.set(x, suelo + altura + vaiven, z);
  grupo.rotation.z = Math.sin(tiempo * 0.9) * 0.03;
  for (const r of grupo.userData.rotores) r.rotation.y += dt * 22;
  const sombra = grupo.userData.sombra;
  if (sombra) {
    sombra.position.set(x, suelo + 0.03, z);
    const k = 1 / (1 + altura * 0.35);
    sombra.scale.set(k, k, 1);
    sombra.material.opacity = 0.25 + 0.4 * k;
  }
}

// ---------- temblor de cámara (sismo) ----------
const temblor = { intensidad: 0, duracion: 0, transcurrido: 0 };
export function sacudir(intensidad = 0.12, duracion = 1.2) {
  temblor.intensidad = intensidad;
  temblor.duracion = duracion;
  temblor.transcurrido = 0;
}
// Desplazamiento de la cámara para este fotograma. Se suma antes de renderizar y se resta después.
export function desplazamientoTemblor(dt) {
  if (temblor.duracion <= 0) return new THREE.Vector3();
  temblor.transcurrido += dt;
  const restante = Math.max(0, 1 - temblor.transcurrido / temblor.duracion);
  if (restante === 0) { temblor.duracion = 0; return new THREE.Vector3(); }
  const t = temblor.transcurrido * 40;
  const f = temblor.intensidad * restante;
  return new THREE.Vector3(Math.sin(t * 1.3) * f, Math.sin(t * 1.7) * f * 0.6, Math.cos(t * 1.1) * f);
}

// ---------- estela de meteorito ----------
// Línea luminosa que se desvanece desde `desde` hasta `hasta` (puntos en coordenadas de escena)
export function estelaMeteorito(escena, desde, hasta, duracion = 1.5) {
  const curva = new THREE.LineCurve3(new THREE.Vector3(...desde), new THREE.Vector3(...hasta));
  const geom = new THREE.TubeGeometry(curva, 24, 0.07, 8, false);
  const material = new THREE.MeshBasicMaterial({ color: 0xffd08a, transparent: true, opacity: 1, toneMapped: false });
  const linea = new THREE.Mesh(geom, material);
  escena.add(linea);
  const inicio = performance.now();
  const paso = () => {
    const t = (performance.now() - inicio) / 1000 / duracion;
    if (t >= 1) {
      escena.remove(linea);
      geom.dispose();
      material.dispose();
      return;
    }
    material.opacity = 1 - t;
    requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// ---------- interferencia del HUD (baja conectividad) ----------
const interferencia = document.createElement("div");
interferencia.id = "interferencia";
interferencia.setAttribute("aria-hidden", "true");
interferencia.style.cssText = [
  "position:fixed", "inset:0", "pointer-events:none", "z-index:45", "display:none",
  "background:repeating-linear-gradient(0deg, rgba(255,255,255,0.14) 0 1px, transparent 1px 3px), repeating-linear-gradient(90deg, rgba(120,220,255,0.06) 0 2px, transparent 2px 6px)",
  "mix-blend-mode:screen", "animation:interferencia 0.2s steps(2) infinite",
].join(";");
document.body.appendChild(interferencia);
const estiloInterferencia = document.createElement("style");
estiloInterferencia.textContent = "@keyframes interferencia { from { transform: translateY(0); } to { transform: translateY(3px); } }";
document.head.appendChild(estiloInterferencia);

export function activarInterferencia(activa, intensidad = 1) {
  interferencia.style.display = activa ? "block" : "none";
  interferencia.style.opacity = String(Math.min(1, Math.max(0, intensidad)));
}

// ---------- marcador de señal biológica (anomalía, no confirma vida) ----------
// Un anillo pulsante en el suelo y una etiqueta fija en pantalla, siempre con el texto de cautela
const TEXTO_BIO = "anomalía, no confirma vida";
const marcadorBio = document.createElement("div");
marcadorBio.id = "marcador-bio";
marcadorBio.textContent = TEXTO_BIO;
marcadorBio.style.cssText = [
  "position:fixed", "transform:translate(-50%,-100%)", "display:none", "pointer-events:none", "z-index:44",
  "background:rgba(10,30,20,0.92)", "border:1px solid #6ee7a8", "color:#c8ffe0", "border-radius:999px",
  "padding:4px 10px", "font:600 12px system-ui,sans-serif", "white-space:nowrap",
].join(";");
document.body.appendChild(marcadorBio);

let anillo = null;
export function marcarSenalBiologica(escena, posicion) {
  quitarSenalBiologica(escena);
  anillo = new THREE.Mesh(
    new THREE.RingGeometry(0.4, 0.5, 40),
    new THREE.MeshBasicMaterial({ color: 0x6ee7a8, transparent: true, opacity: 0.7, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }),
  );
  anillo.rotation.x = -Math.PI / 2;
  anillo.position.copy(new THREE.Vector3(...posicion));
  escena.add(anillo);
  anillo.userData.posicion = new THREE.Vector3(...posicion).add(new THREE.Vector3(0, 0.9, 0));
  marcadorBio.style.display = "block";
}

export function quitarSenalBiologica(escena) {
  if (anillo) escena.remove(anillo);
  anillo = null;
  marcadorBio.style.display = "none";
}

// Pulso del anillo y colocación de la etiqueta en pantalla; llamar en cada fotograma
export function actualizarMarcadores(tiempo, camara) {
  if (!anillo) return;
  anillo.scale.setScalar(1 + 0.15 * Math.sin(tiempo * 3));
  anillo.material.opacity = 0.45 + 0.3 * Math.sin(tiempo * 3);
  const p = anillo.userData.posicion.clone().project(camara);
  const x = (p.x * 0.5 + 0.5) * window.innerWidth;
  const y = (-p.y * 0.5 + 0.5) * window.innerHeight;
  marcadorBio.style.left = `${x}px`;
  marcadorBio.style.top = `${y}px`;
}

// ---------- elementos móviles: meteoritos con estela y rocas que se desplazan ----------
// Con datos simulados hasta que Trabajo exponga sus posiciones. Cada elemento se registra con su
// función de actualización; actualizarMovibles() las llama en cada fotograma.
const moviles = new Set();

export function registrarMovible(grupo, actualizar) {
  moviles.add({ grupo, actualizar });
  return grupo;
}

export function quitarMovible(escena, grupo) {
  for (const m of moviles) {
    if (m.grupo === grupo) moviles.delete(m);
  }
  escena.remove(grupo);
}

export function actualizarMovibles(tiempo, dt) {
  for (const m of moviles) m.actualizar(tiempo, dt);
}

// Meteorito: roca facetada con halo incandescente y una estela que se desvanece tras de sí
export function crearMeteorito(escena, desde, hasta, velocidad = 2.5) {
  const grupo = new THREE.Group();
  const roca = new THREE.Mesh(
    new THREE.DodecahedronGeometry(0.22, 0),
    new THREE.MeshStandardMaterial({ color: 0x5a3a2c, roughness: 0.9, flatShading: true, emissive: 0x3a1204 }),
  );
  const halo = new THREE.Mesh(
    new THREE.SphereGeometry(0.32, 14, 10),
    new THREE.MeshBasicMaterial({ color: 0xff8a3c, transparent: true, opacity: 0.35, depthWrite: false, toneMapped: false }),
  );
  grupo.add(roca, halo);
  const huella = [];
  const geomEstela = new THREE.BufferGeometry();
  const material = new THREE.LineBasicMaterial({ color: 0xffb070, transparent: true, opacity: 0.9, toneMapped: false });
  const estela = new THREE.Line(geomEstela, material);
  escena.add(estela);
  const A = new THREE.Vector3(...desde);
  const B = new THREE.Vector3(...hasta);
  const largo = A.distanceTo(B);
  let t = 0;
  grupo.position.copy(A);
  escena.add(grupo);
  registrarMovible(grupo, (tiempo, dt) => {
    t += (dt * velocidad) / largo;
    if (t >= 1) {
      // Al llegar, el meteorito se reinicia desde el origen de su trayectoria (bucle de demostración)
      t = 0;
      huella.length = 0;
    }
    grupo.position.lerpVectors(A, B, t);
    roca.rotation.x += dt * 3;
    roca.rotation.y += dt * 2;
    halo.scale.setScalar(1 + 0.1 * Math.sin(tiempo * 8));
    huella.push(grupo.position.clone());
    if (huella.length > 14) huella.shift();
    if (huella.length > 1) {
      geomEstela.setFromPoints(huella);
    }
    material.opacity = 0.9 * Math.min(1, huella.length / 14);
  });
  return { grupo, estela };
}

// Roca que se desplaza de lado a lado sobre su base (obstáculo móvil)
export function crearRocaMovil(escena, base, amplitud = 0.6, periodo = 6) {
  const roca = new THREE.Mesh(
    new THREE.DodecahedronGeometry(0.3, 0),
    new THREE.MeshStandardMaterial({ color: 0x7a5340, roughness: 0.92, flatShading: true }),
  );
  roca.castShadow = true;
  const origen = new THREE.Vector3(...base);
  roca.position.copy(origen);
  escena.add(roca);
  registrarMovible(roca, (tiempo) => {
    roca.position.x = origen.x + Math.sin((tiempo * 2 * Math.PI) / periodo) * amplitud;
    roca.rotation.y = tiempo * 0.5;
  });
  return roca;
}
