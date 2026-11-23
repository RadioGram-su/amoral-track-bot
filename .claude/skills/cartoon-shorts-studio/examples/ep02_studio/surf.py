"""Studio-look test: Hex surfs a data packet through a neon fiber tunnel, bursts out over a night AI campus.
Blender 4.0 EEVEE (PBR + SSR + bloom + volumetrics + motion blur). No AI imagery.
Run: xvfb-run -a blender -b --factory-startup -P surf.py -- OUTDIR stills|anim
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Euler, Quaternion

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT = ARGS[0]; MODE = ARGS[1] if len(ARGS) > 1 else 'stills'
random.seed(5)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
FPS = 30; DUR = 4.6; NF = int(DUR * FPS)
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = NF - 1
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
for k, v in dict(taa_render_samples=12, use_bloom=True, bloom_threshold=1.0, bloom_intensity=0.045, bloom_radius=6.0,
                 bloom_knee=0.5, use_ssr=True, ssr_quality=0.25, use_gtao=True, gtao_distance=0.8,
                 use_motion_blur=True, motion_blur_shutter=0.35, motion_blur_steps=1,
                 volumetric_start=0.3, volumetric_end=420, volumetric_tile_size='8', volumetric_samples=32,
                 use_volumetric_lights=True, use_volumetric_shadows=False, use_soft_shadows=False).items():
    try: setattr(ee, k, v)
    except Exception as e: print('skip', k, e)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 540, 960, 100
try:
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
except Exception as e:
    print('look', e)


def lin(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), a)


# ------------------------------------------------------------------ materials
def pbr(base, metal=0.0, rough=0.5, emit=None, es=0.0, coat=0.0):
    m = bpy.data.materials.new('pbr'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(base); b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = lin(emit); b.inputs['Emission Strength'].default_value = es
    return m


def emis(color, s):
    m = bpy.data.materials.new('em'); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    o = N.new('ShaderNodeOutputMaterial'); e = N.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = lin(color); e.inputs['Strength'].default_value = s
    L.new(e.outputs[0], o.inputs['Surface']); return m


def trail_mat(color, s, axis='Y'):
    m = bpy.data.materials.new('trail'); m.use_nodes = True; m.blend_method = 'BLEND'; m.shadow_method = 'NONE'
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    o = N.new('ShaderNodeOutputMaterial'); tc = N.new('ShaderNodeTexCoord'); sp = N.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs['Generated'], sp.inputs[0])
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.2; L.new(sp.outputs[axis], pw.inputs[0])
    edge = N.new('ShaderNodeMath'); edge.operation = 'PINGPONG'; edge.inputs[1].default_value = 0.5; L.new(sp.outputs['X'], edge.inputs[0])
    ed2 = N.new('ShaderNodeMath'); ed2.operation = 'MULTIPLY'; ed2.inputs[1].default_value = 2.0; L.new(edge.outputs[0], ed2.inputs[0])
    fac = N.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; L.new(pw.outputs[0], fac.inputs[0]); L.new(ed2.outputs[0], fac.inputs[1])
    tr = N.new('ShaderNodeBsdfTransparent'); e = N.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = lin(color); e.inputs['Strength'].default_value = s
    mx = N.new('ShaderNodeMixShader'); L.new(fac.outputs[0], mx.inputs['Fac']); L.new(tr.outputs[0], mx.inputs[1]); L.new(e.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], o.inputs['Surface']); return m


# ------------------------------------------------------------------ geometry
def put(ob): sc.collection.objects.link(ob); return ob


def mk(name, bm, mat, smooth=True, ang=35):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
        me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(ang)
    if mat: me.materials.append(mat)
    return put(bpy.data.objects.new(name, me))


def lathe(name, prof, mat, segs=48, smooth=True):
    bm = bmesh.new(); vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=segs, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mk(name, bm, mat, smooth)


def cyl(name, r1, r2, d, mat, segs=32, smooth=True):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=d)
    return mk(name, bm, mat, smooth)


def box(name, size, mat, loc=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    ob = mk(name, bm, mat, smooth=False); ob.location = loc; return ob


def sph(name, r, mat, loc=(0, 0, 0), seg=32, half=None):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    if half:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1),
                               clear_inner=(half == 'top'), clear_outer=(half == 'bottom'))
    ob = mk(name, bm, mat); ob.location = loc; return ob


def bevel(ob, w=0.04, s=3):
    m = ob.modifiers.new('bv', 'BEVEL'); m.width = w; m.segments = s; m.limit_method = 'ANGLE'; return ob


def parent(c, p): c.parent = p; return c


# ================================================================== FIBER TUNNEL (along +Y, length 156)
TL = 156.0; MOD = 6.0; CNT = int(TL / MOD)
wall_m = pbr('#070A12', metal=0.6, rough=0.32)
mods = []
mods.append(lathe('wall', [(3.25, 0), (3.25, MOD)], wall_m, segs=8, smooth=False))
mods.append(lathe('ring', [(2.95, 5.55), (3.25, 5.55), (3.25, 5.85), (2.95, 5.85), (2.95, 5.55)], emis('#35E0FF', 2.6), segs=8, smooth=False))
for k in range(8):
    a = math.radians(22.5 + 45 * k)
    s = box('strip', (0.05, 0.05, MOD * 0.92), emis('#FF3EC8' if k % 2 else '#35E0FF', 2.8), (math.cos(a) * 3.0, math.sin(a) * 3.0, MOD / 2))
    mods.append(s)
for ob in mods:
    ob.rotation_euler = (math.radians(-90), 0, 0)
    ar = ob.modifiers.new('arr', 'ARRAY'); ar.count = CNT; ar.use_relative_offset = False
    ar.use_constant_offset = True; ar.constant_offset_displace = (0, 0, MOD)
portal = cyl('portal', 3.3, 3.3, 0.05, emis('#FFFFFF', 30.0), segs=8, smooth=False)
portal.rotation_euler = (math.radians(90), 0, 0); portal.location = (0, TL + 0.3, 0)
cols = ['#35E0FF', '#35E0FF', '#FF3EC8', '#FFFFFF', '#7B5CFF']
for i in range(320):
    a = random.uniform(0, 2 * math.pi); r = random.uniform(0.4, 2.7); y = random.uniform(6, TL - 2)
    ln = random.choice([0.08, 0.08, 0.5, 1.2])
    box('bit', (0.06, ln, 0.06), emis(random.choice(cols), random.uniform(3, 7)), (math.cos(a) * r, y, math.sin(a) * r))
FONT = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')
for i in range(60):
    cu = bpy.data.curves.new('g', 'FONT'); cu.body = random.choice(['0', '1', '01', '{ }', '</>', '10', '#']); cu.font = FONT
    cu.size = random.uniform(0.25, 0.6); cu.align_x = 'CENTER'; cu.materials.append(emis(random.choice(cols[:3]), 4.0))
    g = put(bpy.data.objects.new('g', cu)); a = random.uniform(0, 2 * math.pi); r = random.uniform(1.4, 2.8)
    g.location = (math.cos(a) * r, random.uniform(6, TL), math.sin(a) * r); g.rotation_euler = (math.radians(90), 0, math.radians(180))

# ================================================================== NIGHT CAMPUS (below, ahead)
GZ = -95.0; CY = 360.0
gm = bpy.data.materials.new('ground'); gm.use_nodes = True
N = gm.node_tree.nodes; L = gm.node_tree.links; b = N['Principled BSDF']
b.inputs['Base Color'].default_value = lin('#07090F'); b.inputs['Roughness'].default_value = 0.85
tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 0.3
L.new(tc.outputs['Object'], vo.inputs['Vector'])
lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.09; L.new(vo.outputs['Distance'], lt.inputs[0])
ln_ = N.new('ShaderNodeVectorMath'); ln_.operation = 'LENGTH'; L.new(tc.outputs['Object'], ln_.inputs[0])
far = N.new('ShaderNodeMath'); far.operation = 'GREATER_THAN'; far.inputs[1].default_value = 180; L.new(ln_.outputs['Value'], far.inputs[0])
mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(lt.outputs[0], mm.inputs[0]); L.new(far.outputs[0], mm.inputs[1])
es = N.new('ShaderNodeMath'); es.operation = 'MULTIPLY'; es.inputs[1].default_value = 9.0; L.new(mm.outputs[0], es.inputs[0])
b.inputs['Emission Color'].default_value = lin('#FFB25C'); L.new(es.outputs[0], b.inputs['Emission Strength'])
bmg = bmesh.new(); bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=5000)
ground = mk('ground', bmg, gm, smooth=False); ground.location = (0, CY, GZ)
for x in range(-160, 161, 32):
    box('road', (3, 340, 0.05), pbr('#15171D', rough=0.4), (x, CY, GZ + 0.03))
    for y in range(int(CY - 170), int(CY + 170), 14):
        box('lamp', (0.4, 0.4, 0.4), emis('#FFB25C', 25), (x + 2.2, y, GZ + 6))
hall_m = pbr('#1A1F2B', metal=0.4, rough=0.45)
UPLINK = None
for ix in range(-2, 3):
    for iy in range(-2, 3):
        cx, cy = ix * 56, CY + iy * 62
        hh = random.choice([14, 18, 24]); box('hall', (46, 34, hh), hall_m, (cx, cy, GZ + hh / 2))
        for sy in (-1, 1):
            box('win', (44, 0.2, 0.9), emis('#3BE6FF', 6.0), (cx, cy + sy * 17.05, GZ + 9))
            box('win', (44, 0.2, 0.5), emis('#7B5CFF', 5.0), (cx, cy + sy * 17.05, GZ + 5))
        for k in range(6):
            box('chill', (5, 4, 2), pbr('#2A3140', metal=0.5, rough=0.4), (cx - 18 + k * 7.2, cy - 8, GZ + 15))
            cyl('fanl', 1.6, 1.6, 0.1, emis('#3BE6FF', 1.5), segs=16).location = (cx - 18 + k * 7.2, cy - 8, GZ + 16.05)
        for sx in (-1, 1):
            for sy in (-1, 1):
                sph('red', 0.35, emis('#FF2A2A', 30), (cx + sx * 22.5, cy + sy * 16.5, GZ + 14.6), seg=8)
        if ix == 0 and iy == 0:
            UPLINK = cyl('uplink', 2.2, 2.2, 220, trail_mat('#35E0FF', 6.0, axis='Z'), segs=24); UPLINK.location = (cx, cy, GZ + 110)
for i in range(7):
    v = put(bpy.data.objects.new('steam', bpy.data.meshes.new('s')))
    bms = bmesh.new(); bmesh.ops.create_cube(bms, size=1.0); bms.to_mesh(v.data); bms.free()
    vm = bpy.data.materials.new('vol'); vm.use_nodes = True
    vn = vm.node_tree.nodes; vn.remove(vn['Principled BSDF']); pv = vn.new('ShaderNodeVolumePrincipled')
    pv.inputs['Density'].default_value = 0.08; pv.inputs['Color'].default_value = (0.8, 0.85, 0.95, 1)
    vm.node_tree.links.new(pv.outputs[0], vn['Material Output'].inputs['Volume']); v.data.materials.append(vm)
    v.location = (random.uniform(-110, 110), CY + random.uniform(-120, 120), GZ + 30); v.scale = (8, 8, 30)

# world: night gradient + stars + light haze
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
WN = w.node_tree.nodes; WL = w.node_tree.links; bg = WN['Background']
wtc = WN.new('ShaderNodeTexCoord'); sep = WN.new('ShaderNodeSeparateXYZ'); WL.new(wtc.outputs['Generated'], sep.inputs[0])
ramp = WN.new('ShaderNodeValToRGB'); WL.new(sep.outputs['Z'], ramp.inputs['Fac'])
ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = lin('#2A1E5C')
ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = lin('#03040A')
vs = WN.new('ShaderNodeTexVoronoi'); vs.inputs['Scale'].default_value = 260; WL.new(wtc.outputs['Generated'], vs.inputs['Vector'])
st = WN.new('ShaderNodeMath'); st.operation = 'LESS_THAN'; st.inputs[1].default_value = 0.035; WL.new(vs.outputs['Distance'], st.inputs[0])
ad = WN.new('ShaderNodeMixRGB'); ad.blend_type = 'ADD'; WL.new(st.outputs[0], ad.inputs['Fac'])
WL.new(ramp.outputs['Color'], ad.inputs['Color1']); ad.inputs['Color2'].default_value = (1, 1, 1, 1)
WL.new(ad.outputs['Color'], bg.inputs['Color'])
vsc = WN.new('ShaderNodeVolumeScatter'); vsc.inputs['Density'].default_value = 0.0045; vsc.inputs['Anisotropy'].default_value = 0.3
WL.new(vsc.outputs[0], WN['World Output'].inputs['Volume'])

# ================================================================== HEX v2 (faces +Y)
brass = pbr('#D9A54C', metal=1.0, rough=0.28); brass_d = pbr('#8F6420', metal=1.0, rough=0.4)
rubber = pbr('#1C2130', rough=0.55, coat=0.3); white = pbr('#F4F6FA', rough=0.12, coat=0.6); black = pbr('#05060A', rough=0.08, coat=1.0)
HEX = put(bpy.data.objects.new('hex', None))
body = parent(bevel(cyl('body', 0.55, 0.55, 0.44, brass, segs=6, smooth=True), 0.06, 3), HEX)
body.rotation_euler = (math.radians(90), math.radians(30), 0)
rim = parent(lathe('rim', [(0.30, -0.02), (0.36, -0.02), (0.36, 0.03), (0.30, 0.03), (0.30, -0.02)], brass_d, segs=32), HEX)
rim.rotation_euler = (math.radians(-90), 0, 0); rim.location = (0, 0.22, 0)
EYE = parent(put(bpy.data.objects.new('eyepiv', None)), HEX); EYE.location = (0, 0.12, 0.0)
parent(sph('eye', 0.27, white), EYE)
iris = parent(cyl('iris', 0.135, 0.135, 0.02, pbr('#062A33', rough=0.2, emit='#2CF0FF', es=4.0), segs=32), EYE)
iris.rotation_euler = (math.radians(90), 0, 0); iris.location = (0, 0.262, 0)
pup = parent(cyl('pupil', 0.065, 0.065, 0.022, black, segs=24), EYE); pup.rotation_euler = (math.radians(90), 0, 0); pup.location = (0, 0.275, 0)
parent(sph('glint', 0.028, emis('#FFFFFF', 8), (-0.06, 0.27, 0.07), seg=8), EYE)
LID_U = parent(sph('lidu', 0.29, brass, half='top'), HEX); LID_U.location = (0, 0.12, 0)
LID_D = parent(sph('lidd', 0.29, brass, half='bottom'), HEX); LID_D.location = (0, 0.12, 0)
brow = parent(bevel(box('brow', (0.34, 0.07, 0.07), rubber), 0.02, 2), HEX)
LIMBS = {k: parent(cyl(k, 0.06, 0.06, 1.0, rubber, segs=12), HEX) for k in ('armL', 'armR', 'legL', 'legR')}
HANDS = {k: parent(sph(k, 0.095, rubber, seg=12), HEX) for k in ('handL', 'handR')}
FEET = {k: parent(bevel(box(k, (0.22, 0.32, 0.12), rubber), 0.04, 2), HEX) for k in ('footL', 'footR')}
for ob in LIMBS.values():
    ob.rotation_mode = 'QUATERNION'

BOARD = put(bpy.data.objects.new('board', None))
parent(bevel(cyl('deck', 0.9, 0.9, 0.1, pbr('#101522', metal=0.6, rough=0.18, coat=1.0), segs=6, smooth=True), 0.03, 2), BOARD).rotation_euler = (0, 0, math.radians(30))
parent(lathe('deckrim', [(0.86, -0.07), (0.95, -0.07), (0.95, -0.02), (0.86, -0.02), (0.86, -0.07)], emis('#35E0FF', 10), segs=6, smooth=False), BOARD).rotation_euler = (0, 0, math.radians(30))
tr = parent(box('trail', (1.1, 16, 0.01), trail_mat('#35E0FF', 1.3)), BOARD); tr.location = (0, -8.4, -0.05)
tr2 = parent(box('trail2', (0.35, 10, 0.01), trail_mat('#FF3EC8', 2.6)), BOARD); tr2.location = (0, -5.4, -0.02)
ld = bpy.data.lights.new('under', 'POINT'); ld.energy = 600; ld.color = lin('#35E0FF')[:3]; ld.shadow_soft_size = 0.4
parent(put(bpy.data.objects.new('under', ld)), BOARD).location = (0, 0, -0.5)
lr = bpy.data.lights.new('rim', 'POINT'); lr.energy = 1400; lr.color = lin('#FF3EC8')[:3]
RIM = parent(put(bpy.data.objects.new('rim', lr)), HEX); RIM.location = (-1.3, -1.2, 1.2)

cam_d = bpy.data.cameras.new('cam'); cam_d.clip_start = 0.05; cam_d.clip_end = 3000; cam_d.sensor_width = 36
cam = put(bpy.data.objects.new('cam', cam_d)); sc.camera = cam; cam.rotation_mode = 'QUATERNION'
lf = bpy.data.lights.new('key', 'AREA'); lf.energy = 140; lf.size = 1.2; lf.color = (1.0, 0.93, 0.85)
parent(put(bpy.data.objects.new('key', lf)), cam).location = (0.9, 0.8, 0.2)


# ================================================================== animation (keyed every frame)
def sm(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
def seg(t, a, b): return min(max((t - a) / (b - a), 0), 1)


T_EXIT = TL / 60.0


def hex_pos(t):
    if t < T_EXIT:
        return Vector((0.35 * math.sin(2.2 * t), 60 * t, 0.12 * math.sin(5 * t)))
    d = t - T_EXIT
    return Vector((0.35 * math.sin(2.2 * t), TL + 52 * d, -9 * d * d))


def rod(ob, a, b):
    d = b - a; ob.location = (a + b) / 2; ob.rotation_quaternion = d.to_track_quat('Z', 'Y'); ob.scale = (1, 1, d.length)


def key(ob, *props):
    for p in props: ob.keyframe_insert(p)


for f in range(NF):
    t = f / FPS; sc.frame_set(f)
    hp = hex_pos(t); roll = -0.22 * math.cos(2.2 * t); pitch = -0.12 if t < T_EXIT else -0.35 * sm(seg(t, T_EXIT, T_EXIT + 0.6)) - 0.12
    HEX.location = hp; HEX.rotation_euler = (pitch, roll, 0); key(HEX, 'location', 'rotation_euler')
    BOARD.location = hp + Vector((0, 0, -0.9)); BOARD.rotation_euler = (pitch * 0.6, roll * 1.3, 0); key(BOARD, 'location', 'rotation_euler')
    # limbs: surf stance, arms wobble
    wob = math.sin(6 * t); wob2 = math.sin(6 * t + 1.7)
    hl = Vector((-0.95, 0.05, 0.25 + 0.1 * wob)); hr = Vector((0.92, -0.05, 0.38 + 0.1 * wob2))
    rod(LIMBS['armL'], Vector((-0.5, 0, 0.05)), hl); rod(LIMBS['armR'], Vector((0.5, 0, 0.05)), hr)
    fl = Vector((-0.34, 0.08, -0.80)); fr = Vector((0.34, -0.12, -0.80))
    rod(LIMBS['legL'], Vector((-0.18, 0, -0.3)), fl + Vector((0, 0, 0.06))); rod(LIMBS['legR'], Vector((0.18, 0, -0.3)), fr + Vector((0, 0, 0.06)))
    HANDS['handL'].location = hl; HANDS['handR'].location = hr; FEET['footL'].location = fl; FEET['footR'].location = fr
    for ob in LIMBS.values(): key(ob, 'location', 'rotation_quaternion', 'scale')
    for ob in list(HANDS.values()) + list(FEET.values()): key(ob, 'location')
    # camera
    shake = Vector((math.sin(t * 13.1) * 0.03 + math.sin(t * 29.3) * 0.015, 0, math.sin(t * 11.7) * 0.03))
    if t < 2.15:
        cp = hp + Vector((0.55, 2.7, 0.35)) + shake; tgt = hp + Vector((0.1, 0, 0.0)); lens = 30 - 6 * sm(seg(t, 0, 0.45))
    else:
        u = sm(seg(t, 2.15, 2.75)); ang = math.pi * u
        rad = 2.7 + 0.6 * u
        cp = hp + Vector((0.55 * math.cos(ang) + 1.0 * math.sin(ang), rad * math.cos(ang), 0.35 + 1.0 * u)) + shake * (1 - 0.6 * u)
        tgt = hp.lerp(hp + Vector((0, 40, -33)), u)
        lens = 24 - 6 * sm(seg(t, 2.4, 2.8)) + 3 * sm(seg(t, 3.2, 4.6))
    cam.location = cp; cam.rotation_quaternion = (tgt - cp).to_track_quat('-Z', 'Y'); cam_d.lens = lens
    key(cam, 'location', 'rotation_quaternion'); cam_d.keyframe_insert('lens')
    # eye: look at camera, blink at 1.0s, squint at exit flash
    R = Euler(HEX.rotation_euler).to_matrix()
    look_tgt = cp if t < 2.4 else hp + Vector((0, 40, -30))
    ld_ = R.transposed() @ (look_tgt - (hp + R @ EYE.location))
    EYE.rotation_mode = 'QUATERNION'; EYE.rotation_quaternion = ld_.to_track_quat('Y', 'Z'); key(EYE, 'rotation_quaternion')
    blink = max(0.0, 1 - abs(t - 1.0) / 0.07)
    squint = sm(seg(t, 2.45, 2.6)) * (1 - sm(seg(t, 2.9, 3.1)))
    close = max(blink, 0.55 * squint)
    LID_U.rotation_euler = (math.radians(48 - 118 * close), 0, 0); LID_D.rotation_euler = (math.radians(-48 + 70 * close), 0, 0)
    key(LID_U, 'rotation_euler'); key(LID_D, 'rotation_euler')
    brow.location = (0.02, 0.24, 0.47 + 0.03 * math.sin(t * 3)); brow.rotation_euler = (0, math.radians(-10 + 8 * squint), 0)
    key(brow, 'location', 'rotation_euler')

if MODE == 'stills':
    for tt in (0.9, 3.6):
        sc.frame_set(int(tt * FPS)); sc.render.filepath = os.path.join(OUT, f'still_{tt:.2f}.png')
        bpy.ops.render.render(write_still=True); print('RENDERED', tt)
else:
    sc.render.filepath = os.path.join(OUT, 'f####'); sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True); print('RENDERED anim')
