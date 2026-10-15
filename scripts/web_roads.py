"""Red vial para el simulador web: ejes reales (OSM via Overture) en coordenadas del modelo (u, v).

Lee references/osm/roads.geojson (scripts/pod/fetch_roads.py) y escribe web/public/scene/roads.json:
  {"roads": [{"c": clase, "w": ancho_m, "ow": 1 si es de un solo sentido, "bus": 1 si es carril
              exclusivo de buses, "n": nombre, "p": [[u, v], ...]}], "nodes": [[u, v, grado], ...]}
Se excluyen las aceras, escaleras y ciclorrutas, y el tramo dentro del nucleo modelado en Blender
(la plaza y la Cra 8 frente a ella ya tienen pavimento propio).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from plaza import config as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ancho de calzada (m) por clase | estimado para el centro de Bogota
WIDTH = {"primary": 10.5, "secondary": 9.0, "tertiary": 8.0, "residential": 6.5, "unclassified": 6.5,
         "service": 4.5, "pedestrian": 6.0, "living_street": 6.0, "unknown": 6.0}
RADIUS = 650.0                      # metros alrededor de la plaza
CORE = (-56.0, 61.5, -68.0, 67.5)   # u0, u1, v0, v1: nucleo con pavimento propio


M_PER_DEG_LAT = 110574.0


class Frame:
    """Igual que plaza.terrain.Frame (sin depender de bpy)."""

    def __init__(self, origin, rot_deg):
        self.lat0, self.lon0 = origin
        self.r = math.radians(rot_deg)
        self.mlon = 111320.0 * math.cos(math.radians(self.lat0))

    def to_uv(self, lat, lon):
        E = (lon - self.lon0) * self.mlon
        N = (lat - self.lat0) * M_PER_DEG_LAT
        c, s = math.cos(self.r), math.sin(self.r)
        return E * c - N * s, E * s + N * c


def inside_core(u, v):
    return CORE[0] < u < CORE[1] and CORE[2] < v < CORE[3]


def split_outside(pts):
    """Corta la polilinea donde entra al nucleo y devuelve los tramos exteriores."""
    out, cur = [], []
    for i, (u, v) in enumerate(pts):
        if inside_core(u, v):
            if cur:
                # punto de salida aproximado en el borde
                if len(cur) >= 1:
                    pu, pv = cur[-1]
                    cur.append(clip_to_core(pu, pv, u, v))
                if len(cur) >= 2:
                    out.append(cur)
                cur = []
        else:
            if not cur and i > 0 and inside_core(*pts[i - 1]):
                cur.append(clip_to_core(u, v, *pts[i - 1]))
            cur.append((u, v))
    if len(cur) >= 2:
        out.append(cur)
    return out


def clip_to_core(ua, va, ub, vb):
    """Punto del segmento a(fuera)->b(dentro) sobre el borde del nucleo (biseccion)."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = (lo + hi) / 2
        if inside_core(ua + (ub - ua) * m, va + (vb - va) * m):
            hi = m
        else:
            lo = m
    return ua + (ub - ua) * lo, va + (vb - va) * lo


def oneway(props):
    for r in props.get("access_restrictions") or []:
        w = r.get("when") or {}
        if r.get("access_type") == "denied" and w.get("heading") == "backward" and not r.get("between") \
                and not w.get("mode") and not w.get("vehicle"):
            return 1
    return 0


def bus_only(props):
    ar = props.get("access_restrictions") or []
    denied_all = any(r.get("access_type") == "denied" and not r.get("when") for r in ar)
    allows_bus = any(r.get("access_type") == "allowed" and "bus" in ((r.get("when") or {}).get("mode") or [])
                     for r in ar)
    return 1 if denied_all and allows_bus else 0


def main():
    fr = Frame(C.GEO["origin"], C.GEO["grid_rot_deg"])
    gj = json.load(open(os.path.join(ROOT, "references/osm/roads.geojson")))
    roads = []
    for f in gj["features"]:
        p = f["properties"]
        cls = p.get("class") or "unknown"
        if cls not in WIDTH:
            continue
        g = f["geometry"]
        lines = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for line in lines:
            pts = [fr.to_uv(lat, lon) for lon, lat in line]
            if min(math.hypot(u, v) for u, v in pts) > RADIUS:
                continue
            for part in split_outside(pts):
                roads.append({"c": cls, "w": WIDTH[cls], "ow": oneway(p), "bus": bus_only(p),
                              "n": p.get("name") or "",
                              "p": [[round(u, 2), round(v, 2)] for u, v in part]})
    # nodos: extremos compartidos (para cruces y cebras)
    deg = {}
    for r in roads:
        for u, v in (r["p"][0], r["p"][-1]):
            k = (round(u, 1), round(v, 1))
            deg[k] = deg.get(k, 0) + 1
    nodes = [[k[0], k[1], d] for k, d in deg.items() if d >= 3]
    out = os.path.join(ROOT, "web/public/scene/roads.json")
    json.dump({"roads": roads, "nodes": nodes}, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
    from collections import Counter
    print(len(roads), "tramos", Counter(r["c"] for r in roads).most_common(), "| un sentido:",
          sum(r["ow"] for r in roads), "| buses:", sum(r["bus"] for r in roads), "| cruces:", len(nodes),
          "|", os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
