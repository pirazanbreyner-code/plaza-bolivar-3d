// Calles reales (OSM via Overture, scripts/web_roads.py): calzadas de asfalto, andenes con sardinel,
// lineas pintadas, cebras en los cruces, y el grafo de carriles para el trafico.
// Coordenadas del modelo (u, v) -> three (x, y, z) = (u, y, -v).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { enhance } from './materials.js';

export const VEHICULAR = new Set(['primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'unknown']);
const SIDEWALK_W = 2.6;
const CURB_H = 0.15;
const TRIM = 7.5;          // sin lineas ni andenes en los ultimos metros antes de un cruce

// Cra 8 frente a la plaza (calzada de Blender, u -50.5..-43; la losa base de -0.12 m la cubre)
const CORE_CRA8 = { u: -46.75, y: -0.115, top: [-52.68, 67.5], bottom: [-49.72, -68.0] };   // sobre la losa base (-0.12)

const key = (u, v) => `${Math.round(u * 2) / 2},${Math.round(v * 2) / 2}`;

function densify(p, step) {
  const out = [p[0]];
  for (let i = 1; i < p.length; i++) {
    const [u0, v0] = p[i - 1], [u1, v1] = p[i];
    const L = Math.hypot(u1 - u0, v1 - v0), n = Math.max(1, Math.ceil(L / step));
    for (let k = 1; k <= n; k++) out.push([u0 + ((u1 - u0) * k) / n, v0 + ((v1 - v0) * k) / n]);
  }
  return out;
}

function frames(p) {
  // tangente y normal izquierda (en u, v) por vertice, con inglete limitado
  const n = p.length, T = [], N = [], cum = [0];
  for (let i = 1; i < n; i++) cum.push(cum[i - 1] + Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]));
  for (let i = 0; i < n; i++) {
    const a = p[Math.max(0, i - 1)], b = p[Math.min(n - 1, i + 1)];
    let tu = b[0] - a[0], tv = b[1] - a[1];
    const l = Math.hypot(tu, tv) || 1; tu /= l; tv /= l;
    let mit = 1;
    if (i > 0 && i < n - 1) {
      const su = p[i][0] - p[i - 1][0], sv = p[i][1] - p[i - 1][1], sl = Math.hypot(su, sv) || 1;
      mit = 1 / Math.max(0.5, (-sv / sl) * -tv + (su / sl) * tu);
    }
    T.push([tu, tv]); N.push([-tv * mit, tu * mit]);
  }
  return { T, N, cum, len: cum[n - 1] };
}

// cinta entre los desplazamientos laterales a y b (m, izquierda positiva), entre s0 y s1 a lo largo
function ribbon(p, F, ys, a, b, s0, s1, lift, out) {
  const pos = [], uv = [], idx = [];
  let k = 0;
  for (let i = 0; i < p.length; i++) {
    const s = F.cum[i];
    if (s < s0 - 1e-6 || s > s1 + 1e-6) continue;
    const [nu, nv] = F.N[i];
    const y = ys[i] + lift;
    pos.push(p[i][0] + nu * a, y, -(p[i][1] + nv * a), p[i][0] + nu * b, y, -(p[i][1] + nv * b));
    uv.push(s, a, s, b);
    if (k > 0) { const j = 2 * (k - 1); idx.push(j, j + 1, j + 2, j + 1, j + 3, j + 2); }
    k++;
  }
  if (k < 2) return;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  // orientar hacia arriba
  g.computeVertexNormals();
  const nrm = g.getAttribute('normal');
  if (nrm.count && nrm.getY(0) < 0) {
    for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }
    g.setIndex(idx); g.computeVertexNormals();
  }
  out.push(g);
}

// cara vertical (sardinel) a lo largo del desplazamiento a, de y0 a y1 relativos
function curb(p, F, ys, a, s0, s1, y0, y1, out, flip) {
  const pos = [], uv = [], idx = [];
  let k = 0;
  for (let i = 0; i < p.length; i++) {
    const s = F.cum[i];
    if (s < s0 - 1e-6 || s > s1 + 1e-6) continue;
    const [nu, nv] = F.N[i];
    const x = p[i][0] + nu * a, z = -(p[i][1] + nv * a);
    pos.push(x, ys[i] + y0, z, x, ys[i] + y1, z);
    uv.push(s, 0, s, y1 - y0);
    if (k > 0) {
      const j = 2 * (k - 1);
      if (flip) idx.push(j, j + 2, j + 1, j + 1, j + 2, j + 3); else idx.push(j, j + 1, j + 2, j + 1, j + 3, j + 2);
    }
    k++;
  }
  if (k < 2) return;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  out.push(g);
}

