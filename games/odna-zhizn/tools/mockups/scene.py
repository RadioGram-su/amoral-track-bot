"""
Мокапы трёх стилей «Одной жизни»: одна сцена долины, три способа рисовки.

    python3 tools/mockups/scene.py <out_dir> [watercolor|paper|lacquer|all]

watercolor — 3D-рендер цвета + отдельный проход карандашных линий (Freestyle);
             акварельная обработка делается в post.py.
paper      — бумажный театр: слои вырезанной бумаги, тени между слоями.
lacquer    — лаковая миниатюра: чёрный лак, темпера, золотые линии и орнамент.
"""
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = os.path.abspath(argv[0] if argv else "mock")
WHICH = argv[1] if len(argv) > 1 else "all"
os.makedirs(OUT, exist_ok=True)
RES = (720, 1280)
TAU = math.tau


# ------------------------------------------------------------ общее

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_mat(name, color, rough=0.8, metal=0.0, sss=0.0, emission=None, estr=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sss > 0:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.05, 0.04, 0.03)
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = estr
    if coat > 0:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.05
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def add_noise_bump(m, scale=60.0, strength=0.25):
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])


def obj(name, bm, m=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if m is not None:
        me.materials.append(m)
    return o


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def sphere(r, loc, m, seg=24, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(loc)
    o = obj("sphere", bm, m)
    smooth(o)
    return o


def cyl(r1, r2, a, b, m, seg=16):
    """Конус/цилиндр от точки a до точки b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d.length)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    for v in bm.verts:
        v.co = rot @ (v.co + Vector((0, 0, d.length / 2))) + a
    o = obj("cyl", bm, m)
    smooth(o)
    return o


def box(size, loc, m, rot_z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    R = Matrix.Rotation(rot_z, 3, "Z")
    for v in bm.verts:
        v.co = R @ Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(loc)
    return obj("box", bm, m)


def camera(loc, target, lens=32, ortho=None):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.sensor_fit = "VERTICAL"
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    bpy.context.scene.camera = cam
    return cam


def light(kind, loc, target, energy, color=(1, 1, 1), size=1.0, spot=None):
    ld = bpy.data.lights.new(kind, kind)
    ld.energy = energy
    ld.color = color
    if kind == "SUN":
        ld.angle = math.radians(size)
    elif kind in ("AREA",):
        ld.size = size
    else:
        ld.shadow_soft_size = size
    if spot and kind == "SPOT":
        ld.spot_size = math.radians(spot)
        ld.spot_blend = 0.6
    o = bpy.data.objects.new(kind, ld)
    bpy.context.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def world(color, strength=1.0):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def render(path, samples=48, transparent=False, view="AgX", look=None, exposure=0.0):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    try:
        s.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    s.render.resolution_x, s.render.resolution_y = RES
    s.render.film_transparent = transparent
    s.view_settings.view_transform = view
    if look:
        s.view_settings.look = look
    s.view_settings.exposure = exposure
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def freestyle(color, thickness, noise_amp=1.5, noise_freq=30.0, crease=True, alpha=1.0):
    s = bpy.context.scene
    s.render.use_freestyle = True
    s.render.line_thickness_mode = "ABSOLUTE"
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    ls_set = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("Lines")
    ls_set.select_by_visibility = True
    ls_set.visibility = "VISIBLE"
    ls_set.select_silhouette = True
    ls_set.select_border = True
    ls_set.select_crease = crease
    ls_set.select_external_contour = True
    fs.crease_angle = math.radians(120)
    st = ls_set.linestyle
    if st is None:
        st = bpy.data.linestyles.new("Pencil")
        ls_set.linestyle = st
    st.color = color
    st.alpha = alpha
    st.thickness = thickness
    st.caps = "ROUND"
    st.chaining = "PLAIN"
    gm = st.geometry_modifiers.new(name="Wobble", type="PERLIN_NOISE_1D")
    gm.amplitude = noise_amp
    gm.frequency = noise_freq
    tm = st.thickness_modifiers.new(name="Taper", type="ALONG_STROKE")
    tm.mapping = "CURVE"
    tm.influence = 0.7
    return st


# ------------------------------------------------------------ рельеф долины

def H(x, y):
    """Высота земли."""
    h = 0.35 * noise.noise(Vector((x * 0.08, y * 0.08, 0.3)))
    h += 1.9 * math.exp(-((x + 4.6) ** 2 + (y - 12.5) ** 2) / 22.0)   # холм с дубом
    h += 1.0 * math.exp(-((x - 7.0) ** 2 + (y - 16.0) ** 2) / 40.0)
    h += 0.04 * y if y > 14 else 0.0                                    # даль поднимается
    sy = 5.2 + 0.7 * math.sin(x * 0.35)                                 # русло ручья
    h -= 0.55 * math.exp(-((y - sy) ** 2) / 0.9)
    return h


def stream_y(x):
    return 5.2 + 0.7 * math.sin(x * 0.35)


def path_pts():
    """Тропинка: от зрителя к дому, через мост."""
    pts = []
    for i in range(60):
        t = i / 59
        y = -4 + t * 14.0
        x = 0.4 + 1.6 * math.sin(t * 2.6) + t * 1.2
        pts.append((x, y))
    return pts


def ribbon(points, width, zoff, m, hfunc=H, name="ribbon"):
    bm = bmesh.new()
    left, right = [], []
    for i, (x, y) in enumerate(points):
        if i < len(points) - 1:
            dx, dy = points[i + 1][0] - x, points[i + 1][1] - y
        else:
            dx, dy = x - points[i - 1][0], y - points[i - 1][1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = width * (0.85 + 0.15 * math.sin(i * 0.7))
        for side, arr in ((1, left), (-1, right)):
            px, py = x + nx * w * side, y + ny * w * side
            arr.append(bm.verts.new((px, py, hfunc(px, py) + zoff)))
    for i in range(len(points) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    o = obj(name, bm, m)
    smooth(o)
    return o


def ground(m, size=90, n=150):
    bm = bmesh.new()
    verts = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x = -size / 2 + size * i / n
            y = -10 + size * j / n
            row.append(bm.verts.new((x, y, H(x, y))))
        verts.append(row)
    for j in range(n):
        for i in range(n):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    o = obj("Ground", bm, m)
    smooth(o)
    return o


# ------------------------------------------------------------ персонажи

def person(base, facing, height, mats, age="adult", stride=0.0, arm_swing=0.0, hold=None):
    """Стилизованная фигура. mats: skin, cloth, cloth2, hair, shoe."""
    bx, by = base
    bz = H(bx, by)
    s = height / 1.75
    head_r = 0.13 * s * (1.35 if age == "child" else 1.0)
    parts = []
    hunch = 0.22 if age == "elder" else 0.0
    R = Matrix.Rotation(facing, 4, "Z")
    O = Vector((bx, by, bz))

    def P(x, y, z):
        return O + (R @ Vector((x, y, z)))

    leg_len = 0.82 * s * (0.85 if age == "child" else 1.0)
    hip = 0.86 * s * (0.85 if age == "child" else 1.0)
    for side in (-1, 1):
        sw = stride * side
        foot = P(0.09 * s * side, sw * 0.32 * s, 0.05)
        knee = P(0.09 * s * side, sw * 0.12 * s + 0.03, hip * 0.52)
        top = P(0.09 * s * side, 0.0, hip)
        parts.append(cyl(0.065 * s, 0.055 * s, top, knee, mats["cloth2"]))
        parts.append(cyl(0.055 * s, 0.045 * s, knee, foot, mats["cloth2"]))
        parts.append(sphere(0.07 * s, foot + Vector((0, 0, -0.01)), mats["shoe"], 12, (0.9, 1.5, 0.6)))
    chest_h = hip + 0.55 * s * (0.8 if age == "child" else 1.0)
    neck = P(0, hunch * 0.6, chest_h - hunch * 0.15)
    # туника колоколом
    parts.append(cyl(0.25 * s, 0.17 * s, P(0, 0, hip - 0.18 * s), neck, mats["cloth"], 20))
    parts.append(cyl(0.255 * s, 0.25 * s, P(0, 0, hip - 0.04 * s), P(0, 0.0, hip + 0.02 * s), mats["cloth2"], 20))
    head_c = neck + Vector((0, 0, head_r * 1.05)) + (R @ Vector((0, hunch * 0.3, 0)))
    parts.append(sphere(head_r, head_c, mats["skin"], 24, (0.95, 0.95, 1.05)))
    parts.append(sphere(head_r * 1.06, head_c + (R @ Vector((0, 0.025, 0.03))), mats["hair"], 24, (1.0, 1.0, 0.8)))
    if age == "elder":
        parts.append(sphere(head_r * 0.7, head_c + (R @ Vector((0, -head_r * 0.75, -head_r * 0.5))), mats["hair"], 16, (1.0, 0.7, 1.1)))
    # глаза
    for side in (-1, 1):
        parts.append(sphere(head_r * 0.11, head_c + (R @ Vector((side * head_r * 0.38, -head_r * 0.9, head_r * 0.08))), mats["shoe"], 8))
    # руки
    sh = neck + Vector((0, 0, -0.06 * s))
    for side in (-1, 1):
        shoulder = sh + (R @ Vector((0.2 * s * side, 0, 0)))
        sw = -arm_swing * side
        if hold is not None and side == hold[0]:
            hand = Vector(hold[1])
        else:
            hand = shoulder + (R @ Vector((0.08 * s * side, sw * 0.35 * s, -0.62 * s)))
        elbow = shoulder.lerp(hand, 0.5) + (R @ Vector((0.03 * side, 0.04, 0)))
        parts.append(cyl(0.055 * s, 0.05 * s, shoulder, elbow, mats["cloth"]))
        parts.append(cyl(0.05 * s, 0.04 * s, elbow, hand, mats["skin"]))
        parts.append(sphere(0.05 * s, hand, mats["skin"], 10))
    if age == "elder":
        hand = sh + (R @ Vector((0.28 * s, -0.25 * s, -0.55 * s)))
        parts.append(cyl(0.022, 0.02, hand + Vector((0, 0, 0.15)), Vector((hand.x, hand.y, bz)), mats["shoe"], 8))
    return parts, head_c


# ------------------------------------------------------------ постройки и растения

def house(loc, rot, mats):
    x, y = loc
    z = H(x, y) - 0.2
    parts = []
    W, D, Hh = 4.2, 3.4, 2.6
    parts.append(box((W, D, Hh), (x, y, z + Hh / 2), mats["wall"], rot))
    R = Matrix.Rotation(rot, 3, "Z")
    # двускатная крыша
    bm = bmesh.new()
    pts = [(-W / 2 - 0.35, -D / 2 - 0.3, Hh), (W / 2 + 0.35, -D / 2 - 0.3, Hh), (W / 2 + 0.35, 0, Hh + 1.7), (-W / 2 - 0.35, 0, Hh + 1.7),
           (-W / 2 - 0.35, D / 2 + 0.3, Hh), (W / 2 + 0.35, D / 2 + 0.3, Hh)]
    v = [bm.verts.new(R @ Vector(p) + Vector((x, y, z))) for p in pts]
    bm.faces.new((v[0], v[1], v[2], v[3]))
    bm.faces.new((v[3], v[2], v[5], v[4]))
    bm.faces.new((v[0], v[3], v[4]))
    bm.faces.new((v[1], v[5], v[2]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.15)
    parts.append(obj("roof", bm, mats["roof"]))
    # фронтоны
    bm = bmesh.new()
    for sx in (-1, 1):
        a = bm.verts.new(R @ Vector((sx * W / 2, -D / 2, Hh)) + Vector((x, y, z)))
        b = bm.verts.new(R @ Vector((sx * W / 2, D / 2, Hh)) + Vector((x, y, z)))
        c = bm.verts.new(R @ Vector((sx * W / 2, 0, Hh + 1.6)) + Vector((x, y, z)))
        bm.faces.new((a, b, c))
    parts.append(obj("gable", bm, mats["wall"]))
    parts.append(box((0.5, 0.5, 1.6), (x + (R @ Vector((1.0, 0.6, 0))).x, y + (R @ Vector((1.0, 0.6, 0))).y, z + Hh + 1.2), mats["stone"], rot))
    door = R @ Vector((0.6, -D / 2 - 0.03, 0))
    parts.append(box((0.8, 0.08, 1.5), (x + door.x, y + door.y, z + 0.95), mats["door"], rot))
    for wx in (-1.3,):
        w = R @ Vector((wx, -D / 2 - 0.03, 0))
        parts.append(box((0.8, 0.08, 0.7), (x + w.x, y + w.y, z + 1.55), mats["window"], rot))
    return parts


def oak(loc, mats, scale=1.0, seed=1):
    x, y = loc
    z = H(x, y) - 0.1
    parts = []
    s = scale
    parts.append(cyl(0.55 * s, 0.32 * s, (x, y, z), (x + 0.2 * s, y, z + 3.2 * s), mats["bark"], 14))
    random.seed(seed)
    for k in range(5):
        a = TAU * k / 5 + 0.4
        end = (x + math.cos(a) * 2.2 * s, y + math.sin(a) * 1.4 * s, z + (4.2 + random.uniform(-0.4, 0.6)) * s)
        parts.append(cyl(0.26 * s, 0.1 * s, (x + 0.2 * s, y, z + 3.0 * s), end, mats["bark"], 10))
    blobs = []
    for k in range(14):
        a = random.uniform(0, TAU)
        r = random.uniform(0.3, 2.6) * s
        c = (x + math.cos(a) * r, y + math.sin(a) * r * 0.7, z + (4.8 + random.uniform(-1.0, 1.6)) * s)
        rr = random.uniform(1.3, 2.0) * s
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rr)
        for v in bm.verts:
            p = v.co.normalized()
            v.co += p * (0.25 * rr * noise.noise(p * 2.5 + Vector((k, seed, 0))))
            v.co += Vector(c)
        o = obj("leaf", bm, mats["leaves"])
        smooth(o)
        parts.append(o)
    return parts


def pine(loc, mats, h=4.0):
    x, y = loc
    z = H(x, y)
    parts = [cyl(0.15, 0.1, (x, y, z), (x, y, z + 0.8), mats["bark"], 8)]
    for k in range(3):
        parts.append(cyl(1.2 * h / 4 * (1 - k * 0.22), 0.0, (x, y, z + 0.6 + k * h * 0.22), (x, y, z + 0.6 + k * h * 0.22 + h * 0.45), mats["pine"], 12))
    return parts


def bridge(mats):
    x0 = 1.95
    parts = []
    for k in range(9):
        yy = stream_y(x0) - 1.2 + k * 0.3
        zz = H(x0, stream_y(x0) - 1.4) + 0.35 + 0.25 * math.sin(math.pi * k / 8)
        parts.append(box((1.7, 0.26, 0.08), (x0, yy, zz), mats["plank"], 0.05))
    for sx in (-0.85, 0.85):
        for yy in (-1.25, 1.25):
            p = (x0 + sx, stream_y(x0) + yy)
            parts.append(cyl(0.06, 0.06, (p[0], p[1], H(*p) - 0.3), (p[0], p[1], H(*p) + 0.95), mats["plank"], 8))
        pts = []
        for k in range(9):
            yy = stream_y(x0) - 1.25 + k * 2.5 / 8
            pts.append((x0 + sx, yy, H(x0, stream_y(x0) - 1.4) + 1.15 + 0.25 * math.sin(math.pi * k / 8)))
        for a, b in zip(pts, pts[1:]):
            parts.append(cyl(0.04, 0.04, a, b, mats["plank"], 6))
    return parts


def build_valley(mats):
    parts = {"ground": [], "chars": []}
    parts["ground"].append(ground(mats["grass"]))
    parts["ground"].append(ribbon(path_pts(), 0.55, 0.03, mats["path"], name="Path"))
    water = []
    for i in range(80):
        x = -30 + i * 0.75
        water.append((x, stream_y(x)))
    parts["ground"].append(ribbon(water, 0.75, 0.0, mats["water"], hfunc=lambda x, y: H(x, stream_y(x)) + 0.32, name="Water"))
    world_objs = []
    world_objs += house((4.6, 10.6), math.radians(-12), mats)
    world_objs += oak((-4.6, 12.6), mats, 1.0, 3)
    world_objs += bridge(mats)
    random.seed(11)
    for k in range(9):
        x = random.uniform(-16, 16)
        y = random.uniform(16, 30)
        if abs(x) < 3 and y < 20:
            continue
        world_objs += pine((x, y), mats, random.uniform(3.0, 5.5))
    # гора
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=64, radius1=36, radius2=0.5, depth=30)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    for v in bm.verts:
        p = v.co
        v.co += p.normalized() * 2.2 * noise.noise(p * 0.08)
        v.co += Vector((0, 75, 15))
    mtn = obj("Mountain", bm, mats["mountain"])
    smooth(mtn)
    world_objs.append(mtn)
    # забор
    for k in range(7):
        x = 1.6 + k * 0.9
        y = 8.0 + k * 0.05
        world_objs.append(cyl(0.05, 0.045, (x, y, H(x, y) - 0.1), (x, y, H(x, y) + 0.8), mats["plank"], 6))
    world_objs.append(cyl(0.035, 0.035, (1.6, 8.0, H(1.6, 8.0) + 0.6), (7.0, 8.3, H(7.0, 8.3) + 0.6), mats["plank"], 6))
    # кусты, камни, цветы
    random.seed(5)
    for k in range(70):
        x = random.uniform(-9, 11)
        y = random.uniform(-3.5, 14)
        if abs(y - stream_y(x)) < 1.1:
            continue
        r = random.uniform(0.12, 0.35)
        world_objs.append(sphere(r, (x, y, H(x, y) + r * 0.3), mats["bush"], 12, (1.2, 1.0, 0.8)))
        if random.random() < 0.35:
            world_objs.append(sphere(0.06, (x + 0.15, y - 0.1, H(x, y) + r * 0.9), random.choice([mats["flower1"], mats["flower2"]]), 8))
    # скамейка и старик у дома
    bx, by = 2.7, 8.7
    world_objs.append(box((1.3, 0.38, 0.07), (bx, by, H(bx, by) + 0.48), mats["plank"], math.radians(-10)))
    for sx in (-0.5, 0.5):
        world_objs.append(box((0.07, 0.36, 0.48), (bx + sx, by, H(bx, by) + 0.24), mats["plank"], math.radians(-10)))
    elder, _ = person((bx + 0.1, by - 0.05), math.radians(-20), 1.62, mats["elder"], age="elder", stride=0.0)
    parts["chars"] += elder
    # герой (взрослый) и ребёнок держатся за руки
    hx, hy = 0.9, -0.2
    hero, hero_head = person((hx, hy), math.radians(-28), 1.78, mats["hero"], stride=0.8, arm_swing=0.6,
                             hold=(-1, (hx - 0.42, hy + 0.05, H(hx, hy) + 0.78)))
    kid, kid_head = person((hx - 0.85, hy + 0.12), math.radians(-35), 1.08, mats["kid"], age="child", stride=-0.9, arm_swing=0.7,
                           hold=(1, (hx - 0.45, hy + 0.06, H(hx, hy) + 0.76)))
    parts["chars"] += hero + kid
    parts["world"] = world_objs
    # дым из трубы
    smoke = []
    for k in range(6):
        smoke.append(sphere(0.35 + k * 0.12, (5.4 + k * 0.25, 11.6 + k * 0.1, H(4.6, 10.6) + 4.3 + k * 0.55), mats["smoke"], 16))
    parts["smoke"] = smoke
    parts["hero_pos"] = (hx, hy, H(hx, hy) + 1.0)
    return parts


CAM_LOC = (0.2, -15.5, 5.2)
CAM_TGT = (1.0, 9.0, 3.2)


# ------------------------------------------------------------ СТИЛЬ 1: АКВАРЕЛЬ

def watercolor():
    reset()
    C = lambda *c: tuple(c)
    mats = {
        "grass": new_mat("grass", C(0.38, 0.55, 0.22), 0.9),
        "path": new_mat("path", C(0.80, 0.66, 0.45), 0.9),
        "water": new_mat("water", C(0.30, 0.55, 0.75), 0.3),
        "wall": new_mat("wall", C(0.93, 0.86, 0.70), 0.9),
        "roof": new_mat("roof", C(0.72, 0.25, 0.16), 0.8),
        "stone": new_mat("stone", C(0.55, 0.52, 0.5), 0.9),
        "door": new_mat("door", C(0.40, 0.24, 0.12), 0.8),
        "window": new_mat("window", C(1.0, 0.80, 0.45), 0.5, emission=(1.0, 0.75, 0.4), estr=1.5),
        "bark": new_mat("bark", C(0.36, 0.24, 0.15), 0.9),
        "leaves": new_mat("leaves", C(0.30, 0.50, 0.18), 0.9),
        "pine": new_mat("pine", C(0.17, 0.36, 0.25), 0.9),
        "plank": new_mat("plank", C(0.55, 0.38, 0.22), 0.9),
        "mountain": new_mat("mountain", C(0.55, 0.60, 0.70), 0.9),
        "bush": new_mat("bush", C(0.33, 0.52, 0.20), 0.9),
        "flower1": new_mat("flower1", C(0.90, 0.30, 0.35), 0.8),
        "flower2": new_mat("flower2", C(0.95, 0.80, 0.25), 0.8),
        "smoke": new_mat("smoke", C(0.9, 0.9, 0.92), 0.9, alpha=0.35),
    }
    skin = new_mat("skin", C(0.96, 0.75, 0.62), 0.7)
    mats["hero"] = {"skin": skin, "cloth": new_mat("hero_c", C(0.20, 0.36, 0.62), 0.8), "cloth2": new_mat("hero_c2", C(0.35, 0.25, 0.18), 0.8),
                    "hair": new_mat("hero_h", C(0.45, 0.27, 0.12), 0.7), "shoe": new_mat("shoe", C(0.12, 0.08, 0.06), 0.7)}
    mats["kid"] = {"skin": skin, "cloth": new_mat("kid_c", C(0.90, 0.55, 0.15), 0.8), "cloth2": new_mat("kid_c2", C(0.30, 0.42, 0.55), 0.8),
                   "hair": new_mat("kid_h", C(0.85, 0.65, 0.30), 0.7), "shoe": mats["hero"]["shoe"]}
    mats["elder"] = {"skin": skin, "cloth": new_mat("eld_c", C(0.45, 0.30, 0.45), 0.8), "cloth2": new_mat("eld_c2", C(0.32, 0.30, 0.28), 0.8),
                     "hair": new_mat("eld_h", C(0.92, 0.92, 0.9), 0.7), "shoe": mats["hero"]["shoe"]}
    v = build_valley(mats)
    camera(CAM_LOC, CAM_TGT, 27)
    world((0.80, 0.84, 0.92), 0.55)
    light("SUN", (-10, -6, 12), (2, 6, 0), 2.4, (1.0, 0.92, 0.80), size=6)
    # проход 1: цвет
    render(os.path.join(OUT, "wc_color.png"), samples=40, view="Standard")
    # проход 2: только карандашные линии (всё — holdout, прозрачный фон)
    hold = bpy.data.materials.new("holdout")
    nt = hold.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    ho = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(ho.outputs[0], out.inputs[0])
    bpy.context.view_layer.material_override = hold
    freestyle((0.16, 0.15, 0.17), 1.6, noise_amp=1.2, noise_freq=24)
    render(os.path.join(OUT, "wc_lines.png"), samples=1, transparent=True, view="Standard")
    # проекция героя на экран — для маски памяти
    from bpy_extras.object_utils import world_to_camera_view
    cam = bpy.context.scene.camera
    p = world_to_camera_view(bpy.context.scene, cam, Vector(v["hero_pos"]))
    with open(os.path.join(OUT, "wc_hero.txt"), "w") as f:
        f.write(f"{p.x} {1 - p.y}\n")


# ------------------------------------------------------------ СТИЛЬ 2: БУМАЖНЫЙ ТЕАТР

def paper_layer(name, poly, depth, color, thick=0.03, rough=0.85, z_off=0.0, edge=(0.96, 0.94, 0.9), sss=0.15):
    """Вырезанный слой бумаги. poly — список (x, z) в плоскости XZ, слой на глубине y=depth."""
    m = new_mat(name, color, rough, sss=sss)
    add_noise_bump(m, 90, 0.12)
    me = new_mat(name + "_edge", edge, 0.9)
    bm = bmesh.new()
    vs = [bm.verts.new((x, depth, z + z_off)) for x, z in poly]
    f = bm.faces.new(vs)
    bmesh.ops.recalc_face_normals(bm, faces=[f])
    if f.normal.y > 0:
        f.normal_flip()
    ret = bmesh.ops.extrude_face_region(bm, geom=[f])
    ev = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=ev, vec=(0, thick, 0))
    for face in bm.faces:
        face.material_index = 0 if abs(face.normal.y) > 0.5 else 1
    o = obj(name, bm, m)
    o.data.materials.append(me)
    return o


def wavy(x0, x1, base, amp, freq, n=120, seed=0.0, top=True, bottom=-30.0):
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        z = base + amp * (math.sin(x * freq + seed) * 0.6 + math.sin(x * freq * 2.3 + seed * 1.7) * 0.25 + noise.noise(Vector((x * 0.4, seed, 0))) * 0.4)
        pts.append((x, z))
    return pts + [(x1, bottom), (x0, bottom)]


def circle(cx, cz, r, n=48, sx=1.0):
    return [(cx + r * sx * math.cos(TAU * i / n), cz + r * math.sin(TAU * i / n)) for i in range(n)]


def puppet(cx, cz, depth, scale, colors, name, pose=0.0, child=False):
    """Бумажная марионетка: детали на латунных гвоздиках."""
    objs = []
    s = scale
    hr = 0.32 * s * (1.25 if child else 1.0)
    skin, cloth, cloth2, hair = colors
    body_h = 1.1 * s * (0.75 if child else 1.0)
    leg_h = 0.95 * s * (0.75 if child else 1.0)
    pin = new_mat("pin_" + name, (0.85, 0.65, 0.3), 0.25, metal=1.0)
    d = depth
    # ноги
    for k, a in enumerate((-pose, pose)):
        R = Matrix.Rotation(a * 0.45, 2)
        pts = [(-0.11 * s, 0), (0.11 * s, 0), (0.09 * s, -leg_h), (0.2 * s, -leg_h - 0.08 * s), (-0.12 * s, -leg_h - 0.08 * s), (-0.1 * s, -leg_h)]
        pts = [tuple(R @ Vector(p)) for p in pts]
        pts = [(cx + p[0] + (k - 0.5) * 0.16 * s, cz + p[1]) for p in pts]
        objs.append(paper_layer(f"{name}_leg{k}", pts, d + 0.02 + k * 0.01, cloth2, 0.012))
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.035 * s, radius2=0.035 * s, depth=0.02)
        for v in bm.verts:
            v.co = Matrix.Rotation(math.pi / 2, 3, "X") @ v.co + Vector((cx + (k - 0.5) * 0.16 * s, d - 0.012, cz - 0.02 * s))
        objs.append(obj("pin", bm, pin))
    # туника
    tun = [(-0.36 * s, 0.0), (0.36 * s, 0.0), (0.2 * s, body_h), (-0.2 * s, body_h)]
    tun = [(cx + x, cz + z) for x, z in tun]
    objs.append(paper_layer(f"{name}_body", tun, d, cloth, 0.012))
    # руки
    for k, a in enumerate((pose, -pose)):
        R = Matrix.Rotation(a * 0.6 + (k - 0.5) * 0.3, 2)
        L = 0.85 * s * (0.75 if child else 1.0)
        pts = [(-0.07 * s, 0.05 * s), (0.07 * s, 0.05 * s), (0.06 * s, -L), (-0.06 * s, -L)]
        pts = [tuple(R @ Vector(p)) for p in pts]
        ax = cx + (k - 0.5) * 0.44 * s
        az = cz + body_h - 0.1 * s
        pts = [(ax + p[0], az + p[1]) for p in pts]
        objs.append(paper_layer(f"{name}_arm{k}", pts, d - 0.015 if k else d + 0.015, cloth, 0.012))
        hand = R @ Vector((0, -L))
        objs.append(paper_layer(f"{name}_hand{k}", circle(ax + hand.x, az + hand.y, 0.08 * s, 16), d - 0.02 if k else d + 0.01, skin, 0.012))
    # голова
    hz = cz + body_h + hr * 0.9
    objs.append(paper_layer(f"{name}_head", circle(cx, hz, hr, 40), d - 0.01, skin, 0.012))
    hair_pts = [(cx + hr * 1.08 * math.cos(a), hz + hr * 1.08 * math.sin(a)) for a in [math.radians(t) for t in range(-10, 191, 10)]]
    hair_pts += [(cx - hr * 0.9, hz + hr * 0.2), (cx + hr * 0.4, hz + hr * 0.55), (cx + hr * 0.95, hz + hr * 0.1)]
    objs.append(paper_layer(f"{name}_hair", hair_pts, d - 0.02, hair, 0.012))
    eye = new_mat("eye_" + name, (0.08, 0.06, 0.05), 0.6)
    for sx in (-0.35, 0.35):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.035 * s, radius2=0.035 * s, depth=0.01)
        for v in bm.verts:
            v.co = Matrix.Rotation(math.pi / 2, 3, "X") @ v.co + Vector((cx + sx * hr, d - 0.035, hz - hr * 0.05))
        objs.append(obj("eye", bm, eye))
    return objs


def paper():
    reset()
    # фон-небо: градиент (вершинные цвета через материал с ColorRamp)
    sky = new_mat("sky", (0.95, 0.75, 0.55), 0.9)
    nt = sky.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.98, 0.72, 0.50, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.45, 0.55, 0.78, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    add_noise_bump(sky, 70, 0.1)
    bm = bmesh.new()
    for v in [(-12, 9, -6), (12, 9, -6), (12, 9, 18), (-12, 9, 18)]:
        bm.verts.new(v)
    bm.faces.new(bm.verts[:])
    o = obj("Sky", bm, sky)
    # солнце
    paper_layer("sun", circle(-2.4, 10.4, 1.3, 64), 8.6, (0.99, 0.88, 0.55), 0.02, sss=0.4)
    # горы
    mpts = [(-12, 4.0), (-7, 6.5), (-4.5, 5.5), (-1.0, 11.2), (0.4, 10.4), (1.2, 11.6), (4.5, 7.0), (7.5, 8.2), (12, 5.0), (12, -6), (-12, -6)]
    paper_layer("mountain", mpts, 8.0, (0.52, 0.56, 0.68), 0.03)
    paper_layer("snow", [(-1.0, 11.2), (0.4, 10.4), (1.2, 11.6), (2.2, 10.1), (1.4, 9.6), (0.6, 10.0), (-0.2, 9.4), (-1.8, 9.8)], 7.95, (0.97, 0.96, 0.95), 0.02)
    # туман — калька
    fog = new_mat("fog", (0.92, 0.92, 0.95), 0.6, alpha=0.55)
    bm = bmesh.new()
    vs = [bm.verts.new((x, 7.3, z)) for x, z in wavy(-12, 12, 6.2, 0.5, 0.8, seed=1.3, bottom=4.0)]
    bm.faces.new(vs)
    obj("fog", bm, fog)
    # дальние холмы с соснами
    paper_layer("hills_far", wavy(-12, 12, 4.6, 0.7, 0.45, seed=2.0), 6.5, (0.42, 0.56, 0.42), 0.03)
    for k, x in enumerate((-9, -7.6, -6.4, 5.8, 7.2, 8.6, 9.8)):
        h = 1.3 + (k % 3) * 0.3
        z = 4.6 + 0.3 * math.sin(x)
        paper_layer(f"pine{k}", [(x, z + h), (x + 0.55, z), (x - 0.55, z)], 6.2, (0.22, 0.38, 0.30), 0.02)
    # холм с дубом и домом
    paper_layer("hill_mid", wavy(-12, 12, 3.0, 0.9, 0.35, seed=4.2), 5.0, (0.55, 0.68, 0.33), 0.03)
    oak_c = [(-4.6 + 1.9 * math.cos(a) * (1 + 0.12 * math.sin(a * 7)), 6.6 + 1.5 * math.sin(a) * (1 + 0.12 * math.cos(a * 5))) for a in [TAU * i / 60 for i in range(60)]]
    paper_layer("oak_crown", oak_c, 4.7, (0.30, 0.50, 0.22), 0.03)
    paper_layer("oak_trunk", [(-4.9, 3.0), (-4.3, 3.0), (-4.45, 5.4), (-3.6, 6.2), (-4.4, 5.9), (-4.6, 6.4), (-4.9, 5.8), (-5.6, 6.1), (-4.85, 5.3)], 4.75, (0.38, 0.25, 0.16), 0.03)
    # дом с горящим окном (свет за вырезом)
    hx, hz = 3.6, 3.0
    paper_layer("house", [(hx - 1.5, hz - 0.5), (hx + 1.5, hz - 0.5), (hx + 1.5, hz + 1.6), (hx - 1.5, hz + 1.6)], 4.6, (0.92, 0.84, 0.66), 0.03)
    paper_layer("roof", [(hx - 1.9, hz + 1.5), (hx + 1.9, hz + 1.5), (hx, hz + 3.0)], 4.55, (0.72, 0.24, 0.16), 0.03)
    paper_layer("chimney", [(hx + 0.7, hz + 2.2), (hx + 1.1, hz + 2.2), (hx + 1.1, hz + 2.9), (hx + 0.7, hz + 2.9)], 4.58, (0.5, 0.45, 0.42), 0.03)
    paper_layer("door", [(hx + 0.3, hz - 0.5), (hx + 0.95, hz - 0.5), (hx + 0.95, hz + 0.75), (hx + 0.3, hz + 0.75)], 4.57, (0.42, 0.25, 0.13), 0.02)
    win = new_mat("win", (1, 0.8, 0.4), 0.5, emission=(1.0, 0.72, 0.35), estr=6.0)
    bm = bmesh.new()
    vs = [bm.verts.new((x, 4.56, z)) for x, z in [(hx - 1.0, hz + 0.3), (hx - 0.3, hz + 0.3), (hx - 0.3, hz + 0.95), (hx - 1.0, hz + 0.95)]]
    bm.faces.new(vs)
    obj("window", bm, win)
    # дым — калька
    for k in range(5):
        paper_layer(f"smoke{k}", circle(hx + 0.95 + k * 0.25, hz + 3.2 + k * 0.45, 0.22 + k * 0.08, 24), 4.65, (0.95, 0.95, 0.97), 0.01, sss=0.5)
    # старик на скамейке
    paper_layer("bench", [(1.0, 2.2), (2.4, 2.2), (2.4, 2.35), (1.0, 2.35)], 4.3, (0.5, 0.33, 0.2), 0.02)
    for o_ in puppet(1.55, 2.25, 4.25, 0.55, ((0.95, 0.76, 0.63), (0.45, 0.30, 0.45), (0.32, 0.30, 0.28), (0.95, 0.95, 0.93)), "elder", 0.1):
        pass
    # ручей и мост
    paper_layer("river", wavy(-12, 12, 1.7, 0.25, 0.6, seed=6.0, bottom=1.0), 3.6, (0.35, 0.58, 0.80), 0.02, sss=0.2)
    paper_layer("river_hi", wavy(-12, 12, 1.45, 0.15, 0.9, seed=7.0, bottom=1.25), 3.55, (0.55, 0.75, 0.90), 0.015)
    arch = [(x, 1.8 + 0.6 * math.cos((x - 1.5) / 1.7 * math.pi / 2)) for x in [1.5 - 1.7 + 3.4 * i / 30 for i in range(31)]]
    arch_in = [(x, 1.5 + 0.45 * math.cos((x - 1.5) / 1.3 * math.pi / 2)) for x in [1.5 + 1.3 - 2.6 * i / 30 for i in range(31)]]
    paper_layer("bridge", arch + [(3.2, 1.1), (2.8, 1.1)] + arch_in + [(0.2, 1.1), (-0.2, 1.1)], 3.4, (0.55, 0.38, 0.22), 0.03)
    # передний план: тропа и трава
    paper_layer("ground_front", wavy(-12, 12, 0.9, 0.35, 0.5, seed=8.0), 2.0, (0.46, 0.62, 0.28), 0.03)
    path_poly = [(-0.6, -3.5), (2.6, -3.5), (1.8, -1.0), (1.6, 0.2), (1.0, 0.9), (0.6, 0.9), (0.6, 0.2), (0.2, -1.0)]
    paper_layer("path", path_poly, 1.95, (0.86, 0.72, 0.50), 0.015)
    grass = []
    for i in range(121):
        x = -12 + 24 * i / 120
        grass.append((x, -0.4 + (0.45 if i % 2 else 0.0) + 0.1 * math.sin(x * 3)))
    paper_layer("grass_front", grass + [(12, -6), (-12, -6)], 0.6, (0.30, 0.48, 0.20), 0.03)
    for k, (x, z, c) in enumerate(((-3.0, -0.1, (0.92, 0.32, 0.35)), (-2.4, 0.15, (0.98, 0.82, 0.3)), (3.9, -0.05, (0.92, 0.32, 0.35)), (4.6, 0.1, (0.6, 0.45, 0.85)))):
        paper_layer(f"flower{k}", circle(x, z, 0.16, 12), 0.55, c, 0.012)
    # герой и ребёнок
    puppet(1.25, 0.15, 1.4, 1.0, ((0.96, 0.76, 0.63), (0.20, 0.36, 0.62), (0.36, 0.25, 0.17), (0.45, 0.27, 0.12)), "hero", 0.35)
    puppet(0.35, 0.05, 1.35, 0.95, ((0.96, 0.76, 0.63), (0.92, 0.56, 0.16), (0.30, 0.42, 0.55), (0.85, 0.65, 0.30)), "kid", -0.4, child=True)
    # рамка театра
    frame = new_mat("frame", (0.55, 0.12, 0.12), 0.7)
    add_noise_bump(frame, 80, 0.15)
    bm = bmesh.new()
    outer = [(-5.6, -3.4), (5.6, -3.4), (5.6, 14.2), (-5.6, 14.2)]
    inner = []
    for i in range(41):
        t = i / 40
        x = -4.3 + 8.6 * t
        inner.append((x, 12.4 + 0.45 * abs(math.sin(t * math.pi * 6))))
    ring_out = [bm.verts.new((x, -0.4, z)) for x, z in outer]
    f = bm.faces.new(ring_out)
    bmesh.ops.recalc_face_normals(bm, faces=[f])
    o = obj("frame_back", bm, frame)
    # рамка как вырез: используем boolean
    cut = new_mat("cut", (1, 1, 1))
    bm = bmesh.new()
    pts = [(-4.3, -2.2), (4.3, -2.2)] + list(reversed(inner))[::-1][::-1][::-1]
    pts = [(-4.3, -2.2), (4.3, -2.2)] + [(p[0], p[1]) for p in reversed(inner)]
    pts = [(-4.3, -2.2), (4.3, -2.2), (4.3, 12.4)] + [p for p in reversed(inner)][1:-1] + [(-4.3, 12.4)]
    vs = [bm.verts.new((x, -1.0, z)) for x, z in pts]
    face = bm.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, verts=[e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, 1.2, 0))
    cutter = obj("cutter", bm, cut)
    bmesh_frame = bmesh.new()
    vs = [bmesh_frame.verts.new((x, -0.45, z)) for x, z in outer]
    fr = bmesh_frame.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bmesh_frame, geom=[fr])
    bmesh.ops.translate(bmesh_frame, verts=[e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0.06, 0))
    fo = obj("Frame", bmesh_frame, frame)
    mod = fo.modifiers.new("cut", "BOOLEAN")
    mod.object = cutter
    mod.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = fo
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.objects.remove(o, do_unlink=True)
    # золотой бордюр рамки
    gold = new_mat("gold", (0.85, 0.62, 0.28), 0.25, metal=1.0)
    for z in (-2.25,):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co = Vector((v.co.x * 8.7, v.co.y * 0.05, v.co.z * 0.08)) + Vector((0, -0.5, z))
        obj("gold_trim", bm, gold)
    # камера и свет
    camera((0.0, -14.0, 5.4), (0.0, 5.0, 5.0), 50)
    world((0.10, 0.09, 0.12), 0.6)
    light("SPOT", (-6.5, -9.0, 13.0), (0.5, 4.0, 3.0), 4200, (1.0, 0.86, 0.66), size=0.9, spot=60)
    light("AREA", (7.0, -6.0, 3.0), (0.0, 4.0, 4.0), 260, (0.65, 0.75, 1.0), size=4)
    light("POINT", (3.3, 4.9, 3.7), (3.3, 4.6, 3.7), 30, (1.0, 0.7, 0.35), size=0.3)
    bpy.context.scene.camera.data.dof.use_dof = True
    bpy.context.scene.camera.data.dof.focus_distance = 15.5
    bpy.context.scene.camera.data.dof.aperture_fstop = 3.5
    render(os.path.join(OUT, "paper.png"), samples=64, view="AgX", look="AgX - Medium High Contrast")


# ------------------------------------------------------------ СТИЛЬ 3: ЛАКОВАЯ МИНИАТЮРА

def lacquer():
    reset()
    C = lambda *c: tuple(c)
    # темпера: насыщенные, матовые; фон — чёрный лак
    black = new_mat("lacquer", C(0.01, 0.01, 0.012), 0.08, coat=1.0)
    mats = {
        "grass": new_mat("grass", C(0.05, 0.16, 0.07), 0.35, coat=0.8),
        "path": new_mat("path", C(0.55, 0.30, 0.10), 0.5, coat=0.6),
        "water": new_mat("water", C(0.05, 0.18, 0.42), 0.1, coat=1.0),
        "wall": new_mat("wall", C(0.85, 0.65, 0.35), 0.6),
        "roof": new_mat("roof", C(0.65, 0.06, 0.05), 0.5),
        "stone": new_mat("stone", C(0.3, 0.25, 0.22), 0.6),
        "door": new_mat("door", C(0.25, 0.08, 0.05), 0.6),
        "window": new_mat("window", C(1.0, 0.75, 0.3), 0.5, emission=(1.0, 0.65, 0.25), estr=3.0),
        "bark": new_mat("bark", C(0.25, 0.10, 0.05), 0.6),
        "leaves": new_mat("leaves", C(0.08, 0.30, 0.12), 0.5, coat=0.5),
        "pine": new_mat("pine", C(0.03, 0.16, 0.10), 0.5),
        "plank": new_mat("plank", C(0.45, 0.20, 0.08), 0.6),
        "mountain": new_mat("mountain", C(0.03, 0.04, 0.07), 0.2, coat=1.0),
        "bush": new_mat("bush", C(0.10, 0.30, 0.10), 0.5),
        "flower1": new_mat("flower1", C(0.85, 0.08, 0.06), 0.5),
        "flower2": new_mat("flower2", C(0.95, 0.70, 0.10), 0.4, metal=0.6),
        "smoke": new_mat("smoke", C(0.9, 0.75, 0.4), 0.4, metal=0.8, alpha=0.4),
    }
    skin = new_mat("skin", C(0.92, 0.70, 0.52), 0.55)
    gold_cloth = new_mat("gold_cloth", C(0.85, 0.60, 0.20), 0.3, metal=0.9)
    mats["hero"] = {"skin": skin, "cloth": new_mat("hero_c", C(0.70, 0.06, 0.05), 0.45), "cloth2": new_mat("hero_c2", C(0.06, 0.12, 0.35), 0.45),
                    "hair": new_mat("hero_h", C(0.20, 0.08, 0.03), 0.5), "shoe": new_mat("shoe", C(0.03, 0.02, 0.02), 0.5)}
    mats["kid"] = {"skin": skin, "cloth": gold_cloth, "cloth2": new_mat("kid_c2", C(0.08, 0.30, 0.12), 0.45),
                   "hair": new_mat("kid_h", C(0.60, 0.40, 0.12), 0.5), "shoe": mats["hero"]["shoe"]}
    mats["elder"] = {"skin": skin, "cloth": new_mat("eld_c", C(0.20, 0.25, 0.55), 0.45), "cloth2": new_mat("eld_c2", C(0.25, 0.10, 0.06), 0.45),
                     "hair": new_mat("eld_h", C(0.95, 0.93, 0.88), 0.5), "shoe": mats["hero"]["shoe"]}
    v = build_valley(mats)
    # небо — чёрный лак со звёздами-золотинками
    bm = bmesh.new()
    for p in [(-60, 95, -10), (60, 95, -10), (60, 95, 70), (-60, 95, 70)]:
        bm.verts.new(p)
    bm.faces.new(bm.verts[:])
    obj("SkyLacquer", bm, black)
    star = new_mat("star", (1.0, 0.8, 0.4), 0.3, emission=(1.0, 0.78, 0.35), estr=8.0)
    random.seed(21)
    for k in range(90):
        sphere(random.uniform(0.08, 0.22), (random.uniform(-40, 40), 92, random.uniform(22, 60)), star, 8)
    # месяц
    moon = new_mat("moon", (1.0, 0.82, 0.45), 0.3, metal=1.0, emission=(1.0, 0.75, 0.35), estr=1.5)
    sphere(3.0, (-14, 90, 46), moon, 32)
    camera(CAM_LOC, CAM_TGT, 27)
    world((0.02, 0.02, 0.03), 0.3)
    light("SUN", (-10, -6, 12), (2, 6, 0), 2.2, (1.0, 0.82, 0.6), size=3)
    light("AREA", (9, -4, 6), (0, 8, 2), 900, (1.0, 0.70, 0.35), size=6)
    light("AREA", (-9, 14, 8), (0, 4, 1), 700, (0.55, 0.65, 1.0), size=6)
    freestyle((0.86, 0.64, 0.26), 1.4, noise_amp=0.6, noise_freq=40)
    render(os.path.join(OUT, "lacquer_raw.png"), samples=56, view="AgX", look="AgX - Medium High Contrast")


if __name__ == "__main__":
    if WHICH in ("watercolor", "all"):
        watercolor()
    if WHICH in ("paper", "all"):
        paper()
    if WHICH in ("lacquer", "all"):
        lacquer()
