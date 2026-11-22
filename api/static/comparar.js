// Comparar dos políticas lado a lado con la misma semilla: dos minimapas 2D sincronizados paso a paso (canvas ligero),
// controles comunes y, al final, una tabla con el ganador por métrica. Las dos partidas viven aparte en el servidor
// (rutas /comparar): no tocan la partida que se está jugando.
import { porcentaje } from "./formato.js?v=r14";
import { el, boton, campo, selector, crearCapa } from "./vx_ui.js?v=r14";
import {
  opcionesPoliticas, nombrePolitica, ayudaPolitica, estadoLado, fichaEn, rutaHasta, pasosDisponibles, ambosTerminados,
  textoDecision, textoDivergencia, TEXTO_SIN_DIVERGENCIA_AUN, TEXTO_SIN_DIVERGENCIA_FIN, filasTabla, veredicto, NOTA_TABLA, hayCiencia, cienciaEn,
  validarFormulario, VELOCIDADES, tamanoCelda,
} from "./comparar_datos.js?v=r14";
import { nombreAccion, nombresMotivos, plural, Vehiculo } from "./textos.js?v=r14";
import { NIVELES } from "./records_datos.js?v=r14";

const COLOR = { a: "#5fd3ff", b: "#ffb454" };
const TERRENO = { 0: "#1b2740", 1: "#58617a", 2: "#2a0f17" };
const CHUNK = 20;

