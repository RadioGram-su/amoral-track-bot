"""Episode 02 — «Как работают дата-центры ИИ» (PS1/PS2 style). Blender 4.0, no AI imagery.
Run: xvfb-run -a blender -b --factory-startup -P ep02.py -- OUTDIR [frames|stills] [first_frame last_frame]
"""
import sys, os, json, math, random, textwrap
EP = '/tmp/claude-0/-home-user-amoral-track-bot/f91e2272-a479-5871-8b79-e1da23093bfd/scratchpad/ep02'
exec(open(os.path.join(EP, 'ps1lib.py'), encoding='utf-8').read())
random.seed(11)
TL = json.load(open(os.path.join(EP, 'timeline.json'), encoding='utf-8'))
FPS = TL['fps']; NFR = int(math.ceil(TL['total'] * FPS))
F0 = int(ARGS[2]) if len(ARGS) > 2 else 0
F1 = int(ARGS[3]) if len(ARGS) > 3 else NFR - 1

FOGS['out'] = ('#B8D4E8', 80, 420, 0.5)
FOGS['hall'] = ('#0A1630', 3, 30, 0.42)


# ------------------------------------------------------------------ extra pixel textures
def mk_rack(seed):
    rnd = random.Random(seed); leds = {}

    def f(x, y):
        if y % 8 == 0: return h2c('#15181D')
        if x in (0, 31): return h2c('#3A3F47')
        slot = y // 8
        if x in (3, 4, 7, 8) and y % 8 in (3, 4):
            k = (slot, x // 4)
            if k not in leds:
                leds[k] = rnd.choice(['#39FF88', '#39FF88', '#3FA9FF', '#FFB020', '#20242A', '#20242A'])
            return h2c(leds[k])
        if x >= 13 and y % 8 in (2, 3, 4, 5) and x % 2 == 0: return h2c('#1A1D22')
        return nz(h2c('#2E333B'), 0.02)
    return f


def t_floor(x, y):
    if x % 16 == 0 or y % 16 == 0: return h2c('#5C636B')
    if x % 4 == 2 and y % 4 == 2: return h2c('#79818A')
    return nz(h2c('#A3AAB1'), 0.02)


def t_wall(x, y): return nz(h2c('#C9CDD2') if (x // 2) % 2 else h2c('#A3A9B0'), 0.015)
def t_roof(x, y): return h2c('#9DA3A9') if (x % 16 == 0 or y % 16 == 0) else nz(h2c('#D3D6D9'), 0.03)
def t_asph(x, y): return h2c('#E8E4D8') if (y % 32 in (0, 1) and x % 8 < 5) else nz(h2c('#4B4D52'), 0.04)


def t_fan(x, y):
    dx, dy = x - 15.5, y - 15.5; r = math.hypot(dx, dy)
    if r > 15: return h2c('#3A3F45')
    if r < 3.5: return h2c('#8A9096')
    a = math.atan2(dy, dx)
    return h2c('#1D2025') if int((a / (2 * math.pi) + 1) * 12) % 2 == 0 else h2c('#7C838B')


def t_pcb(x, y):
    if (y % 8 == 3 and x % 16 < 12) or (x % 8 == 5 and y % 16 > 4): return h2c('#D4AF37')
    return nz(h2c('#1F6B37'), 0.03)


def t_chip(x, y):
    if x in (0, 1, 30, 31) or y in (0, 1, 30, 31): return h2c('#D4AF37')
    if 8 < x < 23 and 8 < y < 23: return nz(h2c('#2A2D38'), 0.02)
    return nz(h2c('#15161C'), 0.02)


def t_coolant(x, y): return h2c('#2F7BFF') if ((x + y) // 4) % 2 else h2c('#A6ECFF')
def t_tower(x, y): return h2c('#5E646B') if x in (0, 15) or y in (0, 15) else nz(h2c('#9AA0A7'), 0.03)


for k in range(3):
    T[f'rack{k}'] = tex(f'rack{k}', 32, 64, mk_rack(100 + k))
T.update(floor=tex('floor', 32, 32, t_floor), wall=tex('wall', 32, 32, t_wall), roof=tex('roof', 32, 32, t_roof),
         asph=tex('asph', 64, 64, t_asph), fan=tex('fan', 32, 32, t_fan), pcb=tex('pcb', 32, 32, t_pcb),
         chip=tex('chip', 32, 32, t_chip), coolant=tex('coolant', 32, 32, t_coolant), tower=tex('tower', 16, 16, t_tower),
         hbm=tex('hbm', 8, 8, lambda x, y: h2c('#8D96A3') if y > 5 else nz(h2c('#3A3F47'), 0.03)),
         copper=tex('copper', 16, 16, lambda x, y: nz(h2c('#C77B3A'), 0.05)),
         fins=tex('fins', 16, 16, lambda x, y: h2c('#C9CED6') if x % 4 < 2 else h2c('#8E949C')),
         phone=tex('phone', 8, 8, lambda x, y: h2c('#15171C')))


def with_scale(m, sx, sy, sz):
    for n in m.node_tree.nodes:
        if n.type == 'VECT_MATH' and n.operation == 'MULTIPLY' and n.inputs[0].is_linked and n.inputs[0].links[0].from_node.type == 'TEX_COORD':
            n.inputs[1].default_value = (sx, sy, sz)
    return m


def add_offset(m):
    N = m.node_tree.nodes; L = m.node_tree.links
    img = [n for n in N if n.type == 'TEX_IMAGE'][0]
    src = img.inputs['Vector'].links[0].from_socket
    add = N.new('ShaderNodeVectorMath'); add.operation = 'ADD'
    L.new(src, add.inputs[0]); L.new(add.outputs[0], img.inputs['Vector'])
    return add


def set_fog(fog, color, f0=None, f1=None):
    for m in bpy.data.materials:
        if f'_{fog}_' not in m.name or not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == 'MAP_RANGE':
                if f0 is not None: n.inputs['From Min'].default_value = f0
                if f1 is not None: n.inputs['From Max'].default_value = f1
            elif n.type == 'MIX_RGB' and n.inputs['Fac'].is_linked and n.inputs['Fac'].links[0].from_node.type == 'MAP_RANGE':
                n.inputs['Color2'].default_value = lin(color)


def wtxt(body, loc, size, color, rot=(0, 0, 0), strength=1.0):
    cu = bpy.data.curves.new('wt', 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.materials.append(glow(color, strength))
    ob = put(bpy.data.objects.new('wt', cu)); ob.location = loc; ob.rotation_euler = rot
    return ob


def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return Vector(a).lerp(Vector(b), u)
def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
def seg(u, a, b): return min(max((u - a) / (b - a), 0), 1)


def bez(p0, p1, p2, u):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    return p0 * (1 - u) ** 2 + p1 * 2 * u * (1 - u) + p2 * u * u


# ================================================================== OUTSIDE
CUR[0] = coll('out')
grid('ground', 400, ps1('steppe', 'out', 0.25))
box('asphalt', (150, 110, 0.1), ps1('asph', 'out', 0.25), (0, 0, 0.05))
FANS = []; STEAM = []
for hy in (-28, 0, 28):
    box('hallb', (64, 22, 9), ps1('wall', 'out', 0.5), (0, hy, 4.5))
    box('roofb', (64.4, 22.4, 0.3), ps1('roof', 'out', 0.25), (0, hy, 9.15))
    for row in (-6, 6):
        for k in range(8):
            x = -26 + k * 7.4
            box('chiller', (5, 3.4, 1.4), ps1('metal', 'out', 0.5), (x, hy + row, 10.0))
            fan = cone('fan', 1.25, 1.25, 0.1, ps1('fan', 'out', 0.4), segs=10)
            fan.location = (x - 1.2, hy + row, 10.75); FANS.append(fan)
            fan2 = cone('fan', 1.25, 1.25, 0.1, ps1('fan', 'out', 0.4), segs=10)
            fan2.location = (x + 1.2, hy + row, 10.75); FANS.append(fan2)
box('hatch', (3, 3, 0.5), ps1('dark', 'out'), (0, 0, 9.5))
for k in range(4):
    tx, ty = 47, -30 + 20 * k
    box('ctower', (9, 9, 11), ps1('metal', 'out', 0.4), (tx, ty, 5.5))
    box('ctop', (7, 7, 1.2), ps1('fan', 'out', 0.25), (tx, ty, 11.6))
    for j in range(5):
        b = ball('steam', 2.2 + j * 0.5, ps1('cloud', 'out', 1.0, emit=0.35), (tx, ty, 13 + j * 3), u=7, v=5)
        STEAM.append((b, Vector((tx, ty, 13)), j))
for k in range(6):
    box('transformer', (3, 2.5, 3.2), ps1('metal_dark', 'out', 1.0), (-48, -14 + k * 5.5, 1.7))


def pylon(x, y):
    tm = ps1('tower', 'out', 1.0); base = 2.6; top = 0.6; h = 22
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam('leg', (x + sx * base, y + sy * base, 0), (x + sx * top, y + sy * top, h), 0.25, tm)
    for z in (6, 12, 18):
        f = 1 - z / h; r = top + (base - top) * f
        for a, b in (((-1, -1), (1, -1)), ((-1, 1), (1, 1)), ((-1, -1), (-1, 1)), ((1, -1), (1, 1))):
            beam('tie', (x + a[0] * r, y + a[1] * r, z), (x + b[0] * r, y + b[1] * r, z), 0.15, tm)
    beam('arm', (x, y - 7, 19), (x, y + 7, 19), 0.3, tm)
    return [Vector((x, y - 6.5, 18.8)), Vector((x, y + 6.5, 18.8)), Vector((x, y, 21.8))]


PY = [pylon(x, 4) for x in (-62, -102, -142, -182)]
WIRES = []
for a, b in zip(PY[:-1], PY[1:]):
    for i in range(3):
        WIRES.append((a[i], b[i])); beam('wire', a[i], b[i], 0.06, ps1('dark', 'out'))
for i in range(3):
    beam('wire', PY[0][i], Vector((-48, -2 + i * 4, 3.3)), 0.06, ps1('dark', 'out'))
BOLTS = []
for i in range(4):
    a = PY[0][i % 3] if i < 3 else Vector((-48, 6, 3.4))
    b = Vector((-30 + i * 9, -6 + i * 4, 9.4))
    pts = [a.lerp(b, s / 7) + (Vector((random.uniform(-2, 2), random.uniform(-2, 2), random.uniform(-1.5, 1.5))) if 0 < s < 7 else Vector()) for s in range(8)]
    bolt = [beam('bolt', pts[s], pts[s + 1], 0.22, glow('#FFF6A8', 6.0)) for s in range(7)]
    BOLTS.append(bolt)
# giant phone in the steppe
PH = Vector((0, -95, 0))
box('phone', (6.4, 12.4, 0.6), ps1('phone', 'out', 1.0), PH + Vector((0, 0, 0.3)))
box('screen', (5.8, 11.4, 0.04), glow('#0F1626', 1.0), PH + Vector((0, 0, 0.62)))
box('bubble', (3.9, 1.3, 0.05), glow('#2F6BFF', 1.0), PH + Vector((0.8, 3.4, 0.66)))
wtxt('Привет!', PH + Vector((0.8, 3.4, 0.7)), 0.7, '#FFFFFF')
ANS = [box('bubble2', (4.6, 2.0, 0.05), glow('#3A4152', 1.0), PH + Vector((-0.4, 1.2, 0.66))),
       wtxt('Привет!\nЧем помочь?', PH + Vector((-0.4, 1.2, 0.7)), 0.6, '#FFFFFF')]
box('notch', (1.4, 0.3, 0.05), glow('#000000', 0.0), PH + Vector((0, 5.4, 0.66)))

# ================================================================== HALL (inside)
CUR[0] = coll('hall')
box('floor', (8, 80, 0.2), ps1('floor', 'hall', 0.5), (0, 0, -0.1))
box('ceil', (8, 80, 0.2), ps1('metal_dark', 'hall', 0.5), (0, 0, 4.4))
for sx in (-1, 1):
    box('wallh', (0.2, 80, 4.6), ps1('metal_dark', 'hall', 0.5), (sx * 4, 0, 2.2))
for sy in (-1, 1):
    box('endw', (8, 0.2, 4.6), ps1('metal_dark', 'hall', 0.5), (0, sy * 40, 2.2))
RACKM = []
for sx in (-1, 1):
    for half in (-1, 1):
        m = with_scale(ps1(f'rack{(sx + half) % 3}', 'hall', 1.0, emit=0.7), 1.43, 1.43, 0.435)
        RACKM.append(m)
        box('racks', (1.0, 37.8, 2.3), m, (sx * 1.7, half * 19.0, 1.15))
    box('tray', (0.6, 76, 0.08), ps1('pipe', 'hall', 1.0), (sx * 1.7, 0, 3.0))
    box('cables', (0.36, 76, 0.16), ps1('black', 'hall'), (sx * 1.7, 0, 3.12))
for y in range(-36, 37, 4):
    box('lamp', (0.35, 1.8, 0.06), glow('#E6F0FF', 1.6), (0, y, 4.27))
CUR[0] = coll('cool')
COOLM = ps1('coolant', 'hall', 2.0, emit=0.9); COOLOFF = add_offset(COOLM)
for sx in (-1, 1):
    for z in (0.6, 2.45):
        p = cone('pipe', 0.09, 0.09, 76, COOLM, segs=6); p.location = (sx * 1.16, 0, z); p.rotation_euler = (math.radians(90), 0, 0)

# GPU exploded (inside hall)
CUR[0] = coll('gpu')
GPU = put(bpy.data.objects.new('gpu', None)); GPU.location = (0, -6.2, 1.25); GPU.scale = (1.5, 1.5, 1.5)
GP = []


def gpart(ob, z0, z1, dx=0.0):
    ob.parent = GPU; GP.append((ob, Vector(ob.location), z0, z1, dx)); return ob


gpart(box('tray', (1.4, 1.0, 0.05), ps1('metal', 'hall', 1.0), (0, 0, 0)), -0.06, -0.55)
gpart(box('pcb', (1.2, 0.8, 0.05), ps1('pcb', 'hall', 1.2), (0, 0, 0)), 0.0, -0.2)
gpart(box('chip', (0.42, 0.42, 0.06), ps1('chip', 'hall', 2.4, emit=0.2), (0, 0, 0)), 0.055, 0.32)
for i, (x, y) in enumerate([(-0.32, -0.16), (-0.32, 0), (-0.32, 0.16), (0.32, -0.16), (0.32, 0), (0.32, 0.16)]):
    gpart(box('hbm', (0.11, 0.14, 0.12), ps1('hbm', 'hall', 4.0), (x, y, 0)), 0.09, 0.55, dx=0.25 * (1 if x > 0 else -1))
gpart(box('coldplate', (0.62, 0.62, 0.1), ps1('copper', 'hall', 1.5), (0, 0, 0)), 0.16, 0.95)
for i in range(14):
    x = -0.33 + i * 0.051
    gpart(box('fin', (0.022, 0.72, 0.36), ps1('fins', 'hall', 2.0), (x, 0, 0)), 0.4, 1.55, dx=x * 0.9)
GLOWCHIP = gpart(box('chipglow', (0.2, 0.2, 0.02), glow('#7CF8FF', 4.0), (0, 0, 0)), 0.09, 0.355)

# ================================================================== shared actors
CUR[0] = coll('actors')
HX = make_hex('out', 1.0)
DROPS = [parent(ball('drop', 0.06, glow('#7CC8FF', 2.0), (sx * 0.6, 0.1, 0.55 + 0.1 * i), u=5, v=3), HX['root']) for i, sx in enumerate((-1, 1, -1))]
PKT = [ball('packet', 0.45 - i * 0.07, glow('#5FF3FF', 5.0 - i * 0.7), (0, 0, 0), u=6, v=4) for i in range(5)]


def place_packet(pos_fn, u, spacing=0.03, show=True):
    for i, p in enumerate(PKT):
        p.hide_render = not show
        p.location = pos_fn(max(u - i * spacing, 0.0))


# ================================================================== HUD (dynamic)
CUR[0] = None
DYN = {}


def htxt(key, body, x, y, px, color, align='LEFT', valign='CENTER', shadow=2, rot=0.0, mono=False):
    objs = []
    for dx, dy, col, z in ((shadow, -shadow, '#000000', -1.0005), (0, 0, color, -1.0)):
        if col == '#000000' and shadow == 0: continue
        cu = bpy.data.curves.new('t', 'FONT'); cu.body = body; cu.font = MONO if mono else FONT
        cu.size = px * PX; cu.align_x = align; cu.align_y = valign; cu.space_line = 1.08
        cu.materials.append(glow(col, 1.0))
        ob = bpy.data.objects.new('t', cu); sc.collection.objects.link(ob); ob.parent = cam
        ob.location = ((x + dx) * PX, (y + dy) * PX, z); ob.rotation_euler = (0, 0, rot); objs.append(ob)
    DYN[key] = objs
    return objs


def hbox(key, x, y, w, h, color, border='#FFFFFF', bw=2):
    objs = []
    if border:
        b = box('pb', (w * PX + 2 * bw * PX, h * PX + 2 * bw * PX, 0.0001), glow(border, 1.0)); b.location = (x * PX, y * PX, -1.0015); objs.append(b)
    p = box('pf', (w * PX, h * PX, 0.0001), glow(color, 1.0)); p.location = (x * PX, y * PX, -1.001); objs.append(p)
    for o in objs: o.parent = cam
    DYN.setdefault(key, []); DYN[key] += objs
    return objs


def hshow(key, on):
    for o in DYN.get(key, []): o.hide_render = not on


def hset(key, body):
    for o in DYN.get(key, []):
        if o.type == 'FONT': o.data.body = body


htxt('lvl', 'УР. 2', -170, 300, 17, '#FFD23F'); htxt('area', 'ДАТА-ЦЕНТР ИИ', -170, 280, 12, '#FFFFFF')
htxt('hearts', '♥♥♥', 170, 300, 17, '#FF3B3B', align='RIGHT'); htxt('count', '◆ ЧИПЫ 0', 170, 280, 12, '#FFFFFF', align='RIGHT')
htxt('title', 'КУДА ЛЕТИТ\nТВОЙ «ПРИВЕТ»?', 0, 200, 30, '#FFD23F', align='CENTER', shadow=3)
hbox('dlg', 0, -250, 330, 96, '#13204A')
hbox('tag', -128, -195, 62, 20, '#FFD23F', border=None)
htxt('tagt', 'ХЕКС', -128, -195, 12, '#13204A', align='CENTER', shadow=0)
htxt('say', '', -152, -214, 14, '#FFFFFF', valign='TOP', shadow=1)
htxt('next', '▼', 150, -286, 11, '#FFD23F', align='CENTER', shadow=0)
htxt('combo', '×10 000!', 0, 150, 40, '#FFD23F', align='CENTER', shadow=3, rot=math.radians(6))
htxt('combo2', 'ТРИЛЛИОНЫ ОПЕРАЦИЙ В СЕКУНДУ', 0, 108, 12, '#FFFFFF', align='CENTER', shadow=2, rot=math.radians(6))
htxt('warn', '⚠ ПЕРЕГРЕВ! ⚠', 0, 170, 26, '#FF3B3B', align='CENTER', shadow=3)
htxt('temp', 'ТЕМП. ▮▮▮▮▮▮▮▮▮▮', 0, 138, 13, '#FF8A3B', align='CENTER', shadow=1)
htxt('cool', '✓ ОХЛАЖДЕНИЕ', 0, 170, 24, '#7CF8FF', align='CENTER', shadow=3)
htxt('energy', 'ЭНЕРГИЯ', 0, 190, 22, '#FFF27A', align='CENTER', shadow=3)
hbox('ebar', 0, 158, 220, 16, '#13204A')
EBAR = [box('es', (16 * PX, 10 * PX, 0.0001), glow('#FFE14D', 1.0)) for i in range(11)]
for i, e in enumerate(EBAR):
    e.parent = cam; e.location = ((-100 + i * 20) * PX, 158 * PX, -1.0); DYN.setdefault('ebar_s', []).append(e)
htxt('city', '= НЕБОЛЬШОЙ ГОРОД', 0, 128, 15, '#FFFFFF', align='CENTER', shadow=2)
hbox('endp', 0, 150, 316, 214, '#13204A')
htxt('endt', 'УРОВЕНЬ ПРОЙДЕН!', 0, 232, 20, '#FFD23F', align='CENTER', shadow=2)
htxt('ends', 'ЧИПЫ...........10 000\nПЕРЕГРЕВ.......0\nЭНЕРГИЯ.......ГОРОД', -138, 170, 13, '#FFFFFF', mono=True, shadow=1)
htxt('ends2', '«ПРИВЕТ»......ДОСТАВЛЕН', -138, 112, 13, '#7CF8FF', mono=True, shadow=1)
htxt('endn', '▶ ДАЛЬШЕ: ПОЧЕМУ\nПОДОРОЖАЛА ОПЕРАТИВКА?', 0, 74, 13, '#FFD23F', align='CENTER', shadow=1)
ALLK = list(DYN.keys())
# keep HUD in front of everything: shrink it toward the camera (same screen size)
HUDROOT = bpy.data.objects.new('hudroot', None); sc.collection.objects.link(HUDROOT)
HUDROOT.parent = cam; HUDROOT.scale = (0.08, 0.08, 0.08)
for k in ALLK + ['ebar_s']:
    for o in DYN.get(k, []):
        o.parent = HUDROOT
for e in EBAR:
    e.parent = HUDROOT


def wrap(s): return '\n'.join(textwrap.wrap(s, 28))


# ================================================================== shots
def hud_base(count_txt):
    for k in ALLK: hshow(k, False)
    for k in ('lvl', 'area', 'hearts', 'count', 'dlg', 'tag', 'tagt', 'say', 'next'): hshow(k, True)
    hset('count', count_txt)


def say(shot, tsec, blink):
    if shot['vstart'] is None: return
    u = seg(tsec, shot['vstart'], shot['vstart'] + shot['vdur'] * 0.92)
    full = shot['text']; n = int(len(full) * u)
    hset('say', wrap(full[:n] if n < len(full) else full)); hshow('next', u >= 1 and blink)


def day():
    sky('#B8D4E8', '#2E5AA8'); set_fog('out', '#B8D4E8', 80, 420); sun_d.energy = 3.0


def show_colls(*names):
    for n, c in COLL.items(): c.hide_render = n not in names


def chips_fmt(n): return '◆ ЧИПЫ ' + f'{int(n):,}'.replace(',', ' ')


def hex_at(loc, yaw, walk=0.0, arm_up=False, hop=0.0):
    HX['root'].location = Vector(loc) + Vector((0, 0, hop)); HX['root'].rotation_euler = (0, 0, yaw)
    hex_pose(HX, walk=walk, arm_up=arm_up, bolt=False)
    for d in DROPS: d.hide_render = True


def yaw_to(src, dst):
    d = Vector(dst) - Vector(src); return math.atan2(-d.x, d.y)


def snap(v, q=0.03): return Vector([round(c / q) * q for c in v])


def shot_hook(u, ts, f):
    day(); show_colls('out', 'actors')
    for a in ANS: a.hide_render = True
    hp = PH + Vector((-1.6, 2.4, 0.62 + 0.82))
    cpos = vlerp(PH + Vector((4.5, -6.0, 7.5)), PH + Vector((3.0, -9.0, 4.0)), ease(u))
    hex_at(hp, yaw_to(hp, cpos), walk=0.0, hop=abs(math.sin(ts * 6)) * 0.08 if u > 0.55 else 0)
    tgt = vlerp(PH + Vector((0, 2, 0.6)), Vector((0, 0, 9)), ease(seg(u, 0.45, 1.0)))
    look(snap(cpos), tgt)
    pk = lambda v: bez(PH + Vector((0.8, 3.4, 0.8)), Vector((0, -50, 45)), Vector((0, 0, 9.6)), v)
    pu = seg(u, 0.5, 1.0) * 0.45
    place_packet(pk, pu, show=u > 0.5)
    hshow('title', u < 0.62)


def shot_outside(u, ts, f):
    day(); show_colls('out', 'actors'); HX['root'].location = (0, 0, -50)
    look(snap(vlerp((70, -85, 48), (24, -36, 21), ease(u))), vlerp((0, -10, 6), (0, 0, 8), ease(u)))
    pk = lambda v: bez(PH + Vector((0.8, 3.4, 0.8)), Vector((0, -50, 45)), Vector((0, 0, 9.6)), v)
    place_packet(pk, 0.45 + 0.55 * ease(seg(u, 0.0, 0.75)), show=u < 0.78)


def hall_fog(): set_fog('hall', '#0A1630', 3, 30)


def shot_hall(u, ts, f):
    show_colls('hall', 'actors'); hall_fog()
    hy = lerp(-26, -12.5, u)
    hex_at((0, hy, 0.82), 0.0, walk=ts * 9.5)
    look(snap((0.7, hy - 4.2, 2.3)), (0, hy + 6, 1.4))
    pk = lambda v: Vector((0, lerp(-34, 34, v), 3.3 + math.sin(v * 20) * 0.2))
    place_packet(pk, seg(u, 0.05, 0.7), spacing=0.012, show=0.05 < u < 0.7)
    return chips_fmt(2500 * ease(u))


def gpu_pose(e):
    for ob, base, z0, z1, dx in GP:
        ob.location = base + Vector((dx * e, 0, lerp(z0, z1, e)))


def shot_gpu(u, ts, f):
    show_colls('hall', 'actors', 'gpu'); hall_fog()
    hex_at((-0.75, -7.9, 0.82), yaw_to((-0.75, -7.9, 0), (0, -6.2, 0)), walk=0.0)
    GPU.rotation_euler = (0, 0, ts * 0.6)
    gpu_pose(ease(seg(u, 0.12, 0.55)))
    c = Vector((0, -6.2, 1.95))
    look(snap(c + Vector((lerp(0.9, -0.5, ease(u)), -3.9, 0.45))), c + Vector((0, 0, 0.15)))
    on = u > 0.5
    hshow('combo', on); hshow('combo2', on)
    n = 2500 + 7500 * ease(seg(u, 0.45, 0.62))
    return chips_fmt(n)


def shot_heat(u, ts, f):
    blink = (f // 3) % 2 == 0
    if u < 0.62:
        show_colls('hall', 'actors', 'cool') if u >= 0.3 else show_colls('hall', 'actors')
        hy = -12.0
        if u < 0.3:
            set_fog('hall', '#6A1010', 1.5, 16)
            hex_at((random.uniform(-0.03, 0.03), hy, 0.82), 0.0)
            for d in DROPS: d.hide_render = False
            hshow('warn', blink); hshow('temp', True)
        else:
            set_fog('hall', '#082A48', 3, 30)
            hex_at((0, hy, 0.82), 0.0, walk=0.0)
            hshow('cool', True)
        COOLOFF.inputs[1].default_value = (0, -ts * 3.0, 0)
        look(snap((1.0, hy - 3.6, 2.0)), (-0.6, hy + 6, 1.6))
    else:
        day(); show_colls('out', 'actors'); HX['root'].location = (0, 0, -50)
        v = seg(u, 0.62, 1.0)
        look(snap(vlerp((-12, -22, 15), (-6, -17, 12.5), ease(v))), (4, -2, 10))
        for fn in FANS: fn.rotation_euler = (0, 0, ts * 14)
    return chips_fmt(10000)


def shot_power(u, ts, f):
    sky('#F2A65A', '#3B2A6B'); set_fog('out', '#8A5A7A', 60, 380); sun_d.energy = 2.2
    show_colls('out', 'actors'); HX['root'].location = (0, 0, -50)
    look(snap(vlerp((-150, -38, 9), (-118, -30, 12), ease(u))), (-60, 0, 12))
    for b in BOLTS:
        on = random.random() < 0.55
        for s in b: s.hide_render = not on
    hshow('energy', True); hshow('ebar', True); hshow('city', u > 0.45)
    k = int(11 * ease(seg(u, 0.05, 0.6)))
    for i, e in enumerate(EBAR): e.hide_render = i >= k
    return chips_fmt(10000)


def shot_return(u, ts, f, end=False):
    day(); show_colls('out', 'actors')
    for a in ANS: a.hide_render = u < 0.45 and not end
    hp = PH + Vector((-1.6, 2.4, 0.62 + 0.82))
    cpos = PH + Vector((3.2, -7.5, 5.0)) if not end else PH + Vector((2.6, -5.5, 3.4))
    hop = abs(math.sin(ts * 7)) * 0.35 if (u > 0.5 or end) else 0
    hex_at(hp, yaw_to(hp, cpos), arm_up=(u > 0.5 or end), hop=hop)
    look(snap(cpos), PH + Vector((-0.3, 1.8, 0.8)) if not end else PH + Vector((-1.2, 2.3, 1.6)))
    pk = lambda v: bez(Vector((0, 0, 9.6)), Vector((0, -50, 45)), PH + Vector((-0.4, 1.2, 0.8)), v)
    place_packet(pk, 0.55 + 0.45 * ease(seg(u, 0.0, 0.45)), show=(u < 0.45 and not end))


SHOTS = dict(hook=shot_hook, outside=shot_outside, hall=shot_hall, gpu=shot_gpu, heat=shot_heat, power=shot_power, ret=shot_return)


def render_frame(f):
    ts = f / FPS
    shot = [s for s in TL['shots'] if s['start'] <= ts < s['end']] or [TL['shots'][-1]]
    shot = shot[0]; u = (ts - shot['start']) / (shot['end'] - shot['start'])
    for i, m in enumerate(RACKM):
        img = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
        img.image = T[f'rack{(f // 2 + i) % 3}']
    for fn in FANS: fn.rotation_euler = (0, 0, ts * 6)
    for b, base, j in STEAM:
        k = (ts * 0.25 + j / 5) % 1.0; b.location = base + Vector((k * 3, 0, k * 15)); b.scale = (1 + k,) * 3
    for b in BOLTS:
        for s in b: s.hide_render = True
    for p in PKT: p.hide_render = True
    for a_ in ANS: a_.hide_render = True
    name = shot['name']
    count = chips_fmt(0)
    hud_base(count)
    if name == 'end':
        shot_return(1.0, ts, f, end=True)
        for k in ALLK: hshow(k, False)
        for k in ('lvl', 'area', 'hearts', 'count', 'endp', 'endt', 'ends', 'ends2', 'endn'): hshow(k, True)
        hset('count', chips_fmt(10000))
        if (f // 4) % 2: hshow('endn', False)
    else:
        fn = SHOTS['ret' if name == 'return' else name]
        r = fn(u, ts, f)
        if r: hset('count', r)
        elif name == 'return': hset('count', chips_fmt(10000))
        say(shot, ts, (f // 4) % 2 == 0)
    sc.render.filepath = os.path.join(OUT, f'f{f:04d}.png')
    bpy.ops.render.render(write_still=True)


if MODE == 'stills':
    for name in ('hook', 'outside', 'hall', 'gpu', 'heat', 'power', 'return', 'end'):
        s = [x for x in TL['shots'] if x['name'] == name][0]
        f = int((s['start'] + (s['end'] - s['start']) * 0.7) * FPS)
        render_frame(f); os.replace(os.path.join(OUT, f'f{f:04d}.png'), os.path.join(OUT, f'still_{name}.png'))
        print('RENDERED', name)
else:
    for f in range(F0, F1 + 1):
        render_frame(f)
        if f % 50 == 0: print('FRAME', f, flush=True)
    print('RENDERED frames', F0, F1)
