"""Generadores parametricos de los edificios de la Plaza de Bolivar.

Cada funcion recibe:
  ctx  -> Ctx con materiales y coleccion
  b    -> dict de config.BUILDINGS[...] (todas las medidas, en metros)
Construye en el marco local de fachada (ver geo.py) bajo un Empty padre.
Si ctx.massing es True solo genera los volumenes (cajas) del edificio.
"""
import math

import bpy

from . import geo
from .geo import MeshBuilder, rect, arch


class Ctx:
    def __init__(self, mats, coll_root, massing=False):
        self.m = mats
        self.root = coll_root
        self.massing = massing

    def coll(self, name):
        return geo.collection(name, self.root)


def _finish(mb, name, coll, mats, parent, bevel=0.0, cutter=None):
    if not mb.faces:
        return None
    obj = mb.to_object(name, coll, mats, parent)
    if bevel:
        geo.bevel(obj, bevel)
    if cutter is not None and cutter.faces:
        c = cutter.to_object(name + " (cortes)", coll, [], parent)
        geo.boolean_diff(obj, c)
    return obj


def _xs(x0, x1, n):
    """Centros de n vanos repartidos uniformemente entre x0 y x1."""
    step = (x1 - x0) / n
    return [x0 + step * (i + 0.5) for i in range(n)]


def _windows(cut, fr, gl, trim, xs, z0, w, h, depth=0.30, arch_top=False, sill=True,
             lintel=None, pediment=False, balcony=False, wall_y=0.0, trim_mat=0):
    """Vanos en un muro cuya cara esta en y=wall_y (exterior hacia -y)."""
    for x in xs:
        x0 = x - w / 2
        o = arch(x0, x0 + w, z0, z0 + h - w / 2, 12) if arch_top else rect(x0, z0, x0 + w, z0 + h)
        cut.prism_xz(o, wall_y - 1.0, wall_y + depth)
        geo.window_unit(fr, gl, x0, z0, w, h, wall_y + depth - 0.1, arch_top=arch_top)
        if sill:
            trim.box(x0 - 0.12, wall_y - 0.12, z0 - 0.14, x0 + w + 0.12, wall_y + depth * 0.5, z0,
                     trim_mat)
        # marco de piedra (jambas) ligeramente saliente
        if lintel is not None or pediment:
            trim.box(x0 - 0.18, wall_y - 0.06, z0, x0, wall_y + 0.02, z0 + h, trim_mat)
            trim.box(x0 + w, wall_y - 0.06, z0, x0 + w + 0.18, wall_y + 0.02, z0 + h, trim_mat)
        if lintel is not None:
            zt = z0 + h + (0.0 if not arch_top else 0.0)
            trim.sweep_x([(0.05, 0), (-0.08, 0), (-0.08, lintel * 0.6), (-0.22, lintel * 0.8),
                          (-0.22, lintel), (0.05, lintel)], x0 - 0.3, x0 + w + 0.3, trim_mat,
                         geo.mat_t(0, wall_y, zt))
        if pediment:
            zt = z0 + h + (lintel or 0.0)
            trim.tri_prism_pediment(x0 - 0.35, x0 + w + 0.35, zt, 0.45 + w * 0.12,
                                    wall_y - 0.25, wall_y + 0.05, trim_mat)
        if balcony:
            trim.box(x0 - 0.35, wall_y - 0.75, z0 - 0.25, x0 + w + 0.35, wall_y, z0 - 0.05, trim_mat)


def _railing(mb, x0, x1, y, z, h=1.0, step=0.12, mat=0):
    """Baranda de hierro sencilla (barrotes + pasamanos)."""
    mb.box(x0, y - 0.03, z + h - 0.05, x1, y + 0.03, z + h, mat)
    mb.box(x0, y - 0.02, z + 0.08, x1, y + 0.02, z + 0.12, mat)
    n = max(1, int((x1 - x0) / step))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        mb.box(x - 0.012, y - 0.012, z, x + 0.012, y + 0.012, z + h, mat)


def _steps(mb, x0, x1, y_front, n, rise, tread, mat=0, z0=0.0):
    """Escalinata que sube hacia +y terminando en y_front."""
    for i in range(n):
        mb.box(x0, y_front - (n - i) * tread, z0, x1, y_front + 0.01, z0 + (i + 1) * rise, mat)


# ====================================================================== CAPITOLIO

