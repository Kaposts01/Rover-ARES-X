// Viaje entre planetas: tarjeta DOM. Todo con textContent (sin innerHTML).
import { DURACION_VIAJE_S } from "/static/viaje_datos.js?v=r14";

export function crearTarjetaViaje(contenedor) {
  const raiz = document.createElement("div");
  raiz.className = "vj-capa oculto";
  raiz.setAttribute("role", "dialog");
  raiz.setAttribute("aria-modal", "true");
  raiz.setAttribute("aria-labelledby", "vj-titulo");
  const tarjeta = document.createElement("div"); tarjeta.className = "vj-tarjeta";
  const titulo = document.createElement("h2"); titulo.id = "vj-titulo"; titulo.className = "vj-titulo";
  const cuerpo = document.createElement("div"); cuerpo.className = "vj-cuerpo";
  const avisos = document.createElement("div"); avisos.className = "vj-avisos";
  const barra = document.createElement("div"); barra.className = "vj-barra";
  barra.setAttribute("role", "progressbar"); barra.setAttribute("aria-valuemin", "0"); barra.setAttribute("aria-valuemax", "100");
  barra.setAttribute("aria-label", "Progreso de la animación (ilustrativo, no es un tiempo de viaje)");
  const relleno = document.createElement("div"); relleno.className = "vj-relleno"; barra.append(relleno);
  const estado = document.createElement("div"); estado.className = "vj-estado";
  const etapa = document.createElement("span"); etapa.className = "vj-etapa";
  const porcentaje = document.createElement("span"); porcentaje.className = "vj-porcentaje";
  estado.append(etapa, porcentaje);
  const omitir = document.createElement("button"); omitir.type = "button"; omitir.className = "secundario vj-omitir"; omitir.textContent = "Omitir viaje";
  tarjeta.append(titulo, estado, barra, cuerpo, avisos, omitir); raiz.append(tarjeta); contenedor.append(raiz);

  let alOmitir = null, intervalo = null, foco = null;
  const onTecla = (e) => {
    if (raiz.classList.contains("oculto")) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); if (alOmitir) alOmitir(); return; }
    if (!["Tab", "Enter"].includes(e.key)) e.stopPropagation();   // mientras dura, las teclas de conducción (y el espacio, que dispara) no llegan a la partida; el espacio activa el botón enfocado por su acción por defecto
  };
  omitir.addEventListener("click", () => { if (alOmitir) alOmitir(); });
  window.addEventListener("keydown", onTecla, true);

  function columna(nombre, filas) {
    const c = document.createElement("div"); c.className = "vj-col";
    const h = document.createElement("strong"); h.textContent = nombre; c.append(h);
    for (const f of filas) {
      const p = document.createElement("p"); p.className = `vj-fila vj-${f.tipo}`;
      p.textContent = `${f.etiqueta}: ${f.valor}`; c.append(p);
    }
    return c;
  }

  // opciones: { duracion, estatica, manual, alOmitir }. En modo estático (movimiento reducido) la barra no se anima y el botón dice «Continuar».
  // Con manual, la barra no avanza sola: la app la mueve con progreso() según la carga real.
  function mostrar(datos, { duracion = DURACION_VIAJE_S, estatica = false, manual = false, alOmitir: cb = null } = {}) {
    barra.setAttribute("aria-label", manual ? "Progreso de la carga de la misión" : "Progreso de la animación (ilustrativo, no es un tiempo de viaje)");
    try { if (!foco) foco = document.activeElement; } catch (e) { foco = null; }   // para devolver el foco al cerrar
    alOmitir = cb;
    titulo.textContent = datos.titulo;
    cuerpo.replaceChildren(columna(datos.desde, datos.origen), columna(datos.hacia, datos.destino));
    avisos.replaceChildren(...datos.avisos.map((a) => { const p = document.createElement("p"); p.textContent = a; return p; }));
    omitir.textContent = estatica ? "Continuar" : "Omitir viaje";
    barra.hidden = estatica;
    relleno.style.width = "0%";
    raiz.classList.remove("oculto");
    clearInterval(intervalo);
    etapa.textContent = ""; porcentaje.textContent = "";
    estado.hidden = !manual;
    if (!estatica && !manual) {
      const ini = performance.now();
      intervalo = setInterval(() => {
        const pct = Math.min(100, ((performance.now() - ini) / (duracion * 1000)) * 100);
        relleno.style.width = `${pct}%`; barra.setAttribute("aria-valuenow", String(Math.round(pct)));
      }, 100);
    }
    omitir.focus({ preventScroll: true });
  }
  // avance 0..1 de la carga real y texto de la etapa del vuelo
  function progreso(avance, texto) {
    const pct = Math.round(Math.min(1, Math.max(0, avance)) * 100);
    relleno.style.width = `${pct}%`; barra.setAttribute("aria-valuenow", String(pct));
    porcentaje.textContent = `${pct} %`;
    if (texto != null && etapa.textContent !== texto) etapa.textContent = texto;
  }
  function ocultar() {
    clearInterval(intervalo); intervalo = null; raiz.classList.add("oculto"); alOmitir = null;
    try { if (foco && foco.isConnected && typeof foco.focus === "function") foco.focus({ preventScroll: true }); } catch (e) { /* el foco ya no existe */ }
    foco = null;
  }
  function dispose() { ocultar(); window.removeEventListener("keydown", onTecla, true); raiz.remove(); }
  return { mostrar, progreso, ocultar, dispose };
}
