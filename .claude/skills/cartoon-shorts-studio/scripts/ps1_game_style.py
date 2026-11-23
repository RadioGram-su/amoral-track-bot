"""UNBUILT / РАЗОБРАНО — PS1/PS2-style low-poly game look. Blender 4.0 EEVEE, no AI.
Run: xvfb-run -a blender -b --factory-startup -P ps1.py -- OUTDIR [stills|clip] [frame,frame]
Raw renders are 360x640; post-process with ffmpeg (palette + bayer dither + nearest x3 + scanlines).
"""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Euler, Quaternion
from bpy_extras.object_utils import world_to_camera_view

random.seed(7)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = ARGS[0] if ARGS else '/tmp'
MODE = ARGS[1] if len(ARGS) > 1 else 'stills'
ONLY = ARGS[2].split(',') if len(ARGS) > 2 else None
W, H = 360, 640
FOV = math.radians(62)
HALF_H = math.tan(FOV / 2); HALF_W = HALF_H * W / H; PX = 2 * HALF_H / H

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 1
sc.render.filter_size = 0.0
sc.eevee.use_bloom = True; sc.eevee.bloom_threshold = 1.0; sc.eevee.bloom_intensity = 0.12; sc.eevee.bloom_radius = 3.0
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
FONT = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
MONO = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')