// valores(): { planeta, vehiculo, tamano, nivel, semilla } con lo que hay en el asistente; planetas(): [[valor, texto], ...]
export function crearComparar({ valores = () => ({}), planetas = () => [] } = {}) {
  const capa = crearCapa({ clase: "vx-comparar", kicker: "Comparar políticas", titulo: "Dos políticas, el mismo mapa", etiqueta: "Comparar dos políticas", alCerrar: () => { pausar(); descartar(); } });
  let datos = null;            // respuesta de /comparar con los pasos acumulados
  let k = 0;                   // paso que se está viendo (0 = salida)
  let reproduciendo = false, ficha = 0, pidiendo = null, avisoDivergencia = false;
  const celdas = { a: 8, b: 8 };

  // ---------- formulario ----------
  const cPlaneta = selector([["Marte", "Marte"]]);
  const cVehiculo = selector([["rover", "Rover"], ["sonda", "Sonda"]]);
  const cTamano = selector([["pequeno", "Pequeño (20×30)"], ["mediano", "Mediano (30×45)"], ["grande", "Grande (40×60)"]], "pequeno");
  const cNivel = selector(NIVELES.map((n, i) => [i + 1, n]), 3);
  const cSemilla = el("input", "vx-control"); cSemilla.type = "number"; cSemilla.min = "0"; cSemilla.placeholder = "aleatoria";
  const cA = selector(opcionesPoliticas(), "hibrido"), cB = selector(opcionesPoliticas(), "sin_rna");
  const ayudaA = el("div", "vx-ayuda-politica"), ayudaB = el("div", "vx-ayuda-politica");
  const sincAyuda = () => { ayudaA.textContent = ayudaPolitica(cA.value); ayudaB.textContent = ayudaPolitica(cB.value); };
  cA.addEventListener("change", sincAyuda); cB.addEventListener("change", sincAyuda);
  const aleatoria = boton("Aleatoria", "secundario", () => { cSemilla.value = String(1 + (crypto.getRandomValues(new Uint32Array(1))[0] % 999999)); });
  const comparar = boton("Comparar", "primario", () => crear());
  const form = el("div", "vx-form");
  const filaMapa = el("div", "vx-barra"), filaPoliticas = el("div", "vx-barra");
  const colA = el("div", "vx-politica vx-a"); colA.append(campo("Política A", cA), ayudaA);
  const colB = el("div", "vx-politica vx-b"); colB.append(campo("Política B", cB), ayudaB);
  filaMapa.append(campo("Planeta", cPlaneta), campo("Vehículo", cVehiculo), campo("Tamaño", cTamano), campo("Nivel", cNivel), campo("Semilla", cSemilla), aleatoria);
  filaPoliticas.append(colA, colB, comparar);
  form.append(filaMapa, filaPoliticas);
  const estadoForm = el("div", "ayuda vx-estado-form"); estadoForm.setAttribute("role", "status"); estadoForm.setAttribute("aria-live", "polite");

  // ---------- paneles de los dos lados ----------
  const lados = {};
  const zonaLados = el("div", "vx-lados oculto");
  for (const id of ["a", "b"]) {
    const caja = el("section", `vx-lado vx-${id}`);
    const tit = el("h3", "vx-lado-titulo");
    const canvas = el("canvas", "vx-mini"); canvas.setAttribute("role", "img");
    const lista = el("dl", "vx-stats");
    const filasStats = {};
    for (const [clave, rotulo] of [["paso", "Paso"], ["bateria", "Batería"], ["sitios", "Sitios visitados"], ["ciencia", "Ciencia recogida"], ["vetos", "Vetos"], ["choques", "Choques"], ["estado", "Estado"]]) {
      const dt = el("dt", "", rotulo), dd = el("dd", "", "—");
      if (clave === "ciencia") { dt.classList.add("oculto"); dd.classList.add("oculto"); filasStats.cienciaDt = dt; }   // solo se muestra si el motor la manda
      lista.append(dt, dd); filasStats[clave] = dd;
    }
    const decision = el("div", "vx-decision");
    caja.append(tit, canvas, lista, decision);
    zonaLados.append(caja);
    lados[id] = { caja, tit, canvas, ctx: canvas.getContext("2d"), filasStats, decision };
  }
  const leyendaMapa = el("div", "ayuda vx-leyenda");
  leyendaMapa.textContent = "Mapa: celdas oscuras = terreno libre, grises = obstáculos, casi negras = barrancos. Rombo = sitio científico (verde si ya se visitó), cuadro verde = refugio, línea = ruta recorrida, aro = posición actual, X roja = primer paso en que las dos se separan.";

  // ---------- controles comunes ----------
  const bIni = boton("⏮", "secundario", () => { pausar(); ir(0); });
  bIni.title = "Volver a la salida"; bIni.setAttribute("aria-label", "Volver a la salida");
  const bAtras = boton("◀ Paso", "secundario", () => { pausar(); ir(k - 1); });
  bAtras.title = "Un paso atrás";
  const bPlay = boton("▶ Reproducir", "primario", () => alternar());
  const bAdelante = boton("Paso ▶", "secundario", async () => { pausar(); await asegurar(k + 1); ir(k + 1); });
  bAdelante.title = "Un paso adelante";
  const bFin = boton("Ir al final ⏭", "secundario", async () => { pausar(); await alFinal(); });
  const cVel = selector(VELOCIDADES, "350"); cVel.setAttribute("aria-label", "Velocidad");
  const barraPasos = el("input", "vx-barra-pasos"); barraPasos.type = "range"; barraPasos.min = "0"; barraPasos.max = "0"; barraPasos.value = "0"; barraPasos.setAttribute("aria-label", "Paso mostrado");
  barraPasos.addEventListener("input", () => { pausar(); ir(Number(barraPasos.value)); });
  const cPausarDiv = el("input"); cPausarDiv.type = "checkbox"; cPausarDiv.checked = true;
  const etiquetaPausa = el("label", "vx-check"); etiquetaPausa.append(cPausarDiv, document.createTextNode(" Pausar cuando se separen"));
  const textoPaso = el("span", "vx-texto-paso", "Paso 0");
  const controles = el("div", "vx-controles oculto");
  controles.append(bIni, bAtras, bPlay, bAdelante, bFin, campo("Velocidad", cVel, "vx-campo-corto"), textoPaso, barraPasos, etiquetaPausa);

  const cajaDiv = el("div", "vx-divergencia oculto"); cajaDiv.setAttribute("role", "status"); cajaDiv.setAttribute("aria-live", "polite");
  const cajaTabla = el("div", "vx-resultado oculto");
  const nota = el("div", "ayuda vx-nota-servidor", "Las dos partidas se juegan aparte en el servidor, con la misma semilla; no afectan a la partida que tengas abierta.");
  capa.cuerpo.append(form, estadoForm, zonaLados, controles, cajaDiv, cajaTabla, leyendaMapa, nota);

  // ---------- comunicación ----------
  async function pedir(metodo, ruta, cuerpo) {
    let r;
    try {
      r = await fetch(ruta, { method: metodo, headers: { "Content-Type": "application/json" }, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    } catch (e) { return { error: "No hay conexión con el motor. Revisa que la API esté levantada." }; }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return { error: j.motivo || `El motor respondió con un error (${r.status}).` };
    return j;
  }
  function mezclar(resp) {
    resp.lados.forEach((l, i) => {
      const d = datos.lados[i];
      d.pasos.push(...l.pasos); d.terminado = l.terminado; d.estado = l.estado;
    });
    datos.divergencia = resp.divergencia; datos.tabla = resp.tabla;
  }
  function traer() {
    if (pidiendo) return pidiendo;
    if (!datos || ambosTerminados(datos.lados)) return Promise.resolve(true);
    const id = datos.id;
    pidiendo = (async () => {
      const r = await pedir("POST", `/comparar/${id}/avanzar`, { pasos: CHUNK });
      if (!datos || datos.id !== id) return false;
      if (r.error) { estadoForm.textContent = r.error; pausar(); return false; }
      mezclar(r);
      return true;
    })().finally(() => { pidiendo = null; });
    return pidiendo;
  }
  async function asegurar(n) {
    while (datos && pasosDisponibles(datos.lados) < n && !ambosTerminados(datos.lados)) {
      if (!(await traer())) return false;
    }
    return true;
  }
  async function alFinal() {
    if (!datos) return;
    estadoForm.textContent = "Calculando hasta el final…";
    while (!ambosTerminados(datos.lados)) { if (!(await traer())) return; }
    estadoForm.textContent = "";
    ir(pasosDisponibles(datos.lados));
  }

  // ---------- reproducción ----------
  function pausar() { reproduciendo = false; ficha += 1; pintarBotones(); }
  function alternar() {
    if (reproduciendo) { pausar(); return; }
    if (!datos) return;
    if (k >= pasosDisponibles(datos.lados) && ambosTerminados(datos.lados)) ir(0);   // al terminar, «Reproducir» empieza de nuevo
    reproduciendo = true; avisoDivergencia = false; ficha += 1; pintarBotones();
    bucle(ficha);
  }
  async function bucle(mia) {
    while (reproduciendo && ficha === mia) {
      if (!(await asegurar(k + 1))) break;
      if (ficha !== mia) return;
      if (k + 1 > pasosDisponibles(datos.lados)) { reproduciendo = false; break; }
      const antes = k;
      ir(k + 1);
      if (!ambosTerminados(datos.lados) && pasosDisponibles(datos.lados) - k < 8) traer();   // pide el siguiente trozo mientras se mira este
      const dv = datos.divergencia;
      if (cPausarDiv.checked && dv && antes < dv.n && k >= dv.n && !avisoDivergencia) { avisoDivergencia = true; reproduciendo = false; break; }
      await new Promise((r) => setTimeout(r, Number(cVel.value)));
    }
    if (ficha === mia) { reproduciendo = false; pintarBotones(); }
  }
  function pintarBotones() {
    bPlay.textContent = reproduciendo ? "❚❚ Pausa" : "▶ Reproducir";
    const disp = datos ? pasosDisponibles(datos.lados) : 0;
    bAtras.disabled = k <= 0; bIni.disabled = k <= 0;
    bAdelante.disabled = !!datos && ambosTerminados(datos.lados) && k >= disp;
  }

  // ---------- dibujo ----------
  function prepararCanvas(id) {
    const L = lados[id], m = datos.mapa, c = celdas[id];
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    L.canvas.width = m.columnas * c * dpr; L.canvas.height = m.filas * c * dpr;
    L.canvas.style.width = `${m.columnas * c}px`; L.canvas.style.height = `${m.filas * c}px`;
    L.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function dibujar(id) {
    const i = id === "a" ? 0 : 1, L = lados[id], m = datos.mapa, c = celdas[id], ctx = L.ctx, lado = datos.lados[i];
    const f = fichaEn(lado, k);
    ctx.clearRect(0, 0, m.columnas * c, m.filas * c);
    for (let r = 0; r < m.filas; r++) for (let q = 0; q < m.columnas; q++) {
      ctx.fillStyle = TERRENO[m.tipo[r][q]] || TERRENO[0];
      ctx.fillRect(q * c, r * c, c, c);
    }
    const visitados = new Set(((f && f.visitados) || []).map((p) => p.join(",")));
    ctx.strokeStyle = "rgba(110,231,168,0.9)"; ctx.lineWidth = Math.max(1, c / 5);
    ctx.strokeRect(m.refugio[1] * c + 1, m.refugio[0] * c + 1, c - 2, c - 2);
    ctx.fillStyle = "rgba(110,231,168,0.35)"; ctx.fillRect(m.refugio[1] * c + 1, m.refugio[0] * c + 1, c - 2, c - 2);
    for (const e of m.estaciones || []) { ctx.fillStyle = "#68d9ca"; ctx.fillRect(e[1] * c + c * 0.3, e[0] * c + c * 0.3, c * 0.4, c * 0.4); }
    for (const s of m.sitios) {
      const x = s.pos[1] * c + c / 2, y = s.pos[0] * c + c / 2, r = Math.max(2.5, c * 0.45);
      ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath();
      ctx.fillStyle = visitados.has(s.pos.join(",")) ? "#6ee7a8" : "#ffd166"; ctx.fill();
    }
    const ruta = rutaHasta(m.inicio, lado, k);
    ctx.beginPath(); ctx.lineWidth = Math.max(1.5, c / 4); ctx.strokeStyle = COLOR[id]; ctx.lineJoin = "round";
    ruta.forEach((p, n) => { const x = p[1] * c + c / 2, y = p[0] * c + c / 2; if (n === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
    ctx.stroke();
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(m.inicio[1] * c + c / 2, m.inicio[0] * c + c / 2, Math.max(1.5, c / 4), 0, 7); ctx.fill();
    const dv = datos.divergencia;
    if (dv && k >= dv.n) {
      const p = lado.pasos[Math.min(dv.n, lado.pasos.length) - 1];
      if (p) {
        const x = p.posicion[1] * c + c / 2, y = p.posicion[0] * c + c / 2, r = Math.max(4, c * 0.75);
        ctx.strokeStyle = "#ff5d6c"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(x - r, y - r); ctx.lineTo(x + r, y + r); ctx.moveTo(x + r, y - r); ctx.lineTo(x - r, y + r); ctx.stroke();
      }
    }
    const pos = f ? f.posicion : m.inicio;
    ctx.beginPath(); ctx.arc(pos[1] * c + c / 2, pos[0] * c + c / 2, Math.max(3, c * 0.6), 0, 7);
    ctx.fillStyle = COLOR[id]; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#fff"; ctx.stroke();
    L.canvas.setAttribute("aria-label", `Minimapa de ${nombrePolitica(lado.politica)}: paso ${k}, fila ${pos[0]}, columna ${pos[1]}`);
  }

  function pintarStats(id) {
    const i = id === "a" ? 0 : 1, L = lados[id], lado = datos.lados[i], f = fichaEn(lado, k);
    const total = datos.inicio[i].sitios_totales;
    L.filasStats.paso.textContent = String(f ? Math.min(k, lado.pasos.length) : 0);
    L.filasStats.bateria.textContent = porcentaje(f ? f.bateria_pct : datos.inicio[i].bateria_pct);
    L.filasStats.sitios.textContent = `${f ? f.sitios_visitados : 0} de ${total}`;
    const conCiencia = hayCiencia(datos.lados);
    L.filasStats.ciencia.classList.toggle("oculto", !conCiencia); L.filasStats.cienciaDt.classList.toggle("oculto", !conCiencia);
    if (conCiencia) { const ci = cienciaEn(lado, k); L.filasStats.ciencia.textContent = ci ? ci.texto : (f ? "—" : "0 %"); }
    L.filasStats.vetos.textContent = String(f ? f.vetos : 0);
    L.filasStats.choques.textContent = String(f ? f.colisiones : 0);
    L.filasStats.estado.textContent = f ? (lado.terminado && k >= lado.pasos.length ? `${estadoLado(lado.estado)} (terminó)` : estadoLado(f.estado)) : "En la salida";
    L.decision.textContent = f ? textoDecision(nombrePolitica(lado.politica), { posicion: f.posicion, accion: f.accion, motivos: f.motivos }) : "Todavía no se movió.";
  }

  function pintarDivergencia() {
    const nombres = datos.lados.map((l) => nombrePolitica(l.politica));
    const t = textoDivergencia(datos.divergencia, nombres[0], nombres[1]);
    cajaDiv.replaceChildren();
    cajaDiv.classList.remove("oculto");
    if (!t) {
      cajaDiv.classList.remove("vx-hay");
      cajaDiv.append(el("div", "", ambosTerminados(datos.lados) && k >= pasosDisponibles(datos.lados) ? TEXTO_SIN_DIVERGENCIA_FIN : TEXTO_SIN_DIVERGENCIA_AUN));
      return;
    }
    const alcanzada = k >= datos.divergencia.n;
    cajaDiv.classList.toggle("vx-hay", alcanzada);
    cajaDiv.append(el("strong", "", `${alcanzada ? "✖ " : ""}${t.titulo}`), el("div", "", t.resumen));
    if (alcanzada) cajaDiv.append(el("div", "vx-dec vx-a", t.a), el("div", "vx-dec vx-b", t.b));
    else cajaDiv.append(boton(`Ir al paso ${datos.divergencia.n}`, "secundario", () => { pausar(); ir(datos.divergencia.n); }));
  }

  function pintarTabla() {
    cajaTabla.replaceChildren();
    const fin = ambosTerminados(datos.lados) && k >= pasosDisponibles(datos.lados);
    cajaTabla.classList.toggle("oculto", !fin || !datos.tabla);
    if (!fin || !datos.tabla) return;
    const nA = nombrePolitica(datos.lados[0].politica), nB = nombrePolitica(datos.lados[1].politica);
    const tabla = el("table", "lab-tabla vx-tabla-res");
    const cab = el("tr"); cab.append(el("th", "", "Métrica"), el("th", "vx-a", `A · ${nA}`), el("th", "vx-b", `B · ${nB}`), el("th", "", "Mejor"));
    const th = el("thead"); th.append(cab);
    const cuerpo = el("tbody");
    for (const f of filasTabla(datos.tabla, nA, nB, datos.lados)) {
      const tr = el("tr");
      const ca = el("td", f.ganador === "a" ? "vx-gana" : "", f.a), cb = el("td", f.ganador === "b" ? "vx-gana" : "", f.b);
      tr.append(el("td", "", f.rotulo), ca, cb, el("td", "", f.texto));
      cuerpo.append(tr);
    }
    tabla.append(th, cuerpo);
    cajaTabla.append(el("div", "vx-veredicto", veredicto(datos.tabla, nA, nB)), tabla, el("div", "ayuda", NOTA_TABLA));
  }

  function ir(n) {
    if (!datos) return;
    k = Math.max(0, Math.min(n, pasosDisponibles(datos.lados)));
    const disp = pasosDisponibles(datos.lados);
    barraPasos.max = String(disp); barraPasos.value = String(k);
    textoPaso.textContent = `Paso ${k}${ambosTerminados(datos.lados) ? ` de ${disp}` : ""}`;
    for (const id of ["a", "b"]) { dibujar(id); pintarStats(id); }
    pintarDivergencia(); pintarTabla(); pintarBotones();
  }

  function medir() {
    if (!datos) return;
    const ancho = Math.max(200, (capa.cuerpo.clientWidth - 24) / 2 - 8), alto = Math.max(180, window.innerHeight * 0.42);
    const c = tamanoCelda(datos.mapa.filas, datos.mapa.columnas, ancho, alto);
    for (const id of ["a", "b"]) { celdas[id] = c; prepararCanvas(id); }
  }
  window.addEventListener("resize", () => { if (capa.visible && datos) { medir(); ir(k); } });

  // ---------- crear la comparación ----------
  async function descartar() {
    if (datos) { const id = datos.id; datos = null; fetch(`/comparar/${id}`, { method: "DELETE" }).catch(() => {}); }
  }
  async function crear() {
    const cuerpo = { semilla: cSemilla.value.trim() === "" ? null : cSemilla.value.trim(), nivel: Number(cNivel.value), tamano: cTamano.value, planeta: cPlaneta.value, modo: cVehiculo.value, politica_a: cA.value, politica_b: cB.value };
    const mal = validarFormulario({ semilla: cuerpo.semilla, politicaA: cA.value, politicaB: cB.value });
    if (mal) { estadoForm.textContent = mal; return; }
    pausar(); await descartar();
    comparar.disabled = true; estadoForm.textContent = "Preparando las dos partidas…";
    const r = await pedir("POST", "/comparar", cuerpo);
    comparar.disabled = false;
    if (r.error) { estadoForm.textContent = r.error; zonaLados.classList.add("oculto"); controles.classList.add("oculto"); cajaDiv.classList.add("oculto"); cajaTabla.classList.add("oculto"); return; }
    datos = { id: r.id, mapa: r.mapa, inicio: r.inicio, lados: r.lados.map((l) => ({ politica: l.politica, pasos: [], terminado: false, estado: "EXPLORACION" })), divergencia: null, tabla: null, semilla: r.semilla };
    cSemilla.value = String(r.semilla);   // la semilla elegida por el servidor queda a la vista para repetirla
    estadoForm.textContent = r.mapas_iguales
      ? `Mismo mapa en las dos: semilla ${r.semilla}, nivel ${NIVELES[r.nivel - 1]}, ${r.planeta} (${Vehiculo(r.vehiculo)}). Pulsa Reproducir.`
      : "Aviso: las dos partidas no salieron con el mismo mapa; no se puede comparar.";
    k = 0; avisoDivergencia = false;
    const nombres = r.lados.map((l) => nombrePolitica(l.politica));
    lados.a.tit.textContent = `A · ${nombres[0]}`; lados.b.tit.textContent = `B · ${nombres[1]}`;
    zonaLados.classList.remove("oculto"); controles.classList.remove("oculto");
    medir(); ir(0);
    traer();   // primer trozo por adelantado
  }

  function llenarPlanetas() {
    const lista = planetas();
    if (lista.length) { cPlaneta.replaceChildren(...lista.map(([v, t]) => { const o = el("option", "", t); o.value = v; return o; })); }
  }

  return {
    abrir({ politicaA = null, politicaB = null } = {}) {
      llenarPlanetas();
      const v = valores();
      if (v.planeta) cPlaneta.value = v.planeta;
      if (v.vehiculo) cVehiculo.value = v.vehiculo;
      if (v.tamano) cTamano.value = v.tamano;
      if (v.nivel) cNivel.value = String(v.nivel);
      if (v.semilla) cSemilla.value = String(v.semilla);
      if (politicaA) cA.value = politicaA;
      if (politicaB) cB.value = politicaB;
      sincAyuda();
      capa.abrir();
    },
    cerrar() { capa.cerrar(); },
    get visible() { return capa.visible; },
  };
}