def capitolio(ctx, b, root):
    """Capitolio Nacional (lado sur, fachada al NNE).

    Cuerpos laterales macizos + portico central de col_across x col_deep columnas jonicas
    que se abre al Patio Mosquera.
    """
    L, D, H = b["length"], b["depth"], b["height"]
    coll = ctx.coll("Capitolio Nacional")
    m = ctx.m
    ax = b["axis_local"]
    pw = b["portico_w"]
    px0, px1 = ax - pw / 2, ax + pw / 2
    hp = b["podium_h"]
    pat_w, pat_d = b["patio"]
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(0, 0, 0, px0, D, H)
        mb.box(px1, 0, 0, L, D, H)
        mb.box(px0, 8.6 + pat_d, 0, px1, D, H)
        mb.box(px0, 0, 0, px1, 8.6, hp)
        mb.box(px0, 0, H - b["entablature_h"], px1, 8.6, H)
        return _finish(mb, "Capitolio massing", coll, [m["massing"]], root)

    hc, rc = b["col_h"], b["col_r"]
    he = b["entablature_h"]
    wall, trim, cut, fr, gl, cols, rf = (MeshBuilder() for _ in range(7))
    # --- podio corrido (zocalo rusticado) y escalinata frente al portico
    trim.box(-0.3, -0.6, 0, L + 0.3, 0.3, hp)
    rise = 0.16
    nst = int(round(hp / rise))
    tread = b["step_tread"]
    _steps(trim, px0 - 3.0, px1 + 3.0, -0.6, nst, hp / nst, tread)
    # --- cuerpos laterales
    pat_y0 = 8.6
    for x0, x1 in ((0.0, px0), (px1, L)):
        wall.box(x0, 0, hp, x1, D, H - 0.01)
        nb = b["side_bays"]
        xs = _xs(x0 + 1.2, x1 - 1.2, nb)
        _windows(cut, fr, gl, trim, xs, hp + 1.3, 1.7, 3.3, lintel=0.3)
        _windows(cut, fr, gl, trim, xs, hp + 7.6, 1.8, 4.2, lintel=0.35, pediment=True,
                 balcony=True)
        # pilastras jonicas de orden gigante entre ejes
        step = (x1 - x0 - 2.4) / nb
        for i in range(nb + 1):
            x = x0 + 1.2 + step * i
            trim.box(x - 0.55, -0.28, hp, x + 0.55, 0.02, hp + hc)
            trim.box(x - 0.7, -0.38, hp + hc - 0.5, x + 0.7, 0.02, hp + hc)
        trim.sweep_x(geo.string_course_profile(0.5, 0.22), x0, x1, 0, geo.mat_t(0, 0, hp + 6.6))
        # cubierta de teja de los cuerpos laterales (vista aerea)
        rf.hip_roof(x0 + 4.0, 4.0, x1 - 4.0, D - 4.0, H - 0.2, 1.6, 3.0, 0)
    # --- portico: suelo, columnas, entablamento y techo
    trim.box(px0, -0.6, 0, px1, pat_y0, hp)
    na, nd = b["col_across"], b["col_deep"]
    sx = (pw - 3.0) / (na - 1)
    xs = [px0 + 1.5 + sx * i for i in range(na)]
    sy = b["col_spacing_deep"]
    ys = [1.0 + sy * j for j in range(nd)]
    for y in ys:
        for x in xs:
            geo.add_column(cols, x, y, hp, hc, rc, "ionic", 0, segments=28)
    z_ent = hp + hc
    trim.box(px0, -0.1, z_ent, px1, pat_y0 + 0.4, H - 1.2)      # arquitrabe + friso
    trim.box(px0, 0.6, z_ent - 0.05, px1, pat_y0, z_ent + 0.25)  # plafon
    # muros de cierre del portico a los lados (pilastras de esquina)
    for x in (px0, px1):
        trim.box(x - 0.8, -0.3, hp, x + 0.8, pat_y0, z_ent)
    # cornisa corrida en toda la fachada + balaustrada
    trim.sweep_x(geo.cornice_profile(1.2, 0.95), -0.4, L + 0.4, 0, geo.mat_t(0, -0.1, H - 1.2))
    geo.add_balustrade(trim, 0.4, L - 0.4, 0.35, H, 1.05, 0.30, 3.6, 0)
    # grifos (4 figuras) sobre la cubierta, simplificados como remates
    for x in (px0 - 1.0, px1 + 1.0, 3.0, L - 3.0):
        trim.box(x - 0.8, 0.0, H + 1.05, x + 0.8, 1.6, H + 1.6)
        trim.lathe([(0.0, 0), (0.6, 0), (0.55, 0.8), (0.35, 1.6), (0.5, 2.0), (0, 2.3)], 10,
                   (x, 0.8, H + 1.6))
    # --- Patio Mosquera (abierto) y cuerpo posterior
    pz0, pz1 = ax - pat_w / 2, ax + pat_w / 2
    wall.box(px0, pat_y0 + pat_d, hp, px1, D, H - 0.01)       # cuerpo del fondo
    for x0, x1 in ((px0, pz0), (pz1, px1)):                  # crujias laterales del patio
        wall.box(x0, pat_y0, hp, x1, pat_y0 + pat_d, H - 0.01)
    trim.box(pz0, pat_y0, 0, pz1, pat_y0 + pat_d, hp)        # suelo del patio
    # ventanas y arcos del patio (muro del fondo, mirando al portico)
    xs_p = _xs(pz0 + 1.0, pz1 - 1.0, 6)
    pb = MeshBuilder()
    _windows(cut, fr, gl, trim, xs_p, hp, 2.2, 5.0, arch_top=True, sill=False,
             wall_y=pat_y0 + pat_d, depth=0.5)
    _windows(cut, fr, gl, trim, xs_p, hp + 8.0, 1.6, 3.4, lintel=0.3, wall_y=pat_y0 + pat_d)
    # estatua de Mosquera en el centro del patio
    pb.box_c(ax, pat_y0 + pat_d / 2, hp, 1.6, 1.6, 2.4)
    _finish(pb, "Capitolio pedestal Mosquera", coll, [m["pedestal"]], root, 0.01)
    fig = MeshBuilder()
    fig.lathe([(0.0, 0), (0.35, 0), (0.42, 0.9), (0.38, 1.5), (0.18, 1.7), (0.15, 2.0),
               (0.0, 2.15)], 12, (ax, pat_y0 + pat_d / 2, hp + 2.4))
    _finish(fig, "Capitolio estatua Mosquera", coll, [m["bronce"]], root)
    _finish(wall, "Capitolio muros", coll, [m["capitolio_sillar"]], root, 0.02, cut)
    _finish(trim, "Capitolio molduras", coll, [m["capitolio_piedra"]], root, 0.015)
    _finish(cols, "Capitolio columnas", coll, [m["capitolio_piedra"]], root)
    _finish(fr, "Capitolio carpinteria", coll, [m["carpinteria_oscura"]], root)
    _finish(gl, "Capitolio vidrios", coll, [m["vidrio"]], root)
    _finish(rf, "Capitolio cubierta", coll, [m["teja"]], root)


# ====================================================================== CATEDRAL

