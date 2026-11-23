// Utilidades de interfaz compartidas por Récords, Comparar políticas y el Tutorial (ronda 23). Todo con textContent.
export function el(tag, clase, texto) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto != null) e.textContent = texto;
  return e;
}
export function boton(texto, clase = "", alClic = null) {
  const b = el("button", `vx-boton ${clase}`.trim(), texto);
  b.type = "button";
  if (alClic) b.addEventListener("click", alClic);
  return b;
}
export function campo(rotulo, control, clase = "") {
  const l = el("label", `vx-campo ${clase}`.trim());
  l.append(el("span", "vx-campo-rotulo", rotulo), control);
  return l;
}
export function selector(opciones, valor) {
  const s = el("select", "vx-control");
  for (const [v, t] of opciones) { const o = el("option", "", t); o.value = String(v); s.append(o); }
  if (valor !== undefined && valor !== null) s.value = String(valor);
  return s;
}

// Capa modal a pantalla completa. Esc la cierra; el foco queda dentro; ninguna tecla llega a la partida.
export function crearCapa({ clase = "", kicker = "", titulo = "", etiqueta = "", alCerrar = null } = {}) {
  const raiz = el("div", `vx-capa oculto ${clase}`.trim());
  raiz.setAttribute("role", "dialog"); raiz.setAttribute("aria-modal", "true"); raiz.setAttribute("aria-label", etiqueta || titulo);
  const caja = el("section", "vx-caja");
  const cab = el("header", "vx-cabecera");
  const tit = el("div"); tit.append(el("div", "titulo-seccion", kicker), el("h2", "vx-titulo", titulo));
  const cerrarB = boton("Cerrar (Esc)", "secundario");
  cab.append(tit, cerrarB);
  const cuerpo = el("div", "vx-cuerpo");
  caja.append(cab, cuerpo); raiz.append(caja);
  document.body.append(raiz);
  let visible = false, foco = null;
  const cerrar = () => {
    if (!visible) return;
    visible = false; raiz.classList.add("oculto");
    try { if (foco && foco.isConnected) foco.focus({ preventScroll: true }); } catch (e) { /* el foco ya no existe */ }
    foco = null;
    if (alCerrar) alCerrar();
  };
  const abrir = () => {
    if (visible) return;
    try { foco = document.activeElement; } catch (e) { foco = null; }
    visible = true; raiz.classList.remove("oculto");
    caja.scrollTop = 0;
    cerrarB.focus({ preventScroll: true });
  };
  const alTecla = (ev) => {
    if (!visible) return;
    if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); cerrar(); return; }
    if (ev.key === "Tab") {
      const lista = [...raiz.querySelectorAll("button, input, select, summary, [tabindex]")].filter((x) => !x.disabled && x.offsetParent !== null && x.getAttribute("tabindex") !== "-1");
      if (!lista.length) { ev.preventDefault(); return; }
      const primero = lista[0], ultimo = lista[lista.length - 1], activo = document.activeElement;
      if (!raiz.contains(activo)) { ev.preventDefault(); primero.focus(); }
      else if (ev.shiftKey && activo === primero) { ev.preventDefault(); ultimo.focus(); }
      else if (!ev.shiftKey && activo === ultimo) { ev.preventDefault(); primero.focus(); }
      return;
    }
    // el resto de teclas se queda en la capa (escribir una semilla no mueve el vehículo ni dispara)
    ev.stopPropagation();
  };
  window.addEventListener("keydown", alTecla, true);
  cerrarB.addEventListener("click", cerrar);
  return { raiz, cuerpo, abrir, cerrar, get visible() { return visible; } };
}
