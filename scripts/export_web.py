"""Exporta la escena al simulador web (three.js). Se ejecuta donde estan las texturas (pod GPU).

Uso:  .venv/bin/python scripts/export_web.py --out web/public/scene [--device gpu]

Salida (en --out):
  nucleo.glb, ciudad.glb, terreno.glb   geometria (modificadores aplicados, UV en metros,
                                        mallas unidas por material, materiales solo como nombre)
  scene.json                            materiales, sol, camaras, puntos de interes, limites
  tex/*.jpg                             texturas PBR (1K) + terreno (4K) + fachadas urbanas
  sky.jpg / sky_env.hdr                 fondo 8K tonemapeado (AgX) e iluminacion HDR 1K
  minimapa.jpg                          planta cenital de la plaza
Coordenadas: Blender (u, v, z). El exportador glTF las pasa a Y arriba: (x, y, z) = (u, z, -v).
"""
import argparse
import json
import math
import os
import shutil
import sys

import bpy
import bmesh
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build as BD  # noqa: E402
from plaza import config as C  # noqa: E402
from plaza import materials as M  # noqa: E402
from plaza import scene as S  # noqa: E402

CHUNK_OF_COLLECTION = {
    "Ciudad (OSM)": "ciudad",
    "Terreno y cerros orientales": "terreno",
}
SKIP_PREFIX = ("Sol",)

# Materiales constantes para la web (los procedurales que no tienen textura)
CONST = {
    "Vidrio": dict(color=(0.02, 0.025, 0.03), roughness=0.05, metalness=0.0, envBoost=1.6),
    "Vidrio azul cupula": dict(color=(0.05, 0.12, 0.22), roughness=0.08, metalness=0.2),
    "Hierro": dict(color=(0.025, 0.027, 0.028), roughness=0.45, metalness=0.7),
    "Bronce estatua": dict(color=(0.20, 0.17, 0.11), roughness=0.5, metalness=0.75),
    "Letras bronce": dict(color=(0.35, 0.25, 0.12), roughness=0.35, metalness=1.0),
    "Esfera del reloj": dict(color=(0.85, 0.84, 0.80), roughness=0.4, metalness=0.0),
    "Farol vidrio": dict(color=(0.9, 0.85, 0.7), roughness=0.25, metalness=0.0, transmission=0.4),
    "Santuarios": dict(color=(0.85, 0.84, 0.80), roughness=0.8, metalness=0.0),
    "Madera balcones": dict(color=(0.12, 0.20, 0.13), roughness=0.55, metalness=0.0),
    "Carpinteria oscura": dict(color=(0.06, 0.07, 0.07), roughness=0.45, metalness=0.0),
    "Carpinteria clara": dict(color=(0.80, 0.80, 0.77), roughness=0.45, metalness=0.0),
    "Colonial zocalo": dict(color=(0.30, 0.22, 0.14), roughness=0.6, metalness=0.0),
    "Cupula roja": dict(color=(0.42, 0.06, 0.04), roughness=0.6, metalness=0.0),
    "Ciudad cubierta plana": dict(color=(0.32, 0.31, 0.30), roughness=0.85, metalness=0.0),
    "Paloma": dict(color=(0.22, 0.23, 0.26), roughness=0.7, metalness=0.0),
    "Pelo y zapatos": dict(color=(0.015, 0.012, 0.01), roughness=0.6, metalness=0.0),
}


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "web", "public", "scene"))
    ap.add_argument("--device", default="auto")
    ap.add_argument("--tex-size", type=int, default=1024)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    return ap.parse_args(argv)


# ---------------------------------------------------------------- utilidades

def chunk_for(ob):
    for c in ob.users_collection:
        name = c.name
        for key, chunk in CHUNK_OF_COLLECTION.items():
            if name == key:
                return chunk
    return "nucleo"


