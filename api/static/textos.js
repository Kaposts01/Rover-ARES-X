import { coma as comaFormato } from "./formato.js?v=r14";
// Textos y formatos de la interfaz: funciones puras, sin DOM, que se prueban con node (api/tests/test_textos_ui.py).
// Aquí viven los nombres que ve el jugador; los valores que compara el código («automatico», «persecucion»...) no cambian.

export const plural = (n, uno, varios) => `${n} ${Number(n) === 1 ? uno : varios}`;
export const reglasActivadas = (n) => (Number(n) === 1 ? "1 regla activada" : `${Number(n) || 0} reglas activadas`);

// Vehículo de la partida: «rover» o «sonda» (cualquier otro valor cae en rover, como el motor)
export const vehiculoDe = (v) => (String(v || "").toLowerCase() === "sonda" ? "sonda" : "rover");
export const Vehiculo = (v) => { const n = vehiculoDe(v); return n[0].toUpperCase() + n.slice(1); };
// Con artículo, para frases: «el rover» / «la sonda», «del rover» / «de la sonda», «al rover» / «a la sonda»
export const elVehiculo = (v) => (vehiculoDe(v) === "sonda" ? "la sonda" : "el rover");
export const delVehiculo = (v) => (vehiculoDe(v) === "sonda" ? "de la sonda" : "del rover");
export const alVehiculo = (v) => (vehiculoDe(v) === "sonda" ? "a la sonda" : "al rover");

export const NOMBRE_MODO = { manual: "Manual", rna: "RNA", difuso: "Difuso", ag: "AG", automatico: "Híbrido" };
export const NOMBRE_TECNICA = { humano: "Humano", rna: "RNA", difuso: "Difuso", ag: "AG", supervisor: "Supervisor", combate: "Combate", escenario: "Escenario" };
export const nombreModo = (m) => NOMBRE_MODO[m] || String(m ?? "-");
export const nombreTecnica = (t) => NOMBRE_TECNICA[t] || String(t ?? "-");

// Estados de la partida (códigos del motor, en mayúscula y sin tilde) para mostrar
export const NOMBRE_ESTADO = {
  CONFIGURACION: "Configuración", EXPLORACION: "Exploración", ALERTA: "Alerta", REPLANIFICACION: "Replanificación",
  REFUGIO: "Refugio", MODO_SEGURO: "Modo seguro", EXITO: "Éxito", FRACASO: "Fracaso", SIN_RUTA: "Sin ruta",
};
export const nombreEstado = (c) => NOMBRE_ESTADO[c] || (c == null ? "-" : String(c));

// Estados de los drones tal como los manda el motor (sin tilde) y como se leen
export const NOMBRE_ESTADO_DRON = { patrulla: "patrulla", alerta: "alerta", persecucion: "persecución", ataque: "ataque" };
export const nombreEstadoDron = (e) => NOMBRE_ESTADO_DRON[e] || String(e ?? "-");