def h2c(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(h, a=1.0):
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    c = h2c(h); return (f(c[0]), f(c[1]), f(c[2]), a)


# ------------------------------------------------------------------ pixel textures (procedural, 32-64 px)
def tex(name, w, h, fn):
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = [0.0] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            r, g, b = fn(x, y); i = (y * w + x) * 4
            px[i] = min(max(r, 0), 1); px[i + 1] = min(max(g, 0), 1); px[i + 2] = min(max(b, 0), 1); px[i + 3] = 1
    img.pixels = px
    return img


def nz(c, a):
    n = random.uniform(-a, a); return tuple(v + n for v in c)


def t_metal(x, y):
    if x % 32 == 0 or y % 32 == 0: return nz(h2c('#4A535E'), 0.02)
    if x % 32 in (3, 28) and y % 32 in (3, 28): return h2c('#C5CED6')
    return nz(h2c('#7F8C99'), 0.035)


def t_metal_dark(x, y):
    if x % 16 == 0 or y % 16 == 0: return nz(h2c('#2C333C'), 0.02)
    return nz(h2c('#4D5866'), 0.03)


def t_rocket(x, y):
    if y % 16 == 0 or x % 32 == 0: return nz(h2c('#9A988F'), 0.02)
    return nz(h2c('#E6E3DA'), 0.025)


def t_booster(x, y):
    if y % 16 == 0 or x % 16 == 0: return nz(h2c('#8E8E88'), 0.02)
    return nz(h2c('#C9C8C1'), 0.03)


def t_red(x, y):
    if y in (0, 31): return h2c('#5E120C')
    return nz(h2c('#C8301F'), 0.04)


def t_concrete(x, y):
    if random.random() < 0.04: return nz(h2c('#5E5C57'), 0.02)
    return nz(h2c('#8E8C86'), 0.05)


def t_steppe(x, y):
    random.seed((x // 2) * 131 + (y // 2) * 17 + 3)
    c = random.choice(['#B59A63', '#B59A63', '#A88E59', '#8E8F55', '#9C8450'])
    random.seed(); return nz(h2c(c), 0.02)


def t_hazard(x, y):
    return h2c('#F2C619') if ((x + y) // 8) % 2 else h2c('#1A1A1A')


def t_brass(x, y):
    if x in (0, 31) or y in (0, 31): return h2c('#8A6420')
    return nz(h2c('#D9A43A'), 0.04)


def t_gantry(x, y):
    if x in (0, 15) or y in (0, 15): return h2c('#5A1712')
    return nz(h2c('#B0392B'), 0.04)


def t_grate(x, y):
    return h2c('#15191E') if (x % 4 < 2 and y % 4 < 2) else nz(h2c('#5B6673'), 0.03)


def t_lox(x, y):
    return nz(h2c('#BFE6FF') if (x * 3 + y * 5) % 23 < 2 else h2c('#7FB8E6'), 0.02)


def t_pipe(x, y):
    if y % 16 == 0: return h2c('#6B5410')
    return nz(h2c('#D6A825'), 0.03)


def t_plain(c):
    return lambda x, y: h2c(c)


T = dict(metal=tex('metal', 64, 64, t_metal), metal_dark=tex('metal_dark', 32, 32, t_metal_dark),
         rocket=tex('rocket', 64, 64, t_rocket), booster=tex('booster', 32, 32, t_booster), red=tex('red', 32, 32, t_red),
         concrete=tex('concrete', 64, 64, t_concrete), steppe=tex('steppe', 64, 64, t_steppe), hazard=tex('hazard', 32, 32, t_hazard),
         brass=tex('brass', 32, 32, t_brass), gantry=tex('gantry', 16, 16, t_gantry), grate=tex('grate', 32, 32, t_grate),
         lox=tex('lox', 32, 32, t_lox), pipe=tex('pipe', 32, 32, t_pipe),
         white=tex('white', 4, 4, t_plain('#F4F4F0')), black=tex('black', 4, 4, t_plain('#101014')),
         dark=tex('dark', 4, 4, t_plain('#2A2F38')), smoke=tex('smoke', 4, 4, t_plain('#D9D9D9')),
         hill=tex('hill', 32, 32, lambda x, y: nz(h2c('#8A8A5A'), 0.04)), cloud=tex('cloud', 4, 4, t_plain('#FFFFFF')))

# ------------------------------------------------------------------ materials
MATS = {}
FOGS = dict(pad=('#A9CBE3', 70, 330, 0.5), tank=('#0E2E33', 2.0, 24, 0.38), sky=('#0B1430', 120, 500, 0.55))


def ps1(tname, fog, scale=0.25, emit=0.0, levels=5):
    key = f'{tname}_{fog}_{scale}_{emit}'
    if key in MATS: return MATS[key]
    fc, f0, f1, amb = FOGS[fog]
    m = bpy.data.materials.new(key); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); tc = N.new('ShaderNodeTexCoord')
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = (scale, scale, scale)
    L.new(tc.outputs['Object'], mul.inputs[0])
    it = N.new('ShaderNodeTexImage'); it.image = T[tname]; it.interpolation = 'Closest'
    it.projection = 'BOX'; it.projection_blend = 0.0; L.new(mul.outputs[0], it.inputs['Vector'])
    dif = N.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = N.new('ShaderNodeShaderToRGB'); L.new(dif.outputs[0], s2r.inputs[0])
    bw = N.new('ShaderNodeRGBToBW'); L.new(s2r.outputs['Color'], bw.inputs['Color'])
    l1 = N.new('ShaderNodeMath'); l1.operation = 'MULTIPLY_ADD'; l1.use_clamp = True
    l1.inputs[1].default_value = 1 - amb; l1.inputs[2].default_value = amb; L.new(bw.outputs[0], l1.inputs[0])
    l2 = N.new('ShaderNodeMath'); l2.operation = 'MULTIPLY'; l2.inputs[1].default_value = levels; L.new(l1.outputs[0], l2.inputs[0])
    l3 = N.new('ShaderNodeMath'); l3.operation = 'FLOOR'; L.new(l2.outputs[0], l3.inputs[0])
    l4 = N.new('ShaderNodeMath'); l4.operation = 'DIVIDE'; l4.inputs[1].default_value = levels; L.new(l3.outputs[0], l4.inputs[0])
    lit = N.new('ShaderNodeMixRGB'); lit.blend_type = 'MULTIPLY'; lit.inputs['Fac'].default_value = 1.0
    L.new(it.outputs['Color'], lit.inputs['Color1']); L.new(l4.outputs[0], lit.inputs['Color2'])
    col = lit
    if emit > 0:
        add = N.new('ShaderNodeMixRGB'); add.blend_type = 'ADD'; add.inputs['Fac'].default_value = emit
        L.new(lit.outputs['Color'], add.inputs['Color1']); L.new(it.outputs['Color'], add.inputs['Color2']); col = add
    cd = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange'); mr.clamp = True
    mr.inputs['From Min'].default_value = f0; mr.inputs['From Max'].default_value = f1
    L.new(cd.outputs['View Distance'], mr.inputs['Value'])
    fm = N.new('ShaderNodeMixRGB'); L.new(mr.outputs[0], fm.inputs['Fac'])
    L.new(col.outputs['Color'], fm.inputs['Color1']); fm.inputs['Color2'].default_value = lin(fc)
    em = N.new('ShaderNodeEmission'); L.new(fm.outputs['Color'], em.inputs['Color'])
    L.new(em.outputs[0], out.inputs['Surface'])
    MATS[key] = m
    return m


def glow(color, strength=3.0):
    key = f'glow_{color}_{strength}'
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = lin(color); em.inputs['Strength'].default_value = strength
    L.new(em.outputs[0], out.inputs['Surface']); MATS[key] = m
    return m


# ------------------------------------------------------------------ geometry helpers (flat-shaded low poly)
COLL = {}


def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name); sc.collection.children.link(c); COLL[name] = c
    return COLL[name]


CUR = [None]


def put(ob):
    (CUR[0] or sc.collection).objects.link(ob); return ob


def mesh_obj(name, bm, mat):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    return put(bpy.data.objects.new(name, me))


def lathe(name, prof, mat, segs=10):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=segs, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat)


def box(name, size, mat, loc=(0, 0, 0), origin_top=False):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if origin_top: bmesh.ops.translate(bm, vec=(0, 0, -size[2] / 2), verts=bm.verts)
    ob = mesh_obj(name, bm, mat); ob.location = loc; return ob


def ball(name, r, mat, loc=(0, 0, 0), u=8, v=6, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    ob = mesh_obj(name, bm, mat); ob.location = loc; ob.scale = scale; return ob


def cone(name, r1, r2, depth, mat, segs=8):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    return mesh_obj(name, bm, mat)


def beam(name, a, b, t, mat):
    a = Vector(a); b = Vector(b); d = b - a
    ob = box(name, (t, t, d.length), mat); ob.location = (a + b) / 2
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = d.to_track_quat('Z', 'Y'); return ob


def grid(name, size, mat):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=8, y_segments=8, size=size)
    return mesh_obj(name, bm, mat)


def parent(ch, par):
    ch.parent = par; return ch


# ------------------------------------------------------------------ HEX (low-poly mascot), faces +Y
def make_hex(fog, scale=1.0):
    root = put(bpy.data.objects.new('hex', None)); root.scale = (scale,) * 3
    P = {}
    body = parent(cone('hex_body', 0.55, 0.55, 0.42, ps1('brass', fog, 1.0), segs=6), root)
    body.rotation_euler = (math.radians(90), 0, 0); P['body'] = body
    sock = parent(cone('hex_socket', 0.30, 0.30, 0.06, ps1('dark', fog), segs=8), root)
    sock.rotation_euler = (math.radians(90), 0, 0); sock.location = (0, 0.20, 0)
    parent(ball('hex_eye', 0.25, ps1('white', fog), (0, 0.17, 0)), root)
    P['pupil'] = parent(ball('hex_pupil', 0.11, ps1('black', fog), (0, 0.39, 0.02), u=6, v=4), root)
    parent(ball('hex_glint', 0.035, glow('#FFFFFF', 1.0), (-0.04, 0.48, 0.08), u=4, v=2), root)
    brow = parent(box('hex_brow', (0.32, 0.06, 0.07), ps1('black', fog), (0.02, 0.24, 0.44)), root)
    brow.rotation_euler = (0, math.radians(-12), 0)
    for s, n in ((-1, 'L'), (1, 'R')):
        leg = parent(box(f'leg{n}', (0.13, 0.13, 0.36), ps1('dark', fog), (s * 0.17, 0, -0.30), origin_top=True), root)
        parent(box(f'foot{n}', (0.2, 0.3, 0.1), ps1('dark', fog), (0, 0.05, -0.38)), leg); P['leg' + n] = leg
        arm = parent(box(f'arm{n}', (0.1, 0.1, 0.36), ps1('dark', fog), (s * 0.52, 0, 0.08), origin_top=True), root)
        P['arm' + n] = arm
    wr = parent(box('wrench', (0.07, 0.07, 0.75), ps1('metal', fog, 2.0), (0, 0, -0.5)), P['armR'])
    head = parent(lathe('wrench_head', [(0.09, -0.04), (0.18, -0.04), (0.18, 0.04), (0.09, 0.04), (0.09, -0.04)], ps1('metal', fog, 2.0), segs=6), wr)
    head.location = (0, 0, -0.42); head.rotation_euler = (math.radians(90), 0, 0)
    bolt = parent(cone('bolt_head', 0.17, 0.17, 0.12, glow('#FF4B2B', 1.6), segs=6), P['armL'])
    bolt.location = (0, 0.02, -0.42)
    bs = parent(cone('bolt_shaft', 0.07, 0.07, 0.45, glow('#FF7A55', 1.4), segs=6), bolt); bs.location = (0, 0, -0.24)
    P['bolt'] = [bolt, bs]
    sh = parent(cone('blob_shadow', 0.55, 0.55, 0.01, glow('#000000', 0.0), segs=10), root)
    sh.location = (0, 0, -0.80); sh.scale = (1, 0.8, 1)
    P['root'] = root
    for b in P['bolt']: b.hide_render = True
    return P


def hex_pose(P, walk=0.0, arm_up=False, bolt=False):
    s = math.sin(walk)
    P['legL'].rotation_euler = (s * 0.5, 0, 0); P['legR'].rotation_euler = (-s * 0.5, 0, 0)
    P['armR'].rotation_euler = (-s * 0.35 + 0.25, 0, 0)
    P['armL'].rotation_euler = (math.radians(170), 0, math.radians(-15)) if arm_up else (s * 0.35, 0, 0)
    P['body'].location = (0, 0, abs(s) * 0.05)
    for b in P['bolt']: b.hide_render = not bolt


# ------------------------------------------------------------------ rocket (low poly)
CORE = [(0, 0.55), (0.46, 0.55), (0.5, 0.75), (0.5, 1.0), (0.62, 6.55), (0.62, 6.8), (0, 6.8)]
BOOST = [(0, 0.55), (0.5, 0.55), (0.56, 0.78), (0.44, 3.0), (0.22, 4.55), (0.07, 5.0), (0, 5.05)]
FAIR = [(0, 8.75), (0.70, 8.75), (0.74, 8.9), (0.74, 10.4), (0.47, 11.15), (0.18, 11.6), (0, 11.65)]


def bell(name, fog, s=1.0):
    return lathe(name, [(0.05 * s, 0.0), (0.08 * s, -0.08 * s), (0.14 * s, -0.32 * s), (0.15 * s, -0.36 * s)], ps1('dark', fog), segs=8)


def make_rocket(fog, sep=0.0, flames=False):
    root = put(bpy.data.objects.new('rocket', None)); R = dict(root=root, boosters=[])
    parent(lathe('core', CORE, ps1('rocket', fog, 0.5)), root)
    parent(lathe('band1', [(0, 6.0), (0.64, 6.0), (0.64, 6.3), (0, 6.3)], ps1('red', fog, 1.0)), root)
    parent(lathe('stage3', [(0, 6.8), (0.55, 6.8), (0.62, 7.15), (0.62, 8.7), (0, 8.7)], ps1('rocket', fog, 0.5)), root)
    parent(lathe('band2', [(0, 7.9), (0.64, 7.9), (0.64, 8.15), (0, 8.15)], ps1('red', fog, 1.0)), root)
    parent(lathe('fairing', FAIR, ps1('rocket', fog, 0.5)), root)
    parent(lathe('tower', [(0, 11.6), (0.12, 11.6), (0.10, 12.2), (0.16, 12.25), (0.16, 12.6), (0.05, 12.9), (0, 12.95)], ps1('dark', fog)), root)
    for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        b = parent(bell(f'cn{i}', fog), root); b.location = (dx * 0.17, dy * 0.17, 0.55)
    for k in range(4):
        a = math.radians(45 + 90 * k); e = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-math.sin(a), math.cos(a), 0))
        piv = parent(put(bpy.data.objects.new(f'bpiv{k}', None)), root)
        tilt = math.atan((0.98 - 0.62) / 5.0)
        dist = 0.98 + sep * 7.0
        piv.location = e * dist + Vector((0, 0, -sep * 3.0))
        piv.rotation_mode = 'QUATERNION'; piv.rotation_quaternion = Quaternion(t, -tilt + sep * math.radians(55))
        parent(lathe(f'booster{k}', BOOST, ps1('booster', fog, 0.5)), piv)
        parent(lathe(f'btip{k}', [(0, 4.3), (0.3, 4.3), (0.07, 5.0), (0, 5.05)], ps1('red', fog, 1.0)), piv)
        for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
            b = parent(bell(f'bn{k}{i}', fog), piv); b.location = (dx * 0.17, dy * 0.17, 0.55)
        if flames:
            f = parent(cone(f'bflame{k}', 0.32, 0.05, 1.6 * (1 - sep), glow('#FFB347', 3.0), segs=8), piv)
            f.location = (0, 0, -0.1 - 0.8 * (1 - sep)); f.rotation_euler = (math.pi, 0, 0)
        R['boosters'].append(piv)
    if flames:
        f1 = parent(cone('flame_outer', 0.95, 0.1, 8.0, glow('#FF8A2A', 2.6), segs=8), root)
        f1.location = (0, 0, -3.6); f1.rotation_euler = (math.pi, 0, 0)
        f2 = parent(cone('flame_inner', 0.55, 0.05, 5.0, glow('#FFF2B0', 4.0), segs=8), root)
        f2.location = (0, 0, -2.0); f2.rotation_euler = (math.pi, 0, 0)
        R['flames'] = [f1, f2]
    return R


