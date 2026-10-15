"""Primitivas geometricas para arquitectura (bpy, sin operadores de UI).

Todo se construye con datos (from_pydata) para que sea rapido y reproducible.
Convencion de fachada local: x a lo largo de la fachada, z arriba, fachada en y=0,
el edificio crece hacia +y (el exterior/plaza queda en -y).
"""
import math
import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- colecciones

def collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def empty(name, coll, location=(0, 0, 0), rot_z_deg=0.0, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 3
    obj.location = location
    obj.rotation_euler = (0, 0, math.radians(rot_z_deg))
    if parent:
        obj.parent = parent
    coll.objects.link(obj)
    return obj


# Rotacion del marco local para que la fachada (normal local -Y) mire hacia...
FACING_ROT = {"S": 0.0, "N": 180.0, "E": 90.0, "W": -90.0}
# Nota: "mira al norte" = la fachada esta en el lado sur de la plaza.


def facade_root(name, coll, origin_xy, facing, z=0.0):
    """Empty padre de un edificio. `facing` = hacia donde mira la fachada (N,S,E,W).

    origin_xy es el extremo izquierdo de la fachada visto desde la plaza.
    """
    return empty(name, coll, (origin_xy[0], origin_xy[1], z), FACING_ROT[facing])


# ---------------------------------------------------------------- MeshBuilder

class MeshBuilder:
    """Acumula piezas (cajas, tornos, prismas, barridos) en una sola malla."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mat = []
        self.smooth = []

    # -- interno
    def _add(self, verts, faces, mat, smooth, matrix):
        base = len(self.verts)
        if matrix is not None:
            verts = [tuple(matrix @ Vector(v)) for v in verts]
        self.verts.extend(verts)
        for f, s in zip(faces, smooth if isinstance(smooth, list) else [smooth] * len(faces)):
            self.faces.append(tuple(base + i for i in f))
            self.mat.append(mat)
            self.smooth.append(s)

    # -- primitivas
    def box(self, x0, y0, z0, x1, y1, z1, mat=0, matrix=None):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        z0, z1 = min(z0, z1), max(z0, z1)
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self._add(v, f, mat, False, matrix)

    def box_c(self, cx, cy, cz, sx, sy, sz, mat=0, matrix=None):
        """Caja centrada en (cx,cy) con base en cz."""
        self.box(cx - sx / 2, cy - sy / 2, cz, cx + sx / 2, cy + sy / 2, cz + sz, mat, matrix)

    def lathe(self, profile, segments=24, center=(0, 0, 0), mat=0, matrix=None,
              smooth=True, scale_xy=(1.0, 1.0), cap_bottom=True, cap_top=True, arc=None):
        """Solido de revolucion. profile = [(r, z), ...] de abajo hacia arriba.

        arc=(a0, a1) en grados genera solo un sector abierto (p. ej. una capa).
        """
        cx, cy, cz = center
        verts, faces, sm = [], [], []
        rings = []
        if arc is not None:
            cap_bottom = cap_top = False
        nring = segments + 1 if arc is not None else segments
        for r, z in profile:
            if r <= 1e-6:
                rings.append([len(verts)])
                verts.append((cx, cy, cz + z))
            else:
                ring = []
                for j in range(nring):
                    if arc is not None:
                        a = math.radians(arc[0] + (arc[1] - arc[0]) * j / segments)
                    else:
                        a = 2 * math.pi * j / segments
                    ring.append(len(verts))
                    verts.append((cx + r * math.cos(a) * scale_xy[0],
                                  cy + r * math.sin(a) * scale_xy[1], cz + z))
                rings.append(ring)
        for i in range(len(rings) - 1):
            a, b = rings[i], rings[i + 1]
            if len(a) == 1 and len(b) == 1:
                continue
            for j in range(segments):
                jn = (j + 1) % segments if arc is None else j + 1
                if len(a) == 1 or len(b) == 1:
                    if arc is not None:
                        continue
                if len(a) == 1:
                    faces.append((a[0], b[jn], b[j])[::-1])
                elif len(b) == 1:
                    faces.append((a[j], a[jn], b[0]))
                else:
                    faces.append((a[j], a[jn], b[jn], b[j]))
                sm.append(smooth)
        if cap_bottom and len(rings[0]) > 1:
            faces.append(tuple(reversed(rings[0]))); sm.append(False)
        if cap_top and len(rings[-1]) > 1:
            faces.append(tuple(rings[-1])); sm.append(False)
        self._add(verts, faces, mat, sm, matrix)

    def prism_xz(self, outline, y0, y1, mat=0, matrix=None):
        """Prisma: contorno [(x,z),...] (antihorario visto desde -y) extruido de y0 a y1."""
        n = len(outline)
        if _signed_area(outline) < 0:
            outline = list(reversed(outline))
        v = [(x, y0, z) for x, z in outline] + [(x, y1, z) for x, z in outline]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, i + n, j + n, j))
        self._add(v, f, mat, False, matrix)

    def sweep_x(self, profile_yz, x0, x1, mat=0, matrix=None, smooth=False):
        """Barrido de un perfil cerrado [(y,z),...] a lo largo de x (cornisas, impostas)."""
        n = len(profile_yz)
        # orientar: antihorario en el plano (y,z) visto desde +x
        if _signed_area(profile_yz) < 0:
            profile_yz = list(reversed(profile_yz))
        v = [(x0, y, z) for y, z in profile_yz] + [(x1, y, z) for y, z in profile_yz]
        f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, j + n, i + n))
        self._add(v, f, mat, [False, False] + [smooth] * n, matrix)

    def tri_prism_pediment(self, x0, x1, z0, height, y0, y1, mat=0, matrix=None):
        """Frontón triangular macizo."""
        xm = (x0 + x1) / 2
        self.prism_xz([(x0, z0), (x1, z0), (xm, z0 + height)], y0, y1, mat, matrix)

    def pyramid(self, cx, cy, z0, sx, sy, h, mat=0, matrix=None):
        v = [(cx - sx / 2, cy - sy / 2, z0), (cx + sx / 2, cy - sy / 2, z0),
             (cx + sx / 2, cy + sy / 2, z0), (cx - sx / 2, cy + sy / 2, z0), (cx, cy, z0 + h)]
        f = [(0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
        self._add(v, f, mat, False, matrix)

    def hip_roof(self, x0, y0, x1, y1, z0, h, inset, mat=0, matrix=None):
        """Cubierta a cuatro aguas (o mansarda si inset es pequeno y se combina)."""
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0 + inset, y0 + inset, z0 + h), (x1 - inset, y0 + inset, z0 + h),
             (x1 - inset, y1 - inset, z0 + h), (x0 + inset, y1 - inset, z0 + h)]
        f = [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
        self._add(v, f, mat, False, matrix)

    def gable_roof_x(self, x0, x1, y0, y1, z0, h, mat=0, matrix=None):
        """Tejado a dos aguas con cumbrera paralela a x."""
        ym = (y0 + y1) / 2
        prof = [(y0, z0), (y1, z0), (ym, z0 + h)]
        self.sweep_x(prof, x0, x1, mat, matrix)

    def plane(self, x0, y0, x1, y1, z, mat=0, matrix=None):
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        self._add(v, [(0, 1, 2, 3)], mat, False, matrix)

    def extend(self, other, matrix=None, mat_offset=0):
        base = len(self.verts)
        vs = other.verts if matrix is None else [tuple(matrix @ Vector(v)) for v in other.verts]
        self.verts.extend(vs)
        self.faces.extend(tuple(base + i for i in f) for f in other.faces)
        self.mat.extend(m + mat_offset for m in other.mat)
        self.smooth.extend(other.smooth)

    # -- salida
    def to_object(self, name, coll, materials=(), parent=None, recalc=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        me.polygons.foreach_set("material_index", self.mat)
        me.polygons.foreach_set("use_smooth", self.smooth)
        for m in materials:
            me.materials.append(m)
        me.update()
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        if parent:
            obj.parent = parent
        return obj


def _signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


# ---------------------------------------------------------------- contornos 2D

def rect(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def arch(x0, x1, z0, z_spring, segs=16, rise=None):
    """Vano rectangular rematado en arco (medio punto por defecto, o rebajado con `rise`)."""
    w = x1 - x0
    xm = (x0 + x1) / 2
    pts = [(x0, z0), (x1, z0), (x1, z_spring)]
    if rise is None or rise >= w / 2 - 1e-6:
        r = w / 2
        for i in range(1, segs):
            a = math.pi * i / segs
            pts.append((xm + r * math.cos(a), z_spring + r * math.sin(a)))
    else:  # arco rebajado: centro bajo la linea de arranque
        half = w / 2
        r = (half ** 2 + rise ** 2) / (2 * rise)
        zc = z_spring + rise - r
        a0 = math.asin(half / r)
        for i in range(1, segs):
            phi = a0 - 2 * a0 * i / segs
            pts.append((xm + r * math.sin(phi), zc + r * math.cos(phi)))
    pts.append((x0, z_spring))
    return pts


# ---------------------------------------------------------------- objetos

def bevel(obj, width=0.02, segments=2, angle_deg=40):
    m = obj.modifiers.new("Bisel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle_deg)
    m.harden_normals = False
    return m


def boolean_diff(obj, cutter):
    m = obj.modifiers.new("Vanos", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "MANIFOLD"
    m.object = cutter
    cutter.display_type = "WIRE"
    cutter.hide_render = True
    cutter.visible_camera = False
    cutter.visible_shadow = False
    cutter.hide_set(True)
    return m


def linked_copy(src, name, coll, location=(0, 0, 0), rot_z_deg=0.0, parent=None, scale=(1, 1, 1)):
    obj = bpy.data.objects.new(name, src.data)
    obj.location = location
    obj.rotation_euler = (0, 0, math.radians(rot_z_deg))
    obj.scale = scale
    if parent:
        obj.parent = parent
    coll.objects.link(obj)
    return obj


def mat_t(x=0.0, y=0.0, z=0.0, rot_z_deg=0.0, scale=1.0):
    return (Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot_z_deg), 4, "Z")
            @ Matrix.Scale(scale, 4))


# ---------------------------------------------------------------- perfiles clasicos
# Perfiles (y, z): y negativo = vuela hacia la plaza. z relativo a la base de la moldura.

def cornice_profile(h=1.2, proj=0.9):
    """Cornisa clasica: arquitrabe-friso simplificado + corona + cimacio. Cerrada hacia +y."""
    k = h
    p = proj
    return [
        (0.30, 0.00), (0.00, 0.00), (0.00, 0.10 * k), (-0.10 * p, 0.14 * k),
        (-0.12 * p, 0.30 * k), (-0.35 * p, 0.38 * k), (-0.40 * p, 0.45 * k),
        (-0.80 * p, 0.55 * k), (-0.82 * p, 0.70 * k), (-0.86 * p, 0.74 * k),
        (-0.95 * p, 0.84 * k), (-1.00 * p, 0.95 * k), (-1.00 * p, 1.00 * k),
        (0.30, 1.00 * k),
    ]


def string_course_profile(h=0.35, proj=0.18):
    return [(0.2, 0.0), (0.0, 0.0), (-proj * 0.6, 0.15 * h), (-proj, 0.45 * h),
            (-proj, 0.8 * h), (-proj * 0.5, h), (0.2, h)]


def plinth_profile(h=1.0, proj=0.15):
    return [(0.2, 0.0), (-proj, 0.0), (-proj, h * 0.8), (-proj * 0.4, h), (0.2, h)]


# ---------------------------------------------------------------- piezas clasicas

def column_profile(h, r, order="ionic", base=True):
    """Perfil (r,z) de columna clasica completa (basa + fuste con entasis + capitel).

    Devuelve tambien la altura del capitel para anadir abaco/volutas aparte.
    """
    prof = []
    if base:
        hb = 0.5 * r  # basa ática simplificada
        prof += [(0, 0), (1.45 * r, 0), (1.45 * r, 0.10 * r), (1.35 * r, 0.18 * r),
                 (1.30 * r, 0.24 * r), (1.15 * r, 0.30 * r), (1.22 * r, 0.40 * r),
                 (1.08 * r, 0.48 * r), (1.0 * r, hb)]
    else:
        hb = 0.0
        prof += [(0, 0), (r, 0)]
    cap_h = {"doric": 0.9 * r, "tuscan": 0.9 * r, "ionic": 0.75 * r, "corinthian": 2.2 * r}[order]
    shaft_h = h - hb - cap_h
    n = 10
    for i in range(1, n + 1):  # entasis: el ultimo 2/3 se adelgaza hasta 0.83 r
        t = i / n
        rr = r if t < 0.33 else r * (1 - 0.17 * ((t - 0.33) / 0.67) ** 1.5)
        prof.append((rr, hb + shaft_h * t))
    top = hb + shaft_h
    rt = r * 0.83
    if order in ("doric", "tuscan"):
        prof += [(rt * 1.06, top + 0.06 * r), (rt * 1.06, top + 0.12 * r), (rt, top + 0.16 * r),
                 (rt * 1.25, top + 0.45 * r), (0, top + 0.45 * r)]
    elif order == "ionic":
        prof += [(rt * 1.08, top + 0.05 * r), (rt * 1.08, top + 0.12 * r),
                 (rt * 1.18, top + 0.35 * r), (0, top + 0.35 * r)]
    else:  # corintio: campana
        prof += [(rt * 1.05, top + 0.06 * r), (rt * 1.0, top + 0.2 * r), (rt * 1.15, top + 1.2 * r),
                 (rt * 1.35, top + 1.7 * r), (0, top + 1.7 * r)]
    return prof, top, cap_h


def add_column(mb, x, y, z, h, r, order="ionic", mat=0, segments=20, base=True, plinth=True,
               matrix=None):
    """Columna completa con plinto, basa, fuste, capitel y abaco (y volutas si es jonica)."""
    zp = z
    if plinth:
        ph = 0.35 * r
        mb.box_c(x, y, z, 3.0 * r, 3.0 * r, ph, mat, matrix)
        zp = z + ph
    hh = h - (zp - z)
    prof, top, cap_h = column_profile(hh, r, order, base)
    mb.lathe(prof, segments, (x, y, zp), mat, matrix)
    ab = 0.18 * r if order != "corinthian" else 0.25 * r
    zab = zp + hh - ab
    if order == "ionic":
        # volutas: dos cilindros horizontales a los lados + abaco delgado
        vr = 0.30 * r
        for side in (-1, 1):
            mb.lathe([(0, 0), (vr, 0), (vr, 0.45 * r), (0, 0.45 * r)], 12,
                     (0, 0, 0), mat, (matrix or Matrix()) @ Matrix.Translation(
                         (x + side * 1.0 * r - side * 0.0, y + 0.22 * r, zab - vr * 0.9))
                     @ Matrix.Rotation(math.radians(90), 4, "X"))
        mb.box_c(x, y, zab - 0.05 * r, 2.5 * r, 2.0 * r, 0.12 * r, mat, matrix)
        mb.box_c(x, y, zab, 2.3 * r, 2.3 * r, ab, mat, matrix)
    else:
        mb.box_c(x, y, zab, 2.5 * r if order != "corinthian" else 2.7 * r,
                 2.5 * r if order != "corinthian" else 2.7 * r, ab, mat, matrix)


def baluster_profile(h=0.75, r=0.09):
    return [(0, 0), (r * 1.25, 0), (r * 1.25, 0.08 * h), (r * 0.9, 0.12 * h), (r * 1.15, 0.28 * h),
            (r * 1.25, 0.42 * h), (r * 0.8, 0.62 * h), (r * 0.55, 0.78 * h), (r * 0.9, 0.84 * h),
            (r * 1.2, 0.88 * h), (r * 1.2, h), (0, h)]


def add_balustrade(mb, x0, x1, y, z, h=1.0, spacing=0.30, post_every=3.0, mat=0, depth=0.35,
                   matrix=None):
    """Balaustrada recta a lo largo de x (base, balaustres, pilastrillas y pasamanos)."""
    bh, rh = 0.15 * h, 0.15 * h
    mb.box(x0, y - depth / 2, z, x1, y + depth / 2, z + bh, mat, matrix)
    mb.box(x0 - 0.03, y - depth / 2 - 0.04, z + h - rh, x1 + 0.03, y + depth / 2 + 0.04, z + h, mat,
           matrix)
    L = x1 - x0
    nposts = max(1, int(round(L / post_every)))
    posts = [x0 + L * i / nposts for i in range(nposts + 1)]
    pw = 0.35
    for px in posts:
        mb.box(px - pw / 2, y - depth / 2 - 0.02, z, px + pw / 2, y + depth / 2 + 0.02, z + h, mat,
               matrix)
    prof = baluster_profile(h - bh - rh, depth * 0.33)
    for a, b in zip(posts[:-1], posts[1:]):
        span = (b - a) - pw
        nb = max(1, int(span / spacing))
        for i in range(nb):
            bx = a + pw / 2 + span * (i + 0.5) / nb
            mb.lathe(prof, 8, (bx, y, z + bh), mat, matrix)


def window_unit(mb_frame, mb_glass, x0, z0, w, h, y, arch_top=False, mullions=True,
                frame_w=0.08, frame_d=0.08, transom=None, matrix=None):
    """Carpinteria + vidrio para un vano, colocada a profundidad y (dentro del muro)."""
    xm = x0 + w / 2
    if arch_top:
        outline = arch(x0, x0 + w, z0, z0 + h - w / 2, 12)
    else:
        outline = rect(x0, z0, x0 + w, z0 + h)
    mb_glass.prism_xz(outline, y + 0.02, y + 0.04, 0, matrix)
    fw = frame_w
    # marco perimetral (aproximado como 4 barras; en arco se usa la caja envolvente inferior)
    top = z0 + h if not arch_top else z0 + h - w / 2
    mb_frame.box(x0, y, z0, x0 + w, y + frame_d, z0 + fw, 0, matrix)
    mb_frame.box(x0, y, z0, x0 + fw, y + frame_d, top, 0, matrix)
    mb_frame.box(x0 + w - fw, y, z0, x0 + w, y + frame_d, top, 0, matrix)
    if not arch_top:
        mb_frame.box(x0, y, z0 + h - fw, x0 + w, y + frame_d, z0 + h, 0, matrix)
    if mullions:
        mb_frame.box(xm - fw / 2, y - 0.01, z0, xm + fw / 2, y + frame_d - 0.01, top, 0, matrix)
        zt = transom if transom is not None else z0 + (top - z0) * 0.72
        mb_frame.box(x0, y - 0.01, zt - fw / 2, x0 + w, y + frame_d - 0.01, zt + fw / 2, 0, matrix)
        zz = z0 + (zt - z0) * 0.5  # palillo intermedio (cuarterones)
        mb_frame.box(x0, y - 0.005, zz - 0.02, x0 + w, y + frame_d - 0.02, zz + 0.02, 0, matrix)


# ---------------------------------------------------------------- UV de caja (Geometry Nodes)

def box_uv_group():
    """Grupo de nodos que guarda 'UVMap' (en metros) proyectando por la normal dominante.

    Caras verticales: (x,z) o (y,z); horizontales: (x,y). Funciona con modificadores vivos
    (booleanas) porque se evalua al final de la pila, y se exporta tal cual a glTF.
    """
    ng = bpy.data.node_groups.get("UV caja (metros)")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("UV caja (metros)", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, Lk = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    pos, nor = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeInputNormal")
    sp, sn = N.new("ShaderNodeSeparateXYZ"), N.new("ShaderNodeSeparateXYZ")
    Lk.new(pos.outputs[0], sp.inputs[0])
    Lk.new(nor.outputs[0], sn.inputs[0])

    def m(op, a, b=None):
        n = N.new("ShaderNodeMath")
        n.operation = op
        Lk.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, (int, float)):
                n.inputs[1].default_value = b
            else:
                Lk.new(b, n.inputs[1])
        return n.outputs[0]

    def comb(x, y):
        n = N.new("ShaderNodeCombineXYZ")
        Lk.new(x, n.inputs[0])
        Lk.new(y, n.inputs[1])
        return n.outputs[0]

    def mixv(f, a, b):
        n = N.new("ShaderNodeMix")
        n.data_type = "VECTOR"
        Lk.new(f, n.inputs[0])
        Lk.new(a, n.inputs[4])
        Lk.new(b, n.inputs[5])
        return n.outputs[1]

    ax, ay, az = m("ABSOLUTE", sn.outputs[0]), m("ABSOLUTE", sn.outputs[1]), m("ABSOLUTE", sn.outputs[2])
    use_yz = m("GREATER_THAN", ax, ay)
    v = mixv(use_yz, comb(sp.outputs[0], sp.outputs[2]), comb(sp.outputs[1], sp.outputs[2]))
    top = m("GREATER_THAN", az, 0.7)
    v = mixv(top, v, comb(sp.outputs[0], sp.outputs[1]))
    st = N.new("GeometryNodeStoreNamedAttribute")
    st.data_type = "FLOAT2"
    st.domain = "CORNER"
    st.inputs["Name"].default_value = "UVMap"
    Lk.new(gi.outputs[0], st.inputs["Geometry"])
    Lk.new(v, st.inputs["Value"])
    Lk.new(st.outputs[0], go.inputs[0])
    return ng


def add_box_uv(obj):
    if obj.type != "MESH" or "UV caja" in obj.modifiers:
        return
    mod = obj.modifiers.new("UV caja", "NODES")
    mod.node_group = box_uv_group()
