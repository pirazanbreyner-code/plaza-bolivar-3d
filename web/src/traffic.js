// Trafico: carros, taxis, buses del SITP y TransMilenio sobre la red vial real.
// Cada tipo de vehiculo es un InstancedMesh para la carroceria (color por instancia) y otro para
// vidrios, plasticos y luces; las ruedas son un InstancedMesh aparte para poder girarlas.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { sampleEdge } from './roads.js';
import { enhance } from './materials.js';

// ------------------------------------------------------------------ geometria
// perfil lateral (x = largo, y = alto) extruido en z (ancho) con bordes redondeados
function extrudeProfile(points, width, bevel = 0.05) {
  const s = new THREE.Shape();
  s.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i++) {
    const p = points[i];
    if (p.length === 4) s.absarc(p[0], p[1], p[2], p[3][0], p[3][1], false);  // arco de rueda (por encima)
    else s.lineTo(p[0], p[1]);
  }
  s.closePath();
  const g = new THREE.ExtrudeGeometry(s, {
    depth: width - 2 * bevel, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel * 0.9,
    bevelSegments: 3, curveSegments: 10,
  });
  g.translate(0, 0, -(width - 2 * bevel) / 2);
  return g;
}

function box(w, h, d, x, y, z) {
  const g = new THREE.BoxGeometry(w, h, d);
  g.translate(x, y, z);
  return g;
}

const ARC = (cx, r) => [cx, 0.3, r, [0, Math.PI]];

// grupos de material de la geometria "resto": 0 vidrio, 1 plastico, 2 faro, 3 stop, 4 cromo, 5 letrero
function rest(parts) {
  const geoms = [], groups = [];
  for (const [g, m] of parts) {
    const ng = g.index ? g.toNonIndexed() : g;
    for (const k of Object.keys(ng.attributes)) if (!['position', 'normal', 'uv'].includes(k)) ng.deleteAttribute(k);
    geoms.push(ng); groups.push(m);
  }
  const merged = mergeGeometries(geoms, true);
  merged.groups.forEach((gr, i) => { gr.materialIndex = groups[i]; });
  return merged;
}

function carModel(kind, extra = () => []) {
  // dimensiones (m) aproximadas de modelos comunes en Bogota
  const D = {
    sedan: { L: 4.45, W: 1.74, wheelX: 1.32, wr: 0.31 },
    hatch: { L: 3.65, W: 1.62, wheelX: 1.18, wr: 0.29 },
    suv: { L: 4.55, W: 1.82, wheelX: 1.38, wr: 0.36 },
  }[kind];
  const { L, W, wheelX } = D;
  const h = L / 2;
  let body, glass, roof;
  if (kind === 'sedan') {
    body = [[-h, 0.38], [-h, 0.86], [-h + 0.2, 0.96], [-1.15, 1.0], [1.0, 0.98], [h - 0.2, 0.82], [h, 0.66], [h, 0.38],
      [wheelX + 0.42, 0.3], ARC(wheelX, 0.4), [-wheelX + 0.42, 0.3], ARC(-wheelX, 0.4), [-h + 0.05, 0.3]];
    glass = [[-1.12, 0.97], [-0.55, 1.4], [0.42, 1.41], [1.02, 0.96]];
    roof = [[-0.62, 1.38], [0.48, 1.39], [0.42, 1.45], [-0.55, 1.44]];
  } else if (kind === 'hatch') {
    body = [[-h, 0.38], [-h, 0.95], [-h + 0.12, 1.0], [0.75, 1.0], [h - 0.15, 0.86], [h, 0.7], [h, 0.38],
      [wheelX + 0.4, 0.3], ARC(wheelX, 0.38), [-wheelX + 0.4, 0.3], ARC(-wheelX, 0.38), [-h + 0.05, 0.3]];
    glass = [[-h + 0.08, 0.99], [-h + 0.25, 1.45], [0.25, 1.5], [0.8, 0.99]];
    roof = [[-h + 0.24, 1.43], [0.27, 1.48], [0.22, 1.54], [-h + 0.3, 1.5]];
  } else {
    body = [[-h, 0.45], [-h, 1.05], [-h + 0.15, 1.12], [1.05, 1.12], [h - 0.15, 1.0], [h, 0.8], [h, 0.45],
      [wheelX + 0.47, 0.36], ARC(wheelX, 0.45), [-wheelX + 0.47, 0.36], ARC(-wheelX, 0.45), [-h + 0.05, 0.36]];
    glass = [[-h + 0.12, 1.1], [-h + 0.22, 1.66], [0.55, 1.68], [1.1, 1.1]];
    roof = [[-h + 0.2, 1.64], [0.58, 1.66], [0.5, 1.74], [-h + 0.25, 1.72]];
  }
  const bodyG = mergeGeometries([extrudeProfile(body, W), extrudeProfile(roof, W - 0.08, 0.03)].map((g) => {
    g.deleteAttribute('uv'); return g;
  }), false);
  const yl = kind === 'suv' ? 0.85 : 0.72;
  const parts = [
    [extrudeProfile(glass, W - 0.1, 0.03), 0],
    [box(0.18, 0.18, W - 0.06, h - 0.02, 0.45, 0), 1], [box(0.18, 0.18, W - 0.06, -h + 0.02, 0.45, 0), 1],
    [box(0.06, 0.12, 0.34, h + 0.01, yl, W / 2 - 0.3), 2], [box(0.06, 0.12, 0.34, h + 0.01, yl, -W / 2 + 0.3), 2],
    [box(0.05, 0.12, 0.3, -h - 0.01, yl + 0.08, W / 2 - 0.25), 3], [box(0.05, 0.12, 0.3, -h - 0.01, yl + 0.08, -W / 2 + 0.25), 3],
    [box(0.04, 0.12, 0.7, h + 0.02, 0.56, 0), 4],
    [box(0.12, 0.08, 0.04, 0.95, 0.95, W / 2 + 0.03), 1], [box(0.12, 0.08, 0.04, 0.95, 0.95, -W / 2 - 0.03), 1],
    ...extra(W),
  ];
  return { body: bodyG, rest: rest(parts), L, W, wheels: [[wheelX, W / 2 - 0.12], [wheelX, -W / 2 + 0.12], [-wheelX, W / 2 - 0.12], [-wheelX, -W / 2 + 0.12]], wr: D.wr };
}

