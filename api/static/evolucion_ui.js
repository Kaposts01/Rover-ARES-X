// Controles de la capa «Evolución del AG»: se montan dentro de la pestaña «Genético» del panel derecho.
// Interruptor de la capa, ▶/⏸, velocidad, deslizador de generación, curvas de fitness (mejor y media) y de diversidad, y la lectura del
// candidato bajo el puntero. Todo con textContent; los textos viven en textos.js (EVO). Los datos llegan adaptados (ag_evolucion_datos.js).
import { dibujarLineas } from "/static/laboratorio.js?v=r14";
import { EVO } from "/static/textos.js?v=r14";
import { VELOCIDADES_EVO, seriesEvolucion, textoGeneracionEvo, lecturaCandidato } from "/static/ag_evolucion_datos.js?v=r14";

const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };
const coma = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d).replace(".", ","));

// acciones: { alActivar(bool), alRecalcular(), alReproducir(), alPausar(), alIr(i), alVelocidad(k) }
export function crearEvolucionUI(acciones = {}) {
  const raiz = el("section", "evo-ui"); raiz.id = "evo-ui"; raiz.setAttribute("aria-label", EVO.titulo);
  const cab = el("div", "evo-cab");
  const titulo = el("div", "pia-mini-titulo", EVO.titulo);
  const interruptor = el("button", "pia-secundario evo-interruptor", EVO.mostrar); interruptor.type = "button"; interruptor.setAttribute("aria-pressed", "false");
  interruptor.title = EVO.ayudaMostrar;
  cab.append(titulo, interruptor);
  const estado = el("p", "evo-estado", EVO.apagada); estado.setAttribute("aria-live", "polite");

  const cuerpo = el("div", "evo-cuerpo oculto");
  const fila = el("div", "evo-fila");
  const play = el("button", "pia-secundario evo-play", "▶"); play.type = "button"; play.title = EVO.reproducir; play.setAttribute("aria-label", EVO.reproducir);
  const vel = el("select", "evo-velocidad"); vel.setAttribute("aria-label", EVO.velocidad); vel.title = EVO.velocidad;
  for (const [k, t] of VELOCIDADES_EVO) { const o = el("option", null, t); o.value = String(k); vel.append(o); }
  vel.value = "1";
  const deslizador = el("input", "evo-deslizador"); deslizador.type = "range"; deslizador.min = "0"; deslizador.max = "0"; deslizador.step = "1"; deslizador.value = "0";
  deslizador.setAttribute("aria-label", EVO.generacion);
  fila.append(play, vel, deslizador);
  const textoGen = el("div", "evo-gen"); textoGen.setAttribute("aria-live", "off");
  const lFit = el("div", "pia-mini-titulo", EVO.curvaFitness);
  const cFit = el("canvas", "pia-lienzo"); const cajaFit = el("div", "pia-lienzo-caja pia-lienzo-ag"); cajaFit.append(cFit);
  const leyFit = el("div", "pia-leyenda");
  for (const [n, c] of [[EVO.mejor, "#6ee7a8"], [EVO.media, "#ffb454"]]) { const s = el("span", "pia-ley", n); s.style.setProperty("--c", c); leyFit.append(s); }
  const lDiv = el("div", "pia-mini-titulo", EVO.curvaDiversidad);
  const cDiv = el("canvas", "pia-lienzo"); const cajaDiv = el("div", "pia-lienzo-caja pia-lienzo-hist"); cajaDiv.append(cDiv);
  const leyenda = el("div", "evo-leyenda");
  for (const [clase, t] of [["mejor", EVO.leyMejor], ["resto", EVO.leyResto], ["sitio", EVO.leySitio], ["base", EVO.leyBase]]) leyenda.append(el("span", `evo-ley evo-ley-${clase}`, t));
  const lectura = el("div", "evo-lectura"); lectura.setAttribute("aria-live", "polite");
  const nota = el("p", "pia-nota evo-nota");
  const difuso = el("details", "evo-difuso oculto"); difuso.append(el("summary", null, EVO.parametrosDifuso)); const dl = el("dl", "pia-datos"); difuso.append(dl);
  const recalcular = el("button", "pia-secundario", EVO.recalcular); recalcular.type = "button";
  cuerpo.append(fila, textoGen, lFit, cajaFit, leyFit, lDiv, cajaDiv, leyenda, el("div", "pia-mini-titulo", EVO.lecturaTitulo), lectura, difuso, nota, recalcular);
  raiz.append(cab, estado, cuerpo);

  // Tooltip junto al puntero (la lectura también se ve mientras se mira el mapa)
  const tip = el("div", "evo-tip oculto"); tip.setAttribute("role", "status"); document.body.append(tip);

  let evo = null, indice = 0, anclada = null;

  function pintarLectura(l) {
    lectura.replaceChildren();
    if (!l) { lectura.append(el("p", "pia-nota", EVO.lecturaVacia)); return; }
    lectura.append(el("div", "evo-lectura-titulo", l.titulo));
    for (const f of l.lineas) {
      const p = el("div", `evo-lectura-fila${f.tipo ? ` ${f.tipo}` : ""}`);
      p.append(el("span", "evo-lectura-clave", f.clave), el("span", "evo-lectura-valor", f.valor));
      lectura.append(p);
    }
    if (l.rectas) lectura.append(el("p", "pia-nota", EVO.rectas));
  }
  function curvas() {
    if (!evo || cuerpo.classList.contains("oculto")) return;
    const s = seriesEvolucion(evo);
    const ys = [...s.mejor, ...s.media].map((p) => p[1]).filter((y) => y !== null);
    const lo = ys.length ? Math.min(...ys) : 0, hi = ys.length ? Math.max(...ys) : 1, m = (hi - lo) * 0.08 || 0.1;
    const xmax = Math.max(1, evo.generaciones.length - 1);
    dibujarLineas(cFit, { xmin: 0, xmax, ymin: lo - m, ymax: hi + m, fmtX: (x) => `${Math.round(x)}`, fmtY: (y) => coma(y, hi - lo < 2 ? 2 : 1),
      series: [{ valores: s.mejor, color: "#6ee7a8", ancho: 2.5 }, { valores: s.media, color: "#ffb454", ancho: 1.6 }],
      marcas: [{ x: indice, color: "rgba(231, 237, 247, 0.7)" }] });
    dibujarLineas(cDiv, { xmin: 0, xmax, ymin: 0, ymax: 1, fmtX: (x) => `${Math.round(x)}`, fmtY: (y) => coma(y, 1),
      series: [{ valores: s.diversidad, color: "#5fd3ff", ancho: 2 }], marcas: [{ x: indice, color: "rgba(231, 237, 247, 0.7)" }] });
  }
  // Clic o arrastre sobre una curva: salta a esa generación
  function irPorCurva(canvas, ev) {
    if (!evo) return;
    const r = canvas.getBoundingClientRect();
    const ancho = r.width - 50 - 12;   // mismos márgenes que dibujarLineas
    const x = Math.round(((ev.clientX - r.left - 50) / ancho) * Math.max(1, evo.generaciones.length - 1));
    if (acciones.alIr) acciones.alIr(Math.max(0, Math.min(evo.generaciones.length - 1, x)));
  }
  for (const c of [cFit, cDiv]) { c.style.cursor = "pointer"; c.addEventListener("pointerdown", (ev) => irPorCurva(c, ev)); }

  interruptor.addEventListener("click", () => { if (acciones.alActivar) acciones.alActivar(interruptor.getAttribute("aria-pressed") !== "true"); });
  play.addEventListener("click", () => { if (play.dataset.estado === "reproduciendo") { if (acciones.alPausar) acciones.alPausar(); } else if (acciones.alReproducir) acciones.alReproducir(); });
  vel.addEventListener("change", () => { if (acciones.alVelocidad) acciones.alVelocidad(Number(vel.value)); });
  deslizador.addEventListener("input", () => { if (acciones.alIr) acciones.alIr(Number(deslizador.value)); });
  recalcular.addEventListener("click", () => { if (acciones.alRecalcular) acciones.alRecalcular(); });

  pintarLectura(null);
  return {
    elemento: raiz,
    // La capa se enciende o apaga (el interruptor y la casilla de «Capas de la escena» van juntos)
    activa(si) {
      interruptor.setAttribute("aria-pressed", String(!!si)); interruptor.textContent = si ? EVO.ocultar : EVO.mostrar;
      if (!si) { cuerpo.classList.add("oculto"); estado.textContent = EVO.apagada; tip.classList.add("oculto"); evo = null; }
    },
    mensaje(texto) { estado.textContent = texto; },
    // datos adaptados con estado «ok»; para vacío, mensaje() con el motivo y datos(null)
    datos(nuevos) {
      evo = nuevos && nuevos.estado === "ok" ? nuevos : null;
      anclada = null;
      cuerpo.classList.toggle("oculto", !evo);
      if (!evo) return;
      indice = evo.seleccionada;
      deslizador.max = String(evo.generaciones.length - 1); deslizador.value = String(indice);
      nota.textContent = evo.fuente === "laboratorio" ? EVO.fuenteLab : "";
      nota.classList.toggle("oculto", evo.fuente !== "laboratorio");
      const t = evo.tiempoS != null ? ` · ${EVO.calculadoEn} ${coma(evo.tiempoS, 1)} s` : "";
      estado.textContent = `${evo.generaciones.length} ${EVO.generaciones}${evo.planeta ? ` · ${evo.planeta}` : ""}${t}`;
      dl.replaceChildren();
      for (const [k, v] of evo.parametrosDifuso) { dl.append(el("dt", null, k.replace(/_/g, " ")), el("dd", null, typeof v === "number" ? coma(v, 3) : String(v))); }
      difuso.classList.toggle("oculto", !evo.parametrosDifuso.length);
      this.generacion(indice, evo.generaciones[indice]);
    },
    generacion(i, g, fin) {
      if (!evo) return;
      indice = i; deslizador.value = String(i);
      textoGen.textContent = textoGeneracionEvo(g, i, evo.generaciones.length);
      curvas();
      if (!anclada) pintarLectura(lecturaCandidato(g && g.candidatos[0], evo, g));
      void fin;
    },
    reproduciendo(si) { play.textContent = si ? "⏸" : "▶"; play.dataset.estado = si ? "reproduciendo" : ""; play.title = si ? EVO.pausar : EVO.reproducir; play.setAttribute("aria-label", play.title); },
    // Candidato bajo el puntero (null = ninguno): se ve en el panel y en un globo junto al cursor
    puntero(c, g, ev) {
      if (!evo) return;
      const l = c ? lecturaCandidato(c, evo, g) : null;
      anclada = l ? true : null;
      pintarLectura(l || lecturaCandidato(g ? g.candidatos[0] : evo.generaciones[indice].candidatos[0], evo, g || evo.generaciones[indice]));
      tip.replaceChildren();
      if (!l || !ev) { tip.classList.add("oculto"); return; }
      tip.append(el("strong", null, l.titulo));
      for (const f of l.lineas) { const p = el("div", f.tipo || ""); p.append(el("span", "evo-lectura-clave", `${f.clave}: `), document.createTextNode(f.valor)); tip.append(p); }
      tip.classList.remove("oculto");
      const x = Math.min(window.innerWidth - tip.offsetWidth - 8, ev.clientX + 16), y = Math.min(window.innerHeight - tip.offsetHeight - 8, ev.clientY + 16);
      tip.style.left = `${Math.max(4, x)}px`; tip.style.top = `${Math.max(4, y)}px`;
    },
    redibujar: curvas,
    dispose() { tip.remove(); raiz.remove(); },
  };
}
