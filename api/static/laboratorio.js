import * as adaptador from "/static/adaptador.js?v=r14";
// Laboratorios de los modelos: genético (CA-04), difuso (CA-05) y RNA (CA-06).
// Datos de los endpoints de docs/CONTRATOS_GRAFICOS.md. Este módulo solo dibuja; el motor está en Python.

const $ = (id) => document.getElementById(id);
const coma = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "-" : Number(v).toFixed(d).replace(".", ","));
const porcentaje = (v) => (v == null ? "-" : `${coma(v * 100, 1)} %`);

// Creación de nodos sin innerHTML: el texto siempre entra con textContent
function nodo(tag, clase, texto) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto !== undefined) e.textContent = texto;
  return e;
}

// Tiempo sin bloquear la interfaz mientras se consulta un endpoint lento
function conRetardo(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

// Lienzo con la resolución de la pantalla; null si el panel está oculto (sin tamaño)
function preparar(canvas) {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (!w || !h) return null;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

// Gráfica de líneas con ejes, marcas verticales y cursor. Guarda su geometría para el cursor.
function dibujarLineas(canvas, cfg) {
  const p = preparar(canvas);
  if (!p) return;
  const { ctx, w, h } = p;
  const m = { l: 50, r: 12, t: 10, b: 24 };
  const xr = cfg.xmax - cfg.xmin || 1;
  const yr = cfg.ymax - cfg.ymin || 1;
  const X = (x) => m.l + ((x - cfg.xmin) / xr) * (w - m.l - m.r);
  const Y = (y) => h - m.b - ((y - cfg.ymin) / yr) * (h - m.t - m.b);
  cfg.geo = { m, w, h, xmin: cfg.xmin, xmax: cfg.xmax };
  ctx.font = "12px 'Segoe UI', system-ui, sans-serif";
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(150, 200, 255, 0.12)";
  ctx.fillStyle = "#98a4bb";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = cfg.ymin + (yr * i) / 4;
    const y = Math.round(Y(v)) + 0.5;
    ctx.beginPath(); ctx.moveTo(m.l, y); ctx.lineTo(w - m.r, y); ctx.stroke();
    ctx.fillText(cfg.fmtY ? cfg.fmtY(v) : coma(v, 1), m.l - 6, y);
  }
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= 4; i++) {
    const v = cfg.xmin + (xr * i) / 4;
    ctx.fillText(cfg.fmtX ? cfg.fmtX(v) : coma(v, 0), X(v), h - m.b + 6);
  }
  for (const mk of cfg.marcas || []) {
    ctx.strokeStyle = mk.color;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(X(mk.x), m.t); ctx.lineTo(X(mk.x), h - m.b); ctx.stroke();
    ctx.setLineDash([]);
  }
  for (const s of cfg.series) {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = s.ancho || 2;
    ctx.lineJoin = "round";
    ctx.setLineDash(s.dash || []);
    ctx.beginPath();
    let abierto = false;
    for (const [x, y] of s.valores) {
      if (y == null) { abierto = false; continue; }
      if (abierto) ctx.lineTo(X(x), Y(y)); else ctx.moveTo(X(x), Y(y));
      abierto = true;
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }
  if (cfg.cursor != null) {
    ctx.strokeStyle = "rgba(231, 237, 247, 0.45)";
    ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(X(cfg.cursor), m.t); ctx.lineTo(X(cfg.cursor), h - m.b); ctx.stroke();
    ctx.setLineDash([]);
  }
}

// Cursor interactivo: el valor más cercano en cfg.xs y su etiqueta en el texto superior
const curvas = new Map();   // id del lienzo -> { cfg, tip }
function activarCursor(id) {
  const canvas = $(id);
  if (canvas.dataset.cursor) return;
  canvas.dataset.cursor = "1";
  canvas.addEventListener("mousemove", (ev) => {
    const e = curvas.get(id);
    if (!e || !e.cfg.xs || !e.cfg.xs.length || !e.cfg.geo) return;
    const r = canvas.getBoundingClientRect();
    const g = e.cfg.geo;
    const xv = g.xmin + ((ev.clientX - r.left - g.m.l) / (g.w - g.m.l - g.m.r)) * (g.xmax - g.xmin);
    let mejor = e.cfg.xs[0];
    for (const x of e.cfg.xs) if (Math.abs(x - xv) < Math.abs(mejor - xv)) mejor = x;
    e.cfg.cursor = mejor;
    dibujarLineas(canvas, e.cfg);
    if (e.tip && e.cfg.etiqueta) e.tip.textContent = e.cfg.etiqueta(mejor);
  });
  canvas.addEventListener("mouseleave", () => {
    const e = curvas.get(id);
    if (!e) return;
    e.cfg.cursor = null;
    dibujarLineas(canvas, e.cfg);
    if (e.tip) e.tip.textContent = e.cfg.etiquetaVacia || "";
  });
}
function curva(id, tipId, cfg) {
  curvas.set(id, { cfg, tip: tipId ? $(tipId) : null });
  activarCursor(id);
  dibujarLineas($(id), cfg);
}

// Índice del punto de una curva más cercano a x
function indiceMasCercano(xs, x) {
  let mejor = 0;
  for (let i = 1; i < xs.length; i++) if (Math.abs(xs[i] - x) < Math.abs(xs[mejor] - x)) mejor = i;
  return mejor;
}

const COLORES_CONJUNTO = ["#ff5d6c", "#ffb454", "#5fd3ff", "#6ee7a8"];

// ---------- Genético (CA-04) ----------
const PESOS_AG = ["ciencia", "distancia", "energia", "riesgo", "tiempo"];
const COMPONENTES_AG = ["ciencia", "distancia", "energia", "riesgo", "tiempo", "penalizacion", "inviabilidad"];
let agDatos = null;
let agCandidato = 0;

// Pesos del fitness ajustables (ARX-47c, M10/M16). Valores por defecto = PESOS_POR_DEFECTO de genetico.py.
// Rango [0, 5] según el plan; el servidor los recibe como ?w_<peso>= (ARX-47a) y rechaza lo fuera de rango.
const PESOS_AG_DEFECTO = { ciencia: 1.0, distancia: 0.3, energia: 0.2, riesgo: 0.8, tiempo: 0.1 };
const PESO_AG_MAX = 5;
let pesosAgTocados = false;   // sin tocar los deslizadores no se envía ningún peso (consulta idéntica a la de siempre)
const NOTA_PESOS_AG = "estos pesos afectan al laboratorio; en el juego el orden de visita lo fija la ruta más corta validada";

function iniciarPesosAG() {
  const cont = $("ag-pesos");
  if (!cont) return;
  for (const k of PESOS_AG) {
    const fila = nodo("label", "", `${k} `);
    const r = nodo("input");
    r.type = "range"; r.id = `ag-peso-${k}`; r.min = "0"; r.max = String(PESO_AG_MAX); r.step = "0.05";
    r.value = String(PESOS_AG_DEFECTO[k]);
    const v = nodo("span", "", coma(PESOS_AG_DEFECTO[k], 2));
    v.id = `ag-peso-${k}-v`;
    r.addEventListener("input", () => { v.textContent = coma(Number(r.value), 2); pesosAgTocados = true; });
    fila.appendChild(r);
    fila.appendChild(v);
    cont.appendChild(fila);
  }
  const aplicar = nodo("button", "boton", "Aplicar pesos");
  aplicar.type = "button"; aplicar.id = "ag-pesos-aplicar";
  aplicar.addEventListener("click", ejecutarAG);
  const defecto = nodo("button", "boton", "Por defecto");
  defecto.type = "button"; defecto.id = "ag-pesos-defecto";
  defecto.addEventListener("click", () => {
    for (const k of PESOS_AG) {
      $(`ag-peso-${k}`).value = String(PESOS_AG_DEFECTO[k]);
      $(`ag-peso-${k}-v`).textContent = coma(PESOS_AG_DEFECTO[k], 2);
    }
    pesosAgTocados = true;   // se envían los valores por defecto explícitos para sobrescribir los de la sesión
    ejecutarAG();
  });
  cont.appendChild(aplicar);
  cont.appendChild(defecto);
  $("ag-pesos-nota").textContent = NOTA_PESOS_AG;
}

function textoCromosoma(cromosoma) {
  const pares = cromosoma.slice(0, 4).map(([f, c]) => `(${f},${c})`).join(" → ");
  return cromosoma.length > 4 ? `${pares} …` : pares;
}

function pintarAG() {
  const gens = agDatos.generaciones;
  const sel = $("ag-generacion");
  const anterior = sel.options.length ? Number(sel.value) : NaN;   // leer antes de vaciar el selector
  sel.replaceChildren();
  for (const g of gens) {
    sel.appendChild(nodo("option", "", `generación ${g.generacion} · mejor ${coma(g.mejor, 2)}`));
    sel.lastChild.value = g.generacion;
  }
  const elegida = Number.isFinite(anterior) && anterior < gens.length ? anterior : Math.min(5, gens.length - 1);
  sel.value = elegida;

  // Rango vertical de los datos (el fitness puede ser negativo), con margen
  const valoresY = gens.flatMap((g) => [g.mejor, g.media, g.peor]);
  const yMin = Math.min(...valoresY);
  const yMax = Math.max(...valoresY);
  const margenY = (yMax - yMin) * 0.08 || 0.1;
  curva("ag-curva", "ag-curva-tip", {
    xmin: 0, xmax: Math.max(1, gens.length - 1), ymin: yMin - margenY, ymax: yMax + margenY,
    xs: gens.map((g) => g.generacion),
    series: [
      { valores: gens.map((g) => [g.generacion, g.mejor]), color: "#6ee7a8", ancho: 2.5 },
      { valores: gens.map((g) => [g.generacion, g.media]), color: "#ffb454", ancho: 1.5 },
      { valores: gens.map((g) => [g.generacion, g.peor]), color: "#ff5d6c", ancho: 1, dash: [4, 3] },
    ],
    marcas: [{ x: elegida, color: "rgba(231, 237, 247, 0.5)" }],
    fmtX: (v) => `${Math.round(v)}`,
    fmtY: (v) => coma(v, 1),
    etiqueta: (x) => {
      const g = gens[x];
      return `generación ${g.generacion} · mejor ${coma(g.mejor)} · media ${coma(g.media)} · peor ${coma(g.peor)}`;
    },
    etiquetaVacia: "Pasa el ratón sobre la curva para ver cada generación.",
  });
  pintarPoblacion(elegida);
  pintarCandidatos();
}

function pintarPoblacion(indice) {
  const g = agDatos.generaciones[indice];
  $("ag-resumen").textContent = `Cruces en esta generación: ${g.cruces} · mutaciones: ${g.mutaciones}`;
  const cont = $("ag-poblacion");
  cont.replaceChildren();
  const tabla = nodo("table", "lab-tabla");
  const cab = nodo("tr");
  for (const t of ["#", "cromosoma (f,c)", "fitness", "operación"]) cab.appendChild(nodo("th", "", t));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  const ordenada = [...g.poblacion].sort((a, b) => b.fitness - a.fitness);
  ordenada.forEach((ind, i) => {
    const fila = nodo("tr");
    fila.appendChild(nodo("td", "", String(i + 1)));
    fila.appendChild(nodo("td", "lab-cromo", textoCromosoma(ind.cromosoma)));
    fila.appendChild(nodo("td", "", coma(ind.fitness, 3)));
    fila.appendChild(nodo("td", `lab-op lab-op-${ind.operacion.replace(/\+/g, "-")}`, ind.operacion));
    cuerpo.appendChild(fila);
  });
  tabla.appendChild(cuerpo);
  cont.appendChild(tabla);
}

function pintarCandidatos() {
  const cont = $("ag-candidatos");
  cont.replaceChildren();
  agDatos.candidatos.forEach((c, i) => {
    const b = nodo("button", "chip" + (i === agCandidato ? " activa" : ""), `candidato ${i + 1} · ${coma(c.fitness, 3)}`);
    b.type = "button";
    b.addEventListener("click", () => { agCandidato = i; pintarCandidatos(); });
    cont.appendChild(b);
  });
  const c = agDatos.candidatos[agCandidato];
  const cont2 = $("ag-desglose");
  cont2.replaceChildren();
  const pesos = agDatos.parametros.pesos || {};
  const tabla = nodo("table", "lab-tabla");
  const cab = nodo("tr");
  for (const t of ["componente", "valor", "peso"]) cab.appendChild(nodo("th", "", t));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  for (const k of COMPONENTES_AG) {
    if (c.desglose[k] === undefined) continue;
    const fila = nodo("tr");
    fila.appendChild(nodo("td", "", k));
    fila.appendChild(nodo("td", "", coma(c.desglose[k], 3)));
    fila.appendChild(nodo("td", "", PESOS_AG.includes(k) && pesos[k] !== undefined ? coma(pesos[k], 2) : "-"));
    cuerpo.appendChild(fila);
  }
  const total = nodo("tr", "lab-total");
  total.appendChild(nodo("td", "", "fitness"));
  total.appendChild(nodo("td", "", coma(c.fitness, 3)));
  total.appendChild(nodo("td", "", ""));
  cuerpo.appendChild(total);
  tabla.appendChild(cuerpo);
  cont2.appendChild(tabla);
  cont2.appendChild(nodo("div", "ayuda", `Ruta de ${c.ruta_pasos} pasos. Valores tal como los devuelve el motor; el peso se aplica dentro del fitness.`));
}

async function ejecutarAG() {
  const boton = $("ag-ejecutar");
  const estado = $("ag-estado");
  const parada = $("ag-parada").value;
  boton.disabled = true;
  const inicio = Date.now();
  const progreso = $("ag-progreso");
  progreso.classList.remove("oculto");
  const contar = () => {
    estado.textContent = `Ejecutando el AG… ${Math.round((Date.now() - inicio) / 1000)} s (unos 70 s con 30 generaciones)`;
  };
  contar();
  const reloj = setInterval(contar, 1000);
  const q = new URLSearchParams();
  if (parada) q.set("parada_sin_mejora", parada);
  if (pesosAgTocados) for (const k of PESOS_AG) q.set(`w_${k}`, $(`ag-peso-${k}`).value);
  const datos = await deps.llamar("GET", "/ag" + (q.toString() ? `?${q}` : ""));
  clearInterval(reloj);
  progreso.classList.add("oculto");
  boton.disabled = false;
  if (!datos) {
    estado.textContent = "No se pudo ejecutar el AG (revisa que haya partida).";
    return;
  }
  agDatos = datos;
  agCandidato = 0;
  estado.textContent = `${datos.generaciones_ejecutadas} generaciones · cruces ${datos.cruces} · mutaciones ${datos.mutaciones}`;
  pintarAG();
}

// ---------- Difuso (CA-05) ----------
const UNIVERSOS = ["distancia", "bateria", "inclinacion", "temperatura"];
const ETIQUETA_UNIVERSO = { distancia: "distancia (m)", bateria: "batería (%)", inclinacion: "inclinación (°)", temperatura: "temperatura (°C)" };
const CONTROL_DIF = { distancia: "dif-distancia", bateria: "dif-bateria", inclinacion: "dif-inclinacion", temperatura: "dif-temperatura" };

function parametrosDifuso() {
  return new URLSearchParams({
    distancia: $("dif-distancia").value,
    bateria: $("dif-bateria").value,
    inclinacion: $("dif-inclinacion").value,
    temperatura: $("dif-temperatura").value,
  });
}

async function consultarDifuso() {
  const datos = await deps.llamar("GET", `/difuso?${parametrosDifuso()}`);
  if (!datos) { $("dif-estado").textContent = "Sin respuesta del difuso (revisa que haya partida)."; return; }
  // Cuarta entrada (ARX-38/41): el motor publica la curva de temperatura. Sin ella, el universo se oculta;
  // la curva de prueba (adaptador.js) solo se usa con ?demo
  const demo = new URLSearchParams(location.search).has("demo");
  const prueba = !datos.curvas.temperatura && adaptador.TEMPERATURA_PRUEBA && demo;
  if (prueba) adaptador.inyectarTemperaturaPrueba(datos, Number($("dif-temperatura").value));
  $("dif-estado").textContent = prueba ? "temperatura: datos de prueba (solo con ?demo)" : "";
  for (const k of UNIVERSOS) $(`${CONTROL_DIF[k]}-v`).textContent = coma(datos.entradas[k], k === "distancia" ? 1 : 0);

  for (const k of UNIVERSOS) {
    const bloque = $(`dif-u-${k}`).closest(".lab-bloque");
    if (!datos.curvas[k]) { bloque.classList.add("oculto"); continue; }   // el motor aún no publica esta variable
    bloque.classList.remove("oculto");
    const u = datos.curvas[k];
    const uni = datos.universos[k];
    const entrada = datos.entradas[k];
    const nombres = Object.keys(u.conjuntos);
    const xs = u.x;
    const etiquetaPunto = (x) => {
      const j = indiceMasCercano(xs, x);
      return `${ETIQUETA_UNIVERSO[k]} ${coma(xs[j], 1)} · ` + nombres.map((n) => `${n} ${porcentaje(u.conjuntos[n][j])}`).join(" · ");
    };
    curva(`dif-u-${k}`, `dif-u-${k}-tip`, {
      xmin: uni.min, xmax: uni.max, ymin: 0, ymax: 1, xs,
      series: nombres.map((n, i) => ({ valores: xs.map((x, j) => [x, u.conjuntos[n][j]]), color: COLORES_CONJUNTO[i % 4] })),
      marcas: [{ x: entrada, color: "rgba(231, 237, 247, 0.6)" }],
      fmtY: (v) => coma(v, 1),
      fmtX: (v) => coma(v, k === "distancia" ? 0 : 0),
      etiqueta: etiquetaPunto,
      etiquetaVacia: "Pasa el ratón sobre una curva.",
    });
    const pe = datos.punto_entrada[k];
    $(`dif-u-${k}-entrada`).textContent = `entrada ${coma(entrada, k === "distancia" ? 1 : 0)} → ` +
      Object.keys(pe).map((n) => `${n} ${porcentaje(pe[n])}`).join(" · ");
  }

  const s = datos.salida;
  const nombresSalida = Object.keys(s.conjuntos);
  curva("dif-salida", "dif-salida-tip", {
    xmin: 0, xmax: 1, ymin: 0, ymax: 1, xs: s.universo,
    series: [
      ...nombresSalida.map((n, i) => ({ valores: s.universo.map((x, j) => [x, s.conjuntos[n][j]]), color: COLORES_CONJUNTO[i % 4] })),
      { valores: s.universo.map((x, j) => [x, s.agregado[j]]), color: "#e7edf7", ancho: 1.5, dash: [5, 3] },
    ],
    marcas: [{ x: s.velocidad, color: "#e7edf7" }],
    fmtX: (v) => coma(v, 1),
    fmtY: (v) => coma(v, 1),
    etiqueta: (x) => `velocidad ${coma(s.velocidad, 3)} · agregado ${coma(s.agregado[indiceMasCercano(s.universo, x)], 2)}`,
    etiquetaVacia: "Pasa el ratón sobre la salida.",
  });
  $("dif-velocidad").textContent = `velocidad ${coma(s.velocidad, 3)} · ${s.fallback ? "recurso de respaldo" : "salida normal"}`;

  pintarReglas(datos.reglas, datos.reglas_activadas);
}

function pintarReglas(reglas, activadas) {
  const cont = $("dif-reglas");
  cont.replaceChildren();
  const fuerzas = new Map(activadas.map((r) => [r.id, r.fuerza]));
  for (const r of reglas) {
    const f = fuerzas.get(r.id);
    const fila = nodo("div", "lab-regla" + (f !== undefined ? " activa" : ""));
    const cab = nodo("div", "", `${r.id} · si ${r.si.map(([v, t]) => `${v} es ${t}`).join(" y ")} → ${r.entonces}`);
    fila.appendChild(cab);
    const barra = nodo("div", "barra");
    const relleno = nodo("div", "");
    relleno.style.width = `${f !== undefined ? Math.round(f * 100) : 0}%`;
    barra.appendChild(relleno);
    fila.appendChild(barra);
    fila.appendChild(nodo("div", "ayuda", f !== undefined ? `activa, fuerza ${coma(f, 2)}: ${r.motivo}` : "no activa"));
    cont.appendChild(fila);
  }
}

async function barridoDifuso() {
  const boton = $("dif-barrido");
  boton.disabled = true;
  const q = new URLSearchParams({
    desde: 10, hasta: 1, paso: 1,
    bateria: $("dif-bateria").value,
    inclinacion: $("dif-inclinacion").value,
  });
  const datos = await deps.llamar("GET", `/difuso/barrido?${q}`);
  boton.disabled = false;
  if (!datos) { $("dif-estado").textContent = "El barrido no respondió (revisa que haya partida)."; return; }
  const filas = datos.filas;
  const xs = filas.map((f) => f.distancia);
  curva("dif-barrido-curva", "dif-barrido-tip", {
    xmin: 1, xmax: 10, ymin: 0, ymax: 1, xs,
    series: [{ valores: filas.map((f) => [f.distancia, f.velocidad]), color: "#6ee7a8", ancho: 2.5 }],
    fmtX: (v) => `${Math.round(v)} m`,
    fmtY: (v) => coma(v, 1),
    etiqueta: (x) => {
      const f = filas[indiceMasCercano(xs, x)];
      return `${f.distancia} m · velocidad ${coma(f.velocidad, 3)} · ${f.reglas.map((r) => `${r.id} (${coma(r.fuerza, 2)})`).join(", ") || "sin reglas"}`;
    },
    etiquetaVacia: "Pasa el ratón sobre la curva: de 10 a 1 m.",
  });
  const cont = $("dif-barrido-tabla");
  cont.replaceChildren();
  const tabla = nodo("table", "lab-tabla");
  const cab = nodo("tr");
  for (const t of ["distancia (m)", "velocidad", "reglas activadas"]) cab.appendChild(nodo("th", "", t));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  for (const f of filas) {
    const fila = nodo("tr");
    fila.appendChild(nodo("td", "", String(f.distancia)));
    fila.appendChild(nodo("td", "", coma(f.velocidad, 3)));
    fila.appendChild(nodo("td", "", f.reglas.map((r) => `${r.id} (${coma(r.fuerza, 2)})`).join(", ") || "-"));
    cuerpo.appendChild(fila);
  }
  tabla.appendChild(cuerpo);
  cont.appendChild(tabla);
}

// ---------- RNA (CA-06) ----------
const ETIQUETA_RASGO = {
  proximidad_frontal_m: "proximidad frontal (m)",
  borde_barranco: "borde de barranco",
  gradiente_altura_m: "gradiente de altura (m)",
  vibracion: "vibración",
};
const CLASES = ["libre", "obstáculo", "barranco"];
const COLOR_CLASE = { libre: "#5fd3ff", "obstáculo": "#ffb454", barranco: "#ff5d6c" };
const RASGOS = [
  { id: "rna-proximidad", clave: "proximidad_frontal_m", min: 0, max: 20, paso: 0.1 },
  { id: "rna-gradiente", clave: "gradiente_altura_m", min: -10, max: 10, paso: 0.1 },
  { id: "rna-vibracion", clave: "vibracion", min: -5, max: 5, paso: 0.1 },
];
let rnaUsoRover = true;   // al abrir, se usa la celda frente al rover hasta que se edite un rasgo

function parametrosRNA() {
  const q = new URLSearchParams({ borde: $("rna-borde").value });
  for (const r of RASGOS) q.set(r.clave === "proximidad_frontal_m" ? "proximidad" : r.clave === "gradiente_altura_m" ? "gradiente" : "vibracion", $(r.id).value);
  return q;
}

function rellenarRasgos(entrada) {
  $("rna-proximidad").value = Math.min(20, Math.max(0, entrada.proximidad_frontal_m)).toFixed(1);
  $("rna-gradiente").value = Math.min(10, Math.max(-10, entrada.gradiente_altura_m)).toFixed(1);
  $("rna-vibracion").value = Math.min(5, Math.max(-5, entrada.vibracion)).toFixed(1);
  $("rna-borde").value = entrada.borde_barranco >= 0.5 ? "1" : "0";
  for (const r of RASGOS) $(`${r.id}-v`).textContent = coma($(r.id).value, 1);
}

async function consultarRNA() {
  const q = rnaUsoRover ? "" : `?${parametrosRNA()}`;
  const datos = await deps.llamar("GET", `/rna${q}`);
  if (!datos) { $("rna-accion").textContent = "Sin respuesta de la RNA (revisa que haya partida)."; return; }
  if (rnaUsoRover) rellenarRasgos(datos.entrada);
  for (const r of RASGOS) $(`${r.id}-v`).textContent = coma($(r.id).value, 1);

  const e = datos.entrada;
  const nrm = datos.normalizada;
  const tabla = nodo("table", "lab-tabla");
  const cab = nodo("tr");
  for (const t of ["rasgo", "entrada", "normalizada"]) cab.appendChild(nodo("th", "", t));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  for (const k of Object.keys(ETIQUETA_RASGO)) {
    const fila = nodo("tr");
    fila.appendChild(nodo("td", "", ETIQUETA_RASGO[k]));
    fila.appendChild(nodo("td", "", coma(e[k === "borde_barranco" ? "borde_barranco" : k], 2)));
    fila.appendChild(nodo("td", "", coma(nrm[k], 2)));
    cuerpo.appendChild(fila);
  }
  tabla.appendChild(cuerpo);
  $("rna-entrada").replaceChildren(tabla);
  $("rna-entrada").appendChild(nodo("div", "ayuda", `borde de barranco: ${e.borde_barranco >= 0.5 ? "sí" : "no"} (entrada ${coma(e.borde_barranco, 0)})`));

  const probs = $("rna-probs");
  probs.replaceChildren();
  const mayor = CLASES.reduce((a, c) => (datos.probabilidades[c] > datos.probabilidades[a] ? c : a), CLASES[0]);
  for (const c of CLASES) {
    const p = datos.probabilidades[c];
    const fila = nodo("div", "lab-prob" + (c === mayor ? " ganadora" : ""));
    fila.appendChild(nodo("div", "", `${c} ${porcentaje(p)}`));
    const barra = nodo("div", "barra");
    const relleno = nodo("div", "");
    relleno.style.width = `${(p * 100).toFixed(1)}%`;
    relleno.style.background = COLOR_CLASE[c];
    barra.appendChild(relleno);
    fila.appendChild(barra);
    probs.appendChild(fila);
  }
  $("rna-accion").textContent = `acción: ${datos.accion} · confianza ${porcentaje(datos.confianza)}` +
    (datos.motivos && datos.motivos.length ? ` · motivos: ${datos.motivos.join(", ")}` : "");

  pintarActivaciones(datos.activaciones);
}

// Mapa de calor de una capa: azul para positivo, rojo para negativo, intensidad por magnitud
function capaCalor(nombre, valores) {
  const max = Math.max(1e-9, ...valores.map((v) => Math.abs(v)));
  const fila = nodo("div", "lab-capa");
  fila.appendChild(nodo("div", "ayuda", `${nombre} (${valores.length})`));
  const celdas = nodo("div", "lab-celdas");
  valores.forEach((v) => {
    const c = nodo("span", "lab-celda");
    const a = Math.min(1, Math.abs(v) / max);
    c.style.background = v >= 0 ? `rgba(95, 211, 255, ${a.toFixed(2)})` : `rgba(255, 93, 108, ${a.toFixed(2)})`;
    c.title = coma(v, 3);
    celdas.appendChild(c);
  });
  fila.appendChild(celdas);
  return fila;
}

function pintarActivaciones(act) {
  const cont = $("rna-activaciones");
  cont.replaceChildren();
  cont.appendChild(capaCalor("oculta 1", act.oculta_1));
  cont.appendChild(capaCalor("oculta 2", act.oculta_2));
  const logits = nodo("div", "lab-logits");
  CLASES.forEach((c, i) => logits.appendChild(nodo("div", "", `${c}: ${coma(act.salida_logits[i], 2)}`)));
  cont.appendChild(logits);
  cont.appendChild(nodo("div", "ayuda", "Azul: activación positiva; rojo: negativa. La intensidad sigue la magnitud dentro de cada capa."));
}

async function cargarEvaluacion() {
  const ev = await deps.llamar("GET", "/rna/evaluacion");
  const cont = $("rna-evaluacion");
  cont.replaceChildren();
  if (!ev) { cont.textContent = "La evaluación no respondió (revisa que haya partida)."; return; }
  const metricas = nodo("div", "lab-metricas");
  const lineas = [
    ["recall de barranco", porcentaje(ev.recall_barranco), true],
    ["macro-F1", coma(ev.macro_f1, 3), false],
    ["error de calibración", coma(ev.error_calibracion, 3), false],
    ["exactitud de la línea base", porcentaje(ev.linea_base_exactitud), false],
    ["muestras de prueba", String(ev.muestras_prueba), false],
  ];
  for (const [nombre, valor, destacar] of lineas) {
    const m = nodo("div", "lab-metrica" + (destacar ? " destacada" : ""));
    m.appendChild(nodo("div", "lab-metrica-valor", valor));
    m.appendChild(nodo("div", "ayuda", nombre));
    metricas.appendChild(m);
  }
  cont.appendChild(metricas);

  const tabla = nodo("table", "lab-tabla lab-confusion");
  const cab = nodo("tr");
  cab.appendChild(nodo("th", "", "real \\ predicha"));
  for (const c of ev.clases) cab.appendChild(nodo("th", "", c));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  ev.matriz_confusion.forEach((fila, i) => {
    const tr = nodo("tr");
    tr.appendChild(nodo("th", "", ev.clases[i]));
    const suma = fila.reduce((a, b) => a + b, 0) || 1;
    fila.forEach((n, j) => {
      const td = nodo("td", "", String(n));
      const intensidad = n / suma;
      td.style.background = i === j ? `rgba(110, 231, 168, ${(0.15 + 0.6 * intensidad).toFixed(2)})` : `rgba(255, 93, 108, ${(0.05 + 0.5 * intensidad).toFixed(2)})`;
      tr.appendChild(td);
    });
    cuerpo.appendChild(tr);
  });
  tabla.appendChild(cuerpo);
  cont.appendChild(tabla);
  cont.appendChild(nodo("div", "ayuda", `Filas: clase real. Columnas: clase predicha. Mapas de prueba: ${ev.mapas_prueba.join(", ")}. ${ev.nota}`));
}

// ---------- overlay y arranque ----------
const deps = { llamar: null, avisar: null };
let cargaEvaluacion = false;

function mostrarSeccion(nombre) {
  for (const s of ["ag", "difuso", "rna", "politicas"]) {
    $(`lab-${s}`).classList.toggle("oculto", s !== nombre);
  }
  for (const b of document.querySelectorAll(".lab-tab")) b.classList.toggle("activa", b.dataset.lab === nombre);
  requestAnimationFrame(() => {
    if (nombre === "difuso") consultarDifuso();
    if (nombre === "rna") { consultarRNA(); if (!cargaEvaluacion) { cargaEvaluacion = true; cargarEvaluacion(); } }
    if (nombre === "ag" && agDatos) pintarAG();
    if (nombre === "politicas") { if (polDatos) pintarPoliticas(); else cargarPoliticas(); }
  });
}

export function iniciarLaboratorios(dependencias) {
  deps.llamar = dependencias.llamar;
  deps.avisar = dependencias.avisar;

  $("abrir-laboratorio").addEventListener("click", () => {
    $("laboratorio").classList.remove("oculto");
    mostrarSeccion(document.querySelector(".lab-tab.activa")?.dataset.lab || "ag");
  });
  $("cerrar-laboratorio").addEventListener("click", () => $("laboratorio").classList.add("oculto"));
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !$("laboratorio").classList.contains("oculto")) $("laboratorio").classList.add("oculto");
  });
  for (const b of document.querySelectorAll(".lab-tab")) b.addEventListener("click", () => mostrarSeccion(b.dataset.lab));

  $("ag-ejecutar").addEventListener("click", ejecutarAG);
  iniciarPoliticas();
  iniciarPesosAG();
  $("ag-generacion").addEventListener("change", (ev) => {
    if (!agDatos) return;
    const i = Number(ev.target.value);
    const cfg = curvas.get("ag-curva").cfg;
    cfg.marcas = [{ x: i, color: "rgba(231, 237, 247, 0.5)" }];
    dibujarLineas($("ag-curva"), cfg);
    pintarPoblacion(i);
  });

  const reconsultarDif = conRetardo(consultarDifuso, 200);
  for (const k of UNIVERSOS) $(CONTROL_DIF[k]).addEventListener("input", reconsultarDif);
  $("dif-barrido").addEventListener("click", barridoDifuso);

  const reconsultarRNA = conRetardo(() => { rnaUsoRover = false; consultarRNA(); }, 200);
  for (const r of RASGOS) $(r.id).addEventListener("input", reconsultarRNA);
  $("rna-borde").addEventListener("change", reconsultarRNA);
  $("rna-restablecer").addEventListener("click", () => { rnaUsoRover = true; consultarRNA(); });
}

