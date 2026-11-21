// Pantalla final: puntaje, estrellas y logros. Datos y funciones puras (sin DOM ni THREE). Se prueban con node.
import { PLANETAS_VIAJE, AVISO_TERRENO } from "./viaje_datos.js?v=r14";

export { PLANETAS_VIAJE, AVISO_TERRENO };
export const CLAVE_PREF = "ares.final";          // localStorage: casilla «Mostrar la pantalla final» (activa por defecto)
export const CLAVE_LOGROS = "ares.logros";       // localStorage: logros desbloqueados
export const CIERRE_INACTIVIDAD_S = 120;         // sin interacción, se cierra sola y deja la meta
export const DURACION_CUENTA_MS = 900;
export const DURACION_CONFETI_MS = 2600;
export const MAX_MOMENTOS = 3;
export const ANCHO_MOMENTO = 960;
export const TECLAS_QUE_PASAN = ["Tab", "Enter"];   // con la pantalla abierta, el resto de las teclas no llega a la partida (el espacio dispara)

// Fórmula del puntaje de juego: ciencia(0 a 1)×1000 + barrancos evitados×50 + batería(%)×5 − violaciones×500, mínimo 0.
export const PESO_CIENCIA = 1000;
export const PESO_BARRANCOS_EVITADOS = 50;
export const PESO_BATERIA = 5;
export const PENALIZACION_VIOLACION = 500;
// Estrellas: 1 si hay éxito sin violaciones; 2 si además ciencia ≥ 60 %; 3 si ciencia ≥ 85 % y batería ≥ 20 %.
export const UMBRAL_2_ESTRELLAS = 0.6;
export const UMBRAL_3_CIENCIA = 0.85;
export const UMBRAL_3_BATERIA = 20;
export const BATERIA_AL_LIMITE = 15;      // «Al límite»: éxito con menos de este % de batería
export const VETOS_INGENIERO = 5;         // «Ingeniero cauto»: vetos mínimos sin fracasar
export const CUERPOS_TROTAMUNDOS = 5;

export const ROTULO_PUNTAJE = "Puntaje de juego, no es un criterio de evaluación.";
export const ROTULO_PUNTAJE_HUD = "Puntaje simple";   // el del HUD: otra cuenta, distinta de la de la pantalla final
export const NOTA_PUNTAJE = "No es el puntaje simple del HUD, ni el fitness del algoritmo genético, ni una métrica de la rúbrica.";
export const ROTULO_FICCION = "Ficción, no evidencia";
export const NOTA_SENAL = "La señal anómala del motor es una lectura sin explicación: no afirma vida.";
export const NOTA_SIN_EVENTO = "Requiere un evento que el rover no tiene.";
export const NOTA_DISTANCIA = "Distancia en celdas del mapa (sin escala en metros).";
export const NOTA_BARRANCOS = "Barrancos evitados: pasos de la bitácora en que el veto frenó un barranco.";
export const NOTA_VIOLACIONES = "Violaciones: colisiones más pasos sobre la tolerancia térmica.";

const num = (v) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));

// Resultado con los nombres del juego. Dato ausente = null (se muestra «—»), nunca un cero inventado.
export function normalizarResultado(estado) {
  const e = estado && typeof estado === "object" ? estado : {};
  const vis = num(e.sitios_visitados), tot = num(e.sitios_totales);
  const col = num(e.colisiones), sobre = num(e.pasos_sobre_tolerancia);
  const avisos = Array.isArray(e.avisos) ? e.avisos.filter((a) => typeof a === "string" && a) : [];
  return {
    codigo: typeof e.estado === "string" ? e.estado : null,
    planeta: typeof e.planeta === "string" ? e.planeta : null,
    modo: typeof e.modo_planeta === "string" ? e.modo_planeta : null,
    ciencia: vis != null && tot != null && tot > 0 ? Math.min(1, Math.max(0, vis / tot)) : null,
    objetivos_muestreados: vis,
    objetivos_totales: tot,
    bateria_pct: num(e.bateria),
    violaciones: col == null && sobre == null ? null : (col || 0) + (sobre || 0),
    vetos: num(e.vetos),
    barrancos_evitados: num(e.barrancos_evitados),
    replanificaciones: num(e.replanes),
    distancia: num(e.distancia_recorrida),
    paso: num(e.paso),
    motivo_final: avisos.length ? avisos[0] : null,
  };
}

