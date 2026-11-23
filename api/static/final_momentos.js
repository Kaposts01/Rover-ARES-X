// Pantalla final: «mejores momentos». Captura hasta 3 imágenes del canvas del renderer (primer veto, mayor riesgo y final).
// Cada captura vuelve a dibujar la escena y copia el canvas en el mismo instante (sin preserveDrawingBuffer en el renderer).
import { MAX_MOMENTOS, ANCHO_MOMENTO } from "./final_datos.js?v=r15";
import { nombresMotivos } from "./textos.js?v=r15";

export const ORDEN_MOMENTOS = ["veto", "riesgo", "final"];

// canvas: el del renderer. dibujar(): hace un render de la escena actual. Todo fallo se anota y se salta la captura.
export function crearMomentos({ canvas, dibujar, ancho = ANCHO_MOMENTO, max = MAX_MOMENTOS } = {}) {
  const guardados = new Map();   // clave -> { titulo, texto, paso, imagen }
  let vivo = true;
  let riesgoMax = -1, pasoRiesgo = -Infinity;

  function capturar(clave, info = {}, { reemplazar = false } = {}) {
    if (!vivo || !canvas || typeof dibujar !== "function") return false;
    if (guardados.has(clave) && !reemplazar) return false;
    if (!guardados.has(clave) && guardados.size >= max) return false;
    try {
      dibujar();
      const w = canvas.width, h = canvas.height;
      if (!w || !h) return false;
      const k = Math.min(1, ancho / w);
      const copia = document.createElement("canvas");
      copia.width = Math.max(1, Math.round(w * k)); copia.height = Math.max(1, Math.round(h * k));
      const ctx = copia.getContext("2d");
      if (!ctx) return false;
      ctx.drawImage(canvas, 0, 0, copia.width, copia.height);
      guardados.set(clave, { titulo: info.titulo || "", texto: info.texto || "", paso: info.paso == null ? null : info.paso, imagen: copia.toDataURL("image/jpeg", 0.82) });
      return true;
    } catch (e) {
      console.warn("momentos: no se pudo capturar la imagen", e);
      return false;
    }
  }

  // Primer paso con un veto (cualquier motivo que empiece por «V-»).
  function alPaso({ paso, motivos, riesgo } = {}) {
    const lista = Array.isArray(motivos) ? motivos : [];
    if (!guardados.has("veto") && lista.some((m) => typeof m === "string" && m.startsWith("V-"))) {
      capturar("veto", { titulo: "Primer veto", texto: `La IA frenó una acción: ${nombresMotivos(lista.filter((m) => m.startsWith("V-")))}.`, paso });
    }
    const r = Number(riesgo);
    if (Number.isFinite(r) && r > riesgoMax && (paso == null || paso - pasoRiesgo >= 8 || !guardados.has("riesgo"))) {
      riesgoMax = r; pasoRiesgo = paso == null ? 0 : paso;
      capturar("riesgo", { titulo: "Mayor riesgo", texto: `Riesgo estimado más alto de la misión: ${Math.round(r * 100)} %.`, paso }, { reemplazar: true });
    }
  }
  function alFinal({ paso, codigo } = {}) {
    capturar("final", { titulo: "Final de la misión", texto: codigo ? `Estado: ${codigo}.` : "", paso });
  }
  function lista() { return ORDEN_MOMENTOS.filter((k) => guardados.has(k)).map((k) => guardados.get(k)); }
  function reiniciar() { guardados.clear(); riesgoMax = -1; pasoRiesgo = -Infinity; }
  function dispose() { vivo = false; reiniciar(); }
  return { alPaso, alFinal, capturar, lista, reiniciar, dispose };
}
