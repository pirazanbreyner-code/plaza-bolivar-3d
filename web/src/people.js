// Peatones: cuerpos articulados (10 piezas instanciadas) con ciclo de marcha procedural, grupos que
// conversan, gente que toma fotos, paraguas cuando llueve y dialogo con el jugador (tecla E).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// ranuras de color: 0 camisa/chaqueta, 1 pantalon, 2 piel, 3 pelo, 4 zapatos, 5 accesorio
function part(g, slot) {
  const ng = g.index ? g.toNonIndexed() : g;
  ng.deleteAttribute('uv');
  ng.setAttribute('slot', new THREE.BufferAttribute(new Float32Array(ng.getAttribute('position').count).fill(slot), 1));
  return ng;
}
const cap = (r, l, y, slot, sx = 1, sz = 1) => {
  const g = new THREE.CapsuleGeometry(r, l, 4, 10);
  g.scale(sx, 1, sz); g.translate(0, y, 0);
  return part(g, slot);
};

function bodyGeoms() {
  const trunk = mergeGeometries([
    cap(0.15, 0.06, 0.02, 1, 1.15, 0.8),                 // cadera
    cap(0.165, 0.3, 0.33, 0, 1.18, 0.72),                // torso
    part(new THREE.CylinderGeometry(0.05, 0.055, 0.1, 8).translate(0, 0.6, 0), 2),   // cuello
  ]);
  const head = new THREE.SphereGeometry(0.105, 14, 12); head.scale(0.92, 1.12, 1); head.translate(0, 0.11, 0.005);
  const hair = new THREE.SphereGeometry(0.112, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.52); hair.scale(0.93, 1.12, 1.02); hair.translate(0, 0.12, -0.008);
  const nose = new THREE.BoxGeometry(0.025, 0.04, 0.04); nose.translate(0, 0.1, 0.1);
  const headG = mergeGeometries([part(head, 2), part(hair, 3), part(nose, 2)]);
  const thigh = cap(0.078, 0.3, -0.21, 1);
  const foot = new THREE.BoxGeometry(0.1, 0.07, 0.25); foot.translate(0, -0.45, 0.05);
  const shin = mergeGeometries([cap(0.06, 0.32, -0.2, 1), part(foot, 4)]);
  const upper = cap(0.056, 0.2, -0.14, 0);
  const hand = new THREE.SphereGeometry(0.045, 8, 6); hand.scale(0.8, 1.1, 0.6); hand.translate(0, -0.3, 0);
  const fore = mergeGeometries([cap(0.047, 0.18, -0.13, 0), part(hand, 2)]);
  // paraguas: baston + copa (en el marco del tronco, sobre el hombro derecho)
  const canopy = new THREE.ConeGeometry(0.55, 0.28, 12, 1, true); canopy.translate(0.12, 1.05, 0.05);
  const stick = new THREE.CylinderGeometry(0.01, 0.01, 0.75, 5); stick.translate(0.12, 0.67, 0.05);
  const umbrella = mergeGeometries([part(canopy, 5), part(stick, 4)]);
  return { trunk, head: headG, thigh, shin, upper, fore, umbrella };
}

const SHIRTS = [[0.02, 0.02, 0.025], [0.03, 0.04, 0.08], [0.08, 0.08, 0.085], [0.18, 0.1, 0.06], [0.12, 0.14, 0.07],
  [0.35, 0.04, 0.04], [0.45, 0.32, 0.06], [0.45, 0.45, 0.43], [0.05, 0.12, 0.2], [0.3, 0.2, 0.25], [0.02, 0.06, 0.04], [0.5, 0.36, 0.22]];
const PANTS = [[0.03, 0.05, 0.11], [0.02, 0.02, 0.02], [0.12, 0.12, 0.12], [0.3, 0.26, 0.2], [0.08, 0.1, 0.16], [0.04, 0.03, 0.025]];
const SKIN = [[0.55, 0.38, 0.28], [0.42, 0.28, 0.19], [0.28, 0.18, 0.12], [0.65, 0.48, 0.38], [0.48, 0.32, 0.22]];
const HAIR = [[0.015, 0.012, 0.01], [0.03, 0.02, 0.012], [0.08, 0.05, 0.03], [0.25, 0.23, 0.22]];
const UMBR = [[0.02, 0.02, 0.025], [0.02, 0.02, 0.025], [0.3, 0.02, 0.03], [0.03, 0.05, 0.2], [0.4, 0.3, 0.03]];
const pick = (a) => a[(Math.random() * a.length) | 0];

