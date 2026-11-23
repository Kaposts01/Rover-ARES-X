// Cine: director de cámara. Solo mueve la cámara y lee los controles; no escribe en la partida ni en el motor.
// La repetición visual dibuja un marcador con las últimas posiciones del rover guardadas en el cliente.
import {
  TOMAS, MOMENTOS, REPETICION, duracionToma, siguienteToma, destinoToma, mezcla,
  nuevoBuffer, empujarMuestra, recortarRepeticion, poseRepeticion, modoCine,
} from "/static/cine_datos.js?v=r15";

const K_POSICION = 2.2, K_MIRADA = 3.5;   // amortiguación de los cortes suaves

// objetivo(): { pos:{x,y,z}, rot } del rover; sueloEn(x,z): altura del terreno; celdas(): { columnas, filas }
export function crearDirector({ THREE, escena, camara, controles, sueloEn, celdas, objetivo, reducido = false }) {
  let activo = false, toma = 0, tToma = 0, modo = modoCine(reducido);
  let controlesAntes = null;
  const pos = new THREE.Vector3(), mira = new THREE.Vector3();
  const buffer = nuevoBuffer();
  let reloj = 0;
  let rep = null;   // { sel, u, plano, alFin }
  let fantasma = null;
  const recursos = [];

  function crearFantasma() {   // marcador de la repetición: anillo en el suelo y baliza, sin tapar al rover
    const g = new THREE.Group();
    const geoA = new THREE.TorusGeometry(0.9, 0.05, 8, 32), geoB = new THREE.ConeGeometry(0.12, 0.5, 8);
    const mat = new THREE.MeshBasicMaterial({ color: 0xffb347 });
    recursos.push(geoA, geoB, mat);
    const anillo = new THREE.Mesh(geoA, mat); anillo.rotation.x = Math.PI / 2; anillo.position.y = -0.15;
    const baliza = new THREE.Mesh(geoB, mat); baliza.rotation.x = Math.PI; baliza.position.y = 1.3;
    g.add(anillo, baliza);
    escena.add(g);
    return g;
  }

  function posicionarInicial() {
    const o = objetivo();
    const d = destinoToma(modo === "estatico" ? 3 : toma, o.pos, o.rot, 0, sueloEn, celdas());
    pos.set(d.pos.x, d.pos.y, d.pos.z); mira.set(d.mira.x, d.mira.y, d.mira.z);
  }

  function activar(v) {
    if (v === activo) return;
    if (v) {
      controlesAntes = { enabled: controles.enabled, damping: controles.enableDamping };
      controles.enabled = false;
      pos.copy(camara.position); mira.copy(controles.target);   // arranca desde donde está la cámara: sin salto
      toma = 0; tToma = 0; activo = true;
      if (modo === "estatico") posicionarInicial();
    } else {
      cancelarRepeticion();
      activo = false;
      // devuelve el control sin salto: el punto de mira pasa a ser el objetivo de OrbitControls
      controles.target.copy(mira);
      camara.position.copy(pos);
      if (controlesAntes) { controles.enabled = controlesAntes.enabled; controles.enableDamping = controlesAntes.damping; }
      controles.update();
    }
  }

  function empezarRepeticion(tipo, alFin) {
    if (!activo || modo === "estatico" || rep) return false;
    const sel = recortarRepeticion(buffer);
    if (!sel.length) return false;
    const m = MOMENTOS[tipo]; if (!m) return false;
    rep = { sel, u: 0, plano: Math.max(0, TOMAS.findIndex((t) => t.id === m.plano)), alFin };
    fantasma = fantasma || crearFantasma();
    fantasma.visible = true;
    return true;
  }
  function cancelarRepeticion() {
    if (!rep) return;
    const alFin = rep.alFin; rep = null;
    if (fantasma) fantasma.visible = false;
    try { if (alFin) alFin(); } catch (e) { console.warn("cine: fallo al terminar la repetición", e); }
  }

  function actualizar(dt) {
    if (!activo) return;
    reloj += dt;
    let o = objetivo(), n = toma, t = tToma;
    if (rep) {
      rep.u += dt / REPETICION.duracion_s;
      const p = poseRepeticion(rep.sel, rep.u);
      fantasma.position.set(p.x, p.y + 0.3, p.z); fantasma.rotation.y = p.rot;
      o = { pos: { x: p.x, y: p.y, z: p.z }, rot: p.rot }; n = rep.plano; t = rep.u * REPETICION.duracion_s;
      if (rep.u >= 1) { cancelarRepeticion(); o = objetivo(); n = toma; t = tToma; }
    } else {
      empujarMuestra(buffer, reloj, o.pos, o.rot);
      if (modo === "automatico") {
        tToma += dt;
        if (tToma >= duracionToma(toma)) { toma = siguienteToma(toma); tToma = 0; }
        n = toma; t = tToma;
      } else n = 3;
    }
    const d = destinoToma(n, o.pos, o.rot, t, sueloEn, celdas());
    const kp = mezcla(dt, K_POSICION), km = mezcla(dt, K_MIRADA);
    pos.x += (d.pos.x - pos.x) * kp; pos.y += (d.pos.y - pos.y) * kp; pos.z += (d.pos.z - pos.z) * kp;
    mira.x += (d.mira.x - mira.x) * km; mira.y += (d.mira.y - mira.y) * km; mira.z += (d.mira.z - mira.z) * km;
    camara.position.copy(pos);
    camara.lookAt(mira);
  }

  // Corte a la toma n (Un paso en modo cine): la toma empieza de cero; no actúa durante una repetición ni en modo estático
  function cortar(n) {
    if (!activo || rep || modo === "estatico") return false;
    toma = ((Math.trunc(n) % TOMAS.length) + TOMAS.length) % TOMAS.length; tToma = 0;
    return true;
  }

  function dispose() {
    if (activo) activar(false);
    if (fantasma) { escena.remove(fantasma); fantasma = null; }
    recursos.forEach((r) => r.dispose());
    recursos.length = 0;
  }

  return {
    activar, actualizar, cortar, dispose,
    empezarRepeticion, cancelarRepeticion,
    get activo() { return activo; },
    get repitiendo() { return !!rep; },
    get toma() { return toma; },
    set reducido(v) { modo = modoCine(v); if (activo && modo === "estatico") { cancelarRepeticion(); posicionarInicial(); } },
  };
}