function taxiModel() {
  // letrero en el techo y franja de cuadros negros a los lados (taxis amarillos de Bogota)
  return carModel('hatch', (W) => {
    const parts = [[box(0.22, 0.14, 0.62, -0.25, 1.6, 0), 5]];
    for (let i = 0; i < 9; i++) for (const s of [1, -1]) parts.push([box(0.12, 0.06, 0.02, -1.0 + i * 0.24, 0.84 + (i % 2) * 0.06, s * (W / 2 + 0.005)), 1]);
    return parts;
  });
}

function busModel(kind) {
  const tm = kind === 'tm';
  const L = tm ? 18.0 : 11.2, W = 2.5, H = 3.1, h = L / 2;
  const prof = [[-h, 0.35], [-h, H - 0.15], [-h + 0.2, H], [h - 0.25, H], [h, H - 0.25], [h, 0.35],
    [h - 1.6, 0.35], ARC(h - 2.3, 0.66), [-h + 3.0, 0.35], ARC(-h + 2.4, 0.66), [-h + 0.1, 0.35]];
  let bodyG = extrudeProfile(prof.map((p) => (p.length === 4 ? [p[0], 0.4, p[2], p[3]] : p)), W, 0.08);
  bodyG.deleteAttribute('uv');
  const parts = [];
  // banda de ventanas
  const wins = tm ? [[-h + 0.4, -0.7], [0.7, h - 2.3]] : [[-h + 0.4, h - 2.2]];
  for (const [a, b] of wins) for (const s of [1, -1]) parts.push([box(b - a, 1.0, 0.04, (a + b) / 2, 2.1, s * (W / 2 + 0.01)), 0]);
  parts.push([box(0.05, 1.2, W - 0.3, h + 0.01, 2.0, 0), 0]);                     // parabrisas
  parts.push([box(0.05, 0.6, W - 0.5, -h - 0.01, 2.3, 0), 0]);                    // vidrio trasero
  parts.push([box(0.06, 0.15, 0.4, h + 0.02, 0.7, W / 2 - 0.35), 2], [box(0.06, 0.15, 0.4, h + 0.02, 0.7, -W / 2 + 0.35), 2]);
  parts.push([box(0.06, 0.25, 0.25, -h - 0.02, 0.9, W / 2 - 0.3), 3], [box(0.06, 0.25, 0.25, -h - 0.02, 0.9, -W / 2 + 0.3), 3]);
  parts.push([box(0.25, 0.35, W - 0.2, h + 0.05, 0.5, 0), 1], [box(0.2, 0.35, W - 0.2, -h - 0.05, 0.5, 0), 1]);
  parts.push([box(0.04, 0.3, 1.6, h + 0.02, H - 0.35, 0), 5]);                    // letrero de ruta
  if (tm) parts.push([box(0.8, H - 0.6, W - 0.1, -0.15, (H + 0.3) / 2, 0), 1]);   // fuelle de la articulacion
  // puertas (vidrio oscuro de piso a techo) en el lado derecho (z negativo = derecha del avance)
  const doors = tm ? [h - 2.0, 2.5, -4.0, -h + 3.5] : [h - 1.2, 0.4];
  for (const x of doors) parts.push([box(1.1, 2.3, 0.04, x, 1.55, -(W / 2 + 0.015)), 0]);
  const wheels = tm
    ? [[h - 2.3, W / 2 - 0.25], [h - 2.3, -W / 2 + 0.25], [1.5, W / 2 - 0.25], [1.5, -W / 2 + 0.25], [-h + 2.4, W / 2 - 0.25], [-h + 2.4, -W / 2 + 0.25]]
    : [[h - 2.3, W / 2 - 0.25], [h - 2.3, -W / 2 + 0.25], [-h + 2.4, W / 2 - 0.25], [-h + 2.4, -W / 2 + 0.25]];
  return { body: bodyG, rest: rest(parts), L, W, wheels, wr: 0.5 };
}