// Códigos de motivo del motor en lenguaje claro (frase corta, sin mayúscula inicial)
export const NOMBRE_MOTIVO = {
  OK: "sin riesgos, avance permitido",
  RECARGA: "recarga en una base",
  "V-RUTA-CON-RIESGO": "la ruta pasaba por una celda peligrosa",
  "V-RNA-BARRANCO": "la RNA vio un barranco delante",
  "V-RNA-BARRANCO-CONFIRMADO": "la RNA confirmó un barranco delante",
  "V-RNA-OBSTACULO": "la RNA vio un obstáculo delante",
  "V-BORDE-BARRANCO": "desnivel de barranco justo enfrente",
  "V-OBSTACULO-EN-RUTA": "obstáculo sobre la ruta",
  "V-PARADO-SIN-AVANCE": "varios pasos detenido",
  "V-CELDA-BLOQUEADA": "celda que no se puede atravesar",
  "V-SENSOR-NAN": "falla de sensor",
  "V-BATERIA-0": "sin batería",
  "V-TEMPERATURA": "temperatura interna sobre la tolerancia",
  "T-SOBRE-TOLERANCIA": "temperatura interna sobre la tolerancia",
  "V-DRON-CERCA": "dron enemigo cerca",
  "V-SEGURIDAD-BARRANCO": "barranco delante",
  "V-SEGURIDAD-OBSTACULO": "obstáculo delante",
  "V-RODEO-SIN-CANDIDATO": "sin por dónde rodear",
  "V-DISPARO-RIESGO": "disparo vetado: celda de riesgo",
  "V-DISPARO-BATERIA-CRITICA": "disparo vetado: batería crítica",
  "V-DISPARO-MODO-SEGURO": "disparo vetado: modo seguro",
  "RNA-RIESGO": "la RNA confirmó riesgo en la celda",
  "RNA-MAX-PLIBRE": "la RNA eligió la celda más libre",
  "AG-SIGUE-RUTA": "el AG sigue su ruta",
  "AG-FALLBACK-GARANTIA": "el AG usó el orden de respaldo",
  "D-VELOCIDAD-OK": "velocidad suficiente",
  "D-VELOCIDAD-BAJA": "velocidad baja",
  "D-DIFUSO-LENTO": "el difuso pidió ir tan lento que se detuvo",
  "D-RODEO": "rodeo de un obstáculo",
  "D-RESBALON": "resbalón en una pendiente",
  "D-HIELO": "resbalón sobre el hielo",
  "D-VIENTO": "una ráfaga de viento desvió al vehículo",
  "D-DISPARO-DRON": "disparo a un dron",
  "D-SIN-CAMINO": "sin camino libre",
  "D-SIN-CANDIDATO": "sin celda candidata",
  "D-FALLA-SENSOR": "sensor en falla",
  "D-SIN-ENLACE": "sin enlace con la base",
  "D-META-ALCANZADA": "meta alcanzada",
  "D-PARTIDA-TERMINADA": "partida terminada",
  "REPLAN-RUTA-VACIA": "la ruta se terminó",
  "REPLAN-SIN-RUTA": "sin ruta válida",
  "REPLAN-RUTA-INCONSISTENTE": "ruta incoherente",
  "REPLAN-SISMO": "sismo en la ruta",
  "REPLAN-AG-SISMO": "sismo: el AG recalculó el orden",
  "REPLAN-AG-METEORITO": "meteorito: el AG recalculó el orden",
  "REPLAN-AG-SENAL": "señal biológica: el AG recalculó el orden",
  "CAZA-DRON-BFS": "persigue al dron por la ruta más corta",
  EXITO: "misión cumplida", FRACASO: "la misión fracasó", SIN_RUTA: "no queda ruta posible", MODO_SEGURO: "el vehículo entró en modo seguro",
};
export function nombreMotivo(codigo) {
  const t = String(codigo ?? "");
  const base = t.split(":")[0];
  if (NOMBRE_MOTIVO[base]) return NOMBRE_MOTIVO[base];
  if (base.startsWith("REPLAN-AG-")) return "el AG recalculó el orden de visita";
  if (base.startsWith("REPLAN")) return "replanificación";
  return t;   // sin traducción: se muestra tal cual, no se inventa
}
export const nombresMotivos = (lista) => (lista || []).filter(Boolean).map(nombreMotivo).join(", ");

// Los avisos del motor a veces llevan un código delante («T-SOBRE-TOLERANCIA: 63 °C…») y hablan del «rover» aunque el
// vehículo sea la sonda: se quita el código y se usa el vehículo real.
export function limpiarAviso(texto, vehiculo = "rover") {
  let t = String(texto ?? "").replace(/^[A-Z]{1,6}(?:-[A-Z0-9]+)+\s*:\s*/, "");
  if (vehiculoDe(vehiculo) === "sonda") {
    t = t.replace(/\bel rover\b/g, "la sonda").replace(/\bEl rover\b/g, "La sonda").replace(/\bdel rover\b/g, "de la sonda")
      .replace(/\bal rover\b/g, "a la sonda").replace(/\brover\b/g, "sonda").replace(/\bRover\b/g, "Sonda");
  }
  return t;
}