def catedral(ctx, b, root):
    """Catedral Primada (lado oriental, fachada al occidente)."""
    W, D = b["length"], b["depth"]
    tw, h1, h2 = b["tower_w"], b["level1_h"], b["level2_h"]
    ha = b["atrium_h"]
    coll = ctx.coll("Catedral Primada")
    m = ctx.m
    hb = b["belfry_h"]
    th = ha + h1 + h2 + hb * (1 + 0.78 + 0.55) + 6.0
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(tw, 0, ha, W - tw, D, ha + h1 + h2)
        mb.tri_prism_pediment(tw, W - tw, ha + h1 + h2, b["pediment_h"], 0, 2)
        for x0 in (0, W - tw):
            mb.box(x0, 0, ha, x0 + tw, tw, th)
        return _finish(mb, "Catedral massing", coll, [m["massing"]], root)

    wall, trim, cut = MeshBuilder(), MeshBuilder(), MeshBuilder()
    fr, gl, cols, roof, metal = (MeshBuilder() for _ in range(5))
    # (el atrio elevado y sus gradas se construyen en build.py, continuo con el del Sagrario)
    z0 = ha
    zc1 = z0 + h1
    zc2 = zc1 + h2
    # cuerpo central: dos ordenes superpuestos
    bx0, bx1 = tw, W - tw
    wall.box(bx0, 0, z0, bx1, D * 0.25, zc2)
    cw = bx1 - bx0
    # puertas: central (mayor) y laterales, en arco
    dm = b["door_main"]
    xs3 = [bx0 + cw * 0.2, bx0 + cw * 0.5, bx0 + cw * 0.8]
    for x, (dw, dh) in zip(xs3, (b["door_side"], dm, b["door_side"])):
        o = arch(x - dw / 2, x + dw / 2, z0, z0 + dh - dw / 2, 16)
        cut.prism_xz(o, -1, 0.9)
        fr.prism_xz(o, 0.8, 0.95, 0)  # hoja de puerta (madera)
    # columnas adosadas, orden inferior (toscano) y superior (jonico)
    for i, x in enumerate([bx0 + cw * f for f in (0.06, 0.35, 0.65, 0.94)]):
        geo.add_column(cols, x, -0.25, z0, h1 - 1.6, 0.48, "tuscan", 0, 20)
        geo.add_column(cols, x, -0.25, zc1, h2 - 1.4, 0.40, "ionic", 0, 20)
    # entablamentos
    trim.sweep_x(geo.cornice_profile(1.6, 1.0), bx0 - 0.4, bx1 + 0.4, 0, geo.mat_t(0, -0.3, zc1 - 1.6))
    trim.sweep_x(geo.cornice_profile(1.4, 0.9), bx0 - 0.4, bx1 + 0.4, 0, geo.mat_t(0, -0.3, zc2 - 1.4))
    # ventana central del segundo cuerpo + hornacinas laterales
    _windows(cut, fr, gl, trim, [bx0 + cw * 0.5], zc1 + 1.0, 2.6, h2 - 3.4, arch_top=True,
             lintel=None, sill=True, depth=0.5)
    for x in (bx0 + cw * 0.2, bx0 + cw * 0.8):
        cut.prism_xz(arch(x - 0.9, x + 0.9, zc1 + 1.6, zc1 + h2 - 4.2, 12), -1, 0.6)
    # fronton
    ph = b["pediment_h"]
    trim.tri_prism_pediment(bx0 - 0.4, bx1 + 0.4, zc2, ph, -0.6, 1.0)
    wall.tri_prism_pediment(bx0, bx1, zc2, ph - 0.4, 0.6, D * 0.25)
    # estatuas sobre el fronton (vertice y extremos)
    for x, z in ((bx0 + cw / 2, zc2 + ph), (bx0 + 0.6, zc2), (bx1 - 0.6, zc2)):
        trim.box_c(x, 0.2, z, 1.2, 1.2, 0.6)
        trim.lathe([(0.0, 0), (0.38, 0), (0.42, 0.9), (0.32, 1.6), (0.36, 2.0), (0.2, 2.2),
                    (0.16, 2.45), (0.0, 2.55)], 10, (x, 0.2, z + 0.6))
    # cruz sobre el fronton
    metal.box(bx0 + cw / 2 - 0.1, 0.1, zc2 + ph + 3.1, bx0 + cw / 2 + 0.1, 0.3, zc2 + ph + 5.0)
    metal.box(bx0 + cw / 2 - 0.6, 0.1, zc2 + ph + 4.2, bx0 + cw / 2 + 0.6, 0.3, zc2 + ph + 4.4)
    # torres
    zb = zc2  # base del campanario
    for tx0 in (0.0, W - tw):
        tx1 = tx0 + tw
        txm = (tx0 + tx1) / 2
        wall.box(tx0, 0, z0, tx1, tw, zb)
        # pilastras de esquina
        for px in (tx0 + 0.45, tx1 - 0.45):
            trim.box(px - 0.45, -0.25, z0, px + 0.45, 0.05, zb)
        # ventanas de las torres
        _windows(cut, fr, gl, trim, [txm], z0 + 3.0, 1.6, 3.4, lintel=0.3, depth=0.4)
        _windows(cut, fr, gl, trim, [txm], zc1 + 1.5, 1.4, 3.0, arch_top=True, depth=0.4)
        # cornisa de la torre (continua la del cuerpo central)
        for z, hh in ((zc1 - 1.6, 1.6), (zc2 - 1.4, 1.4)):
            trim.sweep_x(geo.cornice_profile(hh, 0.9), tx0 - 0.4, tx1 + 0.4, 0, geo.mat_t(0, -0.3, z))
        # tres cuerpos de campanario, cada uno mas estrecho, con arcos pasantes
        tym = tw / 2
        zc = zb
        stages = [(hb, b["belfry_inset"]), (hb * 0.78, b["belfry_inset"] + 0.7),
                  (hb * 0.55, b["belfry_inset"] + 1.4)]
        for k, (hs, inset) in enumerate(stages):
            bx0b, bx1b = tx0 + inset, tx1 - inset
            by0b, by1b = inset, tw - inset
            wall.box(bx0b, by0b, zc, bx1b, by1b, zc + hs)
            ow = (bx1b - bx0b) * (0.46 if k < 2 else 0.36)
            zsp = zc + hs - 1.3 - ow / 2
            front_clock = tx0 == 0.0 and k == 0 and b.get("clock", True)
            if front_clock:  # la torre norte lleva reloj al frente: arco solo en la cara trasera
                cut.prism_xz(arch(txm - ow / 2, txm + ow / 2, zc + 1.0, zsp, 14), tym, by1b + 1)
            else:
                cut.prism_xz(arch(txm - ow / 2, txm + ow / 2, zc + 1.0, zsp, 14), by0b - 1,
                             by1b + 1)
            side = MeshBuilder()  # arco pasante en las caras laterales (eje x local)
            side.prism_xz(arch(-ow / 2, ow / 2, zc + 1.0, zsp, 14), -tw, tw)
            cut.extend(side, geo.mat_t(txm, tym, 0, 90))
            if k == 0:
                metal.lathe([(0, 0), (0.75, 0), (0.6, 0.25), (0.42, 0.9), (0.4, 1.2), (0.2, 1.35),
                             (0, 1.35)], 16, (txm, tym, zsp - 1.0))
            # cornisa del cuerpo + jarrones en las esquinas
            trim.box(bx0b - 0.45, by0b - 0.45, zc + hs - 0.55, bx1b + 0.45, by1b + 0.45, zc + hs)
            for (px, py) in ((bx0b, by0b), (bx1b, by0b), (bx0b, by1b), (bx1b, by1b)):
                trim.lathe([(0, 0), (0.3, 0), (0.3, 0.35), (0.1, 0.5), (0.2, 0.8), (0, 1.15)], 12,
                           (px, py, zc + hs))
            zc += hs
        # cupulin en forma de campana (perfil en S) con linterna y cruz
        inset = stages[-1][1]
        zd = zc
        rd = (tw - 2 * inset) * 0.5
        bell = [(1.04, 0.0), (1.04, 0.18), (0.96, 0.24), (0.98, 0.34), (0.97, 0.55), (0.92, 0.80),
                (0.80, 1.05), (0.62, 1.25), (0.42, 1.38), (0.25, 1.45), (0.0, 1.47)]
        roof.lathe([(rd * a, rd * z) for a, z in bell], 8, (txm, tym, zd), smooth=False)
        ztop = zd + rd * 1.45
        trim.lathe([(0.45, 0), (0.45, 1.1), (0.6, 1.2), (0.35, 1.45), (0.12, 1.75), (0.0, 1.8)], 8,
                   (txm, tym, ztop - 0.1))
        metal.box(txm - 0.07, tym - 0.07, ztop + 1.6, txm + 0.07, tym + 0.07, ztop + 3.5)
        metal.box(txm - 0.55, tym - 0.07, ztop + 2.6, txm + 0.55, tym + 0.07, ztop + 2.8)
        if tx0 == 0.0 and b.get("clock", True):
            # reloj en la torre norte, sobre la cornisa mayor
            zc_clock = zb + hb * 0.45
            trim.lathe([(0.0, 0), (1.15, 0), (1.15, 0.12), (0.0, 0.12)], 32, (0, 0, 0),
                       matrix=geo.mat_t(txm, b["belfry_inset"] - 0.13, zc_clock)
                       @ _rot_x(90))
            clock = MeshBuilder()
            clock.lathe([(0.0, 0), (0.95, 0), (0.95, 0.03), (0.0, 0.03)], 32, (0, 0, 0),
                        matrix=geo.mat_t(txm, b["belfry_inset"] - 0.15, zc_clock) @ _rot_x(90))
            _finish(clock, "Catedral reloj", coll, [m["reloj"]], root)
            metal.box(txm - 0.04, b["belfry_inset"] - 0.2, zc_clock, txm + 0.04,
                      b["belfry_inset"] - 0.17, zc_clock + 0.75)
            metal.box(txm, b["belfry_inset"] - 0.2, zc_clock - 0.03, txm + 0.55,
                      b["belfry_inset"] - 0.17, zc_clock + 0.03)
    # nave detras de la fachada con tejado a dos aguas
    nave_h = b["nave_h"]
    wall.box(tw * 0.3, D * 0.25, z0, W - tw * 0.3, D, z0 + nave_h)
    rf = MeshBuilder()
    rf.sweep_x([(-0.6, 0), (W - tw * 0.6 + 0.6, 0), ((W - tw * 0.6) / 2, 7.0)], 0, D * 0.75 + 0.6)
    roof_obj = MeshBuilder()
    roof_obj.extend(rf, geo.mat_t(W - tw * 0.3, D * 0.25 - 0.3, z0 + nave_h, 90))
    _finish(wall, "Catedral muros", coll, [m["catedral_sillar"]], root, 0.02, cut)
    _finish(trim, "Catedral molduras", coll, [m["catedral_piedra"]], root, 0.012)
    _finish(cols, "Catedral columnas", coll, [m["catedral_piedra"]], root)
    _finish(roof, "Catedral cupulines", coll, [m["cupula"]], root)
    _finish(roof_obj, "Catedral tejado", coll, [m["teja"]], root)
    _finish(fr, "Catedral puertas", coll, [m["madera"]], root)
    _finish(gl, "Catedral vidrios", coll, [m["vidrio"]], root)
    _finish(metal, "Catedral metal", coll, [m["hierro"]], root)