# ------------------------------------------------------------------ world / light / camera
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
WN = world.node_tree.nodes; WL = world.node_tree.links
bg = WN['Background']; wtc = WN.new('ShaderNodeTexCoord'); sep_ = WN.new('ShaderNodeSeparateXYZ')
WL.new(wtc.outputs['Generated'], sep_.inputs[0])
wmr = WN.new('ShaderNodeMapRange'); wmr.inputs['From Min'].default_value = -0.05; wmr.inputs['From Max'].default_value = 0.7
WL.new(sep_.outputs['Z'], wmr.inputs['Value'])
ramp = WN.new('ShaderNodeValToRGB'); WL.new(wmr.outputs[0], ramp.inputs['Fac']); WL.new(ramp.outputs['Color'], bg.inputs['Color'])


def sky(horizon, zenith):
    e = ramp.color_ramp.elements; e[0].color = lin(horizon); e[1].color = lin(zenith)


sun_d = bpy.data.lights.new('sun', 'SUN'); sun_d.energy = 3.0; sun_d.use_shadow = False
sun = put(bpy.data.objects.new('sun', sun_d)); sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(-35))

cam_d = bpy.data.cameras.new('cam'); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24
cam_d.lens = 12 / math.tan(FOV / 2); cam_d.clip_start = 0.05; cam_d.clip_end = 900
cam = put(bpy.data.objects.new('cam', cam_d)); sc.camera = cam