// Puntaje: es uno solo y lo calcula el motor (/estado: puntaje, puntaje_desglose, puntaje_formula). Aquí no se calcula nada.
export const AYUDA_PUNTAJE = "Puntaje de juego: el único de la partida, calculado por el motor. No es un criterio de evaluación.";
export function ayudaPuntaje(formula) {
  const f = typeof formula === "string" && formula.trim() ? formula.trim() : "";
  return f ? `${AYUDA_PUNTAJE} ${f}` : AYUDA_PUNTAJE;
}
// «Sitios visitados» (cuántos sitios pisaste) y «Ciencia recogida» (valor según la ventana de tiempo de cada sitio) son dos datos distintos
export const AYUDA_SITIOS_Y_CIENCIA = "Sitios visitados cuenta cuántos sitios pisaste (8 de 8 = todos). Ciencia recogida es otra cifra: cada sitio vale según la ventana de tiempo en que lo visitaste, por eso puede ser menor aunque hayas visitado todos.";
export function textoSitios(visitados, totales) {
  const ok = (v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));
  return ok(visitados) && ok(totales) ? `${Number(visitados)} de ${Number(totales)}` : "—";
}
export function textoCiencia(fraccion) {
  const ok = fraccion !== null && fraccion !== undefined && fraccion !== "" && Number.isFinite(Number(fraccion));
  return ok ? `${comaFormato(Number(fraccion) * 100, 1)} %` : "—";
}

// Batería del difuso: lo que se rotula «%» es el porcentaje real (el del HUD); la entrada que usó el difuso está en
// unidades del motor y se dice como tal.
export function textoBateriaDifuso(entradas) {
  const e = entradas || {};
  const pct = Number(e.bateria_pct), u = Number(e.bateria);
  const f = (v, d) => comaFormato(v, d, "-");
  if (!Number.isFinite(pct)) return `${f(u, 0)} u. del motor`;
  return `${f(pct, 1)} % (${f(u, 0)} u. del motor)`;
}
export const ETIQUETA_BATERIA_UNIVERSO = "batería (unidades del motor, 0 a 100)";

// Candidato del AG: no trae «ruta_pasos»; se cuenta lo que sí trae (el orden de sitios y los puntos de paso)
export function textoCandidatoAG(c) {
  const orden = c && Array.isArray(c.orden) ? c.orden.length : (c && Array.isArray(c.cromosoma) ? c.cromosoma.length : null);
  if (orden == null) return "Valores tal como los devuelve el motor; el peso se aplica dentro del fitness.";
  const pasos = c.pasos ? c.pasos.filter((q) => q != null).length : 0;
  return `Orden de ${plural(orden, "sitio", "sitios")}${pasos ? ` con ${plural(pasos, "punto de paso", "puntos de paso")}` : ""}. Valores tal como los devuelve el motor; el peso se aplica dentro del fitness.`;
}

// Evaluación de la RNA: la configuración (no hay «nota» en la respuesta)
export function textoEvaluacionRNA(ev) {
  const mapas = ev && Array.isArray(ev.mapas_prueba) && ev.mapas_prueba.length ? ev.mapas_prueba.join(", ") : "-";
  const conf = ev && ev.configuracion ? ` Configuración: ${ev.configuracion}.` : "";
  return `Filas: clase real. Columnas: clase predicha. Mapas de prueba: ${mapas}.${conf}`;
}