export const LINES = [
  '¡Buenas! ¿Primera vez en la Plaza de Bolívar?',
  'Cuidado con las palomas: si les da maíz se le suben encima.',
  'Allá arriba está Monserrate. Se sube en teleférico o en funicular.',
  'En Bogotá llueve casi todas las tardes. Mejor ande con paraguas.',
  'La Catedral se terminó en 1823. Adentro está la tumba de Jiménez de Quesada.',
  'Lea la frase de Santander en el Palacio de Justicia: "las leyes os darán la libertad".',
  'Ese edificio amarillo es el Liévano. Ahí despacha el alcalde.',
  '¿Ya probó el chocolate con queso? En La Candelaria hay varios sitios.',
  'El 20 de julio de 1810 todo empezó en la Casa del Florero, ahí en la esquina.',
  'Hace frío, ¿no? Estamos a 2.600 metros.',
  'Los domingos esto se llena de gente, de vendedores y de palomas.',
  'La estatua de Bolívar es de 1846. Fue la primera estatua pública de la ciudad.',
  'Siga por la Séptima peatonal y llega al Museo del Oro.',
  'Uy, qué pena, lo confundí con un conocido.',
  'El Capitolio se demoró casi ochenta años en terminarse.',
];

function inPoly(u, v, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ui, vi] = poly[i], [uj, vj] = poly[j];
    if ((vi > v) !== (vj > v) && u < ((uj - ui) * (v - vi)) / (vj - vi) + ui) c = !c;
  }
  return c;
}

const _m = new THREE.Matrix4(), _t = new THREE.Matrix4(), _r = new THREE.Matrix4(), _k = new THREE.Matrix4();
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _s = new THREE.Vector3();
const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
const _leg = new THREE.Matrix4(), _arm = new THREE.Matrix4();

