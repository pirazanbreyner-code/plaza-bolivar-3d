// Palomas de la plaza: caminan cabeceando, picotean, huyen en bandada si alguien se acerca, vuelan
// en circulo y vuelven a aterrizar. Con maiz (tecla G) se acercan a comer.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const _m = new THREE.Matrix4(), _m2 = new THREE.Matrix4(), _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
const _v = new THREE.Vector3(), _s = new THREE.Vector3(1, 1, 1), _e = new THREE.Euler();
// alas plegadas hacia atras y algo caidas (derecha / izquierda espejada)
const _qFoldR = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 1.35, -0.25, 'YXZ'));
const _qFoldL = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -1.35, 0.25, 'YXZ'));

function colored(g, col, fn) {
  const ng = g.index ? g.toNonIndexed() : g;
  ng.deleteAttribute('uv');
  const p = ng.getAttribute('position'), c = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const k = fn ? fn(p.getX(i), p.getY(i), p.getZ(i)) : col;
    c[3 * i] = k[0]; c[3 * i + 1] = k[1]; c[3 * i + 2] = k[2];
  }
  ng.setAttribute('color', new THREE.BufferAttribute(c, 3));
  return ng;
}

function pigeonGeoms() {
  const grey = [0.2, 0.21, 0.25];
  const body = new THREE.SphereGeometry(1, 14, 10);
  body.scale(0.085, 0.078, 0.15); body.translate(0, 0.13, 0);
  const bodyC = colored(body, null, (x, y, z) => {
    if (z > 0.06 && y > 0.14) return [0.09, 0.16, 0.12];          // cuello tornasol
    if (y > 0.17 && Math.abs(z) < 0.06) return [0.14, 0.15, 0.18]; // alas plegadas: barras oscuras
    return y < 0.1 ? [0.27, 0.28, 0.32] : grey;
  });
  const tail = new THREE.BoxGeometry(0.075, 0.012, 0.12);
  tail.rotateX(-0.25); tail.translate(0, 0.15, -0.18);
  const legs = [];
  for (const x of [-0.025, 0.025]) {
    const l = new THREE.CylinderGeometry(0.006, 0.006, 0.07, 5);
    l.translate(x, 0.035, 0.01);
    legs.push(colored(l, [0.45, 0.12, 0.1]));
  }
  const neck = new THREE.CylinderGeometry(0.03, 0.045, 0.08, 8);
  neck.rotateX(0.5); neck.translate(0, 0.19, 0.1);
  const bodyG = mergeGeometries([bodyC, colored(tail, [0.08, 0.08, 0.1]), colored(neck, [0.1, 0.18, 0.14]), ...legs]);
  const head = new THREE.SphereGeometry(0.036, 10, 8);
  head.scale(1, 1, 1.15);
  const beak = new THREE.ConeGeometry(0.007, 0.028, 6);
  beak.rotateX(Math.PI / 2); beak.translate(0, -0.006, 0.048);
  const headG = mergeGeometries([colored(head, [0.13, 0.14, 0.17]), colored(beak, [0.05, 0.04, 0.04])]);
  const ws = new THREE.Shape();
  ws.moveTo(0, 0.04); ws.quadraticCurveTo(0.12, 0.08, 0.3, 0.0); ws.lineTo(0.27, -0.05);
  ws.quadraticCurveTo(0.12, -0.08, 0, -0.07); ws.closePath();
  const wing = new THREE.ShapeGeometry(ws, 6);
  wing.rotateX(Math.PI / 2);                      // en el plano XZ, envergadura en +x, borde de ataque en +z
  const wingG = colored(wing, null, (x) => (x > 0.2 ? [0.06, 0.06, 0.07] : x > 0.12 ? [0.15, 0.16, 0.19] : [0.22, 0.23, 0.27]));
  return { body: bodyG, head: headG, wing: wingG };
}

function inPoly(u, v, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ui, vi] = poly[i], [uj, vj] = poly[j];
    if ((vi > v) !== (vj > v) && u < ((uj - ui) * (v - vi)) / (vj - vi) + ui) c = !c;
  }
  return c;
}