// Comparación de políticas: nombre y explicación de cada variante, sin los nombres internos del motor
export const VARIANTES_POLITICA = {
  hibrido: ["Híbrido", "las tres técnicas y el supervisor trabajando juntos"],
  sin_rna: ["Sin RNA", "el híbrido sin la red neuronal"],
  sin_difuso: ["Sin difuso", "el híbrido sin el control de velocidad difuso"],
  sin_ag_vecino: ["Sin AG (vecino más cercano)", "el orden de visita se arma yendo siempre al sitio más cercano"],
  sin_ag_mas_corta: ["AG solo por distancia", "el AG con pesos solo de distancia; con pocos sitios coincide con el híbrido"],
  sin_ag_2opt: ["Sin AG (ruta con 2-opt)", "vecino más cercano mejorado con 2-opt, una mejora local que desenreda cruces de la ruta, sin AG"],
  ruta_corta: ["Ruta corta voraz", "ruta corta que elige siempre el vecino más cercano; no es la ruta óptima"],
  ag_puro: ["AG puro", "el AG con el riesgo congelado y sin RNA ni difuso"],
};
export const nombreVariante = (k) => (VARIANTES_POLITICA[k] ? VARIANTES_POLITICA[k][0] : String(k).replace(/_/g, " "));
export const ayudaVariante = (k) => (VARIANTES_POLITICA[k] ? VARIANTES_POLITICA[k][1] : "");
export const NOTA_POLITICAS = "Cada variante apaga o cambia una técnica y juega las mismas semillas que el híbrido, en la capa de juego. Las cifras comparan estas condiciones: no prueban causas fuera de ellas. Los intentos a barranco no se miden en el híbrido.";
export function notaVariantes(variantes) {
  return Object.keys(variantes || {}).filter((k) => k !== "hibrido" && ayudaVariante(k)).map((k) => `${nombreVariante(k)}: ${ayudaVariante(k)}.`).join(" ");
}

// Resumen de la pantalla de meta: pasos, puntaje, sitios, ciencia y batería
export function resumenMeta(e) {
  const x = e || {};
  const f1 = (v) => (typeof v === "number" ? comaFormato(v, 1) : "—");
  return [
    ["Pasos", x.paso == null ? "—" : String(x.paso)],
    ["Puntaje", x.puntaje == null ? "—" : String(x.puntaje)],
    ["Sitios visitados", textoSitios(x.sitios_visitados, x.sitios_totales)],
    ["Ciencia recogida", textoCiencia(x.ciencia_fraccion)],
    ["Batería", `${f1(x.bateria_pct ?? x.bateria)} %`],
  ];
}