# ====================================================================== GENERICOS

def palacio_generico(ctx, b, root, name, wall_mat, trim_mat, roof=None):
    """Edificio de fachada regular: n pisos x m ejes, zocalo, impostas, cornisa, portada."""
    L, D, H = b["length"], b["depth"], b["height"]
    coll = ctx.coll(name)
    m = ctx.m
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(0, 0, 0, L, D, H)
        return _finish(mb, name + " massing", coll, [m["massing"]], root)
    wall, trim, cut, fr, gl, rmb, met = (MeshBuilder() for _ in range(7))
    nf, nb = b["floors"], b["bays"]
    fh = (H - b.get("cornice_h", 1.2)) / nf
    wall.box(0, 0, 0, L, D, H)
    trim.sweep_x(geo.plinth_profile(b.get("plinth_h", 1.0), 0.12), -0.1, L + 0.1, 0)
    xs = _xs(0.8, L - 0.8, nb)
    portal = b.get("portal_bay")
    for f in range(nf):
        z = f * fh
        ww, wh = b.get("win_w", 1.3), fh * b.get("win_hr", 0.55)
        zs = z + (fh - wh) * (0.5 if f else 0.45)
        sel = [x for i, x in enumerate(xs) if not (f == 0 and portal is not None and i == portal)]
        _windows(cut, fr, gl, trim, sel, zs, ww, wh, arch_top=(f == 0 and b.get("arched_ground")),
                 lintel=0.25 if f else None, pediment=(f == 1 and b.get("pediments", False)),
                 balcony=(f == 1 and b.get("balconies", False) and not b.get("colonial")))
        if f == 1 and b.get("balconies", False) and not b.get("colonial"):
            for x in sel:
                _railing(met, x - ww / 2 - 0.3, x + ww / 2 + 0.3, -0.7, zs - 0.05, 0.95)
        if f > 0:
            trim.sweep_x(geo.string_course_profile(0.3, 0.15), -0.05, L + 0.05, 0,
                         geo.mat_t(0, 0, z - 0.3))
    if portal is not None:
        x = xs[portal]
        pw, ph = b.get("portal_w", 3.4), b.get("portal_h", 5.0)
        o = arch(x - pw / 2, x + pw / 2, 0, ph - pw / 2, 16)
        cut.prism_xz(o, -1, 0.6)
        fr.prism_xz(o, 0.5, 0.62, 0)
        trim.box(x - pw / 2 - 0.9, -0.4, 0, x - pw / 2, 0.05, ph + 0.8)
        trim.box(x + pw / 2, -0.4, 0, x + pw / 2 + 0.9, 0.05, ph + 0.8)
        trim.sweep_x(geo.cornice_profile(0.8, 0.6), x - pw / 2 - 1.1, x + pw / 2 + 1.1, 0,
                     geo.mat_t(0, -0.35, ph + 0.8))
    # pilastras de esquina
    for px in (0.0, L - 0.9):
        trim.box(px, -0.15, 0, px + 0.9, 0.05, H - 1.0)
    ch = b.get("cornice_h", 1.2)
    trim.sweep_x(geo.cornice_profile(ch, 0.8), -0.4, L + 0.4, 0, geo.mat_t(0, 0, H - ch))
    if b.get("parapet"):
        wall.box(0, 0.3, H, L, D, H + b["parapet"])
    if b.get("colonial"):
        # balcon corrido de madera en el piso alto + alero de teja
        zb = fh - 0.15
        wood = MeshBuilder()
        wood.box(0.3, -1.0, zb, L - 0.3, 0.0, zb + 0.15)
        for x in [0.3 + i * 0.16 for i in range(int((L - 0.6) / 0.16) + 1)]:
            wood.box(x - 0.03, -0.98, zb + 0.15, x + 0.03, -0.92, zb + 1.05)
        wood.box(0.3, -1.0, zb + 1.0, L - 0.3, -0.88, zb + 1.1)
        for x in (0.4, L / 2, L - 0.4):  # pies derechos que sostienen el alero
            wood.box(x - 0.07, -0.97, zb + 0.15, x + 0.07, -0.83, H + 0.2)
        # canecillos del alero
        for x in [0.5 + i * 0.6 for i in range(int((L - 1.0) / 0.6) + 1)]:
            wood.box(x - 0.06, -1.25, H - 0.1, x + 0.06, 0.2, H + 0.08)
        _finish(wood, name + " balcon", coll, [m["madera_balcon"]], root, 0.005)
    if roof == "tile":
        rf = MeshBuilder()
        ov = 1.3 if b.get("colonial") else 0.5
        rf.hip_roof(-0.4, -ov, L + 0.4, D + 0.3, H, 3.0, min(L, D) / 2 - 0.5, 0)
        _finish(rf, name + " tejado", coll, [m["teja"]], root)
    _finish(wall, name + " muros", coll, [wall_mat], root, 0.015, cut)
    _finish(trim, name + " molduras", coll, [trim_mat], root, 0.01)
    _finish(fr, name + " carpinteria", coll, [m["madera"]], root)
    _finish(gl, name + " vidrios", coll, [m["vidrio"]], root)
    _finish(met, name + " hierro", coll, [m["hierro"]], root)