// ---------- comparación de políticas (CA del PDF; contrato §7 de CONTRATOS_GRAFICOS.md) ----------
const VARIANTES_POL = [["hibrido", "híbrido"], ["sin_rna", "sin RNA"], ["sin_difuso", "sin difuso"], ["sin_ag", "sin AG"]];
const ETIQUETA_METRICA_POL = { pasos: "pasos", bateria_final: "batería final", sitios_visitados: "sitios visitados", colisiones: "colisiones" };
let polDatos = null;
let polBarras = [];   // geometría de las barras para el cursor

// Escenarios (ARX-28e, ev3-d55 A). El parámetro ?escenario= lo recibe el servidor en ARX-28d;
// el congelado no envía parámetro (respuesta idéntica a la de siempre).
async function cargarPoliticas() {
  const escenario = $("pol-escenario").value;
  $("pol-estado").textContent = `Consultando /comparacion (${escenario})…`;
  const datos = await deps.llamar("GET", "/comparacion" + (escenario === "congelado" ? "" : `?escenario=${encodeURIComponent(escenario)}`));
  if (!datos || !datos.variantes) {
    $("pol-estado").textContent = datos && (datos.motivo || datos.aviso)
      ? `Sin datos del escenario ${escenario}: ${datos.motivo || datos.aviso}`
      : "La comparación no respondió con el contrato esperado.";
    return;
  }
  polDatos = datos;
  const servido = datos.escenario || "congelado";
  let estado = `escenario ${servido} · ${datos.semillas.length} semillas por variante`;
  if (escenario !== "congelado" && !datos.escenario) {
    estado += " · AVISO: el servidor aún no distingue escenarios (llega con ARX-28d); estas cifras son las del congelado";
  }
  $("pol-estado").textContent = estado;
  $("pol-nota").textContent = datos.nota || "";
  pintarPoliticas();
}

