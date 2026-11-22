// Cine: postproceso (bloom, bokeh y viñeta ligera). Recibe THREE y las clases de los passes cargadas con import().
// Si algo falla, quien lo llama vuelve a renderer.render. Mide sus propios cuadros y se apaga si el equipo no rinde.
import { crearMonitorFps, UMBRAL_FPS } from "/static/cine_datos.js?v=r14";

const VINETA = {
  uniforms: { tDiffuse: { value: null }, intensidad: { value: 0.22 } },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
  fragmentShader: "uniform sampler2D tDiffuse; uniform float intensidad; varying vec2 vUv;"
    + " void main(){ vec4 c = texture2D(tDiffuse, vUv); float d = distance(vUv, vec2(0.5)); c.rgb *= 1.0 - intensidad * smoothstep(0.35, 0.8, d); gl_FragColor = c; }",
};

export function crearPostproceso({ THREE, renderer, clases, umbral = UMBRAL_FPS, ventana, alApagarSolo }) {
  const { EffectComposer, RenderPass, UnrealBloomPass, BokehPass, ShaderPass, OutputPass } = clases;
  const tam = renderer.getSize(new THREE.Vector2());
  const pr = renderer.getPixelRatio();
  const composer = new EffectComposer(renderer);
  composer.setPixelRatio(pr);
  composer.setSize(tam.x, tam.y);
  const pase = new RenderPass(null, null);
  const bloom = new UnrealBloomPass(new THREE.Vector2(tam.x, tam.y), 0.45, 0.6, 0.85);   // moderado
  let bokeh = null;
  const vineta = new ShaderPass(VINETA);
  const salida = new OutputPass();   // aplica el ACES y el espacio sRGB del renderer
  composer.addPass(pase);
  composer.addPass(bloom);
  composer.addPass(vineta);
  composer.addPass(salida);
  let activo = true, bokehActivo = false, ultimo = 0, enApagado = false;
  const monitor = crearMonitorFps(ventana ? { ventana, umbral } : { umbral });

  function setBokeh(v, escena, camara) {
    if (v && !bokeh) {
      bokeh = new BokehPass(escena, camara, { focus: 10, aperture: 0.00015, maxblur: 0.004 });   // desenfoque leve
      composer.insertPass(bokeh, 1);
    }
    if (bokeh) bokeh.enabled = !!v;
    bokehActivo = !!v;
  }

  return {
    get activo() { return activo; },
    get bokehActivo() { return bokehActivo; },
    setBokeh,
    // enfoque: distancia de la cámara al rover
    render(escena, camara, enfoque) {
      if (!activo) { renderer.render(escena, camara); return; }
      pase.scene = escena; pase.camera = camara;
      if (bokeh) { bokeh.scene = escena; bokeh.camera = camara; if (enfoque > 0) bokeh.uniforms["focus"].value = enfoque; }
      const t0 = performance.now();
      composer.render();
      const ahora = performance.now();
      if (ultimo && !enApagado && monitor.empujar(ahora - ultimo) === "apagar") {
        enApagado = true;
        try { if (alApagarSolo) alApagarSolo(); } catch (e) { console.warn("cine: fallo al apagar el postproceso", e); }
      }
      ultimo = ahora;
      return ahora - t0;
    },
    ajustar(w, h) { composer.setSize(w, h); },
    reiniciarMedicion() { ultimo = 0; monitor.reiniciar(); },
    dispose() {
      activo = false;
      for (const p of composer.passes) { try { if (p.dispose) p.dispose(); } catch (e) { /* ya liberado */ } }
      try { composer.dispose(); } catch (e) { /* ya liberado */ }
      bokeh = null;
    },
  };
}
