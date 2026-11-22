// Defensa guiada: recorrido de 11 pasos para presentar el trabajo, ligado a los criterios de la consigna (RF/CA de
// docs/MATRIZ_REQUISITOS_PDF.md) y con cifras EN VIVO de la partida en curso. Solo lee del motor, salvo la acción
// «Demostrar» de cada paso, que el usuario pulsa a propósito (dar pasos, abrir un laboratorio, lanzar un evento).
// Todo con textContent (sin innerHTML).
import { textoBateriaDifuso, nombreVariante, plural, Vehiculo } from "/static/textos.js?v=r14";

const coma = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "-" : Number(v).toFixed(d).replace(".", ","));
const pct = (v) => (v == null ? "-" : `${coma(v * 100, 1)} %`);
async function obtener(ruta) { try { const r = await fetch(ruta); return r.ok ? await r.json() : null; } catch (e) { return null; } }
function el(tag, clase, texto) { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; }

let evaluacionRNA = null, comparacion = null;   // en caché durante la sesión (la evaluación tarda ~2 s la primera vez)

function resumenComparacion(d) {
  const por = {};
  for (const f of (d && d.filas) || []) {
    const v = (por[f.variante] = por[f.variante] || { exito: 0, n: 0, choques: 0 });
    v.n += 1; v.exito += f.estado === "EXITO" || f.exito === true ? 1 : 0; v.choques += Number(f.colisiones || 0);
  }
  return por;
}

