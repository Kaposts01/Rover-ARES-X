// Introducción con el sistema solar: datos y funciones puras (sin DOM ni THREE). Se prueban con node.
// Reutiliza las constantes del viaje entre planetas (sin duplicarlas).
import { filasFicha } from "./planeta_datos.js?v=r15";
import { PLANETAS_VIAJE, DISTANCIA_SOL_MKM, AVISO_TERRENO, datosTarjeta } from "./viaje_datos.js?v=r15";

export { PLANETAS_VIAJE, DISTANCIA_SOL_MKM, AVISO_TERRENO };
export const CLAVE_PREF = "ares.intro";          // localStorage: casilla «Mostrar intro» (activa por defecto)
export const GUARDA_PRIMER_CUADRO_S = 3;         // si no hay primer cuadro en 3 s, se omite
export const CIERRE_INACTIVIDAD_S = 90;          // sin interacción, se cierra sola y deja el asistente
export const DURACION_VUELO_S = 1.2;
export const TITULO_INTRO = "ARES-X · sistema solar";
export const SUBTITULO_INTRO = "Elige un planeta para dejarlo preparado en el asistente · Esc para ir directo al menú.";
export const ROTULO_INTRO = "Ilustración, no a escala: tamaños, distancias y velocidades son solo ilustrativos.";
// Versión corta de AVISO_TERRENO (viaje_datos.js) para la pantalla de la intro; la fuente larga sigue siendo AVISO_TERRENO. Una prueba exige que ambas digan que el terreno es el de Marte.
export const AVISO_TERRENO_INTRO = "El terreno de la partida sigue siendo el de Marte en todos los planetas.";
export const NOTA_ELEGIR = "Elegir un planeta solo lo deja seleccionado en el asistente; la partida empieza al pulsar Iniciar.";

// Valores de escena (unidades arbitrarias, NO a escala). Orden: del Sol hacia fuera, como PLANETAS_VIAJE.
export const RADIO_SOL_ESCENA = 5;
const RADIOS = { Mercurio: 0.9, Venus: 1.5, "Tierra": 1.6, Marte: 1.2, "Júpiter": 3.6, Saturno: 3.1, Urano: 2.3, Neptuno: 2.2 };
export const CUERPOS_INTRO = PLANETAS_VIAJE.map((nombre, i) => ({
  nombre,
  distanciaEscena: 11 + i * 6.5,
  radioEscena: RADIOS[nombre],
  faseBase: (i * 2.399963) % (Math.PI * 2),   // ángulo áureo: repartidos, sin alinearse
  indice: i,
}));

export function esPerfilIntro(nombre) { return CUERPOS_INTRO.some((c) => c.nombre === nombre); }

// El sistema solar es la pantalla de inicio. motivo: «abrir» (al cargar la app), «inicio» (vuelta al asistente), «salir» (salida de una partida) y
// «manual» (botón «Ver intro»: ignora la casilla). «repetir» («Volver a jugar») no pasa por la intro. Cualquier otro motivo, o ninguno, no la muestra.
// activada: casilla; webgl: hay contexto. El movimiento reducido NO la impide (solo la vuelve estática).
export const MOTIVOS_INTRO = ["abrir", "inicio", "salir"];
export function debeMostrarIntro({ motivo, activada, reducido, webgl } = {}) {
  void reducido;
  if (!webgl) return false;
  if (motivo === "manual") return true;
  return MOTIVOS_INTRO.includes(motivo) && !!activada;
}
export function modoIntro(reducido) { return reducido ? "estatico" : "animado"; }

// Ángulo = base + t·k, con k puramente visual (más lento hacia fuera). Devuelve [x, 0, z].
export function posicionOrbital(t, cuerpo) {
  const k = 0.35 / (1 + cuerpo.indice * 0.6);
  const a = cuerpo.faseBase + t * k;
  return [cuerpo.distanciaEscena * Math.cos(a), 0, cuerpo.distanciaEscena * Math.sin(a)];
}

// Vuelo de cámara: aproximación suavizada y asentamiento final. Suman exactamente la duración.
export function fasesVuelo(duracion = DURACION_VUELO_S) {
  const aproximacion = duracion * 0.8;
  return { aproximacion, asentamiento: duracion - aproximacion, total: duracion };
}
export function pasoVuelo(u) {
  const k = Math.min(1, Math.max(0, u));
  return k * k * (3 - 2 * k);
}

// Resultado de elegir un cuerpo: el planeta y el vehículo que admite según /planetas. null si no es perfil o no está en el catálogo.
export function elegirCuerpo(nombre, catalogo) {
  if (!esPerfilIntro(nombre)) return null;
  const lista = (catalogo && Array.isArray(catalogo.planetas)) ? catalogo.planetas : [];
  const en = lista.find((x) => x && x.nombre === nombre);
  if (!en || !en.modo) return null;
  return { planeta: nombre, modo: en.modo };
}

// Tarjeta del cuerpo: solo la distancia media al Sol (constante rotulada) y el vehículo permitido (de /planetas).
export function datosCuerpo(nombre, catalogo) {
  const t = datosTarjeta(nombre, nombre, catalogo);
  const lista = (catalogo && Array.isArray(catalogo.planetas)) ? catalogo.planetas : [];
  const en = lista.find((x) => x && x.nombre === nombre);
  return { titulo: nombre, filas: t.origen.concat(filasFicha(en && en.mecanicas, nombre)) };
}
