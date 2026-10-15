"""Construye la escena de la Plaza de Bolivar (Bogota) y (opcionalmente) la renderiza.

Uso:
  .venv/bin/python scripts/build.py --stage massing --render preview
  .venv/bin/python scripts/build.py --stage detail  --render final --cams Cam_Catedral
  .venv/bin/python scripts/build.py --stage detail  --render none      # solo .blend

Etapas:
  massing -> volumenes grises para revisar distribucion, proporciones y camaras
  detail  -> fachadas, materiales procedurales, cielo fisico, bruma, cerros (DEM) y ciudad (OSM)
"""
import argparse
import datetime as dt
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from plaza import config as C  # noqa: E402
from plaza import buildings as B  # noqa: E402
from plaza import geo  # noqa: E402
from plaza import materials as M  # noqa: E402
from plaza import people as PP  # noqa: E402
from plaza import scene as S  # noqa: E402
from plaza import terrain as T  # noqa: E402


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["massing", "detail"], default="massing")
    ap.add_argument("--render", choices=["none", "test", "preview", "final", "ultra", "final4k"],
                    default="preview")
    ap.add_argument("--device", choices=["auto", "gpu", "cpu"], default="auto",
                    help="auto = GPU si Cycles encuentra una (OptiX > CUDA > HIP > oneAPI), si no CPU")
    ap.add_argument("--cams", default="", help="lista separada por comas (vacio = todas)")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--suffix", default="")
    return ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])


def sun_for(when_iso):
    when = dt.datetime.fromisoformat(when_iso)
    elev, az = S.sun_position(C.GEO["origin"][0], C.GEO["origin"][1], C.GEO["tz"], when)
    return elev, (az - C.GEO["grid_rot_deg"]) % 360, az


# ---------------------------------------------------------------- materiales

def make_materials(massing):
    mm = {"massing": M.massing("Massing gris", (0.62, 0.62, 0.6))}
    if massing:
        g = mm["massing"]
        keys = ["plaza", "adoquin", "asfalto", "anden", "bordillo", "terreno", "teja", "pedestal",
                "bronce", "monserrate", "ciudad_teja", "ciudad_plana", "hierro"]
        for k in keys:
            mm[k] = g
        mm["plaza"] = M.flat("Massing plaza", (0.45, 0.45, 0.45), 0.9)
        mm["asfalto"] = M.flat("Massing calle", (0.25, 0.25, 0.25), 0.9)
        mm["terreno"] = M.flat("Massing terreno", (0.25, 0.32, 0.22), 0.95)
        mm["ciudad"] = [M.flat("Massing ciudad", (0.55, 0.55, 0.53), 0.9)]
        return mm
    P = C.MATERIALS
    mm.update({
        "plaza": M.plaza_paving("Losas plaza", **P["plaza"]),
        "adoquin": M.pavers("Adoquin calles", **P["adoquin"]),
        "asfalto": M.asphalt("Asfalto"),
        "anden": M.plaza_paving("Anden", slab=(0.6, 0.4), base=(0.48, 0.47, 0.45), var=0.1,
                                offset=0.5, wet=0.1),
        "bordillo": M.smooth_stone("Bordillo", (0.5, 0.5, 0.48), grime=0.6),
        "capitolio_sillar": M.ashlar("Capitolio silleria", **P["capitolio_sillar"]),
        "capitolio_piedra": M.smooth_stone("Capitolio piedra labrada", **P["capitolio_piedra"]),
        "catedral_sillar": M.ashlar("Catedral silleria", **P["catedral_sillar"]),
        "catedral_piedra": M.smooth_stone("Catedral piedra labrada", **P["catedral_piedra"]),
        "sagrario_estuco": M.stucco("Sagrario estuco", **P["sagrario_estuco"]),
        "sagrario_piedra": M.smooth_stone("Sagrario piedra", **P["sagrario_piedra"]),
        "arzobispal_sillar": M.ashlar("Arzobispal silleria", **P["arzobispal_sillar"]),
        "arzobispal_piedra": M.smooth_stone("Arzobispal piedra", **P["arzobispal_piedra"]),
        "justicia_piedra": M.ashlar("Justicia piedra", **P["justicia_piedra"]),
        "lievano_estuco": M.stucco("Lievano estuco", **P["lievano_estuco"]),
        "lievano_molduras": M.smooth_stone("Lievano molduras", **P["lievano_molduras"]),
        "lievano_piedra": M.ashlar("Lievano arcada piedra", **P["lievano_piedra"]),
        "colonial_blanco": M.stucco("Colonial encalado", **P["colonial_blanco"]),
        "colonial_zocalo": M.painted("Colonial zocalo", P["colonial_zocalo"]["base"], 0.6),
        "crema": M.stucco("Estuco crema", **P["crema"]),
        "ocre_rojo": M.stucco("Estuco ocre rojo", **P["ocre_rojo"]),
        "molduras_blancas": M.smooth_stone("Molduras blancas", **P["molduras_blancas"]),
        "vidrio_azul": M.flat("Vidrio azul cupula", (0.05, 0.12, 0.22), 0.08),
        "reloj": M.flat("Esfera del reloj", (0.85, 0.84, 0.80), 0.4),
        "bandera": M.flag("Bandera de Colombia"),
        "pizarra": M.slate("Pizarra mansarda"),
        "teja": M.roof_tile("Teja de barro"),
        "cupula": M.smooth_stone("Cupulas", **P["cupula"]),
        "vidrio": M.glass("Vidrio"),
        "madera": M.painted("Madera puertas", P["madera"]),
        "madera_balcon": M.painted("Madera balcones", P["madera_balcon"]),
        "carpinteria_oscura": M.painted("Carpinteria oscura", P["carpinteria_oscura"]),
        "carpinteria_clara": M.painted("Carpinteria clara", P["carpinteria_clara"]),
        "hierro": M.iron("Hierro"),
        "bronce": M.bronze("Bronce estatua"),
        "bronce_letras": M.flat("Letras bronce", (0.35, 0.25, 0.12), 0.35, 1.0),
        "pedestal": M.smooth_stone("Pedestal arenisca", **P["pedestal"]),
        "terreno": M.terrain("Terreno", C.GEO["plaza_elev"], C.TERRAIN["urban_max_elev"],
                             C.TERRAIN["paramo_elev"]),
        "monserrate": M.stucco("Santuarios", (0.85, 0.84, 0.80), grime=0.3),
        "ciudad": [M.city_facade(f"Ciudad fachada {i}", c) for i, c in enumerate([
            (0.82, 0.80, 0.74), (0.78, 0.66, 0.45), (0.62, 0.60, 0.57), (0.75, 0.52, 0.38),
            (0.55, 0.62, 0.66), (0.70, 0.70, 0.62), (0.45, 0.42, 0.40)])],
        "ciudad_plana": M.flat("Ciudad cubierta plana", (0.32, 0.31, 0.30), 0.85),
    })
    mm["ciudad_teja"] = mm["teja"]
    return mm


