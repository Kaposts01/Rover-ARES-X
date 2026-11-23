// Panel derecho de IA: pestañas Red neuronal / Difuso / Genético / Misión, siempre a la vista durante la partida.
// Solo lee del motor (GET /rna/red, /rna, /difuso, /ag) y solo pide los datos de la pestaña abierta.
// Todo con textContent (sin innerHTML). Si algo falla, el panel lo dice y la partida sigue igual.
import { coma as comaFormato } from "./formato.js?v=r14";
import { dibujarLineas, preparar } from "/static/laboratorio.js?v=r14";
import { adaptarTramoRNA, titularRNA, celdasAMarcar, NOTA_SIN_TRAMO } from "/static/rna_tramo_datos.js?v=r14";
import { reglasActivadas, plural, nombresMotivos, textoBateriaDifuso, ETIQUETA_BATERIA_UNIVERSO } from "/static/textos.js?v=r14";

const coma = (v, d = 2) => comaFormato(v, d, "-");
const pct = (v) => (v == null ? "-" : `${coma(v * 100, 1)} %`);
const CIAN = "#5fe6ff", MAGENTA = "#ff4fd8", COLOR_CLASE = { libre: "#5fe6ff", "obstáculo": "#ffb454", barranco: "#ff5d6c" };
const COLORES_CONJUNTO = ["#ff5d6c", "#ffb454", "#5fd3ff", "#6ee7a8"];
const ETIQUETA_RASGO = {
  proximidad_frontal_m: "proximidad (m)", desnivel_frontal_m: "desnivel (m)", contraste_optico: "contraste",
  vibracion: "vibración", borde_barranco: "borde", gradiente_altura_m: "gradiente (m)",
};
const ETIQUETA_UNIVERSO = { distancia: "distancia (m)", bateria: ETIQUETA_BATERIA_UNIVERSO, inclinacion: "inclinación (°)", temperatura: "temperatura (°C)" };
const PESTANAS = [["rna", "RNA", "Red neuronal"], ["difuso", "Difuso", "Lógica difusa"], ["ag", "Genético", "Algoritmo genético"], ["mision", "Misión", "Partida y simulación"]];
const ARISTAS_POR_CAPA = 70;      // conexiones dibujadas entre dos capas (las de mayor contribución)
const CLAVE_ANCHO = "ares.panel.ancho", CLAVE_PESTANA = "ares.panel.pestana", CLAVE_PLEGADO = "ares.panel.plegado";

function el(tag, clase, texto) { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; }
function leer(clave, defecto) { try { const v = localStorage.getItem(clave); return v == null ? defecto : v; } catch (e) { return defecto; } }
function guardar(clave, valor) { try { localStorage.setItem(clave, String(valor)); } catch (e) { /* sin almacenamiento */ } }
async function obtener(ruta) {
  try { const r = await fetch(ruta); return r.ok ? await r.json() : null; } catch (e) { return null; }
}

