// Introducción: capa DOM (cabecera, tarjeta del cuerpo, avisos fijos, Omitir y casilla). Todo con textContent (sin innerHTML).
import { TITULO_INTRO, SUBTITULO_INTRO, ROTULO_INTRO, AVISO_TERRENO_INTRO, NOTA_ELEGIR } from "./intro_datos.js?v=r14";

export function crearTarjetaIntro(contenedor) {
  const raiz = document.createElement("div");
  raiz.className = "in-capa oculto";
  raiz.setAttribute("role", "dialog");
  raiz.setAttribute("aria-modal", "true");
  raiz.setAttribute("aria-labelledby", "in-titulo");
  const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };

  const cabecera = el("div", "in-cabecera");
  const titulo = el("h2", "in-titulo", TITULO_INTRO); titulo.id = "in-titulo";
  const subtitulo = el("p", "in-subtitulo", SUBTITULO_INTRO);
  cabecera.append(titulo, subtitulo);

  const omitir = el("button", "secundario in-omitir", "Omitir"); omitir.type = "button";
  omitir.setAttribute("aria-label", "Omitir la introducción (Escape)");

  const tarjeta = el("div", "in-tarjeta"); tarjeta.setAttribute("aria-live", "polite");
  const tTitulo = el("strong", "in-tarjeta-titulo"); const tFilas = el("div", "in-tarjeta-filas");
  tarjeta.append(tTitulo, tFilas);

  const pie = el("div", "in-pie");
  const avisos = el("div", "in-avisos");
  avisos.append(el("p", "in-rotulo", ROTULO_INTRO), el("p", "in-aviso-terreno", AVISO_TERRENO_INTRO), el("p", "in-nota", NOTA_ELEGIR));
  const etiquetaCasilla = el("label", "in-casilla");
  const casilla = document.createElement("input"); casilla.type = "checkbox"; casilla.className = "casilla-intro"; casilla.checked = true;
  etiquetaCasilla.append(casilla, document.createTextNode(" Mostrar la introducción al abrir"));
  pie.append(avisos, etiquetaCasilla);
  raiz.append(cabecera, omitir, tarjeta, pie); contenedor.append(raiz);

  let alOmitir = null, foco = null;
  const onTecla = (e) => {
    if (raiz.classList.contains("oculto")) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); if (alOmitir) alOmitir(); return; }
    if (!["Tab", "Enter", " "].includes(e.key)) e.stopPropagation();   // mientras dura, las teclas de conducción no llegan a la partida
  };
  omitir.addEventListener("click", () => { if (alOmitir) alOmitir(); });
  window.addEventListener("keydown", onTecla, true);

  // opciones: { activada, alOmitir, alCambiarCasilla }
  function mostrar({ activada = true, alOmitir: cb = null, alCambiarCasilla = null } = {}) {
    try { if (!foco) foco = document.activeElement; } catch (e) { foco = null; }
    alOmitir = cb;
    casilla.checked = !!activada;
    casilla.onchange = () => { if (alCambiarCasilla) alCambiarCasilla(casilla.checked); };
    cuerpo(null);
    raiz.classList.remove("oculto");
    omitir.focus({ preventScroll: true });
  }
  // datos: { titulo, filas:[{etiqueta, valor, tipo}] } o null (sin cuerpo señalado)
  function cuerpo(datos) {
    if (!datos) { tarjeta.classList.add("vacia"); tTitulo.textContent = "Sistema solar"; tFilas.replaceChildren(el("p", "in-fila", "Señala un planeta para ver su ficha.")); return; }
    tarjeta.classList.remove("vacia");
    tTitulo.textContent = datos.titulo;
    tFilas.replaceChildren(...datos.filas.map((f) => el("p", `in-fila in-${f.tipo}`, `${f.etiqueta}: ${f.valor}`)));
  }
  function ocultar() {
    raiz.classList.add("oculto"); alOmitir = null;
    try { if (foco && foco.isConnected && typeof foco.focus === "function") foco.focus({ preventScroll: true }); } catch (e) { /* el foco ya no existe */ }
    foco = null;
  }
  function dispose() { ocultar(); window.removeEventListener("keydown", onTecla, true); raiz.remove(); }
  return { mostrar, cuerpo, ocultar, dispose };
}