# ---------------------------------------------------------------- suelo

def build_ground(mm, coll):
    F = C.FRAME
    zs = -0.12  # cota de calles peatonales (la plataforma de la plaza queda 12 cm mas alta)
    # calles peatonales alrededor (adoquin), extendidas por las bocacalles
    g = geo.MeshBuilder()
    g.plane(F["u_w"] - 70, F["v_s"] - 70, F["u_e"] + 70, F["v_n"] + 70, zs)
    g.to_object("Calles peatonales (adoquin)", coll, [mm["adoquin"]])
    # plataforma de la plaza (poligono OSM) como losa de 12 cm
    out = C.PLAZA["outline"]
    pl = geo.MeshBuilder()
    vs = [(x, y, 0.0) for x, y in out] + [(x, y, zs - 0.01) for x, y in out]
    n = len(out)
    faces = [tuple(range(n))] + [tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n)[::-1])
    pl._add(vs, faces, 0, False, None)
    o = pl.to_object("Plaza (losas)", coll, [mm["plaza"]])
    geo.bevel(o, 0.02)
    # plataforma de la estatua con gradas
    sp = C.PLAZA["statue_platform"]
    cx, cy = sp["center"]
    nsteps = sp["steps"]
    st = geo.MeshBuilder()
    for i in range(nsteps):
        inset = 0.40 * i
        w = sp["size"] + 2 * 0.40 * (nsteps - 1) - 2 * inset
        st.box_c(cx, cy, -0.01, w, w, sp["height"] * (i + 1) / nsteps + 0.01)
    o = st.to_object("Plataforma de la estatua", coll, [mm["plaza"]])
    geo.bevel(o, 0.02)
    # Carrera 8: calzada de asfalto + andenes con bordillo
    c8 = C.STREETS["cra8"]
    r0, r1 = c8["road"]
    zr = zs - C.STREETS["sidewalk_curb_h"]
    road = geo.MeshBuilder()
    road.plane(r0, F["v_s"] - 70, r1, F["v_n"] + 70, zr)
    road.to_object("Carrera 8 (calzada)", coll, [mm["asfalto"]])
    sw = geo.MeshBuilder()
    curb = geo.MeshBuilder()
    for a, b in ((c8["u0"] - 2, r0), (r1, c8["u1"])):
        sw.box(a, F["v_s"] - 70, b, F["v_n"] + 70, zr, zs + 0.002)
    for x in (r0, r1):
        curb.box(x - 0.15, F["v_s"] - 70, x + 0.15, F["v_n"] + 70, zr, zs + 0.004)
    sw.to_object("Carrera 8 (andenes)", coll, [mm["anden"]])
    o = curb.to_object("Carrera 8 (bordillos)", coll, [mm["bordillo"]])
    geo.bevel(o, 0.03)
    # atrio de la Catedral y el Sagrario, con gradas corridas hacia la Carrera 7
    A = C.ATRIUM
    at = geo.MeshBuilder()
    at.box(A["u0"], A["v0"], zs, A["u1"], A["v1"], A["h"])
    nst = int(round((A["h"] - zs) / A["riser"]))
    rise = (A["h"] - zs) / nst
    for i in range(nst):
        u = A["u0"] - (nst - i) * A["tread"]
        at.box(u, A["v0"], zs, A["u0"] + 0.01, A["v1"], zs + (i + 1) * rise)
    o = at.to_object("Atrio de la Catedral (gradas)", coll, [mm["catedral_piedra"]
                                                            if "catedral_piedra" in mm else
                                                            mm["massing"]])
    geo.bevel(o, 0.015)
    # muro del jardin del Palacio Arzobispal (desactivado: las fotos muestran fachada en linea)
    gw = C.GARDEN_WALL
    if not gw:
        return zs
    w = geo.MeshBuilder()
    w.box(gw["u"] - 0.25, gw["v0"], zs, gw["u"] + 0.25, gw["v1"], zs + gw["h"])
    w.box(gw["u"] - 0.35, gw["v0"], zs + gw["h"], gw["u"] + 0.35, gw["v1"], zs + gw["h"] + 0.2)
    o = w.to_object("Muro jardin arzobispal", coll, [mm.get("arzobispal_sillar", mm["massing"])])
    geo.bevel(o, 0.02)
    return zs


