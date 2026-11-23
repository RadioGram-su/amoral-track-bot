"""Full Short shots (studio look). Blender 4.0 EEVEE. No AI imagery.
Run: xvfb-run -a blender -b --factory-startup -P short.py -- OUTDIR SHOT [still]
SHOT in: dive hall chip scale heat cool power ret
"""
import json
ST = '/tmp/claude-0/-home-user-amoral-track-bot/f91e2272-a479-5871-8b79-e1da23093bfd/scratchpad/studio'
exec(open(ST + '/kit.py', encoding='utf-8').read())
SHOT = ARGS[1]; STILL = len(ARGS) > 2 and ARGS[2] == 'still'
TLJ = json.load(open(ST + '/timeline.json', encoding='utf-8'))
S0, S1 = TLJ['shots'][SHOT]['start'], TLJ['shots'][SHOT]['end']
F0 = round(S0 * FPS); F1 = round(S1 * FPS) - 1
DUR_S = S1 - S0
random.seed(hash(SHOT) % 1000)
try: ee.motion_blur_position = 'START'
except Exception: pass


def sm(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
def seg(t, a, b): return min(max((t - a) / (b - a), 0), 1)
def rod(ob, a, b): d = b - a; ob.location = (a + b) / 2; ob.rotation_quaternion = d.to_track_quat('Z', 'Y'); ob.scale = (1, 1, max(d.length, 1e-3))
def key(ob, *props):
    for p in props: ob.keyframe_insert(p)


def coll(name):
    c = bpy.data.collections.new(name); sc.collection.children.link(c); return c


def into(c, ob):
    for u in list(ob.users_collection): u.objects.unlink(ob)
    c.objects.link(ob); return ob


# ------------------------------------------------------------------ shared rigs
def world(top='#03040A', horizon='#2A1E5C', density=0.0045, vol_color=(1, 1, 1), stars=True):
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    WN = w.node_tree.nodes; WL = w.node_tree.links; bg = WN['Background']
    wtc = WN.new('ShaderNodeTexCoord'); sp = WN.new('ShaderNodeSeparateXYZ'); WL.new(wtc.outputs['Generated'], sp.inputs[0])
    rp = WN.new('ShaderNodeValToRGB'); WL.new(sp.outputs['Z'], rp.inputs['Fac'])
    rp.color_ramp.elements[0].position = 0.45; rp.color_ramp.elements[0].color = lin(horizon)
    rp.color_ramp.elements[1].position = 0.75; rp.color_ramp.elements[1].color = lin(top)
    out = rp.outputs['Color']
    if stars:
        vs = WN.new('ShaderNodeTexVoronoi'); vs.inputs['Scale'].default_value = 260; WL.new(wtc.outputs['Generated'], vs.inputs['Vector'])
        st = WN.new('ShaderNodeMath'); st.operation = 'LESS_THAN'; st.inputs[1].default_value = 0.035; WL.new(vs.outputs['Distance'], st.inputs[0])
        ad = WN.new('ShaderNodeMixRGB'); ad.blend_type = 'ADD'; WL.new(st.outputs[0], ad.inputs['Fac'])
        WL.new(out, ad.inputs['Color1']); ad.inputs['Color2'].default_value = (1, 1, 1, 1); out = ad.outputs['Color']
    WL.new(out, bg.inputs['Color'])
    if density > 0:
        vsc = WN.new('ShaderNodeVolumeScatter'); vsc.inputs['Density'].default_value = density
        vsc.inputs['Color'].default_value = (*vol_color, 1); vsc.inputs['Anisotropy'].default_value = 0.35
        WL.new(vsc.outputs[0], WN['World Output'].inputs['Volume'])


def moon(e=0.9):
    m_ = bpy.data.lights.new('moon', 'SUN'); m_.energy = e; m_.color = (0.62, 0.72, 1.0); m_.angle = 0.02
    o = put(bpy.data.objects.new('moon', m_)); o.rotation_euler = (math.radians(55), math.radians(15), math.radians(-30))


def city_ground(z, size=5000, clear=180, strength=9.0, scale=0.3):
    gm = bpy.data.materials.new('ground'); gm.use_nodes = True
    N = gm.node_tree.nodes; L = gm.node_tree.links; b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = lin('#07090F'); b.inputs['Roughness'].default_value = 0.85
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = scale
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.09; L.new(vo.outputs['Distance'], lt.inputs[0])
    ln_ = N.new('ShaderNodeVectorMath'); ln_.operation = 'LENGTH'; L.new(tc.outputs['Object'], ln_.inputs[0])
    far = N.new('ShaderNodeMath'); far.operation = 'GREATER_THAN'; far.inputs[1].default_value = clear; L.new(ln_.outputs['Value'], far.inputs[0])
    mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(lt.outputs[0], mm.inputs[0]); L.new(far.outputs[0], mm.inputs[1])
    es = N.new('ShaderNodeMath'); es.operation = 'MULTIPLY'; es.inputs[1].default_value = strength; L.new(mm.outputs[0], es.inputs[0])
    b.inputs['Emission Color'].default_value = lin('#FFB25C'); L.new(es.outputs[0], b.inputs['Emission Strength'])
    bm_ = bmesh.new(); bmesh.ops.create_grid(bm_, x_segments=1, y_segments=1, size=size)
    g = mk('ground', bm_, gm, smooth=False); g.location = (0, 0, z)
    return g, es


def emis_key(m, s, frame):
    n = [x for x in m.node_tree.nodes if x.type == 'EMISSION'][0]
    n.inputs['Strength'].default_value = s; n.inputs['Strength'].keyframe_insert('default_value', frame=frame)


def wtxt(body, loc, size, color, strength=3.0, rot=(0, 0, 0), align='CENTER'):
    f = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    cu = bpy.data.curves.new('wt', 'FONT'); cu.body = body; cu.font = f; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    cu.materials.append(emis(color, strength)); ob = put(bpy.data.objects.new('wt', cu)); ob.location = loc; ob.rotation_euler = rot
    return ob


def rack_img(seed, w=32, h=64):
    rnd = random.Random(seed); img = bpy.data.images.new(f'rk{seed}', w, h, alpha=False); px = [0.0] * (w * h * 4)
    pal = [(0.2, 1.0, 0.55), (0.2, 1.0, 0.55), (0.25, 0.66, 1.0), (1.0, 0.65, 0.1), (0.05, 0.05, 0.06), (0.05, 0.05, 0.06)]
    leds = {}
    for y in range(h):
        for x in range(w):
            c = (0.06, 0.07, 0.09)
            if y % 8 == 0: c = (0.0, 0.0, 0.0)
            elif x in (3, 4, 7, 8, 11, 12) and y % 8 in (3, 4):
                k = (y // 8, x // 4)
                if k not in leds: leds[k] = rnd.choice(pal)
                c = leds[k]
            elif x >= 16 and y % 8 in (2, 5) and x % 3 == 0: c = (0.12, 0.6, 0.9) if rnd.random() < 0.25 else (0.02, 0.02, 0.03)
            i = (y * w + x) * 4; px[i:i + 4] = [c[0], c[1], c[2], 1]
    img.pixels = px; return img


def rack_mat(seed, strength=4.0):
    m = bpy.data.materials.new('rack'); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = lin('#0C0F15'); b.inputs['Metallic'].default_value = 0.5; b.inputs['Roughness'].default_value = 0.35
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeVectorMath'); mp.operation = 'MULTIPLY'; mp.inputs[1].default_value = (1.1, 1.1, 0.42)
    L.new(tc.outputs['Object'], mp.inputs[0])
    it = N.new('ShaderNodeTexImage'); it.image = rack_img(seed); it.interpolation = 'Closest'; it.projection = 'BOX'
    L.new(mp.outputs[0], it.inputs['Vector']); L.new(it.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = strength
    return m


BOARD_KIDS = list(BOARD.children)


def board_on(on):
    for c in BOARD_KIDS: c.hide_render = not on


STANCE = dict(
    surf=lambda t: (Vector((-0.95, 0.05, 0.25 + 0.1 * math.sin(6 * t))), Vector((0.92, -0.05, 0.38 + 0.1 * math.sin(6 * t + 1.7))),
                    Vector((-0.34, 0.08, -0.80)), Vector((0.34, -0.12, -0.80))),
    stand=lambda t: (Vector((-0.66, 0.05, -0.32)), Vector((0.66, 0.05, -0.32)), Vector((-0.2, 0, -0.8)), Vector((0.2, 0, -0.8))),
    cheer=lambda t: (Vector((-0.8, 0.05, 0.85 + 0.08 * math.sin(14 * t))), Vector((0.8, 0.05, 0.85 + 0.08 * math.sin(14 * t + 1))),
                     Vector((-0.22, 0, -0.8)), Vector((0.22, 0, -0.8))),
    shiver=lambda t: (Vector((-0.42 + 0.03 * math.sin(60 * t), 0.4, -0.05)), Vector((0.42 + 0.03 * math.sin(55 * t), 0.4, -0.05)),
                      Vector((-0.16, 0, -0.8)), Vector((0.16, 0, -0.8))),
)


def hex_frame(t, pos, pitch=0.0, roll=0.0, yaw=0.0, look=None, blink=0.0, squint=0.0, stance='surf', board=True, scale=1.0):
    HEX.location = pos; HEX.rotation_euler = (pitch, roll, yaw); HEX.scale = (scale,) * 3; key(HEX, 'location', 'rotation_euler', 'scale')
    R = Euler((pitch, roll, yaw)).to_matrix()
    BOARD.location = pos + R @ Vector((0, 0, -0.9 * scale)); BOARD.rotation_euler = (pitch, roll * 1.2, yaw); BOARD.scale = (scale,) * 3
    key(BOARD, 'location', 'rotation_euler', 'scale')
    hl, hr, fl, fr = STANCE[stance](t)
    rod(LIMBS['armL'], Vector((-0.5, 0, 0.05)), hl); rod(LIMBS['armR'], Vector((0.5, 0, 0.05)), hr)
    rod(LIMBS['legL'], Vector((-0.18, 0, -0.3)), fl + Vector((0, 0, 0.06))); rod(LIMBS['legR'], Vector((0.18, 0, -0.3)), fr + Vector((0, 0, 0.06)))
    HANDS['handL'].location = hl; HANDS['handR'].location = hr; FEET['footL'].location = fl; FEET['footR'].location = fr
    for ob in LIMBS.values(): key(ob, 'location', 'rotation_quaternion', 'scale')
    for ob in list(HANDS.values()) + list(FEET.values()): key(ob, 'location')
    EYE.rotation_mode = 'QUATERNION'
    if look is None:
        EYE.rotation_quaternion = Quaternion()
    else:
        ld_ = R.transposed() @ (Vector(look) - (pos + R @ (EYE.location * scale)))
        EYE.rotation_quaternion = ld_.to_track_quat('Y', 'Z')
    key(EYE, 'rotation_quaternion')
    close = max(blink, 0.55 * squint)
    LID_U.rotation_euler = (math.radians(48 - 118 * close), 0, 0); LID_D.rotation_euler = (math.radians(-48 + 70 * close), 0, 0)
    key(LID_U, 'rotation_euler'); key(LID_D, 'rotation_euler')
    brow.location = (0.02, 0.24, 0.47 + 0.03 * math.sin(t * 3)); brow.rotation_euler = (0, math.radians(-10 + 10 * squint), 0)
    key(brow, 'location', 'rotation_euler')


def cam_frame(pos, tgt, lens, roll=0.0):
    cam.location = pos; cam.rotation_quaternion = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), roll)
    cam_d.lens = lens; key(cam, 'location', 'rotation_quaternion'); cam_d.keyframe_insert('lens')


def shake(t, a=1.0):
    return Vector((math.sin(t * 13.1) * 0.03 + math.sin(t * 29.3) * 0.015, math.sin(t * 9.7) * 0.02, math.sin(t * 11.7) * 0.03)) * a


def blink_at(t, *times, w=0.07):
    return max([0.0] + [max(0.0, 1 - abs(t - x) / w) for x in times])


# ================================================================== scene builders
def build_campus(gz=0.0, rows=5, cols=5, win=6.0):
    halls = []; wins = []
    for ix in range(-(cols // 2), cols // 2 + 1):
        for iy in range(-(rows // 2), rows // 2 + 1):
            cx, cy = ix * 56, iy * 62; hh = random.choice([14, 18, 24])
            halls.append(box('hall', (46, 34, hh), pbr('#1A1F2B', metal=0.4, rough=0.45), (cx, cy, gz + hh / 2)))
            for sy in (-1, 1):
                wins.append(box('win', (44, 0.2, 0.9), emis('#3BE6FF', win), (cx, cy + sy * 17.05, gz + hh * 0.6)))
                wins.append(box('win', (44, 0.2, 0.5), emis('#7B5CFF', win * 0.8), (cx, cy + sy * 17.05, gz + hh * 0.3)))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    sph('red', 0.35, emis('#FF2A2A', 30), (cx + sx * 22.5, cy + sy * 16.5, gz + hh + 0.6), seg=8)
            for k in range(6):
                box('chill', (5, 4, 2), pbr('#2A3140', metal=0.5, rough=0.4), (cx - 18 + k * 7.2, cy - 8, gz + hh + 1))
                cyl('fan', 1.6, 1.6, 0.1, emis('#3BE6FF', 1.2), segs=16).location = (cx - 18 + k * 7.2, cy - 8, gz + hh + 2.05)
    return halls, wins


def build_roof():
    world(density=0.006); moon(1.1)
    rm_ = pbr('#141924', metal=0.5, rough=0.32)
    for sz, lc in (((140, 68, 1), (0, -36, -0.5)), ((140, 68, 1), (0, 36, -0.5)), ((68, 4, 1), (-36, 0, -0.5)), ((68, 4, 1), (36, 0, -0.5))):
        box('roof', sz, rm_, lc)
    for x, y, w, d in ((0, -2.6, 6.2, 1.0), (0, 2.6, 6.2, 1.0), (-2.6, 0, 1.0, 4.2), (2.6, 0, 1.0, 4.2)):
        box('hframe', (w, d, 0.8), pbr('#2A3140', metal=0.7, rough=0.3), (x, y, 0.4))
    glowm = emis('#7CF8FF', 14.0); box('hatchglow', (4.2, 4.2, 0.05), glowm, (0, 0, -0.6))
    sp_ = bpy.data.lights.new('beam', 'SPOT'); sp_.energy = 9000; sp_.spot_size = math.radians(35); sp_.color = lin('#7CF8FF')[:3]
    put(bpy.data.objects.new('beam', sp_)).location = (0, 0, -0.4)
    up = cyl('uplink', 2.0, 2.0, 220, trail_mat('#35E0FF', 5.0, axis='Z'), segs=24); up.location = (0, 0, 110)
    fans = []
    for gx in range(-3, 4):
        for gy in range(-3, 4):
            if abs(gx) <= 1 and abs(gy) <= 1: continue
            cx, cy = gx * 9, gy * 8
            box('chill', (6, 4.4, 2.4), pbr('#2A3140', metal=0.55, rough=0.35), (cx, cy, 1.2))
            f = cyl('fan', 1.7, 1.7, 0.08, emis('#3BE6FF', 1.5), segs=16); f.location = (cx, cy, 2.45); fans.append(f)
            if random.random() < 0.35: sph('red', 0.18, emis('#FF2A2A', 30), (cx + 2.8, cy + 2.0, 2.6), seg=8)
    for i in range(5):
        v = put(bpy.data.objects.new('steam', bpy.data.meshes.new('s')))
        b_ = bmesh.new(); bmesh.ops.create_cube(b_, size=1.0); b_.to_mesh(v.data); b_.free()
        vm = bpy.data.materials.new('vol'); vm.use_nodes = True; vn = vm.node_tree.nodes; vn.remove(vn['Principled BSDF'])
        pv = vn.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = 0.25
        vm.node_tree.links.new(pv.outputs[0], vn['Material Output'].inputs['Volume']); v.data.materials.append(vm)
        v.location = (random.choice([-1, 1]) * random.uniform(14, 26), random.uniform(-24, 24), 8); v.scale = (3.5, 3.5, 12)
    city_ground(-30, clear=120)
    build_campus(gz=-30, rows=3, cols=3)
    return glowm, fans


def build_hall(length=150, haze=0.03, haze_col=(0.75, 0.85, 1.0), led=4.0):
    world(top='#000000', horizon='#000000', density=haze, vol_color=haze_col, stars=False)
    box('floor', (16, length, 0.2), pbr('#0A0D14', metal=0.3, rough=0.07, coat=1.0), (0, 0, -0.1))
    box('ceil', (16, length, 0.3), pbr('#0B0E14', metal=0.4, rough=0.5), (0, 0, 5.2))
    mats = [rack_mat(s, led) for s in (1, 2, 3)]
    for side in (-1, 1):
        for k in range(-length // 2 + 2, length // 2 - 2):
            box('rack', (1.1, 0.92, 2.5), random.choice(mats), (side * 1.85, k * 1.0, 1.25))
        box('tray', (0.7, length, 0.08), pbr('#C9A227', metal=0.8, rough=0.35), (side * 1.85, 0, 2.75))
        box('trayglow', (0.04, length, 0.04), emis('#FF8A1F', 4.0), (side * 1.28, 0, 2.6))
    for y in range(-length // 2 + 3, length // 2 - 3, 6):
        box('panel', (1.0, 2.4, 0.05), emis('#E6F0FF', 6.0), (0, y, 5.03))
        s_ = bpy.data.lights.new('spot', 'SPOT'); s_.energy = 700; s_.spot_size = math.radians(55); s_.spot_blend = 0.6
        s_.color = (0.85, 0.92, 1.0); o = put(bpy.data.objects.new('spot', s_)); o.location = (0, y, 4.9)
    return mats


# ================================================================== shots
NFR = F1 - F0 + 1
board_on(True)

if SHOT == 'dive':
    glowm, fans = build_roof()
    P0 = Vector((0, -24, 26)); P1 = Vector((0, 0, -2.5))
    for f in range(F0, F1 + 1):
        sc.frame_set(f); t = (f - F0) / FPS; u = seg(t, 0, DUR_S * 0.86)
        p = P0.lerp(P1, u ** 1.7) + Vector((1.4 * math.sin(t * 4) * (1 - u), 0, 0))
        pitch = -0.55 - 0.5 * u
        hex_frame(t, p, pitch=pitch, roll=0.25 * math.sin(t * 4), look=P1, stance='surf', squint=0.4 * u)
        cp = p + Vector((1.3, -4.6 + 2.2 * u, 2.6 + 1.5 * u)) + shake(t, 1 + u)
        cam_frame(cp, p.lerp(P1, 0.35) + Vector((0, 1.5, 0)), 20 - 4 * u)
        for k_, fn in enumerate(fans):
            fn.rotation_euler = (0, 0, t * 9 + k_); fn.keyframe_insert('rotation_euler')
        emis_key(glowm, 14 + 220 * sm(seg(t, DUR_S * 0.8, DUR_S)), f)

elif SHOT in ('hall', 'heat', 'cool'):
    mats = build_hall(haze=0.03 if SHOT != 'cool' else 0.04, haze_col=(0.75, 0.85, 1.0) if SHOT != 'heat' else (1.0, 0.7, 0.5),
                      led=4.0 if SHOT != 'heat' else 7.0)
    if SHOT == 'hall':
        for f in range(F0, F1 + 1):
            sc.frame_set(f); t = (f - F0) / FPS
            p = Vector((0.25 * math.sin(t * 3), -40 + 17 * t, 1.15 + 0.08 * math.sin(t * 5)))
            u = sm(seg(t, DUR_S * 0.5, DUR_S * 0.72))
            front = p + Vector((0.45, 3.0, -0.25)); side = p + Vector((0.8, -0.6, 0.5))
            cp = front.lerp(side, u) + shake(t, 0.8)
            hex_frame(t, p, pitch=-0.12, roll=-0.2 * math.cos(t * 3), look=cp if u < 0.5 else p + Vector((0, 10, 0)),
                      blink=blink_at(t, 0.9), stance='surf')
            cam_frame(cp, p + Vector((0, 0.4 * u, 0.05)), 26 - 8 * u, roll=0.12 * u)
    elif SHOT == 'heat':
        sc.use_nodes = True; nt = sc.node_tree; nt.nodes.clear()
        rl = nt.nodes.new('CompositorNodeRLayers'); cp_ = nt.nodes.new('CompositorNodeComposite')
        bw_ = nt.nodes.new('CompositorNodeRGBToBW'); gm_ = nt.nodes.new('CompositorNodeGamma'); gm_.inputs[1].default_value = 0.7
        rp = nt.nodes.new('CompositorNodeValToRGB'); el = rp.color_ramp.elements
        stops = [(0.0, '#05010F'), (0.18, '#3B0A6B'), (0.4, '#C21E4A'), (0.62, '#FF7A1A'), (0.82, '#FFE45C'), (1.0, '#FFFFFF')]
        el[0].position, el[0].color = stops[0][0], lin(stops[0][1]); el[1].position, el[1].color = stops[-1][0], lin(stops[-1][1])
        for pos_, c_ in stops[1:-1]:
            e_ = el.new(pos_); e_.color = lin(c_)
        nt.links.new(rl.outputs['Image'], bw_.inputs[0]); nt.links.new(bw_.outputs[0], gm_.inputs[0]); nt.links.new(gm_.outputs[0], rp.inputs[0])
        nt.links.new(rp.outputs[0], cp_.inputs[0])
        drops = [sph('drop', 0.05, emis('#9AD8FF', 6), (0, 0, 0), seg=8) for _ in range(6)]
        for f in range(F0, F1 + 1):
            sc.frame_set(f); t = (f - F0) / FPS
            p = Vector((0.0, 0.0, 1.1)) + Vector((0.025 * math.sin(t * 70), 0, 0.02 * math.sin(t * 50)))
            hex_frame(t, p, pitch=0.0, look=p + Vector((0, 4, 0.4)), squint=0.8, stance='shiver')
            for i, d_ in enumerate(drops):
                k_ = (t * 1.6 + i / 6) % 1.0; s_ = -1 if i % 2 else 1
                d_.location = p + Vector((s_ * (0.55 + 0.1 * k_), 0.1, 0.5 - 1.2 * k_)); d_.keyframe_insert('location')
            u = sm(seg(t, 0, DUR_S))
            cam_frame(p + Vector((0.6 - 0.3 * u, 3.4 - 1.2 * u, 0.3)) + shake(t, 1.5), p + Vector((0, 0, 0.05)), 30 + 10 * u, roll=-0.18 * u)
    else:  # cool
        cm = bpy.data.materials.new('coolant'); cm.use_nodes = True; N_ = cm.node_tree.nodes; L_ = cm.node_tree.links; N_.clear()
        o_ = N_.new('ShaderNodeOutputMaterial'); wv = N_.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
        wv.inputs['Scale'].default_value = 3.0; wv.inputs['Distortion'].default_value = 2.0
        tc_ = N_.new('ShaderNodeTexCoord'); L_.new(tc_.outputs['Object'], wv.inputs['Vector'])
        rr = N_.new('ShaderNodeValToRGB'); L_.new(wv.outputs['Fac'], rr.inputs['Fac'])
        rr.color_ramp.elements[0].color = lin('#0A3CFF'); rr.color_ramp.elements[1].color = lin('#B8F6FF')
        em_ = N_.new('ShaderNodeEmission'); em_.inputs['Strength'].default_value = 5.0; L_.new(rr.outputs['Color'], em_.inputs['Color'])
        L_.new(em_.outputs[0], o_.inputs['Surface'])
        for sx in (-1, 1):
            for z in (0.7, 1.9):
                pp = cyl('pipe', 0.11, 0.11, 140, cm, segs=12); pp.rotation_euler = (math.radians(90), 0, 0); pp.location = (sx * 1.24, 0, z)
                gl = cyl('glass', 0.15, 0.15, 140, pbr('#BFE8FF', metal=0.0, rough=0.05, coat=1.0), segs=12)
                gl.rotation_euler = (math.radians(90), 0, 0); gl.location = (sx * 1.24, 0, z)
        for i in range(160):
            sph('frost', random.uniform(0.01, 0.03), emis('#E8FBFF', 6), (random.uniform(-1.1, 1.1), random.uniform(-6, 14), random.uniform(0.2, 3.5)), seg=6)
        for f in range(F0, F1 + 1):
            sc.frame_set(f); t = (f - F0) / FPS
            wv.inputs['Phase Offset'].default_value = -t * 9; wv.inputs['Phase Offset'].keyframe_insert('default_value', frame=f)
            p = Vector((0, 0.6 * t, 1.1))
            hex_frame(t, p, look=p + Vector((-2, 2, 0.6)), blink=blink_at(t, 0.35), squint=0.6 * sm(seg(t, 0.4, 0.7)),
                      stance='cheer' if t > 0.55 else 'stand')
            cam_frame(p + Vector((0.9, 2.3, 0.15)) + shake(t, 0.6), p + Vector((-0.3, 0, 0.1)), 24, roll=0.06)

elif SHOT == 'chip':
    world(top='#02030A', horizon='#0A0D1E', density=0.02, vol_color=(0.6, 0.8, 1.0), stars=False)
    cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.4
    ROOT = put(bpy.data.objects.new('gpu', None))
    pcb_img = bpy.data.images.new('pcb', 128, 128, alpha=False); px = []
    for y in range(128):
        for x in range(128):
            gold = (y % 12 == 5 and (x // 7) % 3 != 0) or (x % 16 == 9 and (y // 9) % 2 == 0)
            c = (0.83, 0.62, 0.18) if gold else (0.02, 0.12, 0.06)
            px += [c[0], c[1], c[2], 1]
    pcb_img.pixels = px
    pm = bpy.data.materials.new('pcb'); pm.use_nodes = True; Nn = pm.node_tree.nodes; Ll = pm.node_tree.links; bb = Nn['Principled BSDF']
    it = Nn.new('ShaderNodeTexImage'); it.image = pcb_img; it.projection = 'BOX'
    tc_ = Nn.new('ShaderNodeTexCoord'); mp = Nn.new('ShaderNodeVectorMath'); mp.operation = 'MULTIPLY'; mp.inputs[1].default_value = (0.35, 0.35, 0.35)
    Ll.new(tc_.outputs['Object'], mp.inputs[0]); Ll.new(mp.outputs[0], it.inputs['Vector']); Ll.new(it.outputs['Color'], bb.inputs['Base Color'])
    bb.inputs['Metallic'].default_value = 0.35; bb.inputs['Roughness'].default_value = 0.3
    die_img = bpy.data.images.new('die', 64, 64, alpha=False); px = []
    for y in range(64):
        for x in range(64):
            core = (x % 8 in (1, 2, 3, 4, 5)) and (y % 8 in (1, 2, 3, 4, 5))
            px += ([0.1, 0.9, 1.0, 1] if core else [0.0, 0.02, 0.04, 1])
    die_img.pixels = px
    dm = bpy.data.materials.new('die'); dm.use_nodes = True; Nd = dm.node_tree.nodes; Ld = dm.node_tree.links; bd = Nd['Principled BSDF']
    bd.inputs['Base Color'].default_value = lin('#0A0C12'); bd.inputs['Roughness'].default_value = 0.08; bd.inputs['Coat Weight'].default_value = 1.0
    it2 = Nd.new('ShaderNodeTexImage'); it2.image = die_img; it2.interpolation = 'Closest'; it2.projection = 'BOX'
    tc2 = Nd.new('ShaderNodeTexCoord'); mp2 = Nd.new('ShaderNodeVectorMath'); mp2.operation = 'MULTIPLY'; mp2.inputs[1].default_value = (0.71, 0.71, 0.71)
    Ld.new(tc2.outputs['Object'], mp2.inputs[0]); Ld.new(mp2.outputs[0], it2.inputs['Vector']); Ld.new(it2.outputs['Color'], bd.inputs['Emission Color'])
    parts = []

    def gp(ob, z1, dx=0.0, dy=0.0, rot=0.0, delay=0.0):
        ob.parent = ROOT; parts.append((ob, Vector(ob.location), z1, dx, dy, rot, delay)); return ob

    pcb = gp(bevel(box('pcb', (6, 4.4, 0.12), pm, (0, 0, 0)), 0.02, 2), -0.6)
    gp(box('interposer', (2.9, 2.3, 0.08), pbr('#2B2F38', metal=0.6, rough=0.3), (0, 0, 0.1)), 0.3, delay=0.05)
    die = gp(box('die', (1.4, 1.4, 0.12), dm, (0, 0, 0.2)), 1.0, delay=0.08)
    for i, (x, y) in enumerate([(-1.0, -0.75), (-1.0, 0), (-1.0, 0.75), (1.0, -0.75), (1.0, 0), (1.0, 0.75)]):
        gp(bevel(box('hbm', (0.45, 0.62, 0.34), pbr('#8D96A3', metal=0.9, rough=0.28), (x, y, 0.3)), 0.02, 2), 1.2 + 0.1 * i, dx=0.7 * x, delay=0.12)
    for i in range(70):
        x = random.uniform(-2.8, 2.8); y = random.uniform(-2.0, 2.0)
        if abs(x) < 1.6 and abs(y) < 1.3: continue
        gp(box('cap', (0.12, 0.2, 0.1), pbr(random.choice(['#B08D57', '#9AA3AE', '#1E2028']), metal=0.7, rough=0.3), (x, y, 0.11)), -0.6)
    cp_ = gp(bevel(box('coldplate', (3.2, 2.6, 0.35), pbr('#C77B3A', metal=1.0, rough=0.22), (0, 0, 0.62)), 0.04, 2), 2.6, delay=0.0, rot=0.15)
    base_ = gp(box('hsbase', (3.2, 2.6, 0.15), pbr('#C9CED6', metal=1.0, rough=0.3), (0, 0, 0.9)), 3.6, rot=-0.1)
    for i in range(22):
        x = -1.5 + i * (3.0 / 21)
        gp(box('fin', (0.05, 2.6, 1.4), pbr('#D5DAE2', metal=1.0, rough=0.32), (x, 0, 1.7)), 4.4, dx=x * 0.6, rot=-0.1, delay=0.02)
    bits = [sph('bit', random.uniform(0.02, 0.05), emis(random.choice(['#35E0FF', '#FF3EC8', '#FFFFFF']), 10), (0, 0, 0), seg=6) for _ in range(80)]
    for b_ in bits: b_.parent = ROOT
    BOP = [(random.uniform(1.2, 3.2), random.uniform(0, 6.28), random.uniform(0.3, 2.5), random.uniform(0.6, 1.6)) for _ in bits]
    kl = bpy.data.lights.new('k', 'AREA'); kl.energy = 900; kl.size = 4; put(bpy.data.objects.new('k', kl)).location = (2, -6, 7)
    bpy.data.objects['k'].rotation_euler = (math.radians(45), 0, math.radians(18))
    for c_, loc_ in (('#35E0FF', (-5, 4, 2)), ('#FF3EC8', (5, 4, 3))):
        l_ = bpy.data.lights.new('r', 'POINT'); l_.energy = 2500; l_.color = lin(c_)[:3]; put(bpy.data.objects.new('r', l_)).location = loc_
    board_on(False)
    for f in range(F0, F1 + 1):
        sc.frame_set(f); t = (f - F0) / FPS
        e = sm(seg(t, 0.25, 1.5))
        for ob, base, z1, dx, dy, rot, delay in parts:
            ee_ = sm(seg(t, 0.25 + delay * 3, 1.5 + delay * 3))
            ob.location = base + Vector((dx * ee_, dy * ee_, (z1 - (base.z if z1 < 0 else 0)) * ee_ if z1 < 0 else z1 * ee_))
            ob.rotation_euler = (rot * ee_, 0, 0); key(ob, 'location', 'rotation_euler')
        bd.inputs['Emission Strength'].default_value = 2.0 + 6.0 * e * (0.75 + 0.25 * math.sin(t * 14))
        bd.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
        for b_, (r_, a_, z_, sp__) in zip(bits, BOP):
            a2 = a_ + t * sp__ * 2
            b_.location = Vector((math.cos(a2) * r_, math.sin(a2) * r_ * 0.75, 1.0 + z_ * e)); b_.keyframe_insert('location')
        ROOT.rotation_euler = (0, 0, 0.25 * t); key(ROOT, 'rotation_euler')
        hp = Vector((-2.2, -1.5, 0.06 + 0.86 * 0.32 - 0.6 * e))
        hex_frame(t, hp, yaw=math.radians(-35), look=Vector((0, 0, 1.0 + 1.0 * e)), stance='cheer' if t > 1.7 else 'stand',
                  blink=blink_at(t, 0.5), board=False, scale=0.32)
        a = -0.5 + 0.9 * sm(seg(t, 0, DUR_S)); r = 9.5 - 3.0 * sm(seg(t, 0, DUR_S))
        cp = Vector((math.sin(a) * r, -math.cos(a) * r, 4.2 - 1.2 * sm(seg(t, 0, DUR_S)))) + shake(t, 0.5)
        tg = Vector((0, 0, 0.6 + 1.2 * e))
        cam_frame(cp, tg, 34)
        cam_d.dof.focus_distance = (cp - tg).length; cam_d.dof.keyframe_insert('focus_distance')

elif SHOT == 'scale':
    world(top='#000000', horizon='#000000', density=0.012, vol_color=(0.7, 0.8, 1.0), stars=False)
    box('floor', (400, 400, 0.2), pbr('#07090E', metal=0.3, rough=0.12, coat=1.0), (0, 0, -0.1))
    rk = box('rack', (1.1, 0.92, 2.5), rack_mat(7, 4.0), (0, 0, 1.25))
    top = box('rtop', (0.08, 0.7, 0.04), emis('#35E0FF', 8), (0.0, 0, 2.52)); top.parent = rk; top.location = (0, 0, 1.27)
    a1 = rk.modifiers.new('a1', 'ARRAY'); a1.count = 90; a1.use_relative_offset = False; a1.use_constant_offset = True; a1.constant_offset_displace = (0, 1.0, 0)
    a2 = rk.modifiers.new('a2', 'ARRAY'); a2.count = 40; a2.use_relative_offset = False; a2.use_constant_offset = True; a2.constant_offset_displace = (3.4, 0, 0)
    ta1 = top.modifiers.new('a1', 'ARRAY'); ta1.count = 90; ta1.use_relative_offset = False; ta1.use_constant_offset = True; ta1.constant_offset_displace = (0, 1.0, 0)
    ta2 = top.modifiers.new('a2', 'ARRAY'); ta2.count = 40; ta2.use_relative_offset = False; ta2.use_constant_offset = True; ta2.constant_offset_displace = (3.4, 0, 0)
    rk.location = (-66, -44, 1.25)
    CH = Vector((0.6, 0.0, 1.4))
    hero = box('hero', (1.1, 0.92, 2.5), pbr('#0C0F15', metal=0.5, rough=0.35), (0, 0, 1.25))
    tray = box('tray', (1.0, 0.8, 0.08), pbr('#3A3F47', metal=0.7, rough=0.3), (0.55, 0, 1.4))
    chip = box('chip', (0.22, 0.22, 0.04), emis('#7CF8FF', 18), CH + Vector((0, 0, 0.06)))
    for f in range(F0, F1 + 1):
        sc.frame_set(f); t = (f - F0) / FPS; u = sm(seg(t, 0.0, DUR_S * 0.92))
        d = 0.5 * (220 ** u)
        dir_ = Vector((0.9, -0.5, 0.35)).normalized().lerp(Vector((0.35, -0.45, 1.0)).normalized(), u).normalized()
        cp = CH + dir_ * d + shake(t, 0.3)
        tg = CH.lerp(Vector((-0, 0, 0)), u) + Vector((0, 0, 0))
        cam_frame(cp, tg, 28 - 6 * u)
    board_on(False); HEX.location = (0, 0, -100); key(HEX, 'location')

elif SHOT == 'power':
    world(density=0.004); moon(1.0)
    g, es = city_ground(-0.01, clear=200, strength=12.0)
    halls, wins = build_campus(gz=0.0, rows=5, cols=5, win=7.0)
    up = cyl('uplink', 2.2, 2.2, 260, trail_mat('#35E0FF', 5.0, axis='Z'), segs=24); up.location = (0, 0, 130)
    tm = pbr('#5E646B', metal=0.8, rough=0.4)
    pyl = []
    for i, x in enumerate((-330, -280, -230, -180)):
        y = 20 + i * 3
        for sx in (-1, 1):
            for sy in (-1, 1):
                a_ = Vector((x + sx * 3, y + sy * 3, 0)); b_ = Vector((x + sx * 0.7, y + sy * 0.7, 28)); d_ = b_ - a_
                o = box('leg', (0.4, 0.4, d_.length), tm, (a_ + b_) / 2); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d_.to_track_quat('Z', 'Y')
        box('arm', (0.5, 16, 0.5), tm, (x, y, 25))
        pyl.append([Vector((x, y - 7.5, 24.6)), Vector((x, y + 7.5, 24.6))])
    wires = []
    for a_, b_ in zip(pyl[:-1], pyl[1:]):
        for i in range(2): wires.append((a_[i], b_[i]))
    for i in range(2): wires.append((pyl[-1][i], Vector((-140, -10 + i * 20, 14))))
    for a_, b_ in wires:
        d_ = b_ - a_; o = box('wire', (0.18, 0.18, d_.length), emis('#FFD36B', 3.5), (a_ + b_) / 2)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d_.to_track_quat('Z', 'Y')
    pulses = [(sph('pulse', 0.9, emis('#FFF2B0', 40), (0, 0, 0), seg=10), wires[i % len(wires)], (i * 0.37) % 1.0) for i in range(12)]
    wm = [w_.data.materials[0] for w_ in wins]
    for f in range(F0, F1 + 1):
        sc.frame_set(f); t = (f - F0) / FPS; u = sm(seg(t, 0.2, DUR_S))
        es.inputs[1].default_value = 12.0 * (1 - 0.75 * u); es.inputs[1].keyframe_insert('default_value', frame=f)
        for m_ in wm[::2]: emis_key(m_, 7.0 + 14.0 * u, f)
        for pobj, (a_, b_), ph in pulses:
            k_ = (ph + t * 0.9) % 1.0; pobj.location = a_.lerp(b_, k_); pobj.keyframe_insert('location')
        cp = Vector((-300, -110, 52)).lerp(Vector((-215, -70, 38)), sm(seg(t, 0, DUR_S))) + shake(t, 2)
        cam_frame(cp, Vector((-70, 25, 10)), 24)
    board_on(False); HEX.location = (0, 0, -500); key(HEX, 'location')

elif SHOT == 'ret':
    world(top='#020206', horizon='#08060F', density=0.01, stars=False)
    cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.0
    box('desk', (60, 60, 0.2), pbr('#1A1310', metal=0.0, rough=0.28, coat=0.6), (0, 0, -0.1))
    ph = bevel(box('phone', (3.2, 6.6, 0.3), pbr('#07080B', metal=0.6, rough=0.15, coat=1.0), (0, 0, 0.15)), 0.25, 4)
    scr_m = emis('#0E1422', 1.5); box('screen', (2.95, 6.2, 0.02), scr_m, (0, 0, 0.31))
    box('b1', (1.7, 0.6, 0.02), emis('#2F6BFF', 3), (0.5, 1.6, 0.33)); wtxt('Привет', (0.5, 1.6, 0.35), 0.32, '#FFFFFF', 4)
    ANS = [box('b2', (2.4, 1.0, 0.02), emis('#2A3142', 3), (-0.15, 0.3, 0.33)),
           wtxt('Привет!\nЧем помочь?', (-0.15, 0.3, 0.35), 0.27, '#FFFFFF', 4)]
    for i in range(14):
        sph('bokeh', random.uniform(0.2, 0.5), emis(random.choice(['#FFB25C', '#35E0FF', '#FF3EC8']), 12),
            (random.uniform(-14, 14), random.uniform(10, 22), random.uniform(1, 7)), seg=10)
    la = bpy.data.lights.new('scr', 'AREA'); la.energy = 120; la.size = 3; la.color = lin('#8FB4FF')[:3]
    put(bpy.data.objects.new('scr', la)).location = (0, 0, 2.5)
    lw = bpy.data.lights.new('warm', 'POINT'); lw.energy = 900; lw.color = lin('#FFB25C')[:3]; put(bpy.data.objects.new('warm', lw)).location = (-5, -2, 4)
    pk = [sph('pk', 0.18 - i * 0.025, emis('#7CF8FF', 30 - i * 4), (0, 0, 0), seg=10) for i in range(5)]
    board_on(False)
    for f in range(F0, F1 + 1):
        sc.frame_set(f); t = (f - F0) / FPS
        for i, p_ in enumerate(pk):
            u = seg(t - i * 0.03, 0.0, 0.42)
            p_.location = Vector((2.5, 6.0, 7.0)).lerp(Vector((-0.15, 0.3, 0.4)), u ** 1.4); p_.scale = (1 - sm(seg(t, 0.4, 0.46)),) * 3
            key(p_, 'location', 'scale')
        emis_key(scr_m, 1.5 + 40 * max(0.0, 1 - abs(t - 0.44) / 0.06) + 60 * sm(seg(t, DUR_S - 0.25, DUR_S)), f)
        pop = sm(seg(t, 0.46, 0.6))
        for a_ in ANS:
            a_.scale = (pop,) * 3; a_.keyframe_insert('scale')
        jump = seg(t, 0.75, 1.15)
        hz = 0.31 + 0.82 * 0.55 + (math.sin(jump * math.pi) * 1.2 if 0 < jump < 1 else 0)
        hp = Vector((1.0, -2.0, hz if t > 0.75 else -2.0))
        hex_frame(t, hp, yaw=math.radians(-160), look=cam.location if f > F0 else None,
                  blink=blink_at(t, 1.7, w=0.1), stance='cheer' if t > 1.2 else 'stand', board=False, scale=0.55)
        z = sm(seg(t, DUR_S - 0.6, DUR_S))
        cp = Vector((3.4, -6.0, 4.2)).lerp(Vector((-0.15, 0.3, 1.2)), z) + shake(t, 0.3 * (1 - z))
        tg = Vector((0.2, -0.4, 0.5)).lerp(Vector((-0.15, 0.3, 0.3)), z)
        cam_frame(cp, tg, 32 + 10 * z)
        cam_d.dof.focus_distance = (cp - tg).length; cam_d.dof.keyframe_insert('focus_distance')

# ------------------------------------------------------------------ render
sc.frame_start = F0; sc.frame_end = F1
if STILL:
    fm = F0 + int((F1 - F0) * 0.6); sc.frame_set(fm)
    sc.render.filepath = os.path.join(OUT, f'still_{SHOT}.png'); bpy.ops.render.render(write_still=True); print('RENDERED still', SHOT, fm)
else:
    sc.render.filepath = os.path.join(OUT, 'f####'); sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True); print('RENDERED', SHOT, F0, F1)
