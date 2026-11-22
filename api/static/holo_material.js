// Materiales del estilo «sala de control» (holograma): planetas, Sol, órbitas, rejilla y barrido de radar.
// Los comparten la intro (sistema solar) y el viaje con el cohete. Solo dependen de THREE; todo se genera en shaders.

export const CIAN_HOLO = 0x5fe6ff;

// Planeta holográfico: textura tenue, lado nocturno, borde fresnel cian, meridianos y paralelos, línea de escaneo.
export function materialPlanetaHolo(THREE, { color = 0x88aacc, mapa = null } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uMapa: { value: mapa }, uConMapa: { value: mapa ? 1 : 0 },
      uColor: { value: new THREE.Color(color) }, uCian: { value: new THREE.Color(CIAN_HOLO) },
      uTiempo: { value: 0 }, uResalte: { value: 0 },
    },
    vertexShader: /* glsl */`
      varying vec2 vUv; varying vec3 vN; varying vec3 vV; varying vec3 vMundo; varying vec3 vNMundo; varying float vY;
      void main() {
        vUv = uv; vY = position.y;
        vec4 m = modelMatrix * vec4(position, 1.0); vMundo = m.xyz;
        vNMundo = normalize(mat3(modelMatrix) * normal);
        vec4 mv = viewMatrix * m; vV = normalize(-mv.xyz); vN = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uMapa; uniform float uConMapa; uniform vec3 uColor; uniform vec3 uCian; uniform float uTiempo; uniform float uResalte;
      varying vec2 vUv; varying vec3 vN; varying vec3 vV; varying vec3 vMundo; varying vec3 vNMundo; varying float vY;
      // línea de ~1 px en cada entero de x·n (fwidth la mantiene fina a cualquier distancia)
      float linea(float x, float n) { float v = x * n; float d = abs(fract(v - 0.5) - 0.5); return 1.0 - smoothstep(0.0, fwidth(v) * 1.2, d); }
      void main() {
        vec3 base = uColor;
        if (uConMapa > 0.5) base = mix(uColor, texture2D(uMapa, vUv * vec2(2.0, 1.0)).rgb, 0.5);
        vec3 L = normalize(-vMundo);                         // el Sol está en el origen
        float dia = clamp(dot(vNMundo, L), 0.0, 1.0);
        float luz = 0.18 + 0.95 * dia;
        float fres = pow(1.0 - clamp(dot(vN, vV), 0.0, 1.0), 2.4);
        float rejilla = max(linea(vUv.x + uTiempo * 0.01, 18.0), linea(vUv.y, 9.0));
        float banda = exp(-pow((fract(vUv.y - uTiempo * 0.08) - 0.5) * 24.0, 2.0));
        float parpadeo = 0.96 + 0.04 * sin(uTiempo * 23.0 + vY * 4.0);
        vec3 c = mix(base, uCian * 0.55, 0.22) * luz * 0.75;
        c += uCian * (fres * (0.9 + uResalte * 0.9) + rejilla * (0.22 + 0.3 * uResalte) * (0.35 + dia) + banda * 0.10);
        c *= parpadeo;
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`,
    extensions: { derivatives: true },
  });
}

// Halo de atmósfera: cáscara aditiva del lado trasero (solo el borde brilla).
export function materialHaloHolo(THREE, color = CIAN_HOLO, fuerza = 0.8) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uFuerza: { value: fuerza } },
    vertexShader: /* glsl */`varying vec3 vN; varying vec3 vV;
      void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: /* glsl */`uniform vec3 uColor; uniform float uFuerza; varying vec3 vN; varying vec3 vV;
      void main() { float f = pow(clamp(1.0 + dot(vN, vV) * 1.0, 0.0, 1.0), 3.0); gl_FragColor = vec4(uColor * f * uFuerza, f * uFuerza); }`,
    side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
}

// Sol: plasma animado (ruido) del amarillo al blanco, con borde cian muy leve para casar con el resto.
export function materialSolHolo(THREE) {
  return new THREE.ShaderMaterial({
    uniforms: { uTiempo: { value: 0 } },
    vertexShader: /* glsl */`varying vec3 vP; varying vec3 vN; varying vec3 vV;
      void main() { vP = position; vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: /* glsl */`uniform float uTiempo; varying vec3 vP; varying vec3 vN; varying vec3 vV;
      float h(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float r(vec3 p) { vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                   mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
      void main() {
        vec3 p = normalize(vP) * 2.2;
        float n = r(p + uTiempo * 0.15) * 0.55 + r(p * 2.3 - uTiempo * 0.22) * 0.3 + r(p * 5.1 + uTiempo * 0.4) * 0.15;
        float borde = pow(1.0 - clamp(dot(vN, vV), 0.0, 1.0), 2.0);
        vec3 c = mix(vec3(1.0, 0.55, 0.12), vec3(1.0, 0.95, 0.75), smoothstep(0.35, 0.85, n));
        c += vec3(0.37, 0.9, 1.0) * borde * 0.35;
        gl_FragColor = vec4(c * 1.15, 1.0);
        #include <colorspace_fragment>
      }`,
  });
}

