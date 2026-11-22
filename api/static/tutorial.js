// Tutorial del modo manual: recorrido guiado sobre la interfaz real. Resalta el control y espera la acción del jugador
// (app.js avisa con el evento «ares:accion»). Se ofrece la primera vez, se puede saltar y se reabre con el botón «Tutorial».
import { el, boton } from "./vx_ui.js?v=r14";
import { pasosTutorial, yaVisto, marcarVisto, TEXTO_OFERTA } from "./tutorial_datos.js?v=r14";

const almacen = () => { try { return window.localStorage; } catch (e) { return { getItem() { throw new Error("sin almacenamiento"); }, setItem() { throw new Error("sin almacenamiento"); } }; } };

// vehiculo(): «rover» o «sonda»; preparar(clave): deja visible el panel que el paso necesita (lo resuelve app.js)
export function crearTutorial({ vehiculo = () => "rover", preparar = () => {}, alTerminar = null } = {}) {
  let pasos = [], n = 0, activo = false, hecho = false, temporizador = null;

  const foco = el("div", "tt-foco oculto"); foco.setAttribute("aria-hidden", "true");
  const tarjeta = el("section", "tt-tarjeta oculto"); tarjeta.setAttribute("role", "dialog"); tarjeta.setAttribute("aria-label", "Tutorial del modo manual");
  const kicker = el("div", "tt-kicker"), titulo = el("h3", "tt-titulo"), texto = el("p", "tt-texto"), estado = el("p", "tt-estado");
  estado.setAttribute("role", "status"); estado.setAttribute("aria-live", "polite");
  const puntos = el("div", "tt-puntos");
  const bAtras = boton("Anterior", "secundario", () => ir(n - 1));
  const bSaltarPaso = boton("Saltar este paso", "secundario", () => ir(n + 1));
  const bSig = boton("Siguiente", "primario", () => { if (n >= pasos.length - 1) cerrar(true); else ir(n + 1); });
  const bCerrar = boton("Cerrar tutorial", "enlace", () => cerrar(false));
  const acciones = el("div", "tt-acciones"); acciones.append(bAtras, bSaltarPaso, bSig);
  tarjeta.append(kicker, titulo, texto, estado, puntos, acciones, bCerrar);

  const oferta = el("section", "tt-oferta oculto"); oferta.setAttribute("role", "dialog"); oferta.setAttribute("aria-label", "Ofrecimiento del tutorial");
  const ofertaTitulo = el("h3", "tt-titulo", "¿Quieres un tutorial?");
  const ofertaTexto = el("p", "tt-texto", TEXTO_OFERTA);
  const bEmpezar = boton("Empezar el tutorial", "primario", () => { ocultarOferta(); iniciar(); });
  const bAhoraNo = boton("Ahora no", "secundario", () => ocultarOferta());
  const ofertaPie = el("p", "tt-nota", "Lo puedes abrir cuando quieras con el botón «Tutorial».");
  const ofertaAcc = el("div", "tt-acciones"); ofertaAcc.append(bEmpezar, bAhoraNo);
  oferta.append(ofertaTitulo, ofertaTexto, ofertaAcc, ofertaPie);
  document.body.append(foco, tarjeta, oferta);

  function objetivoDe(paso) {
    for (const sel of paso.objetivo || []) {
      let e = null;
      try { e = document.querySelector(sel); } catch (err) { e = null; }
      if (e && e.getClientRects().length > 0) return e;
    }
    return null;
  }

  function colocar() {
    if (!activo) return;
    const paso = pasos[n], objetivo = objetivoDe(paso);
    const margen = 6, ancho = window.innerWidth, alto = window.innerHeight;
    if (objetivo) {
      const r = objetivo.getBoundingClientRect();
      foco.classList.remove("oculto");
      foco.style.left = `${Math.max(0, r.left - margen)}px`; foco.style.top = `${Math.max(0, r.top - margen)}px`;
      foco.style.width = `${Math.min(ancho, r.width + 2 * margen)}px`; foco.style.height = `${Math.min(alto, r.height + 2 * margen)}px`;
    } else foco.classList.add("oculto");
    const t = tarjeta.getBoundingClientRect();
    let x = (ancho - t.width) / 2, y = alto - t.height - 24;
    if (objetivo) {
      const r = objetivo.getBoundingClientRect();
      const lugares = [   // a la derecha, a la izquierda, debajo, encima; el primero que cabe sin tapar el control resaltado
        [r.right + 16, Math.max(12, Math.min(r.top, alto - t.height - 12))],
        [r.left - t.width - 16, Math.max(12, Math.min(r.top, alto - t.height - 12))],
        [Math.max(12, Math.min(r.left, ancho - t.width - 12)), r.bottom + 16],
        [Math.max(12, Math.min(r.left, ancho - t.width - 12)), r.top - t.height - 16],
      ];
      const sitio = lugares.find(([px, py]) => px >= 8 && py >= 8 && px + t.width <= ancho - 8 && py + t.height <= alto - 8);
      if (sitio) [x, y] = sitio;
    }
    tarjeta.style.left = `${Math.max(8, Math.min(x, ancho - t.width - 8))}px`;
    tarjeta.style.top = `${Math.max(8, Math.min(y, alto - t.height - 8))}px`;
  }

  function pintar() {
    const paso = pasos[n];
    hecho = !paso.accion;
    kicker.textContent = `Tutorial · paso ${n + 1} de ${pasos.length}`;
    titulo.textContent = paso.titulo; texto.textContent = paso.texto;
    puntos.replaceChildren(...pasos.map((_, i) => el("span", `tt-punto${i === n ? " actual" : i < n ? " pasado" : ""}`)));
    bAtras.disabled = n === 0;
    bSig.textContent = n >= pasos.length - 1 ? "Terminar" : "Siguiente";
    actualizarEspera();
  }
  function actualizarEspera() {
    const paso = pasos[n];
    estado.textContent = paso.accion ? (hecho ? `✓ ${paso.hecho}` : paso.pista) : "";
    estado.classList.toggle("hecho", hecho && !!paso.accion);
    bSig.disabled = !hecho;
    bSaltarPaso.classList.toggle("oculto", !paso.accion || hecho || n >= pasos.length - 1);
    requestAnimationFrame(colocar);
  }

  function ir(i) {
    if (!activo) return;
    n = Math.max(0, Math.min(i, pasos.length - 1));
    try { preparar(pasos[n].preparar || null); } catch (e) { console.warn("tutorial: no se pudo preparar el paso", e); }
    pintar();
    // el control resaltado puede estar más abajo dentro de un panel con scroll (p. ej. los eventos en la pestaña Misión)
    setTimeout(() => {
      const o = objetivoDe(pasos[n]);
      if (o) { try { o.scrollIntoView({ block: "center", inline: "nearest" }); } catch (e) { /* sin scroll */ } }
      colocar();
    }, 150);   // los paneles que se abren tardan un instante en tener su tamaño final
  }

  // La acción que espera el paso llega por este evento (app.js lo emite al mover, consultar a los modelos o lanzar un evento)
  window.addEventListener("ares:accion", (ev) => {
    if (!activo || hecho) return;
    const paso = pasos[n];
    if (paso.accion && ev.detail && ev.detail.tipo === paso.accion) { hecho = true; actualizarEspera(); }
  });
  window.addEventListener("keydown", (ev) => {
    if (!activo || ev.key !== "Escape") return;
    ev.preventDefault(); ev.stopPropagation(); cerrar(false);
  }, true);
  window.addEventListener("resize", () => colocar());

  function iniciar() {
    if (activo) return;
    pasos = pasosTutorial(vehiculo()); activo = true;
    tarjeta.classList.remove("oculto");
    document.body.classList.add("tutorial-activo");
    clearInterval(temporizador); temporizador = setInterval(colocar, 400);   // el control resaltado puede moverse (paneles, ventana)
    marcarVisto(almacen());
    ir(0);
  }
  function cerrar(terminado) {
    if (!activo) return;
    activo = false; clearInterval(temporizador); temporizador = null;
    tarjeta.classList.add("oculto"); foco.classList.add("oculto");
    document.body.classList.remove("tutorial-activo");
    marcarVisto(almacen());
    if (alTerminar) alTerminar(terminado);
  }
  function ocultarOferta() { oferta.classList.add("oculto"); marcarVisto(almacen()); }

  return {
    iniciar,
    cerrar: () => cerrar(false),
    get activo() { return activo; },
    // La primera vez que se entra al modo manual: se ofrece, sin obligar. Devuelve true si se ofreció.
    ofrecer() {
      if (activo || yaVisto(almacen())) return false;
      oferta.classList.remove("oculto");
      bEmpezar.focus({ preventScroll: true });
      return true;
    },
    get ofreciendo() { return !oferta.classList.contains("oculto"); },
    cerrarOferta: ocultarOferta,
  };
}