# ====================================================================== SAGRARIO

def sagrario(ctx, b, root):
    """Capilla del Sagrario: fachada-retablo barroca, espadana y cupula."""
    L, D, H = b["length"], b["depth"], b["height"]
    coll = ctx.coll("Capilla del Sagrario")
    m = ctx.m
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(0, 0, 0, L, D, H)
        return _finish(mb, "Sagrario massing", coll, [m["massing"]], root)
    wall, trim, cut, fr, gl, cols, rf, met = (MeshBuilder() for _ in range(8))
    ha = b.get("atrium_h", 0.0)
    wall.box(0, 0, 0, L, D, H)
    xm = L / 2
    # portada en piedra: dos cuerpos con columnas pareadas
    pw = L * 0.55
    trim.box(xm - pw / 2, -0.6, 0, xm + pw / 2, 0.05, H * 0.92)
    o = arch(xm - 1.5, xm + 1.5, ha, ha + 5.2, 16)
    cut.prism_xz(o, -2, 0.9)
    fr.prism_xz(o, 0.8, 0.95, 0)
    for s in (-1, 1):
        for k in (1.55, 2.45):
            geo.add_column(cols, xm + s * k, -0.9, ha, 6.8, 0.26, "corinthian", 0, 16)
            geo.add_column(cols, xm + s * k, -0.9, ha + 7.6, 4.6, 0.20, "ionic", 0, 16)
    trim.sweep_x(geo.cornice_profile(0.9, 0.7), xm - pw / 2 - 0.3, xm + pw / 2 + 0.3, 0,
                 geo.mat_t(0, -0.65, ha + 6.8))
    _windows(cut, fr, gl, trim, [xm], ha + 8.4, 1.6, 2.8, arch_top=True, depth=0.4,
             wall_y=-0.6)
    trim.tri_prism_pediment(xm - pw / 2, xm + pw / 2, ha + 12.3, 2.2, -0.9, 0.0)
    # espadana con dos vanos para campanas
    ew = L * 0.4
    wall.box(xm - ew / 2, 0.2, H, xm + ew / 2, 1.2, H + 5.5)
    for s in (-1, 1):
        cut.prism_xz(arch(xm + s * ew * 0.22 - 0.7, xm + s * ew * 0.22 + 0.7, H + 1.2, H + 3.6, 12),
                     -1, 3)
    trim.tri_prism_pediment(xm - ew / 2 - 0.3, xm + ew / 2 + 0.3, H + 5.5, 1.6, 0.0, 1.4)
    met.box(xm - 0.08, 0.6, H + 7.1, xm + 0.08, 0.8, H + 9.0)
    met.box(xm - 0.5, 0.6, H + 8.1, xm + 0.5, 0.8, H + 8.3)
    # cupula sobre el crucero
    rd = b.get("dome_r", 4.5)
    cy = D * 0.7
    dr = b.get("drum_h", 4.5)
    wall.lathe([(rd + 0.3, 0), (rd + 0.3, dr), (0, dr)], 16, (xm, cy, H))
    rf.lathe([(rd, 0)] + [(rd * math.cos(math.radians(a)), rd * 1.1 * math.sin(math.radians(a)))
                          for a in range(10, 91, 10)], 24, (xm, cy, H + dr))
    trim.lathe([(0.8, 0), (0.8, 1.6), (1.0, 1.7), (0, 2.6)], 12, (xm, cy, H + dr + rd * 1.1 - 0.2))
    rr = MeshBuilder()
    rr.hip_roof(-0.3, 1.0, L + 0.3, D + 0.3, H, 3.0, L / 2 - 0.4, 0)
    _finish(wall, "Sagrario muros", coll, [m["sagrario_estuco"]], root, 0.015, cut)
    _finish(trim, "Sagrario portada", coll, [m["sagrario_piedra"]], root, 0.01)
    _finish(cols, "Sagrario columnas", coll, [m["sagrario_piedra"]], root)
    _finish(rf, "Sagrario cupula", coll, [m["cupula"]], root)
    _finish(rr, "Sagrario tejado", coll, [m["teja"]], root)
    _finish(fr, "Sagrario puerta", coll, [m["madera"]], root)
    _finish(gl, "Sagrario vidrios", coll, [m["vidrio"]], root)
    _finish(met, "Sagrario metal", coll, [m["hierro"]], root)


# ====================================================================== PALACIO DE JUSTICIA