function wheelGeom(r, w) {
  const tire = new THREE.CylinderGeometry(r, r, w, 20, 1);
  tire.rotateX(Math.PI / 2);
  const rim = new THREE.CylinderGeometry(r * 0.62, r * 0.62, w + 0.012, 12, 1);
  rim.rotateX(Math.PI / 2);
  const g = mergeGeometries([tire, rim], true);
  return g;
}

// ------------------------------------------------------------------ materiales
function makeMaterials() {
  const paint = enhance(new THREE.MeshPhysicalMaterial({
    color: 0xffffff, roughness: 0.32, metalness: 0.35, clearcoat: 1, clearcoatRoughness: 0.06,
  }), { grime: 0 });
  const glass = enhance(new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(0.012, 0.016, 0.02), roughness: 0.04, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.02,
  }), { grime: 0 });
  const plastic = enhance(new THREE.MeshStandardMaterial({ color: new THREE.Color(0.018, 0.018, 0.02), roughness: 0.6 }), { grime: 0 });
  const head = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: new THREE.Color(1, 0.95, 0.85), emissiveIntensity: 0.4, roughness: 0.15 });
  const tail = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.3, 0.01, 0.01), emissive: new THREE.Color(1, 0.04, 0.02), emissiveIntensity: 0.25, roughness: 0.2 });
  const chrome = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.6, 0.6, 0.62), metalness: 1, roughness: 0.18 });
  const sign = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.9, 0.9, 0.85), emissive: new THREE.Color(1, 0.85, 0.3), emissiveIntensity: 0.15, roughness: 0.4 });
  const tire = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.02, 0.02, 0.022), roughness: 0.9 });
  const rim = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.45, 0.46, 0.48), metalness: 1, roughness: 0.3 });
  return { paint, rest: [glass, plastic, head, tail, chrome, sign], wheel: [tire, rim], head, tail };
}

// colores frecuentes (lineales)
const CAR_COLORS = [
  [0.78, 0.78, 0.76], [0.78, 0.78, 0.76], [0.8, 0.8, 0.8], [0.42, 0.43, 0.45], [0.42, 0.43, 0.45], [0.12, 0.12, 0.13],
  [0.02, 0.02, 0.022], [0.02, 0.02, 0.022], [0.38, 0.02, 0.02], [0.03, 0.07, 0.25], [0.2, 0.18, 0.15], [0.05, 0.12, 0.08],
];
const TAXI = [0.86, 0.55, 0.0];
const SITP = [0.02, 0.14, 0.42];
const TM_RED = [0.5, 0.02, 0.015];

const SPEED = { primary: 12.5, secondary: 11, tertiary: 9.5, residential: 8, unclassified: 8, unknown: 7 };
const tmp = { pos: new THREE.Vector3(), dir: new THREE.Vector3(), right: new THREE.Vector3() };
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(1, 1, 1), _e = new THREE.Euler();
const _p = new THREE.Vector3(), _w = new THREE.Matrix4(), _r = new THREE.Matrix4();