# ---------------------------------------------------------------- banderas

def add_flag(coll, mm, u, v, z, pole_h, seed=0, w=3.0, h=2.0):
    """Asta + bandera de Colombia ondeando (malla con ondulacion senoidal)."""
    pole = geo.MeshBuilder()
    pole.lathe([(0.0, 0), (0.09, 0), (0.07, pole_h), (0.11, pole_h + 0.05), (0.0, pole_h + 0.22)],
               12, (u, v, z))
    pole.to_object(f"Asta {seed}", coll, [mm["hierro"]])
    nx, nz = 24, 12
    verts, faces = [], []
    ph = seed * 1.7
    for j in range(nz + 1):
        for i in range(nx + 1):
            t = i / nx
            x = 0.12 + t * w
            y = 0.35 * t * math.sin(2 * math.pi * (t * 1.6) + ph) + 0.08 * math.sin(9 * t + j * 0.3)
            zz = pole_h - h - 0.3 + h * j / nz - 0.25 * t * t
            verts.append((x, y, zz))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me = bpy.data.meshes.new(f"Bandera {seed}")
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.materials.append(mm["bandera"])
    ob = bpy.data.objects.new(f"Bandera {seed}", me)
    ob.location = (u, v, z)
    ob.rotation_euler[2] = math.radians(C.LIGHT.get("wind_dir_deg", 200.0))
    ob["flag_h"] = h
    coll.objects.link(ob)
    sol = ob.modifiers.new("Grosor", "SOLIDIFY")
    sol.thickness = 0.01


# ---------------------------------------------------------------- personas