def palacio_justicia(ctx, b, root):
    """Palacio de Justicia (lado norte, fachada al SSO), segun foto de referencia:

    dos alas macizas de arenisca con grandes marcos rehundidos y pilares, cuerpo central
    saliente con un gran portal, volumen superior retranqueado con banda de ventanas y una
    cupula de vidrio en el centro.
    """
    L, D, H = b["length"], b["depth"], b["height"]
    coll = ctx.coll("Palacio de Justicia")
    m = ctx.m
    wing_h, cen_w, cen_h, cen_p = b["wing_h"], b["center_w"], b["center_h"], b["center_proj"]
    up_set = b["upper_setback"]
    xc0, xc1 = L / 2 - cen_w / 2, L / 2 + cen_w / 2
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(0, 0, 0, L, D, wing_h)
        mb.box(xc0, -cen_p, 0, xc1, 10, cen_h)
        mb.box(4, up_set, wing_h, L - 4, D - 6, H)
        return _finish(mb, "Palacio de Justicia massing", coll, [m["massing"]], root)
    wall, trim, cut, fr, gl, met = (MeshBuilder() for _ in range(6))
    # --- alas laterales con marco rehundido, pilares y fachada acristalada al fondo
    rd = b["recess_depth"]
    for x0, x1 in ((0.0, xc0), (xc1, L)):
        wall.box(x0, 0, 0, x1, D, wing_h)
        fx0, fx1 = x0 + 2.6, x1 - 2.6
        cut.prism_xz(rect(fx0, -0.01, fx1, wing_h - 2.6), -1, rd)
        n = b["wing_pillars"]
        for i in range(1, n + 1):
            x = fx0 + (fx1 - fx0) * i / (n + 1)
            trim.box(x - 0.75, rd * 0.35, 0, x + 0.75, rd, wing_h - 2.6)
        # muro cortina al fondo del marco: 3 niveles
        gl.box(fx0, rd - 0.05, 0, fx1, rd, wing_h - 2.6)
        for k in range(1, 3):
            z = (wing_h - 2.6) * k / 3
            fr.box(fx0, rd - 0.35, z - 0.25, fx1, rd - 0.04, z + 0.25)
        for i in range(int((fx1 - fx0) / 1.6) + 1):
            x = fx0 + i * 1.6
            fr.box(x - 0.05, rd - 0.2, 0, x + 0.05, rd - 0.04, wing_h - 2.6)
        # zocalo y remate
        trim.box(x0 - 0.1, -0.25, wing_h - 0.6, x1 + 0.1, 0.4, wing_h + 0.15)
    # --- cuerpo central saliente con el gran portal
    wall.box(xc0, -cen_p, 0, xc1, 12.0, cen_h)
    pw, ph = b["portal"]
    cut.prism_xz(rect(L / 2 - pw / 2, -0.01, L / 2 + pw / 2, ph), -cen_p - 1, 6.0)
    for x in (L / 2 - pw / 6, L / 2 + pw / 6):
        trim.box(x - 0.8, -cen_p + 1.8, 0, x + 0.8, -cen_p + 3.4, ph)
    gl.box(L / 2 - pw / 2, 5.9, 0, L / 2 + pw / 2, 6.0, ph)
    trim.box(xc0 - 0.3, -cen_p - 0.4, cen_h - 0.7, xc1 + 0.3, -cen_p + 1.2, cen_h + 0.15)  # cornisa
    for x0_, x1_ in ((xc0 - 0.3, xc0 + 0.9), (xc1 - 0.9, xc1 + 0.3)):
        trim.box(x0_, -cen_p - 0.4, cen_h - 0.7, x1_, 12.0, cen_h + 0.15)
    # --- volumen superior retranqueado con banda de ventanas y cupula de vidrio
    wall.box(4.0, up_set, wing_h, L - 4.0, D - 6.0, H)
    ncol = b["upper_windows"]
    xs = _xs(6.0, L - 6.0, ncol)
    for zw in (wing_h + 1.2, wing_h + 4.6):
        _windows(cut, fr, gl, trim, xs, zw, 1.7, 2.2, sill=False, depth=0.5, wall_y=up_set)
    for (a0, b0, a1, b1) in ((3.6, up_set - 0.4, L - 3.6, up_set + 0.8),
                             (3.6, D - 6.8, L - 3.6, D - 5.6),
                             (3.6, up_set - 0.4, 4.8, D - 5.6),
                             (L - 4.8, up_set - 0.4, L - 3.6, D - 5.6)):
        trim.box(a0, b0, H - 0.6, a1, b1, H + 0.15)  # pretil perimetral
    dome = MeshBuilder()
    r = b["dome_r"]
    dome.lathe([(r, 0)] + [(r * math.cos(math.radians(a)), r * 0.75 * math.sin(math.radians(a)))
                           for a in range(10, 91, 10)], 32, (L / 2, D * 0.35, H))
    trim.lathe([(r + 0.4, 0), (r + 0.4, 0.8), (0, 0.8)], 32, (L / 2, D * 0.35, H - 0.6))
    _finish(wall, "Palacio de Justicia muros", coll, [m["justicia_piedra"]], root, 0.02, cut)
    _finish(trim, "Palacio de Justicia pilares", coll, [m["justicia_piedra"]], root, 0.015)
    _finish(fr, "Palacio de Justicia carpinteria", coll, [m["carpinteria_oscura"]], root)
    _finish(gl, "Palacio de Justicia vidrios", coll, [m["vidrio"]], root)
    _finish(dome, "Palacio de Justicia cupula", coll, [m["vidrio_azul"]], root)
    # inscripcion de Santander sobre el portal central
    txt = b.get("inscription")
    if txt:
        cu = bpy.data.curves.new("Inscripcion", "FONT")
        cu.body = txt
        cu.align_x = "CENTER"
        cu.size = b.get("inscription_size", 0.5)
        cu.extrude = 0.02
        ob = bpy.data.objects.new("Palacio de Justicia inscripcion", cu)
        coll.objects.link(ob)
        ob.parent = root
        ob.location = (L / 2, -cen_p - 0.03, ph + (cen_h - 0.7 - ph) * 0.45)
        ob.rotation_euler = (math.radians(90), 0, 0)
        cu.materials.append(m["bronce_letras"])


# ====================================================================== LIEVANO

