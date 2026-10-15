// Simulador de la Plaza de Bolivar (Bogota) - three.js
// Escena exportada desde Blender (scripts/export_web.py). Coordenadas de Blender (u, v, z) ->
// three.js (x, y, z) = (u, z, -v).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { MeshBVH } from 'three-mesh-bvh';
import { WebGLPathTracer, DenoiseMaterial } from 'three-gpu-pathtracer';
import { PLACES } from './places.js';
import { G, initMaterials, makeMaterial } from './materials.js';
import { buildRoads } from './roads.js';
import { Traffic } from './traffic.js';
import { Pigeons } from './pigeons.js';
import { People } from './people.js';
import { Weather, PRESETS, makeSkyDome } from './weather.js';
import { SoundScape } from './audio.js';
import { BASE, assetUrl, assetJSON, assetAscii } from './assets.js';

const $ = (id) => document.getElementById(id);
const toThree = (u, v, z = 0) => new THREE.Vector3(u, z, -v);
const coarse = matchMedia('(pointer: coarse)').matches;

// ------------------------------------------------------------------ estado
const state = {
  meta: null,
  quality: coarse ? 'media' : 'alta',
  fly: false,
  pathTracing: false,
  locked: false,
  keys: new Set(),
  yaw: 0, pitch: 0,
  velocity: new THREE.Vector3(),       // vertical (gravedad) y empujes
  move: new THREE.Vector3(),           // velocidad horizontal suavizada
  onGround: false,
  moved: true,
  touchMove: new THREE.Vector2(),
  runToggle: false,
  bob: 0, bobAmp: 0, lastStepSign: 1, fov: 62,
  talk: null, talkT: 0,
  time: 0,
  bellT: 25,
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
initMaterials(BASE, renderer);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(62, 1, 0.25, 30000);
camera.rotation.order = 'YXZ';

const sun = new THREE.DirectionalLight(0xffffff, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0002;
sun.shadow.normalBias = 0.035;
sun.shadow.radius = 1.5;
let SH = 110;
Object.assign(sun.shadow.camera, { left: -SH, right: SH, top: SH, bottom: -SH, near: 1, far: 1400 });
scene.add(sun, sun.target);

// jugador: capsula (centro de la esfera superior en player.position)
const player = new THREE.Object3D();
const CAPSULE = { radius: 0.3, segment: new THREE.Line3(new THREE.Vector3(), new THREE.Vector3(0, -1.08, 0)) };
const EYE = 0.24;
scene.add(player);

let composer, renderPass, gtaoPass, bloomPass, outputPass, finishPass;
let collider = null, skyDome = null, pathTracer = null;
let traffic = null, pigeons = null, people = null, weather = null;
const audio = new SoundScape();
const hdr = { a: null, b: null };

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
const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));
const texLoader = new THREE.TextureLoader();

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
  while (n > 0 && (src[n - 1] === 61 || B64[src[n - 1]] === 255)) n--;
  const out = new Uint8Array(Math.floor((n * 3) / 4));
  let o = 0, acc = 0, bits = 0;
  for (let i = 0; i < n; i++) {
    const v = B64[src[i]];
    if (v === 255) continue;
    acc = ((acc << 6) | v) & 0xffffff; bits += 6;
    if (bits >= 8) { bits -= 8; out[o++] = (acc >> bits) & 255; }
  }
  return out.subarray(0, o);
}
async function fetchBinary(path, onProgress) {
  let bytes = b64decode(await assetAscii(path, onProgress));
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const ds = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(ds).arrayBuffer());
  }
  onProgress?.(1);
  return bytes.buffer;
}
async function loadHDR(name) {
  const d = new HDRLoader().parse(await fetchBinary(name + '.b64.txt'));
  const t = new THREE.DataTexture(d.data, d.width, d.height, THREE.RGBAFormat, d.type);
  Object.assign(t, { colorSpace: THREE.LinearSRGBColorSpace, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, flipY: true });
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.needsUpdate = true;
  return t;
}
async function loadSkyJpg(name) {
  const t = await texLoader.loadAsync(assetUrl(name));
  t.colorSpace = THREE.NoColorSpace;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.anisotropy = 4;
  return t;
}