def _in_poly(x, y, poly):
    inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def add_people(mm, coll, zs):
    sp = C.PLAZA["statue_platform"]
    (sx, sy), half = sp["center"], sp["size"] / 2 + 0.8
    A = C.ATRIUM
    cap = C.BUILDINGS["capitolio"]
    cax = cap["root"][0] - cap["axis_local"]

    def on_platform(x, y):
        return abs(x - sx) < half and abs(y - sy) < half

    def z_at(x, y):
        if on_platform(x, y):
            return sp["height"]
        if A["u0"] < x < A["u1"] and A["v0"] < y < A["v1"]:
            return A["h"]
        if _in_poly(x, y, C.PLAZA["outline"]):
            return 0.0
        return zs

    r = C.PEOPLE["cam_clear_r"]
    cams = [c["loc"] for c in C.CAMERAS.values() if c["loc"][2] < 3]
    avoid = [
        lambda x, y: (x - sx) ** 2 + (y - sy) ** 2 < 3.2 ** 2,                    # pedestal
        lambda x, y: on_platform(x, y) and not (abs(x - sx) < half - 1.4 and
                                                abs(y - sy) < half - 1.4),       # gradas
        lambda x, y: abs(x - cax) < 19 and -68.0 < y < -59.0,                    # escalinata Capitolio
        lambda x, y: A["u0"] - 3.8 < x < A["u0"] + 0.4 and A["v0"] < y < A["v1"],  # gradas atrio
        lambda x, y: -51.0 < x < -42.5,                                          # calzada Cra 8
        lambda x, y: any((x - c[0]) ** 2 + (y - c[1]) ** 2 < r * r for c in cams),
    ]
    zones = [(-38, -48, 38, 46, 7.0), (0.5, -21.0, 12.3, -9.5, 0.8), (40.5, -50, 50.5, 50, 1.5),
             (53.5, -14, 60.5, 50, 1.2), (-38, -59, 45, -51, 1.0), (-38, 51, 45, 66, 1.0),
             (-55, -50, -51.5, 54, 0.5)]
    zones = [(u0, v0, u1, v1, 0.0, w) for (u0, v0, u1, v1, w) in zones]
    skins = [M.flat(f"Piel {i}", c, 0.5) for i, c in enumerate(
        [(0.55, 0.38, 0.28), (0.42, 0.28, 0.19), (0.28, 0.18, 0.12), (0.65, 0.48, 0.38)])]
    tops = [M.flat(f"Ropa {i}", c, 0.8) for i, c in enumerate(
        [(0.02, 0.02, 0.025), (0.03, 0.04, 0.08), (0.08, 0.08, 0.085), (0.18, 0.10, 0.06),
         (0.12, 0.14, 0.07), (0.35, 0.04, 0.04), (0.45, 0.32, 0.06), (0.45, 0.45, 0.43),
         (0.05, 0.12, 0.20), (0.30, 0.20, 0.25)])]
    bottoms = [M.flat(f"Pantalon {i}", c, 0.85) for i, c in enumerate(
        [(0.04, 0.06, 0.12), (0.02, 0.02, 0.02), (0.12, 0.12, 0.12), (0.30, 0.26, 0.20),
         (0.08, 0.10, 0.16)])]
    hair = M.flat("Pelo y zapatos", (0.015, 0.012, 0.01), 0.6)
    objs = PP.scatter_people(coll, {"piel": skins, "arriba": tops, "abajo": bottoms, "pelo": hair},
                             zones, C.PEOPLE["n"], C.PEOPLE["seed"], avoid)
    # ajustar la cota de cada grupo: se hace por vertice segun su posicion
    for ob in objs:
        me = ob.data
        for v in me.vertices:
            v.co.z += z_at(v.co.x, v.co.y)
    pig = M.flat("Paloma", (0.22, 0.23, 0.26), 0.7)
    PP.scatter_pigeons(coll, pig, (sx, sy), 24.0, C.PEOPLE["pigeons"], 9, 0.0,
                       avoid=[lambda x, y: abs(x - sx) < half + 0.3 and abs(y - sy) < half + 0.3,
                              lambda x, y: not _in_poly(x, y, C.PLAZA["outline"]),
                              avoid[-1]])


# ---------------------------------------------------------------- escena