function pintarPoliticas() {
  if (!polDatos) return;
  const metrica = $("pol-metrica").value;
  const filas = VARIANTES_POL.filter(([k]) => polDatos.variantes[k]).map(([k, nombre]) => {
    const v = polDatos.variantes[k];
    const m = v[metrica] || { media: 0, desviacion: 0 };
    return { nombre, v, media: m.media, desv: m.desviacion || 0 };
  });
  dibujarBarrasPol(filas);
  pintarTablaPol();
}

function dibujarBarrasPol(filas) {
  const canvas = $("pol-barras");
  const p = preparar(canvas);
  polBarras = [];
  if (!p || !filas.length) return;
  const { ctx, w, h } = p;
  const m = { l: 52, r: 14, t: 14, b: 40 };
  const top = Math.max(1, ...filas.map((f) => f.media + f.desv)) * 1.1;
  const Y = (y) => h - m.b - (y / top) * (h - m.t - m.b);
  ctx.font = "12px 'Segoe UI', system-ui, sans-serif";
  ctx.strokeStyle = "rgba(150, 200, 255, 0.12)";
  ctx.fillStyle = "#98a4bb";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = (top * i) / 4;
    const y = Math.round(Y(v)) + 0.5;
    ctx.beginPath(); ctx.moveTo(m.l, y); ctx.lineTo(w - m.r, y); ctx.stroke();
    ctx.fillText(coma(v, 1), m.l - 6, y);
  }
  const ancho = (w - m.l - m.r) / filas.length;
  const colores = ["#6ee7a8", "#5fd3ff", "#ffb454", "#ff5d6c"];
  filas.forEach((f, i) => {
    const cx = m.l + ancho * (i + 0.5);
    const bw = Math.min(56, ancho * 0.5);
    const yMedia = Y(f.media);
    ctx.fillStyle = colores[i % colores.length] + "cc";
    ctx.fillRect(cx - bw / 2, yMedia, bw, h - m.b - yMedia);
    // Barra de error: media ± desviación (sin bajar de cero)
    const yHi = Y(f.media + f.desv);
    const yLo = Y(Math.max(0, f.media - f.desv));
    ctx.strokeStyle = "#e7edf7";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx, yHi); ctx.lineTo(cx, yLo);
    ctx.moveTo(cx - 8, yHi); ctx.lineTo(cx + 8, yHi);
    ctx.moveTo(cx - 8, yLo); ctx.lineTo(cx + 8, yLo);
    ctx.stroke();
    ctx.fillStyle = "#c8d2e4";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(f.nombre, cx, h - m.b + 8);
    polBarras.push({ x0: cx - bw / 2, x1: cx + bw / 2, f });
  });
  ctx.textAlign = "left";
  ctx.fillStyle = "#98a4bb";
  ctx.fillText(ETIQUETA_METRICA_POL[$("pol-metrica").value] || "", m.l, 0);
}