export class Traffic {
  constructor(scene, roads, opts = {}) {
    this.scene = scene;
    this.edges = roads.edges;
    this.nodes = roads.nodes;
    this.mats = makeMaterials();
    this.types = {};
    this.vehicles = [];
    this.headlights = 0.4;
    const counts = { sedan: 26, hatch: 16, suv: 12, taxi: 22, bus: 5, tm: 4 };
    const parked = { sedan: 14, hatch: 10, suv: 8, taxi: 4, bus: 0, tm: 0 };
    this.carEdges = this.edges.filter((e) => !e.bus);
    this.busEdges = this.edges.filter((e) => e.bus);
    this.bigEdges = this.carEdges.filter((e) => e.cls === 'primary' || e.cls === 'tertiary' || e.cls === 'secondary');
    // carros estacionados: solo en calles residenciales de un sentido, junto al anden derecho
    this.parkEdges = this.carEdges.filter((e) => e.cls === 'residential' && e.ow && e.lanes >= 2 && e.len > 25);
    for (const e of this.parkEdges) e.hasParked = true;
    for (const kind of Object.keys(counts)) {
      const model = kind === 'taxi' ? taxiModel() : kind === 'bus' || kind === 'tm' ? busModel(kind) : carModel(kind);
      if (kind === 'tm' && !this.busEdges.length) continue;
      const n = counts[kind] + parked[kind];
      const body = new THREE.InstancedMesh(model.body, this.mats.paint, n);
      const restM = new THREE.InstancedMesh(model.rest, this.mats.rest, n);
      const wheels = new THREE.InstancedMesh(wheelGeom(model.wr, kind === 'bus' || kind === 'tm' ? 0.32 : 0.21), this.mats.wheel, n * model.wheels.length);
      for (const im of [body, restM, wheels]) {
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        im.castShadow = true; im.receiveShadow = true;
        im.frustumCulled = false;
        im.name = `trafico:${kind}`;
        scene.add(im);
      }
      this.types[kind] = { model, body, rest: restM, wheels, n, used: 0 };
    }
    this.spawnAll(counts, parked);
  }

  pickEdge(list) {
    let total = 0;
    for (const e of list) total += e.len;
    let r = Math.random() * total;
    for (const e of list) { r -= e.len; if (r <= 0) return e; }
    return list[list.length - 1];
  }

  spawnAll(counts, parked) {
    const color = new THREE.Color();
    for (const [kind, n] of Object.entries(counts)) {
      const T = this.types[kind]; if (!T) continue;
      for (let i = 0; i < n + (parked[kind] || 0); i++) {
        const isParked = i >= n;
        const list = kind === 'tm' ? this.busEdges : kind === 'bus' ? (this.bigEdges.length ? this.bigEdges : this.carEdges)
          : isParked ? this.parkEdges : this.carEdges;
        if (!list.length) continue;
        const e = this.pickEdge(list);
        const dir = e.ow ? 1 : Math.random() < 0.5 ? 1 : -1;
        if (isParked && !list.length) continue;
        const v = {
          kind, idx: T.used++, edge: e, dir, s: Math.random() * e.len, lane: e.ow ? Math.floor(Math.random() * e.lanes) : 0,
          speed: 0, vmax: (SPEED[e.cls] || 8) * (0.85 + Math.random() * 0.3), L: T.model.L, W: T.model.W,
          parked: isParked, spin: 0, wait: 0, latOff: null, yaw: null, horn: 0,
          pos: new THREE.Vector3(), fwd: new THREE.Vector3(1, 0, 0),
        };
        if (kind === 'bus' || kind === 'tm') { v.vmax *= 0.85; v.lane = e.lanes - 1; }
        const c = kind === 'taxi' ? TAXI : kind === 'bus' ? SITP : kind === 'tm' ? TM_RED : CAR_COLORS[(Math.random() * CAR_COLORS.length) | 0];
        T.body.setColorAt(v.idx, color.setRGB(c[0], c[1], c[2]));
        if (isParked) {
          v.s = 8 + Math.random() * (e.len - 16);
          v.parkSide = 1;
        }
        this.vehicles.push(v);
      }
      T.body.count = T.used; T.rest.count = T.used; T.wheels.count = T.used * T.model.wheels.length;
      if (T.body.instanceColor) T.body.instanceColor.needsUpdate = true;
    }
    // separar vehiculos solapados en la misma arista
    this.place(0, true);
  }

