// Pantalla final: capa DOM (estrellas, puntaje, estadísticas, logros, momentos y botones). Todo con textContent.
import {
  ROTULO_PUNTAJE, NOTA_PUNTAJE, ROTULO_FICCION, NOTA_DISTANCIA, NOTA_BARRANCOS, NOTA_VIOLACIONES, AVISO_TERRENO,
  DURACION_CUENTA_MS, DURACION_CONFETI_MS, TECLAS_QUE_PASAN, MAX_MOMENTOS,
  tituloFinal, puntajeFinal, desglosePuntaje, estrellas, formatoDato, confetiPermitido,
} from "./final_datos.js?v=r14";
import { icono, insignia, estrella } from "./final_iconos.js?v=r14";

const reducidoAhora = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

export function crearFinal({ contenedor, alContinuar = null, alCerrar = null, alRepetir = null, alOtroPlaneta = null } = {}) {
  if (!contenedor) throw new Error("crearFinal necesita un contenedor");
  const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };
  const boton = (clase, texto, ico) => {
    const b = el("button", clase); b.type = "button";
    if (ico) b.append(icono(ico, { tam: 18 }));
    b.append(document.createTextNode(texto));
    return b;
  };

  const raiz = el("div", "fn-capa oculto");
  raiz.setAttribute("role", "dialog");
  raiz.setAttribute("aria-modal", "true");
  raiz.setAttribute("aria-labelledby", "fn-titulo");
  const panel = el("section", "fn-panel");
  const confeti = el("canvas", "fn-confeti"); confeti.setAttribute("aria-hidden", "true");

  const cabecera = el("div", "fn-cabecera");
  const titulos = el("div");
  const titulo = el("h2", "fn-titulo"); titulo.id = "fn-titulo";
  const subtitulo = el("p", "fn-subtitulo");
  titulos.append(el("div", "fn-kicker", "ARES-X · informe de misión"), titulo, subtitulo);
  const omitir = boton("secundario fn-omitir", "Omitir");
  omitir.setAttribute("aria-label", "Omitir la pantalla final (Escape)");
  cabecera.append(titulos, omitir);

  const estrellasEl = el("div", "fn-estrellas"); estrellasEl.setAttribute("role", "img");
  const puntajeCaja = el("div", "fn-puntaje-caja");
  const puntajeEtiqueta = el("div", "fn-puntaje-etiqueta", "Puntaje de juego");
  const puntajeValor = el("span", "fn-puntaje", "0"); puntajeValor.setAttribute("aria-live", "polite");
  const rotuloPuntaje = el("p", "fn-rotulo", ROTULO_PUNTAJE);
  const notaPuntaje = el("p", "fn-nota", NOTA_PUNTAJE);
  const desglose = el("ul", "fn-desglose");
  puntajeCaja.append(puntajeEtiqueta, puntajeValor, rotuloPuntaje, notaPuntaje, desglose);

  const rejilla = el("div", "fn-rejilla");
  const notasEstadisticas = el("div", "fn-notas");

  const seccionNuevos = el("section", "fn-seccion");
  const tituloNuevos = el("h3", "fn-seccion-titulo", "Logros nuevos");
  const nuevosEl = el("div", "fn-logros-nuevos");
  seccionNuevos.append(tituloNuevos, nuevosEl);

  const seccionTodos = el("details", "fn-seccion fn-todos");
  const resumenTodos = el("summary", "fn-seccion-titulo");
  const todosEl = el("div", "fn-logros-todos");
  seccionTodos.append(resumenTodos, todosEl);

  const seccionMomentos = el("section", "fn-seccion");
  const momentosEl = el("div", "fn-momentos");
  seccionMomentos.append(el("h3", "fn-seccion-titulo", "Mejores momentos"), momentosEl);

  const aviso = el("p", "fn-nota fn-aviso-terreno", AVISO_TERRENO);
  const acciones = el("div", "fn-acciones");
  const jugar = boton("fn-btn fn-btn-primario", "Volver a jugar", "reiniciar");
  const explorar = boton("fn-btn", "Explorar otro cuerpo", "planeta");
  const cerrar = boton("secundario fn-btn", "Cerrar");
  acciones.append(jugar, explorar, cerrar);
  const etiquetaCasilla = el("label", "fn-casilla");
  const casilla = document.createElement("input"); casilla.type = "checkbox"; casilla.className = "casilla-final"; casilla.checked = true;
  etiquetaCasilla.append(casilla, document.createTextNode(" Mostrar la pantalla final"));

  panel.append(confeti, cabecera, estrellasEl, puntajeCaja, rejilla, notasEstadisticas, seccionNuevos, seccionTodos, seccionMomentos, aviso, acciones, etiquetaCasilla);
  raiz.append(panel);
  contenedor.append(raiz);

  const visor = el("div", "fn-visor oculto");
  visor.setAttribute("role", "dialog"); visor.setAttribute("aria-label", "Imagen del momento ampliada");
  const visorImg = document.createElement("img"); visorImg.alt = "Momento de la misión, ampliado";
  const visorCerrar = el("button", "fn-visor-cerrar"); visorCerrar.type = "button"; visorCerrar.setAttribute("aria-label", "Cerrar la imagen");
  visorCerrar.append(icono("cerrar", { tam: 22 }));
  visor.append(visorImg, visorCerrar);
  contenedor.append(visor);

  let visible = false, vivo = true, foco = null, temporizadorCuenta = null, temporizadorConfeti = null;

  const llamar = (fn) => { if (typeof fn === "function") fn(); };
  const onTecla = (e) => {
    if (!visible) return;
    if (e.key === "Escape") {
      e.preventDefault(); e.stopPropagation();
      if (!visor.classList.contains("oculto")) cerrarVisor(); else llamar(alContinuar);
      return;
    }
    if (!TECLAS_QUE_PASAN.includes(e.key)) e.stopPropagation();   // mientras está abierta, las teclas de conducción (y el espacio, que dispara) no llegan a la partida; el espacio activa el botón enfocado por su acción por defecto
  };
  window.addEventListener("keydown", onTecla, true);
  const cerrarVisor = () => { visor.classList.add("oculto"); };
  visorCerrar.addEventListener("click", cerrarVisor);
  visor.addEventListener("click", (e) => { if (e.target === visor) cerrarVisor(); });
  omitir.addEventListener("click", () => llamar(alContinuar));
  cerrar.addEventListener("click", () => llamar(alCerrar || alContinuar));
  jugar.addEventListener("click", () => llamar(alRepetir));
  explorar.addEventListener("click", () => llamar(alOtroPlaneta));

  function pararAnimaciones() {
    clearInterval(temporizadorCuenta); clearInterval(temporizadorConfeti);
    temporizadorCuenta = temporizadorConfeti = null;
  }

  function pintarEstadistica(nombreIcono, etiqueta, valor) {
    const c = el("div", "fn-stat");
    const ico = el("span", "fn-stat-icono"); ico.append(icono(nombreIcono, { tam: 18 }));
    c.append(ico, el("span", "fn-stat-etiqueta", etiqueta), el("strong", "fn-stat-valor", valor));
    return c;
  }

  function pintarLogro(l, { gris = false } = {}) {
    const c = el("div", `fn-logro${l.obtenido ? " obtenido" : ""}${gris ? " bloqueado" : ""}`);
    const ico = el("span", "fn-logro-icono"); ico.append(insignia(l.icono, { tam: 36, obtenido: !!l.obtenido }));
    const t = el("div", "fn-logro-texto");
    t.append(el("div", "fn-logro-nombre", l.nombre), el("div", "fn-logro-desc", l.descripcion));
    if (l.nota) t.append(el("div", "fn-logro-nota", l.nota));
    if (l.ficcion) t.append(el("div", "fn-ficcion", ROTULO_FICCION));
    c.append(ico, t);
    return c;
  }

  function pintarEstrellas(n) {
    estrellasEl.replaceChildren();
    for (let i = 0; i < 3; i++) {
      const llena = i < n;
      const s = el("span", `fn-estrella ${llena ? "llena" : "vacia"}`);
      s.style.setProperty("--fn-retardo", `${i * 0.28}s`);
      s.append(estrella({ tam: 54, llena }));
      estrellasEl.append(s);
    }
    estrellasEl.setAttribute("aria-label", `${n} de 3 estrellas`);
  }

  function iniciarConfeti() {
    const ctx = confeti.getContext("2d");
    if (!ctx) return;
    const caja = raiz.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    confeti.width = Math.max(1, Math.floor(caja.width * dpr)); confeti.height = Math.max(1, Math.floor(caja.height * dpr));
    ctx.scale(dpr, dpr);
    const colores = ["#68d9ca", "#ffd166", "#83aaff"];
    const piezas = Array.from({ length: 85 }, (_, i) => ({ x: Math.random() * caja.width, y: -Math.random() * caja.height, v: 1 + Math.random() * 2.2, r: 2 + Math.random() * 3, c: colores[i % 3], a: Math.random() * 6 }));
    const t0 = performance.now();
    temporizadorConfeti = setInterval(() => {
      if (!vivo || !visible || performance.now() - t0 > DURACION_CONFETI_MS) { clearInterval(temporizadorConfeti); temporizadorConfeti = null; ctx.clearRect(0, 0, caja.width, caja.height); return; }
      ctx.clearRect(0, 0, caja.width, caja.height);
      for (const p of piezas) { p.y += p.v; p.x += Math.sin(p.y / 18 + p.a) * 0.7; ctx.fillStyle = p.c; ctx.fillRect(p.x, p.y, p.r, p.r * 1.7); }
    }, 32);
  }

  // resultado: de normalizarResultado. momentos: [{titulo, texto, paso, imagen}]. opciones: { logrosNuevos, logros, activada, alCambiarCasilla }
  function mostrar(resultado, momentos = [], { logrosNuevos = [], logros = [], activada = true, alCambiarCasilla = null } = {}) {
    if (!vivo) return;
    const r = resultado || {};
    try { if (!foco) foco = document.activeElement; } catch (e) { foco = null; }
    const reducido = reducidoAhora();
    pararAnimaciones();
    titulo.textContent = tituloFinal(r.codigo);
    subtitulo.textContent = [r.planeta || "—", r.modo || "—", r.motivo_final || r.codigo || "—"].join(" · ");
    const n = estrellas(r);
    pintarEstrellas(n);
    const total = puntajeFinal(r);
    puntajeValor.textContent = reducido ? total.toLocaleString("es-CL") : "0";
    if (!reducido) {
      const t0 = performance.now();
      temporizadorCuenta = setInterval(() => {
        const u = Math.min(1, (performance.now() - t0) / DURACION_CUENTA_MS);
        puntajeValor.textContent = Math.round(total * (1 - Math.pow(1 - u, 3))).toLocaleString("es-CL");
        if (u >= 1) { clearInterval(temporizadorCuenta); temporizadorCuenta = null; }
      }, 24);
    }
    panel.classList.toggle("sin-animacion", reducido);
    const d = desglosePuntaje(r);
    desglose.replaceChildren(...d.terminos.map((t) => {
      const signo = t.clave === "violaciones" ? "−" : "+";
      const valor = t.dato ? t.valor.toLocaleString("es-CL", { maximumFractionDigits: 2 }) : "—";
      const puntos = t.dato ? Math.abs(Math.round(t.puntos)).toLocaleString("es-CL") : "sin dato, cuenta 0";
      return el("li", t.dato ? "" : "sin-dato", `${signo} ${t.etiqueta}: ${valor} × ${t.peso.toLocaleString("es-CL")} = ${puntos}`);
    }));
    rejilla.replaceChildren(
      pintarEstadistica("planeta", "Cuerpo", r.planeta || "—"),
      pintarEstadistica("brujula", "Modo", r.modo || "—"),
      pintarEstadistica("microscopio", "Ciencia", r.ciencia == null ? "—" : `${formatoDato(r.ciencia * 100)} %`),
      pintarEstadistica("probeta", "Objetivos muestreados", r.objetivos_muestreados == null || r.objetivos_totales == null ? "—" : `${formatoDato(r.objetivos_muestreados)} / ${formatoDato(r.objetivos_totales)}`),
      pintarEstadistica("bateria", "Batería final", r.bateria_pct == null ? "—" : `${formatoDato(r.bateria_pct, { decimales: 1 })} %`),
      pintarEstadistica("escudo", "Violaciones / vetos", r.violaciones == null && r.vetos == null ? "—" : `${formatoDato(r.violaciones)} / ${formatoDato(r.vetos)}`),
      pintarEstadistica("montana", "Barrancos evitados", formatoDato(r.barrancos_evitados)),
      pintarEstadistica("replanificar", "Replanificaciones", formatoDato(r.replanificaciones)),
      pintarEstadistica("ubicacion", "Distancia recorrida", r.distancia == null ? "—" : `${formatoDato(r.distancia)} celdas`),
      pintarEstadistica("reloj", "Paso final", formatoDato(r.paso)),
    );
    notasEstadisticas.replaceChildren(el("p", "fn-nota", `${NOTA_DISTANCIA} ${NOTA_BARRANCOS} ${NOTA_VIOLACIONES}`));

    nuevosEl.replaceChildren(...logrosNuevos.map((l) => pintarLogro({ ...l, obtenido: true })));
    seccionNuevos.hidden = !logrosNuevos.length;
    const hechos = logros.filter((l) => l.obtenido).length;
    resumenTodos.textContent = `Todos los logros (${hechos} de ${logros.length})`;
    todosEl.replaceChildren(...logros.map((l) => pintarLogro(l, { gris: l.estado === "bloqueado" })));
    seccionTodos.hidden = !logros.length;

    const lista = (Array.isArray(momentos) ? momentos : []).slice(0, MAX_MOMENTOS);
    momentosEl.replaceChildren(...lista.map((m) => {
      const b = el("button", "fn-momento"); b.type = "button";
      b.setAttribute("aria-label", `${m.titulo || "Momento"} (ampliar imagen)`);
      if (m.imagen) {
        const img = document.createElement("img"); img.src = m.imagen; img.alt = m.titulo || "Momento de la misión";
        b.append(img);
        b.addEventListener("click", () => { visorImg.src = m.imagen; visor.classList.remove("oculto"); visorCerrar.focus({ preventScroll: true }); });
      }
      const t = el("span", "fn-momento-texto");
      t.append(el("span", "fn-momento-paso", `Paso ${m.paso == null ? "—" : m.paso}`), el("span", "fn-momento-titulo", m.titulo || ""), el("span", "fn-momento-desc", m.texto || ""));
      b.append(t);
      return b;
    }));
    seccionMomentos.hidden = !lista.length;

    casilla.checked = !!activada;
    casilla.onchange = () => { if (alCambiarCasilla) alCambiarCasilla(casilla.checked); };
    visor.classList.add("oculto");
    raiz.classList.remove("oculto");
    visible = true;
    panel.scrollTop = 0; raiz.scrollTop = 0;
    omitir.focus({ preventScroll: true });
    confeti.hidden = !confetiPermitido({ n, reducido });
    if (!confeti.hidden) iniciarConfeti();
  }

  function ocultar() {
    pararAnimaciones();
    visible = false;
    raiz.classList.add("oculto"); visor.classList.add("oculto");
    visorImg.removeAttribute("src");
    try { if (foco && foco.isConnected && typeof foco.focus === "function") foco.focus({ preventScroll: true }); } catch (e) { /* el foco ya no existe */ }
    foco = null;
  }
  function dispose() {
    if (!vivo) return;
    ocultar(); vivo = false;
    window.removeEventListener("keydown", onTecla, true);
    raiz.remove(); visor.remove();
  }
  return { mostrar, ocultar, dispose, get visible() { return visible; } };
}