// Cada paso: título, criterios, texto para decir, función que arma las líneas «en vivo» y la demostración opcional
function pasos() {
  return [
    { titulo: "Qué es ARES-X", criterios: ["Alcance"],
      texto: "Un prototipo académico de vehículo planetario (rover o sonda) con IA híbrida: una RNA percibe el terreno, la lógica difusa decide la velocidad, un algoritmo genético planifica el orden de visita y un supervisor de seguridad tiene la última palabra. Es una simulación con supuestos propios, no un modelo de misión real.",
      vivo: async () => { const e = await obtener("/estado"); return e && !e.sin_partida ? [`Partida en curso: ${e.planeta} · semilla ${e.semilla} · nivel ${e.nivel}`] : ["Sin partida: inicia una misión para ver las cifras en vivo."]; } },
    { titulo: "Configuración de la misión", criterios: ["RF-01", "CA-07"], resaltar: "#hud",
      texto: "Se elige planeta, tamaño de mapa, nivel y semilla. La semilla hace la partida reproducible. En los gigantes gaseosos el sistema bloquea el rover con ruedas y propone la sonda.",
      vivo: async () => { const e = await obtener("/estado"); return e && !e.sin_partida ? [`Planeta ${e.planeta} · vehículo: ${Vehiculo(e.modo_planeta)}`, `Batería: ${coma(e.bateria_pct ?? e.bateria, 1)} % de la capacidad · bases de recarga: ${(e.estaciones || []).length} · pilas en el mapa: ${(e.pilas || []).length}`, `Sitios científicos: ${e.sitios_visitados}/${e.sitios_totales}`] : []; } },
    { titulo: "El ciclo observar → decidir → actuar", criterios: ["RF-03", "CA-01"], resaltar: "#barra-mision",
      texto: "En cada paso el vehículo lee sensores ruidosos, la RNA clasifica la celda de enfrente, el difuso fija la velocidad, el AG mantiene el plan y el supervisor aprueba o veta. El narrador lo explica en una frase.",
      vivo: async () => { const d = await obtener("/ia/paso"); return d && d.hay_paso ? [d.narracion] : ["Pulsa «Demostrar» para dar tres pasos."]; },
      demo: { rotulo: "Dar 3 pasos", accion: async (a) => { for (let i = 0; i < 3; i++) await a.paso(); } } },
    { titulo: "Percepción con la RNA", criterios: ["RF-04", "CA-06"], pestana: "rna", resaltar: "#panel-ia",
      texto: "Un perceptrón multicapa (32 y 16 neuronas) clasifica la celda en libre, obstáculo o barranco a partir de proximidad, desnivel, contraste y vibración. Se entrena con partición por mapas, sin fuga entre entrenamiento y prueba. En el panel se ve cómo se propaga la activación.",
      vivo: async () => {
        const d = await obtener("/ia/paso");
        if (!evaluacionRNA) evaluacionRNA = await obtener("/rna/evaluacion");
        const l = [];
        if (d && d.rna) { const p = d.rna.probabilidades_usadas || d.rna.probabilidades; l.push(`Este paso: libre ${pct(p.libre)} · obstáculo ${pct(p["obstáculo"])} · barranco ${pct(p.barranco)}`); }
        if (evaluacionRNA) l.push(`En mapas de prueba: macro-F1 ${coma(evaluacionRNA.macro_f1, 3)} · recall de barrancos ${coma(evaluacionRNA.recall_barranco, 3)} · error de calibración ${coma(evaluacionRNA.error_calibracion, 3)}`);
        return l;
      },
      demo: { rotulo: "Abrir el laboratorio RNA", accion: (a) => a.abrirLab("rna") } },
    { titulo: "Velocidad con lógica difusa", criterios: ["RF-05", "RF-06", "CA-05"], pestana: "difuso", resaltar: "#panel-ia",
      texto: "Un controlador Mamdani con cuatro entradas (distancia al riesgo, batería, inclinación y temperatura), al menos tres conjuntos por variable y más de ocho reglas. La salida se obtiene por centroide. En el laboratorio, el barrido de 10 a 1 m muestra cómo frena al acercarse.",
      vivo: async () => { const d = await obtener("/ia/paso"); if (!d || !d.difuso) return []; const e = d.difuso.entradas;
        return [`Entradas del paso: ${coma(e.distancia, 1)} m · batería ${textoBateriaDifuso(e)} · inclinación ${coma(e.inclinacion, 1)}° · ${coma(e.temperatura, 0)} °C`,
          `Velocidad: ${coma(d.difuso.salida.velocidad, 3)} con ${(d.difuso.reglas_activadas || []).map((r) => r.id).join(", ") || "ninguna regla"}`]; },
      demo: { rotulo: "Abrir el laboratorio difuso", accion: (a) => a.abrirLab("difuso") } },
    { titulo: "Planificación con el algoritmo genético", criterios: ["RF-07", "RF-11", "CA-04"], pestana: "ag", resaltar: "#panel-ia",
      texto: "El AG ordena los sitios científicos: selección por torneo, cruce, mutación y elitismo, con un fitness que pesa ciencia, distancia, energía, riesgo y tiempo, y una restricción dura de batería. Se vuelve a ejecutar cuando la misión replanifica.",
      vivo: async () => { const d = await obtener("/ia/paso"); if (!d || !d.ag) return []; const g = d.ag.generaciones || [];
        return [`Plan en juego: faltan ${plural(d.ag.celdas_restantes, "celda", "celdas")} · sitios ${d.ag.visitados}/${d.ag.sitios} · ${plural(d.ag.replanes, "replanteo", "replanteos")}`,
          g.length ? `Última ejecución: ${plural(g.length, "generación", "generaciones")}, mejor fitness ${coma(g[g.length - 1].mejor, 3)}` : "Sin ejecución del AG todavía"]; },
      demo: { rotulo: "Abrir el laboratorio genético", accion: (a) => a.abrirLab("ag") } },
    { titulo: "Supervisor de seguridad", criterios: ["CA-02"], resaltar: "#decision",
      texto: "El supervisor tiene prioridad sobre las recomendaciones: veta si el telémetro mide un desnivel de barranco, si la RNA ve un peligro o si la ruta pisa una celda marcada, y entonces se replanifica. Con sensores ruidosos fusiona varias lecturas antes de marcar una celda para siempre.",
      vivo: async () => { const e = await obtener("/estado"); return e && !e.sin_partida ? [`Vetos: ${e.vetos} · replanteos: ${e.replanes} · choques: ${e.colisiones}`] : []; } },
    { titulo: "Un imprevisto: meteorito", criterios: ["CA-02", "RF-13"],
      texto: "Al lanzar un meteorito, la zona de impacto queda como riesgo en el mapa estimado; si cae sobre la ruta, el supervisor veta y el AG recalcula el orden de visita. La batería pierde un 5 %.",
      vivo: async () => { const e = await obtener("/estado"); return e && !e.sin_partida ? [`Avisos recientes: ${(e.avisos || []).slice(-2).join(" · ") || "ninguno"}`] : []; },
      demo: { rotulo: "Lanzar un meteorito y dar un paso", accion: async (a) => { await a.evento("meteorito"); await a.paso(); } } },
    { titulo: "Experimento: ¿aporta cada técnica?", criterios: ["RF-14", "RF-15", "CA-08"],
      texto: "Se compara el híbrido con variantes que apagan una técnica, con las mismas 20 semillas. En el escenario exigente (sensores ruidosos) el resultado se publica tal como sale, incluido cuando una técnica no mejora el éxito.",
      vivo: async () => {
        if (!comparacion) comparacion = resumenComparacion(await obtener("/comparacion?escenario=exigente"));
        return ["hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino"].filter((k) => comparacion[k]).map((k) => `${nombreVariante(k)}: ${comparacion[k].exito}/${comparacion[k].n} ${comparacion[k].exito === 1 ? "éxito" : "éxitos"}, ${plural(comparacion[k].choques, "choque", "choques")}`);
      },
      demo: { rotulo: "Abrir la comparación de políticas", accion: (a) => a.abrirLab("politicas") } },
    { titulo: "Trazabilidad", criterios: ["RF-08", "RF-12"],
      texto: "Cada paso queda en la bitácora con señales, probabilidades, grados difusos, velocidad, fitness, ruta, acción y motivo. Se exporta a CSV y el reporte de la misión lo resume con gráficos y la narración paso a paso.",
      vivo: async () => { const h = await obtener("/historial"); return h ? [`Acciones registradas: ${h.total}`] : []; },
      demo: { rotulo: "Abrir el reporte de la misión", accion: (a) => a.reporte() } },
    { titulo: "Limitaciones y cierre", criterios: ["Honestidad"],
      texto: "Con sensores muy ruidosos la RNA calibrada casi no puede distinguir un barranco en una sola observación, así que influye poco en ese escenario; las decisiones las sostienen la fusión de lecturas y el supervisor. Queda un caso conocido de batería con meteoritos en nivel 3. Todo es simulación con supuestos propios.",
      vivo: async () => [] },
  ];
}