// Cuatro términos y total. Un dato ausente aporta 0 al puntaje, pero se marca (`dato: false`) para no hacerlo pasar por medido.
export function desglosePuntaje(r) {
  const x = r || {};
  const t = (clave, etiqueta, valor, peso, signo) => {
    const v = num(valor);
    return { clave, etiqueta, valor: v, peso, dato: v != null, puntos: v == null ? 0 : signo * v * peso };
  };
  const terminos = [
    t("ciencia", "Ciencia (0 a 1)", x.ciencia, PESO_CIENCIA, 1),
    t("barrancos", "Barrancos evitados", x.barrancos_evitados, PESO_BARRANCOS_EVITADOS, 1),
    t("bateria", "Batería final (%)", x.bateria_pct, PESO_BATERIA, 1),
    t("violaciones", "Violaciones", x.violaciones, PENALIZACION_VIOLACION, -1),
  ];
  const bruto = terminos.reduce((s, y) => s + y.puntos, 0);
  return { terminos, bruto, total: Math.max(0, Math.round(bruto)) };
}
export function puntajeFinal(r) { return desglosePuntaje(r).total; }

export function estrellas(r) {
  const x = r || {};
  const viol = num(x.violaciones) || 0, cien = num(x.ciencia), bat = num(x.bateria_pct);
  let n = x.codigo === "EXITO" && viol === 0 ? 1 : 0;
  if (n === 1 && cien != null && cien >= UMBRAL_2_ESTRELLAS) n = 2;
  if (n === 2 && cien >= UMBRAL_3_CIENCIA && bat != null && bat >= UMBRAL_3_BATERIA) n = 3;
  return n;
}

export function tituloFinal(codigo) {
  switch (codigo) {
    case "EXITO": return "¡Misión cumplida!";
    case "FRACASO": return "Misión fallida";
    case "MODO_SEGURO": return "Misión abortada (modo seguro)";
    case "SIN_RUTA": return "Misión abortada (sin ruta)";
    default: return "Misión terminada";
  }
}

export function formatoDato(v, { sufijo = "", decimales = 0 } = {}) {
  const n = num(v);
  if (n == null) return "—";
  return `${n.toLocaleString("es-CL", { maximumFractionDigits: decimales })}${sufijo}`;
}

export function debeMostrarFinal({ activada, reducido, terminal } = {}) {
  void reducido;   // el movimiento reducido no la impide: solo apaga cuenta, entrada y confeti
  return !!activada && !!terminal;
}
export function confetiPermitido({ n, reducido }) { return n === 3 && !reducido; }