def lievano(ctx, b, root):
    """Edificio Lievano (lado occidental, fachada al ESE).

    Basamento en arcada de piedra + 2 pisos con 32 vanos, cuerpo central con fronton,
    mansardas solo en los pabellones de esquina.
    """
    L, D, H = b["length"], b["depth"], b["height"]
    coll = ctx.coll("Edificio Lievano")
    m = ctx.m
    mh = b["mansard_h"]
    nb = b["bays"]
    bw = L / nb
    pavs = b["pavilions"]
    if ctx.massing:
        mb = MeshBuilder()
        mb.box(0, 0, 0, L, D, H)
        for i0, i1 in pavs:
            mb.hip_roof(i0 * bw, 0, (i1 + 1) * bw, D, H, mh, 2.5)
        return _finish(mb, "Lievano massing", coll, [m["massing"]], root)
    wall, trim, cut, fr, gl, rf, met, arc, acut = (MeshBuilder() for _ in range(9))
    ad, ah = b["arcade_depth"], b["arcade_h"]
    xs = _xs(0.0, L, nb)
    pier = b["pier_w"]
    # --- basamento: arcada de piedra (portales)
    wall.box(0, ad, 0, L, D, ah)                 # muro del fondo de los portales
    arc.box(0, 0, 0, L, 1.2, ah)                 # frente de la arcada
    ow = bw - pier
    for x in xs:
        acut.prism_xz(arch(x - ow / 2, x + ow / 2, -0.1, ah - ow / 2 - 0.7, 14), -1, 2.2)
        fr.prism_xz(rect(x - 0.9, 0, x + 0.9, 3.3), ad - 0.12, ad + 0.02, 0)   # puertas de locales
    trim.box(-0.1, 1.2, ah - 0.35, L + 0.1, ad, ah)              # techo de los portales
    trim.sweep_x(geo.string_course_profile(0.45, 0.25), -0.15, L + 0.15, 0, geo.mat_t(0, 0, ah - 0.1))
    # --- pisos altos (revoco claro con molduras)
    wall.box(0, 0, ah, L, D, H - 0.01)
    nf = b["floors_upper"]
    fh = (H - ah - b["cornice_h"]) / nf
    for f in range(nf):
        z = ah + f * fh
        wh = fh * (0.62 if f == 0 else 0.52)
        zs = z + (fh - wh) * (0.55 if f == 0 else 0.45)
        _windows(cut, fr, gl, trim, xs, zs, b["win_w"], wh, lintel=0.28,
                 pediment=(f == 0), balcony=(f == 0), trim_mat=0)
        if f == 0:
            for x in xs:
                _railing(met, x - b["win_w"] / 2 - 0.3, x + b["win_w"] / 2 + 0.3, -0.72,
                         zs - 0.05, 0.95)
        if f > 0:
            trim.sweep_x(geo.string_course_profile(0.3, 0.14), -0.1, L + 0.1, 0,
                         geo.mat_t(0, 0, z - 0.3))
    # pilastras: en los limites de pabellones y cuerpo central, y en cada eje del cuerpo central
    c0, c1 = b["center_pediment"]
    edges = {0, nb}
    for i0, i1 in pavs:
        edges |= {i0, i1 + 1}
    edges |= {c0, c1 + 1}
    edges |= set(range(c0, c1 + 2))
    for i in sorted(edges):
        x = i * bw
        trim.box(x - 0.35, -0.22, ah, x + 0.35, 0.02, H - b["cornice_h"])
    # pabellones y cuerpo central ligeramente salientes
    for i0, i1 in pavs + [(c0, c1)]:
        wall.box(i0 * bw, -0.25, ah, (i1 + 1) * bw, 0.1, H - 0.01)
    ch = b["cornice_h"]
    trim.sweep_x(geo.cornice_profile(ch, 0.85), -0.3, L + 0.3, 0, geo.mat_t(0, -0.25, H - ch))
    # fronton del cuerpo central
    trim.tri_prism_pediment(c0 * bw - 0.3, (c1 + 1) * bw + 0.3, H, 3.2, -0.6, 0.6)
    # balaustrada sobre la cornisa fuera de los pabellones
    seg = [(pavs[0][1] + 1) * bw, c0 * bw, (c1 + 1) * bw, pavs[1][0] * bw]
    geo.add_balustrade(trim, seg[0] + 0.3, seg[1] - 0.3, 0.2, H, 1.0, 0.3, 3.4, 0)
    geo.add_balustrade(trim, seg[2] + 0.3, seg[3] - 0.3, 0.2, H, 1.0, 0.3, 3.4, 0)
    # cubierta: plana con antepecho + mansardas de pizarra en las esquinas
    wall.box(0.5, 1.0, H, L - 0.5, D - 0.5, H + 0.6)
    dorm = MeshBuilder()
    for i0, i1 in pavs:
        x0, x1 = i0 * bw - 0.2, (i1 + 1) * bw + 0.2
        rf.hip_roof(x0, -0.3, x1, D, H, mh * 0.75, 1.2, 0)                      # faldon inferior
        rf.hip_roof(x0 + 1.2, 0.9, x1 - 1.2, D - 1.2, H + mh * 0.75, mh * 0.35,
                    min(x1 - x0, D) / 2 - 1.6, 0)                                # faldon superior
        met.box((x0 + x1) / 2 - 0.08, D / 2 - 0.08, H + mh * 1.1, (x0 + x1) / 2 + 0.08,
                D / 2 + 0.08, H + mh * 1.1 + 2.0)                                # cresteria
        for x in xs[i0:i1 + 1]:
            dorm.box(x - 0.6, 0.4, H + 0.6, x + 0.6, 2.0, H + 2.5)
            dorm.lathe([(0.0, 0), (0.62, 0)] + [(0.62 * math.cos(math.radians(t)),
                        0.5 * math.sin(math.radians(t))) for t in range(15, 91, 15)], 12,
                       (x, 1.2, H + 2.5), scale_xy=(1.0, 0.75))
            gl.box(x - 0.42, 0.37, H + 0.8, x + 0.42, 0.4, H + 2.2)
    _finish(wall, "Lievano muros", coll, [m["lievano_estuco"]], root, 0.015, cut)
    _finish(arc, "Lievano arcada de piedra", coll, [m["lievano_piedra"]], root, 0.015, acut)
    _finish(trim, "Lievano molduras", coll, [m["lievano_molduras"]], root, 0.01)
    _finish(rf, "Lievano mansardas", coll, [m["pizarra"]], root)
    _finish(dorm, "Lievano buhardillas", coll, [m["lievano_molduras"]], root, 0.01)
    _finish(fr, "Lievano carpinteria", coll, [m["carpinteria_clara"]], root)
    _finish(gl, "Lievano vidrios", coll, [m["vidrio"]], root)
    _finish(met, "Lievano hierro", coll, [m["hierro"]], root)


# ====================================================================== ESTATUA