export class People {
  /** opts: outline, avoid [{u,v,r}], shelters [[u,v]], groundY(x,z), count */
  constructor(scene, opts) {
    this.opts = opts;
    const walkers = opts.walkers ?? 70, groups = opts.groups ?? 11;
    const G = bodyGeoms();
    // atributos de color por instancia compartidos por todas las piezas
    const n = walkers + groups * 4 + 6;
    this.cap = n;
    const attrs = {};
    for (const k of ['iShirt', 'iPants', 'iSkin', 'iHair', 'iAcc']) attrs[k] = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.85, side: THREE.DoubleSide });
    mat.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', `#include <common>
          attribute float slot; attribute vec3 iShirt; attribute vec3 iPants; attribute vec3 iSkin; attribute vec3 iHair; attribute vec3 iAcc;
          varying vec3 vPCol; varying float vPRough;`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          vPCol = slot < 0.5 ? iShirt : slot < 1.5 ? iPants : slot < 2.5 ? iSkin : slot < 3.5 ? iHair : slot < 4.5 ? vec3(0.025, 0.022, 0.02) : iAcc;
          vPRough = slot > 1.5 && slot < 2.5 ? 0.5 : slot > 3.5 && slot < 4.5 ? 0.4 : slot > 4.5 ? 0.35 : 0.9;`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vPCol; varying float vPRough;')
        .replace('#include <map_fragment>', '#include <map_fragment>\ndiffuseColor.rgb *= vPCol;')
        .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = vPRough;');
    };
    this.meshes = {};
    for (const [name, geom] of Object.entries(G)) {
      for (const [k, a] of Object.entries(attrs)) geom.setAttribute(k, a);
      const sides = ['thigh', 'shin', 'upper', 'fore'].includes(name) ? ['L', 'R'] : [''];
      for (const sd of sides) {
        const im = new THREE.InstancedMesh(geom, mat, n);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        im.castShadow = true; im.receiveShadow = true; im.frustumCulled = false;
        im.name = 'personas';
        scene.add(im);
        this.meshes[name + sd] = im;
      }
    }
    this.attrs = attrs;
    this.people = [];
    const setCol = (i, k, c) => { attrs[k].setXYZ(i, c[0], c[1], c[2]); };
    let i = 0;
    const add = (props) => {
      const p = {
        i, pos: new THREE.Vector3(), yaw: Math.random() * 6.28, speed: 0, vmax: 1.1 + Math.random() * 0.45,
        phase: Math.random() * 6.28, scale: 0.9 + Math.random() * 0.13, state: 'walk', target: null, t: 0,
        umbrellaOwner: Math.random() < 0.6, umbrella: 0, gesture: 0, look: 0, talk: 0, groundT: 0, ...props,
      };
      const female = Math.random() < 0.5;
      setCol(i, 'iShirt', pick(SHIRTS)); setCol(i, 'iPants', female && Math.random() < 0.3 ? pick(SHIRTS) : pick(PANTS));
      setCol(i, 'iSkin', pick(SKIN)); setCol(i, 'iHair', pick(HAIR)); setCol(i, 'iAcc', pick(UMBR));
      if (female) p.scale *= 0.95;
      this.people.push(p); i++;
      return p;
    };
    for (let k = 0; k < walkers; k++) {
      const p = add({ state: 'walk' });
      p.pos.copy(this.randomSpot());
      p.target = this.randomSpot();
    }
    for (let g = 0; g < groups; g++) {
      const c = this.randomSpot();
      const m = 2 + ((Math.random() * 3) | 0);
      const photo = g % 4 === 0;
      for (let k = 0; k < m; k++) {
        const a = (k / m) * Math.PI * 2 + Math.random() * 0.5;
        const p = add({ state: 'idle', vmax: 1.0 });
        p.pos.set(c.x + Math.cos(a) * 0.65, 0, c.z + Math.sin(a) * 0.65);
        p.yaw = Math.atan2(c.x - p.pos.x, c.z - p.pos.z);
        p.home = p.pos.clone(); p.homeYaw = p.yaw;
        p.photo = photo && k === 0;
        if (p.photo) { p.yaw += Math.PI; p.homeYaw = p.yaw; }
      }
    }
    this.count = i;
    for (const im of Object.values(this.meshes)) im.count = i;
    for (const a of Object.values(attrs)) a.needsUpdate = true;
    for (const p of this.people) p.pos.y = opts.groundY(p.pos.x, p.pos.z);
    this.frame = 0;
  }

  randomSpot() {
    const o = this.opts;
    for (let k = 0; k < 80; k++) {
      const u = -38 + Math.random() * 77, v = -49 + Math.random() * 96;
      if (!inPoly(u, v, o.outline)) continue;
      if (o.avoid.some((a) => Math.hypot(u - a.u, v - a.v) < a.r + 1)) continue;
      return new THREE.Vector3(u, 0, -v);
    }
    return new THREE.Vector3(0, 0, 0);
  }

  /** persona a la que el jugador mira (para la tecla E) */
  findTalkable(camPos, camDir) {
    let best = null, bd = 3.0;
    for (const p of this.people) {
      _v.set(p.pos.x - camPos.x, p.pos.y + 1.55 * p.scale - camPos.y, p.pos.z - camPos.z);
      const d = _v.length();
      if (d > bd) continue;
      if (_v.normalize().dot(camDir) < 0.82) continue;
      best = p; bd = d;
    }
    return best;
  }

  talkTo(p, camPos) {
    p.state = 'talk'; p.talk = 7; p.speed = 0;
    p.faceYaw = Math.atan2(camPos.x - p.pos.x, camPos.z - p.pos.z);
    return LINES[(Math.random() * LINES.length) | 0];
  }

  update(dt, ctx) {
    const P = ctx.player, rain = ctx.rain;
    this.frame++;
    for (const p of this.people) {
      let desiredYaw = p.yaw, target = 0;
      p.umbrella = THREE.MathUtils.lerp(p.umbrella, rain > 0.25 && p.umbrellaOwner ? 1 : 0, Math.min(1, dt * 2));
      if (p.state === 'talk') {
        p.talk -= dt;
        desiredYaw = p.faceYaw;
        p.gesture = THREE.MathUtils.lerp(p.gesture, 0.5 + 0.5 * Math.sin(performance.now() * 0.004 + p.i), Math.min(1, dt * 3));
        if (p.talk <= 0) { p.state = p.home ? 'return' : 'walk'; p.target = p.home ? p.home.clone() : this.randomSpot(); }
      } else if (p.state === 'idle') {
        desiredYaw = p.homeYaw + Math.sin(performance.now() * 0.0004 + p.i) * 0.25;
        p.gesture = p.photo ? 1 : THREE.MathUtils.lerp(p.gesture, Math.max(0, Math.sin(performance.now() * 0.0011 + p.i * 1.7)) * 0.7, Math.min(1, dt * 2));
        // con lluvia, quien no tiene paraguas busca refugio
        if (rain > 0.35 && !p.umbrellaOwner && this.opts.shelters?.length) {
          const s = this.opts.shelters[p.i % this.opts.shelters.length];
          p.state = 'shelter'; p.target = new THREE.Vector3(s[0] + (Math.random() - 0.5) * 6, 0, -(s[1] + (Math.random() - 0.5) * 2));
        }
      } else {
        // caminar hacia el objetivo
        if (!p.target) p.target = this.randomSpot();
        _v.set(p.target.x - p.pos.x, 0, p.target.z - p.pos.z);
        const d = _v.length();
        if (d < 0.6) {
          if (p.state === 'return') { p.state = 'idle'; p.pos.x = p.home.x; p.pos.z = p.home.z; }
          else if (p.state === 'shelter') { p.state = 'sheltered'; }
          else p.target = this.randomSpot();
        } else {
          desiredYaw = Math.atan2(_v.x, _v.z);
          target = p.vmax * (rain > 0.3 ? (p.umbrellaOwner ? 1.15 : 1.8) : 1);
        }
        if (p.state === 'sheltered') { target = 0; if (rain < 0.15) { p.state = p.home ? 'return' : 'walk'; p.target = p.home ? p.home.clone() : this.randomSpot(); } }
        p.gesture = THREE.MathUtils.lerp(p.gesture, 0, Math.min(1, dt * 2));
      }
      // evitar al jugador, a otros y la plataforma de la estatua
      if (target > 0) {
        let ax = Math.sin(desiredYaw), az = Math.cos(desiredYaw);
        const pdx = p.pos.x - P.x, pdz = p.pos.z - P.z, pd = Math.hypot(pdx, pdz);
        if (pd < 2.2) { ax += (pdx / pd) * (2.2 - pd) * 1.5; az += (pdz / pd) * (2.2 - pd) * 1.5; }
        for (const a of this.opts.avoid) {
          const dx = p.pos.x - a.u, dz = p.pos.z + a.v, dd = Math.hypot(dx, dz);
          if (dd < a.r + 1.5) { ax += (dx / dd) * 1.2; az += (dz / dd) * 1.2; }
        }
        if (this.frame % 2 === p.i % 2) {
          for (const o of this.people) {
            if (o === p) continue;
            const dx = p.pos.x - o.pos.x, dz = p.pos.z - o.pos.z, dd = dx * dx + dz * dz;
            if (dd < 0.8 && dd > 1e-6) { const k = (0.8 - dd) * 1.5 / Math.sqrt(dd); ax += dx * k; az += dz * k; }
          }
          p.avoidX = ax; p.avoidZ = az;
        } else { ax = p.avoidX ?? ax; az = p.avoidZ ?? az; }
        desiredYaw = Math.atan2(ax, az);
      }
      let dy = desiredYaw - p.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      p.yaw += THREE.MathUtils.clamp(dy, -3.2 * dt, 3.2 * dt);
      p.speed = THREE.MathUtils.lerp(p.speed, target * Math.max(0, Math.cos(dy)), Math.min(1, dt * 3));
      if (p.speed > 0.01) {
        const nx = p.pos.x + Math.sin(p.yaw) * p.speed * dt, nz = p.pos.z + Math.cos(p.yaw) * p.speed * dt;
        p.pos.x = nx; p.pos.z = nz;
        p.phase += (p.speed * dt) / (1.35 * p.scale) * Math.PI * 2;
      }
      p.groundT -= dt;
      if (p.groundT <= 0) { p.pos.y = this.opts.groundY(p.pos.x, p.pos.z); p.groundT = 0.25 + Math.random() * 0.2; }
    }
    this.write();
  }

  write() {
    const M = this.meshes, now = performance.now() * 0.001;
    for (const p of this.people) {
      const run = p.speed > 1.9 ? 1 : 0;
      const amp = Math.min(1, p.speed / 1.2);
      const ph = p.phase;
      const hipY = 0.92 * p.scale;
      const bob = amp * 0.035 * Math.abs(Math.cos(ph)) - (run ? 0.04 : 0);
      _e.set(run ? 0.12 : 0.03 * amp, p.yaw, 0, 'YXZ');
      _q.setFromEuler(_e);
      _m.compose(_v.set(p.pos.x, p.pos.y + hipY - 0.92 * p.scale * 0 + bob, p.pos.z), _q, _s.set(p.scale, p.scale, p.scale));
      // tronco
      _k.copy(_m).multiply(_r.makeRotationY(Math.sin(ph) * 0.12 * amp));
      M.trunk.setMatrixAt(p.i, _k);
      // cabeza
      const look = p.state === 'idle' ? Math.sin(now * 0.5 + p.i) * 0.5 : 0;
      _t.makeTranslation(0, 0.64, 0).multiply(_r.makeRotationY(look)).multiply(_r.makeRotationX(p.state === 'talk' ? -0.1 + Math.sin(now * 5 + p.i) * 0.04 : 0.05));
      M.head.setMatrixAt(p.i, _t.premultiply(_k));
      // piernas
      for (const [sd, off] of [['L', 0], ['R', Math.PI]]) {
        const s = Math.sin(ph + off), c = Math.cos(ph + off);
        const thighA = -(0.42 + 0.25 * run) * s * amp;
        const knee = (0.08 + (0.7 + 0.6 * run) * Math.max(0, c) ** 1.5) * amp + (1 - amp) * 0.04;
        _t.makeTranslation(sd === 'L' ? 0.095 : -0.095, 0, 0).multiply(_r.makeRotationX(thighA));
        _leg.copy(_t).premultiply(_m);
        M['thigh' + sd].setMatrixAt(p.i, _leg);
        _t.makeTranslation(0, -0.43, 0).multiply(_r.makeRotationX(knee));
        M['shin' + sd].setMatrixAt(p.i, _t.premultiply(_leg));
      }
      // brazos (opuestos a las piernas); el derecho sostiene el paraguas o gesticula
      for (const [sd, off] of [['L', Math.PI], ['R', 0]]) {
        const s = Math.sin(ph + off);
        let armA = (0.35 + 0.5 * run) * s * amp, elbow = -0.25 - 0.35 * run - 0.15 * amp;
        let side = sd === 'L' ? 0.07 : -0.07;
        if (sd === 'R' && p.umbrella > 0.5) { armA = -0.9; elbow = -1.1; side = -0.25; }
        else if (p.photo && p.state === 'idle') { armA = -1.35; elbow = -0.5; }
        else if (p.gesture > 0.05 && sd === (p.i % 2 ? 'L' : 'R')) { armA = -0.5 * p.gesture; elbow = -1.2 * p.gesture - 0.3; }
        _t.makeTranslation(sd === 'L' ? 0.215 : -0.215, 0.52, 0).multiply(_r.makeRotationX(armA)).multiply(_r.makeRotationZ(side));
        _arm.copy(_t).premultiply(_k);
        M['upper' + sd].setMatrixAt(p.i, _arm);
        _t.makeTranslation(0, -0.29, 0).multiply(_r.makeRotationX(elbow));
        M['fore' + sd].setMatrixAt(p.i, _t.premultiply(_arm));
      }
      // paraguas
      if (p.umbrella > 0.02) {
        _t.makeScale(p.umbrella, p.umbrella, p.umbrella);
        M.umbrella.setMatrixAt(p.i, _t.premultiply(_k));
      } else M.umbrella.setMatrixAt(p.i, ZERO);
    }
    for (const im of Object.values(M)) im.instanceMatrix.needsUpdate = true;
  }

  /** Empuja al jugador fuera de las personas */
  pushPlayer(pos, r) {
    for (const p of this.people) {
      const dx = pos.x - p.pos.x, dz = pos.z - p.pos.z, d = Math.hypot(dx, dz), R = r + 0.25 * p.scale;
      if (d < R && d > 1e-4 && Math.abs(pos.y - p.pos.y) < 2) { pos.x += (dx / d) * (R - d); pos.z += (dz / d) * (R - d); }
    }
  }

  headPos(p, out) { return out.set(p.pos.x, p.pos.y + 1.95 * p.scale, p.pos.z); }
}