  laneOffset(v) {
    const e = v.edge;
    if (v.parked) return e.w / 2 + 0.15 - v.W / 2 - 0.15;
    if (!e.ow) return e.w / 4 + 0.1;
    const lw = e.w / e.lanes;
    const lane = e.hasParked ? 0 : v.lane;
    return -e.w / 2 + (lane + 0.5) * lw;
  }

  nextEdge(v) {
    const endKey = v.dir > 0 ? v.edge.k1 : v.edge.k0;
    const node = this.nodes.get(endKey);
    let opts = node ? node.out.filter((o) => !(o.e === v.edge)) : [];
    if (v.kind === 'tm') opts = opts.filter((o) => o.e.bus);
    else opts = opts.filter((o) => !o.e.bus);
    if (v.kind === 'bus') { const big = opts.filter((o) => o.e.cls !== 'residential'); if (big.length) opts = big; }
    if (!opts.length) {
      if (!v.edge.ow) { v.dir = -v.dir; v.s = 0; return true; }     // calle ciega: dar la vuelta
      return false;
    }
    const o = opts[(Math.random() * opts.length) | 0];
    v.edge = o.e; v.dir = o.dir; v.s = 0;
    v.vmax = (SPEED[o.e.cls] || 8) * (0.85 + Math.random() * 0.3) * (v.kind === 'bus' || v.kind === 'tm' ? 0.85 : 1);
    v.lane = o.e.ow ? (v.kind === 'bus' || v.kind === 'tm' ? o.e.lanes - 1 : Math.floor(Math.random() * o.e.lanes)) : 0;
    return true;
  }

  respawn(v, player) {
    const list = v.kind === 'tm' ? this.busEdges : this.carEdges;
    for (let k = 0; k < 20; k++) {
      const e = this.pickEdge(list);
      const p = e.pts[0];
      if (!player || p.distanceTo(player) > 90) { v.edge = e; v.dir = e.ow ? 1 : 1; v.s = 0; v.speed = 0; v.latOff = null; v.yaw = null; return; }
    }
  }

  /** dt en s; player = posicion de los pies del jugador (Vector3) */
  update(dt, player, onHorn) {
    // ordenar por arista para el seguimiento
    const byEdge = new Map();
    for (const v of this.vehicles) {
      if (v.parked) continue;
      const k = v.edge;
      if (!byEdge.has(k)) byEdge.set(k, []);
      byEdge.get(k).push(v);
    }
    for (const v of this.vehicles) {
      if (v.parked) continue;
      const e = v.edge;
      let target = v.vmax;
      // vehiculo de adelante en la misma arista, sentido y carril
      let gap = 1e9;
      for (const o of byEdge.get(e) || []) {
        if (o === v || o.dir !== v.dir || (e.ow && o.lane !== v.lane)) continue;
        const d = o.s - v.s - (o.L + v.L) / 2;
        if (o.s > v.s && d < gap) gap = d;
      }
      const remaining = e.len - v.s;
      if (remaining < 8) target = Math.min(target, 5.5);          // despacio en los cruces
      const safe = 2.5 + v.speed * 1.1;
      if (gap < safe) target = Math.min(target, Math.max(0, (gap - 2.0) * 1.2));
      // peaton (jugador) en el carril
      if (player) {
        _p.subVectors(player, v.pos);
        const f = _p.dot(v.fwd), l = Math.abs(_p.x * -v.fwd.z + _p.z * v.fwd.x);
        if (f > 0 && f < 10 + v.speed * 1.4 + v.L / 2 && l < v.W / 2 + 0.9 && Math.abs(_p.y) < 3) {
          target = Math.min(target, Math.max(0, (f - v.L / 2 - 2.5) * 0.9));
          if (v.speed < 0.5 && f < v.L / 2 + 6) {
            v.horn -= dt;
            if (v.horn <= 0) { v.horn = 4 + Math.random() * 5; onHorn?.(v); }
          }
        }
      }
      // cruce ocupado
      if (remaining < 9) {
        const nk = v.dir > 0 ? e.k1 : e.k0;
        const node = this.nodes.get(nk);
        if (node) {
          if (node.busyBy && node.busyBy !== v && node.busyTime > 0) {
            v.wait += dt;
            if (v.wait < 5) target = Math.min(target, Math.max(0, (remaining - 7) * 0.8));
          } else if (remaining < 6) { node.busyBy = v; node.busyTime = 2.2; v.wait = 0; }
        }
      }
      if (target > v.speed) v.speed = Math.min(target, v.speed + 2.6 * dt);
      else v.speed = Math.max(target, v.speed - 7 * dt);
      v.s += v.speed * dt;
      v.spin += (v.speed * dt) / this.types[v.kind].model.wr;
      if (v.s > e.len) {
        const over = v.s - e.len;
        if (!this.nextEdge(v)) this.respawn(v, player);
        else v.s = over;
      }
    }
    for (const n of this.nodes.values()) if (n.busyTime > 0) { n.busyTime -= dt; if (n.busyTime <= 0) n.busyBy = null; }
    this.place(dt, false);
  }