// ---------- logros (22) ----------
// estado: «directo» (dato real del rover), «adaptacion» (se adapta al motor) o «bloqueado» (sin evento equivalente: nota visible).
// ficcion: se rotula «Ficción, no evidencia». icono: nombre en final_iconos.js.
const L = (id, nombre, descripcion, icono, estado = "directo", extra = {}) => ({ id, nombre, descripcion, icono, estado, ficcion: false, nota: "", ...extra });
export const LOGROS = [
  L("primera_muestra", "Primera muestra", "Visitaste tu primer sitio científico.", "probeta"),
  L("cientifico", "Científico", "Visitaste todos los sitios científicos de una misión.", "microscopio"),
  L("mision_cumplida", "Misión cumplida", "Terminaste una misión con éxito.", "bandera"),
  L("tormenta", "Ojo de la tormenta", "Sobreviviste a una tormenta de polvo completa.", "tormenta", "adaptacion",
    { nota: "El ejemplo pedía 10 pasos seguidos; la tormenta del motor dura 6, así que se pide una completa." }),
  L("noctambulo", "Noctámbulo", "Sobreviviste una noche completa.", "noche"),
  L("geiser", "Géiser a la vista", "Presenciar un géiser.", "geiser", "bloqueado", { ficcion: true, nota: NOTA_SIN_EVENTO }),
  L("volcan", "Bajo el volcán", "Sobrevivir a una erupción volcánica en Ío.", "volcan", "bloqueado", { ficcion: true, nota: NOTA_SIN_EVENTO }),
  L("impacto", "Impacto", "Presenciaste la caída de un meteorito.", "meteorito"),
  L("primer_contacto", "Primer contacto", "Visitaste la señal anómala del motor. No afirma vida.", "alien", "adaptacion", { ficcion: true, nota: NOTA_SENAL }),
  L("senal_anomala", "Señal anómala investigada", "Visitaste la celda de una señal anómala. No confirma vida.", "senal", "adaptacion", { ficcion: true, nota: NOTA_SENAL }),
  L("viajero", "Viajero", "Hiciste tu primer viaje entre cuerpos.", "nave"),
  L("trotamundos", "Trotamundos", "Visitaste cinco cuerpos distintos.", "planeta"),
  L("gran_explorador", "Gran explorador", "Visitaste los 8 cuerpos disponibles.", "satelite", "adaptacion",
    { nota: "El ejemplo pedía 18 cuerpos; aquí hay 8 perfiles." }),
  L("aeronauta", "Aeronauta", "Completaste con éxito una misión en modo sonda.", "cohete"),
  L("ingeniero_cauto", "Ingeniero cauto", "Acumulaste cinco vetos de seguridad y terminaste con éxito.", "escudo"),
  L("limite", "Al límite", "Terminaste con éxito con menos de 15 % de batería.", "bateria"),
  L("cientifico_datos", "Científico de datos", "Abriste los tres laboratorios de los modelos.", "grafico"),
  L("comparador", "Comparador", "Abriste la comparación de políticas.", "balanza"),
  L("arquitecto", "Arquitecto del terreno", "Colocaste un barranco con el control de eventos.", "bloque"),
  L("ojos_robot", "Ojos del robot", "Cámara en primera persona.", "camara", "bloqueado", { nota: "Este juego no tiene cámara en primera persona." }),
  L("frio_extremo", "Frío extremo", "Misión en Plutón o Tritón.", "frio", "bloqueado", { ficcion: true, nota: "No hay esos cuerpos: el catálogo tiene 8." }),
  L("explorador", "Primer despliegue", "Iniciaste tu primera misión.", "huella"),
];
export const IDS_LOGROS = LOGROS.map((l) => l.id);
export function logroPorId(id) { return LOGROS.find((l) => l.id === id) || null; }

export function memoriaVacia() { return { obtenidos: {}, visitados: [], labs: [], mision: misionVacia() }; }
function misionVacia() { return { ambiente: "normal", fallo: false }; }

function clonar(m) {
  const base = m && typeof m === "object" ? m : memoriaVacia();
  return {
    obtenidos: { ...(base.obtenidos || {}) },
    visitados: Array.isArray(base.visitados) ? [...base.visitados] : [],
    labs: Array.isArray(base.labs) ? [...base.labs] : [],
    mision: { ...misionVacia(), ...(base.mision || {}) },
  };
}

