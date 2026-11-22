// Capa 3D «Evolución del AG»: reproduce, generación por generación, las rutas candidatas que probó el algoritmo genético sobre el mapa.
// Dibuja las mejores de cada generación (la primera resaltada, el resto en tonos tenues), los sitios con su ventana de tiempo y las
// bases de recarga, y avisa de qué candidato está bajo el puntero. Los datos llegan ya adaptados (ag_evolucion_datos.js).
// Memoria: las geometrías de las rutas se liberan al cambiar de generación; los materiales (6 de rutas, 2 de marcas) se crean una vez
// y se liberan en dispose(); las etiquetas de los sitios son lienzos que se redibujan, nunca nuevas texturas por generación.
import * as THREE from "three";
import { celdaValida, textoVentana } from "/static/ag_evolucion_datos.js?v=r14";

const ALTO_SOBRE_SUELO = 0.28;
const COLOR_MEJOR = 0xffcf63, COLOR_RESTO = 0x42d9f2, COLOR_BASE = 0x6ee7a8, COLOR_SITIO = 0xffb454, COLOR_RESALTE = 0xffffff;
const RADIO_PICK_PX = 16;
const SEGUNDOS_BASE = 0.7;     // por generación a velocidad ×1

export function crearEvolucion(escena, { alturaTerreno, camara, elemento, alCambiar, alPuntero } = {}) {
  const raiz = new THREE.Group();
  raiz.name = "evolucion-ag";
  escena.add(raiz);
  const rutas = new THREE.Group(); rutas.name = "evolucion-rutas"; raiz.add(rutas);
  const marcas = new THREE.Group(); marcas.name = "evolucion-marcas"; raiz.add(marcas);

  let datos = null;
  let indice = 0;
  let reproduciendo = false;
  let velocidad = 1;
  let acumulado = 0;
  let vivo = true;
  let resaltado = -1;                      // candidato bajo el puntero (rango) o -1
  let candidatoFijo = 0;                   // el que se resalta cuando el puntero no apunta a ninguno
  let dibujadas = [];                      // { rango, muestras:[Vector3], malla }
  let sitiosEscena = [];                   // { id, sprite, lienzo, textura, anillo }
  const matRutas = [];                     // materiales reutilizados: [0] mejor, resto candidatas
  const comunes = {
    geoAnillo: new THREE.RingGeometry(0.32, 0.44, 40).rotateX(-Math.PI / 2),
    geoBase: new THREE.RingGeometry(0.34, 0.5, 4).rotateX(-Math.PI / 2),
    matSitio: new THREE.MeshBasicMaterial({ color: COLOR_SITIO, transparent: true, opacity: 0.95, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }),
    matBase: new THREE.MeshBasicMaterial({ color: COLOR_BASE, transparent: true, opacity: 0.95, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }),
  };
  for (let k = 0; k < 6; k++) matRutas.push(new THREE.MeshBasicMaterial({ color: k === 0 ? COLOR_MEJOR : COLOR_RESTO, transparent: true, opacity: 0.5, depthWrite: false, toneMapped: false }));

  const punto = (celda) => {
    const x = celda[1] + 0.5, z = celda[0] + 0.5;
    return new THREE.Vector3(x, (alturaTerreno ? alturaTerreno(x, z) : 0) + ALTO_SOBRE_SUELO, z);
  };

  // ---------- marcas fijas: sitios (anillo + etiqueta con la ventana de tiempo) y bases de recarga ----------
  function etiqueta(sitio, orden) {
    const lienzo = document.createElement("canvas");
    lienzo.width = 320; lienzo.height = 84;
    const textura = new THREE.CanvasTexture(lienzo);
    textura.colorSpace = THREE.SRGBColorSpace;
    const mat = new THREE.SpriteMaterial({ map: textura, transparent: true, depthTest: false, toneMapped: false });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(1.9, 0.5, 1);
    sprite.renderOrder = 8;
    return { lienzo, textura, sprite, sitio, orden };
  }
  function pintarEtiqueta(e, orden) {
    const c = e.lienzo.getContext("2d");
    c.clearRect(0, 0, 320, 84);
    c.fillStyle = "rgba(8, 14, 26, 0.82)"; c.strokeStyle = orden ? "rgba(255, 207, 99, 0.95)" : "rgba(255, 180, 84, 0.7)"; c.lineWidth = 3;
    const r = 14; c.beginPath(); c.moveTo(r, 4); c.arcTo(316, 4, 316, 80, r); c.arcTo(316, 80, 4, 80, r); c.arcTo(4, 80, 4, 4, r); c.arcTo(4, 4, 316, 4, r); c.fill(); c.stroke();
    c.fillStyle = "#ffe9b8"; c.font = "bold 30px 'Segoe UI', system-ui, sans-serif"; c.textBaseline = "middle";
    // El motor numera los sitios (1, 2…): «9.2» se leería como un decimal, así que se escribe «9.º · sitio 2»
    const numerico = /^\d+$/.test(String(e.sitio.id));
    const titulo = `${orden ? (numerico ? `${orden}.º · ` : `${orden}.`) : ""}${numerico ? "sitio " : ""}${e.sitio.id}${e.sitio.valor !== null ? ` · valor ${e.sitio.valor}` : ""}`;
    for (let px = 30; px >= 20 && c.measureText(titulo).width > 288; px -= 2) c.font = `bold ${px}px 'Segoe UI', system-ui, sans-serif`;
    c.fillText(titulo, 16, 28);
    if (e.sitio.ventana || (datos && datos.hayVentanas)) {   // sin ninguna ventana en los datos, la segunda línea sobra
      c.fillStyle = e.sitio.ventana ? "#9ff0ff" : "#9fb2c8"; c.font = "26px 'Segoe UI', system-ui, sans-serif";
      c.fillText(textoVentana(e.sitio), 16, 62);
    }
    e.textura.needsUpdate = true;
  }
  function limpiarMarcas() {
    for (const e of sitiosEscena) { marcas.remove(e.sprite); e.sprite.material.dispose(); e.textura.dispose(); }
    for (const o of [...marcas.children]) marcas.remove(o);
    sitiosEscena = [];
  }
  function construirMarcas() {
    limpiarMarcas();
    if (!datos) return;
    for (const s of datos.sitios) {
      const p = punto(s.celda);
      const anillo = new THREE.Mesh(comunes.geoAnillo, comunes.matSitio);
      anillo.position.copy(p); anillo.position.y += 0.02; anillo.renderOrder = 4; marcas.add(anillo);
      const e = etiqueta(s, 0);
      e.sprite.position.set(p.x, p.y + 1.2, p.z);
      marcas.add(e.sprite);
      pintarEtiqueta(e, 0);
      sitiosEscena.push(e);
    }
    for (const b of datos.bases) {
      const p = punto(b);
      const m = new THREE.Mesh(comunes.geoBase, comunes.matBase);
      m.position.copy(p); m.rotation.y = Math.PI / 4; m.renderOrder = 4; marcas.add(m);
    }
  }
  // Numera los sitios en el orden del candidato resaltado (1., 2., 3.…)
  function numerarSitios(candidato) {
    const posicion = new Map();
    if (candidato) candidato.orden.forEach((id, i) => posicion.set(id, i + 1));
    for (const e of sitiosEscena) pintarEtiqueta(e, posicion.get(e.sitio.id) || 0);
  }

  // ---------- rutas de la generación ----------
  function liberarRutas() {
    for (const o of [...rutas.children]) { rutas.remove(o); if (o.geometry) o.geometry.dispose(); }   // los materiales son compartidos: no se liberan aquí
    dibujadas = [];
  }
  function estilo() {
    const n = dibujadas.length;
    const activo = resaltado >= 0 ? resaltado : candidatoFijo;
    for (const d of dibujadas) {
      const m = d.malla.material;
      const esActivo = d.rango === activo;
      m.opacity = esActivo ? 1 : (resaltado >= 0 ? 0.16 : Math.max(0.22, 0.62 - (d.rango / Math.max(1, n - 1)) * 0.4));
      d.malla.renderOrder = esActivo ? 6 : 5;
      d.malla.scale.set(1, 1, 1);
    }
    numerarSitios(datos && datos.generaciones[indice] ? datos.generaciones[indice].candidatos.find((c) => c.rango === activo) : null);
  }
  function dibujar(i) {
    liberarRutas();
    const g = datos && datos.generaciones[i];
    if (!g) return;
    g.candidatos.forEach((c) => {
      const pts = c.puntos.filter(celdaValida).map(punto);
      if (pts.length < 2) return;
      const curva = c.rectas ? new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.1) : new THREE.CatmullRomCurve3(pts, false, "centripetal");
      const radio = c.rango === 0 ? 0.06 : 0.03;
      const geo = new THREE.TubeGeometry(curva, Math.max(24, pts.length * 12), radio, 6, false);
      const malla = new THREE.Mesh(geo, matRutas[Math.min(c.rango, matRutas.length - 1)]);
      malla.name = c.rango === 0 ? "ruta-ganadora" : `candidato-${c.rango + 1}`;
      rutas.add(malla);
      dibujadas.push({ rango: c.rango, muestras: curva.getPoints(Math.max(40, pts.length * 10)), malla });
    });
    estilo();
    if (alCambiar) alCambiar(i, g);
  }

  // ---------- puntero: el candidato cuya línea queda a menos de RADIO_PICK_PX de la posición del ratón ----------
  const v = new THREE.Vector3();
  let ultimoPick = 0;
  function candidatoBajo(ev) {
    if (!elemento || !camara || !dibujadas.length) return -1;
    const r = elemento.getBoundingClientRect();
    const px = ev.clientX - r.left, py = ev.clientY - r.top;
    let mejorRango = -1, mejorD = RADIO_PICK_PX * RADIO_PICK_PX;
    for (const d of dibujadas) {
      let ax = null, ay = null;
      for (const m of d.muestras) {
        v.copy(m).project(camara);
        if (v.z > 1 || v.z < -1) { ax = null; continue; }
        const x = (v.x * 0.5 + 0.5) * r.width, y = (-v.y * 0.5 + 0.5) * r.height;
        if (ax !== null) {   // distancia del puntero al segmento (ax,ay)-(x,y)
          const dx = x - ax, dy = y - ay, l2 = dx * dx + dy * dy || 1e-9;
          const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2));
          const qx = ax + t * dx - px, qy = ay + t * dy - py, d2 = qx * qx + qy * qy;
          if (d2 < mejorD) { mejorD = d2; mejorRango = d.rango; }
        }
        ax = x; ay = y;
      }
    }
    return mejorRango;
  }
  function alMover(ev) {
    if (!vivo || !datos || !dibujadas.length) return;
    const ahora = performance.now();
    if (ahora - ultimoPick < 45) return;
    ultimoPick = ahora;
    const rango = candidatoBajo(ev);
    if (rango !== resaltado) { resaltado = rango; estilo(); }
    const g = datos.generaciones[indice];
    if (alPuntero) alPuntero(rango >= 0 && g ? g.candidatos.find((c) => c.rango === rango) : null, g, ev);
  }
  function alSalir() { if (resaltado !== -1) { resaltado = -1; estilo(); } if (alPuntero) alPuntero(null, null, null); }
  if (elemento) { elemento.addEventListener("pointermove", alMover); elemento.addEventListener("pointerleave", alSalir); }

  return {
    // d = resultado de adaptarEvolucion con estado «ok»; null limpia la capa
    cargar(nuevos) {
      reproduciendo = false; resaltado = -1; candidatoFijo = 0;
      datos = nuevos && nuevos.estado === "ok" ? nuevos : null;
      liberarRutas();
      if (!datos) { limpiarMarcas(); return; }
      indice = Math.max(0, Math.min(datos.generaciones.length - 1, datos.seleccionada));
      construirMarcas();
      dibujar(indice);
    },
    irA(g) {
      if (!datos) return;
      indice = Math.max(0, Math.min(datos.generaciones.length - 1, Math.floor(Number(g)) || 0));
      dibujar(indice);
    },
    reproducir() {
      if (!vivo || !datos) return;
      if (indice >= datos.generaciones.length - 1) { indice = 0; dibujar(0); }   // al final, vuelve a empezar
      reproduciendo = true; acumulado = 0;
    },
    pausar() { reproduciendo = false; },
    alternar() { if (reproduciendo) this.pausar(); else this.reproducir(); return reproduciendo; },
    velocidad(k) { velocidad = Math.max(0.1, Number(k) || 1); },
    fijarCandidato(rango) { candidatoFijo = Math.max(0, Number(rango) || 0); estilo(); },
    animar(dt) {
      if (!vivo || !reproduciendo || !datos) return;
      acumulado += Math.max(0, dt) * velocidad;
      if (acumulado < SEGUNDOS_BASE) return;
      acumulado = 0;
      if (indice >= datos.generaciones.length - 1) { reproduciendo = false; if (alCambiar) alCambiar(indice, datos.generaciones[indice], true); return; }
      indice++;
      dibujar(indice);
      if (indice >= datos.generaciones.length - 1) { reproduciendo = false; if (alCambiar) alCambiar(indice, datos.generaciones[indice], true); }
    },
    get reproduciendo() { return reproduciendo; },
    get indice() { return indice; },
    get numGeneraciones() { return datos ? datos.generaciones.length : 0; },
    // para pruebas y diagnóstico: cuántos objetos hay vivos
    get conteo() { return { rutas: rutas.children.length, marcas: marcas.children.length }; },
    dispose() {
      if (!vivo) return;
      vivo = false; reproduciendo = false;
      if (elemento) { elemento.removeEventListener("pointermove", alMover); elemento.removeEventListener("pointerleave", alSalir); }
      liberarRutas(); limpiarMarcas();
      for (const m of matRutas) m.dispose();
      comunes.geoAnillo.dispose(); comunes.geoBase.dispose(); comunes.matSitio.dispose(); comunes.matBase.dispose();
      escena.remove(raiz);
    },
  };
}