// Órbita: trazo discontinuo que avanza. La geometría lleva el atributo «aRecorrido» (0..1 a lo largo de la vuelta).
export function materialOrbitaHolo(THREE, color = CIAN_HOLO) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uTiempo: { value: 0 }, uResalte: { value: 0 }, uTramos: { value: 90 } },
    vertexShader: /* glsl */`attribute float aRecorrido; varying float vR; void main() { vR = aRecorrido; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`uniform vec3 uColor; uniform float uTiempo; uniform float uResalte; uniform float uTramos; varying float vR;
      void main() { float d = step(0.45, fract(vR * uTramos - uTiempo * 0.6)); float a = mix(0.3, 0.85, uResalte) * mix(0.35, 1.0, d);
        gl_FragColor = vec4(uColor, a); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
}

export function geometriaOrbita(THREE, radio, segmentos = 256) {
  const pos = new Float32Array(segmentos * 3), rec = new Float32Array(segmentos);
  for (let i = 0; i < segmentos; i++) {
    const a = (i / segmentos) * Math.PI * 2;
    pos.set([Math.cos(a) * radio, 0, Math.sin(a) * radio], i * 3); rec[i] = i / segmentos;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aRecorrido", new THREE.BufferAttribute(rec, 1));
  return g;
}

// Barrido de radar sobre el plano orbital: disco cuyo brillo decae detrás del haz que gira.
export function materialBarridoHolo(THREE, color = CIAN_HOLO) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uAngulo: { value: 0 } },
    vertexShader: /* glsl */`varying vec2 vP; void main() { vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`uniform vec3 uColor; uniform float uAngulo; varying vec2 vP;
      void main() { float a = atan(vP.y, vP.x); float d = mod(uAngulo - a, 6.28318); float estela = exp(-d * 2.2);
        float r = length(vP); float bordes = smoothstep(1.0, 0.96, r) * smoothstep(0.0, 0.12, r);
        gl_FragColor = vec4(uColor, estela * 0.16 * bordes); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
}

// Estrellas con titileo: tamaño y fase por estrella.
export function materialEstrellasHolo(THREE, { tam = 1.6, color = 0xcfe8ff } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: { uTiempo: { value: 0 }, uTam: { value: tam }, uColor: { value: new THREE.Color(color) }, uEscala: { value: 1 } },
    vertexShader: /* glsl */`attribute float aFase; uniform float uTiempo; uniform float uTam; uniform float uEscala; varying float vBrillo;
      void main() { vBrillo = 0.55 + 0.45 * sin(uTiempo * (1.0 + aFase) + aFase * 30.0);
        gl_PointSize = uTam * uEscala * (0.6 + aFase * 0.8); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`uniform vec3 uColor; varying float vBrillo;
      void main() { vec2 q = gl_PointCoord - 0.5; float a = smoothstep(0.5, 0.0, length(q)); gl_FragColor = vec4(uColor * vBrillo, a * vBrillo); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
}

export function geometriaEstrellas(THREE, n, rMin, rMax) {
  const p = new Float32Array(n * 3), f = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const r = rMin + Math.random() * (rMax - rMin), a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1);
    p.set([r * Math.sin(b) * Math.cos(a), r * Math.cos(b), r * Math.sin(b) * Math.sin(a)], i * 3); f[i] = Math.random();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(p, 3));
  g.setAttribute("aFase", new THREE.BufferAttribute(f, 1));
  return g;
}

// Retícula de selección: cuatro arcos que giran alrededor del planeta señalado (siempre de cara a la cámara).
export function crearReticula(THREE, color = CIAN_HOLO) {
  const grupo = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
  const geos = [];
  for (let i = 0; i < 4; i++) {
    const g = new THREE.RingGeometry(1.25, 1.33, 24, 1, i * Math.PI / 2 + 0.25, Math.PI / 2 - 0.5);
    geos.push(g); grupo.add(new THREE.Mesh(g, mat));
  }
  const gInt = new THREE.RingGeometry(1.08, 1.1, 64); geos.push(gInt);
  const interior = new THREE.Mesh(gInt, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide }));
  grupo.add(interior);
  grupo.visible = false;
  grupo.userData.recursos = [mat, interior.material, ...geos];
  return grupo;
}
