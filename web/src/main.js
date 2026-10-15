// Simulador de la Plaza de Bolivar (Bogota) - three.js
// Escena exportada desde Blender (scripts/export_web.py). Coordenadas de Blender (u, v, z) ->
// three.js (x, y, z) = (u, z, -v).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { MeshBVH } from 'three-mesh-bvh';
import { WebGLPathTracer } from 'three-gpu-pathtracer';
import { PLACES } from './places.js';

const BASE = 'scene/';
const $ = (id) => document.getElementById(id);
const toThree = (u, v, z = 0) => new THREE.Vector3(u, z, -v);

// ------------------------------------------------------------------ estado
const state = {
  meta: null,
  quality: 'alta',
  fly: false,
  pathTracing: false,
  locked: false,
  keys: new Set(),
  yaw: 0, pitch: 0,
  velocity: new THREE.Vector3(),
  onGround: false,
  moved: true,
  touchMove: new THREE.Vector2(),
};

// ------------------------------------------------------------------ renderer
const canvas = $('view');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
} catch (e) {
  fatal('Tu navegador no pudo iniciar WebGL. Prueba con Chrome, Safari o Edge actualizados.');
  throw e;
}
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;   // conserva el tono de los materiales (AgX los lavaba)
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 30000);
camera.rotation.order = 'YXZ';

