// Panel derecho de IA: pestañas Red neuronal / Difuso / Genético / Misión, siempre a la vista durante la partida.
// Solo lee del motor (GET /rna/red, /rna, /difuso, /ag) y solo pide los datos de la pestaña abierta.
// Todo con textContent (sin innerHTML). Si algo falla, el panel lo dice y la partida sigue igual.
import { dibujarLineas, preparar } from "/static/laboratorio.js?v=r14";

const coma = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "-" : Number(v).toFixed(d).replace(".", ","));
const pct = (v) => (v == null ? "-" : `${coma(v * 100, 1)} %`);
const CIAN = "#5fe6ff", MAGENTA = "#ff4fd8", COLOR_CLASE = { libre: "#5fe6ff", "obstáculo": "#ffb454", barranco: "#ff5d6c" };
const COLORES_CONJUNTO = ["#ff5d6c", "#ffb454", "#5fd3ff", "#6ee7a8"];
const ETIQUETA_RASGO = {
  proximidad_frontal_m: "proximidad (m)", desnivel_frontal_m: "desnivel (m)", contraste_optico: "contraste",
  vibracion: "vibración", borde_barranco: "borde", gradiente_altura_m: "gradiente (m)",
};
const ETIQUETA_UNIVERSO = { distancia: "distancia (m)", bateria: "batería (%)", inclinacion: "inclinación (°)", temperatura: "temperatura (°C)" };
const PESTANAS = [["rna", "RNA", "Red neuronal"], ["difuso", "Difuso", "Lógica difusa"], ["ag", "Genético", "Algoritmo genético"], ["mision", "Misión", "Partida y simulación"]];
const AG_CADA_N = 8;              // /ag es lo más costoso: se repide al cambiar el plan o cada N actualizaciones
const ARISTAS_POR_CAPA = 70;      // conexiones dibujadas entre dos capas (las de mayor contribución)
const CLAVE_ANCHO = "ares.panel.ancho", CLAVE_PESTANA = "ares.panel.pestana", CLAVE_PLEGADO = "ares.panel.plegado";

function el(tag, clase, texto) { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; }
function leer(clave, defecto) { try { const v = localStorage.getItem(clave); return v == null ? defecto : v; } catch (e) { return defecto; } }
function guardar(clave, valor) { try { localStorage.setItem(clave, String(valor)); } catch (e) { /* sin almacenamiento */ } }
async function obtener(ruta) {
  try { const r = await fetch(ruta); return r.ok ? await r.json() : null; } catch (e) { return null; }
}