def principled_values(mat):
    if mat is None or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            bc = n.inputs["Base Color"]
            col = tuple(bc.default_value[:3])
            return dict(color=col, roughness=float(n.inputs["Roughness"].default_value),
                        metalness=float(n.inputs["Metallic"].default_value),
                        linked=bc.is_linked)
    return None


def evaluated_world_mesh(ob, dg):
    """Malla con todos los modificadores aplicados y en coordenadas de mundo."""
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(ob.matrix_world)
    if ob.matrix_world.determinant() < 0:
        me.flip_normals()
    return me


def uv_from_attribute(me):
    """Garantiza una capa UV real 'UVMap' (la del modificador de nodos llega como atributo)."""
    attr = me.attributes.get("UVMap")
    if attr is not None and attr.data_type == "FLOAT2" and attr.domain == "CORNER":
        if "UVMap" not in me.uv_layers:
            data = np.empty(len(me.loops) * 2, dtype=np.float32)
            attr.data.foreach_get("vector", data)
            me.attributes.remove(attr)
            uv = me.uv_layers.new(name="UVMap")
            uv.data.foreach_set("uv", data)
    elif "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")


# ---------------------------------------------------------------- horneados

def bake_image(obj, mat, name, w, h, kind="COLOR"):
    """Hornea el color base (o la rugosidad) del material de obj a una imagen nueva."""
    img = bpy.data.images.new(name, w, h, alpha=False,
                              float_buffer=False, is_data=(kind == "ROUGHNESS"))
    nt = mat.node_tree
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 8
    sc.render.bake.margin = 4
    if kind == "COLOR":
        sc.render.bake.use_pass_direct = False
        sc.render.bake.use_pass_indirect = False
        sc.render.bake.use_pass_color = True
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    else:
        bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    nt.nodes.remove(node)
    return img


def save_jpg(img, path, quality=88):
    sc = bpy.context.scene
    st = sc.render.image_settings
    st.file_format = "JPEG"
    st.quality = quality
    st.color_mode = "RGB"
    img.save_render(path, scene=sc)


def bake_terrain(obj, out_dir, size=4096):
    me = obj.data
    u0, u1 = C.TERRAIN["u_range"]
    v0, v1 = C.TERRAIN["v_range"]
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    li = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", li)
    uv = np.stack([(co[li, 0] - u0) / (u1 - u0), (co[li, 1] - v0) / (v1 - v0)], 1)
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    layer = me.uv_layers.new(name="UVTerr")
    layer.data.foreach_set("uv", uv.astype(np.float32).ravel())
    me.uv_layers.active = layer
    img = bake_image(obj, obj.active_material, "terreno_color", size, size)
    save_jpg(img, os.path.join(out_dir, "tex", "terreno.jpg"), 85)
    return {"type": "unique", "map": "tex/terreno.jpg", "roughness": 0.92, "uv": "UVTerr"}