const sun = new THREE.DirectionalLight(0xffffff, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0003;
sun.shadow.normalBias = 0.04;
sun.shadow.radius = 1.5;
const SH = 110;
Object.assign(sun.shadow.camera, { left: -SH, right: SH, top: SH, bottom: -SH, near: 1, far: 900 });
scene.add(sun, sun.target);

// jugador: capsula (centro de la esfera superior en player.position)
const player = new THREE.Object3D();
const CAPSULE = { radius: 0.3, segment: new THREE.Line3(new THREE.Vector3(), new THREE.Vector3(0, -1.08, 0)) };
const EYE = 0.24;
scene.add(player);

let composer, renderPass, gtaoPass, outputPass;
let collider = null, skyDome = null, pathTracer = null, envTexture = null;
const loadedMaterials = [];

// ------------------------------------------------------------------ utilidades
function fatal(msg) {
  const el = $('loading');
  el.hidden = false;
  el.querySelector('.load-title').textContent = 'No se pudo abrir el simulador';
  el.querySelector('.load-msg').textContent = msg;
}

function setProgress(f, msg) {
  $('load-bar').style.transform = `scaleX(${Math.max(0.02, Math.min(1, f))})`;
  if (msg) $('load-step').textContent = msg;
}

const texLoader = new THREE.TextureLoader();
const texCache = new Map();
function loadTex(path, srgb) {
  const key = path + (srgb ? '#s' : '');
  if (!texCache.has(key)) {
    const t = texLoader.load(BASE + path);
    t.flipY = false;                       // los UV de glTF ya vienen invertidos en v
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    texCache.set(key, t);
  }
  return texCache.get(key);
}
function texRepeat(path, srgb, tile) {
  const base = loadTex(path, srgb);
  if (!tile) return base;
  const t = base.clone();                  // comparte la imagen; solo cambia la repeticion
  t.repeat.set(1 / tile[0], 1 / tile[1]);
  t.needsUpdate = true;
  return t;
}

// Suciedad cerca del suelo y variacion de color a gran escala (rompe la repeticion)
function addWeathering(mat, strength = 1) {
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uGrime = { value: strength };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos; varying vec3 vWNrm;')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        vWNrm = normalize(mat3(modelMatrix) * objectNormal);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vWPos; varying vec3 vWNrm; uniform float uGrime;
        float h2(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
          return mix(mix(h2(i), h2(i+vec2(1,0)), f.x), mix(h2(i+vec2(0,1)), h2(i+vec2(1,1)), f.x), f.y); }`)
      .replace('#include <map_fragment>', `#include <map_fragment>
        {
          float wall = 1.0 - abs(vWNrm.y);
          float big = vnoise(vWPos.xz * 0.11 + vWPos.y * 0.07) * 0.6 + vnoise(vWPos.xz * 0.37 - vWPos.y * 0.2) * 0.4;
          diffuseColor.rgb *= mix(0.9, 1.08, big);
          float ground = 1.0 - smoothstep(-0.15, 1.7, vWPos.y);
          float streak = smoothstep(0.55, 0.85, vnoise(vec2(vWPos.x * 2.3 + vWPos.z * 2.3, vWPos.y * 0.12)));
          float g = clamp(ground * 0.42 + streak * 0.16, 0.0, 0.6) * wall * uGrime;
          diffuseColor.rgb *= 1.0 - g;
        }`);
  };
}

function makeMaterial(name, def) {
  let m;
  if (!def) def = { type: 'const', color: [0.6, 0.6, 0.6], roughness: 0.8, metalness: 0 };
  if (def.type === 'pbr' || def.type === 'tile') {
    m = new THREE.MeshStandardMaterial({
      map: texRepeat(def.map, true, def.tile),
      roughnessMap: def.roughnessMap ? texRepeat(def.roughnessMap, false, def.tile) : null,
      normalMap: def.normalMap ? texRepeat(def.normalMap, false, def.tile) : null,
      roughness: 1, metalness: 0,
      color: def.color ? new THREE.Color(def.color[0], def.color[1], def.color[2]) : new THREE.Color(1, 1, 1),
    });
    if (m.normalMap) m.normalScale.set(1, 1);
    const ground = /plaza|adoquin|anden|asfalto|teja|pizarra|bordillo/i.test(name);
    addWeathering(m, ground ? 0.0 : 1.0);
  } else if (def.type === 'unique') {
    m = new THREE.MeshStandardMaterial({ map: loadTex(def.map, true), roughness: def.roughness ?? 0.9, metalness: 0 });
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
    if (def.envBoost) m.envMapIntensity = def.envBoost;
    if (def.transmission) { m.transparent = true; m.opacity = 0.75; }
  }
  m.name = name;
  loadedMaterials.push(m);
  return m;
}

// ------------------------------------------------------------------ cielo
function makeSkyDome(tex, scale, gamma) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { tSky: { value: tex }, uScale: { value: scale }, uGamma: { value: gamma } },
    vertexShader: `varying vec3 vDir;
      void main(){ vDir = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p.xyww; }`,
    fragmentShader: `varying vec3 vDir; uniform sampler2D tSky; uniform float uScale; uniform float uGamma;
      #include <common>
      void main(){
        vec3 d = normalize(vDir);
        vec2 uv = vec2(atan(d.z, d.x) * RECIPROCAL_PI2 + 0.5, asin(clamp(d.y, -1.0, 1.0)) * RECIPROCAL_PI + 0.5);
        vec3 c = texture2D(tSky, uv).rgb;
        gl_FragColor = vec4(uScale * pow(c, vec3(uGamma)), 1.0);
      }`,
    side: THREE.BackSide, depthWrite: false, depthTest: true, fog: false, toneMapped: true,
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1000, 64, 32), mat);
  dome.frustumCulled = false;
  dome.renderOrder = -10;
  return dome;
}

// ------------------------------------------------------------------ carga
async function load() {
  setProgress(0.02, 'Leyendo la descripcion de la escena…');
  const meta = await (await fetch(BASE + 'scene.json')).json();
  state.meta = meta;
  // misma exposicion que Cycles (-1,25 EV) + 0,5 EV: el mapeo Neutral comprime menos que AgX
  renderer.toneMappingExposure = Math.pow(2, (meta.sky.exposure ?? -1.25) + 0.5);

  // sol (direccion del modelo -> three)
  const d = meta.sun.dirBlender;
  state.sunDir = new THREE.Vector3(d[0], d[2], -d[1]).normalize();
  sun.intensity = meta.sky.sunIntensity ?? 6.5;
  sun.color.setRGB(1.0, 0.975, 0.94);

  // cielo HDR (fondo codificado) + IBL
  setProgress(0.06, 'Cargando el cielo…');
  const skyTex = await texLoader.loadAsync(BASE + meta.sky.background);
  skyTex.colorSpace = THREE.NoColorSpace;
  skyTex.generateMipmaps = true;
  skyTex.minFilter = THREE.LinearMipmapLinearFilter;
  skyTex.anisotropy = 4;
  skyDome = makeSkyDome(skyTex, meta.sky.backgroundScale, meta.sky.backgroundGamma);
  scene.add(skyDome);
  state.skyTex = skyTex;
  const hdrData = new HDRLoader().parse(await fetchBinary(BASE + meta.sky.environment + '.b64.txt', () => {}));
  const hdr = new THREE.DataTexture(hdrData.data, hdrData.width, hdrData.height, THREE.RGBAFormat, hdrData.type);
  Object.assign(hdr, { colorSpace: THREE.LinearSRGBColorSpace, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, flipY: true });
  hdr.needsUpdate = true;
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  envTexture = hdr;
  const pmrem = new THREE.PMREMGenerator(renderer);
  state.pmremEnv = pmrem.fromEquirectangular(hdr).texture;
  scene.environment = state.pmremEnv;
  pmrem.dispose();
  const fc = meta.sky.fogColor || [1.6, 1.8, 2.1];
  scene.fog = new THREE.FogExp2(new THREE.Color(fc[0], fc[1], fc[2]), 1.0 / ((meta.fog?.distance ?? 14000) * 0.42));

  // geometria
  const loader = new GLTFLoader();
  const parts = [['nucleo', 'la plaza y sus edificios', 0.55], ['ciudad', 'la ciudad', 0.1], ['terreno', 'los cerros orientales', 0.2]];
  let acc = 0.1;
  const matByName = new Map();
  const colliderGeoms = [];
  for (const [file, label, w] of parts) {
    setProgress(acc, `Cargando ${label}…`);
    const buf = await fetchBinary(BASE + file + '.glb.b64.txt', (f) => setProgress(acc + w * f));
    const gltf = await loader.parseAsync(buf, BASE);
    acc += w;
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      // la exportacion no lleva materiales: el nombre de malla es "<bloque>:<material>"
      const mi = gltf.parser.associations.get(o)?.meshes;
      const raw = mi !== undefined ? gltf.parser.json.meshes[mi].name : o.name;
      const name = raw.includes(':') ? raw.slice(raw.indexOf(':') + 1) : raw;
      if (!matByName.has(name)) matByName.set(name, makeMaterial(name, meta.materials[name]));
      o.material = matByName.get(name);
      dequantize(o.geometry);
      const dynamic = /Personas|Piel|Ropa|Pantalon|Paloma|Pelo|Bandera/i.test(name);
      o.castShadow = file !== 'terreno';
      o.receiveShadow = true;
      if (file === 'terreno') o.castShadow = false;
      if (!dynamic && !/Vidrio|vidrio|Farol/.test(name)) {
        const g = o.geometry.clone();
        for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
        g.applyMatrix4(o.matrixWorld);
        colliderGeoms.push(g);
      }
    });
    scene.add(gltf.scene);
  }
  setProgress(0.9, 'Calculando colisiones…');
  await nextFrame();
  const merged = mergeGeometries(colliderGeoms, false);
  colliderGeoms.forEach((g) => g.dispose());
  merged.boundsTree = new MeshBVH(merged, { targetLeafSize: 16, maxDepth: 64 });
  collider = new THREE.Mesh(merged);
  collider.visible = false;
  collider.updateMatrixWorld(true);
  setProgress(1, 'Listo');
}

// los atributos cuantizados (int16/int8 normalizados) se pasan a float: el trazador de rayos
// copia los arreglos tal cual y no sabe desnormalizarlos
function dequantize(g) {
  for (const [k, a] of Object.entries(g.attributes)) {
    if (!a.normalized && a.array instanceof Float32Array) continue;
    const n = a.itemSize, out = new Float32Array(a.count * n);
    for (let i = 0; i < a.count; i++) for (let j = 0; j < n; j++) out[i * n + j] = a.getComponent(i, j);
    g.setAttribute(k, new THREE.BufferAttribute(out, n));
  }
}

// Binarios publicados como texto base64 (los artifacts no sirven .glb ni .hdr) y comprimidos con
// gzip: se decodifican aqui y se descomprimen con DecompressionStream (sin WebAssembly)
const B64 = (() => {
  const t = new Uint8Array(256).fill(255);
  const abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  for (let i = 0; i < 64; i++) t[abc.charCodeAt(i)] = i;
  return t;
})();
function b64decode(src) {
  let n = src.length;
  while (n > 0 && (src[n - 1] === 61 || B64[src[n - 1]] === 255)) n--;   // '=' y saltos finales
  const out = new Uint8Array(Math.floor((n * 3) / 4));
  let o = 0, acc = 0, bits = 0;
  for (let i = 0; i < n; i++) {
    const v = B64[src[i]];
    if (v === 255) continue;
    acc = (acc << 6) | v; bits += 6;
    if (bits >= 8) { bits -= 8; out[o++] = (acc >> bits) & 255; }
  }
  return out.subarray(0, o);
}
async function fetchBinary(url, onProgress) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`no se pudo descargar ${url} (${res.status})`);
  const total = Number(res.headers.get('content-length')) || 0;
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    if (total) onProgress(Math.min(1, got / total));
  }
  const text = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { text.set(c, o); o += c.length; }
  let bytes = b64decode(text);
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const ds = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(ds).arrayBuffer());
  }
  onProgress(1);
  return bytes.buffer;
}

const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));

// ------------------------------------------------------------------ postproceso
function setupComposer() {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 4 });
  composer = new EffectComposer(renderer, rt);
  renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);
  gtaoPass = new GTAOPass(scene, camera, size.x, size.y);
  gtaoPass.updateGtaoMaterial({ radius: 0.6, distanceExponent: 1.5, thickness: 1.5, scale: 1.1, samples: 12 });
  gtaoPass.blendIntensity = 0.85;
  composer.addPass(gtaoPass);
  outputPass = new OutputPass();
  composer.addPass(outputPass);
  applyQuality();
}

function applyQuality() {
  const high = state.quality === 'alta';
  const dpr = Math.min(window.devicePixelRatio || 1, high ? 1.75 : 1.0);
  renderer.setPixelRatio(dpr);
  if (gtaoPass) gtaoPass.enabled = high;
  const ms = high ? 4096 : 2048;
  if (sun.shadow.mapSize.x !== ms) {
    sun.shadow.mapSize.set(ms, ms);
    sun.shadow.map?.dispose();
    sun.shadow.map = null;
  }
  resize();
  $('q-alta').setAttribute('aria-pressed', String(high));
  $('q-media').setAttribute('aria-pressed', String(!high));
}

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  if (composer) {
    const s = renderer.getDrawingBufferSize(new THREE.Vector2());
    composer.setSize(w, h);
    composer.setPixelRatio(renderer.getPixelRatio());
    gtaoPass?.setSize(s.x, s.y);
  }
  if (pathTracer) pathTracer.updateCamera();
  state.moved = true;
}
window.addEventListener('resize', resize);

// ------------------------------------------------------------------ jugador y camara
function placePlayer(loc, target, fly = false) {
  const p = toThree(loc[0], loc[1], loc[2]);
  const t = toThree(target[0], target[1], target[2]);
  state.fly = fly || loc[2] > 6;
  player.position.copy(p).add(new THREE.Vector3(0, -EYE, 0));
  const dir = t.clone().sub(p).normalize();
  state.yaw = Math.atan2(-dir.x, -dir.z);
  state.pitch = Math.asin(THREE.MathUtils.clamp(dir.y, -0.99, 0.99));
  state.velocity.set(0, 0, 0);
  state.moved = true;
  updateFlyUI();
}

const tmp = { v1: new THREE.Vector3(), v2: new THREE.Vector3(), box: new THREE.Box3(), seg: new THREE.Line3(), mat: new THREE.Matrix4() };
const GRAVITY = -24;

function stepPhysics(dt) {
  const k = state.keys;
  const run = k.has('ShiftLeft') || k.has('ShiftRight');
  const speed = state.fly ? (run ? 40 : 12) : (run ? 6.5 : 2.6);
  const fwd = new THREE.Vector3(-Math.sin(state.yaw), 0, -Math.cos(state.yaw));
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
  const move = new THREE.Vector3();
  if (k.has('KeyW') || k.has('ArrowUp')) move.add(fwd);
  if (k.has('KeyS') || k.has('ArrowDown')) move.sub(fwd);
  if (k.has('KeyD') || k.has('ArrowRight')) move.add(right);
  if (k.has('KeyA') || k.has('ArrowLeft')) move.sub(right);
  move.addScaledVector(fwd, state.touchMove.y).addScaledVector(right, state.touchMove.x);
  if (move.lengthSq() > 1) move.normalize();

  if (state.fly) {
    const dir = new THREE.Vector3(0, 0, -1).applyEuler(new THREE.Euler(state.pitch, state.yaw, 0, 'YXZ'));
    const r = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0)).normalize();
    const v = new THREE.Vector3()
      .addScaledVector(dir, (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) + state.touchMove.y)
      .addScaledVector(r, (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0) + state.touchMove.x);
    if (k.has('KeyE') || k.has('Space')) v.y += 1;
    if (k.has('KeyQ') || k.has('KeyC')) v.y -= 1;
    if (v.lengthSq() > 0) { player.position.addScaledVector(v.normalize(), speed * dt); state.moved = true; }
    return;
  }

  if (move.lengthSq() > 0) state.moved = true;
  if (state.onGround) state.velocity.y = dt * GRAVITY;
  else state.velocity.y += dt * GRAVITY;
  player.position.addScaledVector(state.velocity, dt);
  player.position.addScaledVector(move, speed * dt);
  player.updateMatrixWorld();
  if (!collider) return;

  // capsula contra el BVH (como el ejemplo de three-mesh-bvh)
  tmp.box.makeEmpty();
  tmp.mat.copy(collider.matrixWorld).invert();
  tmp.seg.copy(CAPSULE.segment);
  tmp.seg.start.applyMatrix4(player.matrixWorld).applyMatrix4(tmp.mat);
  tmp.seg.end.applyMatrix4(player.matrixWorld).applyMatrix4(tmp.mat);
  tmp.box.expandByPoint(tmp.seg.start);
  tmp.box.expandByPoint(tmp.seg.end);
  tmp.box.min.addScalar(-CAPSULE.radius);
  tmp.box.max.addScalar(CAPSULE.radius);
  collider.geometry.boundsTree.shapecast({
    intersectsBounds: (box) => box.intersectsBox(tmp.box),
    intersectsTriangle: (tri) => {
      const triPoint = tmp.v1, capPoint = tmp.v2;
      const dist = tri.closestPointToSegment(tmp.seg, triPoint, capPoint);
      if (dist < CAPSULE.radius) {
        const depth = CAPSULE.radius - dist;
        const dir = capPoint.sub(triPoint).normalize();
        tmp.seg.start.addScaledVector(dir, depth);
        tmp.seg.end.addScaledVector(dir, depth);
      }
    },
  });
  const newPos = new THREE.Vector3().copy(tmp.seg.start).applyMatrix4(collider.matrixWorld);
  const delta = newPos.clone().sub(player.position);
  state.onGround = delta.y > Math.abs(dt * state.velocity.y * 0.25);
  const off = Math.max(0, delta.length() - 1e-5);
  delta.normalize().multiplyScalar(off);
  player.position.add(delta);
  if (!state.onGround) {
    delta.normalize();
    state.velocity.addScaledVector(delta, -delta.dot(state.velocity));
  } else {
    state.velocity.set(0, 0, 0);
  }
  if (player.position.y < -60) placePlayer(PLACES[0].view.loc, PLACES[0].view.target);
}

function jump() {
  if (state.fly) return;
  if (state.onGround) { state.velocity.y = 6.0; state.onGround = false; }
}

function updateCamera() {
  camera.position.copy(player.position).add(new THREE.Vector3(0, EYE, 0));
  camera.rotation.set(state.pitch, state.yaw, 0, 'YXZ');
  // la sombra sigue a la camara (ajustada a la reticula de texeles para que no tiemble)
  const texel = (2 * SH) / sun.shadow.mapSize.x;
  const c = camera.position.clone();
  c.x = Math.round(c.x / texel) * texel;
  c.z = Math.round(c.z / texel) * texel;
  sun.target.position.copy(c);
  sun.position.copy(c).addScaledVector(state.sunDir, 400);
}

// ------------------------------------------------------------------ entrada
window.addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLInputElement) return;
  state.keys.add(e.code);
  if (e.code === 'Space') { e.preventDefault(); jump(); }
  if (e.code === 'KeyF') toggleFly();
  if (e.code === 'KeyR') togglePathTracing();
  if (e.code === 'KeyM') $('places').toggleAttribute('data-open');
  if (e.code === 'Escape' && state.pathTracing) togglePathTracing();
});
window.addEventListener('keyup', (e) => state.keys.delete(e.code));
window.addEventListener('blur', () => state.keys.clear());

canvas.addEventListener('click', () => {
  if (matchMedia('(pointer: coarse)').matches) return;
  canvas.requestPointerLock?.()?.catch?.(() => {});
});
document.addEventListener('pointerlockchange', () => {
  state.locked = document.pointerLockElement === canvas;
  document.body.classList.toggle('locked', state.locked);
});
document.addEventListener('mousemove', (e) => {
  if (!state.locked) return;
  look(e.movementX, e.movementY, 0.0022);
});
function look(dx, dy, s) {
  state.yaw -= dx * s;
  state.pitch = THREE.MathUtils.clamp(state.pitch - dy * s, -1.45, 1.45);
  state.moved = true;
}
// arrastrar con el raton sin bloquear el puntero tambien mira
let drag = null;
canvas.addEventListener('pointerdown', (e) => { if (!state.locked) drag = { x: e.clientX, y: e.clientY, id: e.pointerId, type: e.pointerType }; });
window.addEventListener('pointermove', (e) => {
  if (!drag || drag.id !== e.pointerId) return;
  look(e.clientX - drag.x, e.clientY - drag.y, drag.type === 'touch' ? 0.004 : 0.003);
  drag.x = e.clientX; drag.y = e.clientY;
});
window.addEventListener('pointerup', (e) => { if (drag && drag.id === e.pointerId) drag = null; });

// joystick tactil
(function setupStick() {
  const pad = $('stick'), knob = $('stick-knob');
  let id = null, cx = 0, cy = 0;
  pad.addEventListener('pointerdown', (e) => {
    id = e.pointerId; pad.setPointerCapture(id);
    const r = pad.getBoundingClientRect(); cx = r.left + r.width / 2; cy = r.top + r.height / 2;
    e.stopPropagation();
  });
  pad.addEventListener('pointermove', (e) => {
    if (e.pointerId !== id) return;
    const R = 48;
    let dx = e.clientX - cx, dy = e.clientY - cy;
    const l = Math.hypot(dx, dy); if (l > R) { dx *= R / l; dy *= R / l; }
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
    state.touchMove.set(dx / R, -dy / R);
    state.moved = true;
  });
  const end = (e) => { if (e.pointerId !== id) return; id = null; state.touchMove.set(0, 0); knob.style.transform = ''; };
  pad.addEventListener('pointerup', end);
  pad.addEventListener('pointercancel', end);
})();

// ------------------------------------------------------------------ modos
function toggleFly() {
  state.fly = !state.fly;
  state.velocity.set(0, 0, 0);
  updateFlyUI();
}
function updateFlyUI() {
  $('btn-fly').setAttribute('aria-pressed', String(state.fly));
  $('mode-label').textContent = state.fly ? 'Volando' : 'Caminando';
}

async function togglePathTracing() {
  state.pathTracing = !state.pathTracing;
  $('btn-rt').setAttribute('aria-pressed', String(state.pathTracing));
  document.body.classList.toggle('pt', state.pathTracing);
  if (!state.pathTracing) {
    scene.background = null; scene.environment = state.pmremEnv; skyDome.visible = true;
    $('rt-status').textContent = '';
    return;
  }
  if (!pathTracer) {
    $('rt-status').textContent = 'Preparando el trazado de rayos…';
    await nextFrame(); await nextFrame();
    pathTracer = new WebGLPathTracer(renderer);
    pathTracer.tiles.set(2, 2);
    pathTracer.bounces = 5;
    pathTracer.filterGlossyFactor = 0.5;
    pathTracer.minSamples = 1;
    pathTracer.renderDelay = 0;
    pathTracer.fadeDuration = 300;
    pathTracer.dynamicLowRes = true;
    pathTracer.lowResScale = 0.35;
    pathTracer.renderScale = Math.min(1, 1.25 / renderer.getPixelRatio());
    state.ptBackground = await decodeSkyForPathTracer();
  }
  skyDome.visible = false;
  scene.background = state.ptBackground;
  scene.environment = envTexture;          // el trazador necesita el mapa equirectangular, no el PMREM
  updateCamera();
  if (!state.ptReady) {
    $('rt-status').textContent = 'Construyendo la estructura de rayos (unos segundos)…';
    await nextFrame(); await nextFrame();
    pathTracer.setScene(scene, camera);
    state.ptReady = true;
  } else {
    pathTracer.updateEnvironment();
    pathTracer.updateCamera();
  }
  state.moved = false;
}

// el trazador no admite el material del cielo: se decodifica el fondo a una textura flotante
async function decodeSkyForPathTracer() {
  const img = state.skyTex.image;
  const W = 4096, H = 2048;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0, W, H);
  const src = g.getImageData(0, 0, W, H).data;
  const data = new Uint16Array(W * H * 4);
  const s = state.meta.sky.backgroundScale, gm = state.meta.sky.backgroundGamma;
  const lut = new Uint16Array(256);
  for (let i = 0; i < 256; i++) lut[i] = THREE.DataUtils.toHalfFloat(s * Math.pow(i / 255, gm));
  const one = THREE.DataUtils.toHalfFloat(1);
  for (let y = 0; y < H; y++) {
    const sy = (H - 1 - y) * W;                // DataTexture: fila 0 abajo
    for (let x = 0; x < W; x++) {
      const i = (sy + x) * 4, o = (y * W + x) * 4;
      data[o] = lut[src[i]]; data[o + 1] = lut[src[i + 1]]; data[o + 2] = lut[src[i + 2]]; data[o + 3] = one;
    }
  }
  const t = new THREE.DataTexture(data, W, H, THREE.RGBAFormat, THREE.HalfFloatType);
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.magFilter = t.minFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return t;
}

// ------------------------------------------------------------------ interfaz
function buildPlaces() {
  const list = $('place-list');
  PLACES.forEach((p, i) => {
    const b = document.createElement('button');
    b.className = 'place';
    b.type = 'button';
    b.innerHTML = `<span class="place-name">${p.name}</span><span class="place-kind">${p.kind}</span>`;
    b.addEventListener('click', () => { goTo(i); });
    list.appendChild(b);
  });
}
function goTo(i) {
  const p = PLACES[i];
  placePlayer(p.view.loc, p.view.target, p.view.fly);
  showCard(p);
  if (pathTracer && state.pathTracing) pathTracer.updateCamera();
}
let cardTimer = null, lastCard = null;
function showCard(p) {
  if (lastCard === p.name && !$('card').hidden) return;
  lastCard = p.name;
  $('card-kind').textContent = p.kind;
  $('card-name').textContent = p.name;
  $('card-text').textContent = p.text;
  $('card-facts').innerHTML = p.facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
  $('card').hidden = false;
  clearTimeout(cardTimer);
  cardTimer = setTimeout(() => { $('card').hidden = true; }, 14000);
}
$('card-close').addEventListener('click', () => { $('card').hidden = true; });

function proximityCards() {
  const u = camera.position.x, v = -camera.position.z;
  let best = null, bd = 1e9;
  for (const p of PLACES) {
    if (!p.near) continue;
    const d = Math.hypot(u - p.near[0], v - p.near[1]);
    if (d < p.near[2] && d < bd) { bd = d; best = p; }
  }
  if (best) showCard(best);
}

// minimapa
const mini = { img: null, ctx: null };
function setupMinimap() {
  const c = $('minimap');
  mini.ctx = c.getContext('2d');
  mini.img = new Image();
  mini.img.src = BASE + 'minimapa.jpg';
  c.addEventListener('click', (e) => {
    const r = c.getBoundingClientRect();
    const half = state.meta.minimap.half;
    const u = ((e.clientX - r.left) / r.width) * 2 * half - half;
    const v = half - ((e.clientY - r.top) / r.height) * 2 * half;
    placePlayer([u, v, 1.62], [u + 10 * -Math.sin(state.yaw), v + 10 * Math.cos(state.yaw), 1.62], false);
    player.position.y = 8;
  });
}
function drawMinimap() {
  const g = mini.ctx; if (!g) return;
  const c = g.canvas, S = c.width, half = state.meta.minimap.half;
  g.clearRect(0, 0, S, S);
  if (mini.img.complete) g.drawImage(mini.img, 0, 0, S, S);
  const px = (u) => ((u + half) / (2 * half)) * S, py = (v) => ((half - v) / (2 * half)) * S;
  for (const p of PLACES) {
    if (!p.near) continue;
    g.beginPath(); g.arc(px(p.near[0]), py(p.near[1]), 3.2, 0, Math.PI * 2);
    g.fillStyle = 'rgba(240, 214, 160, 0.95)'; g.fill();
  }
  const u = camera.position.x, v = -camera.position.z;
  const x = px(u), y = py(v);
  const a = -state.yaw;
  g.save(); g.translate(x, y); g.rotate(a);
  g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 26, -Math.PI / 2 - 0.5, -Math.PI / 2 + 0.5); g.closePath();
  g.fillStyle = 'rgba(255, 244, 214, 0.28)'; g.fill();
  g.beginPath(); g.moveTo(0, -8); g.lineTo(5.5, 6); g.lineTo(0, 3); g.lineTo(-5.5, 6); g.closePath();
  g.fillStyle = '#ffd27a'; g.strokeStyle = '#1a1612'; g.lineWidth = 1.5; g.fill(); g.stroke();
  g.restore();
}

function hud() {
  const u = camera.position.x, v = -camera.position.z;
  const gr = state.meta.gridRotationDeg;
  const head = ((-THREE.MathUtils.radToDeg(state.yaw) + gr) % 360 + 360) % 360;
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
  $('compass').textContent = `${dirs[Math.round(head / 45) % 8]} ${Math.round(head)}°`;
  $('alt').textContent = `${(2614 + camera.position.y).toFixed(0)} m s. n. m.`;
}

// botones
$('btn-fly').addEventListener('click', toggleFly);
$('btn-rt').addEventListener('click', togglePathTracing);
$('btn-places').addEventListener('click', () => $('places').toggleAttribute('data-open'));
$('btn-jump').addEventListener('click', jump);
$('q-alta').addEventListener('click', () => { state.quality = 'alta'; applyQuality(); });
$('q-media').addEventListener('click', () => { state.quality = 'media'; applyQuality(); });
$('btn-full').addEventListener('click', () => {
  const el = document.documentElement;
  if (!document.fullscreenElement) el.requestFullscreen?.().catch(() => {});
  else document.exitFullscreen?.();
});
$('start').addEventListener('click', () => {
  $('intro').hidden = true;
  if (!matchMedia('(pointer: coarse)').matches) canvas.requestPointerLock?.()?.catch?.(() => {});
});

// ------------------------------------------------------------------ bucle
const clock = new THREE.Clock();
let frame = 0;
function loop() {
  requestAnimationFrame(loop);
  const dt = Math.min(0.05, clock.getDelta());
  if (!state.pathTracing || state.keys.size || state.touchMove.lengthSq()) {
    const sub = 5;
    for (let i = 0; i < sub; i++) stepPhysics(dt / sub);
  }
  updateCamera();
  if (state.pathTracing && pathTracer) {
    if (state.moved) { pathTracer.updateCamera(); state.moved = false; }
    pathTracer.renderSample();
    $('rt-status').textContent = `Trazado de rayos · ${Math.floor(pathTracer.samples)} muestras`;
  } else {
    composer.render(dt);
    state.moved = false;
  }
  if (frame++ % 3 === 0) { drawMinimap(); hud(); }
  if (frame % 20 === 0) proximityCards();
}

// ------------------------------------------------------------------ inicio
(async function start() {
  try {
    buildPlaces();
    await load();
    setupComposer();
    setupMinimap();
    const c0 = state.meta.cameras.Cam_Referencia;
    placePlayer(c0.loc, [c0.target[0], c0.target[1], 6]);
    $('loading').hidden = true;
    $('intro').hidden = false;
    window.__sim = { state, camera, renderer, scene, placePlayer, togglePathTracing, goTo };
    loop();
  } catch (e) {
    console.error(e);
    fatal('Error al cargar la escena: ' + (e?.message || e));
  }
})();