def estatua(ctx, b, coll_name="Estatua de Bolivar"):
    """Pedestal + figura de bronce simplificada (Bolivar de Tenerani)."""
    coll = ctx.coll(coll_name)
    m = ctx.m
    hp, hs = b["pedestal_h"], b["statue_h"]
    sx = b["base_w"]
    if ctx.massing:
        mb = MeshBuilder()
        mb.box_c(0, 0, 0, sx, sx, hp)
        fig = MeshBuilder()
        fig.lathe([(0.0, 0), (0.45, 0), (0.45, hs), (0, hs)], 12, (0, 0, hp))
        _finish(mb, "Pedestal massing", coll, [m["massing"]], None)
        return _finish(fig, "Estatua massing", coll, [m["massing"]], None)
    ped = MeshBuilder()
    # gradas
    z = 0.0
    for i, (w, h) in enumerate(b["steps"]):
        ped.box_c(0, 0, z, w, w, h)
        z += h
    # zocalo, dado y cornisa
    zb = z
    dz = hp - zb
    ped.box_c(0, 0, zb, sx, sx, dz * 0.18)
    ped.box_c(0, 0, zb + dz * 0.18, sx * 0.86, sx * 0.86, dz * 0.06)
    ped.box_c(0, 0, zb + dz * 0.24, sx * 0.78, sx * 0.78, dz * 0.56)
    ped.box_c(0, 0, zb + dz * 0.80, sx * 0.86, sx * 0.86, dz * 0.08)
    ped.box_c(0, 0, zb + dz * 0.88, sx * 0.92, sx * 0.92, dz * 0.07)
    ped.box_c(0, 0, zb + dz * 0.95, sx * 0.80, sx * 0.80, dz * 0.05)
    # figura: esqueleto + modificador Skin (silueta organica), capa, cabeza y espada
    fig = MeshBuilder()
    hs_ = hs
    zf = hp + 0.12
    fig.box_c(0, 0, hp, 1.0, 1.0, 0.12)  # peana de bronce
    obj_body = _skin_figure(coll, hs_, zf)
    s = hs_ / 7.5
    # cabeza
    fig.lathe([(0, 6.45 * s), (0.30 * s, 6.55 * s), (0.42 * s, 6.92 * s), (0.40 * s, 7.25 * s),
               (0.22 * s, 7.48 * s), (0, 7.52 * s)], 14, (0, -0.06 * s, zf), scale_xy=(0.9, 1.0))
    # capa: cae desde los hombros por la espalda y el costado izquierdo hasta la pantorrilla
    # (sector abierto por delante: de -20 a 200 grados, el frente -y queda descubierto)
    fig.lathe([(1.25 * s, 1.3 * s), (1.15 * s, 2.6 * s), (1.05 * s, 4.2 * s), (1.02 * s, 5.4 * s),
               (1.05 * s, 6.0 * s), (0.75 * s, 6.25 * s), (0.45 * s, 6.3 * s)], 24,
              (0.0, 0.12 * s, zf), scale_xy=(1.0, 0.62), arc=(-20.0, 200.0))
    # espada en la mano derecha, punta hacia el suelo
    fig.box(-0.95 * s - 0.025, -0.55 * s - 0.025, zf + 0.25 * s, -0.95 * s + 0.025,
            -0.55 * s + 0.025, zf + 3.4 * s)
    fig.box(-0.95 * s - 0.18, -0.55 * s - 0.03, zf + 3.35 * s, -0.95 * s + 0.18, -0.55 * s + 0.03,
            zf + 3.42 * s)
    # pergamino en la mano izquierda
    fig.lathe([(0.07, 0), (0.07, 0.42), (0, 0.42)], 10, (0, 0, 0),
              matrix=geo.mat_t(0.62 * s, -0.75 * s, zf + 3.9 * s) @ _rot_x(90))
    _finish(ped, "Pedestal", coll, [m["pedestal"]], None, 0.012)
    obj = _finish(fig, "Bolivar (bronce)", coll, [m["bronce"]], None)
    obj_body.data.materials.append(m["bronce"])
    if obj is not None:
        sub = obj.modifiers.new("Suavizado", "SUBSURF")
        sub.levels = 1
        sub.render_levels = 2
    if b.get("rotation_deg"):
        for o in coll.objects:
            o.rotation_euler[2] = math.radians(b["rotation_deg"])
    return obj


def _skin_figure(coll, h, z0):
    """Cuerpo humano de pie (contrapposto) con modificador Skin + Subsurf. Mira hacia -y."""
    s = h / 7.5
    J = {  # articulaciones (x, y, z) y radio
        "pelvis": ((0.0, 0.0, 3.75), 0.62), "abdomen": ((0.0, 0.0, 4.5), 0.60),
        "pecho": ((0.0, 0.02, 5.4), 0.72), "cuello": ((0.0, 0.0, 6.25), 0.28),
        "cabeza": ((0.0, -0.05, 6.5), 0.22),
        "cadera_d": ((0.42, 0.0, 3.6), 0.40), "rodilla_d": ((0.40, -0.25, 1.95), 0.27),
        "tobillo_d": ((0.40, -0.05, 0.25), 0.22), "pie_d": ((0.42, -0.65, 0.10), 0.15),
        "cadera_i": ((-0.42, 0.0, 3.6), 0.40), "rodilla_i": ((-0.48, 0.05, 1.95), 0.27),
        "tobillo_i": ((-0.50, 0.10, 0.25), 0.22), "pie_i": ((-0.55, -0.50, 0.10), 0.15),
        "hombro_d": ((0.95, 0.0, 5.95), 0.30), "codo_d": ((1.05, -0.05, 4.65), 0.22),
        "mano_d": ((0.95, -0.50, 3.55), 0.17),
        "hombro_i": ((-0.95, 0.0, 5.95), 0.30), "codo_i": ((-1.10, 0.05, 4.65), 0.22),
        "mano_i": ((-0.62, -0.70, 3.95), 0.17),
    }
    E = [("pelvis", "abdomen"), ("abdomen", "pecho"), ("pecho", "cuello"), ("cuello", "cabeza"),
         ("pelvis", "cadera_d"), ("cadera_d", "rodilla_d"), ("rodilla_d", "tobillo_d"),
         ("tobillo_d", "pie_d"), ("pelvis", "cadera_i"), ("cadera_i", "rodilla_i"),
         ("rodilla_i", "tobillo_i"), ("tobillo_i", "pie_i"), ("pecho", "hombro_d"),
         ("hombro_d", "codo_d"), ("codo_d", "mano_d"), ("pecho", "hombro_i"),
         ("hombro_i", "codo_i"), ("codo_i", "mano_i")]
    names = list(J)
    # la figura mira hacia -y, asi que su mano derecha queda en -x (se refleja el esqueleto)
    verts = [(-J[n][0][0] * s, J[n][0][1] * s, z0 + J[n][0][2] * s) for n in names]
    edges = [(names.index(a), names.index(b)) for a, b in E]
    me = bpy.data.meshes.new("Bolivar cuerpo")
    me.from_pydata(verts, edges, [])
    ob = bpy.data.objects.new("Bolivar cuerpo (bronce)", me)
    coll.objects.link(ob)
    sk = ob.modifiers.new("Piel", "SKIN")
    sk.use_smooth_shade = True
    for i, n in enumerate(names):
        r = J[n][1] * s
        sv = me.skin_vertices[0].data[i]
        sv.radius = (r, r * (0.75 if n in ("pecho", "abdomen", "pelvis") else 1.0))
        sv.use_root = n == "pelvis"
    sub = ob.modifiers.new("Suavizado", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    return ob


def _rot_x(deg):
    from mathutils import Matrix
    return Matrix.Rotation(math.radians(deg), 4, "X")
