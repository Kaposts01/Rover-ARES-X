// Marcas de evento en la escena: anillo que late y haz de luz sobre la celda (o el vehículo) afectada. Sin DOM: se prueba aparte.
// Las geometrías son compartidas y se liberan en dispose(); cada marca crea 2 materiales que libera al terminar (no se acumula nada).
const DURACION_S = 7;
const MAX_MARCAS = 12;   // un sismo puede traer varias grietas: más allá de 12 no se dibujan

export function crearMarcasEvento({ THREE, escena, altura }) {
  const geoAnillo = new THREE.RingGeometry(0.36, 0.46, 48);
  geoAnillo.rotateX(-Math.PI / 2);
  const geoHaz = new THREE.CylinderGeometry(0.05, 0.16, 3, 10, 1, true);
  geoHaz.translate(0, 1.5, 0);
  const marcas = [];   // { grupo, anillo, haz, matAnillo, matHaz, t0, dura, pos, rotulo, color }
  let reloj = 0;

  function quitar(m) {
    escena.remove(m.grupo);
    m.matAnillo.dispose(); m.matHaz.dispose();
    marcas.splice(marcas.indexOf(m), 1);
  }

  // celdas: [[fila, columna]]; o puntos: [THREE.Vector3] (marcas sobre el vehículo). Devuelve la cantidad dibujada.
  function marcar({ celdas = [], puntos = [], rotulo = "", color = 0xffb454, dura = DURACION_S, renovar = true } = {}) {
    const lugares = celdas.map(([f, c]) => { const x = c + 0.5, z = f + 0.5; return new THREE.Vector3(x, altura(x, z), z); }).concat(puntos.map((p) => p.clone()));
    let n = 0;
    for (const pos of lugares) {
      if (marcas.length >= MAX_MARCAS) break;
      const previa = marcas.find((m) => m.rotulo === rotulo && m.pos.distanceToSquared(pos) < 0.04);
      if (previa) { if (renovar) { previa.t0 = reloj; previa.dura = dura; n += 1; } continue; }   // el mismo evento dos veces: se renueva (o se ignora), no se duplica
      const matAnillo = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9, depthWrite: false, toneMapped: false, side: THREE.DoubleSide });
      const matHaz = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.3, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
      const anillo = new THREE.Mesh(geoAnillo, matAnillo), haz = new THREE.Mesh(geoHaz, matHaz);
      anillo.position.y = 0.06;
      const grupo = new THREE.Group(); grupo.add(anillo, haz); grupo.position.copy(pos);
      grupo.renderOrder = 5;
      escena.add(grupo);
      marcas.push({ grupo, anillo, haz, matAnillo, matHaz, t0: reloj, dura, pos, rotulo, color });
      n += 1;
    }
    return n;
  }

  // tiempo: segundos de la escena (monótono)
  function actualizar(tiempo) {
    reloj = tiempo;
    for (const m of [...marcas]) {
      const edad = tiempo - m.t0;
      if (edad >= m.dura) { quitar(m); continue; }
      const fase = (edad % 1.2) / 1.2;                       // el anillo se expande una vez cada 1,2 s
      m.anillo.scale.setScalar(1 + fase * 1.8);
      const salida = Math.min(1, (m.dura - edad) / 1);        // el último segundo se desvanece
      m.matAnillo.opacity = 0.9 * (1 - fase) * salida + 0.1 * salida;
      m.matHaz.opacity = (0.26 + 0.1 * Math.sin(edad * 6)) * salida;
    }
  }

  // La marca más reciente: el DOM la usa para el rótulo y la flecha de «fuera de cuadro»
  function principal() {
    let u = null;
    for (const m of marcas) if (!u || m.t0 >= u.t0) u = m;
    return u ? { pos: u.pos.clone().add(new THREE.Vector3(0, 3.1, 0)), base: u.pos.clone(), rotulo: u.rotulo, color: u.color, restante: u.dura - (reloj - u.t0) } : null;
  }

  function limpiar() { for (const m of [...marcas]) quitar(m); }
  function dispose() { limpiar(); geoAnillo.dispose(); geoHaz.dispose(); }
  return { marcar, actualizar, principal, limpiar, dispose, get cantidad() { return marcas.length; } };
}