// ---------- eventos: dónde pasó y qué se ve (ronda 23) ----------
// Direcciones entre dos celdas [fila, columna]; la fila crece hacia el sur y la columna hacia el este (como el motor).
const PUNTOS_CARDINALES = ["este", "sureste", "sur", "suroeste", "oeste", "noroeste", "norte", "noreste"];
export function direccionEntre(desde, hasta) {
  const df = Number(hasta[0]) - Number(desde[0]), dc = Number(hasta[1]) - Number(desde[1]);
  if (df === 0 && dc === 0) return null;
  const angulo = Math.atan2(df, dc);                           // 0 = este, π/2 = sur
  return PUNTOS_CARDINALES[(Math.round(angulo / (Math.PI / 4)) + 8) % 8];
}
// «fila 19, columna 2 · a 2 celdas al este de la sonda»; sin vehículo, solo la celda
export function ubicacionEvento(celda, vehiculoCelda, vehiculo = "rover") {
  if (!Array.isArray(celda) || celda.length < 2) return "";
  const base = `fila ${celda[0]}, columna ${celda[1]}`;
  if (!Array.isArray(vehiculoCelda) || vehiculoCelda.length < 2) return base;
  const dist = Math.max(Math.abs(celda[0] - vehiculoCelda[0]), Math.abs(celda[1] - vehiculoCelda[1]));
  const dir = direccionEntre(vehiculoCelda, celda);
  const de = vehiculoDe(vehiculo) === "sonda" ? "de la sonda" : "del rover";
  if (dist === 0 || !dir) return `${base} · justo donde está ${vehiculoDe(vehiculo) === "sonda" ? "la sonda" : "el rover"}`;
  return `${base} · a ${plural(dist, "celda", "celdas")} al ${dir} ${de}`;
}
// Cómo se marca cada evento en la escena: rótulo corto, color y si va sobre una celda o sobre el vehículo
export const MARCA_EVENTO = {
  barranco: { rotulo: "Barranco", color: 0xff5d6c, sobre: "celda" },
  meteorito: { rotulo: "Impacto de meteorito", color: 0xff8a3c, sobre: "celda" },
  sismo: { rotulo: "Sismo: grietas", color: 0xffb454, sobre: "celda" },
  senal_biologica: { rotulo: "Señal biológica", color: 0x6ee7a8, sobre: "celda" },
  falla_sensor: { rotulo: "Falla de sensor", color: 0xffb454, sobre: "vehiculo" },
  bateria_baja: { rotulo: "Batería baja", color: 0xff5d6c, sobre: "vehiculo" },
  tormenta: { rotulo: "Tormenta", color: 0xb4bfd3, sobre: "vehiculo" },
  noche: { rotulo: "Noche", color: 0x7f9bff, sobre: "vehiculo" },
  baja_conectividad: { rotulo: "Sin enlace", color: 0xa78bfa, sobre: "vehiculo" },
};
// Celdas afectadas según la respuesta de POST /evento
export function celdasDeEvento(nombre, r) {
  if (!r || typeof r !== "object") return [];
  const lista = [];
  const una = (c) => { if (Array.isArray(c) && c.length === 2 && c.every((n) => Number.isFinite(Number(n)))) lista.push([Number(c[0]), Number(c[1])]); };
  if (Array.isArray(r.celdas)) r.celdas.forEach(una);
  if (Array.isArray(r.grietas)) r.grietas.forEach(una);
  if (r.impacto) una(r.impacto);
  if (r.celda) una(r.celda);
  return lista;
}
// Frase del aviso: qué pasó y dónde. Un evento sin efecto lo dice claro.
export function avisoEvento(nombre, rotulo, r, vehiculoCelda, vehiculo = "rover") {
  const detalle = (r && r.detalle) || (r && r.ok ? "hecho" : "sin efecto");
  if (!r || !r.ok) return `Evento ${rotulo} sin efecto: ${detalle}`;
  const celdas = celdasDeEvento(nombre, r);
  let donde = celdas.length ? ubicacionEvento(celdas[0], vehiculoCelda, vehiculo) : "";
  // el detalle del motor ya dice «en (19, 2)»: no se repite fila y columna
  if (donde && String(detalle).includes(`(${celdas[0][0]}, ${celdas[0][1]})`)) donde = donde.replace(/^fila \d+, columna \d+( · )?/, "");
  return donde ? `Evento ${rotulo}: ${detalle} · ${donde}` : `Evento ${rotulo}: ${detalle}`;
}

// ---------- acciones de un paso (ronda 23): lo que hizo el vehículo, en lenguaje claro ----------
export const NOMBRE_ACCION = {
  avanzar: "avanzó", replanificar: "replanificó la ruta", esperar: "esperó", detener: "se detuvo", disparar: "disparó a un dron",
  cazar: "persiguió a un dron", recargar: "recargó batería", fin: "terminó", error: "no pudo decidir",
};
export const nombreAccion = (a) => NOMBRE_ACCION[a] || String(a ?? "—").replace(/_/g, " ");

// Nombres del difuso para mostrar: el motor usa identificadores sin tilde (bateria, critica, rapida…); en pantalla van con tilde
const NOMBRE_DIFUSO = { bateria: "batería", inclinacion: "inclinación", critica: "crítica", rapida: "rápida", fria: "fría", media: "media", salida: "velocidad de salida" };
export const nombreDifuso = (x) => NOMBRE_DIFUSO[x] || String(x ?? "");

