// Cine: interfaz (DOM). Todo con textContent; sin innerHTML.
import { ROTULO_REPETICION } from "/static/cine_datos.js?v=r15";

const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };

// Lecturas del cine (FPS y aviso) dentro del contenedor de opciones; las casillas están en el HTML para poder cargar el cine al marcarlas.
export function crearPanelCine(contenedor) {
  const fps = el("div", "cn-fps"); fps.id = "cine-fps";
  const aviso = el("div", "cn-aviso oculto"); aviso.id = "cine-aviso"; aviso.setAttribute("role", "status");
  contenedor.append(fps, aviso);
  return {
    fps(texto) { fps.textContent = texto || ""; },
    aviso(texto) { aviso.textContent = texto || ""; aviso.classList.toggle("oculto", !texto); },
  };
}

// Cinta flotante: ya no es una cinta fija. Solo muestra, mientras duran, la etiqueta de la repetición y los avisos temporales
// (autoapagado, «H o Esc para salir» 3 s al entrar). En el cine solo quedan bandas, subtítulos, ▶/⏸ y «Salir del cine».
export function crearCintaCine(contenedor) {
  const cinta = el("div", "cn-cinta oculto"); cinta.id = "cine-cinta"; cinta.setAttribute("role", "status");
  const rep = el("span", "cn-cinta-rep oculto", ROTULO_REPETICION);
  const aviso = el("span", "cn-cinta-aviso oculto");
  cinta.append(rep, aviso);
  contenedor.append(cinta);
  let temporizador = null;
  const pintar = () => { cinta.classList.toggle("oculto", rep.classList.contains("oculto") && aviso.classList.contains("oculto")); };
  return {
    director(v) { if (!v) { rep.classList.add("oculto"); aviso.classList.add("oculto"); clearTimeout(temporizador); } pintar(); },
    repeticion(v) { rep.classList.toggle("oculto", !v); pintar(); },
    aviso(t, ms = 9000) {
      aviso.textContent = t || ""; aviso.classList.toggle("oculto", !t); pintar();
      clearTimeout(temporizador);
      if (t) temporizador = setTimeout(() => { aviso.classList.add("oculto"); pintar(); }, ms);
    },
    dispose() { clearTimeout(temporizador); cinta.remove(); },
  };
}