// ------------------------------------------------------------------ carga
let terrainBVH = null;
const _ray = new THREE.Ray(), _down = new THREE.Vector3(0, -1, 0);
function heightAt(u, v) {
  if (!terrainBVH) return 0;
  _ray.origin.set(u, 4000, -v); _ray.direction.copy(_down);
  const hit = terrainBVH.raycastFirst(_ray, THREE.DoubleSide);
  return hit ? hit.point.y : 0;
}
function groundY(x, z, from = 2.6) {
  if (!collider) return 0;
  _ray.origin.set(x, from, z); _ray.direction.copy(_down);
  const hit = collider.geometry.boundsTree.raycastFirst(_ray, THREE.DoubleSide);
  return hit ? hit.point.y : 0;
}

async function load() {
  setProgress(0.02, 'Leyendo la descripción de la escena…');
  const meta = await assetJSON('scene.json');
  state.meta = meta;
  state.baseExposure = Math.pow(2, (meta.sky.exposure ?? -1.25) + 0.5);
  renderer.toneMappingExposure = state.baseExposure;
  const d = meta.sun.dirBlender;
  state.sunDir = new THREE.Vector3(d[0], d[2], -d[1]).normalize();
  state.baseSun = meta.sky.sunIntensity ?? 6.5;
  sun.intensity = state.baseSun;
  sun.color.setRGB(1.0, 0.975, 0.94);

  setProgress(0.05, 'Cargando el cielo…');
  const [skyA, skyB, hdrA, hdrB] = await Promise.all([loadSkyJpg(meta.sky.background), loadSkyJpg('sky2_bg.jpg'), loadHDR(meta.sky.environment), loadHDR('sky2_env.hdr')]);
  hdr.a = hdrA; hdr.b = hdrB; state.skyTexA = skyA; state.skyTexB = skyB;
  skyDome = makeSkyDome(skyA, skyB, meta.sky.backgroundScale, meta.sky.backgroundGamma);
  scene.add(skyDome);
  const fc = meta.sky.fogColor || [0.34, 0.36, 0.44];
  scene.fog = new THREE.FogExp2(new THREE.Color(fc[0], fc[1], fc[2]), 1.73 / 10000);

  // geometria
  const loader = new GLTFLoader();
  const parts = [['nucleo', 'la plaza y sus edificios', 0.45], ['ciudad', 'la ciudad', 0.1], ['terreno', 'los cerros orientales', 0.15]];
  let acc = 0.1;
  const matByName = new Map();
  const getMat = (name) => {
    if (!matByName.has(name)) matByName.set(name, makeMaterial(name, meta.materials[name]));
    return matByName.get(name);
  };
  const colliderGeoms = [];
  const DYNAMIC = /Personas|Piel|Ropa|Pantalon|Paloma|Pelo|Bandera/i;
  for (const [file, label, w] of parts) {
    setProgress(acc, `Cargando ${label}…`);
    const buf = await fetchBinary(file + '.glb.b64.txt', (f) => setProgress(acc + w * f));
    const gltf = await loader.parseAsync(buf, BASE);
    acc += w;
    gltf.scene.updateMatrixWorld(true);
    const remove = [];
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      // la exportacion no lleva materiales: el nombre de malla es "<bloque>:<material>"
      const mi = gltf.parser.associations.get(o)?.meshes;
      const raw = mi !== undefined ? gltf.parser.json.meshes[mi].name : o.name;
      const name = raw.includes(':') ? raw.slice(raw.indexOf(':') + 1) : raw;
      // personas y palomas estaticas de Blender: las reemplazan las animadas
      if (/^(Ropa|Piel|Pantalon|Pelo y zapatos|Paloma)/.test(name)) { remove.push(o); return; }
      o.material = getMat(name);
      dequantize(o.geometry);
      // losa base de las calles en Blender (un solo cuadrilatero de ~260 m): asfalto, no adoquin
      if (name === 'adoquin (PBR)' && o.geometry.getAttribute('position').count <= 8) o.material = getMat('asfalto (PBR)');
      if (/plaza_franjas/.test(name)) o.position.y += 0.012;          // franjas sobre la losa (evita parpadeo)
      o.updateMatrixWorld(true);
      o.castShadow = file !== 'terreno';
      o.receiveShadow = true;
      if (file === 'terreno' && name === 'Terreno') {
        const g = o.geometry.clone();
        for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
        g.applyMatrix4(o.matrixWorld);
        terrainBVH = new MeshBVH(g);
      }
      if (!DYNAMIC.test(name) && !/Vidrio|vidrio|Farol/.test(name)) {
        const g = o.geometry.clone();
        for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
        g.applyMatrix4(o.matrixWorld);
        colliderGeoms.push(g);
      }
    });
    for (const o of remove) o.parent.remove(o);
    scene.add(gltf.scene);
  }

  // calles reales con lineas, andenes y cebras
  setProgress(0.72, 'Trazando las calles…');
  await nextFrame();
  const roadsData = await assetJSON('roads.json');
  const roads = buildRoads(roadsData, heightAt, {
    asfalto: getMat('asfalto (PBR)'), adoquin: getMat('adoquin (PBR)'), anden: getMat('anden (PBR)'), bordillo: getMat('bordillo (PBR)'),
  });
  scene.add(roads.group);
  roads.group.traverse((o) => {
    if (!o.isMesh || /lineas/.test(o.name)) return;
    const g = o.geometry.clone();
    for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
    colliderGeoms.push(g);
  });

  setProgress(0.8, 'Calculando colisiones…');
  await nextFrame();
  const merged = mergeGeometries(colliderGeoms.map((g) => (g.index ? g.toNonIndexed() : g)), false);
  colliderGeoms.length = 0;
  merged.boundsTree = new MeshBVH(merged, { maxDepth: 64 });
  collider = new THREE.Mesh(merged);
  collider.visible = false;
  collider.updateMatrixWorld(true);

  // vida y clima
  setProgress(0.88, 'Llenando la plaza de gente, palomas y carros…');
  await nextFrame();
  const outline = meta.plaza.outline;
  const avoid = [{ u: 6.4, v: -15.25, r: 9.5 }];
  traffic = new Traffic(scene, roads);
  pigeons = new Pigeons(scene, { outline, avoid, count: coarse ? 140 : 240, groundY: (x, z) => groundY(x, z) });
  people = new People(scene, {
    outline, avoid, groundY: (x, z) => groundY(x, z),
    walkers: coarse ? 40 : 72, groups: coarse ? 7 : 12,
    shelters: [[3.5, -69.5], [52.5, 30], [52.5, 0], [-37, 47]],
  });
  weather = new Weather({
    renderer, scene, sun, skyDome, hdrA, hdrB, baseSun: state.baseSun, baseExposure: state.baseExposure,
    fogA: new THREE.Color(fc[0], fc[1], fc[2]), fogB: new THREE.Color(0.62, 0.65, 0.7),
  });
  weather.onThunder = (delay) => audio.thunder(delay);
  weather.onChange = (name) => updateWeatherUI(name);
  setProgress(1, 'Listo');
}

