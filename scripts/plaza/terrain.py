"""Terreno real (DEM) de los cerros orientales y ciudad de fondo a partir de OSM."""
import hashlib
import json
import math
import os
import random

import bmesh
import bpy
import numpy as np

from . import geo

M_PER_DEG_LAT = 110574.0


class Frame:
    """Conversion entre lat/lon y el marco de reticula (u, v) del modelo."""

    def __init__(self, origin, rot_deg):
        self.lat0, self.lon0 = origin
        self.r = math.radians(rot_deg)
        self.mlon = 111320.0 * math.cos(math.radians(self.lat0))

    def to_uv(self, lat, lon):
        E = (lon - self.lon0) * self.mlon
        N = (lat - self.lat0) * M_PER_DEG_LAT
        c, s = math.cos(self.r), math.sin(self.r)
        return E * c - N * s, E * s + N * c

    def to_latlon(self, u, v):
        c, s = math.cos(self.r), math.sin(self.r)
        E = u * c + v * s
        N = -u * s + v * c
        return self.lat0 + N / M_PER_DEG_LAT, self.lon0 + E / self.mlon


class DEM:
    """Muestreo bilineal de las teselas terrarium (Web Mercator)."""

    def __init__(self, path):
        d = np.load(path)
        self.z = d["dem"].astype(np.float64)
        self.n = float(d["n"])
        self.px0 = float(d["px0"])
        self.py0 = float(d["py0"])

    def sample(self, lat, lon):
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        x = (lon + 180.0) / 360.0 * self.n - self.px0 - 0.5
        y = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * self.n - self.py0 - 0.5
        h, w = self.z.shape
        x = np.clip(x, 0, w - 1.001)
        y = np.clip(y, 0, h - 1.001)
        x0 = np.floor(x).astype(int)
        y0 = np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        z = self.z
        return ((z[y0, x0] * (1 - fx) + z[y0, x0 + 1] * fx) * (1 - fy)
                + (z[y0 + 1, x0] * (1 - fx) + z[y0 + 1, x0 + 1] * fx) * fy)


def terrain_height_fn(dem, frame, base_elev, flatten_r):
    r0, r1 = flatten_r

    def fn(u, v):
        u = np.asarray(u, dtype=np.float64)
        v = np.asarray(v, dtype=np.float64)
        c, s = math.cos(frame.r), math.sin(frame.r)
        E = u * c + v * s
        N = -u * s + v * c
        lat = frame.lat0 + N / M_PER_DEG_LAT
        lon = frame.lon0 + E / frame.mlon
        h = dem.sample(lat, lon) - base_elev
        r = np.hypot(u, v)
        t = np.clip((r - r0) / (r1 - r0), 0, 1)
        t = t * t * (3 - 2 * t)
        return h * t - 0.06 * (1 - t)  # bajo la plaza queda 6 cm por debajo de los pavimentos

    return fn


def build_terrain(coll, mat, height_fn, u_range, v_range, step):
    us = np.arange(u_range[0], u_range[1] + step, step)
    vs = np.arange(v_range[0], v_range[1] + step, step)
    U, V = np.meshgrid(us, vs)
    Z = height_fn(U, V)
    nx, ny = len(us), len(vs)
    verts = np.stack([U.ravel(), V.ravel(), Z.ravel()], axis=1)
    ii, jj = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1))
    a = (jj * nx + ii).ravel()
    faces = np.stack([a, a + 1, a + nx + 1, a + nx], axis=1)
    me = bpy.data.meshes.new("Terreno DEM")
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", (np.arange(len(faces)) * 4).astype(np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    me.materials.append(mat)
    obj = bpy.data.objects.new("Cerros orientales y sabana (DEM)", me)
    coll.objects.link(obj)
    return obj


def landmark(coll, mat_wall, mat_roof, frame, height_fn, dem, lm):
    """Santuario en una cumbre: se busca el maximo local del DEM a menos de 150 m."""
    u, v = frame.to_uv(lm["lat"], lm["lon"])
    best = (height_fn(u, v), u, v)
    for du in range(-150, 151, 15):
        for dv in range(-150, 151, 15):
            h = float(height_fn(u + du, v + dv))
            if h > best[0]:
                best = (h, u + du, v + dv)
    z, u, v = best
    w, d, h = lm["size"]
    mb = geo.MeshBuilder()
    mb.box_c(u, v, z - 6, w, d, h + 6, 0)
    mb.box_c(u - w / 2 + 3, v, z + h, 5, 5, lm["tower"] - h, 0)
    mb.gable_roof_x(u - w / 2 + 5.5, u + w / 2, v - d / 2 - 0.5, v + d / 2 + 0.5, z + h, 3.5, 1)
    obj = mb.to_object(lm["name"], coll, [mat_wall, mat_roof])
    print(f"[hito] {lm['name']}: u={u:.0f} v={v:.0f} cota relativa={z:.0f} m")
    return obj


