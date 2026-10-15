// Clima: cielo despejado <-> nublado (dos HDRI reales), sol, niebla, humedad y charcos, lluvia con
// salpicaduras, rayos y truenos. Las transiciones son graduales; el modo automatico cambia el clima
// cada pocos minutos como en una tarde de Bogota.
import * as THREE from 'three';
import { G } from './materials.js';

export const PRESETS = {
  soleado: { label: 'Soleado', sky: 0, dark: 1, sun: 1, vis: 10000, wet: 0, rain: 0, ev: 0, lights: 0, wind: 0.15 },
  nublado: { label: 'Nublado', sky: 1, dark: 0.85, sun: 0.1, vis: 4500, wet: 0, rain: 0, ev: 0.45, lights: 0.15, wind: 0.3 },
  lluvia: { label: 'Lluvia', sky: 1, dark: 0.5, sun: 0, vis: 1400, wet: 1, rain: 0.6, ev: 0.85, lights: 0.6, wind: 0.45 },
  tormenta: { label: 'Tormenta', sky: 1, dark: 0.3, sun: 0, vis: 750, wet: 1, rain: 1, ev: 1.15, lights: 1, wind: 0.8, lightning: 1 },
  niebla: { label: 'Niebla', sky: 1, dark: 0.92, sun: 0.04, vis: 170, wet: 0.35, rain: 0, ev: 0.55, lights: 0.8, wind: 0.05 },
};
const NEXT = {
  soleado: [['soleado', 0.35], ['nublado', 0.65]],
  nublado: [['lluvia', 0.45], ['soleado', 0.35], ['niebla', 0.2]],
  lluvia: [['nublado', 0.55], ['tormenta', 0.3], ['lluvia', 0.15]],
  tormenta: [['lluvia', 1]],
  niebla: [['nublado', 1]],
};

export function makeSkyDome(texA, texB, scale, gamma) {
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      tSky: { value: texA }, tSky2: { value: texB }, uScale: { value: scale }, uGamma: { value: gamma },
      uMix: { value: 0 }, uDark: { value: 1 }, uFlash: { value: 0 }, uFogColor: { value: new THREE.Color() }, uFogAmt: { value: 0 },
    },
    vertexShader: `varying vec3 vDir;
      void main(){ vDir = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p; }`,
    fragmentShader: `varying vec3 vDir; uniform sampler2D tSky, tSky2; uniform float uScale, uGamma, uMix, uDark, uFlash, uFogAmt; uniform vec3 uFogColor;
      #include <common>
      void main(){
        vec3 d = normalize(vDir);
        vec2 uv = vec2(atan(d.z, d.x) * RECIPROCAL_PI2 + 0.5, asin(clamp(d.y, -1.0, 1.0)) * RECIPROCAL_PI + 0.5);
        vec3 a = uScale * pow(texture2D(tSky, uv).rgb, vec3(uGamma));
        vec3 b = uScale * pow(texture2D(tSky2, uv).rgb, vec3(uGamma)) * uDark;
        vec3 c = mix(a, b, uMix) * (1.0 + uFlash);
        float h = 1.0 - smoothstep(-0.03, 0.1 + 0.6 * uFogAmt, d.y);
        c = mix(c, uFogColor, clamp(uFogAmt * (0.35 + 0.65 * h), 0.0, 1.0));
        gl_FragColor = vec4(c, 1.0);
      }`,
    side: THREE.BackSide, depthWrite: false, depthTest: false, fog: false,
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1000, 64, 32), mat);
  dome.frustumCulled = false;
  dome.renderOrder = -100;
  dome.onBeforeRender = (r, s, cam) => { dome.position.copy(cam.position); };
  return dome;
}

