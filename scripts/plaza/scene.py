"""Cielo, sol, nubes, camaras, presets de render y guardado."""
import datetime as _dt
import math
import os

import bpy

from . import materials as M


# ---------------------------------------------------------------- posicion solar

def sun_position(lat, lon, tz_hours, when):
    """Elevacion y azimut (grados, azimut desde el norte en sentido horario). NOAA simplificado."""
    doy = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hour * 60 + eqt + 4 * lon - 60 * tz_hours
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    cos_z = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    zen = math.acos(max(-1, min(1, cos_z)))
    elev = 90 - math.degrees(zen)
    az = math.degrees(math.atan2(math.sin(ha),
                                 math.cos(ha) * math.sin(la) - math.tan(decl) * math.cos(la)))
    az = (az + 180) % 360
    return elev, az


# ---------------------------------------------------------------- mundo

def setup_world(elev_deg, az_model_deg, altitude_m=2600.0, clouds=0.45, cloud_bright=1.0,
                strength=1.0, air=1.0, aerosol=1.5):
    """Cielo fisico (dispersion multiple) + nubes procedurales. Sin disco solar (lo pone la lampara)."""
    w = bpy.data.worlds.get("Cielo") or bpy.data.worlds.new("Cielo")
    bpy.context.scene.world = w
    t = M.NT(w)
    sky = t.n("ShaderNodeTexSky", sky_type="MULTIPLE_SCATTERING")
    sky.sun_disc = False
    sky.sun_elevation = math.radians(elev_deg)
    sky.sun_rotation = math.radians(az_model_deg)
    sky.altitude = altitude_m
    sky.air_density = air
    sky.aerosol_density = aerosol
    tc = t.n("ShaderNodeTexCoord")
    d = t.separate(tc.outputs["Generated"])
    zc = t.math("MAXIMUM", d[2], 0.0)
    den = t.math("ADD", zc, 0.06)
    u = t.math("DIVIDE", d[0], den)
    v = t.math("DIVIDE", d[1], den)
    uv = t.combine(u, v, 0.0)
    n = t.noise(uv, 0.32, 10, 0.62, distortion=0.45)
    c0 = 0.64 - clouds * 0.25
    shape = t.maprange(n.outputs["Fac"], c0, c0 + 0.045, 0.0, 1.0, smooth=True)
    horizon = t.maprange(d[2], 0.0, 0.10, 0.0, 1.0, smooth=True)
    mask = t.math("MULTIPLY", shape, horizon)
    dens = t.noise(uv, 1.6, 6, 0.6).outputs["Fac"]
    # brillo de la nube proporcional a la luminancia del cielo en esa direccion
    bw = t.n("ShaderNodeRGBToBW")
    t.l(sky.outputs[0], bw.inputs[0])
    lum = t.math("MULTIPLY", bw.outputs[0], cloud_bright)
    thick = t.maprange(n.outputs["Fac"], c0, c0 + 0.25, 0.0, 1.0)
    shade = t.math("ADD", t.maprange(dens, 0.3, 0.7, 0.35, 0.75),
                   t.math("MULTIPLY", t.math("SUBTRACT", 1.0, thick), 0.55))
    k = t.math("MULTIPLY", lum, shade)
    cloud_col = t.mix(1.0, t.combine(k, k, k), (1.0, 0.98, 0.95, 1.0), "MULTIPLY")
    col = t.mix(mask, sky.outputs[0], cloud_col)
    bg = t.n("ShaderNodeBackground", inputs={"Strength": strength})
    t.l(col, bg.inputs["Color"])
    out = t.n("ShaderNodeOutputWorld")
    t.l(bg.outputs[0], out.inputs["Surface"])
    w["cloud_noise"] = n.name
    return w