def look(loc, target, roll=0.0):
    cam.location = Vector(loc); d = Vector(target) - Vector(loc)
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), roll)


# ------------------------------------------------------------------ HUD (camera-space, pixel units)
HUD = {}


def hud_tag(tag, ob):
    HUD.setdefault(tag, []).append(ob); ob.parent = cam; return ob


def hud_txt(tag, body, x, y, px, color, align='LEFT', mono=False, shadow=2, rot=0.0):
    """x,y in pixels from screen center (y up)."""
    for dx, dy, col, z in ((shadow, -shadow, '#000000', -1.0005), (0, 0, color, -1.0)):
        if dx == 0 and col == '#000000':
            continue
        if col == '#000000' and shadow == 0:
            continue
        cu = bpy.data.curves.new('t', 'FONT'); cu.body = body; cu.font = MONO if mono else FONT
        cu.size = px * PX; cu.align_x = align; cu.align_y = 'CENTER'; cu.space_line = 1.05
        cu.materials.append(glow(col, 1.0))
        ob = bpy.data.objects.new('t', cu); sc.collection.objects.link(ob)
        ob.location = ((x + dx) * PX, (y + dy) * PX, z); ob.rotation_euler = (0, 0, rot)
        hud_tag(tag, ob)


def hud_box(tag, x, y, w, h, color, border='#FFFFFF', bw=2):
    if border:
        b = box('pb', (w * PX + 2 * bw * PX, h * PX + 2 * bw * PX, 0.0001), glow(border, 1.0))
        b.location = (x * PX, y * PX, -1.0015); hud_tag(tag, b)
    p = box('pf', (w * PX, h * PX, 0.0001), glow(color, 1.0)); p.location = (x * PX, y * PX, -1.001); hud_tag(tag, p)