// mezcla los dos HDRI de iluminacion y regenera el PMREM (solo cuando cambia)
class EnvBlend {
  constructor(renderer, hdrA, hdrB) {
    this.renderer = renderer;
    this.rt = new THREE.WebGLRenderTarget(1024, 512, { type: THREE.HalfFloatType, depthBuffer: false });
    this.rt.texture.mapping = THREE.EquirectangularReflectionMapping;
    this.mat = new THREE.ShaderMaterial({
      uniforms: { a: { value: hdrA }, b: { value: hdrB }, uMix: { value: 0 }, uDark: { value: 1 }, uFog: { value: 0 }, uFogColor: { value: new THREE.Color() } },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: `varying vec2 vUv; uniform sampler2D a, b; uniform float uMix, uDark, uFog; uniform vec3 uFogColor;
        void main(){ vec3 c = mix(texture2D(a, vUv).rgb, texture2D(b, vUv).rgb * uDark, uMix);
          float el = (vUv.y - 0.5) * 3.14159;
          c = mix(c, uFogColor, uFog * (1.0 - smoothstep(0.0, 1.2, abs(el))));
          gl_FragColor = vec4(c, 1.0); }`,
      depthTest: false, depthWrite: false,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mat);
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.scene = new THREE.Scene(); this.scene.add(this.quad);
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.out = null;
    this.key = '';
  }
  update(mix, dark, fog, fogColor) {
    const q = (x) => Math.round(x * 20) / 20;   // regenerar solo en pasos de 5 %
    mix = q(mix); dark = q(dark); fog = q(fog);
    const k = `${mix}|${dark}|${fog}`;
    if (k === this.key && this.out) return null;
    this.key = k;
    Object.assign(this.mat.uniforms.uMix, { value: mix });
    this.mat.uniforms.uDark.value = dark; this.mat.uniforms.uFog.value = fog; this.mat.uniforms.uFogColor.value.copy(fogColor);
    const r = this.renderer, prev = r.getRenderTarget(), tm = r.toneMapping;
    r.toneMapping = THREE.NoToneMapping;
    r.setRenderTarget(this.rt); r.render(this.scene, this.cam); r.setRenderTarget(prev);
    r.toneMapping = tm;
    this.out = this.pmrem.fromEquirectangular(this.rt.texture, this.out);
    return this.out.texture;
  }
}

function rainSystem() {
  const N = 14000;
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([-0.5, 0, 0, 0.5, 0, 0, 0.5, 1, 0, -0.5, 1, 0], 3));
  g.setIndex([0, 1, 2, 0, 2, 3]);
  const off = new Float32Array(N * 4);
  for (let i = 0; i < N * 4; i++) off[i] = Math.random();
  g.setAttribute('aOff', new THREE.InstancedBufferAttribute(off, 4));
  g.instanceCount = N;
  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uCam: { value: new THREE.Vector3() }, uBox: { value: new THREE.Vector3(44, 24, 44) },
      uWind: { value: new THREE.Vector2(0.6, 0.3) }, uColor: { value: new THREE.Color(0.55, 0.6, 0.66) }, uAmt: { value: 0 } },
    vertexShader: `attribute vec4 aOff; uniform float uTime, uAmt; uniform vec3 uCam, uBox; uniform vec2 uWind; varying float vA;
      void main(){
        float speed = 8.5 + aOff.w * 2.0;
        vec3 vel = vec3(uWind.x, -speed, uWind.y);
        vec3 lo = uCam - uBox * 0.5;
        vec3 p = aOff.xyz * uBox + vel * uTime;
        p = mod(p - lo, uBox) + lo;
        vec3 dirv = normalize(vel);
        vec3 toCam = cameraPosition - p; float dist = length(toCam);
        vec3 side = normalize(cross(dirv, toCam / max(dist, 1e-3)));
        float w = max(0.011, dist * 0.0022);
        vec3 wp = p + side * position.x * w - dirv * position.y * 0.85;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
        float edge = 1.0 - smoothstep(0.35, 0.5, max(abs(p.x - uCam.x) / uBox.x, abs(p.z - uCam.z) / uBox.z));
        vA = step(aOff.w, uAmt) * edge * (0.011 / w) * (0.25 + 0.75 * position.y) * smoothstep(0.4, 2.0, dist);
      }`,
    fragmentShader: 'uniform vec3 uColor; varying float vA; void main(){ gl_FragColor = vec4(uColor, vA * 0.7); }',
    transparent: true, depthWrite: false,
  });
  const m = new THREE.Mesh(g, mat);
  m.frustumCulled = false; m.renderOrder = 10; m.visible = false;
  return m;
}