# ---------------------------------------------------------------- ciudad OSM

def _poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def _seed(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def osm_city(coll, path, frame, height_fn, wall_mats, roof_mats, cfg, massing=False):
    """Extruye las huellas OSM (excepto las modeladas en detalle) con tejado a cuatro aguas."""
    data = json.load(open(path))
    ex_names = cfg["exclude_names"]
    ex_boxes = cfg["exclude_boxes"]
    fh = cfg["floor_h"]
    groups = {}
    count = 0
    for f in data["features"]:
        p = f["properties"]
        if p.get("is_underground"):
            continue
        name = ((p.get("names") or {}).get("primary") or "")
        if any(n.lower() in name.lower() for n in ex_names):
            continue
        g = f["geometry"]
        rings = [g["coordinates"][0]] if g["type"] == "Polygon" else [pp[0] for pp in
                                                                        g["coordinates"]]
        for ring in rings:
            pts = [frame.to_uv(lat, lon) for lon, lat in ring[:-1]]
            if len(pts) < 3:
                continue
            area = _poly_area(pts)
            if area < 0:
                pts.reverse()
                area = -area
            if area < 12:
                continue
            cu = sum(x for x, _ in pts) / len(pts)
            cv = sum(y for _, y in pts) / len(pts)
            if any(b[0] < cu < b[2] and b[1] < cv < b[3] for b in ex_boxes):
                continue
            rnd = random.Random(_seed(p["id"]))
            nf = p.get("num_floors")
            if not nf:
                r = math.hypot(cu, cv)
                # La Candelaria (sur/oriente): 1-3 pisos; centro (norte/occidente): mas alto
                downtown = cv > 150 or cu < -200
                if area < 120:
                    nf = rnd.choice([1, 2, 2, 2, 3])
                elif area < 500:
                    nf = rnd.choice([2, 2, 3, 3, 4] + ([5, 6] if downtown else []))
                else:
                    nf = rnd.choice([2, 3, 4, 5] + ([6, 8, 10, 12] if downtown else []))
                if r > 500 and downtown:
                    nf += rnd.choice([0, 0, 2, 4])
            h = nf * fh + rnd.uniform(0.3, 1.2)
            z0 = float(height_fn(cu, cv))
            pitched = nf <= 4 and rnd.random() < 0.85
            k = rnd.randrange(len(wall_mats))
            groups.setdefault((k, pitched), []).append((pts, z0, h, area))
            count += 1
    objs = []
    for (k, pitched), items in groups.items():
        bm = bmesh.new()
        for pts, z0, h, area in items:
            vs = [bm.verts.new((x, y, z0 - 3.0)) for x, y in pts]
            try:
                face = bm.faces.new(vs)
            except ValueError:
                continue
            face.material_index = 0
            ext = bmesh.ops.extrude_face_region(bm, geom=[face])
            top_verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=top_verts, vec=(0, 0, h + 3.0))
            top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMFace)]
            if pitched and not massing:
                minside = math.sqrt(area) * 0.5
                t = max(0.6, min(3.5, minside * 0.45))
                res = bmesh.ops.inset_region(bm, faces=top, thickness=t, depth=t * 0.55,
                                             use_even_offset=True)
                for fc in res["faces"]:
                    fc.material_index = 1
                for fc in top:
                    fc.material_index = 1
            else:
                for fc in top:
                    fc.material_index = 2
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"Ciudad OSM {k}{'t' if pitched else 'p'}")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(wall_mats[k])
        me.materials.append(roof_mats[0])
        me.materials.append(roof_mats[1])
        ob = bpy.data.objects.new(me.name, me)
        coll.objects.link(ob)
        objs.append(ob)
    print(f"[ciudad] {count} edificios OSM extruidos")
    return objs


def filler(coll, name, poly, h, mat, z0=0.0):
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z0 - 2.0)) for x, y in poly]
    face = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)],
                        vec=(0, 0, h + 2.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob
