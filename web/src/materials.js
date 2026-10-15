// Materiales PBR del simulador: texturas escaneadas (Poly Haven, CC0) con
//  - relieve por parallax (POM) usando la altura guardada en el canal B del mapa "arh"
//  - oclusion ambiental (canal R) y rugosidad (canal G) del mismo mapa
//  - variacion de color a gran escala y suciedad cerca del suelo (rompen la repeticion)
//  - humedad, charcos y ondas de lluvia controlados por el clima (uniformes compartidos G)
import * as THREE from 'three';

export const G = {
  uTime: { value: 0 },
  uWet: { value: 0 },       // 0 seco .. 1 empapado
  uPuddles: { value: 0 },   // extension de los charcos
  uRain: { value: 0 },      // intensidad de la lluvia (ondas en los charcos)
  uPom: { value: 1 },       // 1 = relieve parallax activo (calidad alta)
  // nucleo modelado en Blender (u0, u1, v0, v1): ahi el terreno no se dibuja (evita superposiciones)
  uCore: { value: new THREE.Vector4(-56.0, 61.5, -68.0, 67.5) },
};

let BASE = 'scene/';
let maxAniso = 8;
const texLoader = new THREE.TextureLoader();
const cache = new Map();
export const allMaterials = [];

export function initMaterials(base, renderer) {
  BASE = base;
  maxAniso = renderer.capabilities.getMaxAnisotropy();
}

export function loadTex(path, srgb) {
  const key = path + (srgb ? '#s' : '');
  if (!cache.has(key)) {
    const t = texLoader.load(BASE + path);
    t.flipY = false;                       // los UV de glTF ya vienen invertidos en v
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = maxAniso;
    cache.set(key, t);
  }
  return cache.get(key);
}

export function texRepeat(path, srgb, tile) {
  const base = loadTex(path, srgb);
  if (!tile) return base;
  const key = `${path}#${srgb ? 's' : 'l'}#${tile[0]}x${tile[1]}`;
  if (!cache.has(key)) {
    const t = base.clone();                // comparte la imagen; solo cambia la repeticion
    t.repeat.set(1 / tile[0], 1 / tile[1]);
    t.needsUpdate = true;
    cache.set(key, t);
  }
  return cache.get(key);
}

// ------------------------------------------------------------------ GLSL
const GLSL_COMMON = /* glsl */`
varying vec3 vWPos;
varying vec3 vWNrm;
uniform float uTime, uWet, uPuddles, uRain, uPom, uGrime, uPomDepth, uBay, uSeed, uTileM;
uniform vec4 uCore;
float gWet = 0.0;
float gPud = 0.0;
float gWin = 0.0;
float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y);
}
`;

const POM = /* glsl */`
#ifdef USE_MAP
  vec2 pomUv = vMapUv;
#else
  vec2 pomUv = vec2(0.0);
#endif
#ifdef DISCARD_CORE
  if (vWPos.x > uCore.x && vWPos.x < uCore.y && -vWPos.z > uCore.z && -vWPos.z < uCore.w) discard;
#endif
#if defined(USE_POM) && defined(USE_MAP) && defined(USE_ROUGHNESSMAP)
  {
    float dist = length(vViewPosition);
    float fade = (1.0 - smoothstep(10.0, 26.0, dist)) * uPom;
    if (fade > 0.001) {
      vec3 V = normalize(vViewPosition);
      vec3 Ng = normalize(vNormal);
      vec3 q0 = dFdx(-vViewPosition), q1 = dFdy(-vViewPosition);
      vec2 st0 = dFdx(vMapUv), st1 = dFdy(vMapUv);
      vec3 q1perp = cross(q1, Ng), q0perp = cross(Ng, q0);
      vec3 T = q1perp * st0.x + q0perp * st1.x;
      vec3 B = q1perp * st0.y + q0perp * st1.y;
      float det = max(dot(T, T), dot(B, B));
      float sc = det == 0.0 ? 0.0 : inversesqrt(det);
      T *= sc; B *= sc;
      vec3 Vt = vec3(dot(V, T), dot(V, B), dot(V, Ng));
      if (Vt.z > 0.05) {
        float nl = mix(28.0, 8.0, Vt.z);
        vec2 P = Vt.xy / max(Vt.z, 0.2) * uPomDepth * fade;
        vec2 dUV = P / nl;
        float layer = 1.0 / nl, cur = 0.0;
        vec2 uv = vMapUv;
        float depth = 1.0 - textureGrad(roughnessMap, uv, st0, st1).b;
        for (int i = 0; i < 28; i++) {
          if (cur >= depth || float(i) >= nl) break;
          uv -= dUV; cur += layer;
          depth = 1.0 - textureGrad(roughnessMap, uv, st0, st1).b;
        }
        vec2 prev = uv + dUV;
        float after = depth - cur;
        float before = (1.0 - textureGrad(roughnessMap, prev, st0, st1).b) - cur + layer;
        float w = after / (after - before + 1e-5);
        pomUv = mix(uv, prev, clamp(w, 0.0, 1.0));
      }
    }
  }
#endif
`;

