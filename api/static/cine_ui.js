// Cine: interfaz (DOM). Todo con textContent; sin innerHTML.
import { ROTULO_REPETICION } from "/static/cine_datos.js?v=r14";

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

// Cinta flotante: mientras el director está activo dice cómo salir y rotula la repetición; también muestra el aviso de autoapagado.
export function crearCintaCine(contenedor, { alDesactivar }) {
  const cinta = el("div", "cn-cinta oculto"); cinta.id = "cine-cinta"; cinta.setAttribute("role", "status");
  const texto = el("span", "cn-cinta-texto", "Director de cámara · H o Esc para salir");
  const rep = el("span", "cn-cinta-rep oculto", ROTULO_REPETICION);
  const aviso = el("span", "cn-cinta-aviso oculto");
  const boton = el("button", "secundario cn-cinta-boton", "Desactivar"); boton.type = "button";
  boton.addEventListener("click", () => alDesactivar());
  cinta.append(texto, rep, aviso, boton);
  contenedor.append(cinta);
  let directorVisible = false, temporizador = null;
  const pintar = () => {
    texto.classList.toggle("oculto", !directorVisible); boton.classList.toggle("oculto", !directorVisible);
    cinta.classList.toggle("oculto", !directorVisible && aviso.classList.contains("oculto"));
  };
  return {
    director(v) { directorVisible = !!v; if (!v) rep.classList.add("oculto"); pintar(); },
    repeticion(v) { rep.classList.toggle("oculto", !v); },
    aviso(t) {
      aviso.textContent = t || ""; aviso.classList.toggle("oculto", !t); pintar();
      clearTimeout(temporizador);
      if (t) temporizador = setTimeout(() => { aviso.classList.add("oculto"); pintar(); }, 9000);
    },
    dispose() { clearTimeout(temporizador); cinta.remove(); },
  };
}