def bake_city_tile(mat, out_dir, tile=(10.4, 7.0), px=1024):
    """Hornea una fachada urbana procedural a una textura repetible de tile metros."""
    w, h = tile
    me = bpy.data.meshes.new("bake_plane")
    z0 = 100.0  # lejos del suelo para no hornear la suciedad de la base
    me.from_pydata([(0, 0, z0), (w, 0, z0), (w, 0, z0 + h), (0, 0, z0 + h)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="bake")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    me.materials.append(mat)
    ob = bpy.data.objects.new("bake_plane", me)
    bpy.context.scene.collection.objects.link(ob)
    hpx = int(px * h / w)
    col = bake_image(ob, mat, mat.name + "_c", px, hpx)
    rgh = bake_image(ob, mat, mat.name + "_r", px // 2, hpx // 2, "ROUGHNESS")
    safe = mat.name.replace(" ", "_")
    save_jpg(col, os.path.join(out_dir, "tex", f"{safe}.jpg"), 85)
    save_jpg(rgh, os.path.join(out_dir, "tex", f"{safe}_r.jpg"), 85)
    bpy.data.objects.remove(ob)
    return {"type": "tile", "map": f"tex/{safe}.jpg", "roughnessMap": f"tex/{safe}_r.jpg",
            "tile": [w, h]}


def prepare_pbr_textures(out_dir, used, size):
    """Copia/redimensiona las texturas PBR (diff, rough, nor) a JPG del tamano web."""
    from PIL import Image
    done = set()
    for tex in used:
        if tex in done:
            continue
        for kind in ("diff", "rough", "nor"):
            src = os.path.join(M.TEX["dir"], f"{tex}_{kind}_2k.jpg")
            dst = os.path.join(out_dir, "tex", f"{tex}_{kind}.jpg")
            im = Image.open(src)
            im = im.convert("L" if kind == "rough" else "RGB").resize((size, size), Image.LANCZOS)
            im.save(dst, quality=86 if kind != "nor" else 92)
        done.add(tex)


# ---------------------------------------------------------------- cielo

def write_rgbe(path, img):
    """Guarda float32 HxWx3 como Radiance .hdr sin RLE."""
    h, w, _ = img.shape
    mx = img.max(axis=2)
    e = np.where(mx > 1e-32, np.ceil(np.log2(np.maximum(mx, 1e-32))), -128).astype(np.int32)
    sc = np.where(mx > 1e-32, 256.0 / np.power(2.0, e), 0.0)
    rgb = np.clip(img * sc[..., None], 0, 255).astype(np.uint8)
    ex = np.clip(e + 128, 0, 255).astype(np.uint8)
    data = np.concatenate([rgb, ex[..., None]], axis=2)
    with open(path, "wb") as f:
        f.write(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n")
        f.write(f"-Y {h} +X {w}\n".encode())
        f.write(data.tobytes())


def export_sky(out_dir, hdri_path, rot_deg, exposure, look):
    """Cielo para three.js a partir del HDRI (sin re-render):

    - sky_bg.jpg : fondo 8K en HDR codificado (valor = 8 * jpg^2.2, lineal) para que el cielo pase
                   por el mismo tone mapping que la escena. Disco solar recortado.
    - sky_env.hdr: iluminacion (IBL) 1K en Radiance, sol recortado (el sol es una luz direccional).
    Convenciones: la rotacion Z de Blender equivale a desplazar columnas rot/360*W; three.js usa
    u3 = uBlender - 0.5 (medio ancho).
    """
    from PIL import Image

    def load(path):
        im = bpy.data.images.load(path)
        w, h = im.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        bpy.data.images.remove(im)
        px = buf.reshape(h, w, 4)[::-1, :, :3]  # fila 0 arriba
        px = np.roll(px, int(round(rot_deg / 360.0 * w)), axis=1)
        return np.roll(px, w // 2, axis=1)

    big = load(hdri_path)
    lum = big.mean(axis=2)
    hor = big[big.shape[0] // 2 - big.shape[0] // 40: big.shape[0] // 2].reshape(-1, 3)
    fog_color = [float(x) for x in np.median(hor, axis=0)]
    enc = np.power(np.clip(big / 8.0, 0.0, 1.0), 1.0 / 2.2)
    Image.fromarray((enc * 255 + 0.5).astype(np.uint8)).save(
        os.path.join(out_dir, "sky_bg.jpg"), quality=90)
    del big, enc
    small = load(hdri_path.replace("_8k.hdr", "_2k.hdr"))
    h, w, _ = small.shape
    lum = small.mean(axis=2)
    cut = np.percentile(lum, 99.9)
    k = np.minimum(1.0, cut * 1.5 / np.maximum(lum, 1e-6))
    small = (small * k[..., None]).reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))
    write_rgbe(os.path.join(out_dir, "sky_env.hdr"), small.astype(np.float32))
    return fog_color


def export_minimap(out_dir, half=140.0, px=1024):
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("planta")
    cam.type = "ORTHO"
    cam.ortho_scale = 2 * half
    co = bpy.data.objects.new("planta", cam)
    sc.collection.objects.link(co)
    co.location = (0, 0, 400)
    co.rotation_euler = (0, 0, 0)
    sc.camera = co
    sc.render.resolution_x = sc.render.resolution_y = px
    sc.cycles.samples = 32
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 85
    sc.render.filepath = os.path.join(out_dir, "minimapa.jpg")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)
    return {"half": half, "px": px}


# ---------------------------------------------------------------- principal

def main():
    a = parse()
    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, "tex"), exist_ok=True)
    BD.build("detail", haze=False)
    sc = bpy.context.scene
    hdri_mode = sc.get("modo_luz") == "hdri"
    S.setup_render("preview", C.ASSETS["exposure"] if hdri_mode else C.LIGHT["exposure"],
                   C.LIGHT["look"], a.device)

    # --- materiales: describir para la web y hornear lo procedural
    mats = {}
    used_tex = set()
    terrain = next(o for o in bpy.data.objects if o.name.startswith("Cerros orientales"))
    for mat in bpy.data.materials:
        if mat.users == 0:
            continue
        if "pbr" in mat:
            d = mat["pbr"].to_dict() if hasattr(mat["pbr"], "to_dict") else dict(mat["pbr"])
            tex = d["tex"]
            avg = M.TEX["avg"][tex]
            tint = d.get("tint")
            factor = [t / max(v, 1e-3) for t, v in zip(tint, avg)] if tint else [1, 1, 1]
            mats[mat.name] = {"type": "pbr", "map": f"tex/{tex}_diff.jpg",
                              "roughnessMap": f"tex/{tex}_rough.jpg",
                              "normalMap": f"tex/{tex}_nor.jpg", "tile": [d["tile"], d["tile"]],
                              "color": factor}
            used_tex.add(tex)
        elif mat.name in CONST:
            mats[mat.name] = dict(type="const", **CONST[mat.name])
        elif mat.name.startswith("Ciudad fachada"):
            mats[mat.name] = bake_city_tile(mat, out)
        elif mat.name == "Bandera de Colombia":
            mats[mat.name] = {"type": "flag"}
        elif mat.name.startswith(("Piel", "Ropa", "Pantalon")):
            v = principled_values(mat)
            mats[mat.name] = dict(type="const", color=v["color"], roughness=v["roughness"],
                                  metalness=0.0)
        else:
            v = principled_values(mat)
            if v and not v["linked"]:
                mats[mat.name] = dict(type="const", color=v["color"], roughness=v["roughness"],
                                      metalness=v["metalness"])
    mats[terrain.active_material.name] = bake_terrain(terrain, out)
    prepare_pbr_textures(out, used_tex, a.tex_size)
    missing = sorted({s.material.name for o in bpy.data.objects if o.type == "MESH"
                      for s in o.material_slots if s.material and s.material.name not in mats})
    for name in missing:
        mats[name] = dict(type="const", color=(0.6, 0.6, 0.6), roughness=0.8, metalness=0.0)
    print("[web] materiales sin descripcion (gris):", missing)

    # --- geometria: aplicar modificadores, unir por (bloque, material)
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for ob in list(bpy.data.objects):
        if ob.type not in ("MESH", "FONT") or ob.hide_render or ob.name.startswith(SKIP_PREFIX):
            continue
        me = evaluated_world_mesh(ob, dg)
        if len(me.polygons) == 0:
            bpy.data.meshes.remove(me)
            continue
        if ob is not terrain:
            uv_from_attribute(me)
        groups.setdefault(chunk_for(ob), []).append(me)
    # los objetos originales se ocultan; se exportan solo las mallas unidas
    scn = bpy.context.scene
    exp_coll = bpy.data.collections.new("export_web")
    scn.collection.children.link(exp_coll)
    stats = {}
    for chunk, meshes in groups.items():
        bm_by_mat = {}
        for me in meshes:
            bm = bmesh.new()
            bm.from_mesh(me)
            for mi, mat in enumerate(me.materials):
                key = mat.name if mat else "sin_material"
                faces = [f for f in bm.faces if f.material_index == mi]
                if not faces:
                    continue
                sub = bm.copy()
                bmesh.ops.delete(sub, geom=[f for f in sub.faces if f.material_index != mi],
                                 context="FACES")
                tmp = bpy.data.meshes.new("tmp")
                sub.to_mesh(tmp)
                sub.free()
                bm_by_mat.setdefault(key, []).append(tmp)
            bm.free()
        objs = []
        for key, parts in bm_by_mat.items():
            bm = bmesh.new()
            for p in parts:
                bm.from_mesh(p)
            merged = bpy.data.meshes.new(f"{chunk}:{key}")
            bm.to_mesh(merged)
            bm.free()
            for p in parts:
                bpy.data.meshes.remove(p)
            merged.materials.clear()
            mat = bpy.data.materials.get(key) or bpy.data.materials.new(key)
            merged.materials.append(mat)
            ob = bpy.data.objects.new(f"{chunk}:{key}", merged)
            exp_coll.objects.link(ob)
            objs.append(ob)
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
        stats[chunk] = {"objects": len(objs), "triangles": tris}
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objs)
        bpy.ops.export_scene.gltf(filepath=os.path.join(out, f"{chunk}.glb"), export_format="GLB",
                                  use_selection=True, export_materials="PLACEHOLDER",
                                  export_texcoords=True, export_normals=True, export_apply=False,
                                  export_yup=True, export_cameras=False, export_lights=False)
        for o in objs:
            bpy.data.objects.remove(o)
        print(f"[web] {chunk}: {stats[chunk]}", flush=True)

    # --- cielo, minimapa, metadatos
    elev, az_m, az = BD.sun_for(C.LIGHT["datetime"])
    sky = {}
    if hdri_mode:
        w = bpy.data.worlds["Cielo"]
        fog_color = export_sky(out, w["hdri"], w["hdri_rot"], C.ASSETS["exposure"], C.LIGHT["look"])
        info = json.load(open(os.path.join(ROOT, C.ASSETS["info"])))["hdri"]
        sun_normal = info["E_sun_horizontal"] / math.sin(math.radians(info["sun_elev"]))
        sky = {"background": "sky_bg.jpg", "backgroundScale": 8.0, "backgroundGamma": 2.2,
               "environment": "sky_env.hdr", "fogColor": fog_color,
               "sunIntensity": sun_normal + C.ASSETS.get("sun_boost", 0.0),
               "exposure": C.ASSETS["exposure"]}
    mini = export_minimap(out)
    sun_dir_blender = [math.cos(math.radians(elev)) * math.sin(math.radians(az_m)),
                       math.cos(math.radians(elev)) * math.cos(math.radians(az_m)),
                       math.sin(math.radians(elev))]
    meta = {
        "materials": mats,
        "sun": {"elevation": elev, "azimuthModel": az_m, "azimuthTrue": az,
                "dirBlender": sun_dir_blender, "datetime": C.LIGHT["datetime"]},
        "sky": sky,
        "fog": {"distance": C.LIGHT["haze_dist"]},
        "minimap": mini,
        "cameras": {k: {"loc": v["loc"], "target": v["target"], "focal": v["focal"]}
                    for k, v in C.CAMERAS.items()},
        "plaza": {"outline": C.PLAZA["outline"], "frame": C.FRAME},
        "gridRotationDeg": C.GEO["grid_rot_deg"],
        "stats": stats,
    }
    json.dump(meta, open(os.path.join(out, "scene.json"), "w"), indent=1, ensure_ascii=False)
    print("[web] listo", out)


if __name__ == "__main__":
    main()