const MAP = /* glsl */`
#ifdef USE_MAP
  diffuseColor *= texture2D(map, pomUv);
#endif
#ifdef CITY
  {
    // ventanas procedurales: vanos de uBay m, pisos de 3,1 m (UV en metros; v = 1 - altura)
    vec2 raw = vMapUv * uTileM;
    float wallMask = 1.0 - step(0.5, abs(vWNrm.y));
    vec2 q = vec2(raw.x / uBay, (1.0 - raw.y) / 3.1);
    vec2 id = floor(q), c = fract(q);
    float r = h2(id + uSeed);
    float w = step(0.2, c.x) * step(c.x, 0.8) * step(0.28, c.y) * step(c.y, 0.88);
    float inner = step(0.235, c.x) * step(c.x, 0.765) * step(0.32, c.y) * step(c.y, 0.85);
    float sill = step(0.17, c.x) * step(c.x, 0.83) * step(0.245, c.y) * step(c.y, 0.28);
    gWin = inner * wallMask;
    vec3 frameC = r < 0.55 ? vec3(0.7, 0.69, 0.66) : vec3(0.04, 0.04, 0.045);
    diffuseColor.rgb = mix(diffuseColor.rgb, frameC, clamp(w - inner + sill, 0.0, 1.0) * wallMask);
    vec3 glassC = mix(vec3(0.012, 0.014, 0.018), vec3(0.1, 0.08, 0.055), step(0.8, r));
    diffuseColor.rgb = mix(diffuseColor.rgb, glassC, gWin);
  }
#endif
  {
    float wall = 1.0 - abs(vWNrm.y);
    float big = vnoise(vWPos.xz * 0.11 + vWPos.y * 0.07) * 0.6 + vnoise(vWPos.xz * 0.37 - vWPos.y * 0.2) * 0.4;
    diffuseColor.rgb *= mix(0.88, 1.08, big);
    float ground = 1.0 - smoothstep(-0.15, 1.9, vWPos.y);
    float streak = smoothstep(0.55, 0.85, vnoise(vec2(vWPos.x * 2.3 + vWPos.z * 2.3, vWPos.y * 0.12)));
    float g = clamp(ground * 0.45 + streak * 0.18, 0.0, 0.62) * wall * uGrime;
    diffuseColor.rgb *= 1.0 - g;
    // humedad: mas en superficies horizontales; en muros, en franjas de escurrimiento
    float up = smoothstep(0.55, 0.92, vWNrm.y);
    gWet = uWet * mix(0.55 + 0.35 * streak, 1.0, up);
  #ifdef GROUND
    #ifdef USE_ROUGHNESSMAP
      float hgt = texture2D(roughnessMap, pomUv).b;
    #else
      float hgt = 0.5;
    #endif
    float pn = vnoise(vWPos.xz * 0.13) * 0.62 + vnoise(vWPos.xz * 0.47 + 7.3) * 0.38;
    float m = (1.0 - pn) * 0.78 + (1.0 - hgt) * 0.22;
    float t = 1.0 - uPuddles * 0.56;
    gPud = up * smoothstep(t, t + 0.05, m) * step(0.01, uPuddles);
  #endif
    diffuseColor.rgb *= mix(1.0, 0.58, gWet);
    diffuseColor.rgb *= mix(1.0, 0.72, gPud);
  }
`;