// Parámetros del difuso que difieren del de defecto (GET /ag/evolucion → parametros_difuso). Claves del motor:
//   «distancia.cerca», «salida.lenta»…  lista de puntos de la función de pertenencia (3 = triángulo, 4 = trapecio)
//   «regla.R4»                           peso de la regla (0 = desactivada)
//   «conduccion.v_hielo», «…v_viento», «…v_pendiente», «…factor_desvio», «…umbral_desvio»   topes y umbrales de conducción
const UNIDAD_VARIABLE_DIFUSO = { distancia: " m", bateria: " %", inclinacion: " °", temperatura: " °C", salida: "" };
const NOMBRE_CONDUCCION = {
  v_hielo: ["Tope de velocidad sobre hielo", "fraccion"], v_viento: ["Tope de velocidad con viento fuerte", "fraccion"],
  v_pendiente: ["Tope de velocidad en pendiente fuerte", "fraccion"], factor_desvio: ["Reserva de batería exigida para seguir hasta la meta", "veces"],
  umbral_desvio: ["Batería por debajo de la cual se desvía a una base", "porcentaje"],
};
// Devuelve [nombre, texto] listo para mostrar; una clave que no se conoce se muestra tal cual, con guiones bajos como espacios.
export function parametroDifusoLegible(clave, valor) {
  const k = String(clave ?? "");
  const num = (v, d = 2) => comaFormato(v, d, "—");
  const corto = (v) => num(v, 2).replace(/,?0+$/, "");   // 0,00 → 0 · 15,80 → 15,8 · 45,00 → 45
  const lista = Array.isArray(valor) ? valor.filter((x) => Number.isFinite(Number(x))) : null;
  const m = /^([a-z_]+)\.([A-Za-z0-9_]+)$/.exec(k);
  if (m && lista) {
    const [, variable, etiqueta] = m;
    const unidad = UNIDAD_VARIABLE_DIFUSO[variable] ?? "";
    return [`${nombreDifuso(variable)[0].toUpperCase()}${nombreDifuso(variable).slice(1)} · «${nombreDifuso(etiqueta)}»`,
      `función de pertenencia con puntos ${lista.map(corto).join(" · ")}${unidad}`];
  }
  if (m && m[1] === "regla") return [`Regla ${m[2]}`, Number(valor) === 0 ? "desactivada" : `peso ${corto(valor)} (1 = el de defecto)`];
  if (m && m[1] === "conduccion" && NOMBRE_CONDUCCION[m[2]]) {
    const [nombre, tipo] = NOMBRE_CONDUCCION[m[2]];
    return [nombre, tipo === "porcentaje" ? `${num(Number(valor) * 100, 0)} % de la capacidad` : tipo === "veces" ? `×${corto(valor)}` : `${num(Number(valor) * 100, 0)} % de la velocidad máxima`];
  }
  const texto = lista ? lista.map(corto).join(" · ") : typeof valor === "number" ? num(valor, 3) : String(valor);
  return [k.replace(/[._]/g, " "), texto];
}

// ---------- Laboratorio genético (ronda 23) ----------
export const LAB_AG = {
  calculando: (s) => `Calculando… ${s} s`,
  terminado: (resumen, s) => `${resumen} · calculado en ${comaFormato(s, 1)} s`,
  opcionSinParada: "sin parada (todas las generaciones)",
  notaPesos: "Estos pesos mueven el fitness del laboratorio. En la partida el AG planifica con ventanas de tiempo (cada sitio vale más si se llega dentro de la suya), "
    + "recargas obligatorias en las bases y sitios opcionales que puede descartar; su fitness es la ciencia recogida menos un coste por pasos y por recargas reparadas, y no usa estos pesos.",
  factible: "plan factible", infactible: "plan infactible",
  violaciones: "Restricciones que incumple", paradas: "Paradas de recarga", descartados: "Sitios opcionales descartados", ciencia: "Ciencia recogida", pasos: "Pasos",
};
export function lineasExtraCandidatoAG(c) {
  const x = c || {};
  const filas = [];
  const lista = (v) => (Array.isArray(v) ? v : []);
  if (typeof x.factible === "boolean") filas.push([x.factible ? LAB_AG.factible : LAB_AG.infactible, ""]);
  const viol = lista(x.violaciones).map((v) => (typeof v === "string" ? v : JSON.stringify(v)));
  if (viol.length) filas.push([LAB_AG.violaciones, viol.join("; ")]);
  const paradas = lista(x.paradas).length ? lista(x.paradas).length : lista(x.recargas).length;
  if (paradas) filas.push([LAB_AG.paradas, String(paradas)]);
  if (lista(x.sacrificados).length) filas.push([LAB_AG.descartados, String(lista(x.sacrificados).length)]);
  const ciencia = [x.ciencia, x.ciencia_recogida].find((v) => Number.isFinite(Number(v)) && v !== null);
  if (ciencia !== undefined) filas.push([LAB_AG.ciencia, comaFormato(ciencia, 2)]);
  if (Number.isFinite(Number(x.pasos)) && x.pasos !== null) filas.push([LAB_AG.pasos, String(Math.round(Number(x.pasos)))]);
  return filas;
}

