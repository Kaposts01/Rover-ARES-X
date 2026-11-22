// Editor de reglas difusas (Laboratorios → Difuso → «Editar reglas»): tabla de reglas editable, puntos de las funciones de pertenencia
// arrastrables o con campos numéricos, y el efecto en vivo (salida, activaciones, superficie y barrido, siempre «antes → después»).
// El cálculo de la vista previa es local (difuso_reglas_datos.js): al cambiar algo no se espera al servidor. Los cambios válidos se aplican
// a la partida con PUT /difuso/reglas (con una pequeña espera); «Restaurar» llama a DELETE. Sin soporte en el motor (404), todo queda en
// vista previa y se dice. Todo con textContent; textos en textos.js (EDIT).
import { EDIT, reglasActivadas } from "/static/textos.js?v=r14";
import {
  adaptarReglas, modeloDeFabrica, clonar, inferir, barrido, superficie, validar, viabilidadAntecedente, diferencias, cuerpoPUT,
} from "/static/difuso_reglas_datos.js?v=r14";

const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };
const coma = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d).replace(".", ","));
const COLORES = ["#ff5d6c", "#ffb454", "#5fd3ff", "#6ee7a8", "#c79bff"];
const ESPERA_APLICAR_MS = 600;
const ENTRADAS_POR_DEFECTO = { distancia: 1, bateria: 90, inclinacion: 2, temperatura: 15 };
const NOMBRE_VARIABLE = { distancia: "distancia", bateria: "batería", inclinacion: "inclinación", temperatura: "temperatura" };
const UNIDAD = { distancia: "m", bateria: "u.", inclinacion: "°", temperatura: "°C" };
const nombreVar = (v) => NOMBRE_VARIABLE[v] || v;

