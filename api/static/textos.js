// Textos y formatos de la interfaz: funciones puras, sin DOM, que se prueban con node (api/tests/test_textos_ui.py).
// Aquí viven los nombres que ve el jugador; los valores que compara el código («automatico», «persecucion»...) no cambian.

export const plural = (n, uno, varios) => `${n} ${Number(n) === 1 ? uno : varios}`;
export const reglasActivadas = (n) => (Number(n) === 1 ? "1 regla activada" : `${Number(n) || 0} reglas activadas`);

// Vehículo de la partida: «rover» o «sonda» (cualquier otro valor cae en rover, como el motor)
export const vehiculoDe = (v) => (String(v || "").toLowerCase() === "sonda" ? "sonda" : "rover");
export const Vehiculo = (v) => { const n = vehiculoDe(v); return n[0].toUpperCase() + n.slice(1); };

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
  "V-RUTA-CON-RIESGO": "la ruta pasaba por una celda peligrosa",
  "V-RNA-BARRANCO": "la RNA vio un barranco delante",
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

// Puntaje simple del HUD (juego/partida.py: puntaje): la fórmula real, en una línea
export const FORMULA_PUNTAJE_SIMPLE = "100 × sitios visitados ÷ sitios totales + 0,5 × batería restante (unidades del motor) + 50 si no hubo ningún veto del supervisor";
export const AYUDA_PUNTAJE_SIMPLE = `Puntaje simple = ${FORMULA_PUNTAJE_SIMPLE}. No es el puntaje de la pantalla final ni un criterio de evaluación.`;
export function puntajeSimple({ visitados, totales, bateria, vetos }) {
  const ciencia = totales > 0 ? (100 * visitados) / totales : 0;
  return Math.round(ciencia + 0.5 * bateria + (vetos === 0 ? 50 : 0));
}

// Batería del difuso: lo que se rotula «%» es el porcentaje real (el del HUD); la entrada que usó el difuso está en
// unidades del motor y se dice como tal.
export function textoBateriaDifuso(entradas) {
  const e = entradas || {};
  const pct = Number(e.bateria_pct), u = Number(e.bateria);
  const f = (v, d) => (Number.isFinite(v) ? v.toFixed(d).replace(".", ",") : "-");
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

// Resumen de la pantalla de meta: pasos, puntaje y batería
export function resumenMeta(e) {
  const x = e || {};
  const f1 = (v) => (typeof v === "number" ? v.toFixed(1).replace(".", ",") : "—");
  return [
    ["Pasos", x.paso == null ? "—" : String(x.paso)],
    ["Puntaje simple", x.puntaje == null ? "—" : String(x.puntaje)],
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
