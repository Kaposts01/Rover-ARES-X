// Pantalla final: logros (almacén en el navegador y aviso emergente). Todo con textContent.
import { CLAVE_LOGROS, ROTULO_FICCION, evaluarLogros, normalizarResultado, leerLogros, memoriaVacia, serializarLogros, listaLogros } from "./final_datos.js?v=r14";
import { insignia } from "./final_iconos.js?v=r14";

// Almacén en localStorage con try/catch; si no está disponible, funciona en memoria durante la sesión.
export function crearAlmacenLocal(clave = CLAVE_LOGROS) {
  let enMemoria = null;
  return {
    leer() {
      try { const t = localStorage.getItem(clave); return t == null ? enMemoria : t; } catch (e) { return enMemoria; }
    },
    escribir(texto) {
      enMemoria = texto;
      try { localStorage.setItem(clave, texto); } catch (e) { /* sin almacenamiento: queda en memoria */ }
    },
    borrar() {
      enMemoria = null;
      try { localStorage.removeItem(clave); } catch (e) { /* sin almacenamiento */ }
    },
  };
}

// contenedor: donde va el aviso emergente. alDesbloquear(logro) se llama una vez por logro nuevo.
export function crearLogros({ almacen = crearAlmacenLocal(), alDesbloquear = null, contenedor = null } = {}) {
  let memoria = leerLogros(almacen.leer());
  let vivo = true;
  const avisos = new Set();
  let pila = null;
  if (contenedor) {
    pila = document.createElement("div");
    pila.className = "fn-avisos";
    pila.setAttribute("aria-live", "polite");
    contenedor.append(pila);
  }
  const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };

  function aviso(logro) {
    if (!pila || !vivo) return;
    const caja = el("div", "fn-aviso");
    const ico = el("span", "fn-aviso-icono"); ico.append(insignia(logro.icono, { tam: 44 }));
    const texto = el("div", "fn-aviso-texto");
    texto.append(el("div", "fn-aviso-kicker", "Logro desbloqueado"), el("div", "fn-aviso-nombre", logro.nombre), el("div", "fn-aviso-desc", logro.descripcion));
    if (logro.ficcion) texto.append(el("div", "fn-ficcion", ROTULO_FICCION));
    caja.append(ico, texto);
    pila.append(caja); avisos.add(caja);
    setTimeout(() => { avisos.delete(caja); caja.remove(); }, 4600);
  }

  // evento: ver evaluarLogros en final_datos.js. Devuelve los logros nuevos (puede ser una lista vacía). Nunca lanza.
  function revisar(evento) {
    if (!vivo) return [];
    try {
      const r = evaluarLogros(evento, memoria, new Date().toISOString());
      memoria = r.memoria;
      if (r.nuevos.length) {
        try { almacen.escribir(serializarLogros(memoria)); } catch (e) { console.warn("logros: no se pudo guardar", e); }
        for (const l of r.nuevos) { aviso(l); if (typeof alDesbloquear === "function") alDesbloquear(l); }
      }
      return r.nuevos;
    } catch (e) {
      console.warn("logros: no se pudo evaluar", e);
      return [];
    }
  }
  // Lee un /estado: ambiente, resultado parcial y paso de la señal anómala a «visitada» (el motor la pone en null solo al visitarla).
  let senalPrevia = false;
  function revisarEstado(e) {
    if (!e || typeof e !== "object" || e.sin_partida) return [];
    const hay = Array.isArray(e.senal);
    const senalVisitada = senalPrevia && e.senal === null;
    senalPrevia = hay;
    return revisar({ tipo: "paso", resultado: normalizarResultado(e), ambiente: e.ambiente, senalVisitada });
  }
  function lista() { return listaLogros(memoria); }
  function borrar() {
    memoria = memoriaVacia();
    try { almacen.borrar ? almacen.borrar() : almacen.escribir(serializarLogros(memoria)); } catch (e) { /* ya vacío */ }
  }
  function dispose() { vivo = false; avisos.forEach((a) => a.remove()); avisos.clear(); if (pila) pila.remove(); }
  return { revisar, revisarEstado, lista, borrar, dispose };
}