// acciones: { paso(), evento(nombre), abrirLab(seccion), abrirPestana(id), reporte() }
export function crearDefensa(acciones) {
  const lista = pasos();
  const raiz = el("aside", "def-capa oculto"); raiz.setAttribute("aria-label", "Defensa guiada"); raiz.setAttribute("role", "dialog");
  const cab = el("div", "def-cabecera");
  const contador = el("span", "def-contador");
  const salir = el("button", "def-salir", "✕"); salir.type = "button"; salir.title = "Salir de la defensa";
  cab.append(el("span", "def-marca", "🎓 Defensa guiada"), contador, salir);
  const titulo = el("h2", "def-titulo");
  const criterios = el("div", "def-criterios");
  const texto = el("p", "def-texto");
  const vivoT = el("div", "def-vivo-titulo", "En vivo");
  const vivo = el("ul", "def-vivo");
  const pie = el("div", "def-pie");
  const ant = el("button", "def-boton", "◀ Anterior"); ant.type = "button";
  const demo = el("button", "def-boton def-demo"); demo.type = "button";
  const sig = el("button", "def-boton def-siguiente", "Siguiente ▶"); sig.type = "button";
  pie.append(ant, demo, sig);
  const barra = el("div", "def-progreso"); const relleno = el("div", "def-relleno"); barra.append(relleno);
  raiz.append(cab, barra, titulo, criterios, texto, vivoT, vivo, pie);
  document.body.append(raiz);

  let i = 0, resaltado = null, generacion = 0;
  function quitarResaltado() { if (resaltado) resaltado.classList.remove("def-resaltado"); resaltado = null; }
  async function refrescarVivo() {
    const g = ++generacion;
    vivo.replaceChildren(el("li", "def-cargando", "cargando…"));
    let lineas = [];
    try { lineas = (await lista[i].vivo()) || []; } catch (e) { lineas = ["sin datos"]; }
    if (g !== generacion) return;   // el usuario ya cambió de paso
    vivo.replaceChildren(...(lineas.length ? lineas : ["—"]).map((t) => el("li", null, t)));
  }
  function mostrar(n) {
    i = Math.max(0, Math.min(lista.length - 1, n));
    const p = lista[i];
    contador.textContent = `${i + 1}/${lista.length}`;
    relleno.style.width = `${((i + 1) / lista.length) * 100}%`;
    titulo.textContent = p.titulo;
    criterios.replaceChildren(...p.criterios.map((c) => el("span", "def-criterio", c)));
    criterios.title = "Criterios de la consigna del trabajo: RF = requisito funcional, CA = criterio de aceptación";
    if (p.criterios.some((c) => /^(RF|CA)-/.test(c))) criterios.append(el("span", "def-criterios-nota", "Criterios de la consigna (RF: requisito funcional · CA: criterio de aceptación)"));
    texto.textContent = p.texto;
    ant.disabled = i === 0;
    sig.textContent = i === lista.length - 1 ? "Terminar ✓" : "Siguiente ▶";
    demo.hidden = !p.demo; if (p.demo) demo.textContent = `▶ ${p.demo.rotulo}`;
    quitarResaltado();
    if (p.resaltar) { resaltado = document.querySelector(p.resaltar); if (resaltado) resaltado.classList.add("def-resaltado"); }
    if (p.pestana) { try { acciones.abrirPestana(p.pestana); } catch (e) { /* sin panel */ } }
    refrescarVivo();
  }
  function cerrar() { quitarResaltado(); raiz.classList.add("oculto"); document.body.classList.remove("defensa-activa"); }
  ant.addEventListener("click", () => mostrar(i - 1));
  sig.addEventListener("click", () => (i === lista.length - 1 ? cerrar() : mostrar(i + 1)));
  salir.addEventListener("click", cerrar);
  demo.addEventListener("click", async () => {
    const p = lista[i]; if (!p.demo) return;
    demo.disabled = true;
    try { await p.demo.accion(acciones); } catch (e) { console.warn("defensa: la demostración falló", e); }
    finally { demo.disabled = false; refrescarVivo(); }
  });
  return {
    abrir() { raiz.classList.remove("oculto"); document.body.classList.add("defensa-activa"); mostrar(i); },
    cerrar,
    alPaso() { if (!raiz.classList.contains("oculto")) refrescarVivo(); },   // tras cada paso, las cifras se actualizan
    get abierta() { return !raiz.classList.contains("oculto"); },
  };
}