const ROUGH = /* glsl */`
float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
  roughnessFactor *= texture2D(roughnessMap, pomUv).g;
#endif
roughnessFactor = mix(roughnessFactor, roughnessFactor * 0.3 + 0.06, gWet);
roughnessFactor = mix(roughnessFactor, 0.025, gPud);
roughnessFactor = mix(roughnessFactor, 0.05, gWin);
`;

const NORMAL = /* glsl */`
#if defined(USE_NORMALMAP_TANGENTSPACE)
  vec3 mapN = texture2D(normalMap, pomUv).xyz * 2.0 - 1.0;
  mapN.xy *= normalScale * (1.0 - gPud * 0.95) * (1.0 - gWin);
  normal = normalize(tbn * mapN);
#endif
#ifdef GROUND
  if (gPud > 0.01 && uRain > 0.01) {
    vec2 rp = vWPos.xz * 2.4;
    vec2 cell = floor(rp);
    vec2 grad = vec2(0.0);
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec2 c = cell + vec2(float(i), float(j));
      float t = fract(uTime * 1.1 + h2(c));
      vec2 d = rp - (c + vec2(h2(c + 3.1), h2(c + 7.7)));
      float r = length(d);
      float front = t * 1.3;
      float wave = sin((r - front) * 26.0) * (1.0 - t) * smoothstep(front + 0.3, front, r) * smoothstep(front - 0.5, front, r);
      grad += d / max(r, 1e-3) * wave;
    }
    vec3 wN = normalize(vec3(-grad.x * 0.07 * uRain, 1.0, -grad.y * 0.07 * uRain));
    normal = normalize(mix(normal, normalize((viewMatrix * vec4(wN, 0.0)).xyz), gPud));
  }
#endif
`;

const AO = /* glsl */`
#ifdef USE_AOMAP
  float ambientOcclusion = (texture2D(aoMap, pomUv).r - 1.0) * aoMapIntensity + 1.0;
  reflectedLight.indirectDiffuse *= ambientOcclusion;
  #if defined(USE_ENVMAP) && defined(STANDARD)
    float dotNV = saturate(dot(geometryNormal, geometryViewDir));
    reflectedLight.indirectSpecular *= computeSpecularOcclusion(dotNV, ambientOcclusion, material.roughness);
  #endif
#endif
`;

/**
 * Inyecta en un MeshStandardMaterial el relieve, la suciedad y el clima.
 * opts: grime (0..1), pomDepth (profundidad en unidades de UV; 0 = sin parallax), ground (charcos),
 *       discardCore (terreno: no dibujar dentro del nucleo)
 */