  place(dt, snap) {
    const dirty = new Set();
    for (const v of this.vehicles) {
      const T = this.types[v.kind];
      sampleEdge(v.edge, Math.min(v.s, v.edge.len), v.dir, tmp);
      const target = this.laneOffset(v);
      if (v.latOff === null || snap) v.latOff = target;
      else v.latOff += THREE.MathUtils.clamp(target - v.latOff, -1.6 * dt, 1.6 * dt);
      const yawT = Math.atan2(tmp.dir.x, tmp.dir.z);
      if (v.yaw === null || snap) v.yaw = yawT;
      else {
        let d = yawT - v.yaw;
        d = Math.atan2(Math.sin(d), Math.cos(d));
        v.yaw += d * Math.min(1, dt * 5);
      }
      v.fwd.set(Math.sin(v.yaw), 0, Math.cos(v.yaw));
      v.pos.copy(tmp.pos).addScaledVector(tmp.right, v.latOff);
      const pitch = Math.asin(THREE.MathUtils.clamp(tmp.dir.y, -0.3, 0.3));
      // el modelo apunta a +x: rotar -90 grados para que +x quede en la direccion de avance
      _e.set(0, v.yaw - Math.PI / 2, pitch, 'YXZ');
      _q.setFromEuler(_e);
      _m.compose(v.pos, _q, _s);
      T.body.setMatrixAt(v.idx, _m);
      T.rest.setMatrixAt(v.idx, _m);
      const wl = T.model.wheels;
      for (let k = 0; k < wl.length; k++) {
        _r.makeRotationZ(-v.spin);
        _w.makeTranslation(wl[k][0], T.model.wr, wl[k][1]).multiply(_r);
        _w.premultiply(_m);
        T.wheels.setMatrixAt(v.idx * wl.length + k, _w);
      }
      dirty.add(T);
    }
    for (const T of dirty) {
      T.body.instanceMatrix.needsUpdate = true; T.rest.instanceMatrix.needsUpdate = true; T.wheels.instanceMatrix.needsUpdate = true;
    }
  }

  setHeadlights(k) {
    this.mats.head.emissiveIntensity = 0.4 + 5 * k;
    this.mats.tail.emissiveIntensity = 0.25 + 2.5 * k;
    this.mats.rest[5].emissiveIntensity = 0.15 + 2 * k;
  }

  /** Empuja al jugador fuera de los vehiculos (cajas orientadas) */
  pushPlayer(p, radius) {
    for (const v of this.vehicles) {
      const dx = p.x - v.pos.x, dz = p.z - v.pos.z;
      if (dx * dx + dz * dz > 100 || p.y - v.pos.y > 3.2 || p.y < v.pos.y - 1) continue;
      const f = dx * v.fwd.x + dz * v.fwd.z, l = dx * -v.fwd.z + dz * v.fwd.x;
      const hx = v.L / 2 + radius, hz = v.W / 2 + radius;
      if (Math.abs(f) < hx && Math.abs(l) < hz) {
        const px = hx - Math.abs(f), pz = hz - Math.abs(l);
        if (px < pz) { const s = Math.sign(f) * px; p.x += v.fwd.x * s; p.z += v.fwd.z * s; }
        else { const s = Math.sign(l) * pz; p.x += -v.fwd.z * s; p.z += v.fwd.x * s; }
      }
    }
  }

  nearest(p) {
    let best = null, bd = 1e9;
    for (const v of this.vehicles) {
      if (v.parked) continue;
      const d = v.pos.distanceToSquared(p);
      if (d < bd) { bd = d; best = v; }
    }
    return best ? { v: best, d: Math.sqrt(bd) } : null;
  }
}