// ---------- Evolución del AG en el mapa (ronda 23) ----------
export const EVO = {
  titulo: "Evolución del AG en el mapa",
  mostrar: "Mostrar en el mapa", ocultar: "Ocultar del mapa",
  ayudaMostrar: "Dibuja sobre el mapa las rutas candidatas que probó el algoritmo genético, generación por generación.",
  apagada: "Apagada: no se dibuja nada en el mapa ni se pide nada al motor.",
  calculando: "Calculando la evolución del AG… puede tardar unos segundos.",
  reproducir: "Reproducir la evolución", pausar: "Pausar", velocidad: "Velocidad de reproducción", generacion: "Generación",
  generaciones: "generaciones", calculadoEn: "calculado en",
  curvaFitness: "fitness por generación · mejor y media", curvaDiversidad: "diversidad de la población (0 = todas iguales, 1 = todas distintas)",
  mejor: "mejor", media: "media",
  leyMejor: "Línea amarilla: la mejor ruta", leyResto: "Líneas cian: otras candidatas", leySitio: "Anillo naranja: sitio y su ventana de tiempo", leyBase: "Rombo verde: base de recarga",
  lecturaTitulo: "lectura del candidato bajo el puntero",
  lecturaVacia: "Pasa el puntero sobre una ruta del mapa para ver su orden de visita, su fitness y si cumple las restricciones.",
  rectas: "La línea une los sitios en el orden de visita: no es el camino que recorrería el vehículo celda a celda.",
  parametrosDifuso: "Parámetros del difuso que eligió el AG", recalcular: "Volver a calcular desde la posición actual",
  fuenteLab: "El motor todavía no publica la evolución completa: se usan las poblaciones del laboratorio genético. No traen ventanas de tiempo, paradas de recarga ni si cada candidato es factible.",
  candidato: "Candidato", orden: "Orden", recargas: "Recargas", recarga: "recarga", antesDe: "antes de", despuesDe: "después de", antesDelPrimero: "antes del primer sitio", sinRecargas: "ninguna", penalizaciones: "Penalizaciones",
  fitness: "Fitness", mejorDeLaGeneracion: "la mejor de la generación", factible: "Factible", si: "sí", no: "no", sinDato: "sin dato",
  restriccion: "Restricción que viola", sinDetalle: "el motor no detalla cuál", ventanas: "Ventanas",
  sinRespuesta: "El motor no respondió con la evolución del AG. Revisa que haya partida y vuelve a intentarlo.",
  sinPlan: "Todavía no hay un plan del AG: inicia la misión y deja que la IA planifique.",
  sinSitios: "No quedan sitios pendientes: no hay orden de visita que evolucionar.",
  sinSitiosEnDatos: "La respuesta del motor no trae sitios que dibujar.",
  sinGeneraciones: "La respuesta del motor no trae generaciones con rutas candidatas.",
  inviableLab: "el orden no es viable con la batería disponible",
  accesoGenetico: "Ver la evolución en el mapa",
  copias: (n) => `${n} individuos de la población tienen este mismo orden`,
  planCambio: "El plan cambió después de calcular esta evolución: pulsa «Volver a calcular desde la posición actual».",
};