export class Pigeons {
  /** opts: outline (poligono de la plaza en u,v), avoid ([{u, v, r}]), count, groundY(x, z) */
  constructor(scene, opts) {
    this.opts = opts;
    const n = opts.count ?? 240;
    this.n = n;
    const g = pigeonGeoms();
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82 });
    const wingMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide });
    this.body = new THREE.InstancedMesh(g.body, mat, n);
    this.head = new THREE.InstancedMesh(g.head, mat, n);
    this.wingR = new THREE.InstancedMesh(g.wing, wingMat, n);
    this.wingL = new THREE.InstancedMesh(g.wing, wingMat, n);
    const col = new THREE.Color();
    for (const im of [this.body, this.head, this.wingR, this.wingL]) {
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.frustumCulled = false;
      im.name = 'palomas';
      scene.add(im);
    }
    this.body.castShadow = true;
    this.birds = [];
    for (let i = 0; i < n; i++) {
      const r = Math.random();
      // variedad de plumajes: gris comun, oscuras, claras, algunas blancas o cafes
      const k = r < 0.62 ? [1, 1, 1] : r < 0.8 ? [0.6, 0.6, 0.65] : r < 0.9 ? [1.5, 1.45, 1.4] : r < 0.95 ? [3.2, 3.1, 3.0] : [1.6, 1.15, 0.8];
      col.setRGB(k[0], k[1], k[2]);
      for (const im of [this.body, this.head, this.wingR, this.wingL]) im.setColorAt(i, col);
      const p = this.randomSpot();
      this.birds.push({
        p: new THREE.Vector3(p.x, opts.groundY(p.x, p.z), p.z), vel: new THREE.Vector3(), yaw: Math.random() * 6.28,
        state: 'ground', t: Math.random() * 3, mode: 'walk', phase: Math.random(), flap: 0, flapAmp: 0,
        alarm: -1, flight: 0, target: null, offset: new THREE.Vector3((Math.random() - 0.5) * 14, (Math.random() - 0.5) * 5, (Math.random() - 0.5) * 14),
        peck: 0, open: 0, bank: 0, pitch: 0, speed: 0.25 + Math.random() * 0.15,
      });
    }
    // maiz
    this.corn = [];
    const cg = new THREE.SphereGeometry(0.009, 5, 4);
    this.cornMesh = new THREE.InstancedMesh(cg, new THREE.MeshStandardMaterial({ color: new THREE.Color(0.75, 0.48, 0.05), roughness: 0.5 }), 200);
    this.cornMesh.count = 0; this.cornMesh.frustumCulled = false;
    scene.add(this.cornMesh);
    this.flockAngle = 0;
    this.events = [];   // despegues para el sonido
  }

  randomSpot(avoidP, minD = 0) {
    const o = this.opts;
    for (let k = 0; k < 60; k++) {
      const u = -38 + Math.random() * 77, v = -49 + Math.random() * 96;
      if (!inPoly(u, v, o.outline)) continue;
      if (o.avoid.some((a) => Math.hypot(u - a.u, v - a.v) < a.r)) continue;
      const x = u, z = -v;
      if (avoidP && Math.hypot(x - avoidP.x, z - avoidP.z) < minD) continue;
      return new THREE.Vector3(x, 0, z);
    }
    return new THREE.Vector3(0, 0, 0);
  }

  allowed(x, z) {
    const u = x, v = -z;
    return inPoly(u, v, this.opts.outline) && !this.opts.avoid.some((a) => Math.hypot(u - a.u, v - a.v) < a.r);
  }

  throwCorn(pos, dir) {
    const c = new THREE.Vector3(pos.x + dir.x * 1.6, 0, pos.z + dir.z * 1.6);
    if (!this.allowed(c.x, c.z)) return false;
    for (let i = 0; i < 40; i++) {
      const a = Math.random() * 6.28, r = Math.sqrt(Math.random()) * 0.9;
      const k = new THREE.Vector3(c.x + Math.cos(a) * r, 0, c.z + Math.sin(a) * r);
      k.y = this.opts.groundY(k.x, k.z) + 0.009;
      this.corn.push(k);
    }
    if (this.corn.length > 200) this.corn.splice(0, this.corn.length - 200);
    this.cornCenter = c;
    // las que vuelan bajan a comer
    for (const b of this.birds) if (b.state === 'fly' && Math.random() < 0.7) { b.flight = Math.min(b.flight, Math.random() * 2); }
    return true;
  }

  takeoff(b, from) {
    if (b.state !== 'ground') return;
    b.state = 'fly';
    const away = _v.set(b.p.x - from.x, 0, b.p.z - from.z);
    if (away.lengthSq() < 1e-4) away.set(Math.random() - 0.5, 0, Math.random() - 0.5);
    away.normalize();
    b.vel.set(away.x * 3.2, 3.6 + Math.random(), away.z * 3.2);
    b.flight = 7 + Math.random() * 12;
    b.flapAmp = 1;
    this.events.push(b.p.clone());
  }

  /** ctx: { player (pies), playerSpeed, flying } */
  update(dt, ctx) {
    const P = ctx.player;
    this.flockAngle += dt * 0.22;
    const fc = new THREE.Vector3(Math.cos(this.flockAngle) * 26, 13 + Math.sin(this.flockAngle * 0.7) * 3, -Math.sin(this.flockAngle) * 26 + 5);
    const scare = ctx.flying ? 7 : ctx.playerSpeed > 4 ? 5.5 : ctx.playerSpeed > 0.5 ? 2.4 : 1.4;
    const hasCorn = this.corn.length > 0;
    for (const b of this.birds) {
      if (b.state === 'ground') {
        const dP = Math.hypot(b.p.x - P.x, b.p.z - P.z);
        if (b.alarm > 0) { b.alarm -= dt; if (b.alarm <= 0) { this.takeoff(b, P); this.alarmNeighbors(b, P); continue; } }
        if (dP < scare * (0.8 + 0.4 * ((b.phase * 7) % 1)) && Math.abs(P.y - b.p.y) < 3) { this.takeoff(b, P); this.alarmNeighbors(b, P); continue; }
        b.t -= dt;
        let speed = 0;
        let targetYaw = b.yaw;
        // maiz cerca: caminar hacia el grano mas cercano
        let food = null;
        if (hasCorn && this.cornCenter && Math.hypot(b.p.x - this.cornCenter.x, b.p.z - this.cornCenter.z) < 30) {
          let bd = 1e9;
          for (let i = 0; i < this.corn.length; i += 3) {
            const k = this.corn[i];
            const d = (k.x - b.p.x) ** 2 + (k.z - b.p.z) ** 2;
            if (d < bd) { bd = d; food = k; }
          }
        }
        if (food) {
          const d = Math.hypot(food.x - b.p.x, food.z - b.p.z);
          targetYaw = Math.atan2(food.x - b.p.x, food.z - b.p.z);
          if (d > 0.18) { speed = d > 3 ? 0.9 : 0.45; b.mode = 'walk'; }
          else {
            b.mode = 'peck';
            if (Math.random() < dt * 0.8) {
              const i = this.corn.indexOf(food);
              if (i >= 0) this.corn.splice(i, 1);
            }
          }
        } else {
          if (b.t <= 0) {
            b.mode = Math.random() < 0.45 ? 'peck' : Math.random() < 0.8 ? 'walk' : 'stand';
            b.t = 0.8 + Math.random() * 2.5;
            if (b.mode === 'walk') b.yawTarget = b.yaw + (Math.random() - 0.5) * 2.2;
          }
          if (b.mode === 'walk') { speed = b.speed; targetYaw = b.yawTarget ?? b.yaw; }
        }
        let d = targetYaw - b.yaw; d = Math.atan2(Math.sin(d), Math.cos(d));
        b.yaw += THREE.MathUtils.clamp(d, -4 * dt, 4 * dt);
        if (speed > 0) {
          const nx = b.p.x + Math.sin(b.yaw) * speed * dt, nz = b.p.z + Math.cos(b.yaw) * speed * dt;
          if (this.allowed(nx, nz)) { b.p.x = nx; b.p.z = nz; }
          else { b.yawTarget = Math.atan2(-b.p.x, -b.p.z - 2); b.yaw += 1.5 * dt; }
          b.phase += speed * dt / 0.07;
        }
        b.peck = THREE.MathUtils.lerp(b.peck, b.mode === 'peck' ? (Math.sin(performance.now() * 0.012 + b.phase * 20) > 0.2 ? 1 : 0.4) : 0, Math.min(1, dt * 14));
        b.open = Math.max(0, b.open - dt * 3);
        b.flapAmp = 0; b.bank = 0; b.pitch = 0;
      } else {
        // vuelo: hacia un punto de la bandada; luego aterrizar
        b.flight -= dt;
        let target;
        if (b.state === 'fly') {
          target = _v.copy(fc).add(b.offset);
          if (b.flight <= 0) {
            b.state = 'land';
            b.target = hasCorn && this.cornCenter && Math.random() < 0.85
              ? new THREE.Vector3(this.cornCenter.x + (Math.random() - 0.5) * 3, 0, this.cornCenter.z + (Math.random() - 0.5) * 3)
              : this.randomSpot(P, 8);
            b.target.y = this.opts.groundY(b.target.x, b.target.z);
          }
        } else target = _v.copy(b.target).add(new THREE.Vector3(0, Math.min(3, b.p.distanceTo(b.target) * 0.25), 0));
        const desired = target.clone().sub(b.p);
        const dist = desired.length();
        const vmax = b.state === 'land' ? Math.max(1.2, Math.min(8, dist * 0.9)) : 8.5;
        desired.normalize().multiplyScalar(vmax);
        b.vel.lerp(desired, Math.min(1, dt * (b.state === 'land' ? 2.2 : 1.3)));
        b.p.addScaledVector(b.vel, dt);
        const hv = Math.hypot(b.vel.x, b.vel.z);
        if (hv > 0.3) {
          const ny = Math.atan2(b.vel.x, b.vel.z);
          let d = ny - b.yaw; d = Math.atan2(Math.sin(d), Math.cos(d));
          b.yaw += d * Math.min(1, dt * 4);
          b.bank = THREE.MathUtils.lerp(b.bank, THREE.MathUtils.clamp(-d * 1.5, -0.7, 0.7), Math.min(1, dt * 3));
        }
        b.pitch = THREE.MathUtils.clamp(-Math.atan2(b.vel.y, Math.max(hv, 0.1)) * 0.6, -0.6, 0.6);
        const climbing = b.vel.y > 0.5 || b.state === 'land' && dist < 4;
        b.flapAmp = THREE.MathUtils.lerp(b.flapAmp, climbing || (b.flight % 3) > 1.2 ? 1 : 0.12, Math.min(1, dt * 4));
        b.flap += dt * (climbing ? 15 : 9);
        b.open = 1;
        const gy = b.state === 'land' ? b.target.y : -1e9;
        if (b.state === 'land' && dist < 0.35) {
          b.state = 'ground'; b.p.copy(b.target); b.vel.set(0, 0, 0); b.mode = 'stand'; b.t = 0.5 + Math.random();
        } else if (b.p.y < gy) b.p.y = gy;
      }
    }
    this.write();
  }

  alarmNeighbors(src, from) {
    for (const o of this.birds) {
      if (o.state !== 'ground' || o.alarm > 0) continue;
      const d = Math.hypot(o.p.x - src.p.x, o.p.z - src.p.z);
      if (d < 3.2) o.alarm = 0.05 + Math.random() * 0.5 + d * 0.08;
    }
  }

  write() {
    const t = performance.now() * 0.001;
    for (let i = 0; i < this.n; i++) {
      const b = this.birds[i];
      _e.set(b.pitch, b.yaw, b.bank, 'YXZ');
      _q.setFromEuler(_e);
      _m.compose(b.p, _q, _s);
      this.body.setMatrixAt(i, _m);
      // cabeza: cabeceo al caminar, picoteo
      const f = (b.phase % 1);
      const bob = b.state === 'ground' && b.mode === 'walk' ? 0.026 * (f < 0.3 ? f / 0.3 : 1 - (f - 0.3) / 0.7) : 0;
      _m2.makeRotationX(b.peck * 1.1);
      _m2.setPosition(0, 0.225 - b.peck * 0.12, 0.13 + bob + b.peck * 0.04);
      this.head.setMatrixAt(i, _m2.premultiply(_m));
      // alas: plegadas en el suelo, aleteo en vuelo
      const flap = b.open > 0 ? Math.sin(b.flap) * 0.95 * b.flapAmp + 0.12 : 0;
      for (const [im, side] of [[this.wingR, 1], [this.wingL, -1]]) {
        _q2.setFromEuler(_e.set(0, 0, flap * side, 'YXZ'));
        _q.copy(side > 0 ? _qFoldR : _qFoldL).slerp(_q2, b.open);
        _m2.compose(_v.set(0.055 * side, 0.165, 0.03), _q, _s.set(side, 1, 1));
        _s.set(1, 1, 1);
        im.setMatrixAt(i, _m2.premultiply(_m));
      }
    }
    for (const im of [this.body, this.head, this.wingR, this.wingL]) im.instanceMatrix.needsUpdate = true;
    // maiz
    this.cornMesh.count = this.corn.length;
    for (let i = 0; i < this.corn.length; i++) { _m.makeTranslation(this.corn[i].x, this.corn[i].y, this.corn[i].z); this.cornMesh.setMatrixAt(i, _m); }
    this.cornMesh.instanceMatrix.needsUpdate = true;
    void t;
  }

  /** Para el modo trazado de rayos: posiciones fijas */
  count() { return this.n; }
}
