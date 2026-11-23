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