// rectangulo orientado (marcas): centro en s, desplazamiento lateral c, largo L (a lo largo), ancho W
function quadAt(p, F, ys, s, c, L, W, lift, out) {
  // ubicar segmento
  let i = 1;
  while (i < p.length - 1 && F.cum[i] < s) i++;
  const t = (s - F.cum[i - 1]) / Math.max(1e-6, F.cum[i] - F.cum[i - 1]);
  const u = p[i - 1][0] + (p[i][0] - p[i - 1][0]) * t, v = p[i - 1][1] + (p[i][1] - p[i - 1][1]) * t;
  const y = ys[i - 1] + (ys[i] - ys[i - 1]) * t + lift;
  let tu = p[i][0] - p[i - 1][0], tv = p[i][1] - p[i - 1][1];
  const l = Math.hypot(tu, tv) || 1; tu /= l; tv /= l;
  const nu = -tv, nv = tu;
  const cu = u + nu * c, cv = v + nv * c;
  const corners = [[-L / 2, -W / 2], [L / 2, -W / 2], [L / 2, W / 2], [-L / 2, W / 2]]
    .map(([a, b]) => [cu + tu * a + nu * b, y, -(cv + tv * a + nv * b)]);
  out.push(...corners[0], ...corners[1], ...corners[2], ...corners[0], ...corners[2], ...corners[3]);
}

function polyGeom(arr) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
  const n = new Float32Array(arr.length);
  for (let i = 1; i < n.length; i += 3) n[i] = 1;
  g.setAttribute('normal', new THREE.BufferAttribute(n, 3));
  const uv = new Float32Array((arr.length / 3) * 2);
  for (let i = 0; i < arr.length / 3; i++) { uv[2 * i] = arr[3 * i]; uv[2 * i + 1] = arr[3 * i + 2]; }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return g;
}

/**
 * data: roads.json; heightAt(u, v) -> altura del terreno (y de three); mats: { asfalto, adoquin, anden, bordillo }
 * Devuelve { group, edges, nodes } con el grafo de carriles para el trafico.
 */