def hud_common(tag, level, area, count):
    hud_txt(tag, level, -170, 300, 17, '#FFD23F')
    hud_txt(tag, area, -170, 280, 12, '#FFFFFF')
    hud_txt(tag, '♥♥♥', 170, 300, 17, '#FF3B3B', align='RIGHT')
    hud_txt(tag, f'◆ СОПЛА {count}/32', 170, 280, 12, '#FFFFFF', align='RIGHT')


# ================================================================== SCENES
# ---- 1. launch pad (steppe)
CUR[0] = coll('pad')
pad_g = grid('ground', 300, ps1('steppe', 'pad', 0.25))
box('pad', (16, 16, 1), ps1('concrete', 'pad', 0.25), (0, 0, 0.5))
for sx, sy, w, d in ((0, -8, 16, 0.6), (0, 8, 16, 0.6), (-8, 0, 0.6, 16), (8, 0, 0.6, 16)):
    box('hz', (w, d, 0.06), ps1('hazard', 'pad', 1.0), (sx, sy, 1.03))
gx = -4.4
for cx in (gx - 1, gx + 1):
    for cy in (-1, 1):
        beam('col', (cx, cy, 1), (cx, cy, 17), 0.22, ps1('gantry', 'pad', 1.0))
for z in range(2, 17, 2):
    for (a, b) in (((gx - 1, -1), (gx + 1, -1)), ((gx - 1, 1), (gx + 1, 1)), ((gx - 1, -1), (gx - 1, 1)), ((gx + 1, -1), (gx + 1, 1))):
        beam('hb', (a[0], a[1], z), (b[0], b[1], z), 0.14, ps1('gantry', 'pad', 1.0))
    beam('db', (gx - 1, -1, z - 2 + 1), (gx + 1, -1, z + 1), 0.1, ps1('gantry', 'pad', 1.0))