// ---------- edición de reglas difusas (ronda 23) ----------
export const EDIT = {
  sinRespuesta: "El motor no respondió con las reglas del difuso. Revisa que haya partida.",
  sinVariables: "El motor no entregó las variables del difuso.", sinReglas: "El motor no entregó reglas.",
  sinCondicion: "la regla no tiene ninguna condición", variableDesconocida: (v) => `la variable «${v}» no existe`,
  etiquetaDesconocida: (e, v) => `«${e}» no es una etiqueta de ${v}`, variableRepetida: (v) => `usa ${v} dos veces`,
  fueraDelUniverso: (e, v) => `«${e}» queda fuera del universo de ${v}`, sinCobertura: (e, v) => `«${e}» de ${v} no cubre ningún valor`,
  puntosDesordenados: (donde, pts) => `${donde}: los puntos deben ir de menor a mayor (ahora: ${pts}).`,
  puntosIguales: (donde) => `${donde}: los puntos no pueden ser todos iguales, la etiqueta no cubriría nada.`,
  puntosFuera: (donde, a, b) => `${donde}: algún punto queda fuera del universo (de ${a} a ${b}).`,
  hueco: (n, a, b) => `En ${n}, ninguna etiqueta cubre los valores de ${a} a ${b}: ahí ninguna regla se activaría.`,
  pesoFuera: (id) => `${id}: el peso debe estar entre 0 y 1.`,
  consecuenteDesconocido: (id, e) => `${id}: la velocidad «${e || "—"}» no existe.`,
  noViable: (id, motivo) => `${id} no se activará nunca: ${motivo}.`,
  ningunaActiva: "Deja al menos una regla activa: sin ninguna, el vehículo no tendría salida y se detendría siempre.",
  titulo: "Editar reglas y funciones de pertenencia",
  modoExplorar: "Explorar", modoEditar: "Editar reglas",
  ayuda: "Activa o desactiva reglas, cambia su velocidad o su peso (0 a 1) y arrastra los puntos de las curvas. La salida, las activaciones y la superficie se recalculan al instante; abajo se ve el antes y el después.",
  personalizadas: "Reglas personalizadas activas", delPlaneta: "Reglas del planeta", vistaPrevia: "Reglas personalizadas · solo vista previa",
  restaurar: "Restaurar reglas del planeta", restaurando: "Restaurando…", restauradas: "Reglas del planeta restauradas.",
  aplicando: "Aplicando a la partida…", aplicada: "Aplicadas a la partida en curso.", noAplicada: (m) => `No se aplicó: ${m}`,
  aplicarInterruptor: "Aplicar a la partida en curso", aplicarAyuda: "Activado: los cambios pasan solos a la partida a los 0,6 s. Desactivado: solo se ven en la vista previa y la partida sigue como está.",
  soloVista: "Solo vista previa: los cambios no se envían a la partida.",
  sinSoporte: "El motor todavía no acepta reglas personalizadas: los cambios solo se ven aquí, en la vista previa; la partida sigue con las reglas del planeta.",
  hayErrores: "Hay errores que corregir antes de aplicar a la partida.", sinCambios: "Sin cambios respecto a las reglas del planeta.",
  cambios: (n) => `${n} ${n === 1 ? "cambio" : "cambios"} respecto a las reglas del planeta`,
  colActiva: "Activa", colRegla: "Regla", colPeso: "Peso", colViable: "Viable", colFuerza: "Fuerza antes → después",
  viable: "Sí", nada: "No", si: "si", y: "y", es: "es", entonces: "entonces velocidad", quitar: "Quitar condición", agregar: "+ condición",
  salidaTitulo: "Salida · velocidad", antes: "antes", despues: "después", salidaDe: "Velocidad",
  activaciones: "Activaciones", superficie: "Superficie de velocidad · distancia y batería", verCambio: "Ver el cambio (después − antes)",
  barrido: "Barrido de distancia · de 10 a 1 m", pertenencia: "Funciones de pertenencia · arrastra los puntos", puntos: "Puntos",
  ejeDistancia: "distancia (m)", ejeBateria: "batería (unidades del motor)",
  sinEntradas: "Mueve alguna entrada o consulta el difuso para calcular el efecto.",
  tablaAyuda: "El peso multiplica la fuerza de la regla. Una regla con peso 0 es como si estuviera apagada.",
  curvaOriginal: "línea discontinua: las reglas del planeta",
};
