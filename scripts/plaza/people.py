"""Personas y palomas simplificadas para dar escala (geometria procedural, sin assets externos)."""
import math
import random

from mathutils import Matrix

from . import geo


def _person(mbs, x, y, z, h, yaw_deg, stride, rnd):
    """Figura humana de baja resolucion (se suaviza con Subsurf). mbs = (piel, arriba, abajo, pelo)."""
    skin, top, bottom, hair = mbs
    base = geo.mat_t(x, y, z, yaw_deg)
    s = h / 1.70
    # piernas con zancada (rotacion alrededor de x local)
    for side, ang in ((-1, stride), (1, -stride)):
        m = base @ Matrix.Translation((side * 0.095 * s, 0, 0.82 * s)) @ Matrix.Rotation(
            math.radians(ang), 4, "X")
        bottom.lathe([(0.0, -0.82 * s), (0.055 * s, -0.82 * s), (0.06 * s, -0.45 * s),
                      (0.075 * s, -0.05 * s), (0.08 * s, 0.0), (0.0, 0.02 * s)], 8, (0, 0, 0),
                     matrix=m)
        # zapato
        top_m = m @ Matrix.Translation((0, -0.05 * s, -0.84 * s))
        hair.box_c(0, 0, 0, 0.09 * s, 0.24 * s, 0.07 * s, 0, top_m)
    # cadera y torso (eliptico)
    bottom.lathe([(0.0, 0.78 * s), (0.15 * s, 0.80 * s), (0.16 * s, 0.92 * s), (0.0, 0.95 * s)],
                 10, (0, 0, 0), matrix=base, scale_xy=(1.0, 0.68))
    coat = rnd.random() < 0.45
    top.lathe([(0.0, 0.90 * s if not coat else 0.62 * s),
               (0.16 * s if not coat else 0.19 * s, 0.90 * s if not coat else 0.62 * s),
               (0.155 * s, 1.05 * s), (0.17 * s, 1.30 * s), (0.18 * s, 1.40 * s),
               (0.11 * s, 1.47 * s), (0.05 * s, 1.49 * s), (0.0, 1.5 * s)], 12, (0, 0, 0),
              matrix=base, scale_xy=(1.0, 0.62))
    # brazos
    for side, ang in ((-1, -stride * 0.8), (1, stride * 0.8)):
        m = base @ Matrix.Translation((side * 0.2 * s, 0, 1.40 * s)) @ Matrix.Rotation(
            math.radians(ang), 4, "X") @ Matrix.Rotation(math.radians(side * 6), 4, "Y")
        top.lathe([(0.0, -0.62 * s), (0.04 * s, -0.62 * s), (0.045 * s, -0.3 * s),
                   (0.055 * s, -0.02 * s), (0.0, 0.03 * s)], 8, (0, 0, 0), matrix=m)
        skin.lathe([(0.0, -0.74 * s), (0.04 * s, -0.70 * s), (0.035 * s, -0.62 * s),
                    (0.0, -0.60 * s)], 6, (0, 0, 0), matrix=m)
    # cuello, cabeza y pelo
    skin.lathe([(0.045 * s, 1.47 * s), (0.045 * s, 1.55 * s), (0.0, 1.56 * s)], 8, (0, 0, 0),
               matrix=base)
    skin.lathe([(0.0, 1.53 * s), (0.06 * s, 1.56 * s), (0.08 * s, 1.63 * s), (0.078 * s, 1.68 * s),
                (0.0, 1.70 * s)], 10, (0, 0, 0), matrix=base, scale_xy=(0.85, 1.0))
    hair.lathe([(0.0, 1.62 * s), (0.083 * s, 1.63 * s), (0.083 * s, 1.68 * s),
                (0.0, 1.72 * s)], 10, (0, 0.012 * s, 0), matrix=base, scale_xy=(0.88, 1.0))