export function enhance(mat, opts = {}) {
  const local = {
    uGrime: { value: opts.grime ?? 1 }, uPomDepth: { value: opts.pomDepth ?? 0 },
    uBay: { value: opts.bay ?? 3 }, uSeed: { value: opts.seed ?? 0 }, uTileM: { value: opts.tileM ?? 1 },
  };
  mat.defines = mat.defines || {};
  if (opts.city) mat.defines.CITY = '';
  if (opts.pomDepth > 0) mat.defines.USE_POM = '';
  if (opts.ground) mat.defines.GROUND = '';
  if (opts.discardCore) mat.defines.DISCARD_CORE = '';
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, G, local);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        {
          vec4 wp = vec4(transformed, 1.0);
          #ifdef USE_INSTANCING
            wp = instanceMatrix * wp;
          #endif
          vWPos = (modelMatrix * wp).xyz;
          vec3 on = objectNormal;
          #ifdef USE_INSTANCING
            on = mat3(instanceMatrix) * on;
          #endif
          vWNrm = normalize(mat3(modelMatrix) * on);
        }`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\n' + GLSL_COMMON)
      .replace('#include <logdepthbuf_fragment>', '#include <logdepthbuf_fragment>\n' + POM)
      .replace('#include <map_fragment>', MAP)
      .replace('#include <roughnessmap_fragment>', ROUGH)
      .replace('#include <normal_fragment_maps>', NORMAL)
      .replace('#include <aomap_fragment>', AO);
  };
  mat.customProgramCacheKey = () => `enh-${opts.pomDepth > 0}-${!!opts.ground}-${!!opts.discardCore}-${!!opts.city}`;
  return mat;
}

const GROUND_RE = /plaza|adoquin|anden|asfalto|bordillo|calzada|acera/i;
// en Blender algunas superficies tienen las caras invertidas (Cycles dibuja ambos lados)
const TWO_SIDED_RE = /adoquin|anden|asfalto|bordillo|plaza/i;
const ROOF_RE = /teja|pizarra|cupula/i;

/** Material a partir de la descripcion de scene.json */
export function makeMaterial(name, def) {
  let m;
  if (!def) def = { type: 'const', color: [0.6, 0.6, 0.6], roughness: 0.8, metalness: 0 };
  if (def.type === 'pbr') {
    const tile = def.tile;
    const arh = texRepeat(`tex/${def.tex}_arh.jpg`, false, tile);
    m = new THREE.MeshStandardMaterial({
      map: texRepeat(`tex/${def.tex}_diff.jpg`, true, tile),
      normalMap: texRepeat(`tex/${def.tex}_nor.jpg`, false, tile),
      roughnessMap: arh, aoMap: arh, aoMapIntensity: 1.0,
      roughness: 1, metalness: 0,
      color: new THREE.Color(...(def.color || [1, 1, 1])),
    });
    if (TWO_SIDED_RE.test(name)) m.side = THREE.DoubleSide;
    const ns = def.normalScale ?? 1.2;
    m.normalScale.set(ns, ns);
    const ground = GROUND_RE.test(name);
    enhance(m, {
      grime: ground || ROOF_RE.test(name) ? 0 : 1,
      pomDepth: (def.pom || 0) / tile[0],
      ground,
    });
  } else if (def.type === 'city') {
    const tile = def.tile;
    const arh = texRepeat(`tex/${def.tex}_arh.jpg`, false, tile);
    m = new THREE.MeshStandardMaterial({
      map: texRepeat(`tex/${def.tex}_diff.jpg`, true, tile),
      normalMap: texRepeat(`tex/${def.tex}_nor.jpg`, false, tile),
      roughnessMap: arh, aoMap: arh, roughness: 1, metalness: 0,
      color: new THREE.Color(...def.color),
    });
    enhance(m, { grime: 1, city: true, bay: def.bay, seed: def.seed, tileM: tile[0] });
  } else if (def.type === 'tile') {
    m = new THREE.MeshStandardMaterial({
      map: texRepeat(def.map, true, def.tile),
      roughnessMap: def.roughnessMap ? texRepeat(def.roughnessMap, false, def.tile) : null,
      roughness: 1, metalness: 0,
    });
    enhance(m, { grime: 1 });
  } else if (def.type === 'unique') {
    m = new THREE.MeshStandardMaterial({ map: loadTex(def.map, true), roughness: def.roughness ?? 0.9, metalness: 0 });
    enhance(m, { grime: 0, discardCore: /terreno/i.test(def.map) });
  } else if (def.type === 'flag') {
    const c = document.createElement('canvas');
    c.width = 6; c.height = 8;
    const g = c.getContext('2d');
    g.fillStyle = '#fcd116'; g.fillRect(0, 0, 6, 4);
    g.fillStyle = '#003893'; g.fillRect(0, 4, 6, 2);
    g.fillStyle = '#ce1126'; g.fillRect(0, 6, 6, 2);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace; t.flipY = false; t.magFilter = THREE.NearestFilter;
    m = new THREE.MeshStandardMaterial({ map: t, roughness: 0.75, side: THREE.DoubleSide });
  } else {
    m = new THREE.MeshStandardMaterial({
      color: new THREE.Color(def.color[0], def.color[1], def.color[2]),
      roughness: def.roughness ?? 0.8, metalness: def.metalness ?? 0,
    });
    if (def.transmission) { m.transparent = true; m.opacity = 0.75; }
    if (!/Vidrio|vidrio|Farol|Letras|Bronce|Hierro/.test(name)) enhance(m, { grime: 0.6 });
    else if (/Bronce|Hierro|Letras/.test(name)) enhance(m, { grime: 0 });   // tambien se mojan
  }
  m.name = name;
  allMaterials.push(m);
  return m;
}