export function buildRoads(data, heightAt, mats) {
  const asph = [], ped = [], walk = [], curbs = [], white = [], yellow = [];
  // grado de cada extremo (solo vias vehiculares y peatonales)
  const deg = new Map();
  for (const r of data.roads) for (const q of [r.p[0], r.p[r.p.length - 1]]) {
    const k = key(q[0], q[1]); deg.set(k, (deg.get(k) || 0) + 1);
  }
  const width = new Map();   // ancho maximo que llega a cada nodo (para las cebras)
  for (const r of data.roads) for (const q of [r.p[0], r.p[r.p.length - 1]]) {
    const k = key(q[0], q[1]); width.set(k, Math.max(width.get(k) || 0, r.w));
  }
  const edges = [];
  data.roads.forEach((r, ri) => {
    const p = densify(r.p, 5);
    const F = frames(p);
    if (F.len < 2) return;
    const ys = p.map(([u, v]) => heightAt(u, v));
    const veh = VEHICULAR.has(r.c) || r.bus;
    const k0 = key(p[0][0], p[0][1]), k1 = key(p[p.length - 1][0], p[p.length - 1][1]);
    const j0 = (deg.get(k0) || 0) >= 2, j1 = (deg.get(k1) || 0) >= 2;
    const lift = 0.07 + (ri % 5) * 0.006;
    const w = r.c === 'pedestrian' ? 9 : r.w;
    if (r.c === 'pedestrian') {
      ribbon(p, F, ys, w / 2, -w / 2, 0, F.len, 0.05 + (ri % 5) * 0.006, ped);
      return;
    }
    ribbon(p, F, ys, w / 2, -w / 2, 0, F.len, lift, asph);
    if (r.c === 'service' && !r.bus) return;
    // andenes con sardinel (no en los cruces)
    const s0 = j0 ? Math.min(F.len / 2, (width.get(k0) || w) / 2 + SIDEWALK_W + 0.5) : 0;
    const s1 = j1 ? Math.max(F.len / 2, F.len - ((width.get(k1) || w) / 2 + SIDEWALK_W + 0.5)) : F.len;
    if (s1 - s0 > 2 && !r.bus) {
      for (const side of [1, -1]) {
        const a = side * (w / 2), b = side * (w / 2 + SIDEWALK_W);
        ribbon(p, F, ys, side > 0 ? b : a, side > 0 ? a : b, s0, s1, lift + CURB_H, walk);
        curb(p, F, ys, a, s0, s1, lift - 0.02, lift + CURB_H, curbs, side > 0);
      }
    }
    // lineas pintadas
    const m0 = j0 ? TRIM : 1, m1 = F.len - (j1 ? TRIM : 1);
    const ml = lift + 0.012;
    if (m1 - m0 > 4 && veh) {
      const lanes = Math.max(1, Math.round(w / 3.3));
      if (!r.ow && !r.bus) {
        const dashed = r.c === 'residential' || r.c === 'unknown' || r.c === 'unclassified';
        for (let s = m0; s < m1; s += dashed ? 6 : 2) quadAt(p, F, ys, Math.min(s + (dashed ? 1.5 : 1), m1 - 0.5), 0, dashed ? 3 : 2.02, 0.13, ml, yellow);
      } else if (lanes > 1) {
        for (let l = 1; l < lanes; l++) {
          const c = -w / 2 + (w * l) / lanes;
          for (let s = m0; s < m1; s += 7.5) quadAt(p, F, ys, Math.min(s + 1.5, m1 - 0.5), c, 3, 0.12, ml, white);
        }
      }
      if (r.c === 'primary' || r.c === 'tertiary' || r.bus) {
        for (const c of [w / 2 - 0.3, -w / 2 + 0.3]) for (let s = m0; s < m1; s += 2) quadAt(p, F, ys, Math.min(s + 1, m1 - 0.5), c, 2.02, 0.12, ml, white);
      }
    }
    // cebras y lineas de pare en los cruces
    if (veh && !r.bus) {
      for (const [isStart, jn] of [[true, j0 && (deg.get(k0) || 0) >= 3], [false, j1 && (deg.get(k1) || 0) >= 3]]) {
        if (!jn || F.len < 14) continue;
        const sc = isStart ? 4.6 : F.len - 4.6;
        for (let c = -w / 2 + 0.6; c <= w / 2 - 0.5; c += 1.0) quadAt(p, F, ys, sc, c, 3.2, 0.5, ml, white);
        const sStop = isStart ? 7.0 : F.len - 7.0;
        if (!r.ow || !isStart) quadAt(p, F, ys, sStop, isStart ? w / 4 : -w / 4, 0.4, r.ow ? w : w / 2, ml, white);
      }
    }
    // grafo de trafico
    if (veh) edges.push(makeEdge(p, ys.map((y) => y + lift), r, k0, k1));
  });

  // Cra 8 frente a la plaza: rampas sobre la calzada de Blender y tramo sintetico para el trafico
  const c8 = [CORE_CRA8.top, [CORE_CRA8.u, 62], [CORE_CRA8.u, -62], CORE_CRA8.bottom];
  const yTop = heightAt(...CORE_CRA8.top) + 0.07, yBot = heightAt(...CORE_CRA8.bottom) + 0.07;
  for (const [a, b, ya] of [[[CORE_CRA8.u, 67.5], [CORE_CRA8.u, 60], yTop], [[CORE_CRA8.u, -67.5], [CORE_CRA8.u, -60], yBot]]) {
    const g = new THREE.PlaneGeometry(7.5, Math.abs(b[1] - a[1]));
    g.rotateX(-Math.PI / 2);
    const pos = g.getAttribute('position');
    for (let i = 0; i < pos.count; i++) {
      const vz = -pos.getZ(i) + (a[1] + b[1]) / 2;              // v del vertice
      const f = (vz - b[1]) / (a[1] - b[1]);                    // 1 en el borde del nucleo
      pos.setXYZ(i, pos.getX(i) + CORE_CRA8.u, CORE_CRA8.y + 0.004 + (ya - CORE_CRA8.y) * Math.max(0, f), -vz);
    }
    g.computeVertexNormals();
    const uv = g.getAttribute('uv');
    for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i), pos.getZ(i));
    asph.push(g);
  }
  // linea discontinua entre los dos carriles de la Cra 8 en el nucleo
  {
    const pp = [[CORE_CRA8.u, 60], [CORE_CRA8.u, -60]], F = frames(pp), ys = [CORE_CRA8.y, CORE_CRA8.y];
    for (let s = 1; s < F.len - 2; s += 7.5) quadAt(pp, F, ys, s + 1.5, 0, 3, 0.12, 0.01, white);
  }
  const ys8 = [yTop, CORE_CRA8.y + 0.005, CORE_CRA8.y + 0.005, yBot];
  edges.push(makeEdge(c8, ys8, { c: 'tertiary', w: 7.5, ow: 1, bus: 0, n: 'Carrera 8' },
    key(...CORE_CRA8.top), key(...CORE_CRA8.bottom)));

  const group = new THREE.Group();
  group.name = 'calles';
  const add = (geoms, mat, name, opts = {}) => {
    if (!geoms.length) return;
    const g = mergeGeometries(geoms.map((x) => (x.index ? x.toNonIndexed() : x)), false);
    const m = new THREE.Mesh(g, mat);
    m.name = name; m.receiveShadow = true; m.castShadow = !!opts.cast;
    group.add(m);
  };
  add(asph, mats.asfalto, 'calles:asfalto');
  add(ped, mats.adoquin, 'calles:adoquin');
  add(walk, mats.anden, 'calles:anden', { cast: true });
  add(curbs, mats.bordillo, 'calles:sardinel', { cast: true });
  const paint = (color) => enhance(new THREE.MeshStandardMaterial({
    color, roughness: 0.62, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
  }), { grime: 0, ground: true });
  if (white.length) add([polyGeom(white)], paint(new THREE.Color(0.62, 0.62, 0.6)), 'calles:lineas_blancas');
  if (yellow.length) add([polyGeom(yellow)], paint(new THREE.Color(0.62, 0.42, 0.04)), 'calles:lineas_amarillas');

  // nodos del grafo
  const nodes = new Map();
  for (const e of edges) for (const [k, end] of [[e.k0, 0], [e.k1, 1]]) {
    if (!nodes.has(k)) nodes.set(k, { key: k, out: [], pos: end ? e.pts[e.pts.length - 1] : e.pts[0], busyBy: null });
  }
  for (const e of edges) {
    nodes.get(e.k0).out.push({ e, dir: 1 });
    if (!e.ow) nodes.get(e.k1).out.push({ e, dir: -1 });
  }
  return { group, edges, nodes };
}

function makeEdge(p2, ys, r, k0, k1) {
  const pts = p2.map(([u, v], i) => new THREE.Vector3(u, ys[i], -v));
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
  const lanes = Math.max(1, Math.round(r.w / 3.3));
  return { pts, cum, len: cum[cum.length - 1], ow: !!r.ow, bus: !!r.bus, w: r.w, lanes, cls: r.c, name: r.n, k0, k1 };
}

/** Punto, direccion y lado derecho de una arista en la distancia s (en el sentido dir) */
export function sampleEdge(e, s, dir, out) {
  const d = dir > 0 ? s : e.len - s;
  let i = 1;
  while (i < e.pts.length - 1 && e.cum[i] < d) i++;
  const a = e.pts[i - 1], b = e.pts[i];
  const t = THREE.MathUtils.clamp((d - e.cum[i - 1]) / Math.max(1e-6, e.cum[i] - e.cum[i - 1]), 0, 1);
  out.pos.lerpVectors(a, b, t);
  out.dir.subVectors(b, a).normalize();
  if (dir < 0) out.dir.negate();
  out.right.set(-out.dir.z, 0, out.dir.x).normalize();
  return out;
}
