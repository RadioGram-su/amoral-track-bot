"""
Нарисуй героя — процедурные 3D-модели стола.

Запуск (Blender как python-модуль, bpy 5.2):
    python3 tools/blender/build_props.py godot/assets/models

Или из Blender:
    blender -b -P tools/blender/build_props.py -- godot/assets/models

Масштаб: 1 единица Blender = 1 дм (10 см). Ось Z вверх (glTF экспорт делает Y вверх).
Каждая модель экспортируется в отдельный .glb. Имена материалов используются
в Godot для подмены на собственные шейдеры (см. scripts/props.gd).
"""
import bpy
import bmesh
import math
import json
import os
import random
import sys
from mathutils import Vector, Matrix, noise

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = argv[1:]
OUT = os.path.abspath(argv[0] if argv else "godot/assets/models")
os.makedirs(OUT, exist_ok=True)

random.seed(7)
TAU = math.tau

# ------------------------------------------------------------------ utils

_MATS = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()


def mat(name, color, rough=0.5, metal=0.0, emission=None, alpha=1.0, transmission=0.0):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 4.0
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    if transmission > 0:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    m.diffuse_color = (*color, alpha)
    _MATS[name] = m
    return m


def obj_from_bm(name, bm, material=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if material is not None:
        if isinstance(material, (list, tuple)):
            for m in material:
                me.materials.append(m)
        else:
            me.materials.append(material)
    return ob


def deselect_all():
    for o in bpy.context.scene.objects:
        if o is not None:
            o.select_set(False)


def activate(ob):
    deselect_all()
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def bevel(ob, width, segments=3, angle=40.0, apply=True):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = True
    if apply:
        apply_mods(ob)


def subsurf(ob, levels=2, apply=True):
    m = ob.modifiers.new("Subd", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    if apply:
        apply_mods(ob)


def smooth(ob, angle=35.0):
    """Гладкие нормали + острые рёбра по углу (аналог auto smooth)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for f in bm.faces:
        f.smooth = True
    lim = math.radians(angle)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)
            e.smooth = a < lim
        else:
            e.smooth = False
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def set_origin(ob, point):
    """Переносит origin в точку (мировые координаты), не двигая геометрию."""
    p = Vector(point)
    ob.data.transform(Matrix.Translation(-(p - ob.location)))
    ob.location = p


def apply_transform(ob):
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


def join(objs, name):
    deselect_all()
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def planar_uv(ob, axis="Z", bounds=None):
    """UV по плоской проекции. bounds = (umin, umax, vmin, vmax) в координатах."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    pts = [v.co for v in bm.verts]
    if axis == "Z":
        get = lambda c: (c.x, c.y)
    elif axis == "Y":
        get = lambda c: (c.x, c.z)
    else:
        get = lambda c: (c.y, c.z)
    if bounds is None:
        us = [get(c)[0] for c in pts]
        vs = [get(c)[1] for c in pts]
        bounds = (min(us), max(us), min(vs), max(vs))
    u0, u1, v0, v1 = bounds
    for f in bm.faces:
        for l in f.loops:
            a, b = get(l.vert.co)
            l[uv].uv = ((a - u0) / (u1 - u0), (b - v0) / (v1 - v0))
    bm.to_mesh(ob.data)
    bm.free()


def box_uv(ob, scale=1.0):
    """Кубическая проекция UV (для дерева, картона)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co
            if ax == 2:
                l[uv].uv = (c.x * scale, c.y * scale)
            elif ax == 1:
                l[uv].uv = (c.x * scale, c.z * scale)
            else:
                l[uv].uv = (c.y * scale, c.z * scale)
    bm.to_mesh(ob.data)
    bm.free()


def cube(size, loc=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(loc)
    return bm


def lathe(profile, steps=48, axis="Z"):
    """profile: список (r, h). Возвращает bmesh тела вращения."""
    bm = bmesh.new()
    rings = []
    for i in range(steps):
        a = TAU * i / steps
        ring = []
        for r, h in profile:
            if axis == "Z":
                co = (r * math.cos(a), r * math.sin(a), h)
            else:  # ось X
                co = (h, r * math.cos(a), r * math.sin(a))
            ring.append(bm.verts.new(co))
        rings.append(ring)
    for i in range(steps):
        r0, r1 = rings[i], rings[(i + 1) % steps]
        for j in range(len(profile) - 1):
            try:
                bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def prism(n, radius, length, axis="X", start=0.0, rot=0.0):
    """n-угольная призма вдоль оси X, от start до start+length."""
    bm = bmesh.new()
    a_ring, b_ring = [], []
    for i in range(n):
        a = rot + TAU * i / n
        y, z = radius * math.cos(a), radius * math.sin(a)
        a_ring.append(bm.verts.new((start, y, z)))
        b_ring.append(bm.verts.new((start + length, y, z)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a_ring[i], a_ring[j], b_ring[j], b_ring[i]))
    bm.faces.new(list(reversed(a_ring)))
    bm.faces.new(b_ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tube_along(points, radius, sides=10, closed=False):
    """Трубка по ломаной (проволока зажима, скрепка, ручки)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t.normalize()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        n1 = t.cross(up).normalized()
        n2 = t.cross(n1).normalized()
        ring = []
        for k in range(sides):
            a = TAU * k / sides
            ring.append(bm.verts.new(p + (n1 * math.cos(a) + n2 * math.sin(a)) * radius))
        rings.append(ring)
    count = len(rings) if closed else len(rings) - 1
    for i in range(count):
        r0, r1 = rings[i], rings[(i + 1) % len(rings)]
        for k in range(sides):
            kk = (k + 1) % sides
            bm.faces.new((r0[k], r0[kk], r1[kk], r1[k]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def export(objs, filename):
    deselect_all()
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    path = os.path.join(OUT, filename)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_normals=True,
        export_texcoords=True,
    )
    print("exported", path)


def to_godot(v):
    """Blender (x, y, z) Z-up → Godot (x, z, -y) Y-up."""
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


ANCHORS = {}

# ------------------------------------------------------------------ палитра

C_WOOD = (0.32, 0.17, 0.08)
C_PAPER = (0.93, 0.89, 0.80)
C_YELLOW = (0.95, 0.68, 0.10)
C_RED = (0.72, 0.10, 0.08)
C_PINK = (0.92, 0.48, 0.50)
C_METAL = (0.78, 0.76, 0.72)
C_BRASS = (0.80, 0.62, 0.30)
C_BLACK = (0.02, 0.02, 0.025)
C_GRAPHITE = (0.08, 0.08, 0.09)

# ================================================================== СТОЛ


def build_desk():
    reset()
    W, D, T = 9.0, 11.0, 0.4
    m_top = mat("desk_wood", C_WOOD, rough=0.35)
    m_leg = mat("desk_wood_dark", (0.18, 0.09, 0.04), rough=0.5)
    top = obj_from_bm("desk_top", cube((W, D, T), (0, 0, -T / 2)), m_top)
    bevel(top, 0.04, segments=4, angle=30)
    smooth(top, 32)
    box_uv(top, 0.25)
    parts = [top]
    # царга
    for sx, sy, sz, lx, ly in (
        (W - 1.0, 0.12, 0.9, 0, D / 2 - 0.5),
        (W - 1.0, 0.12, 0.9, 0, -D / 2 + 0.5),
        (0.12, D - 1.0, 0.9, W / 2 - 0.5, 0),
        (0.12, D - 1.0, 0.9, -W / 2 + 0.5, 0),
    ):
        ap = obj_from_bm("apron", cube((sx, sy, sz), (lx, ly, -T - sz / 2)), m_leg)
        bevel(ap, 0.015, 2)
        smooth(ap)
        box_uv(ap, 0.25)
        parts.append(ap)
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = obj_from_bm("leg", cube((0.45, 0.45, 7.2), (sx * (W / 2 - 0.45), sy * (D / 2 - 0.45), -T - 3.6)), m_leg)
            bevel(leg, 0.03, 3)
            smooth(leg)
            box_uv(leg, 0.25)
            parts.append(leg)
    desk = join(parts, "Desk")
    export([desk], "desk.glb")
    ANCHORS["desk"] = {"width": W, "depth": D, "top_y": 0.0}


# ================================================================== ТЕТРАДЬ


def page_mesh(name, x0, x1, side, material, nx=48, ny=12):
    """Страница с изгибом у корешка. side = +1 правая, -1 левая."""
    H = 2.05
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = i / nx
            x = x0 + (x1 - x0) * u
            d = abs(x) / 1.7  # 0 у корешка, 1 у края
            z = 0.028 + 0.030 * math.sin(min(d, 1.0) * math.pi * 0.5 + 0.0) * math.exp(-d * 2.2) - 0.012 * d
            z += 0.004 * math.sin(d * 7.0)
            y = -H / 2 + H * j / ny
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for l in f.loops:
                c = l.vert.co
                u = (c.x - min(x0, x1)) / abs(x1 - x0)
                v = (c.y + H / 2) / H
                l[uv].uv = (u, v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    ob = obj_from_bm(name, bm, material)
    smooth(ob, 80)
    return ob


def build_notebook():
    reset()
    m_cover = mat("notebook_cover", (0.12, 0.33, 0.30), rough=0.7)
    m_left = mat("page_left", C_PAPER, rough=0.9)
    m_right = mat("page_right", C_PAPER, rough=0.9)
    m_edge = mat("page_edge", (0.86, 0.83, 0.76), rough=0.95)
    m_staple = mat("staple", C_METAL, rough=0.25, metal=1.0)
    cover = obj_from_bm("cover", cube((3.52, 2.12, 0.012), (0, 0, 0.006)), m_cover)
    bevel(cover, 0.004, 2)
    smooth(cover)
    planar_uv(cover, "Z")
    # стопки страниц (торцы)
    stackL = obj_from_bm("stackL", cube((1.68, 2.03, 0.02), (-0.86, 0, 0.02)), m_edge)
    stackR = obj_from_bm("stackR", cube((1.68, 2.03, 0.02), (0.86, 0, 0.02)), m_edge)
    for s in (stackL, stackR):
        bevel(s, 0.006, 2)
        smooth(s)
    left = page_mesh("PageLeft", -1.70, -0.02, -1, m_left)
    right = page_mesh("PageRight", 0.02, 1.70, 1, m_right)
    staples = []
    for y in (-0.5, 0.5):
        pts = [(0.0, y - 0.09, 0.0), (0.0, y - 0.09, 0.045), (0.0, y + 0.09, 0.045), (0.0, y + 0.09, 0.0)]
        st = obj_from_bm("staple", tube_along(pts, 0.006, 6), m_staple)
        smooth(st, 60)
        staples.append(st)
    body = join([cover, stackL, stackR] + staples, "NotebookBody")
    # страницы — отдельные узлы, чтобы Godot нашёл их по имени
    root = bpy.data.objects.new("Notebook", None)
    bpy.context.collection.objects.link(root)
    for o in (body, left, right):
        o.parent = root
    export([root], "notebook.glb")
    ANCHORS["notebook"] = {"page_w": 1.68, "page_h": 2.05, "right_page_x": [0.02, 1.70]}


# ================================================================== КАРАНДАШ


def build_pencil():
    reset()
    m_paint = mat("pencil_paint", C_YELLOW, rough=0.35)
    m_wood = mat("pencil_wood", (0.85, 0.66, 0.45), rough=0.8)
    m_lead = mat("pencil_lead", C_GRAPHITE, rough=0.4, metal=0.4)
    m_ferrule = mat("pencil_ferrule", C_BRASS, rough=0.3, metal=1.0)
    m_eraser = mat("pencil_eraser", C_PINK, rough=0.85)
    R = 0.042
    body = obj_from_bm("body", prism(6, R, 1.42, start=0.0, rot=math.pi / 6), m_paint)
    bevel(body, 0.004, 2, angle=50)
    smooth(body, 50)
    # заточка: шестигранник → конус
    bm = bmesh.new()
    ring = []
    for i in range(6):
        a = math.pi / 6 + TAU * i / 6
        ring.append(bm.verts.new((1.42, R * math.cos(a), R * math.sin(a))))
    mid = []
    for i in range(24):
        a = TAU * i / 24
        mid.append(bm.verts.new((1.66, 0.012 * math.cos(a), 0.012 * math.sin(a))))
    # соединяем 6-угольник с 24-угольником
    for i in range(24):
        a_i = (i * 6) // 24
        b_i = (((i + 1) % 24) * 6) // 24
        if a_i == b_i:
            bm.faces.new((ring[a_i], mid[(i + 1) % 24], mid[i]))
        else:
            bm.faces.new((ring[a_i], ring[b_i], mid[(i + 1) % 24], mid[i]))
    bm.faces.new(list(reversed(ring)))
    bm.faces.new(mid)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    wood = obj_from_bm("wood", bm, m_wood)
    smooth(wood, 30)
    lead = obj_from_bm("lead", lathe([(0.0122, 1.659), (0.0122, 1.66), (0.0, 1.735)], 24, axis="X"), m_lead)
    smooth(lead, 60)
    ferrule = obj_from_bm("ferrule", lathe([(0.0, -0.001), (0.044, -0.001), (0.045, -0.02), (0.043, -0.04), (0.045, -0.06), (0.044, -0.085), (0.0, -0.085)], 32, axis="X"), m_ferrule)
    smooth(ferrule, 40)
    eraser = obj_from_bm("eraser", lathe([(0.0, -0.08), (0.041, -0.08), (0.041, -0.13), (0.036, -0.155), (0.0, -0.16)], 32, axis="X"), m_eraser)
    smooth(eraser, 60)
    pencil = join([body, wood, lead, ferrule, eraser], "Pencil")
    # центр масс ~ середина
    set_origin(pencil, (0.78, 0, 0))
    pencil.location = (0, 0, 0)
    export([pencil], "pencil.glb")


# ================================================================== РУЧКИ / МАРКЕРЫ


def build_marker():
    reset()
    m_body = mat("marker_body", (0.95, 0.95, 0.93), rough=0.3)
    m_cap = mat("marker_cap", C_RED, rough=0.3)
    m_tip = mat("marker_tip", C_RED, rough=0.8)
    prof_body = [(0.0, 0.0), (0.06, 0.0), (0.072, 0.03), (0.075, 0.12), (0.075, 1.0), (0.07, 1.05), (0.055, 1.1), (0.045, 1.12)]
    body = obj_from_bm("body", lathe(prof_body, 40, axis="X"), m_body)
    smooth(body, 35)
    tip = obj_from_bm("tip", lathe([(0.03, 1.12), (0.03, 1.15), (0.022, 1.2), (0.0, 1.215)], 24, axis="X"), m_tip)
    smooth(tip, 50)
    cap_prof = [(0.0, 1.45), (0.07, 1.45), (0.082, 1.43), (0.084, 1.35), (0.084, 1.02), (0.08, 1.0), (0.077, 1.0)]
    cap = obj_from_bm("cap", lathe(cap_prof, 40, axis="X"), m_cap)
    smooth(cap, 35)
    clip = obj_from_bm("clip", cube((0.42, 0.03, 0.02), (1.2, 0.0, 0.095)), m_cap)
    bevel(clip, 0.008, 2)
    smooth(clip, 35)
    end = obj_from_bm("end", lathe([(0.0, -0.02), (0.06, -0.02), (0.062, 0.0)], 32, axis="X"), m_cap)
    smooth(end, 40)
    mk = join([body, tip, cap, clip, end], "Marker")
    set_origin(mk, (0.7, 0, 0))
    mk.location = (0, 0, 0)
    export([mk], "marker.glb")


def build_pen():
    reset()
    m_body = mat("pen_body", (0.15, 0.25, 0.65), rough=0.25, alpha=0.6)
    m_cap = mat("pen_cap", (0.10, 0.18, 0.55), rough=0.3)
    m_tip = mat("pen_tip", C_METAL, rough=0.2, metal=1.0)
    m_ink = mat("pen_ink", (0.10, 0.15, 0.5), rough=0.5)
    body = obj_from_bm("body", prism(6, 0.042, 1.15, start=0.0, rot=0.0), m_body)
    bevel(body, 0.006, 2, angle=50)
    smooth(body, 50)
    cone = obj_from_bm("cone", lathe([(0.036, 1.15), (0.03, 1.22), (0.014, 1.3), (0.008, 1.32)], 24, axis="X"), m_cap)
    smooth(cone, 40)
    tip = obj_from_bm("tip", lathe([(0.008, 1.32), (0.006, 1.345), (0.0, 1.352)], 16, axis="X"), m_tip)
    refill = obj_from_bm("refill", lathe([(0.0, 0.05), (0.012, 0.05), (0.012, 1.13), (0.0, 1.13)], 12, axis="X"), m_ink)
    endcap = obj_from_bm("endcap", lathe([(0.0, -0.06), (0.03, -0.06), (0.04, -0.02), (0.04, 0.02), (0.0, 0.02)], 24, axis="X"), m_cap)
    smooth(endcap, 40)
    pen = join([body, cone, tip, refill, endcap], "Pen")
    set_origin(pen, (0.65, 0, 0))
    pen.location = (0, 0, 0)
    export([pen], "pen.glb")


# ================================================================== ЛАСТИК / ТОЧИЛКА / ЛИНЕЙКА


def build_eraser():
    reset()
    m_rub = mat("eraser_rubber", (0.95, 0.93, 0.88), rough=0.9)
    m_sleeve = mat("eraser_sleeve", (0.18, 0.38, 0.78), rough=0.6)
    rub = obj_from_bm("rubber", cube((0.6, 0.24, 0.11), (0, 0, 0.055)), m_rub)
    bevel(rub, 0.03, 4, angle=30)
    smooth(rub, 30)
    sl = obj_from_bm("sleeve", cube((0.34, 0.25, 0.115), (0.12, 0, 0.0575)), m_sleeve)
    bevel(sl, 0.006, 2)
    smooth(sl, 30)
    box_uv(sl, 3.0)
    er = join([rub, sl], "Eraser")
    export([er], "eraser.glb")


def build_sharpener():
    reset()
    m_body = mat("sharpener_body", (0.80, 0.12, 0.18), rough=0.35)
    m_blade = mat("sharpener_blade", C_METAL, rough=0.2, metal=1.0)
    body = obj_from_bm("body", cube((0.26, 0.17, 0.14), (0, 0, 0.07)), m_body)
    bevel(body, 0.012, 3, angle=30)
    hole = obj_from_bm("cut", lathe([(0.0, -0.2), (0.045, -0.2), (0.045, -0.06), (0.0, 0.08)], 24, axis="X"), None)
    hole.location = (0.0, 0.0, 0.07)
    mod = body.modifiers.new("Bool", "BOOLEAN")
    mod.object = hole
    mod.operation = "DIFFERENCE"
    apply_mods(body)
    bpy.data.objects.remove(hole, do_unlink=True)
    smooth(body, 30)
    blade = obj_from_bm("blade", cube((0.17, 0.10, 0.006), (0.0, 0.0, 0.143)), m_blade)
    bevel(blade, 0.002, 1)
    screw = obj_from_bm("screw", lathe([(0.0, 0.16), (0.018, 0.16), (0.018, 0.168), (0.0, 0.17)], 16), m_blade)
    sh = join([body, blade, screw], "Sharpener")
    export([sh], "sharpener.glb")


def build_ruler():
    reset()
    m_ruler = mat("ruler", (0.85, 0.88, 0.90), rough=0.15, alpha=0.75)
    r = obj_from_bm("Ruler", cube((3.2, 0.36, 0.025), (0, 0, 0.0125)), m_ruler)
    bevel(r, 0.006, 2)
    smooth(r, 30)
    planar_uv(r, "Z")
    export([r], "ruler.glb")


# ================================================================== КРУЖКА


def build_mug():
    reset()
    m_mug = mat("mug_glaze", (0.85, 0.30, 0.22), rough=0.18)
    m_inner = mat("mug_inner", (0.95, 0.93, 0.88), rough=0.15)
    m_cocoa = mat("mug_cocoa", (0.20, 0.10, 0.05), rough=0.08)
    outer = [(0.0, 0.0), (0.36, 0.0), (0.39, 0.02), (0.41, 0.08), (0.42, 0.5), (0.425, 0.88), (0.42, 0.92)]
    inner = [(0.42, 0.92), (0.40, 0.935), (0.38, 0.92), (0.375, 0.5), (0.37, 0.12), (0.34, 0.07), (0.0, 0.07)]
    o = obj_from_bm("outer", lathe(outer, 64), m_mug)
    i = obj_from_bm("inner", lathe(inner, 64), m_inner)
    for ob in (o, i):
        smooth(ob, 40)
    cocoa = obj_from_bm("cocoa", lathe([(0.0, 0.74), (0.376, 0.74)], 64), m_cocoa)
    # ручка
    pts = []
    for k in range(17):
        a = -math.pi / 2 + math.pi * k / 16
        pts.append((0.40 + 0.22 * math.cos(a), 0.0, 0.48 + 0.25 * math.sin(a)))
    handle = obj_from_bm("handle", tube_along(pts, 0.045, 14), m_mug)
    subsurf(handle, 1)
    smooth(handle, 60)
    mug = join([o, i, cocoa, handle], "Mug")
    export([mug], "mug.glb")


# ================================================================== ЛАМПА


def build_lamp(base_pos, target):
    reset()
    m_metal = mat("lamp_metal", (0.12, 0.30, 0.26), rough=0.3, metal=0.6)
    m_joint = mat("lamp_joint", C_METAL, rough=0.25, metal=1.0)
    m_inner = mat("lamp_shade_inner", (0.95, 0.9, 0.8), rough=0.4)
    m_bulb = mat("lamp_bulb", (1.0, 0.85, 0.6), rough=0.1, emission=(1.0, 0.8, 0.5))
    B = Vector(base_pos)
    base = obj_from_bm("base", lathe([(0.0, 0.0), (0.55, 0.0), (0.58, 0.03), (0.56, 0.09), (0.45, 0.13), (0.12, 0.16), (0.0, 0.16)], 64), m_metal)
    base.location = B
    apply_transform(base)
    smooth(base, 35)
    T = Vector(target)
    flat = (T - B)
    flat.z = 0
    flat.normalize()
    elbow = B + Vector((0, 0, 0.16)) + flat * 0.9 + Vector((0, 0, 3.0))
    head = elbow + flat * 2.0 + Vector((0, 0, 0.6))
    shoulder = B + Vector((0, 0, 0.2))
    arm1 = obj_from_bm("arm1", tube_along([shoulder, elbow], 0.055, 16), m_metal)
    arm2 = obj_from_bm("arm2", tube_along([elbow, head], 0.05, 16), m_metal)
    for a in (arm1, arm2):
        smooth(a, 50)
    joints = []
    for p in (shoulder, elbow, head):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.09)
        for v in bm.verts:
            v.co += p
        j = obj_from_bm("joint", bm, m_joint)
        smooth(j, 80)
        joints.append(j)
    # абажур: конус вдоль направления на цель
    d = (T - head).normalized()
    shade_prof_out = [(0.10, -0.05), (0.14, 0.0), (0.22, 0.12), (0.36, 0.32), (0.48, 0.55), (0.5, 0.57)]
    shade_prof_in = [(0.5, 0.57), (0.47, 0.55), (0.35, 0.33), (0.21, 0.14), (0.12, 0.02), (0.0, 0.02)]
    rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
    so = obj_from_bm("shade", lathe(shade_prof_out, 64), m_metal)
    si = obj_from_bm("shade_in", lathe(shade_prof_in, 64), m_inner)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.13)
    for v in bm.verts:
        v.co += Vector((0, 0, 0.2))
    bulb = obj_from_bm("bulb", bm, m_bulb)
    for o in (so, si, bulb):
        o.data.transform(rot)
        o.data.transform(Matrix.Translation(head))
        smooth(o, 50)
    lamp = join([base, arm1, arm2, so, si] + joints, "Lamp")
    bulb.name = "LampBulb"
    bulb.parent = lamp
    export([lamp], "lamp.glb")
    bulb_pos = head + d * 0.2
    ANCHORS["lamp"] = {"bulb": to_godot(bulb_pos), "dir": to_godot(d), "base": to_godot(B), "target": to_godot(T)}


# ================================================================== БУДИЛЬНИК


def build_clock():
    reset()
    m_body = mat("clock_body", (0.75, 0.15, 0.14), rough=0.25, metal=0.3)
    m_chrome = mat("clock_chrome", C_METAL, rough=0.15, metal=1.0)
    m_face = mat("clock_face", (0.96, 0.94, 0.88), rough=0.6)
    m_glass = mat("clock_glass", (0.9, 0.95, 1.0), rough=0.02, alpha=0.18)
    m_hand = mat("clock_hand", C_BLACK, rough=0.4)
    R = 0.42
    zc = R + 0.08
    # корпус: вращение вокруг оси -Y (лицом к камере)
    prof = [(0.0, -0.13), (R - 0.03, -0.13), (R, -0.10), (R + 0.01, 0.0), (R, 0.10), (R - 0.03, 0.13), (0.0, 0.13)]
    bm = lathe(prof, 64)
    body = obj_from_bm("body", bm, m_body)
    body.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    body.data.transform(Matrix.Translation((0, 0, zc)))
    smooth(body, 40)
    bez = obj_from_bm("bezel", lathe([(R - 0.06, 0.135), (R - 0.01, 0.135), (R - 0.005, 0.15), (R - 0.05, 0.155)], 64), m_chrome)
    bez.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    bez.data.transform(Matrix.Translation((0, 0, zc)))
    smooth(bez, 50)
    parts = [body, bez]
    for s in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.17)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context="VERTS")
        bell = obj_from_bm("bell", bm, m_chrome)
        bell.rotation_euler = (0, s * math.radians(38), 0)
        bell.location = (s * 0.27, 0, zc + 0.36)
        apply_transform(bell)
        smooth(bell, 60)
        parts.append(bell)
        foot = obj_from_bm("foot", tube_along([(s * 0.18, 0, zc - 0.32), (s * 0.27, 0, 0.03)], 0.025, 10), m_chrome)
        parts.append(foot)
        ball = bmesh.new()
        bmesh.ops.create_uvsphere(ball, u_segments=12, v_segments=8, radius=0.04)
        for v in ball.verts:
            v.co += Vector((s * 0.27, 0, 0.035))
        parts.append(obj_from_bm("ball", ball, m_chrome))
    handle = obj_from_bm("handle", tube_along([(-0.18, 0, zc + 0.36), (-0.12, 0, zc + 0.52), (0.12, 0, zc + 0.52), (0.18, 0, zc + 0.36)], 0.02, 10), m_chrome)
    parts.append(handle)
    hammer = obj_from_bm("hammer", tube_along([(0, 0, zc + R - 0.02), (0, 0, zc + R + 0.14)], 0.015, 8), m_chrome)
    parts.append(hammer)
    clock = join(parts, "Clock")
    # циферблат (UV 0..1)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    center = bm.verts.new((0, -0.134, zc))
    ring = [bm.verts.new(((R - 0.06) * math.cos(TAU * i / 64), -0.134, zc + (R - 0.06) * math.sin(TAU * i / 64))) for i in range(64)]
    for i in range(64):
        f = bm.faces.new((center, ring[(i + 1) % 64], ring[i]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (0.5 + c.x / (2 * (R - 0.06)), 0.5 + (c.z - zc) / (2 * (R - 0.06)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    face = obj_from_bm("ClockFace", bm, m_face)
    for f in face.data.polygons:
        pass
    face.parent = clock
    # стекло
    gl = obj_from_bm("ClockGlass", lathe([(0.0, 0.152), (R - 0.05, 0.147)], 48), m_glass)
    gl.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    gl.data.transform(Matrix.Translation((0, 0, zc)))
    gl.parent = clock
    # стрелки (origin в центре)
    for name, length, width in (("HandHour", 0.2, 0.03), ("HandMinute", 0.3, 0.018)):
        h = obj_from_bm(name, cube((width, 0.008, length), (0, 0, length / 2 - 0.03)), m_hand)
        h.data.transform(Matrix.Translation((0, -0.141, 0)))
        h.location = (0, 0, zc)
        h.parent = clock
    export([clock], "clock.glb")
    ANCHORS["clock"] = {"face_center_y": zc}


# ================================================================== ЗАЖИМ-ПОДСТАВКА


def build_clip():
    reset()
    m_black = mat("clip_black", C_BLACK, rough=0.18, metal=0.5)
    m_wire = mat("clip_wire", C_METAL, rough=0.12, metal=1.0)
    W = 0.56
    # профиль: треугольник с губками сверху
    prof = [(-0.17, 0.0), (0.17, 0.0), (0.035, 0.2), (0.012, 0.215), (-0.012, 0.215), (-0.035, 0.2)]
    bm = bmesh.new()
    a = [bm.verts.new((-W / 2, y, z)) for y, z in prof]
    b = [bm.verts.new((W / 2, y, z)) for y, z in prof]
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = obj_from_bm("ClipBody", bm, m_black)
    bevel(body, 0.012, 3, angle=25)
    smooth(body, 35)
    wires = []
    for s in (-1, 1):
        # дужки сложены вниз и работают как ножки подставки
        pts = [(-W / 2 + 0.07, s * 0.035, 0.205), (-W / 2 + 0.07, s * 0.12, 0.16), (-W / 2 + 0.075, s * 0.36, 0.016),
               (W / 2 - 0.075, s * 0.36, 0.016), (W / 2 - 0.07, s * 0.12, 0.16), (W / 2 - 0.07, s * 0.035, 0.205)]
        w = obj_from_bm("wire", tube_along(pts, 0.012, 8), m_wire)
        smooth(w, 70)
        wires.append(w)
    clip = join([body] + wires, "Clip")
    export([clip], "clip.glb")
    ANCHORS["clip"] = {"slot_height": 0.215, "width": W, "depth": 0.34}


# ================================================================== КОМКИ БУМАГИ


def build_paper_balls():
    reset()
    m = mat("paper_crumpled", C_PAPER, rough=0.95)
    objs = []
    for k in range(3):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=4, radius=0.26 + 0.04 * k)
        seed = Vector((k * 13.1, k * 7.7, k * 3.3))
        for v in bm.verts:
            p = v.co.normalized()
            # крупные складки + мелкие заломы
            d = 0.06 * noise.noise(p * 2.2 + seed) + 0.035 * noise.noise(p * 5.0 + seed)
            cell = noise.voronoi(p * 3.0 + seed)[0][0]
            d -= 0.05 * cell
            v.co = v.co + p * d
        ob = obj_from_bm(f"PaperBall{k}", bm, m)
        smooth(ob, 18)
        ob.location = (k * 1.0, 0, 0)
        objs.append(ob)
    for o in objs:
        o.location = (0, 0, 0)
        export([o], f"paperball{objs.index(o)}.glb")


# ================================================================== ЧЕРНИЛЬНИЦА


def build_inkbottle():
    reset()
    m_glass = mat("ink_glass", (0.85, 0.92, 0.95), rough=0.03, alpha=0.35)
    m_ink = mat("ink_liquid", (0.05, 0.07, 0.25), rough=0.05)
    m_cap = mat("ink_cap", C_BLACK, rough=0.3)
    m_label = mat("ink_label", (0.92, 0.86, 0.70), rough=0.8)
    body = obj_from_bm("glass", lathe([(0.0, 0.0), (0.3, 0.0), (0.33, 0.04), (0.34, 0.36), (0.30, 0.44), (0.12, 0.5), (0.11, 0.6), (0.0, 0.6)], 6 * 8), m_glass)
    smooth(body, 30)
    ink = obj_from_bm("ink", lathe([(0.0, 0.02), (0.31, 0.02), (0.32, 0.25), (0.0, 0.25)], 48), m_ink)
    label = obj_from_bm("label", lathe([(0.345, 0.12), (0.345, 0.28)], 48), m_label)
    cap = obj_from_bm("cap", lathe([(0.0, 0.58), (0.13, 0.58), (0.135, 0.72), (0.12, 0.74), (0.0, 0.74)], 32), m_cap)
    smooth(cap, 40)
    b = join([body, ink, label, cap], "InkBottle")
    export([b], "inkbottle.glb")


# ================================================================== КНИГИ


def build_books():
    reset()
    cols = [(0.55, 0.12, 0.12), (0.12, 0.25, 0.45), (0.25, 0.40, 0.22), (0.45, 0.32, 0.15)]
    m_pages = mat("book_pages", (0.92, 0.88, 0.78), rough=0.9)
    objs = []
    z = 0.0
    for k, (w, d, h) in enumerate(((2.4, 1.7, 0.32), (2.2, 1.6, 0.26), (2.5, 1.75, 0.38), (2.0, 1.5, 0.22))):
        m_cov = mat(f"book_cover{k}", cols[k], rough=0.6)
        cov = obj_from_bm("cover", cube((w, d, h), (0, 0, z + h / 2)), m_cov)
        bevel(cov, 0.03, 3)
        smooth(cov, 35)
        pages = obj_from_bm("pages", cube((w - 0.06, d - 0.08, h - 0.05), (0.04, 0, z + h / 2)), m_pages)
        bk = join([cov, pages], f"Book{k}")
        bk.rotation_euler = (0, 0, math.radians(random.uniform(-9, 9)))
        apply_transform(bk)
        objs.append(bk)
        z += h
    books = join(objs, "Books")
    export([books], "books.glb")


# ================================================================== ОКНО


def build_window():
    reset()
    m_frame = mat("window_frame", (0.80, 0.78, 0.72), rough=0.5)
    m_sill = mat("window_sill", (0.86, 0.84, 0.80), rough=0.35)
    W, H, T = 7.0, 6.0, 0.25
    parts = []
    for sx, sz, lx, lz in ((W, T, 0, H / 2), (W, T, 0, -H / 2), (T, H, W / 2, 0), (T, H, -W / 2, 0), (0.14, H, 0, 0), (W, 0.14, 0, 0.6)):
        p = obj_from_bm("frame", cube((sx, 0.3, sz), (lx, 0, lz)), m_frame)
        bevel(p, 0.02, 2)
        smooth(p)
        parts.append(p)
    sill = obj_from_bm("sill", cube((W + 1.0, 1.2, 0.18), (0, -0.5, -H / 2 - 0.2)), m_sill)
    bevel(sill, 0.04, 3)
    smooth(sill)
    parts.append(sill)
    win = join(parts, "Window")
    export([win], "window.glb")


# ================================================================== НОЖНИЦЫ


def build_scissors():
    reset()
    m_blade = mat("scissor_blade", C_METAL, rough=0.12, metal=1.0)
    m_handle = mat("scissor_handle", (0.95, 0.55, 0.10), rough=0.35)
    objs = []
    for s in (-1, 1):
        bm = bmesh.new()
        outline = [(0.0, 0.0), (0.9, s * 0.02), (1.25, s * 0.0), (0.9, s * 0.08), (0.2, s * 0.1), (0.0, s * 0.07)]
        top = [bm.verts.new((x, y, 0.012 * s)) for x, y in outline]
        bot = [bm.verts.new((x, y, 0.012 * s - 0.018)) for x, y in outline]
        n = len(outline)
        bm.faces.new(top)
        bm.faces.new(list(reversed(bot)))
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((top[i], bot[i], bot[j], top[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        blade = obj_from_bm("blade", bm, m_blade)
        smooth(blade, 30)
        ring_pts = []
        for k in range(24):
            a = TAU * k / 24
            ring_pts.append((-0.42 + 0.2 * math.cos(a), s * (0.2 + 0.13 * math.sin(a)), 0.0))
        ring = obj_from_bm("ring", tube_along(ring_pts, 0.045, 12, closed=True), m_handle)
        arm = obj_from_bm("arm", tube_along([(-0.24, s * 0.16, 0.0), (0.02, s * 0.04, 0.0)], 0.045, 12), m_handle)
        for o in (ring, arm):
            smooth(o, 60)
        half = join([blade, ring, arm], "ScissorUpper" if s > 0 else "ScissorLower")
        objs.append(half)
    root = bpy.data.objects.new("Scissors", None)
    bpy.context.collection.objects.link(root)
    for o in objs:
        o.parent = root
    pivot = bmesh.new()
    bmesh.ops.create_cone(pivot, cap_ends=True, segments=16, radius1=0.035, radius2=0.035, depth=0.06)
    pv = obj_from_bm("pivot", pivot, m_blade)
    pv.parent = root
    export([root], "scissors.glb")


# ================================================================== RUN

if __name__ == "__main__":
    build_desk()
    build_notebook()
    build_pencil()
    build_marker()
    build_pen()
    build_eraser()
    build_sharpener()
    build_ruler()
    build_mug()
    build_lamp(base_pos=(-3.4, 3.6, 0.0), target=(0.3, -0.6, 0.0))
    build_clock()
    build_clip()
    build_paper_balls()
    build_inkbottle()
    build_books()
    build_window()
    build_scissors()
    with open(os.path.join(OUT, "anchors.json"), "w", encoding="utf-8") as f:
        json.dump(ANCHORS, f, ensure_ascii=False, indent=2)
    print("done", OUT)