def build(stage):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    massing = stage == "massing"
    elev, az_m, az = sun_for(C.LIGHT["datetime"])
    M.HAZE = None if massing else {
        "dist": C.LIGHT["haze_dist"], "elev": elev, "az": az_m,
        "altitude": C.GEO["plaza_elev"], "air": C.LIGHT["sky"]["air"],
        "aerosol": C.LIGHT["sky"]["aerosol"], "strength": 0.85}
    mm = make_materials(massing)
    root = geo.collection("Plaza de Bolivar")
    ctx = B.Ctx(mm, root, massing)

    zs = build_ground(mm, geo.collection("Suelo, plaza y calles", root))

    for key, b in C.BUILDINGS.items():
        b = dict(b)
        coll = ctx.coll(b["name"])
        root_e = geo.facade_root(f"{b['name']} (origen)", coll, b["root"], b["facing"],
                                 z=b.get("z", zs))
        root_e.rotation_euler[2] += math.radians(b.get("rot_adjust", 0.0))
        kind = b["builder"]
        if kind == "generico":
            B.palacio_generico(ctx, b, root_e, b["name"],
                               mm["massing"] if massing else mm[b["wall_mat"]],
                               mm["massing"] if massing else mm[b["trim_mat"]], roof=b.get("roof"))
        else:
            getattr(B, {"capitolio": "capitolio", "catedral": "catedral", "sagrario": "sagrario",
                        "justicia": "palacio_justicia", "lievano": "lievano"}[kind])(ctx, b, root_e)

    # estatua sobre su plataforma
    sp = C.PLAZA["statue_platform"]
    B.estatua(ctx, C.STATUE)  # aplica el giro de la estatua a sus objetos
    st_root = geo.empty("Estatua de Bolivar (origen)", ctx.coll("Estatua de Bolivar"),
                        (sp["center"][0], sp["center"][1], sp["height"]), 0.0)
    for o in ctx.coll("Estatua de Bolivar").objects:
        if o is not st_root and o.parent is None:
            o.parent = st_root

    if not massing:
        add_people(mm, ctx.coll("Personas y palomas"), zs)
        fc = ctx.coll("Banderas")
        for i, (u, v, z, h) in enumerate(C.FLAGS):
            add_flag(fc, mm, u, v, z, h, seed=i)

    # terreno real (DEM) y ciudad OSM
    frame = T.Frame(C.GEO["origin"], C.GEO["grid_rot_deg"])
    dem = T.DEM(os.path.join(ROOT, C.TERRAIN["dem"]))
    hfn = T.terrain_height_fn(dem, frame, C.GEO["plaza_elev"], C.CITY["flatten_r"])
    tcoll = geo.collection("Terreno y cerros orientales", root)
    T.build_terrain(tcoll, mm["terreno"], hfn, C.TERRAIN["u_range"], C.TERRAIN["v_range"],
                    C.TERRAIN["step"])
    for lm in C.LANDMARKS:
        T.landmark(tcoll, mm["monserrate"], mm["teja"], frame, hfn, dem, lm)
    ccoll = geo.collection("Ciudad (OSM)", root)
    T.osm_city(ccoll, os.path.join(ROOT, C.CITY["osm"]), frame, hfn, mm["ciudad"],
               (mm["ciudad_teja"], mm["ciudad_plana"]), C.CITY, massing)
    for name, poly, h in C.FILLERS:
        T.filler(ccoll, name, poly, h, mm["ciudad"][0], zs)

    # luz y camaras
    lc = geo.collection("Luz y camaras", root)
    print(f"[sol] {C.LIGHT['datetime']}: elevacion {elev:.1f}, azimut {az:.1f} (modelo {az_m:.1f})")
    S.setup_world(elev, az_m, C.GEO["plaza_elev"], **C.LIGHT["sky"])
    S.add_sun(elev, az_m, C.LIGHT["sun_strength"], coll=lc)
    for name, cam in C.CAMERAS.items():
        o = S.add_camera(name, cam["loc"], cam["target"], cam["focal"], cam.get("level", True), lc,
                         shift_x=cam.get("shift_x", 0.0))
        o["datetime"] = cam.get("datetime", C.LIGHT["datetime"])
    return frame


def main():
    a = parse()
    build(a.stage)
    tag = "massing" if a.stage == "massing" else "detalle"
    if not a.no_save:
        S.save_blend(os.path.join(ROOT, "blend", f"plaza_{tag}{a.suffix}.blend"))
    if a.render != "none":
        S.setup_render(a.render, C.LIGHT["exposure"], C.LIGHT["look"], a.device)
        cams = [c for c in a.cams.split(",") if c] or list(C.CAMERAS)
        for cam in cams:
            elev, az_m, az = sun_for(C.CAMERAS[cam].get("datetime", C.LIGHT["datetime"]))
            S.update_sun(elev, az_m)
            print(f"[sol] {cam}: elevacion {elev:.1f}, azimut real {az:.1f}")
            out = os.path.join(ROOT, "renders", tag, f"{cam}_{a.render}{a.suffix}.png")
            S.render_camera(cam, out)


if __name__ == "__main__":
    main()