function splashSystem() {
  const N = 900;
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([-1, 0, -1, 1, 0, -1, 1, 0, 1, -1, 0, 1], 3));
  g.setIndex([0, 2, 1, 0, 3, 2]);
  const off = new Float32Array(N * 3);
  for (let i = 0; i < N * 3; i++) off[i] = Math.random();
  g.setAttribute('aOff', new THREE.InstancedBufferAttribute(off, 3));
  g.instanceCount = N;
  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uCam: { value: new THREE.Vector3() }, uGround: { value: 0 }, uAmt: { value: 0 }, uColor: { value: new THREE.Color(0.6, 0.65, 0.7) } },
    vertexShader: `attribute vec3 aOff; uniform float uTime, uGround, uAmt; uniform vec3 uCam; varying vec2 vP; varying float vT, vOn;
      void main(){
        float box = 26.0; vec2 lo = uCam.xz - box * 0.5;
        float t = fract(uTime * 1.7 + aOff.z);
        float cyc = floor(uTime * 1.7 + aOff.z);
        vec2 j = fract(vec2(sin(cyc * 12.9 + aOff.x * 78.2), sin(cyc * 4.1 + aOff.y * 37.7)) * 43758.5);
        vec2 xz = mod(aOff.xy * box + j * 3.0 - lo, box) + lo;
        float r = 0.01 + t * 0.07;
        vec3 wp = vec3(xz.x + position.x * r, uGround + 0.025, xz.y + position.z * r);
        vP = position.xz; vT = t; vOn = step(aOff.z, uAmt);
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: `uniform vec3 uColor; varying vec2 vP; varying float vT, vOn;
      void main(){ float d = length(vP); float ring = smoothstep(0.75, 0.9, d) * (1.0 - smoothstep(0.9, 1.0, d));
        gl_FragColor = vec4(uColor, ring * (1.0 - vT) * (1.0 - vT) * 0.22 * vOn); }`,
    transparent: true, depthWrite: false,
  });
  const m = new THREE.Mesh(g, mat);
  m.frustumCulled = false; m.renderOrder = 9; m.visible = false;
  return m;
}

export class Weather {
  /** env: { renderer, scene, sun, skyDome, hdrA, hdrB, fogA (Color), fogB (Color), baseSun, baseExposure } */
  constructor(env) {
    this.env = env;
    this.blend = new EnvBlend(env.renderer, env.hdrA, env.hdrB);
    this.cur = { ...PRESETS.soleado };
    this.target = PRESETS.soleado;
    this.name = 'soleado';
    this.auto = false;
    this.autoT = 200;
    this.wet = 0; this.puddles = 0;
    this.flash = 0; this.nextBolt = 8; this.boltSeq = [];
    this.rain = rainSystem(); this.splash = splashSystem();
    env.scene.add(this.rain, this.splash);
    this.bolt = new THREE.DirectionalLight(0xc8d4ff, 0);
    env.scene.add(this.bolt, this.bolt.target);
    this.fogColor = new THREE.Color();
    this.onThunder = null;
    this.onChange = null;
    this.envTexture = null;
  }

  set(name) {
    if (!PRESETS[name]) return;
    this.name = name; this.target = PRESETS[name];
    this.onChange?.(name);
  }

  setAuto(on) { this.auto = on; this.autoT = 150 + Math.random() * 90; }

  update(dt, ctx) {
    const c = this.cur, t = this.target, e = this.env;
    const k = 1 - Math.exp(-dt / 6), kr = 1 - Math.exp(-dt / 3);
    for (const f of ['sky', 'dark', 'sun', 'ev', 'lights', 'wind']) c[f] += (t[f] - c[f]) * k;
    c.vis = Math.exp(Math.log(c.vis) + (Math.log(t.vis) - Math.log(c.vis)) * k);
    c.rain += (t.rain - c.rain) * kr;
    // humedad: se moja en ~25 s y se seca en ~2 min
    const wt = Math.max(t.wet, c.rain > 0.1 ? 1 : 0);
    this.wet += (wt - this.wet) * (1 - Math.exp(-dt / (wt > this.wet ? 25 : 110)));
    const pt = c.rain > 0.1 ? Math.min(1, this.wet * 1.2) : this.puddles * 0.999;
    this.puddles += (pt - this.puddles) * (1 - Math.exp(-dt / (pt > this.puddles ? 40 : 150)));
    G.uWet.value = this.wet; G.uPuddles.value = this.puddles; G.uRain.value = c.rain;

    // cielo, sol, niebla
    const dome = e.skyDome.material.uniforms;
    dome.uMix.value = c.sky; dome.uDark.value = c.dark;
    this.fogColor.copy(e.fogA).lerp(e.fogB, c.sky).multiplyScalar(THREE.MathUtils.lerp(1, c.dark, c.sky) * (1 + this.flash * 0.6));
    const fogAmt = THREE.MathUtils.clamp(1 - (c.vis - 150) / 2500, 0, 1);
    dome.uFogColor.value.copy(this.fogColor); dome.uFogAmt.value = fogAmt;
    e.scene.fog.color.copy(this.fogColor);
    e.scene.fog.density = 1.73 / c.vis;
    e.sun.intensity = e.baseSun * c.sun;
    e.sun.castShadow = c.sun > 0.03;
    e.renderer.toneMappingExposure = e.baseExposure * Math.pow(2, c.ev);
    const tex = this.blend.update(c.sky, c.dark, fogAmt * 0.8, this.fogColor);
    if (tex) { this.envTexture = tex; if (!ctx.pathTracing) e.scene.environment = tex; }
    e.scene.environmentIntensity = 1 + this.flash * 2.5;

    // lluvia
    const cam = ctx.camera.position;
    this.rain.visible = this.splash.visible = c.rain > 0.02 && !ctx.pathTracing;
    const ru = this.rain.material.uniforms, su = this.splash.material.uniforms;
    ru.uTime.value += dt; su.uTime.value += dt;
    ru.uCam.value.copy(cam); su.uCam.value.copy(cam);
    ru.uAmt.value = c.rain; su.uAmt.value = c.rain * (ctx.groundY !== undefined ? 1 : 0);
    ru.uWind.value.set(1.5 * c.wind, 0.8 * c.wind);
    su.uGround.value = ctx.groundY ?? 0;
    const sky = THREE.MathUtils.lerp(1, c.dark, c.sky);
    ru.uColor.value.setRGB(0.5, 0.55, 0.6).multiplyScalar(0.5 + sky * 0.8 + this.flash * 2);

    // rayos
    if ((t.lightning || 0) > 0 && c.rain > 0.7) {
      this.nextBolt -= dt;
      if (this.nextBolt <= 0) {
        this.nextBolt = 6 + Math.random() * 14;
        const n = 1 + ((Math.random() * 3) | 0);
        let tt = 0;
        for (let i = 0; i < n; i++) { this.boltSeq.push([tt, 0.06 + Math.random() * 0.1, 1.5 + Math.random() * 2.5]); tt += 0.1 + Math.random() * 0.25; }
        const a = Math.random() * Math.PI * 2;
        this.bolt.position.set(Math.cos(a) * 300, 400, Math.sin(a) * 300).add(cam);
        this.bolt.target.position.copy(cam);
        const delay = 0.4 + Math.random() * 4;
        setTimeout(() => this.onThunder?.(delay), delay * 1000);
      }
    }
    this.flash = 0;
    for (const b of this.boltSeq) {
      b[0] -= dt;
      if (b[0] <= 0 && b[0] > -b[1]) this.flash = Math.max(this.flash, b[2]);
    }
    this.boltSeq = this.boltSeq.filter((b) => b[0] > -b[1]);
    this.bolt.intensity = this.flash * 6;
    dome.uFlash.value = this.flash * 0.8;

    // clima automatico
    if (this.auto) {
      this.autoT -= dt;
      if (this.autoT <= 0) {
        this.autoT = 150 + Math.random() * 120;
        const opts = NEXT[this.name];
        let r = Math.random();
        for (const [n, p] of opts) { r -= p; if (r <= 0) { this.set(n); break; } }
      }
    }
    return c;
  }
}