for z in (6.5, 10.5):
    beam('arm', (gx + 1, 0, z), (-0.65, 0, z), 0.3, ps1('gantry', 'pad', 1.0))
for i in range(9):
    a = i / 9 * 2 * math.pi + 0.3; d = random.uniform(170, 260)
    h = cone('hill', random.uniform(40, 80), 2, random.uniform(14, 30), ps1('hill', 'pad', 0.1), segs=5)
    h.location = (math.cos(a) * d, math.sin(a) * d, 6)
for i in range(6):
    a = random.uniform(0, 2 * math.pi); d = random.uniform(90, 200)
    ball('cloud', 1, ps1('cloud', 'pad', 1.0, emit=0.4), (math.cos(a) * d, math.sin(a) * d, random.uniform(55, 85)), u=7, v=4,
         scale=(random.uniform(14, 24), random.uniform(8, 12), random.uniform(3, 5)))
CUR[0] = coll('pad_rocket')
RP = make_rocket('pad'); RP['root'].location = (0, 0, 1.0)
CUR[0] = coll('pad_smoke')
for i in range(26):
    a = random.uniform(0, 2 * math.pi); d = random.uniform(0, 7)
    ball('smoke', random.uniform(1.2, 2.6), ps1('smoke', 'pad', 1.0, emit=0.25), (math.cos(a) * d, math.sin(a) * d, random.uniform(1.5, 5)), u=7, v=5)
CUR[0] = coll('pad_hex')
HP = make_hex('pad', 1.0); HP['root'].location = (3.0, -11.0, 0.82); HP['root'].rotation_euler = (0, 0, math.radians(-160))

# ---- 2. LOX tank interior
CUR[0] = coll('tank')
lathe('tank_wall', [(0, -4), (6, -4), (6, 26), (0, 26)], ps1('metal', 'tank', 0.3), segs=12)
for z in range(-2, 26, 4):
    lathe('ring', [(5.55, z - 0.2), (5.95, z - 0.2), (5.95, z + 0.2), (5.55, z + 0.2), (5.55, z - 0.2)], ps1('metal_dark', 'tank', 0.5), segs=12)
lox = cone('lox', 5.95, 5.95, 0.1, ps1('lox', 'tank', 0.4, emit=0.5), segs=12); lox.location = (0, 0, -2.2)
box('catwalk', (1.8, 12, 0.15), ps1('grate', 'tank', 0.5), (0, 0, 0))
for y in range(-6, 7, 2):
    for sx in (-0.9, 0.9):
        box('post', (0.06, 0.06, 0.9), ps1('metal_dark', 'tank', 1.0), (sx, y, 0.45))
for sx in (-0.9, 0.9):
    box('rail', (0.07, 12, 0.07), ps1('pipe', 'tank', 1.0), (sx, 0, 0.92))
