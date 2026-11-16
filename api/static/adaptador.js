// Adaptador de datos del motor (CONTRATOS_GRAFICOS.md §8, §10 y §13: /planetas, /moviles, /objetivos).
// Intenta el endpoint real; si no existe o falla, usa los datos de prueba, que siguen exactamente
// esos esquemas. Cuando el motor publique los endpoints, no hay que tocar nada más aquí.

const PRUEBA = {
  planetas: {
    planetas: [
      { nombre: "Marte", modo: "rover", viable: true, motivo: null },
      { nombre: "Mercurio", modo: "rover", viable: true, motivo: null },
      { nombre: "Júpiter", modo: "sonda", viable: false,
        motivo: "Gigante gaseoso sin suelo accesible: no admite rodaje; usa modo sonda" },
    ],
    modos: ["rover", "sonda"],
    activo: { planeta: "Marte", modo: "rover" },
  },
  objetivos: {
    mision: "Recolecta cristales y destruye drones",
    condiciones: [
      { nombre: "Cristales", progreso: 2, total: 5, cumplido: false },
      { nombre: "Drones destruidos", progreso: 1, total: 3, cumplido: false },
    ],
  },
  moviles: {
    paso: 37,
    moviles: [
      { id: "dron-1", tipo: "dron", pos: [12, 7], trayectoria: [[11, 7], [12, 7]], estado: "persecucion" },
      { id: "obst-2", tipo: "obstaculo_movil", pos: [9, 14], trayectoria: [[9, 13], [9, 14]], estado: "patrulla" },
      { id: "meteorito-1", tipo: "meteorito", pos: [4, 20], impacto: false,
        trayectoria: [[0, 25], [2, 23], [4, 20]], zona_riesgo: [[3, 19], [3, 20], [4, 19], [4, 20]] },
    ],
    eventos_del_paso: [
      { nombre: "meteorito", efecto: "zona_riesgo", celdas: [[3, 19], [3, 20]] },
      { nombre: "senal_biologica", efecto: "lectura_anomala", afirma_vida: false, celdas: [[9, 14]] },
    ],
    ruta: { planificada: [[19, 0], [18, 0]], ejecutada: [[19, 0]] },
  },
};

// Fuente actual de cada dato: "motor" si el endpoint responde, "prueba" si no existe
const fuentes = {};

// Fuente de datos: false = datos de prueba (los endpoints aún no existen). Al publicar el motor, poner true.
// Con false no se pide nada a la red, así la consola no registra 404 de endpoints pendientes.
const FUENTE_MOTOR = { planetas: true, moviles: true, objetivos: true };   // por endpoint: el motor sirve estos tres

async function obtener(ruta, clave) {
  if (!FUENTE_MOTOR[clave]) {
    fuentes[clave] = "prueba";
    return structuredClone(PRUEBA[clave]);
  }
  try {
    const r = await fetch(ruta);
    // 409 = sin partida: no hay datos reales; el llamador oculta el bloque en vez de mostrar datos de prueba
    if (r.status === 409) {
      fuentes[clave] = "motor";
      return null;
    }
    if (r.ok) {
      fuentes[clave] = "motor";
      return await r.json();
    }
  } catch (err) {
    // Sin conexión o sin endpoint: se usan los datos de prueba
  }
  fuentes[clave] = "prueba";
  return structuredClone(PRUEBA[clave]);
}

export const planetas = () => obtener("/planetas", "planetas");
// Tolerante: si el motor manda los obstáculos móviles en «obstaculos_moviles», se mezclan en «moviles»
// con tipo «obstaculo_movil» (contrato §10). El campo «vida» de los drones se ignora.
export const objetivos = () => obtener("/objetivos", "objetivos");   // ARX-66 del motor (datos de prueba hasta entonces)
export async function moviles() {
  const datos = await obtener("/moviles", "moviles");
  if (Array.isArray(datos.obstaculos_moviles)) {
    const extra = datos.obstaculos_moviles.map((o) => ({ ...o, tipo: "obstaculo_movil" }));
    datos.moviles = [...(datos.moviles || []), ...extra];
    delete datos.obstaculos_moviles;
  }
  return datos;
}
export const fuente = (clave) => fuentes[clave] || "sin consultar";
// Temperatura interna del rover (docs/PLAN_PLANETAS.md). Datos de prueba hasta que ARX-50 la exponga en /estado.
export function calorPrueba() {
  return { temperatura_interna: 42, tolerancia: 60 };
}

// Datos de prueba de la cuarta entrada del difuso (temperatura, °C). Mismo formato que las otras tres:
// universo, curvas con 101 puntos y punto de entrada. Se quita cuando el motor devuelva curvas.temperatura.
export const TEMPERATURA_PRUEBA = true;
export function inyectarTemperaturaPrueba(datos, valor) {
  const x = Array.from({ length: 101 }, (_, i) => -60 + i);
  const fria = x.map((v) => (v <= -30 ? 1 : v >= 5 ? 0 : (5 - v) / 35));
  const templada = x.map((v) => (v <= -10 || v >= 35 ? 0 : v <= 12 ? (v + 10) / 22 : (35 - v) / 23));
  const caliente = x.map((v) => (v >= 30 ? 1 : v <= 15 ? 0 : (v - 15) / 15));
  const i = Math.min(100, Math.max(0, Math.round(valor + 60)));
  datos.universos.temperatura = { min: -60, max: 40 };
  datos.curvas.temperatura = { x, conjuntos: { fria, templada, caliente } };
  datos.entradas.temperatura = valor;
  datos.punto_entrada.temperatura = { fria: fria[i], templada: templada[i], caliente: caliente[i] };
  datos.prueba_temperatura = true;
  return datos;
}