// opciones: controles (nodo a llevar a la pestaña Misión), alCambiarAncho(px), alAmpliar(laboratorio), alMaximizar()
export function crearPanelIA({ controles = null, alCambiarAncho = null, alAmpliar = null, alMaximizar = null } = {}) {
  const raiz = el("aside", "pia oculto"); raiz.id = "panel-ia"; raiz.setAttribute("aria-label", "Panel de IA");
  const asa = el("div", "pia-asa"); asa.title = "Arrastra para cambiar el ancho"; asa.setAttribute("aria-hidden", "true");
  const cabecera = el("div", "pia-cabecera");
  const tabs = el("div", "pia-tabs"); tabs.setAttribute("role", "tablist");
  const acciones = el("div", "pia-acciones");
  const bAmpliar = el("button", "pia-boton", "⤢"); bAmpliar.type = "button"; bAmpliar.title = "Ampliar en el laboratorio";
  const bMax = el("button", "pia-boton", "▣"); bMax.type = "button"; bMax.title = "Solo la escena (H)";
  const bPlegar = el("button", "pia-boton", "»"); bPlegar.type = "button"; bPlegar.title = "Plegar el panel";
  acciones.append(bAmpliar, bMax, bPlegar);
  cabecera.append(tabs, acciones);
  const cuerpo = el("div", "pia-cuerpo");
  raiz.append(asa, cabecera, cuerpo);

  // ---------- secciones ----------
  const secciones = {}, botones = {};
  for (const [id, nombre, largo] of PESTANAS) {
    const b = el("button", "pia-tab", nombre); b.type = "button"; b.setAttribute("role", "tab"); b.dataset.pestana = id; b.title = largo;
    b.addEventListener("click", () => abrir(id));
    tabs.append(b); botones[id] = b;
    const s = el("section", "pia-seccion"); s.setAttribute("role", "tabpanel"); s.dataset.pestana = id;
    cuerpo.append(s); secciones[id] = s;
  }

  // Red neuronal
  const rnaDecision = el("div", "pia-decision", "Esperando el primer paso…");
  const rnaLienzo = el("canvas", "pia-red"); rnaLienzo.setAttribute("aria-label", "Red neuronal: entradas, capas ocultas y salida");
  const rnaLeyenda = el("p", "pia-nota", "Cada círculo es una neurona y su brillo es su activación. Las líneas son las conexiones que más pesan en esta decisión: cian excita, magenta inhibe.");
  const rnaProbs = el("div", "pia-barras");
  const rnaRepetir = el("button", "pia-secundario", "↻ Ver pensar otra vez"); rnaRepetir.type = "button";
  secciones.rna.append(rnaDecision, el("div", "pia-lienzo-caja pia-lienzo-red", null), rnaProbs, rnaLeyenda, rnaRepetir);
  secciones.rna.querySelector(".pia-lienzo-red").append(rnaLienzo);

  // Difuso
  const difSalida = el("div", "pia-decision", "Esperando el primer paso…");
  const difRejilla = el("div", "pia-rejilla");
  const difLienzos = {};
  for (const k of Object.keys(ETIQUETA_UNIVERSO)) {
    const caja = el("div", "pia-mini");
    const t = el("div", "pia-mini-titulo", ETIQUETA_UNIVERSO[k]); const v = el("span", "pia-mini-valor"); t.append(v);
    const c = el("canvas", "pia-lienzo"); const lc = el("div", "pia-lienzo-caja pia-lienzo-mini"); lc.append(c);
    caja.append(t, lc); difRejilla.append(caja); difLienzos[k] = { c, v };
  }
  const difTituloSalida = el("div", "pia-mini-titulo", "salida · velocidad (agregado y centroide)");
  const difLienzoSalida = el("canvas", "pia-lienzo"); const difCajaSalida = el("div", "pia-lienzo-caja"); difCajaSalida.append(difLienzoSalida);
  const difReglas = el("ol", "pia-reglas");
  secciones.difuso.append(difSalida, difRejilla, difTituloSalida, difCajaSalida, el("div", "pia-subtitulo", "Reglas activadas"), difReglas);

  // Genético
  const agResumen = el("div", "pia-decision", "Abre esta pestaña durante la partida para ver el AG.");
  const agLienzo = el("canvas", "pia-lienzo"); const agCaja = el("div", "pia-lienzo-caja pia-lienzo-ag"); agCaja.append(agLienzo);
  const agLeyenda = el("div", "pia-leyenda");
  for (const [n, c] of [["mejor", "#6ee7a8"], ["media", "#ffb454"], ["peor", "#ff5d6c"]]) { const s = el("span", "pia-ley", n); s.style.setProperty("--c", c); agLeyenda.append(s); }
  const agDatos = el("dl", "pia-datos");
  const agNota = el("p", "pia-nota", "El AG ordena los sitios científicos pendientes. La línea amarilla de la escena es la ruta que sigue la IA.");
  secciones.ag.append(agResumen, agCaja, agLeyenda, agDatos, agNota);

  // Misión: los controles de la partida (Partida y simulación) pasan aquí
  if (controles) secciones.mision.append(controles);

  // ---------- estado ----------
  let pestana = leer(CLAVE_PESTANA, "rna"); if (!secciones[pestana]) pestana = "rna";
  let plegado = leer(CLAVE_PLEGADO, "0") === "1";
  let ancho = Number(leer(CLAVE_ANCHO, "")) || Math.round(Math.min(560, Math.max(360, window.innerWidth * 0.24)));
  let red = null, rnaDatos = null, difDatos = null, agDatosUlt = null;
  let enVuelo = { rna: false, difuso: false, ag: false };
  let firmaAg = null, cuentaAg = 0, pendienteAg = true;
  let anim = null;   // { t0 } mientras corre el pulso de la red

  function anchoReal() { return raiz.classList.contains("oculto") ? 0 : (plegado ? 46 : ancho); }
  function avisarAncho() { try { if (alCambiarAncho) alCambiarAncho(anchoReal()); } catch (e) { /* sin encuadre */ } }
  function aplicarAncho() {
    ancho = Math.round(Math.min(Math.max(ancho, 300), Math.min(720, window.innerWidth * 0.55)));
    raiz.style.setProperty("--ancho-panel", `${ancho}px`);
    document.documentElement.style.setProperty("--ancho-panel-ia", `${anchoReal()}px`);
    avisarAncho();
  }
  function aplicarPlegado() {
    raiz.classList.toggle("plegado", plegado);
    bPlegar.textContent = plegado ? "«" : "»"; bPlegar.title = plegado ? "Abrir el panel" : "Plegar el panel";
    guardar(CLAVE_PLEGADO, plegado ? "1" : "0");
    aplicarAncho();
    if (!plegado) redibujar();
  }

  function abrir(id) {
    pestana = id; guardar(CLAVE_PESTANA, id);
    if (plegado) { plegado = false; aplicarPlegado(); }
    for (const [k] of PESTANAS) {
      const activa = k === id;
      botones[k].classList.toggle("activa", activa); botones[k].setAttribute("aria-selected", String(activa));
      secciones[k].hidden = !activa;
    }
    bAmpliar.disabled = id === "mision";
    actualizar({ forzar: true });
  }

  // ---------- datos ----------
  async function cargarRNA() {
    if (enVuelo.rna) return; enVuelo.rna = true;
    try {
      const datos = await obtener("/rna");
      if (!datos) { rnaDecision.textContent = "Sin datos de la RNA (no hay partida o el motor no respondió)."; return; }
      if (!red || !red.modelo || !datos.modelo || red.modelo.perfil !== datos.modelo.perfil) red = await obtener("/rna/red");
      rnaDatos = datos;
      pintarRNA(); pulsar();
    } finally { enVuelo.rna = false; }
  }
  async function cargarDifuso() {
    if (enVuelo.difuso) return; enVuelo.difuso = true;
    try {
      const datos = await obtener("/difuso");
      if (!datos) { difSalida.textContent = "Sin datos del difuso."; return; }
      difDatos = datos; pintarDifuso();
    } finally { enVuelo.difuso = false; }
  }
  async function cargarAG() {
    if (enVuelo.ag) return; enVuelo.ag = true;
    agResumen.textContent = agDatosUlt ? agResumen.textContent : "Calculando el AG…";
    try {
      const datos = await obtener("/ag");
      if (!datos) { agResumen.textContent = "Sin datos del AG."; return; }
      agDatosUlt = datos; pendienteAg = false; pintarAG();
    } finally { enVuelo.ag = false; }
  }

  // firma: cambia cuando cambia el plan (siguiente objetivo, replanteo o refugio). forzar: al abrir la pestaña.
  function actualizar({ firma = undefined, forzar = false } = {}) {
    if (raiz.classList.contains("oculto") || plegado) { if (firma !== undefined && firma !== firmaAg) { firmaAg = firma; pendienteAg = true; } return; }
    if (firma !== undefined) {
      cuentaAg += 1;
      if (firma !== firmaAg || cuentaAg >= AG_CADA_N) { firmaAg = firma; pendienteAg = true; cuentaAg = 0; }
    }
    if (pestana === "rna") cargarRNA();
    else if (pestana === "difuso") cargarDifuso();
    else if (pestana === "ag" && (pendienteAg || forzar && !agDatosUlt)) cargarAG();
  }

  // ---------- dibujo: red neuronal ----------
  function capasRed() {
    if (!rnaDatos) return null;
    const nombres = rnaDatos.modelo ? rnaDatos.modelo.rasgos : Object.keys(rnaDatos.normalizada || {});
    const entrada = nombres.map((n) => Number(rnaDatos.normalizada[n]) || 0);
    const a = rnaDatos.activaciones || {};
    const clases = red && red.clases ? red.clases : Object.keys(rnaDatos.probabilidades || {});
    const salida = clases.map((c) => Number(rnaDatos.probabilidades[c]) || 0);
    return { nombres, clases, valores: [entrada, a.oculta_1 || [], a.oculta_2 || [], salida] };
  }
  function dibujarRed(progreso) {
    const p = preparar(rnaLienzo); if (!p) return;
    const { ctx, w, h } = p;
    const capas = capasRed(); if (!capas) return;
    // márgenes según el texto más largo de cada lado (los rótulos no se cortan)
    ctx.font = "11px 'Cascadia Mono', Consolas, monospace";
    const ent0 = rnaDatos.entrada || {};
    const anchoTexto = (lista) => Math.max(0, ...lista.map((t) => ctx.measureText(t).width));
    const textosIzq = capas.nombres.map((n) => `${ETIQUETA_RASGO[n] || n} ${coma(ent0[n], 1)}`);
    const textosDer = capas.clases.map((c, j) => `${c} ${pct(capas.valores[3][j])}`);
    const margenIzq = Math.min(w * 0.38, anchoTexto(textosIzq) + 20), margenDer = Math.min(w * 0.32, anchoTexto(textosDer) + 24), mt = 14, mb = 14;
    const xs = capas.valores.map((_, i) => margenIzq + (i / (capas.valores.length - 1)) * (w - margenIzq - margenDer));
    const ys = capas.valores.map((v) => v.map((_, j) => mt + (v.length === 1 ? 0.5 : j / (v.length - 1)) * (h - mt - mb)));
    const maxAbs = capas.valores.map((v) => Math.max(1e-6, ...v.map((x) => Math.abs(x))));
    // conexiones: contribución = activación de origen × peso
    for (let k = 0; k < capas.valores.length - 1; k++) {
      const W = red && red.pesos ? red.pesos[k] : null; if (!W) continue;
      const origen = capas.valores[k], lista = [];
      for (let i = 0; i < origen.length; i++) for (let j = 0; j < (W[i] || []).length; j++) lista.push([i, j, origen[i] * W[i][j]]);
      lista.sort((a, b) => Math.abs(b[2]) - Math.abs(a[2]));
      const top = lista.slice(0, ARISTAS_POR_CAPA), m = Math.abs((top[0] || [0, 0, 1])[2]) || 1;
      const brillo = progreso == null ? 1 : Math.min(1, Math.max(0.15, (progreso * 3 - k) * 1.4));
      for (const [i, j, c] of top) {
        const f = Math.abs(c) / m;
        ctx.strokeStyle = c >= 0 ? CIAN : MAGENTA;
        ctx.globalAlpha = (0.08 + 0.6 * f) * brillo; ctx.lineWidth = 0.6 + 1.8 * f;
        ctx.beginPath(); ctx.moveTo(xs[k], ys[k][i]); ctx.lineTo(xs[k + 1], ys[k + 1][j]); ctx.stroke();
      }
      // pulso: chispas que viajan por las 6 conexiones más fuertes de la capa que se está «pensando»
      if (progreso != null) {
        const u = progreso * 3 - k;
        if (u > 0 && u < 1) {
          ctx.globalAlpha = 1;
          for (const [i, j, c] of top.slice(0, 6)) {
            const x = xs[k] + (xs[k + 1] - xs[k]) * u, y = ys[k][i] + (ys[k + 1][j] - ys[k][i]) * u;
            ctx.fillStyle = c >= 0 ? "#dffbff" : "#ffd6f6";
            ctx.beginPath(); ctx.arc(x, y, 2.6, 0, Math.PI * 2); ctx.fill();
          }
        }
      }
    }
    ctx.globalAlpha = 1;
    // neuronas
    const ganadora = capas.valores[3].indexOf(Math.max(...capas.valores[3]));
    capas.valores.forEach((v, k) => {
      const r = v.length > 20 ? 3.2 : v.length > 10 ? 4.2 : 6.5;
      const visible = progreso == null || progreso * 3 >= k - 0.05;
      v.forEach((x, j) => {
        const a = Math.min(1, Math.abs(x) / maxAbs[k]);
        const esGanadora = k === 3 && j === ganadora;
        ctx.fillStyle = `rgba(95, 230, 255, ${visible ? 0.15 + 0.85 * a : 0.12})`;
        if (k === 3) ctx.fillStyle = esGanadora && visible ? COLOR_CLASE[capas.clases[j]] || CIAN : `rgba(150, 170, 190, ${visible ? 0.25 + 0.5 * a : 0.15})`;
        ctx.strokeStyle = "rgba(95, 230, 255, 0.55)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(xs[k], ys[k][j], esGanadora ? r + 2.5 : r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        if (esGanadora && visible) { ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.beginPath(); ctx.arc(xs[k], ys[k][j], r + 6, 0, Math.PI * 2); ctx.stroke(); }
      });
    });
    // rótulos: entradas a la izquierda, clases a la derecha, capas abajo
    ctx.font = "11px 'Cascadia Mono', Consolas, monospace"; ctx.textBaseline = "middle";
    ctx.fillStyle = "#a9c6d8"; ctx.textAlign = "right";
    textosIzq.forEach((t, j) => ctx.fillText(t, xs[0] - 10, ys[0][j]));
    ctx.textAlign = "left";
    capas.clases.forEach((c, j) => {
      ctx.fillStyle = j === ganadora ? "#ffffff" : "#a9c6d8";
      ctx.fillText(textosDer[j], xs[3] + 12, ys[3][j]);
    });
  }
  function pulsar() {
    if (!rnaDatos) return;
    const reducido = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducido || secciones.rna.hidden) { dibujarRed(null); return; }
    const t0 = performance.now(), dura = 1100;
    const id = {}; anim = id;
    const paso = () => {
      if (anim !== id) return;
      const u = Math.min(1, (performance.now() - t0) / dura);
      dibujarRed(u >= 1 ? null : u);
      if (u < 1) requestAnimationFrame(paso); else anim = null;
    };
    requestAnimationFrame(paso);
  }
  function barras(contenedor, filas) {
    contenedor.replaceChildren(...filas.map(([nombre, valor, color, texto]) => {
      const f = el("div", "pia-barra-fila");
      const n = el("span", "pia-barra-nombre", nombre), v = el("span", "pia-barra-valor", texto != null ? texto : pct(valor));
      const b = el("div", "pia-barra"), r = el("div", "pia-barra-relleno");
      r.style.width = `${Math.round(Math.min(1, Math.max(0, valor)) * 100)}%`; if (color) r.style.background = color;
      b.append(r); f.append(n, v, b); return f;
    }));
  }
  function pintarRNA() {
    if (!rnaDatos) return;
    const probs = rnaDatos.probabilidades || {};
    const clases = Object.keys(probs);
    const mejor = clases.reduce((a, b) => (probs[b] > probs[a] ? b : a), clases[0]);
    rnaDecision.replaceChildren(el("strong", null, `${mejor} · ${pct(probs[mejor])}`), document.createTextNode(` → acción ${rnaDatos.accion || "-"}`));
    rnaDecision.style.setProperty("--c", COLOR_CLASE[mejor] || CIAN);
    barras(rnaProbs, clases.map((c) => [c, probs[c], COLOR_CLASE[c]]));
  }

  // ---------- dibujo: difuso ----------
  function pintarDifuso() {
    const d = difDatos; if (!d || secciones.difuso.hidden) return;
    const s = d.salida || {};
    difSalida.replaceChildren(el("strong", null, `velocidad ${coma(s.velocidad, 3)}`),
      document.createTextNode(s.fallback ? " · sin reglas: valor de respaldo" : ` · ${(d.reglas_activadas || []).length} reglas activadas`));
    if (d.aborto && d.aborto.activo) difSalida.append(el("div", "pia-alerta", d.aborto.motivo));
    for (const [k, { c, v }] of Object.entries(difLienzos)) {
      const cur = d.curvas && d.curvas[k]; if (!cur) continue;
      const x = d.entradas[k];
      v.textContent = ` ${coma(x, k === "distancia" ? 1 : 0)}`;
      const nombres = Object.keys(cur.conjuntos);
      dibujarLineas(c, {
        xmin: d.universos[k].min, xmax: d.universos[k].max, ymin: 0, ymax: 1,
        series: nombres.map((n, i) => ({ valores: cur.x.map((xx, j) => [xx, cur.conjuntos[n][j]]), color: COLORES_CONJUNTO[i % 4], ancho: 1.6 })),
        marcas: [{ x, color: "rgba(255,255,255,0.75)" }], fmtY: (y) => coma(y, 1), fmtX: (xx) => coma(xx, 0),
      });
    }
    const nombres = Object.keys(s.conjuntos || {});
    const series = nombres.map((n, i) => ({ valores: s.universo.map((y, j) => [y, s.conjuntos[n][j]]), color: COLORES_CONJUNTO[i % 4], ancho: 1, dash: [4, 3] }));
    if (s.agregado) series.push({ valores: s.universo.map((y, j) => [y, s.agregado[j]]), color: CIAN, ancho: 3 });
    dibujarLineas(difLienzoSalida, { xmin: 0, xmax: 1, ymin: 0, ymax: 1, series, marcas: [{ x: s.velocidad, color: "#ffffff" }], fmtX: (x) => coma(x, 1), fmtY: (y) => coma(y, 1) });
    const act = (d.reglas_activadas || []).slice().sort((a, b) => b.fuerza - a.fuerza).slice(0, 6);
    difReglas.replaceChildren(...(act.length ? act.map((r) => {
      const li = el("li", "pia-regla"); const b = el("div", "pia-barra"); const rr = el("div", "pia-barra-relleno"); rr.style.width = `${Math.round(r.fuerza * 100)}%`;
      b.append(rr); li.append(el("span", "pia-regla-texto", `${/^R/i.test(String(r.id)) ? r.id : `R${r.id}`} · ${r.motivo}`), el("span", "pia-barra-valor", coma(r.fuerza, 2)), b); return li;
    }) : [el("li", "pia-nota", "Ninguna regla activada.")]));
  }

  // ---------- dibujo: genético ----------
  function pintarAG() {
    const d = agDatosUlt; if (!d || secciones.ag.hidden) return;
    if (d.sin_sitios) { agResumen.textContent = `Sin sitios pendientes: ${d.motivo || "la misión ya los visitó"}.`; agDatos.replaceChildren(); preparar(agLienzo); return; }
    const gens = d.generaciones || [];
    const ult = gens[gens.length - 1] || {};
    agResumen.replaceChildren(el("strong", null, `mejor fitness ${coma(ult.mejor, 2)}`), document.createTextNode(` · ${d.generaciones_ejecutadas || gens.length} generaciones${d.viable === false ? " · ruta no viable" : ""}`));
    if (gens.length) {
      const ys = gens.flatMap((g) => [g.mejor, g.media, g.peor]);
      const lo = Math.min(...ys), hi = Math.max(...ys), m = (hi - lo) * 0.08 || 0.1;
      dibujarLineas(agLienzo, {
        xmin: 0, xmax: Math.max(1, gens.length - 1), ymin: lo - m, ymax: hi + m,
        series: [
          { valores: gens.map((g, i) => [i, g.mejor]), color: "#6ee7a8", ancho: 2.5 },
          { valores: gens.map((g, i) => [i, g.media]), color: "#ffb454", ancho: 1.5 },
          { valores: gens.map((g, i) => [i, g.peor]), color: "#ff5d6c", ancho: 1, dash: [4, 3] },
        ], fmtX: (v) => `${Math.round(v)}`, fmtY: (v) => coma(v, 2),
      });
    }
    const pr = d.parametros || {};
    const filas = [
      ["celdas de la ruta", d.mejor_ruta ? d.mejor_ruta.length : "-"], ["población", pr.poblacion], ["cruces", d.cruces], ["mutaciones", d.mutaciones],
      ["órdenes evaluados", d.ordenes_evaluados], ["prob. cruce / mutación", `${coma(pr.prob_cruce, 2)} / ${coma(pr.prob_mutacion, 2)}`],
    ];
    agDatos.replaceChildren(...filas.flatMap(([k, v]) => [el("dt", null, k), el("dd", null, v == null ? "-" : String(v))]));
    if (d.fallback) agDatos.append(el("dt", null, "aviso"), el("dd", "pia-alerta", d.fallback));
  }

  function redibujar() {
    if (pestana === "rna") dibujarRed(null);
    else if (pestana === "difuso") pintarDifuso();
    else if (pestana === "ag") pintarAG();
  }

  // ---------- interacción ----------
  rnaRepetir.addEventListener("click", pulsar);
  bPlegar.addEventListener("click", () => { plegado = !plegado; aplicarPlegado(); if (!plegado) actualizar({ forzar: true }); });
  bMax.addEventListener("click", () => { if (alMaximizar) alMaximizar(); });
  bAmpliar.addEventListener("click", () => { if (alAmpliar) alAmpliar({ rna: "rna", difuso: "difuso", ag: "ag" }[pestana]); });
  let arrastre = null;
  asa.addEventListener("pointerdown", (ev) => { if (plegado) return; arrastre = { x: ev.clientX, ancho }; asa.setPointerCapture(ev.pointerId); raiz.classList.add("redimensionando"); });
  asa.addEventListener("pointermove", (ev) => { if (!arrastre) return; ancho = arrastre.ancho + (arrastre.x - ev.clientX); aplicarAncho(); });
  const soltar = () => { if (!arrastre) return; arrastre = null; raiz.classList.remove("redimensionando"); guardar(CLAVE_ANCHO, ancho); redibujar(); };
  asa.addEventListener("pointerup", soltar); asa.addEventListener("pointercancel", soltar);
  let reajuste = null;
  window.addEventListener("resize", () => { clearTimeout(reajuste); reajuste = setTimeout(() => { aplicarAncho(); redibujar(); }, 120); });
  // Visibilidad: el panel solo existe en la partida (la app lo muestra u oculta)
  function mostrar(si) {
    const antes = !raiz.classList.contains("oculto");
    raiz.classList.toggle("oculto", !si);
    aplicarAncho();
    if (si && !antes) { redibujar(); actualizar({ forzar: true }); }
  }

  document.body.append(raiz);
  aplicarPlegado();
  abrir(pestana);
  return { actualizar, mostrar, abrir, get ancho() { return anchoReal(); }, elemento: raiz };
}