function pintarTablaPol() {
  const cont = $("pol-tabla");
  cont.replaceChildren();
  const tabla = nodo("table", "lab-tabla");
  const cab = nodo("tr");
  for (const t of ["política", "éxito", "pasos (media · mediana · desv.)", "colisiones", "batería (mediana)"]) cab.appendChild(nodo("th", "", t));
  tabla.appendChild(nodo("thead")).appendChild(cab);
  const cuerpo = nodo("tbody");
  for (const [k, nombre] of VARIANTES_POL) {
    const v = polDatos.variantes[k];
    if (!v) continue;
    const fila = nodo("tr");
    fila.appendChild(nodo("td", "", nombre));
    fila.appendChild(nodo("td", "", `${v.exitos}/${v.n} (${coma(v.tasa_exito, 1)} %)`));
    fila.appendChild(nodo("td", "", `${coma(v.pasos.media, 1)} · ${coma(v.pasos.mediana, 1)} · ${coma(v.pasos.desviacion, 2)}`));
    fila.appendChild(nodo("td", "", coma(v.colisiones.media, 2)));
    fila.appendChild(nodo("td", "", coma(v.bateria_final.mediana, 1)));
    cuerpo.appendChild(fila);
  }
  tabla.appendChild(cuerpo);
  cont.appendChild(tabla);
}

function iniciarPoliticas() {
  $("pol-barras-tip").textContent = "Pasa el ratón sobre una barra para ver su valor exacto.";
  $("pol-cargar").addEventListener("click", cargarPoliticas);
  $("pol-escenario").addEventListener("change", cargarPoliticas);
  $("pol-metrica").addEventListener("change", pintarPoliticas);
  const canvas = $("pol-barras");
  canvas.addEventListener("mousemove", (ev) => {
    const r = canvas.getBoundingClientRect();
    const mx = ev.clientX - r.left;
    const b = polBarras.find((g) => mx >= g.x0 - 6 && mx <= g.x1 + 6);
    $("pol-barras-tip").textContent = b
      ? `${b.f.nombre}: media ${coma(b.f.media, 2)} ± ${coma(b.f.desv, 2)} (${ETIQUETA_METRICA_POL[$("pol-metrica").value]})`
      : "Pasa el ratón sobre una barra.";
  });
}
