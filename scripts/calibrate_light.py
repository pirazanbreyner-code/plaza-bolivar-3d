"""Mide la irradiancia del cielo y de la lampara solar sobre un plano horizontal blanco.

Sirve para fijar LIGHT.sun_strength (relacion sol/cielo realista) y LIGHT.exposure.
Uso: .venv/bin/python scripts/calibrate_light.py
"""
import datetime as dt, math, os, sys, tempfile
import bpy, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plaza import config as C, scene as S

def measure(sky, sun_strength, elev, az):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 256; sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = 16
    sc.view_settings.view_transform = "Standard"
    if sky:
        S.setup_world(elev, az, C.GEO["plaza_elev"], **C.LIGHT["sky"])
    else:
        w = bpy.data.worlds.new("negro"); sc.world = w
        w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    if sun_strength:
        S.add_sun(elev, az, sun_strength)
    me = bpy.data.meshes.new("p"); me.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[],[(0,1,2,3)])
    ob = bpy.data.objects.new("p", me); sc.collection.objects.link(ob)
    m = bpy.data.materials.new("blanco"); b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1,1,1,1); b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    me.materials.append(m)
    ob.visible_shadow = False
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.5; cam.location = (0,0,0.5); sc.camera = cam
    out = os.path.join(tempfile.gettempdir(), "calib.exr")
    sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    px = np.array(bpy.data.images.load(out).pixels[:]).reshape(-1, 4)[:, :3]
    return px.mean(0)

when = dt.datetime.fromisoformat(C.LIGHT["datetime"])
elev, az = S.sun_position(C.GEO["origin"][0], C.GEO["origin"][1], C.GEO["tz"], when)
sky = measure(True, 0, elev, az)
sun = measure(False, 1.0, elev, az)
e_sky = sky.mean() * math.pi
e_sun1 = sun.mean() * math.pi
print(f"elev {elev:.1f}  E_cielo(horizontal) = {e_sky:.4f}   E_sol(1 W/m2) = {e_sun1:.4f}")
for ratio in (2.5, 3.0, 4.0):
    s = ratio * e_sky / e_sun1
    total = e_sky + s * e_sun1
    expo = math.log2(2.7 / total)
    print(f"  ratio directa/difusa {ratio}: sun_strength = {s:.2f}  E_total = {total:.3f}  exposure ~ {expo:+.2f}")