// ------------------------------------------------------------------ postproceso
const FinishShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uVig: { value: 0.55 }, uGrain: { value: 0.018 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime, uVig, uGrain; varying vec2 vUv;
    void main(){ vec4 c = texture2D(tDiffuse, vUv); vec2 d = vUv - 0.5; c.rgb *= 1.0 - dot(d, d) * uVig;
      float n = fract(sin(dot(vUv * vec2(12.9898, 78.233) + uTime, vec2(1.0))) * 43758.5453);
      c.rgb += (n - 0.5) * uGrain; gl_FragColor = c; }`,
};
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
  bloomPass = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.18, 0.5, 7.0);
  composer.addPass(bloomPass);
  outputPass = new OutputPass();
  composer.addPass(outputPass);
  finishPass = new ShaderPass(FinishShader);
  composer.addPass(finishPass);
  applyQuality();
}

function applyQuality() {
  const high = state.quality === 'alta';
  const dpr = Math.min(window.devicePixelRatio || 1, high ? 1.75 : 1.0);
  renderer.setPixelRatio(dpr);
  if (gtaoPass) gtaoPass.enabled = high;
  if (bloomPass) bloomPass.enabled = high;
  G.uPom.value = high ? 1 : 0;
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
  state.move.set(0, 0, 0);
  state.moved = true;
  updateFlyUI();
}

const tmp = { v1: new THREE.Vector3(), v2: new THREE.Vector3(), box: new THREE.Box3(), seg: new THREE.Line3(), mat: new THREE.Matrix4() };
const GRAVITY = -24;
const running = () => state.keys.has('ShiftLeft') || state.keys.has('ShiftRight') || state.runToggle;

function stepPhysics(dt) {
  const k = state.keys;
  const run = running();
  const fwd = new THREE.Vector3(-Math.sin(state.yaw), 0, -Math.cos(state.yaw));
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
  const wish = new THREE.Vector3();
  if (k.has('KeyW') || k.has('ArrowUp')) wish.add(fwd);
  if (k.has('KeyS') || k.has('ArrowDown')) wish.sub(fwd);
  if (k.has('KeyD') || k.has('ArrowRight')) wish.add(right);
  if (k.has('KeyA') || k.has('ArrowLeft')) wish.sub(right);
  wish.addScaledVector(fwd, state.touchMove.y).addScaledVector(right, state.touchMove.x);
  if (wish.lengthSq() > 1) wish.normalize();

  if (state.fly) {
    const speed = run ? 45 : 14;
    const dir = new THREE.Vector3(0, 0, -1).applyEuler(new THREE.Euler(state.pitch, state.yaw, 0, 'YXZ'));
    const r = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0)).normalize();
    const v = new THREE.Vector3()
      .addScaledVector(dir, (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) + state.touchMove.y)
      .addScaledVector(r, (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0) + state.touchMove.x);
    if (k.has('KeyE') || k.has('Space')) v.y += 1;
    if (k.has('KeyQ') || k.has('KeyC')) v.y -= 1;
    if (v.lengthSq() > 1) v.normalize();
    state.move.lerp(v.multiplyScalar(speed), Math.min(1, dt * 4));
    if (state.move.lengthSq() > 1e-4) { player.position.addScaledVector(state.move, dt); state.moved = true; }
    return;
  }

  // aceleracion suave (inercia de una persona), mas lenta en el aire
  const speed = run ? 6.2 : 2.7;
  const accel = state.onGround ? 12 : 2.5;
  state.move.lerp(wish.multiplyScalar(speed), Math.min(1, dt * accel));
  if (state.move.lengthSq() > 1e-3) state.moved = true;
  if (state.onGround) state.velocity.y = dt * GRAVITY;
  else state.velocity.y += dt * GRAVITY;
  player.position.addScaledVector(state.velocity, dt);
  player.position.addScaledVector(state.move, dt);
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

const feet = new THREE.Vector3();
function feetPos() { return feet.copy(player.position).add(CAPSULE.segment.end).addScaledVector(_down, CAPSULE.radius); }

// sombra: centrada delante de la camara, ajustada a la reticula de texeles en el espacio de la luz
const lightRot = new THREE.Matrix4(), lightInv = new THREE.Matrix4(), _c = new THREE.Vector3();
const _origin = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0), _ld = new THREE.Vector3(), _fw = new THREE.Vector3();
function updateShadow() {
  const alt = Math.max(0, camera.position.y);
  const want = alt > 120 ? 420 : alt > 35 ? 220 : 110;
  if (want !== SH) {
    SH = want;
    Object.assign(sun.shadow.camera, { left: -SH, right: SH, top: SH, bottom: -SH });
    sun.shadow.camera.updateProjectionMatrix();
  }
  lightRot.lookAt(_origin, _ld.copy(state.sunDir).negate(), _up);
  lightInv.copy(lightRot).invert();
  _fw.set(-Math.sin(state.yaw), 0, -Math.cos(state.yaw));
  _c.copy(camera.position).addScaledVector(_fw, SH * 0.45);
  _c.y = Math.min(_c.y, 30);
  _c.applyMatrix4(lightInv);
  const texel = (2 * SH) / sun.shadow.mapSize.x;
  _c.x = Math.round(_c.x / texel) * texel;
  _c.y = Math.round(_c.y / texel) * texel;
  _c.applyMatrix4(lightRot);
  sun.target.position.copy(_c);
  sun.position.copy(_c).addScaledVector(state.sunDir, 600);
  sun.target.updateMatrixWorld();
}

const _bobV = new THREE.Vector3();
function updateCamera(dt = 0) {
  // balanceo de la cabeza al caminar y correr; pasos sincronizados
  const hs = Math.hypot(state.move.x, state.move.z);
  const walking = !state.fly && state.onGround && hs > 0.4;
  state.bobAmp = THREE.MathUtils.lerp(state.bobAmp, walking ? Math.min(1, hs / 6) : 0, Math.min(1, dt * 6));
  if (walking) {
    const stride = hs > 4 ? 1.15 : 0.72;
    state.bob += (hs * dt / stride) * Math.PI;
    const sgn = Math.sign(Math.sin(state.bob));
    if (sgn !== state.lastStepSign) { state.lastStepSign = sgn; audio.step(hs > 4, G.uWet.value); }
  }
  const by = Math.abs(Math.sin(state.bob)) * 0.06 * state.bobAmp - 0.03 * state.bobAmp;
  const bx = Math.cos(state.bob) * 0.025 * state.bobAmp;
  camera.position.copy(player.position).add(_bobV.set(0, EYE + by, 0));
  camera.position.x += Math.cos(state.yaw) * bx;
  camera.position.z -= Math.sin(state.yaw) * bx;
  camera.rotation.set(state.pitch, state.yaw, Math.sin(state.bob * 0.5) * 0.004 * state.bobAmp, 'YXZ');
  // campo de vision mas amplio al correr; plano cercano segun la altura (precision de profundidad)
  const fovT = !state.fly && hs > 4.5 ? 69 : 62;
  state.fov = THREE.MathUtils.lerp(state.fov, fovT, Math.min(1, dt * 4));
  const alt = Math.max(0, camera.position.y - 2);
  const near = THREE.MathUtils.clamp(0.25 + alt * 0.02, 0.25, 6);
  if (Math.abs(camera.fov - state.fov) > 0.05 || Math.abs(camera.near - near) / near > 0.05) {
    camera.fov = state.fov; camera.near = near; camera.updateProjectionMatrix();
  }
  if (state.sunDir) updateShadow();
}

// ------------------------------------------------------------------ entrada
window.addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLInputElement) return;
  state.keys.add(e.code);
  if (e.code === 'Space') { e.preventDefault(); jump(); }
  if (e.code === 'KeyF') toggleFly();
  if (e.code === 'KeyR') togglePathTracing();
  if (e.code === 'KeyM') $('places').toggleAttribute('data-open');
  if (e.code === 'KeyE' && !state.fly) talk();
  if (e.code === 'KeyG') throwCorn();
  if (e.code === 'KeyT') $('weather').toggleAttribute('data-open');
  if (e.code === 'Escape' && state.pathTracing) togglePathTracing();
});
window.addEventListener('keyup', (e) => state.keys.delete(e.code));
window.addEventListener('blur', () => state.keys.clear());

canvas.addEventListener('click', () => {
  if (coarse) return;
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
let drag = null;
canvas.addEventListener('pointerdown', (e) => { if (!state.locked) drag = { x: e.clientX, y: e.clientY, id: e.pointerId, type: e.pointerType }; });
window.addEventListener('pointermove', (e) => {
  if (!drag || drag.id !== e.pointerId) return;
  look(e.clientX - drag.x, e.clientY - drag.y, drag.type === 'touch' ? 0.004 : 0.003);
  drag.x = e.clientX; drag.y = e.clientY;
});
window.addEventListener('pointerup', (e) => { if (drag && drag.id === e.pointerId) drag = null; });

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

// ------------------------------------------------------------------ interacciones
const _cd = new THREE.Vector3();
function talk() {
  if (!people) return;
  camera.getWorldDirection(_cd);
  const p = people.findTalkable(camera.position, _cd);
  if (!p) return;
  state.talk = p; state.talkT = 7;
  $('bubble-text').textContent = people.talkTo(p, camera.position);
  $('bubble').hidden = false;
}
function throwCorn() {
  if (!pigeons || state.fly) return;
  const fwd = new THREE.Vector3(-Math.sin(state.yaw), 0, -Math.cos(state.yaw));
  const ok = pigeons.throwCorn(feetPos(), fwd);
  toast(ok ? 'Maíz en el piso: las palomas ya vienen' : 'Las palomas comen en la plaza: acércate a ella');
}
let toastT = null;
function toast(msg) {
  const el = $('toast');
  el.textContent = msg; el.hidden = false;
  clearTimeout(toastT);
  toastT = setTimeout(() => { el.hidden = true; }, 2600);
}

function toggleFly() {
  state.fly = !state.fly;
  state.velocity.set(0, 0, 0);
  updateFlyUI();
}
function updateFlyUI() {
  $('btn-fly').setAttribute('aria-pressed', String(state.fly));
  $('mode-label').textContent = state.fly ? 'Volando' : 'Caminando';
}

// ------------------------------------------------------------------ trazado de rayos
const _bm = new THREE.Matrix4(), _bn = new THREE.Matrix3(), _bc = new THREE.Color(), _bv = new THREE.Vector3();
// el trazador no admite InstancedMesh ni colores por instancia: se congela una copia estatica de
// carros, personas y palomas, agrupada por material y color
function bakeInstances(center, radius) {
  const group = new THREE.Group();
  const buckets = new Map();
  const r2 = radius * radius;
  scene.traverse((im) => {
    if (!im.isInstancedMesh || !im.visible || im.count === 0) return;
    const mats = Array.isArray(im.material) ? im.material : [im.material];
    const base = im.geometry.index ? im.geometry.toNonIndexed() : im.geometry;
    const groups = base.groups.length ? base.groups : [{ start: 0, count: base.getAttribute('position').count, materialIndex: 0 }];
    const P = base.getAttribute('position'), N = base.getAttribute('normal'), VC = base.getAttribute('color'), SL = base.getAttribute('slot');
    const SLOTS = ['iShirt', 'iPants', 'iSkin', 'iHair', null, 'iAcc'];
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, _bm);
      _bm.premultiply(im.matrixWorld);
      if (Math.abs(_bm.determinant()) < 1e-9) continue;
      const px = _bm.elements[12] - center.x, pz = _bm.elements[14] - center.z;
      if (px * px + pz * pz > r2) continue;
      _bn.getNormalMatrix(_bm);
      if (im.instanceColor) im.getColorAt(i, _bc); else _bc.setRGB(1, 1, 1);
      for (const gr of groups) {
        const mat = mats[gr.materialIndex];
        for (let t = gr.start; t < gr.start + gr.count; t += 3) {
          let r = _bc.r, g = _bc.g, b = _bc.b;
          if (SL) {
            const k = SLOTS[Math.round(SL.getX(t))];
            if (k) { const a = im.geometry.getAttribute(k); r = a.getX(i); g = a.getY(i); b = a.getZ(i); } else { r = g = b = 0.025; }
          } else if (VC) { r *= VC.getX(t); g *= VC.getY(t); b *= VC.getZ(t); }
          const key = `${mat.uuid}|${r.toFixed(2)},${g.toFixed(2)},${b.toFixed(2)}`;
          let bk = buckets.get(key);
          if (!bk) { bk = { mat, color: [r, g, b], pos: [], nor: [], people: !!SL }; buckets.set(key, bk); }
          for (let v = t; v < t + 3; v++) {
            _bv.fromBufferAttribute(P, v).applyMatrix4(_bm); bk.pos.push(_bv.x, _bv.y, _bv.z);
            _bv.fromBufferAttribute(N, v).applyMatrix3(_bn).normalize(); bk.nor.push(_bv.x, _bv.y, _bv.z);
          }
        }
      }
    }
  });
  for (const bk of buckets.values()) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(bk.pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(bk.nor, 3));
    const m = bk.people ? new THREE.MeshStandardMaterial({ roughness: 0.85 }) : bk.mat.clone();
    m.vertexColors = false;
    m.onBeforeCompile = () => {};
    m.color.multiply(new THREE.Color(bk.color[0], bk.color[1], bk.color[2]));
    group.add(new THREE.Mesh(g, m));
  }
  return group;
}

async function togglePathTracing() {
  state.pathTracing = !state.pathTracing;
  $('btn-rt').setAttribute('aria-pressed', String(state.pathTracing));
  document.body.classList.toggle('pt', state.pathTracing);
  const instanced = [];
  scene.traverse((o) => { if (o.isInstancedMesh) instanced.push(o); });
  if (!state.pathTracing) {
    scene.background = null; scene.environment = weather.envTexture; skyDome.visible = true;
    if (state.baked) { scene.remove(state.baked); state.baked.traverse((o) => o.geometry?.dispose()); state.baked = null; }
    for (const o of instanced) o.visible = true;
    $('rt-status').textContent = '';
    return;
  }
  $('rt-status').textContent = 'Preparando el trazado de rayos…';
  await nextFrame(); await nextFrame();
  if (!pathTracer) {
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
    // filtro de ruido que preserva bordes mientras hay pocas muestras; se desvanece al converger
    const dn = new FullScreenQuad(new DenoiseMaterial({ map: null, blending: THREE.NoBlending }));
    pathTracer.renderToCanvasCallback = (target, r, quad) => {
      const s = pathTracer.samples;
      const auto = r.autoClear;
      r.autoClear = false;
      if (quad.material.map === target.texture && s >= 1 && s < 400) {
        const k = 1 - Math.min(1, s / 400);
        dn.material.map = target.texture;
        dn.material.sigma = 1.2 + 3.3 * k;
        dn.material.threshold = 0.04 + 0.16 * k;
        dn.material.kSigma = 1.0;
        dn.render(r);
      } else quad.render(r);
      r.autoClear = auto;
    };
  }
  const overcast = weather.cur.sky > 0.5;
  state.ptBackground = await decodeSkyForPathTracer(overcast ? state.skyTexB : state.skyTexA, overcast ? weather.cur.dark : 1);
  state.baked = bakeInstances(camera.position, 160);
  for (const o of instanced) o.visible = false;
  scene.add(state.baked);
  skyDome.visible = false;
  scene.background = state.ptBackground;
  scene.environment = overcast ? hdr.b : hdr.a;     // el trazador necesita el mapa equirectangular
  updateCamera();
  $('rt-status').textContent = 'Construyendo la estructura de rayos (unos segundos)…';
  await nextFrame(); await nextFrame();
  pathTracer.setScene(scene, camera);
  state.moved = false;
}

async function decodeSkyForPathTracer(tex, k) {
  const img = tex.image;
  const W = 4096, H = 2048;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0, W, H);
  const src = g.getImageData(0, 0, W, H).data;
  const data = new Uint16Array(W * H * 4);
  const s = state.meta.sky.backgroundScale * k, gm = state.meta.sky.backgroundGamma;
  const lut = new Uint16Array(256);
  for (let i = 0; i < 256; i++) lut[i] = THREE.DataUtils.toHalfFloat(s * Math.pow(i / 255, gm));
  const one = THREE.DataUtils.toHalfFloat(1);
  for (let y = 0; y < H; y++) {
    const sy = (H - 1 - y) * W;
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
  mini.img.src = assetUrl('minimapa.jpg');
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
  if (traffic) {
    g.fillStyle = 'rgba(255, 210, 80, 0.9)';
    for (const v of traffic.vehicles) {
      const u = v.pos.x, w = -v.pos.z;
      if (Math.abs(u) < half && Math.abs(w) < half) g.fillRect(px(u) - 2, py(w) - 2, 4, 4);
    }
  }
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
  const gr = state.meta.gridRotationDeg;
  const head = ((-THREE.MathUtils.radToDeg(state.yaw) + gr) % 360 + 360) % 360;
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
  $('compass').textContent = `${dirs[Math.round(head / 45) % 8]} ${Math.round(head)}°`;
  $('alt').textContent = `${(2614 + camera.position.y).toFixed(0)} m s. n. m.`;
  const kmh = Math.hypot(state.move.x, state.move.z) * 3.6;
  $('speed').textContent = `${kmh.toFixed(0)} km/h`;
  $('mode-label').textContent = state.fly ? 'Volando' : kmh > 15 ? 'Corriendo' : 'Caminando';
}

function updateWeatherUI(name) {
  document.querySelectorAll('[data-w]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.w === name)));
  $('weather-label').textContent = PRESETS[name].label + (weather?.auto ? ' · auto' : '');
}

const _hp = new THREE.Vector3(), _right = new THREE.Vector3();
const panOf = (p) => {
  _right.set(Math.cos(state.yaw), 0, -Math.sin(state.yaw));
  return THREE.MathUtils.clamp(_hp.subVectors(p, camera.position).normalize().dot(_right), -1, 1);
};
function interactions(dt) {
  // aviso para hablar
  let prompt = '';
  if (people && !state.fly && !state.pathTracing) {
    camera.getWorldDirection(_cd);
    const p = people.findTalkable(camera.position, _cd);
    if (p && p !== state.talk) prompt = coarse ? '' : 'E · Hablar';
    $('btn-talk').hidden = !p;
  }
  $('prompt').textContent = prompt; $('prompt').hidden = !prompt;
  // globo de dialogo sobre la persona
  if (state.talk) {
    state.talkT -= dt;
    people.headPos(state.talk, _hp).project(camera);
    const el = $('bubble');
    if (state.talkT <= 0 || _hp.z > 1 || camera.position.distanceTo(state.talk.pos) > 9) { state.talk = null; el.hidden = true; }
    else {
      el.style.left = `${((_hp.x + 1) / 2) * canvas.clientWidth}px`;
      el.style.top = `${((1 - _hp.y) / 2) * canvas.clientHeight}px`;
    }
  }
}

function sounds(dt) {
  if (!audio.ctx) return;
  const f = feetPos();
  const near = traffic?.nearest(f);
  audio.setLevels({
    rain: weather.cur.rain, wind: weather.cur.wind, traffic: near ? Math.max(0, 1 - near.d / 80) : 0,
    engineDist: near?.d ?? 1e9, engineSpeed: near?.v.speed ?? 0,
  });
  for (const p of pigeons.events.splice(0)) audio.flutter(p.distanceTo(camera.position), panOf(p));
  if (Math.random() < dt * 0.25 && weather.cur.rain < 0.2) {
    const b = pigeons.birds[(Math.random() * pigeons.birds.length) | 0];
    if (b.state === 'ground') audio.coo(b.p.distanceTo(camera.position), panOf(b.p));
  }
  state.bellT -= dt;
  if (state.bellT <= 0) {
    state.bellT = 240;
    const cat = toThree(61, 45, 40);
    audio.bells(3, cat.distanceTo(camera.position), panOf(cat));
  }
}

// botones
$('btn-fly').addEventListener('click', toggleFly);
$('btn-rt').addEventListener('click', togglePathTracing);
$('btn-places').addEventListener('click', () => $('places').toggleAttribute('data-open'));
$('btn-weather').addEventListener('click', () => $('weather').toggleAttribute('data-open'));
$('btn-jump').addEventListener('click', jump);
$('btn-run').addEventListener('click', () => { state.runToggle = !state.runToggle; $('btn-run').setAttribute('aria-pressed', String(state.runToggle)); });
$('btn-corn').addEventListener('click', throwCorn);
$('btn-talk').addEventListener('click', talk);
$('btn-sound').addEventListener('click', () => {
  audio.start();
  audio.setMuted(!audio.muted);
  $('btn-sound').setAttribute('aria-pressed', String(!audio.muted));
});
document.querySelectorAll('[data-w]').forEach((b) => b.addEventListener('click', () => {
  weather.setAuto(false); $('w-auto').setAttribute('aria-pressed', 'false'); weather.set(b.dataset.w);
}));
$('w-auto').addEventListener('click', () => {
  weather.setAuto(!weather.auto);
  $('w-auto').setAttribute('aria-pressed', String(weather.auto));
  updateWeatherUI(weather.name);
});
$('q-alta').addEventListener('click', () => { state.quality = 'alta'; applyQuality(); });
$('q-media').addEventListener('click', () => { state.quality = 'media'; applyQuality(); });
$('btn-full').addEventListener('click', () => {
  const el = document.documentElement;
  if (!document.fullscreenElement) el.requestFullscreen?.().catch(() => {});
  else document.exitFullscreen?.();
});
$('start').addEventListener('click', () => {
  $('intro').hidden = true;
  audio.start();
  $('btn-sound').setAttribute('aria-pressed', 'true');
  if (!coarse) canvas.requestPointerLock?.()?.catch?.(() => {});
});

// ------------------------------------------------------------------ bucle
const timer = new THREE.Timer();
let frame = 0;
function loop(ts) {
  requestAnimationFrame(loop);
  timer.update(ts);
  const dt = Math.min(0.05, timer.getDelta());
  state.time += dt;
  G.uTime.value = state.time;
  const ptIdle = state.pathTracing;
  if (!ptIdle || state.keys.size || state.touchMove.lengthSq()) {
    const sub = 5;
    for (let i = 0; i < sub; i++) stepPhysics(dt / sub);
    if (!state.fly && traffic) { traffic.pushPlayer(player.position, CAPSULE.radius); people.pushPlayer(player.position, CAPSULE.radius); }
  }
  updateCamera(dt);
  const f = feetPos();
  if (!ptIdle) {
    const wc = weather.update(dt, { camera, pathTracing: false, groundY: f.y });
    traffic.setHeadlights(wc.lights);
    traffic.update(dt, f, (v) => audio.horn(v.pos.distanceTo(camera.position), panOf(v.pos)), people.people);
    pigeons.update(dt, { player: f, playerSpeed: Math.hypot(state.move.x, state.move.z), flying: state.fly });
    people.update(dt, { player: f, rain: wc.rain });
    finishPass.uniforms.uTime.value = state.time % 10;
  }
  if (state.pathTracing && pathTracer) {
    if (state.moved) { pathTracer.updateCamera(); state.moved = false; }
    pathTracer.renderSample();
    $('rt-status').textContent = `Trazado de rayos · ${Math.floor(pathTracer.samples)} muestras`;
  } else {
    composer.render(dt);
    state.moved = false;
  }
  interactions(dt);
  sounds(dt);
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
    updateWeatherUI('soleado');
    const c0 = state.meta.cameras.Cam_Referencia;
    placePlayer(c0.loc, [c0.target[0], c0.target[1], 6]);
    $('loading').hidden = true;
    $('intro').hidden = false;
    window.__sim = { state, camera, renderer, scene, placePlayer, togglePathTracing, goTo, G,
      weather: () => weather, traffic: () => traffic, pigeons: () => pigeons, people: () => people };
    requestAnimationFrame(loop);
  } catch (e) {
    console.error(e);
    fatal('Error al cargar la escena: ' + (e?.message || e));
  }
})();