async function pedir(metodo, ruta, cuerpo) {
  try {
    const r = await fetch(ruta, { method: metodo, headers: { "Content-Type": "application/json" }, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    return { ok: r.ok, status: r.status, cuerpo: await r.json().catch(() => null) };
  } catch (e) { return { ok: false, status: 0, cuerpo: null }; }
}
const motivoDe = (r) => (r.cuerpo && (r.cuerpo.motivo || r.cuerpo.detail || r.cuerpo.mensaje)) ? String(typeof (r.cuerpo.motivo || r.cuerpo.detail) === "string" ? (r.cuerpo.motivo || r.cuerpo.detail) : JSON.stringify(r.cuerpo.detail)) : `error ${r.status}`;

// deps: { contenedor, dibujarLineas, preparar, alEstado({personalizadas, soloPrevia, cambios}) }
export function crearEditorDifuso({ contenedor, dibujarLineas, preparar, alEstado }) {
  let base = null, modelo = null, soloPrevia = false, personalizadas = false, entradas = { ...ENTRADAS_POR_DEFECTO };
  let temporizador = null, firmaAplicada = "", versionAplicar = 0, mostrarCambio = false, tablaRows = new Map();

  // ---------- esqueleto ----------
  const raiz = el("div", "dedit");
  const ayuda = el("p", "ayuda", EDIT.ayuda);
  const barra = el("div", "dedit-barra");
  const insignia = el("span", "badge-reglas", EDIT.delPlaneta); insignia.id = "dedit-insignia";
  const restaurar = el("button", "secundario", EDIT.restaurar); restaurar.type = "button"; restaurar.id = "dedit-restaurar";
  const mensaje = el("span", "ayuda dedit-mensaje"); mensaje.setAttribute("aria-live", "polite"); mensaje.id = "dedit-mensaje";
  barra.append(insignia, restaurar, mensaje);
  const avisos = el("ul", "dedit-avisos"); avisos.id = "dedit-avisos";
  const bSalida = el("div", "lab-bloque");
  const resumenSalida = el("div", "dedit-resumen"); resumenSalida.id = "dedit-resumen";
  const cSalida = el("canvas", "lienzo"); const cajaSalida = el("div", "lienzo-caja"); cajaSalida.append(cSalida);
  bSalida.append(el("div", "titulo-seccion", EDIT.salidaTitulo), resumenSalida, cajaSalida, el("div", "ayuda", EDIT.curvaOriginal));
  const bTabla = el("div", "lab-bloque");
  const tablaCaja = el("div", "lab-scroll dedit-tabla"); tablaCaja.id = "dedit-tabla";
  bTabla.append(el("div", "titulo-seccion", EDIT.activaciones), tablaCaja, el("div", "ayuda", EDIT.tablaAyuda));
  const bPertenencia = el("div", "lab-bloque");
  const rejilla = el("div", "dedit-rejilla"); rejilla.id = "dedit-pertenencia";
  bPertenencia.append(el("div", "titulo-seccion", EDIT.pertenencia), rejilla);
  const bGraficos = el("div", "lab-grid-2");
  const bSup = el("div", "lab-bloque");
  const cSup = el("canvas", "lienzo"); const cajaSup = el("div", "lienzo-caja"); cajaSup.append(cSup);
  const verCambio = el("input"); verCambio.type = "checkbox"; verCambio.id = "dedit-ver-cambio";
  const etCambio = el("label", "veto"); etCambio.append(verCambio, document.createTextNode(` ${EDIT.verCambio}`));
  const tipSup = el("div", "tip");
  bSup.append(el("div", "titulo-seccion", EDIT.superficie), cajaSup, tipSup, etCambio);
  const bBarr = el("div", "lab-bloque");
  const cBarr = el("canvas", "lienzo"); const cajaBarr = el("div", "lienzo-caja"); cajaBarr.append(cBarr);
  bBarr.append(el("div", "titulo-seccion", EDIT.barrido), cajaBarr);
  bGraficos.append(bSup, bBarr);
  raiz.append(ayuda, barra, avisos, bSalida, bTabla, bPertenencia, bGraficos);
  contenedor.replaceChildren(raiz);

  // ---------- estado visible ----------
  function cambios() { return base && modelo ? diferencias(base, modelo).total : 0; }
  function notificar() { if (alEstado) alEstado({ personalizadas, soloPrevia, cambios: cambios() }); }
  function pintarInsignia() {
    const n = cambios();
    const activa = soloPrevia ? n > 0 : personalizadas;
    insignia.textContent = soloPrevia ? (n > 0 ? EDIT.vistaPrevia : EDIT.delPlaneta) : (personalizadas ? EDIT.personalizadas : EDIT.delPlaneta);
    insignia.classList.toggle("inactiva", !activa);
    insignia.title = n ? EDIT.cambios(n) : EDIT.sinCambios;
    restaurar.disabled = !(personalizadas || n > 0);
  }

  // ---------- recálculo en vivo ----------
  const hoy = () => ({ ...ENTRADAS_POR_DEFECTO, ...entradas });
  function pintarAvisos(mensajes) {
    avisos.replaceChildren(...mensajes.map((m) => el("li", `dedit-aviso ${m.tipo}`, m.texto)));
  }
  function pintarSalida(antes, despues) {
    const dif = Math.abs(despues.velocidad - antes.velocidad) > 1e-6;
    resumenSalida.replaceChildren(
      el("span", "dedit-clave", EDIT.salidaDe),
      el("span", "dedit-antes", `${EDIT.antes} ${coma(antes.velocidad, 3)}`), document.createTextNode(" → "),
      el("strong", `dedit-despues${dif ? " cambio" : ""}`, `${EDIT.despues} ${coma(despues.velocidad, 3)}`),
      el("span", "ayuda", ` · ${despues.fallback ? "sin reglas activadas: valor de respaldo" : reglasActivadas(despues.reglas.filter((r) => r.fuerza > 0).length)}`));
    const [u0, u1] = modelo.salida.universo;
    const series = [];
    Object.entries(modelo.salida.etiquetas).forEach(([n, pts], i) => series.push({ valores: antes.universo.map((x) => [x, curvaY(pts, x)]), color: COLORES[i % 5], ancho: 1 }));
    series.push({ valores: antes.universo.map((x, j) => [x, antes.agregado[j]]), color: "#9fb2c8", ancho: 1.5, dash: [5, 4] });
    series.push({ valores: despues.universo.map((x, j) => [x, despues.agregado[j]]), color: "#ffffff", ancho: 2.5 });
    dibujarLineas(cSalida, { xmin: u0, xmax: u1, ymin: 0, ymax: 1, series, marcas: [{ x: antes.velocidad, color: "#9fb2c8" }, { x: despues.velocidad, color: "#ffffff" }], fmtX: (v) => coma(v, 1), fmtY: (v) => coma(v, 1), xs: [] });
  }
  const curvaY = (pts, x) => {
    const p = pts.length === 3 ? [pts[0], pts[1], pts[1], pts[2]] : pts;
    if (x < p[0] || x > p[3]) return 0;
    const izq = p[1] > p[0] ? (x - p[0]) / Math.max(p[1] - p[0], 1e-12) : (x >= p[1] ? 1 : 0);
    const der = p[3] > p[2] ? (p[3] - x) / Math.max(p[3] - p[2], 1e-12) : (x <= p[2] ? 1 : 0);
    return Math.min(1, Math.max(0, Math.min(izq, der)));
  };
  function actualizarFuerzas(antes, despues) {
    for (const [id, f] of tablaRows) {
      const a = antes.reglas.find((r) => r.id === id), d = despues.reglas.find((r) => r.id === id);
      f.antes.textContent = coma(a ? a.fuerza : 0, 2); f.despues.textContent = coma(d ? d.fuerza : 0, 2);
      f.barra.style.width = `${Math.round((d ? d.fuerza : 0) * 100)}%`;
      f.fila.classList.toggle("activa", !!d && d.fuerza > 0);
      f.fila.classList.toggle("cambio", !!a && !!d && Math.abs(a.fuerza - d.fuerza) > 1e-6);
      const via = viabilidadAntecedente(modelo.reglas.find((r) => r.id === id), modelo);
      f.viable.textContent = via.viable ? EDIT.viable : EDIT.nada; f.viable.title = via.motivo; f.viable.classList.toggle("mal", !via.viable);
    }
  }
  function pintarBarrido() {
    const a = barrido(base, hoy()), d = barrido(modelo, hoy());
    dibujarLineas(cBarr, { xmin: 1, xmax: 10, ymin: 0, ymax: 1, xs: [],
      series: [{ valores: a.map((f) => [f.distancia, f.velocidad]), color: "#9fb2c8", ancho: 1.5, dash: [5, 4] }, { valores: d.map((f) => [f.distancia, f.velocidad]), color: "#6ee7a8", ancho: 2.5 }],
      fmtX: (v) => `${Math.round(v)} m`, fmtY: (v) => coma(v, 1) });
  }
  let geoSup = null;
  function pintarSuperficie() {
    const s1 = superficie(modelo, hoy()), s0 = superficie(base, hoy());
    const p = preparar(cSup);
    if (!p || !s1) return;
    const { ctx, w, h } = p;
    const m = { l: 46, r: 8, t: 8, b: 26 }, nx = s1.xs.length, ny = s1.ys.length;
    const cw = (w - m.l - m.r) / nx, ch = (h - m.t - m.b) / ny;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const v = s1.z[j][i], dlt = v - s0.z[j][i];
      ctx.fillStyle = mostrarCambio ? colorCambio(dlt) : colorVelocidad(v);
      ctx.fillRect(m.l + i * cw, h - m.b - (j + 1) * ch, Math.ceil(cw) + 0.5, Math.ceil(ch) + 0.5);
    }
    ctx.fillStyle = "#98a4bb"; ctx.font = "11px 'Segoe UI', system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (let k = 0; k <= 4; k++) ctx.fillText(coma(s1.xs[0] + ((s1.xs[nx - 1] - s1.xs[0]) * k) / 4, 0), m.l + ((w - m.l - m.r) * k) / 4, h - m.b + 5);
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (let k = 0; k <= 2; k++) ctx.fillText(coma(s1.ys[0] + ((s1.ys[ny - 1] - s1.ys[0]) * k) / 2, 0), m.l - 5, h - m.b - ((h - m.t - m.b) * k) / 2);
    ctx.textAlign = "left"; ctx.fillText(`${EDIT.ejeBateria} ↑   ${EDIT.ejeDistancia} →`, m.l + 4, m.t + 6);
    // marca de la entrada actual
    const e = hoy(); const ex = m.l + ((e.distancia - s1.xs[0]) / (s1.xs[nx - 1] - s1.xs[0])) * (w - m.l - m.r), ey = h - m.b - ((e.bateria - s1.ys[0]) / (s1.ys[ny - 1] - s1.ys[0])) * (h - m.t - m.b);
    ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(ex, ey, 5, 0, Math.PI * 2); ctx.stroke();
    geoSup = { m, w, h, s0, s1, nx, ny };
  }
  const rampa = [[0.09, 0.15, 0.4], [0.1, 0.6, 0.8], [0.45, 0.9, 0.55], [1, 0.92, 0.45]];
  function colorVelocidad(v) {
    const t = Math.min(1, Math.max(0, v)) * 3, i = Math.min(2, Math.floor(t)), f = t - i;
    const c = rampa[i].map((a, k) => a + (rampa[i + 1][k] - a) * f);
    return `rgb(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)})`;
  }
  function colorCambio(d) {
    const t = Math.min(1, Math.abs(d) / 0.5);
    return d >= 0 ? `rgba(110,231,168,${(0.08 + 0.9 * t).toFixed(2)})` : `rgba(255,93,108,${(0.08 + 0.9 * t).toFixed(2)})`;
  }
  cSup.addEventListener("mousemove", (ev) => {
    if (!geoSup) return;
    const r = cSup.getBoundingClientRect(), { m, w, h, s0, s1, nx, ny } = geoSup;
    const i = Math.floor(((ev.clientX - r.left - m.l) / (w - m.l - m.r)) * nx), j = Math.floor(((h - m.b - (ev.clientY - r.top)) / (h - m.t - m.b)) * ny);
    if (i < 0 || j < 0 || i >= nx || j >= ny) { tipSup.textContent = ""; return; }
    tipSup.textContent = `distancia ${coma(s1.xs[i], 1)} m · batería ${coma(s1.ys[j], 0)} u. · velocidad ${coma(s0.z[j][i], 2)} → ${coma(s1.z[j][i], 2)}`;
  });
  cSup.addEventListener("mouseleave", () => { tipSup.textContent = ""; });
  verCambio.addEventListener("change", () => { mostrarCambio = verCambio.checked; pintarSuperficie(); });

  let marco = 0;
  function recalcular({ estructura = false } = {}) {
    if (!modelo) return;
    if (estructura) pintarTabla();
    cancelAnimationFrame(marco);
    marco = requestAnimationFrame(() => {
      if (!modelo) return;
      const antes = inferir(base, hoy()), despues = inferir(modelo, hoy());
      pintarSalida(antes, despues); actualizarFuerzas(antes, despues); pintarBarrido(); pintarSuperficie(); pintarCurvas();
    });
    const v = validar(modelo);
    pintarAvisos(v);
    pintarInsignia();
    programarAplicar(v);
    notificar();
  }

  // ---------- aplicar a la partida ----------
  function programarAplicar(validacion) {
    clearTimeout(temporizador);
    const hayError = validacion.some((m) => m.tipo === "error");
    if (hayError) { mensaje.textContent = EDIT.hayErrores; return; }
    if (soloPrevia) { mensaje.textContent = cambios() ? EDIT.sinSoporte : EDIT.sinCambios; return; }
    const firma = JSON.stringify(cuerpoPUT(modelo, base));
    if (firma === firmaAplicada) { mensaje.textContent = cambios() ? "" : EDIT.sinCambios; return; }   // lo que se ve ya es lo que tiene la partida
    mensaje.textContent = EDIT.aplicando;
    const version = ++versionAplicar;
    temporizador = setTimeout(async () => {
      const r = await pedir("PUT", "/difuso/reglas", cuerpoPUT(modelo, base));
      if (version !== versionAplicar) return;   // llegó otra edición: esa respuesta ya no cuenta
      if (r.ok) { firmaAplicada = firma; personalizadas = r.cuerpo && typeof r.cuerpo.personalizadas === "boolean" ? r.cuerpo.personalizadas : true; mensaje.textContent = EDIT.aplicada; }
      else if ([404, 405, 501].includes(r.status)) { soloPrevia = true; mensaje.textContent = EDIT.sinSoporte; }
      else mensaje.textContent = EDIT.noAplicada(motivoDe(r));
      pintarInsignia(); notificar();
    }, ESPERA_APLICAR_MS);
  }
  restaurar.addEventListener("click", async () => {
    clearTimeout(temporizador); versionAplicar++;
    mensaje.textContent = EDIT.restaurando;
    if (soloPrevia) { modelo = clonar(base); personalizadas = false; mensaje.textContent = EDIT.restauradas; pintarTabla(); pintarEditores(); recalcular(); return; }
    const r = await pedir("DELETE", "/difuso/reglas");
    if (!r.ok && ![404, 405].includes(r.status)) { mensaje.textContent = EDIT.noAplicada(motivoDe(r)); return; }
    await cargar();
    mensaje.textContent = EDIT.restauradas;
  });

  // ---------- tabla de reglas ----------
  function selector(opciones, valor, alCambiar, etiqueta, rotulos = {}) {
    const s = el("select", "dedit-sel"); s.setAttribute("aria-label", etiqueta);
    const lista = opciones.includes(valor) || valor === "" ? opciones : [valor, ...opciones];
    for (const o of lista) { const op = el("option", null, rotulos[o] || o); op.value = o; s.append(op); }
    s.value = valor; s.addEventListener("change", () => alCambiar(s.value));
    return s;
  }
  function pintarTabla() {
    tablaRows = new Map();
    const tabla = el("table", "lab-tabla dedit-tabla-reglas");
    const cab = el("tr");
    for (const t of [EDIT.colActiva, EDIT.colRegla, EDIT.colPeso, EDIT.colViable, EDIT.colFuerza]) cab.append(el("th", null, t));
    const encabezado = el("thead"); encabezado.append(cab); tabla.append(encabezado);
    const cuerpo = el("tbody");
    const vars = Object.keys(modelo.variables), salidas = Object.keys(modelo.salida.etiquetas);
    for (const r of modelo.reglas) {
      const fila = el("tr", "dedit-regla"); fila.dataset.regla = r.id;
      const cActiva = el("td"); const chk = el("input"); chk.type = "checkbox"; chk.checked = r.activa; chk.setAttribute("aria-label", `${EDIT.colActiva} ${r.id}`);
      chk.addEventListener("change", () => { r.activa = chk.checked; fila.classList.toggle("apagada", !r.activa); recalcular(); });
      cActiva.append(chk);
      const cRegla = el("td", "dedit-celda-regla");
      cRegla.append(el("strong", null, `${r.id} `));
      r.si.forEach(([v, e], k) => {
        cRegla.append(document.createTextNode(k === 0 ? `${EDIT.si} ` : ` ${EDIT.y} `));
        const libres = vars.filter((x) => x === v || !r.si.some(([u]) => u === x));
        cRegla.append(selector(libres, v, (nv) => { r.si[k] = [nv, Object.keys(modelo.variables[nv].etiquetas)[0]]; recalcular({ estructura: true }); }, `variable ${k + 1}`, NOMBRE_VARIABLE));
        cRegla.append(document.createTextNode(` ${EDIT.es} `));
        cRegla.append(selector(Object.keys((modelo.variables[v] || { etiquetas: {} }).etiquetas), e, (ne) => { r.si[k] = [v, ne]; recalcular(); }, `etiqueta ${k + 1}`));
        if (r.si.length > 1) { const q = el("button", "dedit-mini", "✕"); q.type = "button"; q.title = EDIT.quitar; q.setAttribute("aria-label", EDIT.quitar); q.addEventListener("click", () => { r.si.splice(k, 1); recalcular({ estructura: true }); }); cRegla.append(q); }
      });
      if (r.si.length < vars.length) {
        const mas = el("button", "dedit-mini", EDIT.agregar); mas.type = "button";
        mas.addEventListener("click", () => { const libre = vars.find((x) => !r.si.some(([u]) => u === x)); if (libre) { r.si.push([libre, Object.keys(modelo.variables[libre].etiquetas)[0]]); recalcular({ estructura: true }); } });
        cRegla.append(" ", mas);
      }
      cRegla.append(document.createTextNode(` → ${EDIT.entonces} `));
      cRegla.append(selector(salidas, r.entonces, (n) => { r.entonces = n; recalcular(); }, "velocidad de salida"));
      if (r.texto) cRegla.append(el("div", "ayuda dedit-texto", r.texto));
      const cPeso = el("td", "dedit-celda-peso");
      const rango = el("input"); rango.type = "range"; rango.min = "0"; rango.max = "1"; rango.step = "0.05"; rango.value = String(Math.min(1, Math.max(0, r.peso))); rango.setAttribute("aria-label", `${EDIT.colPeso} ${r.id}`);
      const num = el("input", "dedit-num"); num.type = "number"; num.min = "0"; num.max = "1"; num.step = "0.05"; num.value = String(r.peso); num.setAttribute("aria-label", `${EDIT.colPeso} ${r.id} (número)`);
      rango.addEventListener("input", () => { r.peso = Number(rango.value); num.value = rango.value; recalcular(); });
      num.addEventListener("input", () => { r.peso = num.value === "" ? NaN : Number(num.value); if (num.value !== "" && r.peso >= 0 && r.peso <= 1) rango.value = num.value; recalcular(); });
      cPeso.append(rango, num);
      const cViable = el("td", "dedit-viable");
      const cFuerza = el("td", "dedit-fuerza");
      const a = el("span", "dedit-antes"), d = el("strong", "dedit-despues"), barra2 = el("div", "barra"), rel = el("div");
      barra2.append(rel); cFuerza.append(a, document.createTextNode(" → "), d, barra2);
      fila.classList.toggle("apagada", !r.activa);
      fila.append(cActiva, cRegla, cPeso, cViable, cFuerza); cuerpo.append(fila);
      tablaRows.set(r.id, { fila, antes: a, despues: d, barra: rel, viable: cViable });
    }
    tabla.append(cuerpo);
    tablaCaja.replaceChildren(tabla);
  }

  // ---------- editores de funciones de pertenencia ----------
  const editores = new Map();   // variable -> { canvas, geo, campos }
  const FORMA_Y = { 3: [0, 1, 0], 4: [0, 1, 1, 0] };
  function pintarEditores() {
    editores.clear();
    const cajas = [];
    const todos = [...Object.entries(modelo.variables).map(([n, v]) => [n, v, false]), ["salida", modelo.salida, true]];
    for (const [nombre, v, esSalida] of todos) {
      if (!Object.keys(v.etiquetas).length) continue;
      const caja = el("div", "dedit-var");
      caja.append(el("div", "titulo-seccion", esSalida ? EDIT.salidaTitulo : `${nombreVar(nombre)} (${UNIDAD[nombre] || ""})`.replace(" ()", "")));
      const c = el("canvas", "lienzo dedit-lienzo"); const cc = el("div", "lienzo-caja"); cc.append(c); caja.append(cc);
      const campos = el("div", "dedit-campos");
      const refs = {};
      Object.entries(v.etiquetas).forEach(([et, pts], i) => {
        const f = el("div", "dedit-campo"); const t = el("span", "dedit-etq", et); t.style.setProperty("--c", COLORES[i % 5]); f.append(t);
        refs[et] = pts.map((val, k) => {
          const inp = el("input", "dedit-num"); inp.type = "number"; inp.step = String(Math.max(0.01, (v.universo[1] - v.universo[0]) / 200)); inp.value = String(val);
          inp.setAttribute("aria-label", `${et} de ${nombreVar(nombre)}, punto ${k + 1}`);
          inp.addEventListener("input", () => { if (inp.value !== "" && Number.isFinite(Number(inp.value))) { pts[k] = Number(inp.value); recalcular(); } });
          f.append(inp); return inp;
        });
        campos.append(f);
      });
      caja.append(campos);
      rejilla.append(caja); cajas.push(caja);
      const e = { canvas: c, v, nombre, refs, geo: null };
      editores.set(nombre, e);
      activarArrastre(e);
    }
    rejilla.replaceChildren(...cajas);
  }
  function dibujarEditor(e) {
    const p = preparar(e.canvas); if (!p) return;
    const { ctx, w, h } = p, v = e.v, [u0, u1] = v.universo;
    const m = { l: 34, r: 12, t: 10, b: 22 };
    const X = (x) => m.l + ((x - u0) / (u1 - u0)) * (w - m.l - m.r), Y = (y) => h - m.b - y * (h - m.t - m.b);
    e.geo = { m, w, h, X, Y, u0, u1 };
    ctx.font = "11px 'Segoe UI', system-ui, sans-serif"; ctx.fillStyle = "#98a4bb"; ctx.strokeStyle = "rgba(150,200,255,0.12)";
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (let k = 0; k <= 4; k++) { const x = u0 + ((u1 - u0) * k) / 4; ctx.fillText(coma(x, Math.abs(u1 - u0) <= 2 ? 2 : 0), X(x), h - m.b + 5); ctx.beginPath(); ctx.moveTo(X(x), m.t); ctx.lineTo(X(x), h - m.b); ctx.stroke(); }
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (const y of [0, 0.5, 1]) { ctx.fillText(coma(y, 1), m.l - 5, Y(y)); ctx.beginPath(); ctx.moveTo(m.l, Y(y)); ctx.lineTo(w - m.r, Y(y)); ctx.stroke(); }
    const original = e.nombre === "salida" ? base.salida : base.variables[e.nombre];
    Object.entries(v.etiquetas).forEach(([et, pts], i) => {
      const color = COLORES[i % 5];
      if (original && original.etiquetas[et]) {   // la curva de las reglas del planeta, tenue y discontinua
        ctx.strokeStyle = color; ctx.globalAlpha = 0.35; ctx.setLineDash([4, 4]); ctx.lineWidth = 1; trazar(ctx, original.etiquetas[et], X, Y, u0, u1); ctx.setLineDash([]); ctx.globalAlpha = 1;
      }
      ctx.strokeStyle = color; ctx.lineWidth = 2; trazar(ctx, pts, X, Y, u0, u1);
      const ys = FORMA_Y[pts.length];
      pts.forEach((x, k) => { ctx.fillStyle = color; ctx.strokeStyle = "#0b0f1a"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(X(x), Y(ys[k]), 5.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); });
    });
    // la entrada actual
    if (e.nombre !== "salida" && Number.isFinite(hoy()[e.nombre])) { const x = Math.min(u1, Math.max(u0, hoy()[e.nombre])); ctx.strokeStyle = "rgba(255,255,255,0.6)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(X(x), m.t); ctx.lineTo(X(x), h - m.b); ctx.stroke(); ctx.setLineDash([]); }
  }
  function trazar(ctx, pts, X, Y, u0, u1) {
    const ys = FORMA_Y[pts.length];
    ctx.beginPath();
    // extiende a los bordes del universo con ceros si la forma no llega
    ctx.moveTo(X(Math.min(u0, pts[0])), Y(0));
    pts.forEach((x, k) => ctx.lineTo(X(x), Y(ys[k])));
    ctx.lineTo(X(Math.max(u1, pts[pts.length - 1])), Y(0));
    ctx.stroke();
  }
  function pintarCurvas() { for (const e of editores.values()) dibujarEditor(e); }
  function activarArrastre(e) {
    let agarrado = null;
    const cercano = (ev) => {
      if (!e.geo) return null;
      const r = e.canvas.getBoundingClientRect(), px = ev.clientX - r.left, py = ev.clientY - r.top;
      let mejor = null, md = 14 * 14;
      Object.entries(e.v.etiquetas).forEach(([et, pts]) => pts.forEach((x, k) => {
        const dx = e.geo.X(x) - px, dy = e.geo.Y(FORMA_Y[pts.length][k]) - py, d = dx * dx + dy * dy;
        if (d < md) { md = d; mejor = { et, k }; }
      }));
      return mejor;
    };
    e.canvas.style.touchAction = "none";
    e.canvas.addEventListener("pointerdown", (ev) => { agarrado = cercano(ev); if (agarrado) { e.canvas.setPointerCapture(ev.pointerId); ev.preventDefault(); } });
    e.canvas.addEventListener("pointermove", (ev) => {
      if (!agarrado) { e.canvas.style.cursor = cercano(ev) ? "grab" : "default"; return; }
      const r = e.canvas.getBoundingClientRect(), g = e.geo;
      let x = g.u0 + ((ev.clientX - r.left - g.m.l) / (g.w - g.m.l - g.m.r)) * (g.u1 - g.u0);
      const pts = e.v.etiquetas[agarrado.et];
      const lo = agarrado.k > 0 ? pts[agarrado.k - 1] : g.u0, hi = agarrado.k < pts.length - 1 ? pts[agarrado.k + 1] : g.u1;
      const paso = Math.max(0.01, (g.u1 - g.u0) / 200);
      x = Math.round(Math.min(hi, Math.max(lo, x)) / paso) * paso;
      pts[agarrado.k] = Number(x.toFixed(4));
      e.refs[agarrado.et][agarrado.k].value = String(pts[agarrado.k]);
      recalcular();
    });
    const soltar = () => { agarrado = null; };
    e.canvas.addEventListener("pointerup", soltar); e.canvas.addEventListener("pointercancel", soltar);
  }

  // ---------- carga ----------
  async function cargar() {
    mensaje.textContent = "";
    const r = await pedir("GET", "/difuso/reglas");
    let datos = r.ok ? adaptarReglas(r.cuerpo) : null;
    if (r.ok && datos.estado !== "ok") { mensaje.textContent = datos.motivo; datos = null; }
    soloPrevia = !datos;
    if (!datos) datos = modeloDeFabrica();
    base = clonar(datos); modelo = clonar(datos); personalizadas = !soloPrevia && datos.personalizadas;
    firmaAplicada = JSON.stringify(cuerpoPUT(base, base));
    pintarTabla(); pintarEditores();
    recalcular();
    if (soloPrevia && !mensaje.textContent) mensaje.textContent = EDIT.sinSoporte;
    notificar();
  }

  return {
    async abrir() { if (!modelo) await cargar(); else recalcular(); },
    recargar: cargar,
    // entradas del difuso en las unidades del motor ({distancia, bateria, inclinacion, temperatura})
    entradas(e) { if (e && typeof e === "object") { entradas = { ...entradas, ...e }; if (modelo) recalcular(); } },
    redibujar() { if (modelo) recalcular(); },
    reiniciar() { modelo = null; base = null; personalizadas = false; clearTimeout(temporizador); versionAplicar++; tablaCaja.replaceChildren(); rejilla.replaceChildren(); avisos.replaceChildren(); mensaje.textContent = ""; },
    get personalizadas() { return personalizadas; },
  };
}