// evento: {tipo:"inicio"|"viaje"|"laboratorio"|"barranco"|"paso", ...}; ahora: texto de fecha que pone quien llama (la función es pura).
// Devuelve { memoria, nuevos } sin modificar la memoria recibida; «nuevos» son las definiciones recién desbloqueadas.
export function evaluarLogros(evento, memoria, ahora = "") {
  const m = clonar(memoria);
  const nuevos = [];
  const dar = (id) => {
    if (m.obtenidos[id]) return;
    const def = logroPorId(id);
    if (!def || def.estado === "bloqueado") return;
    m.obtenidos[id] = { fecha: String(ahora) };
    nuevos.push(def);
  };
  const visitar = (nombre) => {
    if (typeof nombre === "string" && PLANETAS_VIAJE.includes(nombre) && !m.visitados.includes(nombre)) m.visitados.push(nombre);
    if (m.visitados.length >= CUERPOS_TROTAMUNDOS) dar("trotamundos");
    if (PLANETAS_VIAJE.every((p) => m.visitados.includes(p))) dar("gran_explorador");
  };
  const ev = evento && typeof evento === "object" ? evento : {};
  switch (ev.tipo) {
    case "inicio":
      m.mision = misionVacia();
      dar("explorador");
      visitar(ev.planeta);
      break;
    case "viaje":
      dar("viajero"); visitar(ev.desde); visitar(ev.hacia);
      break;
    case "laboratorio":
      if (["ag", "difuso", "rna"].includes(ev.id) && !m.labs.includes(ev.id)) m.labs.push(ev.id);
      if (ev.id === "politicas") dar("comparador");
      if (m.labs.length >= 3) dar("cientifico_datos");
      break;
    case "barranco":
      dar("arquitecto");
      break;
    case "meteorito":
      dar("impacto");
      break;
    case "paso": {
      const r = ev.resultado && typeof ev.resultado === "object" ? ev.resultado : {};
      const amb = typeof ev.ambiente === "string" ? ev.ambiente : "normal";
      const previo = m.mision.ambiente;
      const vivo = r.codigo !== "FRACASO";
      if (r.objetivos_muestreados >= 1) dar("primera_muestra");
      if (r.objetivos_totales > 0 && r.objetivos_muestreados === r.objetivos_totales) dar("cientifico");
      if (previo === "tormenta" && amb !== "tormenta" && vivo) dar("tormenta");
      if (previo === "noche" && amb !== "noche" && vivo) dar("noctambulo");
      m.mision.ambiente = amb;
      if (ev.meteorito) dar("impacto");
      if (ev.senalVisitada) { dar("senal_anomala"); dar("primer_contacto"); }
      if (r.codigo && ["FRACASO", "SIN_RUTA", "MODO_SEGURO"].includes(r.codigo)) m.mision.fallo = true;
      if (r.codigo === "EXITO") {
        dar("mision_cumplida");
        if (r.modo === "sonda") dar("aeronauta");
        if (r.bateria_pct != null && r.bateria_pct < BATERIA_AL_LIMITE) dar("limite");
        if (r.vetos != null && r.vetos >= VETOS_INGENIERO && !m.mision.fallo) dar("ingeniero_cauto");
      }
      break;
    }
    default: break;
  }
  return { memoria: m, nuevos };
}

// Lectura tolerante del almacén: cualquier cosa que no sea el formato esperado da memoria vacía.
export function leerLogros(texto) {
  const vacia = memoriaVacia();
  try {
    const o = typeof texto === "string" ? JSON.parse(texto) : texto;
    if (!o || typeof o !== "object" || Array.isArray(o)) return vacia;
    const obtenidos = {};
    if (o.obtenidos && typeof o.obtenidos === "object" && !Array.isArray(o.obtenidos)) {
      for (const id of IDS_LOGROS) {
        const d = o.obtenidos[id];
        if (d && typeof d === "object") obtenidos[id] = { fecha: typeof d.fecha === "string" ? d.fecha : "" };
      }
    }
    const lista = (x, validos) => (Array.isArray(x) ? [...new Set(x.filter((v) => typeof v === "string" && validos.includes(v)))] : []);
    return { obtenidos, visitados: lista(o.visitados, PLANETAS_VIAJE), labs: lista(o.labs, ["ag", "difuso", "rna"]), mision: misionVacia() };
  } catch (e) {
    return vacia;
  }
}
export function serializarLogros(m) {
  const x = clonar(m);
  return JSON.stringify({ obtenidos: x.obtenidos, visitados: x.visitados, labs: x.labs });
}

// Lista para mostrar: las 22 con su estado actual.
export function listaLogros(memoria) {
  const m = clonar(memoria);
  return LOGROS.map((l) => ({ ...l, obtenido: !!m.obtenidos[l.id], fecha: m.obtenidos[l.id] ? m.obtenidos[l.id].fecha : null }));
}
