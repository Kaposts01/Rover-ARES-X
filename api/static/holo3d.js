// Capa 3D «Holograma de IA»: panel en un canvas junto al rover y la ruta luminosa del AG.
// El contenido llega ya adaptado (holo_datos.js). Sin recursos externos; sin fábricas globales.
import * as THREE from "three";
import { limpiar, porcentaje } from "/static/holo_datos.js?v=r14";

const ANCHO = 1024;
const ALTO = 560;

export function crearHolograma(escena, { alturaTerreno } = {}) {
  const lienzo = document.createElement("canvas");
  lienzo.width = ANCHO;
  lienzo.height = ALTO;
  const ctx = lienzo.getContext("2d");
  const textura = new THREE.CanvasTexture(lienzo);
  textura.colorSpace = THREE.SRGBColorSpace;
  textura.minFilter = THREE.LinearFilter;
  const matPanel = new THREE.MeshBasicMaterial({
    map: textura, transparent: true, opacity: 0.95, depthWrite: false, depthTest: false, toneMapped: false, side: THREE.DoubleSide,
  });
  const geoPanel = new THREE.PlaneGeometry(1.6, 1.6 * ALTO / ANCHO);
  const panel = new THREE.Mesh(geoPanel, matPanel);
  panel.name = "holo-panel";
  panel.renderOrder = 999;
  const grupo = new THREE.Group();
  grupo.name = "holo-ia";
  grupo.add(panel);
  escena.add(grupo);

  const matRuta = new THREE.MeshBasicMaterial({ color: 0xffdc8a, transparent: true, opacity: 0.85, depthWrite: false, toneMapped: false });
  let rutaMalla = null;
  let ultima = "";
  let vivo = true;

  function barra(x, y, ancho, valor, color) {
    ctx.fillStyle = "rgba(121,211,224,0.2)";
    ctx.fillRect(x, y, ancho, 14);
    ctx.fillStyle = color;
    ctx.fillRect(x, y, ancho * Math.max(0, Math.min(1, valor)), 14);
  }

  function pintar(d) {
    ctx.clearRect(0, 0, ANCHO, ALTO);
    ctx.fillStyle = "rgba(5,28,43,0.82)";
    ctx.strokeStyle = "rgba(82,238,255,0.95)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(14, 14, ANCHO - 28, ALTO - 28, 28);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#a5f7ff";
    ctx.font = "bold 34px system-ui, sans-serif";
    ctx.fillText("ROVER · ESTADO COGNITIVO", 44, 70);
    // RNA: las 3 clases reales
    ctx.fillStyle = "#73eaff";
    ctx.font = "bold 28px system-ui, sans-serif";
    ctx.fillText("RED NEURONAL", 44, 118);
    ctx.fillStyle = "#efffff";
    ctx.font = "bold 36px system-ui, sans-serif";
    ctx.fillText(d.hayRna ? `RNA: ${limpiar(d.prediccion)} ${porcentaje(d.confianza)}   acción: ${d.accion || "sin dato"}` : "RNA: sin dato", 44, 160);
    d.clases.forEach((c, i) => {
      const x = 44 + i * 310;
      ctx.font = "24px system-ui, sans-serif";
      ctx.fillStyle = "#a5d9e3";
      ctx.fillText(`${limpiar(c.nombre)}  ${d.hayRna ? porcentaje(c.prob) : "—"}`, x, 205);
      barra(x, 217, 270, d.hayRna ? c.prob : 0, c.nombre === d.prediccion ? "#8fffff" : "#39b7d2");
    });
    // Difuso: un solo medidor
    ctx.fillStyle = "#73eaff";
    ctx.font = "bold 28px system-ui, sans-serif";
    ctx.fillText("LÓGICA DIFUSA", 44, 290);
    ctx.font = "24px system-ui, sans-serif";
    ctx.fillStyle = "#a5d9e3";
    ctx.fillText(`velocidad  ${d.velocidad === null ? "sin dato" : porcentaje(d.velocidad)}${d.fallbackDifuso ? "  (respaldo)" : ""}`, 44, 328);
    barra(44, 340, 600, d.velocidad === null ? 0 : d.velocidad, "#4deaff");
    // AG
    ctx.fillStyle = "#73eaff";
    ctx.font = "bold 28px system-ui, sans-serif";
    ctx.fillText("ALGORITMO GENÉTICO", 44, 410);
    ctx.fillStyle = "#ffe49c";
    ctx.font = "24px system-ui, sans-serif";
    ctx.fillText(`Método: ${d.metodo || "sin dato"}`, 44, 448);
    ctx.fillStyle = "#b9dce3";
    ctx.font = "22px system-ui, sans-serif";
    ctx.fillText(`Ruta del plan: ${d.mejorRuta.length ? d.mejorRuta.length + " celdas" : "sin ruta"}   ·   Estado: ${d.estado || "sin dato"}`, 44, 484);
    if (d.vetos.length) {
      ctx.fillStyle = "rgba(111,9,21,0.94)";
      ctx.fillRect(34, 496, ANCHO - 68, 38);
      ctx.strokeStyle = "#ff5262";
      ctx.lineWidth = 2;
      ctx.strokeRect(34, 496, ANCHO - 68, 38);
      ctx.fillStyle = "#fff1f1";
      ctx.font = "bold 20px system-ui, sans-serif";
      ctx.fillText(`SUPERVISOR: ${d.vetos.join(" · ")}`, 48, 522);
    }
    textura.needsUpdate = true;
  }

  function quitarRuta() {
    if (!rutaMalla) return;
    escena.remove(rutaMalla);
    rutaMalla.geometry.dispose();
    rutaMalla = null;
  }

  return {
    // `d` sale de adaptarHolo; `ancla` = posición del rover en escena; `camara` para orientar el panel
    actualizar(d, ancla, camara) {
      if (!vivo) return;
      const clave = JSON.stringify(d);
      if (clave !== ultima) {
        ultima = clave;
        pintar(d);
        quitarRuta();
        const pts = d.mejorRuta.map(([f, c]) => {
          const x = c + 0.5;
          const z = f + 0.5;
          return new THREE.Vector3(x, (alturaTerreno ? alturaTerreno(x, z) : 0) + 0.12, z);
        });
        if (pts.length >= 2) {
          const curva = new THREE.CatmullRomCurve3(pts, false, "centripetal");
          rutaMalla = new THREE.Mesh(new THREE.TubeGeometry(curva, Math.min(180, Math.max(32, pts.length * 8)), 0.03, 6, false), matRuta);
          rutaMalla.name = "holo-ruta";
          rutaMalla.frustumCulled = false;
          escena.add(rutaMalla);
        }
      }
      this.anclar(ancla, camara);
    },
    // Reposiciona sin redibujar (cada cuadro): a la derecha del rover en pantalla
    anclar(ancla, camara) {
      if (!vivo || !ancla) return;
      let escala = 1;
      if (camara) {
        grupo.quaternion.copy(camara.quaternion);
        escala = Math.max(0.6, Math.min(2.2, camara.position.distanceTo(ancla) / 7));
      }
      grupo.scale.setScalar(escala);
      grupo.position.copy(ancla);
      grupo.position.y += 1.1 * escala;
      if (camara) grupo.position.addScaledVector(new THREE.Vector3(1, 0, 0).applyQuaternion(camara.quaternion), 1.3 * escala);
    },
    dispose() {
      if (!vivo) return;
      vivo = false;
      escena.remove(grupo);
      quitarRuta();
      geoPanel.dispose();
      matPanel.dispose();
      textura.dispose();
      matRuta.dispose();
      lienzo.width = lienzo.height = 0;
    },
  };
}
