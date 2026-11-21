// Capa 3D «Evolución del AG»: dibuja, por generación, los mejores órdenes de visita que probó el algoritmo genético.
// Los datos llegan ya adaptados (evolucion_datos.js). Aquí solo se dibuja; sin fábricas globales.
import * as THREE from "three";
import { celdaAEscena, textoGeneracion } from "/static/evolucion_datos.js?v=r14";

const SEGUNDOS_POR_GENERACION = 0.35;
const ALTO_SOBRE_SUELO = 0.25;

export function crearEvolucion(escena, { alturaTerreno, alCambiar } = {}) {
  const raiz = new THREE.Group();
  raiz.name = "evolucion-ag";
  raiz.renderOrder = 3;
  escena.add(raiz);
  let datos = { generaciones: [], seleccionada: 0 };
  let indice = 0;
  let reproduciendo = false;
  let acumulado = 0;
  let vivo = true;

  const punto = (celda) => {
    const p = celdaAEscena(celda);
    return new THREE.Vector3(p.x, (alturaTerreno ? alturaTerreno(p.x, p.z) : 0) + ALTO_SOBRE_SUELO, p.z);
  };

  function liberar() {
    for (const o of [...raiz.children]) {
      raiz.remove(o);
      o.geometry.dispose();
      o.material.dispose();
    }
  }

  function dibujar(i, final) {
    liberar();
    const g = datos.generaciones[i];
    if (!g) return;
    const n = g.candidatos.length;
    g.candidatos.forEach((c, k) => {
      const pts = c.puntos.map(punto);
      if (pts.length < 2) return;
      const curva = new THREE.CatmullRomCurve3(pts, false, "centripetal");
      const geo = new THREE.TubeGeometry(curva, Math.max(18, pts.length * 10), k === 0 ? 0.045 : 0.018, 6, false);
      const opacidad = final ? (k === 0 ? 0.98 : 0.11) : Math.max(0.23, 1 - (k / Math.max(1, n - 1)) * 0.68);
      const mat = new THREE.MeshBasicMaterial({
        color: k === 0 ? 0xffcf63 : 0x42d9f2, transparent: true, opacity: opacidad, depthWrite: false, toneMapped: false,
      });
      const malla = new THREE.Mesh(geo, mat);
      malla.name = k === 0 ? "ruta-ganadora" : `candidato-${k + 1}`;
      malla.renderOrder = 4;
      raiz.add(malla);
    });
    if (alCambiar) alCambiar(i, textoGeneracion(g, i), final);
  }

  return {
    cargar(nuevos) {
      reproduciendo = false;
      datos = nuevos || { generaciones: [], seleccionada: 0 };
      indice = Math.min(datos.seleccionada, Math.max(0, datos.generaciones.length - 1));
      if (datos.generaciones.length) dibujar(indice, true); else liberar();
    },
    irA(g) {
      reproduciendo = false;
      indice = Math.max(0, Math.min(datos.generaciones.length - 1, Math.floor(Number(g)) || 0));
      dibujar(indice, indice === datos.seleccionada);
    },
    reproducir() {
      if (!vivo || !datos.generaciones.length) return;
      indice = 0;
      acumulado = 0;
      reproduciendo = datos.seleccionada > 0;
      dibujar(0, !reproduciendo);
    },
    animar(dt) {
      if (!vivo || !reproduciendo) return;
      acumulado += Math.max(0, dt);
      if (acumulado < SEGUNDOS_POR_GENERACION) return;
      acumulado = 0;
      indice++;
      if (indice >= datos.seleccionada) { indice = datos.seleccionada; reproduciendo = false; }
      dibujar(indice, !reproduciendo);
    },
    get reproduciendo() { return reproduciendo; },
    get numGeneraciones() { return datos.generaciones.length; },
    dispose() {
      if (!vivo) return;
      vivo = false;
      reproduciendo = false;
      liberar();
      escena.remove(raiz);
    },
  };
}
