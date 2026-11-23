"""UNBUILT / РАЗОБРАНО — style frames. Blender 4.0, EEVEE + Freestyle, no AI.
Run: xvfb-run -a blender -b --factory-startup -P style.py -- OUTDIR
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Euler, Quaternion

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp'
ONLY = sys.argv[sys.argv.index('--') + 2].split(',') if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 2 else None
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

PAL = dict(paper='#F3EAD7', grid='#E3D4B6', ink='#1D2A44', red='#FF4B2B', red_s='#C7341F',
           must='#F2B134', must_s='#C98A1C', cream='#FFF8EC', cream_s='#D8CCB2',
           teal='#2A9D8F', teal_s='#1E6F66', steel='#A3ACBE', steel_s='#6B7385',
           dark='#3B4256', dark_s='#232838', shadow='#E0D0AF', sect='#FBE2D6', white='#FFFFFF')


def lin(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), a)


def lighten(h, k):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join('%02X' % int(v + (255 - v) * k) for v in c)


# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 16
sc.eevee.use_soft_shadows = False
sc.eevee.shadow_cascade_size = '2048'
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.render.use_freestyle = True
sc.render.line_thickness_mode = 'ABSOLUTE'
sc.render.line_thickness = 1.0
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.02, 0.02, 1)

NOLINE = bpy.data.collections.new('NoLine'); sc.collection.children.link(NOLINE)
vl = sc.view_layers[0]; vl.use_freestyle = True
fs = vl.freestyle_settings; fs.crease_angle = math.radians(140)
ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('ink')
ls.select_by_visibility = True; ls.select_by_edge_types = True
ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
ls.select_by_collection = True; ls.collection = NOLINE; ls.collection_negation = 'EXCLUSIVE'
if ls.linestyle is None:
    ls.linestyle = bpy.data.linestyles.new('ink')
ls.linestyle.color = lin(PAL['ink'])[:3]
ls.linestyle.thickness = 3.4

FONT = bpy.data.fonts.load(FONT_PATH)

# camera basis (fixed iso-ish angle, 25 deg above horizon)
AZ = math.radians(35)
CAM_ROT = Euler((math.radians(65), 0, AZ))
M3 = CAM_ROT.to_matrix()
R = M3 @ Vector((1, 0, 0))          # screen right
UP = M3 @ Vector((0, 1, 0))         # screen up
BACK = M3 @ Vector((0, 0, 1))       # toward camera
NH = Vector((BACK.x, BACK.y, 0)).normalized()   # horizontal toward camera
Z = Vector((0, 0, 1))


def link(ob, noline=False):
    (NOLINE if noline else sc.collection).objects.link(ob)
    return ob


# ---------------------------------------------------------------- materials
MATS = {}


def toon(key, base, shade, dots=0.38):
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    dif = N.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = N.new('ShaderNodeShaderToRGB'); L.new(dif.outputs[0], s2r.inputs[0])
    bw = N.new('ShaderNodeRGBToBW'); L.new(s2r.outputs['Color'], bw.inputs['Color'])
    lit = N.new('ShaderNodeMath'); lit.operation = 'GREATER_THAN'; lit.inputs[1].default_value = 0.20
    L.new(bw.outputs[0], lit.inputs[0])
    hi = N.new('ShaderNodeMath'); hi.operation = 'GREATER_THAN'; hi.inputs[1].default_value = 0.80
    L.new(bw.outputs[0], hi.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = (81, 144, 0)
    L.new(tc.outputs['Window'], mul.inputs[0])
    fr = N.new('ShaderNodeVectorMath'); fr.operation = 'FRACTION'; L.new(mul.outputs[0], fr.inputs[0])
    sb = N.new('ShaderNodeVectorMath'); sb.operation = 'SUBTRACT'; sb.inputs[1].default_value = (0.5, 0.5, 0)
    L.new(fr.outputs[0], sb.inputs[0])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(sb.outputs[0], ln.inputs[0])
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.27
    L.new(ln.outputs['Value'], lt.inputs[0])
    dm = N.new('ShaderNodeMath'); dm.operation = 'MULTIPLY'; dm.inputs[1].default_value = dots
    L.new(lt.outputs[0], dm.inputs[0])
    sh = N.new('ShaderNodeMixRGB'); sh.inputs['Color1'].default_value = lin(shade)
    sh.inputs['Color2'].default_value = lin(PAL['ink']); L.new(dm.outputs[0], sh.inputs['Fac'])
    m1 = N.new('ShaderNodeMixRGB'); L.new(lit.outputs[0], m1.inputs['Fac'])
    L.new(sh.outputs['Color'], m1.inputs['Color1']); m1.inputs['Color2'].default_value = lin(base)
    m2 = N.new('ShaderNodeMixRGB'); L.new(hi.outputs[0], m2.inputs['Fac'])
    L.new(m1.outputs['Color'], m2.inputs['Color1']); m2.inputs['Color2'].default_value = lin(lighten(base, 0.35))
    em = N.new('ShaderNodeEmission'); L.new(m2.outputs['Color'], em.inputs['Color'])
    L.new(em.outputs[0], out.inputs['Surface'])
    MATS[key] = m
    return m


def flat(color):
    key = 'flat_' + color
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = lin(color); L.new(em.outputs[0], out.inputs['Surface'])
    MATS[key] = m
    return m


def hatch(key, base, line, spacing=16.0, width=0.28):
    m = bpy.data.materials.new(key); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); tc = N.new('ShaderNodeTexCoord')
    dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'
    dp.inputs[1].default_value = (1080 / spacing, 1920 / spacing, 0)
    L.new(tc.outputs['Window'], dp.inputs[0])
    fr = N.new('ShaderNodeMath'); fr.operation = 'FRACT'; L.new(dp.outputs['Value'], fr.inputs[0])
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
    L.new(fr.outputs[0], lt.inputs[0])
    mx = N.new('ShaderNodeMixRGB'); mx.inputs['Color1'].default_value = lin(base)
    mx.inputs['Color2'].default_value = lin(line); L.new(lt.outputs[0], mx.inputs['Fac'])
    em = N.new('ShaderNodeEmission'); L.new(mx.outputs['Color'], em.inputs['Color'])
    L.new(em.outputs[0], out.inputs['Surface'])
    return m


def paper_mat():
    m = bpy.data.materials.new('paper'); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); tc = N.new('ShaderNodeTexCoord')
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = (18, 32, 0)
    L.new(tc.outputs['Window'], mul.inputs[0])
    fr = N.new('ShaderNodeVectorMath'); fr.operation = 'FRACTION'; L.new(mul.outputs[0], fr.inputs[0])
    sp = N.new('ShaderNodeSeparateXYZ'); L.new(fr.outputs[0], sp.inputs[0])
    mn = N.new('ShaderNodeMath'); mn.operation = 'MINIMUM'
    L.new(sp.outputs['X'], mn.inputs[0]); L.new(sp.outputs['Y'], mn.inputs[1])
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.035
    L.new(mn.outputs[0], lt.inputs[0])
    mx = N.new('ShaderNodeMixRGB'); mx.inputs['Color1'].default_value = lin(PAL['paper'])
    mx.inputs['Color2'].default_value = lin(PAL['grid']); L.new(lt.outputs[0], mx.inputs['Fac'])
    em = N.new('ShaderNodeEmission'); L.new(mx.outputs['Color'], em.inputs['Color'])
    L.new(em.outputs[0], out.inputs['Surface'])
    return m


M = dict(
    red=toon('red', PAL['red'], PAL['red_s']), must=toon('must', PAL['must'], PAL['must_s']),
    cream=toon('cream', PAL['cream'], PAL['cream_s']), teal=toon('teal', PAL['teal'], PAL['teal_s']),
    steel=toon('steel', PAL['steel'], PAL['steel_s']), dark=toon('dark', PAL['dark'], PAL['dark_s'], dots=0.0),
    ink=toon('ink', PAL['ink'], PAL['ink'], dots=0.0),
)
SECT = hatch('sect', PAL['sect'], PAL['red'])


# ---------------------------------------------------------------- geometry
def mesh_obj(name, bm, mat, smooth=True, ang=35, noline=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
        me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(ang)
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), noline)


def lathe(name, prof, mat, segs=56):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi,
                   steps=segs, use_merge=True, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat)


def cyl(name, r1, r2, depth, mat, segs=32, noline=False, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    return mesh_obj(name, bm, mat, smooth=smooth, noline=noline)


def box(name, size, mat, loc=(0, 0, 0), noline=False):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    ob = mesh_obj(name, bm, mat, smooth=False, noline=noline); ob.location = loc
    return ob


def sphere(name, r, mat, loc=(0, 0, 0), scale=(1, 1, 1), noline=False):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=r)
    ob = mesh_obj(name, bm, mat, noline=noline); ob.location = loc; ob.scale = scale
    return ob


def rod(name, a, b, r, mat, segs=12, noline=False):
    a = Vector(a); b = Vector(b); d = b - a
    ob = cyl(name, r, r, d.length, mat, segs, noline=noline)
    ob.location = (a + b) / 2; ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return ob


def facing(ob, q_extra=None):
    q = NH.to_track_quat('Z', 'Y')
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q @ q_extra if q_extra else q
    return ob


def cut(ob, no, keep_negative=True, fill=None):
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=(0, 0, 0), plane_no=no,
                                 clear_outer=keep_negative, clear_inner=not keep_negative)
    if fill is not None:
        edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            me.materials.append(fill); idx = len(me.materials) - 1
            made = bmesh.ops.contextual_create(bm, geom=edges)
            for f in made['faces']:
                f.material_index = idx; f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    return ob


def dup(ob, name):
    n = ob.copy(); n.data = ob.data.copy(); n.name = name
    link(n); return n


# ---------------------------------------------------------------- pose system
PARTS = []
TAGS = {}


def tag(t, *obs):
    TAGS.setdefault(t, []).extend(obs)


def part(ob, off=(0, 0, 0), qaxis=None, a0=0.0, a1=0.0, s0=None, s1=None):
    PARTS.append(dict(ob=ob, loc=Vector(ob.location), off=Vector(off), qaxis=qaxis, a0=a0, a1=a1,
                      q0=ob.rotation_quaternion.copy() if ob.rotation_mode == 'QUATERNION' else None,
                      s0=s0, s1=s1))
    return ob


def pose(t):
    for p in PARTS:
        ob = p['ob']; ob.location = p['loc'] + p['off'] * t
        if p['qaxis'] is not None:
            ob.rotation_mode = 'QUATERNION'
            ob.rotation_quaternion = Quaternion(p['qaxis'], p['a0'] + (p['a1'] - p['a0']) * t)
        if p['s0'] is not None:
            ob.scale = Vector(p['s0']).lerp(Vector(p['s1']), t)


# ---------------------------------------------------------------- rocket (generic 3-stage with 4 side boosters)
CORE_PROF = [(0, 0.55), (0.46, 0.55), (0.5, 0.75), (0.5, 1.0), (0.62, 6.55), (0.62, 6.8), (0, 6.8)]
core_full = lathe('core_full', CORE_PROF, M['cream']); tag('assembled', core_full)
core_cut = lathe('core_cut', CORE_PROF, M['cream']); cut(core_cut, NH, keep_negative=True, fill=SECT)
tag('exploded', core_cut)
band = lathe('core_band', [(0, 6.0), (0.635, 6.0), (0.635, 6.25), (0, 6.25)], M['red'])
tag('assembled', band)
band_cut = lathe('core_band_cut', [(0, 6.0), (0.635, 6.0), (0.635, 6.25), (0, 6.25)], M['red'])
cut(band_cut, NH, keep_negative=True, fill=SECT); tag('exploded', band_cut)

lox = sphere('tank_lox', 0.40, M['teal'], loc=(0, 0, 5.0), scale=(1, 1, 2.1)); tag('exploded', lox)
ker = sphere('tank_ker', 0.40, M['must'], loc=(0, 0, 2.6), scale=(1, 1, 1.9)); tag('exploded', ker)
pipe = rod('pipe', (0, 0, 3.3), (0, 0, 4.2), 0.07, M['dark']); tag('exploded', pipe)


def bell(name, scale=1.0):
    s = scale
    return lathe(name, [(0.05 * s, 0.0), (0.07 * s, -0.06 * s), (0.13 * s, -0.30 * s), (0.15 * s, -0.36 * s)], M['dark'], segs=28)


def engine_cluster(prefix, center_xy, z, off, main_r=0.17, vern_r=0.40, n_vern=2, vern_dirs=None):
    cx, cy = center_xy; obs = []
    for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        b = bell(f'{prefix}_m{i}'); b.location = (cx + dx * main_r, cy + dy * main_r, z); obs.append(part(b, off))
    dirs = vern_dirs or [i * 2 * math.pi / n_vern for i in range(n_vern)]
    for i, a in enumerate(dirs):
        b = bell(f'{prefix}_v{i}', 0.55); b.location = (cx + math.cos(a) * vern_r, cy + math.sin(a) * vern_r, z + 0.05)
        obs.append(part(b, off))
    return obs


FRONT = math.atan2(NH.y, NH.x)
BOOST_ANG = [FRONT + math.radians(45 + 90 * k) for k in range(4)]
BOOST_PROF = [(0, 0.55), (0.5, 0.55), (0.56, 0.78), (0.44, 3.0), (0.22, 4.55), (0.07, 5.0), (0, 5.05)]
for k, a in enumerate(BOOST_ANG):
    e = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-math.sin(a), math.cos(a), 0))
    b = lathe(f'booster{k}', BOOST_PROF, M['red'])
    b.location = e * 0.98
    tilt = math.atan((0.98 - 0.62) / 5.0)
    b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = Quaternion(t, -tilt)
    part(b, off=e * 1.9 + Vector((0, 0, -0.25)), qaxis=t, a0=-tilt, a1=math.radians(24))
    engine_cluster(f'b{k}', (e.x * 0.98, e.y * 0.98), 0.55, e * 1.9 + Vector((0, 0, -0.95)),
                   vern_dirs=[a + math.pi / 2, a - math.pi / 2])
    # radial dashed guide
    for j in range(7):
        r0 = 0.75 + j * 0.42
        d = rod(f'guide{k}_{j}', e * r0 + Vector((0, 0, 1.2)), e * (r0 + 0.26) + Vector((0, 0, 1.2)), 0.028,
                flat(PAL['red']), noline=True)
        tag('exploded', d)

engine_cluster('core', (0, 0), 0.55, (0, 0, -1.1), vern_r=0.36, vern_dirs=[i * math.pi / 2 + math.pi / 4 for i in range(4)])

# interstage truss + third stage
truss = []
for i in range(8):
    a0 = i * math.pi / 4; a1 = a0 + math.pi / 4
    truss.append(part(rod(f'truss{i}', (0.55 * math.cos(a0), 0.55 * math.sin(a0), 6.8),
                          (0.55 * math.cos(a1), 0.55 * math.sin(a1), 7.15), 0.035, M['ink']), (0, 0, 0.55)))
st3 = part(lathe('stage3', [(0, 7.15), (0.6, 7.15), (0.62, 7.3), (0.62, 8.7), (0, 8.7)], M['cream']), (0, 0, 1.0))
st3b = part(lathe('stage3_band', [(0, 7.9), (0.635, 7.9), (0.635, 8.15), (0, 8.15)], M['red']), (0, 0, 1.0))

# spacecraft (generic capsule stack)
SC_OFF = (0, 0, 1.75)
svc = part(lathe('sc_service', [(0, 8.8), (0.42, 8.8), (0.44, 8.9), (0.44, 9.4), (0, 9.4)], M['steel']), SC_OFF)
dsc = part(lathe('sc_descent', [(0, 9.4), (0.43, 9.4), (0.40, 9.55), (0.27, 9.95), (0, 10.0)], M['teal']), SC_OFF)
orb = part(sphere('sc_orbital', 0.31, M['cream'], loc=(0, 0, 10.28)), SC_OFF)
for sgn in (-1, 1):
    p = box(f'sc_panel{sgn}', (0.95, 0.03, 0.34), M['must'])
    p.location = Vector((0, 0, 9.15)) + R * sgn * (0.44 + 0.5)
    p.rotation_euler = Euler((0, 0, AZ))
    part(p, SC_OFF, s0=(0.0, 1, 1), s1=(1, 1, 1)); tag('exploded', p)
    pr = rod(f'sc_panel_rod{sgn}', Vector((0, 0, 9.15)) + R * sgn * 0.44, Vector((0, 0, 9.15)) + R * sgn * 0.5, 0.03, M['ink'])
    part(pr, SC_OFF); tag('exploded', pr)

FAIR_PROF = [(0, 8.75), (0.70, 8.75), (0.74, 8.9), (0.74, 10.4), (0.47, 11.15), (0.18, 11.6), (0, 11.65)]
fair_full = lathe('fairing_full', FAIR_PROF, M['must']); tag('assembled', fair_full)
fl = lathe('fairing_L', FAIR_PROF, M['must']); cut(fl, R, keep_negative=True)
fr_ = lathe('fairing_R', FAIR_PROF, M['must']); cut(fr_, R, keep_negative=False)
part(fl, off=-R * 1.35 + Vector((0, 0, 1.2))); part(fr_, off=R * 1.35 + Vector((0, 0, 1.2)))
tag('exploded', fl, fr_)
tower = part(lathe('escape_tower', [(0, 11.6), (0.12, 11.6), (0.10, 12.2), (0.16, 12.25), (0.16, 12.6), (0.05, 12.9), (0, 12.95)], M['ink']), (0, 0, 2.9))

# center line (dash-dot), visible when exploded
zc = -1.7
while zc < 16.0:
    for ln_, gap in ((0.55, 0.16), (0.09, 0.16)):
        tag('exploded', rod('axis', (0, 0, zc), (0, 0, zc + ln_), 0.03, flat(PAL['red']), noline=True)); zc += ln_ + gap

# ground shadow
gs = cyl('ground_shadow', 1.9, 1.9, 0.01, flat(PAL['shadow']), segs=64, noline=True); gs.location = (0, 0, 0.0)

# ---------------------------------------------------------------- mascot: HEX (brass nut with one eye)
hex_root = bpy.data.objects.new('hex_root', None); link(hex_root)


def hx(ob):
    ob.parent = hex_root
    return ob


body = hx(facing(cyl('hex_body', 0.52, 0.52, 0.40, M['must'], segs=6, smooth=False), Quaternion((0, 0, 1), math.radians(30))))
hole = hx(facing(cyl('hex_hole', 0.25, 0.25, 1.2, M['ink'], segs=40))); hole.hide_render = True
bm_ = body.modifiers.new('hole', 'BOOLEAN'); bm_.operation = 'DIFFERENCE'; bm_.object = hole; bm_.solver = 'EXACT'
bv = body.modifiers.new('bevel', 'BEVEL'); bv.width = 0.035; bv.segments = 2; bv.limit_method = 'ANGLE'
hx(sphere('hex_eye', 0.235, M['cream'], loc=(0, 0, 0)))
hx(sphere('hex_pupil', 0.105, M['ink'], loc=NH * 0.17 + Z * 0.035 + R * 0.02))
hx(sphere('hex_glint', 0.032, flat(PAL['white']), loc=NH * 0.28 + Z * 0.075 - R * 0.015, noline=True))
hx(facing(box('hex_brow', (0.30, 0.055, 0.05), M['ink']), Quaternion((0, 0, 1), math.radians(-14)))).location = NH * 0.22 + Z * 0.44 + R * 0.03
for s in (-1, 1):
    hx(rod('hex_leg', R * s * 0.16 - Z * 0.34, R * s * 0.19 - Z * 0.72, 0.05, M['ink']))
    hx(sphere('hex_foot', 0.1, M['ink'], loc=R * s * 0.19 - Z * 0.76 + NH * 0.05, scale=(1, 1, 0.6)))
hx(rod('hex_arm_r', R * 0.46, R * 0.74 + Z * 0.28, 0.045, M['ink']))
wrench = [hx(rod('wr_handle', R * 0.74 + Z * 0.15, R * 0.74 + Z * 0.98, 0.055, M['steel']))]
head = hx(facing(cyl('wr_head', 0.19, 0.19, 0.07, M['steel'], segs=40))); head.location = R * 0.74 + Z * 1.12
wh = hx(facing(cyl('wr_hole', 0.09, 0.09, 0.5, M['ink'], segs=6))); wh.location = head.location; wh.hide_render = True
mb = head.modifiers.new('h', 'BOOLEAN'); mb.operation = 'DIFFERENCE'; mb.object = wh; mb.solver = 'EXACT'
wrench.append(head)
arm_down = hx(rod('hex_arm_l_down', -R * 0.46, -R * 0.70 - Z * 0.30, 0.045, M['ink']))
arm_up = hx(rod('hex_arm_l_up', -R * 0.46, -R * 0.74 + Z * 0.30, 0.045, M['ink']))
bolt = [hx(cyl('bolt_head', 0.15, 0.15, 0.11, M['steel'], segs=6, smooth=False)),
        hx(rod('bolt_shaft', -R * 0.74 + Z * 0.52, -R * 0.74 + Z * 0.06, 0.065, M['steel']))]
bolt[0].location = -R * 0.74 + Z * 0.58
for i in range(4):
    bolt.append(hx(cyl(f'bolt_thread{i}', 0.08, 0.08, 0.025, M['steel'], segs=24)))
    bolt[-1].location = -R * 0.74 + Z * (0.12 + i * 0.09)
hs = hx(cyl('hex_shadow', 0.55, 0.55, 0.01, flat(PAL['shadow']), segs=48, noline=True)); hs.location = -Z * 0.835
tag('arm_down', arm_down); tag('arm_up', arm_up); tag('bolt', *bolt)
HEX_POS = NH * 4.4 + Z * 0.85

# ---------------------------------------------------------------- camera + paper
cam_d = bpy.data.cameras.new('cam'); cam_d.type = 'ORTHO'; cam_d.clip_end = 400
cam = link(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
paper = bpy.data.objects.new('paper', bpy.data.meshes.new('paper'))
bmp = bmesh.new(); bmesh.ops.create_grid(bmp, x_segments=1, y_segments=1, size=1.0); bmp.to_mesh(paper.data); bmp.free()
paper.data.materials.append(paper_mat()); link(paper, noline=True)
paper.parent = cam; paper.location = (0, 0, -150); paper.scale = (40, 40, 1)

sun_d = bpy.data.lights.new('sun', 'SUN'); sun_d.energy = 3.2; sun_d.angle = 0.005
sun = link(bpy.data.objects.new('sun', sun_d))
ldir = (-R * 0.9 + NH * 0.7 + Z * 1.3).normalized()
sun.rotation_mode = 'QUATERNION'; sun.rotation_quaternion = (-ldir).to_track_quat('-Z', 'Y')


def set_cam(target, scale):
    cam.rotation_euler = CAM_ROT; cam.location = Vector(target) + BACK * 80; cam_d.ortho_scale = scale


# ---------------------------------------------------------------- overlays (text, labels, plates)
def txt(body_, loc, size, color, align='CENTER', noline=True, name='txt'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body_; cu.font = FONT; cu.size = size
    cu.align_x = align; cu.align_y = 'CENTER'; cu.space_line = 0.95
    cu.materials.append(flat(color))
    ob = link(bpy.data.objects.new(name, cu), noline)
    ob.location = loc; ob.rotation_euler = CAM_ROT
    return ob


def plate(loc, w, h, color, name='plate'):
    ob = box(name, (w, h, 0.01), flat(color), noline=True)
    ob.location = loc; ob.rotation_euler = CAM_ROT
    return ob


def disc(loc, r, color):
    ob = cyl('disc', r, r, 0.02, flat(color), segs=40, noline=True)
    ob.location = loc; ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = BACK.to_track_quat('Z', 'Y')
    return ob


def scr(target, x, y, depth=12):
    return Vector(target) + R * x + UP * y + BACK * depth


def title(tagname, target, y, text_, size, w, h, fg=PAL['cream'], bg=PAL['ink']):
    tag(tagname, plate(scr(target, 0, y, 14), w, h, bg), txt(text_, scr(target, 0, y, 14.05), size, fg))


def bug(tagname, target, x, y, text_, size):
    w = len(text_) * size * 0.66 + size * 0.8
    tag(tagname, plate(scr(target, x + w / 2, y, 14), w, size * 1.7, PAL['red']),
        txt(text_, scr(target, x + w / 2, y, 14.05), size, PAL['cream']))


def label(tagname, target, num, anchor, x, y, text_, size=0.40, side='L'):
    L = scr(target, x, y, 10)
    a = Vector(anchor)
    objs = [rod('leader', a, L, 0.022, flat(PAL['ink']), noline=True),
            sphere('anchor', 0.075, flat(PAL['ink']), loc=a, noline=True),
            disc(L + BACK * 0.02, 0.27, PAL['red']),
            txt(str(num), L + BACK * 0.05, 0.30, PAL['cream'])]
    if side == 'L':
        objs.append(txt(text_, L + R * 0.38 + BACK * 0.05, size, PAL['ink'], align='LEFT'))
    else:
        objs.append(txt(text_, L - R * 0.38 + BACK * 0.05, size, PAL['ink'], align='RIGHT'))
    tag(tagname, *objs)


TA = Vector((0, 0, 6.6)); SA = 17.0      # frame A camera
TB = Vector((0, 0, 7.0)); SB = 20.0      # frames B/C camera
TD = HEX_POS + Z * 0.15; SD = 4.8        # frame D camera

title('title_ru', TA, 7.0, 'ПОЧЕМУ У ЭТОЙ РАКЕТЫ\n32 СОПЛА?', 0.6, 9.0, 1.7)
title('title_en', TA, 7.0, 'WHY DOES THIS ROCKET\nHAVE 32 NOZZLES?', 0.6, 9.0, 1.7)
bug('bug_ru_A', TA, -4.5, 8.22, 'РАЗОБРАНО · №001', 0.24)
bug('bug_en_A', TA, -4.5, 8.22, 'UNBUILT · #001', 0.24)
title('title_ru_B', TB, 8.55, 'ЧТО ВНУТРИ?', 0.8, 6.4, 1.3)
title('title_en_B', TB, 8.55, "WHAT'S INSIDE?", 0.8, 7.4, 1.3)
bug('bug_ru_B', TB, -5.45, 9.55, 'РАЗОБРАНО · №001', 0.26)
bug('bug_en_B', TB, -5.45, 9.55, 'UNBUILT · #001', 0.26)

e_rf = Vector((math.cos(BOOST_ANG[0]), math.sin(BOOST_ANG[0]), 0))
ANCH = dict(
    fair=Vector((0, 0, 10.6 + 1.2)) + R * (1.35 + 0.74),
    craft=Vector((0, 0, 9.7 + 1.75)) + NH * 0.42,
    lox=Vector((0, 0, 5.2)) + NH * 0.40,
    ker=Vector((0, 0, 2.6)) + NH * 0.40,
    boost=e_rf * (0.98 + 1.9) + Vector((0, 0, 2.2)) + NH * 0.45,
    noz=Vector((0, 0, -0.85)) + NH * 0.15,
)
LBL = [  # num, anchor, x, y, side, ru, en
    (1, 'craft', -5.05, 6.2, 'L', 'Корабль', 'Spacecraft'),
    (2, 'fair', 5.05, 7.0, 'R', 'Обтекатель', 'Fairing'),
    (3, 'lox', -5.05, 0.6, 'L', 'Бак кислорода', 'Oxygen tank'),
    (4, 'ker', 5.05, -0.9, 'R', 'Бак керосина', 'Kerosene tank'),
    (5, 'boost', 5.05, -9.25, 'R', 'Боковой блок ×4', 'Side booster ×4'),
    (6, 'noz', -5.05, -9.25, 'L', '32 сопла', '32 nozzles'),
]
for n, an, x, y, side, ru, en in LBL:
    label('labels_ru', TB, n, ANCH[an], x, y, ru, side=side)
    label('labels_en', TB, n, ANCH[an], x, y, en, side=side)

title('title_ru_D', TD, 1.78, 'А ЭТА ДЕТАЛЬ\nОТКУДА?', 0.22, 2.3, 0.62)
title('title_en_D', TD, 1.78, 'WAIT… WHERE DOES\nTHIS ONE GO?', 0.2, 2.4, 0.6)
title('cta_ru_D', TD, -1.98, 'ОТВЕТ — В СЛЕДУЮЩЕЙ СЕРИИ', 0.105, 2.35, 0.26, bg=PAL['red'])
title('cta_en_D', TD, -1.98, 'ANSWER IN THE NEXT EPISODE', 0.105, 2.35, 0.26, bg=PAL['red'])

ALL_TAGS = list(TAGS.keys())


def show(*visible):
    for t, obs in TAGS.items():
        for ob in obs:
            ob.hide_render = t not in visible


FRAMES = {
    'A_hook_ru': (0.0, TA, SA, ['assembled', 'title_ru', 'bug_ru_A', 'arm_down']),
    'A_hook_en': (0.0, TA, SA, ['assembled', 'title_en', 'bug_en_A', 'arm_down']),
    'B_inside_ru': (1.0, TB, SB, ['exploded', 'labels_ru', 'title_ru_B', 'bug_ru_B', 'arm_down']),
    'C_inside_en': (1.0, TB, SB, ['exploded', 'labels_en', 'title_en_B', 'bug_en_B', 'arm_down']),
    'D_end_ru': (1.0, TD, SD, ['exploded', 'title_ru_D', 'cta_ru_D', 'arm_up', 'bolt']),
}

hex_root.location = HEX_POS
for name, (t, target, scale, vis) in FRAMES.items():
    if ONLY and name not in ONLY:
        continue
    pose(t); show(*vis)
    for ob in wrench:
        ob.hide_render = False
    set_cam(target, scale)
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name)