lathe('pipe', [(0, -4), (0.6, -4), (0.6, 26), (0, 26)], ps1('pipe', 'tank', 0.5), segs=8).location = (3.3, 2.5, 0)
for i in range(10):
    a = i / 10 * 2 * math.pi
    b = box('lamp', (0.35, 0.35, 0.2), glow('#FFE08A', 2.5), (math.cos(a) * 5.85, math.sin(a) * 5.85, 3 + (i % 3) * 4))
for i in range(8):
    a = random.uniform(0, 2 * math.pi); d = random.uniform(2.5, 5.3)
    ball('vapor', random.uniform(0.25, 0.5), ps1('smoke', 'tank', 1.0, emit=0.5), (math.cos(a) * d, math.sin(a) * d, random.uniform(-1.8, -0.6)), u=6, v=4)
NOZ = lathe('pickup', [(0.12, 0.0), (0.2, -0.12), (0.4, -0.6), (0.44, -0.7)], glow('#FF8A1F', 2.2), segs=8)
NOZ.location = (0, 3.6, 1.9); NOZ.rotation_euler = (math.radians(20), 0, 0)
SPARK = []
for i in range(6):
    s = ball('spark', 0.07, glow('#FFF3B0', 4.0), (0, 0, 0), u=4, v=2); SPARK.append(s)
FLASH = ball('flash', 0.6, glow('#FFFFFF', 5.0), (0, 3.6, 1.9), u=8, v=6); FLASH.hide_render = True
CUR[0] = coll('tank_hex')
HT = make_hex('tank', 1.0); HT['root'].location = (0, -1.0, 0.9)

# ---- 3. sky: booster separation (Korolev cross)
CUR[0] = coll('sky')
RS = make_rocket('sky', sep=0.55, flames=True)
for i in range(70):
    v = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.15, 1))).normalized() * 420
    ball('star', random.uniform(0.6, 1.4), glow('#FFFFFF', 2.0), v, u=4, v=2)
for k, piv in enumerate(RS['boosters']):
    a = math.radians(45 + 90 * k); e = Vector((math.cos(a), math.sin(a), 0))
    for j in range(9):
        t = j / 8
        p = e * (1.2 + 3.6 * t) + Vector((0, 0, -0.6 - 2.0 * t - 4 * t * t))
        ball('trail', 0.35 + 0.55 * t, ps1('smoke', 'sky', 1.0, emit=0.35), p, u=6, v=4)
for j in range(12):
    ball('exhaust', 1.0 + j * 0.45, ps1('smoke', 'sky', 1.0, emit=0.3), (random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), -9 - j * 3.2), u=7, v=5)

# ================================================================== HUD per frame
CUR[0] = None
hud_common('h_pad', 'УР. 1', 'РАКЕТА', 0)
hud_txt('h_pad', 'ЗАЧЕМ РАКЕТЕ\n32 СОПЛА?', 0, 205, 30, '#FFD23F', align='CENTER', shadow=3)
hud_box('h_pad', 0, -268, 300, 34, '#13204A')
hud_txt('h_pad', 'ЗАДАНИЕ: НАЙДИ ВСЕ СОПЛА', 0, -268, 13, '#FFFFFF', align='CENTER', shadow=1)

hud_common('h_tank', 'УР. 1-2', 'БАК O₂', 7)
hud_txt('h_tank', '+1', 34, 92, 24, '#FFD23F', align='CENTER', shadow=2)
hud_box('h_tank', 0, -250, 330, 92, '#13204A')
hud_box('h_tank', -128, -197, 62, 20, '#FFD23F', border=None)
hud_txt('h_tank', 'ХЕКС', -128, -197, 12, '#13204A', align='CENTER', shadow=0)
hud_txt('h_tank', 'Тут жидкий кислород.\nМинус 183 градуса!', -150, -252, 14, '#FFFFFF', shadow=1)
hud_txt('h_tank', '▼', 150, -284, 11, '#FFD23F', align='CENTER', shadow=0)

hud_common('h_sky', 'УР. 1-3', 'ОТДЕЛЕНИЕ', 24)
hud_txt('h_sky', 'КРЕСТ\nКОРОЛЁВА!', 0, 175, 34, '#FFD23F', align='CENTER', shadow=3, rot=math.radians(5))
hud_txt('h_sky', 'КОМБО ×4', 0, 118, 14, '#FFFFFF', align='CENTER', shadow=2, rot=math.radians(5))

