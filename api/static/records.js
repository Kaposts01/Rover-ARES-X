// Vista «Récords»: mejores marcas por semilla (y planeta y nivel), con filtros, y borrado con confirmación en la página.
import { el, boton, campo, selector, crearCapa } from "./vx_ui.js?v=r15";
import {
  NIVELES, nombreNivel, nombreTamano, rotuloOrigen, AYUDA_ORIGEN, politicaDe, textoResultado, textoBateria, fechaLegible,
  consultaFiltros, hayFiltros, TEXTO_VACIO, TEXTO_VACIO_FILTRADO, TEXTO_ERROR, textoBorrado, configuracionDe,
} from "./records_datos.js?v=r15";
import { Vehiculo, plural } from "./textos.js?v=r15";

// alJugar(config): empieza una misión con esa semilla y condiciones (lo resuelve app.js)
export function crearRecords({ alJugar = null } = {}) {
  const capa = crearCapa({ clase: "vx-records", kicker: "Récords", titulo: "Mejores marcas por semilla", etiqueta: "Récords por semilla" });
  const filtros = { planeta: "", nivel: "", tamano: "", origen: "", resultado: "", semilla: "" };
  let verTodos = false, ultimo = null;

  const cPlaneta = selector([["", "todos"]]);
  const cNivel = selector([["", "todos"], ...NIVELES.map((n, i) => [i + 1, n])]);
  const cTamano = selector([["", "todos"], ["pequeno", "Pequeño"], ["mediano", "Mediano"], ["grande", "Grande"]]);
  const cOrigen = selector([["", "todas"], ["manual", "Manual"], ["asistida", "Manual con ayuda de la IA"], ["ia", "IA"]]);
  const cResultado = selector([["", "todos"], ["EXITO", "Éxito"], ["FRACASO", "Fracaso"]]);
  const cSemilla = el("input", "vx-control"); cSemilla.type = "number"; cSemilla.min = "0"; cSemilla.placeholder = "cualquiera";
  const cOrden = selector([["puntaje", "Mejor puntaje"], ["semilla", "Semilla"], ["reciente", "Más reciente"]], "puntaje");
  cOrden.addEventListener("change", () => pintar());
  const limpiar = boton("Limpiar filtros", "secundario", () => {
    for (const k of Object.keys(filtros)) filtros[k] = "";
    [cPlaneta, cNivel, cTamano, cOrigen, cResultado, cSemilla].forEach((c) => { c.value = ""; });
    cargar();
  });
  const barra = el("div", "vx-barra");
  barra.append(campo("Planeta", cPlaneta), campo("Nivel", cNivel), campo("Tamaño", cTamano), campo("Quién jugó", cOrigen), campo("Resultado", cResultado), campo("Semilla", cSemilla), campo("Ordenar por", cOrden), limpiar);
  const enlaces = { planeta: cPlaneta, nivel: cNivel, tamano: cTamano, origen: cOrigen, resultado: cResultado, semilla: cSemilla };
  for (const [k, c] of Object.entries(enlaces)) c.addEventListener("change", () => { filtros[k] = c.value; cargar(); });

  const verTodosC = el("input"); verTodosC.type = "checkbox";
  verTodosC.addEventListener("change", () => { verTodos = verTodosC.checked; pintar(); });
  const etiquetaTodos = el("label", "vx-check"); etiquetaTodos.append(verTodosC, document.createTextNode(" Mostrar todos los intentos, no solo la mejor marca"));
  const borrar = boton("Borrar récords…", "peligro", () => pedirBorrado());
  const sub = el("div", "vx-subbarra"); sub.append(etiquetaTodos, borrar);

  const resumen = el("div", "ayuda vx-resumen"); resumen.setAttribute("role", "status"); resumen.setAttribute("aria-live", "polite");
  const confirmacion = el("div", "vx-confirmar oculto"); confirmacion.setAttribute("role", "alertdialog");
  const tablaCaja = el("div", "vx-tabla-caja");
  const leyenda = el("div", "ayuda");
  leyenda.textContent = "Puntaje de juego: el de la pantalla final. Los récords cuentan solo misiones con éxito: gana el mayor puntaje y, a igualdad, menos pasos. Las marcas manuales, las manuales con ayuda de la IA y las de la IA compiten por separado.";
  capa.cuerpo.append(barra, sub, resumen, confirmacion, tablaCaja, leyenda);

  function mensaje(texto, conReintento = false) {
    tablaCaja.replaceChildren();
    const m = el("div", "vx-vacio", texto);
    if (conReintento) m.append(document.createTextNode(" "), boton("Reintentar", "secundario", () => cargar()));
    tablaCaja.append(m);
  }

  async function cargar() {
    resumen.textContent = "Cargando…";
    try {
      const r = await fetch(`/records${consultaFiltros(filtros)}`);
      if (!r.ok) throw new Error(String(r.status));
      ultimo = await r.json();
    } catch (e) {
      ultimo = null; resumen.textContent = ""; mensaje(TEXTO_ERROR, true); borrar.disabled = true; return;
    }
    cPlaneta.replaceChildren(...[["", "todos"], ...ultimo.planetas.map((p) => [p, p])].map(([v, t]) => { const o = el("option", "", t); o.value = v; return o; }));
    cPlaneta.value = ultimo.planetas.includes(filtros.planeta) ? filtros.planeta : "";
    borrar.disabled = ultimo.total === 0;
    pintar();
  }

  function pintar() {
    if (!ultimo) return;
    const filas = [...(verTodos ? ultimo.records : ultimo.mejores)];
    if (cOrden.value === "semilla") filas.sort((a, b) => (a.semilla - b.semilla) || String(a.planeta).localeCompare(String(b.planeta)) || (a.nivel - b.nivel));
    else if (cOrden.value === "reciente") filas.sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
    resumen.textContent = ultimo.total === 0 ? "" : `${plural(ultimo.total, "misión guardada", "misiones guardadas")} · ${verTodos ? `${plural(ultimo.filtrados, "intento", "intentos")} con estos filtros` : `${plural(ultimo.mejores.length, "mejor marca", "mejores marcas")} con estos filtros`}`;
    if (!filas.length) { mensaje(ultimo.total === 0 || !hayFiltros(filtros) ? TEXTO_VACIO : TEXTO_VACIO_FILTRADO); return; }
    const tabla = el("table", "lab-tabla vx-tabla");
    const cab = el("tr");
    for (const t of ["Planeta", "Nivel", "Tamaño", "Semilla", "Vehículo", "Quién jugó", "Resultado", "Puntaje", "Pasos", "Batería", verTodos ? "Fecha" : "Éxitos / intentos", ""]) cab.append(el("th", "", t));
    const th = el("thead"); th.append(cab);
    const cuerpo = el("tbody");
    for (const r of filas) {
      const tr = el("tr", r.resultado === "EXITO" ? "" : "vx-fallo");
      const quien = el("td");
      const ins = el("span", `vx-insignia vx-${r.origen}`, r.origen === "asistida" ? "Manual + IA" : rotuloOrigen(r.origen));
      ins.title = `${rotuloOrigen(r.origen)}. ${AYUDA_ORIGEN[r.origen] || ""}`.trim();
      quien.append(ins);
      if (r.origen === "ia") quien.append(document.createTextNode(` ${politicaDe(r)}`));
      const jugar = boton("Jugar esta semilla", "secundario vx-jugar", () => { if (alJugar) { capa.cerrar(); alJugar(configuracionDe(r)); } });
      jugar.title = `Empieza una misión en ${r.planeta}, nivel ${nombreNivel(r.nivel)}, semilla ${r.semilla}`;
      const ult = el("td"); ult.append(jugar);
      const td = (t) => el("td", "", t);
      tr.append(td(r.planeta), td(nombreNivel(r.nivel)), td(nombreTamano(r.tamano).replace(/ \(.*/, "")), td(String(r.semilla)),
        td(Vehiculo(r.vehiculo)), quien, td(textoResultado(r)), td(String(r.puntaje)), td(String(r.pasos)), td(textoBateria(r)),
        td(verTodos ? fechaLegible(r.fecha) : `${r.exitos} de ${r.intentos}`), ult);
      cuerpo.append(tr);
    }
    tabla.append(th, cuerpo);
    const caja = el("div", "lab-scroll vx-scroll"); caja.append(tabla);
    tablaCaja.replaceChildren(caja);
  }

  function pedirBorrado() {
    if (!ultimo || ultimo.total === 0) return;
    confirmacion.replaceChildren(el("span", "", textoBorrado(ultimo.total)),
      boton("Sí, borrar todo", "peligro", async () => {
        try {
          const r = await fetch("/records", { method: "DELETE" });
          if (!r.ok) throw new Error(String(r.status));
        } catch (e) { confirmacion.replaceChildren(el("span", "", "No se pudo borrar: el motor no responde.")); return; }
        confirmacion.classList.add("oculto");
        await cargar();
      }),
      boton("Cancelar", "secundario", () => { confirmacion.classList.add("oculto"); borrar.focus(); }));
    confirmacion.classList.remove("oculto");
    confirmacion.querySelector("button.secundario").focus();
  }

  return {
    abrir({ planeta = "", semilla = "" } = {}) {
      confirmacion.classList.add("oculto");
      filtros.planeta = planeta || "";
      filtros.semilla = semilla === null || semilla === undefined ? "" : String(semilla);
      cSemilla.value = filtros.semilla;
      capa.abrir();
      cargar();
    },
    cerrar: capa.cerrar,
    get visible() { return capa.visible; },
  };
}
