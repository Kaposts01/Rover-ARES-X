// Sonido procedural con Web Audio (sin archivos): motor según la velocidad, veto, replanteo, choque, sitio y meteorito.
// Apagado por defecto: el navegador solo permite audio tras un gesto del usuario (el botón de la barra).
// Nunca lanza: si Web Audio no está disponible, el juego sigue en silencio.

export function crearSonido() {
  let ctx = null, maestro = null, activo = false;

  function asegurar() {
    if (ctx) return true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    ctx = new AC();
    maestro = ctx.createGain(); maestro.gain.value = 0.25; maestro.connect(ctx.destination);
    return true;
  }
  function tono(frec, dur, { tipo = "sine", vol = 0.5, hasta = null, retraso = 0 } = {}) {
    if (!activo || !ctx) return;
    const t0 = ctx.currentTime + retraso;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = tipo; o.frequency.setValueAtTime(frec, t0);
    if (hasta) o.frequency.exponentialRampToValueAtTime(hasta, t0 + dur);
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(vol, t0 + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g); g.connect(maestro); o.start(t0); o.stop(t0 + dur + 0.05);
  }
  function ruido(dur, { vol = 0.4, filtro = 400 } = {}) {
    if (!activo || !ctx) return;
    const n = Math.floor(ctx.sampleRate * dur), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = ctx.createBufferSource(); s.buffer = b;
    const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = filtro;
    const g = ctx.createGain(); g.gain.value = vol;
    s.connect(f); f.connect(g); g.connect(maestro); s.start();
  }

  // Un paso de la IA: r = respuesta de POST /paso; antes/despues = estado (para detectar sitios nuevos)
  function paso(r, antes, despues) {
    if (!activo || !r) return;
    try {
      const motivos = (r.motivos || []).join(";");
      const vel = Number((r.ultimo && r.ultimo.velocidad) ?? 0.5);
      if (r.accion === "avanzar") tono(70 + vel * 60, 0.45, { tipo: "sawtooth", vol: 0.08 + vel * 0.1, hasta: 60 + vel * 50 });
      if (/V-CELDA-BLOQUEADA/.test(motivos)) ruido(0.25, { vol: 0.6, filtro: 220 });
      else if (/(^|;)V-/.test(motivos)) { tono(880, 0.12, { tipo: "square", vol: 0.12 }); tono(660, 0.16, { tipo: "square", vol: 0.12, retraso: 0.13 }); }
      if (r.accion === "replanificar" || /REPLAN/.test(motivos)) tono(520, 0.18, { vol: 0.2, hasta: 780 });
      if (antes && despues && (despues.sitios_visitados || 0) > (antes.sitios_visitados || 0)) {
        [523, 659, 784].forEach((f, i) => tono(f, 0.5, { vol: 0.22, retraso: i * 0.09 }));
      }
      const nuevos = despues && antes ? (despues.avisos || []).slice((antes.avisos || []).length) : [];
      if (nuevos.some((a) => /meteorito/i.test(String(a))) || /METEORITO/.test(motivos)) ruido(1.2, { vol: 0.7, filtro: 160 });
      if (nuevos.some((a) => /sismo/i.test(String(a)))) ruido(1.6, { vol: 0.6, filtro: 90 });
    } catch (e) { /* el sonido nunca corta la partida */ }
  }
  function fin(exito) {
    if (!activo) return;
    const notas = exito ? [523, 659, 784, 1047] : [392, 311, 262];
    notas.forEach((f, i) => tono(f, 0.6, { vol: 0.25, retraso: i * 0.15, tipo: exito ? "sine" : "triangle" }));
  }
  function alternar() {
    if (!asegurar()) return false;
    activo = !activo;
    if (activo && ctx.state === "suspended") ctx.resume();
    if (activo) tono(660, 0.15, { vol: 0.2 });
    return activo;
  }
  return { paso, fin, alternar, get activo() { return activo; } };
}