hud_box('h_end', 0, 150, 316, 196, '#13204A')
hud_txt('h_end', 'УРОВЕНЬ ПРОЙДЕН!', 0, 222, 20, '#FFD23F', align='CENTER', shadow=2)
hud_txt('h_end', 'СОПЛА.........32/32\nВРЕМЯ..........0:44\nРЕКОРД.........НОВЫЙ', -138, 160, 13, '#FFFFFF', mono=True, shadow=1)
hud_txt('h_end', 'ЛИШНИЕ ДЕТАЛИ..1 ???', -138, 100, 13, '#FF4B4B', mono=True, shadow=1)
hud_txt('h_end', '▶ ДАЛЬШЕ: ЭКРАНОПЛАН', 0, 68, 13, '#FFD23F', align='CENTER', shadow=1)


# ================================================================== render control
def show(colls, hud):
    for n, c in COLL.items():
        c.hide_render = n not in colls
    for t, obs in HUD.items():
        for ob in obs:
            ob.hide_render = t != hud


def setup_pad(): sky('#A9CBE3', '#2E5AA8'); sun_d.energy = 3.0


def setup_tank(): sky('#0E2E33', '#0E2E33'); sun_d.energy = 2.4


def setup_sky(): sky('#1F3C88', '#03050F'); sun_d.energy = 3.2


def frame_pad():
    setup_pad(); show({'pad', 'pad_rocket', 'pad_hex'}, 'h_pad'); hex_pose(HP, walk=0.6)
    HP['root'].location = (2.4, -6.6, 1.82); HP['root'].rotation_euler = (0, 0, math.radians(-150))
    look((6.2, -16.5, 1.6), (0.5, 0, 7.6))


def frame_tank(t=0.0):
    setup_tank(); show({'tank', 'tank_hex'}, 'h_tank')
    hex_pose(HT, walk=0.9 + t * 30)
    HT['root'].location = (0, -1.0 + t * 4.5, 0.9); HT['root'].rotation_euler = (0, 0, 0)
    NOZ.rotation_euler = (math.radians(20), 0, t * 6.0); NOZ.location = (0, 3.6, 1.9 + math.sin(t * 9) * 0.15)
    for i, s in enumerate(SPARK):
        a = i / 6 * 2 * math.pi + t * 5
        s.location = NOZ.location + Vector((math.cos(a) * 0.75, math.sin(a) * 0.3, math.sin(a * 2) * 0.4 - 0.3))
    hl = HT['root'].location
    look((hl.x + 1.0, hl.y - 4.4, hl.z + 2.6), (0, hl.y + 4.2, 1.2))


def frame_sky():
    setup_sky(); show({'sky'}, 'h_sky')
    look((9.5, -10.5, -15.0), (0, 0, 3.8), roll=math.radians(-8))


def frame_end():
    setup_pad(); show({'pad', 'pad_hex', 'pad_smoke'}, 'h_end'); hex_pose(HP, walk=0.0, arm_up=True, bolt=True)
    HP['root'].location = (3.0, -11.0, 0.82); HP['root'].rotation_euler = (0, 0, math.radians(-165))
    look((4.2, -15.6, 1.9), (2.6, -9.0, 2.6))


def render(name):
    sc.render.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDERED', name)


if MODE == 'stills':
    for name, fn in (('1_pad', frame_pad), ('2_tank', frame_tank), ('3_sky', frame_sky), ('4_end', frame_end)):
        if ONLY and name not in ONLY: continue
        fn(); render(name)
else:
    # 4 s clip at 30 fps, animated "on twos" (15 fps steps) for the retro feel
    os.makedirs(OUT, exist_ok=True)
    total = 120
    for f in range(total):
        step = (f // 2) * 2
        t = step / total
        frame_tank(t)
        picked = step >= 96
        FLASH.hide_render = not (96 <= step < 104)
        FLASH.location = NOZ.location; FLASH.scale = (1 + (step - 96) * 0.35,) * 3
        NOZ.hide_render = picked
        for s in SPARK: s.hide_render = picked
        for ob in HUD['h_tank']:
            ob.hide_render = False
            if ob.type == 'FONT':
                if ob.data.body == '+1':
                    ob.hide_render = not picked
                elif 'СОПЛА' in ob.data.body:
                    ob.data.body = '◆ СОПЛА 7/32' if picked else '◆ СОПЛА 6/32'
        sc.render.filepath = os.path.join(OUT, f'f{f:04d}.png'); bpy.ops.render.render(write_still=True)
    print('RENDERED clip')