def add_sun(elev_deg, az_model_deg, strength=4.0, angle_deg=0.53, coll=None):
    data = bpy.data.lights.get("Sol") or bpy.data.lights.new("Sol", "SUN")
    data.energy = strength
    data.angle = math.radians(angle_deg)
    data.color = (1.0, 0.96, 0.9)
    obj = bpy.data.objects.get("Sol") or bpy.data.objects.new("Sol", data)
    if obj.name not in (coll or bpy.context.scene.collection).objects:
        (coll or bpy.context.scene.collection).objects.link(obj)
    obj.rotation_euler = (math.radians(90 - elev_deg), 0.0, math.radians(180 - az_model_deg))
    obj.location = (0, 0, 120)
    return obj


# ---------------------------------------------------------------- camaras

def add_camera(name, loc, target, focal=28.0, level=True, coll=None, sensor=36.0, shift_x=0.0,
               clip_end=20000.0):
    """Camara. Con level=True no se inclina (verticales rectas) y se encuadra con shift vertical."""
    cam = bpy.data.cameras.new(name)
    cam.lens = focal
    cam.sensor_width = sensor
    cam.clip_start = 0.1
    cam.clip_end = clip_end
    obj = bpy.data.objects.new(name, cam)
    (coll or bpy.context.scene.collection).objects.link(obj)
    obj.location = loc
    dx, dy, dz = (target[0] - loc[0], target[1] - loc[1], target[2] - loc[2])
    yaw = math.atan2(dy, dx) - math.pi / 2
    horiz = math.hypot(dx, dy)
    pitch = math.atan2(dz, horiz)
    if level:
        obj.rotation_euler = (math.radians(90), 0, yaw)
        cam.shift_y = max(-1.0, min(1.0, focal * math.tan(pitch) / sensor))
    else:
        obj.rotation_euler = (math.radians(90) + pitch, 0, yaw)
    cam.shift_x = shift_x
    return obj


# ---------------------------------------------------------------- render

PRESETS = {
    "test": dict(res=(480, 270), samples=16, threshold=0.1),
    "preview": dict(res=(960, 540), samples=64, threshold=0.05),
    "final": dict(res=(1920, 1080), samples=384, threshold=0.015),
    "final4k": dict(res=(3840, 2160), samples=1024, threshold=0.01),
}


def setup_render(preset="preview", exposure=0.0, look="AgX - Base Contrast"):
    sc = bpy.context.scene
    p = PRESETS[preset]
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device = "CPU"
    c.samples = p["samples"]
    c.use_adaptive_sampling = True
    c.adaptive_threshold = p["threshold"]
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    try:
        c.denoising_prefilter = "ACCURATE"
    except Exception:
        pass
    c.max_bounces = 8
    c.diffuse_bounces = 4
    c.glossy_bounces = 4
    c.transmission_bounces = 8
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0
    c.blur_glossy = 1.0
    c.use_light_tree = True
    sc.render.resolution_x, sc.render.resolution_y = p["res"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.film_transparent = False
    vs = sc.view_settings
    vs.view_transform = "AgX"
    vs.look = look
    vs.exposure = exposure
    vs.gamma = 1.0
    sc.render.threads_mode = "AUTO"
    return sc


def render_camera(cam_name, out_path):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam_name]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sc.render.filepath = out_path
    t0 = _dt.datetime.now()
    bpy.ops.render.render(write_still=True)
    dt = (_dt.datetime.now() - t0).total_seconds()
    print(f"[render] {cam_name} -> {out_path} ({dt:.1f}s)", flush=True)
    return dt


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), compress=True)
    print(f"[blend] guardado {path}", flush=True)


def update_sun(elev_deg, az_model_deg):
    """Actualiza sol, cielo del World y nodos de cielo de la bruma en todos los materiales."""
    trees = [m.node_tree for m in bpy.data.materials if m.node_tree]
    if bpy.context.scene.world:
        trees.append(bpy.context.scene.world.node_tree)
    for nt in trees:
        for n in nt.nodes:
            if n.bl_idname == "ShaderNodeTexSky":
                n.sun_elevation = math.radians(elev_deg)
                n.sun_rotation = math.radians(az_model_deg)
    sun = bpy.data.objects.get("Sol")
    if sun:
        sun.rotation_euler = (math.radians(90 - elev_deg), 0.0, math.radians(180 - az_model_deg))