// opciones: controles (nodo a llevar a la pestaña Misión), alCambiarAncho(px), alAmpliar(laboratorio), alMaximizar()
// alMarcarCeldas([{celda, riesgo}]) pinta en la escena las celdas que clasificó la RNA; vehiculo() = «rover» | «sonda»
export function crearPanelIA({ controles = null, alCambiarAncho = null, alAmpliar = null, alMaximizar = null, alNarrar = null, alMarcarCeldas = null, vehiculo = null, alEditarReglas = null } = {}) {
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

  // Cabecera común: el paso, la celda y el rumbo de la decisión que se está mostrando (se ve cambiar paso a paso)
  const pasoInfo = el("div", "pia-paso", "Sin pasos todavía: pulsa «Un paso» o «Reproducir».");
  const narracion = el("p", "pia-narracion"); narracion.setAttribute("aria-live", "polite");
  cuerpo.append(pasoInfo, narracion);
  function historial(titulo) {
    const caja = el("div", "pia-historial");
    const t = el("div", "pia-mini-titulo", titulo);
    const lc = el("div", "pia-lienzo-caja pia-lienzo-hist"); const c = el("canvas", "pia-lienzo"); lc.append(c);
    caja.append(t, lc);
    return { caja, c };
  }
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
  const rnaHist = historial("últimos pasos · p(barranco) y confianza");
  const rnaTramo = el("div", "pia-tramo"); rnaTramo.setAttribute("aria-label", "Celdas de la ruta que clasificó la RNA");
  secciones.rna.append(rnaDecision, rnaTramo, el("div", "pia-lienzo-caja pia-lienzo-red", null), rnaProbs, rnaHist.caja, rnaLeyenda, rnaRepetir);
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
  const difHist = historial("últimos pasos · velocidad del difuso");
  // Enlace a la edición de reglas (Laboratorios → Difuso) y aviso de que hay reglas propias en juego
  const difEdicion = el("div", "pia-edicion");
  const difAviso = el("span", "pia-badge-reglas oculto", "Reglas personalizadas activas"); difAviso.id = "dif-aviso-panel";
  const difEditar = el("button", "pia-secundario", "Editar las reglas y ver el efecto"); difEditar.type = "button"; difEditar.title = "Abre Laboratorios → Difuso: reglas, pesos y funciones de pertenencia editables";
  difEditar.addEventListener("click", () => { if (alEditarReglas) alEditarReglas(); });
  difEdicion.append(difEditar, difAviso);
  secciones.difuso.append(difEdicion, difSalida, difHist.caja, difRejilla, difTituloSalida, difCajaSalida, el("div", "pia-subtitulo", "Reglas activadas"), difReglas);

  // Genético
  const agResumen = el("div", "pia-decision", "Esperando el primer paso…");
  const agHist = historial("últimos pasos · celdas que faltan de la ruta en juego");
  const agLienzo = el("canvas", "pia-lienzo"); const agCaja = el("div", "pia-lienzo-caja pia-lienzo-ag"); agCaja.append(agLienzo);
  const agLeyenda = el("div", "pia-leyenda");
  for (const [n, c] of [["mejor", "#6ee7a8"], ["media", "#ffb454"], ["peor", "#ff5d6c"]]) { const s = el("span", "pia-ley", n); s.style.setProperty("--c", c); agLeyenda.append(s); }
  const agDatos = el("dl", "pia-datos");
  const agNota = el("p", "pia-nota", "Es el AG del plan en juego: la curva es su última ejecución real y cambia cuando la misión replanifica (sitio visitado, sismo, meteorito, veto). La línea amarilla de la escena es esa ruta.");
  const agTituloCurva = el("div", "pia-mini-titulo", "fitness por generación · última ejecución");
  secciones.ag.append(agResumen, agHist.caja, agTituloCurva, agCaja, agLeyenda, agDatos, agNota);

  // Misión: los controles de la partida (Partida y simulación) pasan aquí
  if (controles) secciones.mision.append(controles);

  // ---------- estado ----------
  let pestana = leer(CLAVE_PESTANA, "rna"); if (!secciones[pestana]) pestana = "rna";
  let plegado = leer(CLAVE_PLEGADO, "0") === "1";
  let ancho = Number(leer(CLAVE_ANCHO, "")) || Math.round(Math.min(560, Math.max(360, window.innerWidth * 0.24)));
  let red = null, rnaDatos = null, difDatos = null, agDatosUlt = null, iaUlt = null;
  let enVuelo = false, ultimoPaso = null, epoca = 0;   // epoca: sube con cada partida nueva; una respuesta de la anterior se descarta
  const HIST_N = 40;
  const hist = [];   // { paso, pb, conf, vel, faltan, replan }
  let anim = null;   // { t0 } mientras corre el pulso de la red

  function anchoReal() { return raiz.classList.contains("oculto") ? 0 : (plegado ? 46 : ancho); }
  function avisarAncho() { try { if (alCambiarAncho) alCambiarAncho(anchoReal()); } catch (e) { /* sin encuadre */ } }
  function aplicarAncho() {
    ancho = Math.round(Math.min(Math.max(ancho, 300), Math.min(720, window.innerWidth * 0.55)));
    raiz.style.setProperty("--ancho-panel", `${ancho}px`);
    document.documentElement.style.setProperty("--ancho-panel-ia", `${anchoReal()}px`);
    avisarAncho();
  }
  function aplicarPlegado(persistir = true) {
    raiz.classList.toggle("plegado", plegado);
    bPlegar.textContent = plegado ? "«" : "»"; bPlegar.title = plegado ? "Abrir el panel" : "Plegar el panel";
    if (persistir) guardar(CLAVE_PLEGADO, plegado ? "1" : "0");
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

  // ---------- datos: la decisión real del último paso (GET /ia/paso) ----------
  async function cargar(forzar = false) {
    if (enVuelo) return; enVuelo = true;
    const miEpoca = epoca;
    try {
      const d = await obtener("/ia/paso");
      if (miEpoca !== epoca) return;   // llegó de la partida anterior
      if (!d) { pasoInfo.textContent = "Sin datos (no hay partida o el motor no respondió)."; return; }
      // /ia/paso es la decisión del ÚLTIMO PASO DE LA IA: si el jugador movió el vehículo a mano (o aún no hubo paso de la IA),
      // esa decisión es vieja. Entonces la RNA se lee en vivo sobre la celda de enfrente (GET /rna) en cada movimiento.
      const vieja = !d.hay_paso || (d.paso_ia != null && d.paso_ia !== d.paso);
      const vivo = vieja ? await obtener("/rna") : null;
      if (miEpoca !== epoca) return;
      const enVivo = !!vivo;
      iaUlt = enVivo ? { ...d, rna: vivo, celda: null, posicion: null } : d;
      const nuevo = (d.hay_paso || enVivo) && d.paso !== ultimoPaso;
      narracion.textContent = d.hay_paso && !enVivo ? (d.narracion || "") : "";
      if (nuevo && alNarrar && !enVivo) { try { alNarrar(d.narracion || ""); } catch (e) { /* sin subtítulos */ } }
      if (enVivo) {
        pasoInfo.replaceChildren(el("strong", null, `Paso ${d.paso}`),
          document.createTextNode(d.hay_paso ? ` · lectura en vivo de la RNA sobre la celda de enfrente (la última decisión de la IA fue en el paso ${d.paso_ia ?? "—"}; desde entonces conduces tú)`
            : " · lectura en vivo de la RNA sobre la celda de enfrente (todavía no hubo un paso de la IA)"));
      } else if (!d.hay_paso) { pasoInfo.textContent = "Sin pasos todavía: pulsa «Un paso» o «Reproducir»."; }
      else {
        const sup = d.supervisor || {};
        pasoInfo.replaceChildren(el("strong", null, `Paso ${d.paso}`),
          document.createTextNode(` · celda ${d.posicion ? `(${d.posicion.join(", ")})` : "-"} → ${d.rumbo || "-"} · ${sup.accion || "-"}`),
          el("span", "pia-motivos", nombresMotivos(sup.motivos)));
      }
      const rnaFuente = enVivo ? vivo : d.rna;
      if (rnaFuente) {
        if (!red || !red.modelo || !rnaFuente.modelo || red.modelo.perfil !== rnaFuente.modelo.perfil) red = await obtener("/rna/red");
        if (miEpoca !== epoca) return;
        rnaDatos = { ...rnaFuente, accion: enVivo ? rnaFuente.accion : (d.supervisor || {}).accion };
      } else rnaDatos = null;
      difDatos = enVivo ? null : (d.difuso || null);
      agDatosUlt = d.ag || null;
      if (nuevo) {
        ultimoPaso = d.paso;
        const pr = (rnaFuente && (rnaFuente.probabilidades_usadas || rnaFuente.probabilidades)) || {};
        hist.push({ paso: d.paso, pb: pr.barranco ?? null, conf: Object.keys(pr).length ? Math.max(...Object.values(pr)) : null,
          vel: !enVivo && d.difuso ? d.difuso.velocidad_usada ?? d.difuso.salida.velocidad : null,
          faltan: d.ag ? d.ag.celdas_restantes : null, replan: !enVivo && !!(d.ag && d.ag.ultimo_replanteo && d.ag.ultimo_replanteo.paso === d.paso) });
        if (hist.length > HIST_N) hist.shift();
      }
      if (!rnaDatos) rnaDecision.textContent = "La RNA no actuó en este paso (modo sin RNA o sin paso de la IA).";
      if (rnaDatos && enVivo) rnaDecision.setAttribute("data-en-vivo", "1"); else rnaDecision.removeAttribute("data-en-vivo");
      if (!difDatos) difSalida.textContent = "El difuso no actuó en este paso (modo sin difuso o sin paso de la IA).";
      pintarRNA(); pintarDifuso(); pintarAG(); pintarHistoriales();
      if (nuevo || forzar) { pulsar(); if (rnaFuente) marcar(celdasAMarcar(tramoActual())); }
    } finally { enVuelo = false; }
  }

  // Se llama tras cada paso (y al abrir la pestaña). Una sola petición para las tres técnicas.
  function actualizar({ forzar = false } = {}) {
    if (raiz.classList.contains("oculto") || plegado) return;
    cargar(forzar);
  }

  // ---------- historial de los últimos pasos (se ve el cambio aunque una sola decisión se parezca a la anterior) ----------
  function serie(campo) { return hist.map((h, i) => [i, h[campo]]); }
  function pintarHistoriales() {
    if (!hist.length) return;
    const xmax = Math.max(1, hist.length - 1);
    const marcasReplan = hist.map((h, i) => (h.replan ? { x: i, color: "rgba(255, 200, 87, 0.8)" } : null)).filter(Boolean);
    const fmtX = (v) => { const h = hist[Math.round(v)]; return h ? String(h.paso) : ""; };
    if (!secciones.rna.hidden) dibujarLineas(rnaHist.c, { xmin: 0, xmax, ymin: 0, ymax: 1, fmtX, fmtY: (y) => coma(y, 1),
      series: [{ valores: serie("pb"), color: COLOR_CLASE.barranco, ancho: 2 }, { valores: serie("conf"), color: CIAN, ancho: 1.2, dash: [3, 3] }] });
    if (!secciones.difuso.hidden) dibujarLineas(difHist.c, { xmin: 0, xmax, ymin: 0, ymax: 1, fmtX, fmtY: (y) => coma(y, 1),
      series: [{ valores: serie("vel"), color: CIAN, ancho: 2 }] });
    if (!secciones.ag.hidden) {
      const f = hist.map((h) => h.faltan).filter((v) => v != null);
      dibujarLineas(agHist.c, { xmin: 0, xmax, ymin: 0, ymax: Math.max(1, ...f), fmtX, fmtY: (y) => `${Math.round(y)}`,
        series: [{ valores: serie("faltan"), color: "#ffc857", ancho: 2 }], marcas: marcasReplan });
    }
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
    // márgenes según el texto más largo de cada lado (los rótulos no se cortan): si no caben, la letra baja de 11 a 9 px y,
    // como última salvaguarda, el margen puede llegar a la mitad del lienzo
    const ent0 = rnaDatos.entrada || {};
    const textosIzq = capas.nombres.map((n) => `${ETIQUETA_RASGO[n] || n} ${coma(ent0[n], 1)}`);
    const textosDer = capas.clases.map((c, j) => `${c} ${pct(capas.valores[3][j])}`);
    let tam = 11, margenIzq, margenDer;
    for (; tam >= 9; tam--) {
      ctx.font = `${tam}px 'Cascadia Mono', Consolas, monospace`;
      const anchoTexto = (lista) => Math.max(0, ...lista.map((t) => ctx.measureText(t).width));
      margenIzq = anchoTexto(textosIzq) + 20; margenDer = anchoTexto(textosDer) + 24;
      if (margenIzq <= w * 0.4 && margenDer <= w * 0.32) break;
    }
    tam = Math.max(9, tam);
    margenIzq = Math.min(w * 0.5, margenIzq); margenDer = Math.min(w * 0.4, margenDer);
    const mt = 14, mb = 14;
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
    ctx.font = `${tam}px 'Cascadia Mono', Consolas, monospace`; ctx.textBaseline = "middle";
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
  function marcar(lista) { try { if (alMarcarCeldas) alMarcarCeldas(lista); } catch (e) { /* sin marcas en la escena */ } }
  function tramoActual() { return adaptarTramoRNA(iaUlt, vehiculo ? vehiculo() : "rover"); }
  function pintarRNA() {
    if (!rnaDatos) return;
    const probs = rnaDatos.probabilidades || {};
    const clases = Object.keys(probs);
    const mejor = clases.reduce((a, b) => (probs[b] > probs[a] ? b : a), clases[0]);
    const tramo = tramoActual();
    const f0 = tramo && tramo.filas[0];
    // la cabecera siempre dice de qué celda habla (la clasificación de la celda de enfrente), no solo «libre 100 %»
    const envivo = rnaDecision.getAttribute("data-en-vivo") === "1";
    rnaDecision.replaceChildren(el("strong", null, f0 ? titularRNA(f0) : `${mejor} · ${pct(probs[mejor])}`),
      document.createTextNode(envivo ? ` (celda de enfrente ahora) → el supervisor ${rnaDatos.accion ? `haría: ${rnaDatos.accion}` : "no decidió"}` : ` → acción ${rnaDatos.accion || "-"}`));
    rnaDecision.style.setProperty("--c", COLOR_CLASE[mejor] || CIAN);
    barras(rnaProbs, clases.map((c) => [c, probs[c], COLOR_CLASE[c]]));
    pintarTramo(tramo);
    // el resumen de la columna izquierda también dice de qué celda habla
    const rs = document.getElementById("res-rna"), rc = document.getElementById("rna-celda");
    if (f0 && rs) rs.textContent = titularRNA(f0);
    if (f0 && rc) rc.textContent = `(${f0.celda[0]}, ${f0.celda[1]})`;
  }
  function pintarTramo(tramo) {
    if (!tramo) { rnaTramo.replaceChildren(); return; }
    const filas = tramo.filas.map((f) => {
      const fila = el("div", "pia-tramo-fila" + (f.clase !== "libre" ? " riesgo" : ""));
      fila.tabIndex = 0;
      const [, donde] = f.lugar.split(" · ");
      const cab = el("div", "pia-tramo-cab"); cab.append(el("strong", null, `Celda (${f.celda[0]}, ${f.celda[1]})`), el("span", null, donde ? ` · ${donde}` : ""));
      const barra = el("div", "pia-tramo-barra");
      const rotulos = [];
      for (const c of ["libre", "obstáculo", "barranco"]) {
        const seg = el("i"); seg.style.width = `${(f.probabilidades[c] * 100).toFixed(1)}%`; seg.style.background = COLOR_CLASE[c]; barra.append(seg);
        rotulos.push(`${c} ${pct(f.probabilidades[c])}`);
      }
      fila.append(cab, barra, el("div", "pia-tramo-texto", rotulos.join(" · ")));
      const resaltar = () => marcar([{ celda: f.celda, riesgo: f.clase !== "libre", destacada: true }]);
      fila.addEventListener("mouseenter", resaltar); fila.addEventListener("focus", resaltar);
      return fila;
    });
    rnaTramo.replaceChildren(el("div", "pia-mini-titulo", tramo.real ? "ruta por delante · lo que clasificó la RNA, celda por celda" : "celda que clasificó la RNA en este paso"), ...filas,
      ...(tramo.real ? [] : [el("p", "pia-nota", NOTA_SIN_TRAMO)]));
  }

  // ---------- dibujo: difuso ----------
  function pintarDifuso() {
    const d = difDatos; if (!d || secciones.difuso.hidden) return;
    const s = d.salida || {};
    difSalida.replaceChildren(el("strong", null, `velocidad ${coma(s.velocidad, 3)}`),
      document.createTextNode(s.fallback ? " · sin reglas: valor de respaldo" : ` · ${reglasActivadas((d.reglas_activadas || []).length)}`));
    if (d.aborto && d.aborto.activo) difSalida.append(el("div", "pia-alerta", d.aborto.motivo));
    for (const [k, { c, v }] of Object.entries(difLienzos)) {
      const cur = d.curvas && d.curvas[k]; if (!cur) continue;
      const x = d.entradas[k];
      // la batería se rotula con el % real de la capacidad (el del HUD) y, entre paréntesis, lo que recibió el difuso
      v.textContent = k === "bateria" ? ` ${textoBateriaDifuso(d.entradas)}` : ` ${coma(x, k === "distancia" ? 1 : 0)}`;
      const nombres = Object.keys(cur.conjuntos);
      dibujarLineas(c, {
        xmin: d.universos[k].min, xmax: d.universos[k].max, ymin: 0, ymax: 1,
        series: nombres.map((n, i) => ({ valores: cur.x.map((xx, j) => [xx, cur.conjuntos[n][j]]), color: COLORES_CONJUNTO[i % 4], ancho: 1.6 })),
        marcas: [{ x: Math.min(d.universos[k].max, Math.max(d.universos[k].min, x)), color: "rgba(255,255,255,0.75)" }], fmtY: (y) => coma(y, 1), fmtX: (xx) => coma(xx, 0),
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
    const gens = d.generaciones || [];
    const ult = gens[gens.length - 1] || {};
    const rep = d.ultimo_replanteo;
    agResumen.replaceChildren(
      el("strong", null, `faltan ${plural(d.celdas_restantes, "celda", "celdas")} · sitios ${d.visitados}/${d.sitios}`),
      document.createTextNode(gens.length ? ` · mejor fitness ${coma(ult.mejor, 2)}${d.viable === false ? " · orden no viable (respaldo)" : ""}` : " · sin ejecución del AG todavía"));
    // ultimo_replanteo solo anota los replanteos por eventos (sismo, meteorito…); los de rutina (sitio visitado, veto) no
    agTituloCurva.textContent = rep ? `fitness por generación · última ejecución (replanteo por evento en el paso ${rep.paso}: ${rep.motivo})`
      : (d.replanes ? `fitness por generación · última ejecución del AG (${plural(d.replanes, "replanteo", "replanteos")} en la misión)` : "fitness por generación · plan inicial");
    if (gens.length) {
      const ys = gens.flatMap((g) => [g.mejor, g.media, g.peor]).filter((v) => v != null);
      const lo = Math.min(...ys), hi = Math.max(...ys), m = (hi - lo) * 0.08 || 0.1;
      dibujarLineas(agLienzo, {
        xmin: 0, xmax: Math.max(1, gens.length - 1), ymin: lo - m, ymax: hi + m,
        series: [
          { valores: gens.map((g, i) => [i, g.mejor]), color: "#6ee7a8", ancho: 2.5 },
          { valores: gens.map((g, i) => [i, g.media]), color: "#ffb454", ancho: 1.5 },
          { valores: gens.map((g, i) => [i, g.peor]), color: "#ff5d6c", ancho: 1, dash: [4, 3] },
        ], fmtX: (v) => `${Math.round(v)}`, fmtY: (v) => coma(v, 2),
      });
    } else preparar(agLienzo);
    const sig = d.objetivos && d.objetivos.length ? `(${d.objetivos[0].join(", ")})` : "refugio";
    const filas = [
      ["siguiente objetivo", sig], ["orden planificado", (d.objetivos || []).map((o) => `(${o.join(",")})`).join(" → ") || "-"],
      ["replanteos de la misión", d.replanes], ["órdenes evaluados (última ejecución)", d.evaluados ?? "-"],
    ];
    agDatos.replaceChildren(...filas.flatMap(([k, v]) => [el("dt", null, k), el("dd", null, v == null ? "-" : String(v))]));
    for (const f of d.fallbacks || []) agDatos.append(el("dt", null, "aviso"), el("dd", "pia-alerta", String(f)));
  }

  function redibujar() {
    if (pestana === "rna") dibujarRed(null);
    else if (pestana === "difuso") pintarDifuso();
    else if (pestana === "ag") pintarAG();
    pintarHistoriales();
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
  // Partida nueva: se vacía todo lo derivado de la misión anterior (historial de los gráficos, decisión mostrada, narración)
  function reiniciar() {
    epoca += 1; hist.length = 0; ultimoPaso = null; iaUlt = null; rnaDatos = null; difDatos = null; agDatosUlt = null; red = null; anim = null;
    pasoInfo.textContent = "Sin pasos todavía: pulsa «Un paso» o «Reproducir».";
    narracion.textContent = "";
    rnaDecision.textContent = "Esperando el primer paso…"; difSalida.textContent = "Esperando el primer paso…"; agResumen.textContent = "Esperando el primer paso…";
    rnaProbs.replaceChildren(); difReglas.replaceChildren(); agDatos.replaceChildren();
    rnaTramo.replaceChildren(); marcar([]);   // el tramo (y sus marcas en la escena) era de la partida anterior
    for (const c of [rnaLienzo, rnaHist.c, difHist.c, agHist.c, difLienzoSalida, agLienzo, ...Object.values(difLienzos).map((x) => x.c)]) {
      const x = c.getContext && c.getContext("2d"); if (x) { x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, c.width, c.height); }
    }
    for (const { v } of Object.values(difLienzos)) v.textContent = "";
    if (!raiz.classList.contains("oculto") && !plegado) actualizar({ forzar: true });
  }
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
  // Ancho angosto: el panel se pliega solo a su tira lateral sin tocar la preferencia guardada; al volver a un ancho normal se restaura
  function plegarPorAncho(si) { plegado = si ? true : leer(CLAVE_PLEGADO, "0") === "1"; aplicarPlegado(false); if (!plegado) { redibujar(); actualizar({ forzar: true }); } }
  return { actualizar, mostrar, abrir, reiniciar, plegarPorAncho, seccion: (id) => secciones[id] || null, reglasPersonalizadas: (si) => difAviso.classList.toggle("oculto", !si), redibujar, get ancho() { return anchoReal(); }, elemento: raiz };
}
