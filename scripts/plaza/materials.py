"""Materiales procedurales (sin texturas externas) para Cycles.

Todas las texturas usan coordenadas Object en metros (el objeto no se escala),
de modo que el tamano de bloques/losas es real y no depende de UVs.
"""
import bpy

_CACHE = {}

# Bruma atmosferica (perspectiva aerea). build.py la configura antes de crear materiales:
# HAZE = {"dist": 7000, "elev": deg, "az": deg, "altitude": m, "air":..., "aerosol":...}
HAZE = None


# ---------------------------------------------------------------- utilidades de nodos

class NT:
    def __init__(self, mat_or_world, clear=True):
        self.nt = mat_or_world.node_tree
        if clear:
            self.nt.nodes.clear()
        self.x = 0

    def n(self, kind, inputs=None, **props):
        node = self.nt.nodes.new(kind)
        node.location = (self.x, 0)
        self.x += 200
        for k, v in props.items():
            setattr(node, k, v)
        for k, v in (inputs or {}).items():
            node.inputs[k].default_value = v
        return node

    def l(self, a, b):
        self.nt.links.new(a, b)
        return b

    # -- atajos que devuelven sockets
    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._in(m.inputs[0], a)
        if b is not None:
            self._in(m.inputs[1], b)
        return m.outputs[0]

    def vmath(self, op, a, b=None):
        m = self.n("ShaderNodeVectorMath", operation=op)
        self._in(m.inputs[0], a)
        if b is not None:
            self._in(m.inputs[1], b)
        return m.outputs[0] if op not in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else m.outputs[1]

    def mix(self, fac, a, b, blend="MIX"):
        m = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self._in(m.inputs[0], fac)
        self._in(m.inputs[6], a)
        self._in(m.inputs[7], b)
        return m.outputs[2]

    def mixf(self, fac, a, b):
        m = self.n("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self._in(m.inputs[0], fac)
        self._in(m.inputs[2], a)
        self._in(m.inputs[3], b)
        return m.outputs[0]

    def mixv(self, fac, a, b):
        m = self.n("ShaderNodeMix", data_type="VECTOR")
        self._in(m.inputs[0], fac)
        self._in(m.inputs[4], a)
        self._in(m.inputs[5], b)
        return m.outputs[1]

    def maprange(self, v, a0, a1, b0=0.0, b1=1.0, smooth=False):
        m = self.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP" if smooth else "LINEAR",
                   clamp=True)
        self._in(m.inputs["Value"], v)
        m.inputs["From Min"].default_value = a0
        m.inputs["From Max"].default_value = a1
        m.inputs["To Min"].default_value = b0
        m.inputs["To Max"].default_value = b1
        return m.outputs["Result"]

    def noise(self, vec, scale, detail=6.0, rough=0.55, distortion=0.0, dims="3D"):
        m = self.n("ShaderNodeTexNoise", noise_dimensions=dims,
                   inputs={"Scale": scale, "Detail": detail, "Roughness": rough,
                           "Distortion": distortion})
        self._in(m.inputs["Vector"], vec)
        return m

    def voronoi(self, vec, scale, feature="F1", rand=1.0):
        m = self.n("ShaderNodeTexVoronoi", feature=feature, inputs={"Scale": scale,
                                                                    "Randomness": rand})
        self._in(m.inputs["Vector"], vec)
        return m

    def combine(self, x, y, z):
        m = self.n("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._in(m.inputs[i], v)
        return m.outputs[0]

    def separate(self, vec):
        m = self.n("ShaderNodeSeparateXYZ")
        self._in(m.inputs[0], vec)
        return m.outputs

    def ramp(self, fac, stops):
        m = self.n("ShaderNodeValToRGB")
        self._in(m.inputs[0], fac)
        el = m.color_ramp.elements
        while len(el) > len(stops):
            el.remove(el[-1])
        while len(el) < len(stops):
            el.new(0.5)
        for e, (pos, col) in zip(el, stops):
            e.position = pos
            e.color = col if len(col) == 4 else (*col, 1.0)
        return m.outputs[0]

    def bump(self, height, strength=1.0, distance=0.02, normal=None):
        m = self.n("ShaderNodeBump", inputs={"Strength": strength, "Distance": distance})
        self._in(m.inputs["Height"], height)
        if normal is not None:
            self._in(m.inputs["Normal"], normal)
        return m.outputs[0]

    def _in(self, sock, v):
        if hasattr(v, "is_output") or hasattr(v, "links"):
            self.l(v, sock)
        else:
            sock.default_value = v


def _new_mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m, False
    m = bpy.data.materials.new(name)
    if m.node_tree is None:  # compatibilidad con versiones anteriores a 5.x
        m.use_nodes = True
    return m, True


def _principled(t, base, rough, normal=None, metallic=0.0, spec=0.5, coat=0.0):
    p = t.n("ShaderNodeBsdfPrincipled")
    t._in(p.inputs["Base Color"], base)
    t._in(p.inputs["Roughness"], rough)
    t._in(p.inputs["Metallic"], metallic)
    p.inputs["Specular IOR Level"].default_value = spec
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    if normal is not None:
        t.l(normal, p.inputs["Normal"])
    _output(t, p.outputs[0])
    return p


def _sky_node(t, elev, az, cfg):
    import math
    sky = t.n("ShaderNodeTexSky", sky_type="MULTIPLE_SCATTERING")
    sky.sun_disc = False
    sky.sun_elevation = math.radians(elev)
    sky.sun_rotation = math.radians(az)
    sky.altitude = cfg.get("altitude", 2600.0)
    sky.air_density = cfg.get("air", 1.0)
    sky.aerosol_density = cfg.get("aerosol", 1.0)
    return sky


def _output(t, shader, haze=True):
    """Conecta el shader a la salida, mezclando bruma segun la distancia a la camara."""
    out = t.n("ShaderNodeOutputMaterial")
    if HAZE is None or not haze:
        t.l(shader, out.inputs["Surface"])
        return
    geo = t.n("ShaderNodeNewGeometry")
    view = t.vmath("SCALE", geo.outputs["Incoming"], None)
    t.nt.nodes[-1].inputs[3].default_value = -1.0   # escala -1: direccion camara -> punto
    flat = t.vmath("MULTIPLY", view, (1.0, 1.0, 0.0))
    d = t.vmath("NORMALIZE", t.vmath("ADD", flat, (0.0, 0.0, 0.06)))
    sky = _sky_node(t, HAZE["elev"], HAZE["az"], HAZE)
    t.l(d, sky.inputs["Vector"])
    em = t.n("ShaderNodeEmission", inputs={"Strength": HAZE.get("strength", 1.0)})
    t.l(sky.outputs[0], em.inputs["Color"])
    cam = t.n("ShaderNodeCameraData")
    k = t.math("MULTIPLY", cam.outputs["View Distance"], -1.0 / HAZE["dist"])
    f = t.math("SUBTRACT", 1.0, t.math("EXPONENT", k))
    mx = t.n("ShaderNodeMixShader")
    t.l(f, mx.inputs[0])
    t.l(shader, mx.inputs[1])
    t.l(em.outputs[0], mx.inputs[2])
    t.l(mx.outputs[0], out.inputs["Surface"])


def _rgb(c):
    return (*c, 1.0) if len(c) == 3 else c


def _scale(rgb, k):
    return tuple(min(1.0, v * k) for v in rgb[:3]) + (1.0,)


def _proj_coords(t, top_xy=True):
    """Coordenadas planas segun la normal: fachadas (x,z)/(y,z), techos/suelos (x,y)."""
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    nrm = tc.outputs["Normal"]
    p = t.separate(obj)
    nn = t.separate(nrm)
    ax = t.math("ABSOLUTE", nn[0])
    ay = t.math("ABSOLUTE", nn[1])
    az = t.math("ABSOLUTE", nn[2])
    use_yz = t.math("GREATER_THAN", ax, ay)
    v_xz = t.combine(p[0], p[2], 0.0)
    v_yz = t.combine(p[1], p[2], 0.0)
    v = t.mixv(use_yz, v_xz, v_yz)
    if top_xy:
        is_top = t.math("GREATER_THAN", az, 0.7)
        v = t.mixv(is_top, v, t.combine(p[0], p[1], 0.0))
    return v, obj


def _grime(t, color, strength=1.0, height=1.6):
    """Suciedad cerca del suelo + chorreaduras verticales + variacion de baja frecuencia."""
    geo = t.n("ShaderNodeNewGeometry")
    pos = geo.outputs["Position"]
    z = t.separate(pos)[2]
    ground = t.maprange(z, 0.0, height, 1.0, 0.0, smooth=True)
    streak_vec = t.vmath("MULTIPLY", pos, (2.5, 2.5, 0.12))
    streaks = t.noise(streak_vec, 3.0, 4.0, 0.6).outputs["Fac"]
    streaks = t.maprange(streaks, 0.5, 0.75, 0.0, 1.0)
    blotch = t.noise(pos, 0.35, 3.0, 0.5).outputs["Fac"]
    blotch = t.maprange(blotch, 0.35, 0.7, 0.0, 1.0)
    fac = t.math("ADD", t.math("MULTIPLY", ground, 0.55 * strength),
                 t.math("MULTIPLY", streaks, 0.22 * strength))
    fac = t.math("ADD", fac, t.math("MULTIPLY", blotch, 0.18 * strength), clamp=True)
    dirt = (0.32, 0.29, 0.25, 1.0)
    return t.mix(fac, color, t.mix(1.0, color, dirt, "MULTIPLY"))


# ---------------------------------------------------------------- materiales

def ashlar(name, base, var=0.12, block=(0.90, 0.45), mortar=0.008, mortar_col=None,
           grime=1.0, rough=0.78, offset=0.5):
    """Silleria de piedra (bloques) con variacion por bloque, juntas y suciedad."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    v, obj = _proj_coords(t)
    br = t.n("ShaderNodeTexBrick", offset=offset, offset_frequency=2, squash=1.0,
             squash_frequency=2,
             inputs={"Color1": _scale(base, 1 + var), "Color2": _scale(base, 1 - var),
                     "Mortar": _rgb(mortar_col or _scale(base, 0.82)), "Scale": 1.0,
                     "Mortar Size": mortar, "Mortar Smooth": 0.3, "Bias": 0.0,
                     "Brick Width": block[0], "Row Height": block[1]})
    t.l(v, br.inputs["Vector"])
    col = br.outputs["Color"]
    big = t.noise(obj, 0.6, 4, 0.5).outputs["Fac"]
    col = t.mix(t.maprange(big, 0.3, 0.7, 0.0, 0.35), col, _scale(base, 0.85), "MIX")
    grain = t.noise(obj, 35.0, 8, 0.7).outputs["Fac"]
    col = t.mix(0.25, col, t.mix(grain, _scale(base, 0.8), _scale(base, 1.15)), "OVERLAY")
    col = _grime(t, col, grime)
    joint = t.math("SUBTRACT", 1.0, br.outputs["Fac"])
    h = t.math("ADD", t.math("MULTIPLY", joint, 0.6), t.math("MULTIPLY", grain, 0.25))
    pit = t.voronoi(obj, 18.0).outputs["Distance"]
    h = t.math("ADD", h, t.math("MULTIPLY", pit, 0.12))
    nrm = t.bump(h, 0.6, 0.015)
    r = t.maprange(grain, 0.2, 0.8, rough - 0.08, rough + 0.1)
    _principled(t, col, r, nrm)
    return m


def smooth_stone(name, base, grime=1.0, rough=0.7, grain_scale=30.0):
    """Piedra labrada lisa (columnas, cornisas, molduras)."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    big = t.noise(obj, 0.8, 4, 0.5).outputs["Fac"]
    col = t.mix(t.maprange(big, 0.3, 0.7, 0, 1), _scale(base, 0.9), _scale(base, 1.08))
    grain = t.noise(obj, grain_scale, 8, 0.7).outputs["Fac"]
    col = t.mix(0.2, col, t.mix(grain, _scale(base, 0.8), _scale(base, 1.15)), "OVERLAY")
    col = _grime(t, col, grime)
    nrm = t.bump(grain, 0.25, 0.01)
    _principled(t, col, t.maprange(grain, 0.2, 0.8, rough - 0.1, rough + 0.1), nrm)
    return m


def stucco(name, base, grime=1.0, rough=0.85):
    """Paramento revocado y pintado."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    big = t.noise(obj, 0.5, 5, 0.55).outputs["Fac"]
    col = t.mix(t.maprange(big, 0.3, 0.7, 0, 1), _scale(base, 0.93), _scale(base, 1.04))
    fine = t.noise(obj, 60.0, 6, 0.65).outputs["Fac"]
    col = _grime(t, col, grime)
    nrm = t.bump(fine, 0.15, 0.01)
    _principled(t, col, rough, nrm, spec=0.35)
    return m


def plaza_paving(name, slab=(1.0, 1.0), base=(0.42, 0.41, 0.39), var=0.18,
                 band_every=0.0, band_w=0.6, band_col=(0.62, 0.60, 0.56), wet=0.25, offset=0.0,
                 joint=0.006):
    """Losas de piedra con variacion por losa, juntas, desgaste y zonas humedas."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    p = t.separate(obj)
    v = t.combine(p[0], p[1], 0.0)
    br = t.n("ShaderNodeTexBrick", offset=offset, offset_frequency=2, squash=1.0,
             inputs={"Color1": _scale(base, 1 + var), "Color2": _scale(base, 1 - var),
                     "Mortar": _rgb(_scale(base, 0.45)), "Scale": 1.0, "Mortar Size": joint,
                     "Mortar Smooth": 0.4, "Bias": 0.0, "Brick Width": slab[0],
                     "Row Height": slab[1]})
    t.l(v, br.inputs["Vector"])
    col = br.outputs["Color"]
    # tono por losa extra (segundo brick con otro tamano de celda para romper repeticion)
    br2 = t.n("ShaderNodeTexBrick", offset=0.37, offset_frequency=3,
              inputs={"Color1": (1.06, 1.05, 1.03, 1), "Color2": (0.9, 0.9, 0.9, 1),
                      "Mortar": (1, 1, 1, 1), "Scale": 1.0, "Mortar Size": 0.0,
                      "Brick Width": slab[0] * 1.0, "Row Height": slab[1] * 1.0, "Bias": 0.0})
    t.l(t.combine(p[0], p[1], 0.0), br2.inputs["Vector"])
    col = t.mix(var * 2.0, col, t.mix(1.0, col, br2.outputs["Color"], "MULTIPLY"))
    if band_every > 0:
        fx = t.math("FLOORED_MODULO", p[0], band_every)
        fy = t.math("FLOORED_MODULO", p[1], band_every)
        bx = t.math("LESS_THAN", fx, band_w)
        by = t.math("LESS_THAN", fy, band_w)
        band = t.math("MAXIMUM", bx, by)
        col = t.mix(band, col, _rgb(band_col))
    big = t.noise(obj, 0.08, 4, 0.55).outputs["Fac"]
    col = t.mix(t.maprange(big, 0.35, 0.7, 0, 0.3), col, _scale(base, 0.7))
    grain = t.noise(obj, 25.0, 8, 0.7).outputs["Fac"]
    col = t.mix(0.25, col, t.mix(grain, _scale(base, 0.75), _scale(base, 1.2)), "OVERLAY")
    # humedad: manchas grandes mas oscuras y brillantes
    wetn = t.noise(obj, 0.05, 3, 0.5, distortion=0.3).outputs["Fac"]
    wetm = t.maprange(wetn, 0.62 - 0.12 * wet, 0.70 - 0.12 * wet, 0.0, 1.0, smooth=True)
    wetm = t.math("MULTIPLY", wetm, wet * 3.0, clamp=True)
    col = t.mix(t.math("MULTIPLY", wetm, 0.5), col, _scale(base, 0.45))
    joint_m = t.math("SUBTRACT", 1.0, br.outputs["Fac"])
    h = t.math("ADD", t.math("MULTIPLY", joint_m, 0.5), t.math("MULTIPLY", grain, 0.2))
    nrm = t.bump(h, 0.5, 0.01)
    r = t.mixf(wetm, t.maprange(grain, 0.2, 0.8, 0.55, 0.85), 0.05)
    _principled(t, col, r, nrm)
    return m


def pavers(name, size=(0.20, 0.10), base=(0.38, 0.33, 0.29), var=0.2):
    """Adoquin (calles peatonales)."""
    return plaza_paving(name, slab=size, base=base, var=var, offset=0.5, wet=0.15, joint=0.012)


def asphalt(name):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    fine = t.noise(obj, 180.0, 4, 0.6).outputs["Fac"]
    vor = t.voronoi(obj, 120.0).outputs["Distance"]
    big = t.noise(obj, 0.15, 4, 0.55).outputs["Fac"]
    col = t.mix(fine, (0.045, 0.045, 0.047, 1), (0.10, 0.10, 0.10, 1))
    col = t.mix(t.maprange(big, 0.35, 0.65, 0, 0.6), col, (0.13, 0.13, 0.13, 1))
    nrm = t.bump(t.math("ADD", fine, vor), 0.35, 0.01)
    _principled(t, col, t.maprange(big, 0.3, 0.7, 0.75, 0.92), nrm)
    return m


def glass(name="Vidrio"):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    n = t.noise(tc.outputs["Object"], 0.4, 2, 0.5).outputs["Fac"]
    col = t.mix(n, (0.012, 0.016, 0.02, 1), (0.03, 0.035, 0.04, 1))
    p = _principled(t, col, 0.04, spec=0.5)
    p.inputs["IOR"].default_value = 1.52
    p.inputs["Coat Weight"].default_value = 0.0
    return m


def painted(name, rgb, rough=0.45):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    n = t.noise(tc.outputs["Object"], 8.0, 6, 0.6).outputs["Fac"]
    col = t.mix(n, _scale(rgb, 0.92), _scale(rgb, 1.05))
    col = _grime(t, col, 0.6)
    _principled(t, col, rough, t.bump(n, 0.1, 0.005))
    return m


def bronze(name="Bronce"):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    n = t.noise(obj, 3.0, 6, 0.6).outputs["Fac"]
    patina = t.maprange(n, 0.45, 0.65, 0, 1)
    geo = t.n("ShaderNodeNewGeometry")
    up = t.separate(geo.outputs["Normal"])[2]
    patina = t.math("ADD", patina, t.math("MULTIPLY", t.maprange(up, 0.3, 0.9, 0, 1), 0.5),
                    clamp=True)
    col = t.mix(patina, (0.30, 0.20, 0.10, 1), (0.16, 0.26, 0.21, 1))
    met = t.maprange(patina, 0, 1, 0.9, 0.35)
    r = t.maprange(patina, 0, 1, 0.38, 0.65)
    p = _principled(t, col, r, t.bump(n, 0.2, 0.01))
    t.l(met, p.inputs["Metallic"])
    return m


def iron(name="Hierro"):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    _principled(t, (0.025, 0.027, 0.028, 1), 0.45, metallic=0.7)
    return m


def slate(name="Pizarra"):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    v, obj = _proj_coords(t, top_xy=False)
    br = t.n("ShaderNodeTexBrick", offset=0.5, offset_frequency=2,
             inputs={"Color1": (0.11, 0.12, 0.14, 1), "Color2": (0.07, 0.08, 0.09, 1),
                     "Mortar": (0.03, 0.03, 0.035, 1), "Scale": 1.0, "Mortar Size": 0.006,
                     "Brick Width": 0.25, "Row Height": 0.16, "Bias": 0.0})
    t.l(v, br.inputs["Vector"])
    n = t.noise(obj, 20, 6, 0.6).outputs["Fac"]
    nrm = t.bump(t.math("SUBTRACT", 1.0, br.outputs["Fac"]), 0.5, 0.01)
    _principled(t, br.outputs["Color"], t.maprange(n, 0.2, 0.8, 0.35, 0.6), nrm)
    return m


def roof_tile(name="Teja"):
    """Teja de barro (casas coloniales del fondo)."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    p = t.separate(obj)
    # canales de teja: seno a lo largo de x (cumbrera paralela a x)
    wave = t.math("SINE", t.math("MULTIPLY", p[0], 6.283 / 0.25))
    rows = t.n("ShaderNodeTexBrick", offset=0.5,
               inputs={"Color1": (0.40, 0.17, 0.09, 1), "Color2": (0.30, 0.13, 0.08, 1),
                       "Mortar": (0.2, 0.1, 0.06, 1), "Scale": 1.0, "Mortar Size": 0.01,
                       "Brick Width": 0.25, "Row Height": 0.40, "Bias": 0.0})
    t.l(t.combine(p[0], t.math("ADD", p[1], p[2]), 0.0), rows.inputs["Vector"])
    n = t.noise(obj, 1.2, 5, 0.6).outputs["Fac"]
    col = t.mix(t.maprange(n, 0.3, 0.7, 0, 0.6), rows.outputs["Color"], (0.18, 0.12, 0.09, 1))
    h = t.math("ADD", t.math("MULTIPLY", wave, 0.5), t.math("SUBTRACT", 1, rows.outputs["Fac"]))
    _principled(t, col, 0.75, t.bump(h, 0.6, 0.02))
    return m


def terrain(name="Terreno", base_elev=2614.0, urban_max=2760.0, paramo=3150.0, near_r=700.0):
    """Terreno: calles cerca, barrios en laderas bajas, bosque, paramo y roca en pendientes."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    p = t.separate(obj)
    elev = t.math("ADD", p[2], base_elev)
    geo = t.n("ShaderNodeNewGeometry")
    nz = t.separate(geo.outputs["Normal"])[2]
    n_big = t.noise(obj, 0.004, 6, 0.6).outputs["Fac"]
    n_mid = t.noise(obj, 0.03, 6, 0.6).outputs["Fac"]
    # barrios (vistos de lejos): mosaico de tejados de barro, cubiertas claras y calles
    vor = t.voronoi(t.vmath("MULTIPLY", obj, (1.0, 1.0, 0.0)), 0.035)
    roofs = t.ramp(vor.outputs["Color"], [
        (0.0, (0.30, 0.13, 0.07)), (0.35, (0.36, 0.17, 0.09)), (0.55, (0.55, 0.53, 0.50)),
        (0.75, (0.25, 0.24, 0.23)), (0.9, (0.62, 0.60, 0.55)), (1.0, (0.12, 0.16, 0.08))])
    gaps = t.maprange(vor.outputs["Distance"], 0.35, 0.5, 0.0, 1.0)
    urban = t.mix(t.math("MULTIPLY", gaps, 0.5), roofs, (0.10, 0.10, 0.10, 1))
    urban = t.mix(0.55, urban, (0.27, 0.21, 0.17, 1))
    # bosque: copas agrupadas (voronoi) con verdes oscuros y eucaliptos azulados
    crowns = t.voronoi(obj, 0.12)
    forest = t.mix(crowns.outputs["Distance"], (0.028, 0.05, 0.02, 1), (0.008, 0.016, 0.007, 1))
    forest = t.mix(t.maprange(n_mid, 0.55, 0.7, 0, 0.7), forest, (0.05, 0.07, 0.055, 1))
    forest = t.mix(t.maprange(n_big, 0.3, 0.7, 0, 0.5), forest, (0.06, 0.075, 0.03, 1))
    paramo_c = t.mix(n_mid, (0.12, 0.12, 0.06, 1), (0.08, 0.09, 0.04, 1))
    rock = t.mix(n_mid, (0.22, 0.20, 0.17, 1), (0.14, 0.13, 0.11, 1))
    # mezcla por cota (con borde irregular)
    jitter = t.math("MULTIPLY", t.math("SUBTRACT", n_big, 0.5), 160.0)
    e = t.math("ADD", elev, jitter)
    f_forest = t.maprange(e, urban_max - 15, urban_max + 25, 0, 1)
    col = t.mix(f_forest, urban, forest)
    f_par = t.maprange(e, paramo - 40, paramo + 60, 0, 1)
    col = t.mix(f_par, col, paramo_c)
    f_rock = t.maprange(nz, 0.62, 0.45, 0, 0.8)
    col = t.mix(f_rock, col, rock)
    # cerca de la plaza (zona OSM) el suelo son calles de asfalto/adoquin
    r = t.vmath("LENGTH", t.combine(p[0], p[1], 0.0))
    near = t.maprange(r, near_r - 150, near_r + 50, 1.0, 0.0)
    street = t.mix(n_mid, (0.08, 0.08, 0.08, 1), (0.16, 0.15, 0.14, 1))
    col = t.mix(near, col, street)
    h = t.math("ADD", crowns.outputs["Distance"], t.math("MULTIPLY", n_mid, 2.0))
    nrm = t.bump(h, 0.8, 1.5)
    rough = t.mixf(near, 0.92, 0.8)
    _principled(t, col, rough, nrm, spec=0.25)
    return m


def city_facade(name, base, win=(2.6, 3.5), grime=1.2):
    """Fachada urbana con ventanas procedurales (para la ciudad de fondo)."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    v, obj = _proj_coords(t, top_xy=False)
    vv = t.separate(v)
    fu = t.math("FLOORED_MODULO", vv[0], win[0])
    geo = t.n("ShaderNodeNewGeometry")
    z = t.separate(geo.outputs["Position"])[2]
    fz = t.math("FLOORED_MODULO", vv[1], win[1])
    wu = t.math("MULTIPLY", t.math("GREATER_THAN", fu, win[0] * 0.3),
                t.math("LESS_THAN", fu, win[0] * 0.75))
    wz = t.math("MULTIPLY", t.math("GREATER_THAN", fz, win[1] * 0.3),
                t.math("LESS_THAN", fz, win[1] * 0.85))
    nrm_z = t.math("ABSOLUTE", t.separate(tc_normal(t))[2])
    vertical = t.math("LESS_THAN", nrm_z, 0.5)
    mask = t.math("MULTIPLY", t.math("MULTIPLY", wu, wz), vertical)
    big = t.noise(obj, 0.3, 4, 0.5).outputs["Fac"]
    col = t.mix(t.maprange(big, 0.3, 0.7, 0, 1), _scale(base, 0.92), _scale(base, 1.05))
    col = _grime(t, col, grime)
    col = t.mix(mask, col, (0.03, 0.035, 0.04, 1))
    r = t.mixf(mask, 0.85, 0.12)
    _principled(t, col, r, spec=0.4)
    return m


def tc_normal(t):
    tc = t.n("ShaderNodeTexCoord")
    return tc.outputs["Normal"]


def flag(name="Bandera", top=None):
    """Bandera de Colombia: amarillo (mitad superior), azul y rojo (cuartos), segun z local."""
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    tc = t.n("ShaderNodeTexCoord")
    p = t.separate(tc.outputs["Object"])
    geo = t.n("ShaderNodeObjectInfo")
    # la bandera ocupa z en [pole_h-h-0.3, pole_h-0.3]; se normaliza con el bbox generado
    gen = t.separate(tc.outputs["Generated"])
    zf = gen[2]
    col = t.mix(t.math("GREATER_THAN", zf, 0.5), (0.45, 0.012, 0.03, 1), (0.85, 0.62, 0.0, 1))
    blue = t.math("MULTIPLY", t.math("GREATER_THAN", zf, 0.25), t.math("LESS_THAN", zf, 0.5))
    col = t.mix(blue, col, (0.0, 0.03, 0.22, 1))
    red = t.math("LESS_THAN", zf, 0.25)
    col = t.mix(red, col, (0.45, 0.012, 0.03, 1))
    p_ = _principled(t, col, 0.7, spec=0.3)
    p_.inputs["Sheen Weight"].default_value = 0.3
    p_.inputs["Subsurface Weight"].default_value = 0.0
    return m


def flat(name, rgb, rough=0.8, metallic=0.0):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    _principled(t, _rgb(rgb), rough, metallic=metallic)
    return m


def massing(name="Massing", rgb=(0.7, 0.7, 0.7)):
    return flat(name, rgb, 0.9)


def lamp_glass(name="Farol vidrio"):
    m, new = _new_mat(name)
    if not new:
        return m
    t = NT(m)
    p = _principled(t, (0.9, 0.85, 0.7, 1), 0.25)
    p.inputs["Transmission Weight"].default_value = 0.6
    return m