def scatter_people(coll, mats, zones, n, seed, avoid, parent=None):
    """mats = {'piel': [...], 'arriba': [...], 'abajo': [...], 'pelo': m}. zones = [(u0,v0,u1,v1,z,w)]."""
    rnd = random.Random(seed)
    groups = {}
    placed = []
    total_w = sum(z[5] for z in zones)
    tries = 0
    while len(placed) < n and tries < n * 60:
        tries += 1
        r = rnd.random() * total_w
        for zone in zones:
            r -= zone[5]
            if r <= 0:
                break
        u0, v0, u1, v1, zz, _ = zone
        x, y = rnd.uniform(u0, u1), rnd.uniform(v0, v1)
        if any(f(x, y) for f in avoid):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < 0.8 ** 2 for px, py in placed):
            continue
        placed.append((x, y))
        # pequenos grupos: a veces se anade un acompanante
        companions = [(x, y)]
        if rnd.random() < 0.35:
            companions.append((x + rnd.uniform(0.5, 0.8), y + rnd.uniform(-0.3, 0.3)))
        yaw = rnd.uniform(0, 360)
        walking = rnd.random() < 0.55
        for cx, cy in companions:
            ks = rnd.randrange(len(mats["piel"]))
            kt = rnd.randrange(len(mats["arriba"]))
            kb = rnd.randrange(len(mats["abajo"]))
            key = (ks, kt, kb)
            if key not in groups:
                groups[key] = [geo.MeshBuilder() for _ in range(4)]
            h = rnd.gauss(1.66, 0.08)
            _person(groups[key], cx, cy, zz, h, yaw + rnd.uniform(-15, 15),
                    rnd.uniform(14, 24) if walking else rnd.uniform(0, 4), rnd)
    objs = []
    for (ks, kt, kb), mbs in groups.items():
        allm = geo.MeshBuilder()
        for i, mb in enumerate(mbs):
            allm.extend(mb, mat_offset=i)
        ob = allm.to_object(f"Personas {ks}-{kt}-{kb}", coll,
                            [mats["piel"][ks], mats["arriba"][kt], mats["abajo"][kb], mats["pelo"]],
                            parent, recalc=False)
        sub = ob.modifiers.new("Suavizado", "SUBSURF")
        sub.levels = 0
        sub.render_levels = 1
        objs.append(ob)
    print(f"[personas] {len(placed)} grupos colocados")
    return objs


def scatter_pigeons(coll, mat, center, radius, n, seed, z=0.0, avoid=()):
    rnd = random.Random(seed)
    mb = geo.MeshBuilder()
    k = 0
    while k < n:
        a = rnd.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rnd.random())
        x, y = center[0] + r * math.cos(a), center[1] + r * math.sin(a)
        if any(f(x, y) for f in avoid):
            continue
        yaw = rnd.uniform(0, 360)
        s = rnd.uniform(0.9, 1.1)
        m = geo.mat_t(x, y, z, yaw)
        # cuerpo (elipsoide horizontal), cabeza y cola
        mb.lathe([(0.0, -0.13 * s), (0.04 * s, -0.10 * s), (0.055 * s, 0.0), (0.04 * s, 0.09 * s),
                  (0.0, 0.12 * s)], 8, (0, 0, 0),
                 matrix=m @ Matrix.Translation((0, 0, 0.09 * s)) @ Matrix.Rotation(
                     math.radians(-80), 4, "X"))
        mb.lathe([(0.0, 0.0), (0.025 * s, 0.01 * s), (0.022 * s, 0.04 * s), (0.0, 0.05 * s)], 6,
                 (0, -0.12 * s, 0.14 * s), matrix=m)
        for side in (-1, 1):
            mb.box_c(side * 0.015 * s, 0.0, 0.0, 0.006, 0.006, 0.06 * s, 0, m)
        k += 1
    ob = mb.to_object("Palomas", coll, [mat], recalc=False)
    print(f"[palomas] {n}")
    return ob
