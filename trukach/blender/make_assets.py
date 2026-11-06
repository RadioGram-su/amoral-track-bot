"""Generates the 3D assets for style B.

Run:  blender -b -P blender/make_assets.py -- <out_dir>
Produces:
  character_mira.glb  — segmented acrobat (one object per bone, origin at the proximal joint,
                        bone along Blender +Z == Godot +Y, front = +X). Rigid segments with
                        rounded ends: no skin stretching, so no twisted joints.
  props.glb           — rooftop props (crate, ac_unit, tank, vent, chimney, antenna, rail, post,
                        bar, skylight, flag).
Sizes match core/rig.gd exactly.
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "."

# --- rig constants (keep in sync with core/rig.gd) ---
SPINE, NECK, HEAD_R = 0.50, 0.155, 0.118
THIGH, SHIN, FOOT, HEEL, SOLE = 0.445, 0.43, 0.19, 0.06, 0.06
UARM, FARM, HAND = 0.29, 0.255, 0.085


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb, rough=0.6, metal=0.0, emit=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = 2.0
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def new_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(material)
    return ob


def loft(name, rings, material, seg=28, dome0=True, dome1=True):
    """rings: list of (z, rx, ry, cx). Ellipse in XY (rx front/back, ry side) at height z."""
    bm = bmesh.new()
    rr = list(rings)
    # hemispherical end caps
    if dome0:
        z, rx, ry, cx = rr[0]
        caps = []
        for k in range(4, 0, -1):
            a = k / 4 * math.pi / 2
            caps.append((z - math.sin(a) * min(rx, ry) * 0.9, rx * math.cos(a) + 1e-4, ry * math.cos(a) + 1e-4, cx))
        rr = caps + rr
    if dome1:
        z, rx, ry, cx = rr[-1]
        for k in range(1, 5):
            a = k / 4 * math.pi / 2
            rr.append((z + math.sin(a) * min(rx, ry) * 0.9, rx * math.cos(a) + 1e-4, ry * math.cos(a) + 1e-4, cx))
    verts = []
    for (z, rx, ry, cx) in rr:
        ring = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            ring.append(bm.verts.new((cx + rx * math.cos(t), ry * math.sin(t), z)))
        verts.append(ring)
    for a, b in zip(verts[:-1], verts[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(verts[0])))
    bm.faces.new(verts[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm, material)


def ellipsoid(name, center, radii, material, seg=28, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return new_obj(name, bm, material)


def box(name, size, center, material, bevel=0.02):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES", profile=0.5)
    ob = new_obj(name, bm, material)
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def cyl(name, r, h, center, material, axis="Z", seg=24, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    if axis == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    elif axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    ob = new_obj(name, bm, material)
    return ob


def join(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def transform(ob, m):
    ob.data.transform(m)


def export(path, names=None):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)


# ======================================================================= character
def character():
    reset()
    jacket = mat("jacket", srgb("#1f9e95"), 0.55)
    jacket_d = mat("jacket_trim", srgb("#f2ede2"), 0.5)
    leg = mat("leggings", srgb("#25252e"), 0.7)
    skin = mat("skin", srgb("#e7b48e"), 0.5)
    hair = mat("hair", srgb("#3a2320"), 0.45)
    shoe = mat("shoe", srgb("#f4f1ea"), 0.5)
    sole = mat("sole", srgb("#ff6a45"), 0.6)
    eye = mat("eye", srgb("#16121c"), 0.2)

    # torso along +Z from pelvis (0) to neck base (SPINE), front +X
    t = loft("torso", [(0.0, 0.112, 0.142, -0.005), (0.12, 0.105, 0.132, 0.0), (0.25, 0.122, 0.158, 0.012),
                       (0.37, 0.115, 0.182, 0.008), (0.445, 0.085, 0.15, 0.0), (0.49, 0.05, 0.06, 0.0)], jacket)
    zip_ = box("zip", (0.012, 0.012, 0.36), (0.125, 0.0, 0.25), jacket_d, 0.004)
    hem = loft("hem", [(0.02, 0.118, 0.148, -0.005), (0.06, 0.118, 0.148, -0.005)], jacket_d, dome0=False, dome1=False)
    join("torso", [t, zip_, hem])
    ellipsoid("pelvis", (0.0, 0.0, 0.005), (0.118, 0.145, 0.09), leg)
    loft("neck", [(0.0, 0.045, 0.045, 0.0), (NECK * 0.7, 0.042, 0.042, 0.0)], skin)
    # head: origin at head centre, up +Z, face +X
    h = ellipsoid("head", (0, 0, 0), (HEAD_R, HEAD_R * 0.92, HEAD_R * 1.04), skin)
    nose = ellipsoid("nose", (HEAD_R * 0.96, 0.0, -0.012), (0.022, 0.016, 0.026), skin)
    hr = ellipsoid("hair", (-0.026, 0.0, 0.012), (HEAD_R * 0.92, HEAD_R * 0.98, HEAD_R * 1.05), hair)
    tail = loft("tail", [(0.0, 0.035, 0.035, 0.0), (0.06, 0.04, 0.038, 0.0), (0.17, 0.028, 0.026, 0.0), (0.24, 0.012, 0.012, 0.0)], hair)
    transform(tail, Matrix.Translation((-0.11, 0.0, 0.03)) @ Matrix.Rotation(math.radians(-150), 4, "Y"))
    tie = loft("tie", [(0.0, 0.03, 0.03, 0.0), (0.02, 0.03, 0.03, 0.0)], jacket)
    transform(tie, Matrix.Translation((-0.115, 0.0, 0.03)) @ Matrix.Rotation(math.radians(-150), 4, "Y"))
    eyes = []
    for s in (-1, 1):
        eyes.append(ellipsoid("eye", (HEAD_R * 0.86, s * 0.045, 0.018), (0.012, 0.012, 0.016), eye))
    brow = []
    for s in (-1, 1):
        brow.append(box("brow", (0.012, 0.03, 0.007), (HEAD_R * 0.9, s * 0.045, 0.048), hair, 0.002))
    join("head", [h, nose, hr, tail, tie] + eyes + brow)

    # limbs along +Z (proximal joint at 0), front +X
    ua = loft("upper_arm", [(0.0, 0.054, 0.054, 0.0), (0.12, 0.05, 0.048, 0.0), (UARM, 0.042, 0.042, 0.0)], jacket)
    st = loft("stripe", [(0.03, 0.056, 0.056, 0.0), (0.05, 0.056, 0.056, 0.0)], jacket_d, dome0=False, dome1=False)
    join("upper_arm", [ua, st])
    fa = loft("forearm", [(0.0, 0.042, 0.042, 0.0), (0.09, 0.043, 0.045, 0.004), (FARM, 0.033, 0.036, 0.0)], jacket)
    cuff = loft("cuff", [(FARM - 0.035, 0.037, 0.04, 0.0), (FARM - 0.005, 0.037, 0.04, 0.0)], jacket_d, dome0=False, dome1=False)
    join("forearm", [fa, cuff])
    hd = loft("hand", [(0.0, 0.024, 0.036, 0.0), (0.05, 0.022, 0.042, 0.004), (HAND, 0.016, 0.034, 0.008)], skin)
    th = ellipsoid("thumb", (0.018, 0.03, 0.035), (0.014, 0.012, 0.03), skin)
    join("hand", [hd, th])
    loft("thigh", [(0.0, 0.082, 0.078, 0.0), (0.16, 0.076, 0.07, 0.006), (THIGH, 0.056, 0.054, 0.0)], leg)
    loft("shin", [(0.0, 0.056, 0.052, 0.0), (0.11, 0.06, 0.052, -0.012), (0.28, 0.046, 0.042, -0.004), (SHIN, 0.038, 0.036, 0.0)], leg)
    # shoe: ankle at origin; sole SOLE below; heel -HEEL, toe +FOOT along +X
    body = loft("shoe_body", [(0.0, 0.038, 0.045, 0.0), (0.09, 0.034, 0.05, 0.0), (0.2, 0.024, 0.042, 0.0), (0.25, 0.012, 0.03, 0.0)], shoe)
    transform(body, Matrix.Translation((-HEEL - 0.015, 0.0, -0.03)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    sl = box("sole", (0.27, 0.09, 0.022), (0.06, 0.0, -SOLE + 0.011), sole, 0.008)
    collar = loft("collar", [(-0.02, 0.042, 0.042, 0.0), (0.03, 0.04, 0.04, 0.0)], shoe, dome0=False)
    lace = box("lace", (0.09, 0.05, 0.008), (0.06, 0.0, 0.003), sole, 0.003)
    join("foot", [body, sl, collar, lace])
    export(os.path.join(OUT, "character_mira.glb"))


# ======================================================================= props
def props():
    reset()
    wood = mat("wood", srgb("#b07a45"), 0.8)
    wood_d = mat("wood_dark", srgb("#6e4627"), 0.85)
    steel = mat("steel", srgb("#b9c0ca"), 0.35, 0.6)
    steel_d = mat("steel_dark", srgb("#454b57"), 0.5, 0.4)
    paint = mat("paint_white", srgb("#d9dde3"), 0.55)
    rust = mat("tank_wood", srgb("#7a4c38"), 0.8)
    brick = mat("brick", srgb("#8b4a3d"), 0.85)
    dark = mat("dark", srgb("#24222c"), 0.6)
    glass = mat("glass", srgb("#7fb6d6"), 0.08, 0.2)
    red = mat("lamp", srgb("#ff3b2f"), 0.4, emit=srgb("#ff3b2f"))
    black = mat("flag_black", srgb("#16141c"), 0.7)
    white = mat("flag_white", srgb("#f2f2f2"), 0.7)
    objs = {}

    # crate 0.9 x 0.85 x 0.9 (origin bottom-centre)
    parts = [box("c_core", (0.86, 0.86, 0.81), (0, 0, 0.425), wood, 0.01)]
    for x in (-0.43, 0.43):
        for y in (-0.43, 0.43):
            parts.append(box("c_post", (0.06, 0.06, 0.85), (x, y, 0.425), wood_d, 0.008))
    for z in (0.03, 0.82):
        for y in (-0.43, 0.43):
            parts.append(box("c_rail", (0.9, 0.06, 0.06), (0, y, z), wood_d, 0.008))
        for x in (-0.43, 0.43):
            parts.append(box("c_rail", (0.06, 0.9, 0.06), (x, 0, z), wood_d, 0.008))
    br = box("c_brace", (1.05, 0.04, 0.07), (0, -0.445, 0.425), wood_d, 0.006)
    br.data.transform(Matrix.Translation((0, -0.445, 0.425)) @ Matrix.Rotation(math.radians(43), 4, "Y") @ Matrix.Translation((0, 0.445, -0.425)))
    parts.append(br)
    objs["crate"] = join("crate", parts)

    # AC unit 1.1 x 0.8 x 0.7, fan facing the camera (Blender -Y == Godot +Z)
    parts = [box("a_body", (1.1, 0.7, 0.8), (0, 0, 0.42), paint, 0.03)]
    parts.append(cyl("a_fan", 0.25, 0.04, (0.22, -0.36, 0.43), steel_d, axis="Y", seg=32))
    for i in range(6):
        parts.append(box("a_fin", (0.36, 0.02, 0.025), (-0.27, -0.355, 0.2 + i * 0.08), steel_d, 0.004))
    for x in (-0.45, 0.45):
        parts.append(box("a_foot", (0.08, 0.6, 0.04), (x, 0, 0.02), dark, 0.005))
    blade = []
    for k in range(4):
        b = box("a_blade", (0.2, 0.01, 0.05), (0.1, 0.0, 0.0), steel, 0.004)
        b.data.transform(Matrix.Translation((0.22, -0.385, 0.43)) @ Matrix.Rotation(k * math.pi / 2, 4, "Y"))
        blade.append(b)
    objs["ac_unit"] = join("ac_unit", parts + blade)

    # water tank (1.9 wide, 3.2 tall)
    parts = []
    for x in (-0.7, 0.7):
        for y in (-0.7, 0.7):
            parts.append(cyl("t_leg", 0.05, 1.45, (x * 0.95, y * 0.95, 0.72), dark))
    for z in (0.45, 1.05):
        for y in (-0.66, 0.66):
            parts.append(box("t_brace", (1.4, 0.03, 0.04), (0, y, z), dark, 0.004))
    parts.append(cyl("t_floor", 0.98, 0.08, (0, 0, 1.45), dark, seg=40))
    parts.append(cyl("t_barrel", 0.92, 1.35, (0, 0, 2.15), rust, seg=40))
    for z in (1.65, 2.05, 2.45, 2.75):
        parts.append(cyl("t_band", 0.935, 0.035, (0, 0, z), dark, seg=40))
    parts.append(cyl("t_roof", 1.02, 0.55, (0, 0, 3.08), dark, seg=40, r2=0.05))
    objs["tank"] = join("tank", parts)

    # vent pipe with cap
    parts = [cyl("v_pipe", 0.12, 0.85, (0, 0, 0.425), steel), cyl("v_cap", 0.24, 0.12, (0, 0, 0.98), steel, r2=0.08),
             cyl("v_ring", 0.14, 0.05, (0, 0, 0.1), steel_d)]
    objs["vent"] = join("vent", parts)

    # chimney 0.7 x 2.2
    parts = [box("ch_body", (0.7, 0.7, 2.2), (0, 0, 1.1), brick, 0.01), box("ch_cap", (0.86, 0.86, 0.12), (0, 0, 2.22), dark, 0.02)]
    for z in range(1, 11):
        parts.append(box("ch_mortar", (0.71, 0.71, 0.012), (0, 0, z * 0.2), mat("mortar", srgb("#6d3a31"), 0.9), 0.0))
    objs["chimney"] = join("chimney", parts)

    # antenna mast 4 m
    parts = [cyl("an_mast", 0.035, 4.0, (0, 0, 2.0), dark)]
    for i, w in enumerate((0.8, 0.62, 0.44)):
        parts.append(box("an_bar", (w, 0.025, 0.025), (0, 0, 1.9 + i * 0.6), dark, 0.0))
    parts.append(ellipsoid("an_lamp", (0, 0, 4.05), (0.06, 0.06, 0.06), red))
    objs["antenna"] = join("antenna", parts)

    # railing tile, 1.1 m long along +X, 1.0 high
    parts = [cyl("r_post", 0.025, 1.0, (0, 0, 0.5), steel_d), cyl("r_top", 0.03, 1.1, (0.55, 0, 1.0), steel_d, axis="X"),
             cyl("r_mid", 0.018, 1.1, (0.55, 0, 0.55), steel_d, axis="X")]
    objs["rail"] = join("rail", parts)

    # bar support post 3 m and the bar itself (along Blender Y == Godot Z), 3.4 m long
    parts = [cyl("p_post", 0.06, 3.0, (0, 0, 1.5), steel_d), box("p_base", (0.4, 0.4, 0.05), (0, 0, 0.025), dark, 0.01)]
    objs["post"] = join("post", parts)
    objs["bar"] = cyl("bar", 0.04, 3.4, (0, 0, 0), steel, axis="Y", seg=24)

    # skylight 2.2 x 0.5
    sk = box("s_frame", (2.2, 1.2, 0.18), (0, 0, 0.09), dark, 0.01)
    gl = box("s_glass", (2.0, 1.05, 0.3), (0, 0, 0.32), glass, 0.0)
    gl.data.transform(Matrix.Translation((0, 0, 0.18)) @ Matrix.Rotation(math.radians(-12), 4, "X") @ Matrix.Translation((0, 0, -0.18)))
    objs["skylight"] = join("skylight", [sk, gl])

    # finish flag: pole 2.6 m + checkered cloth 0.9 x 0.6
    parts = [cyl("f_pole", 0.03, 2.6, (0, 0, 1.3), steel)]
    for cx in range(6):
        for cy in range(4):
            parts.append(box("f_cell", (0.15, 0.01, 0.15), (0.075 + cx * 0.15, 0, 2.55 - 0.075 - cy * 0.15), white if (cx + cy) % 2 == 0 else black, 0.0))
    objs["flag"] = join("flag", parts)

    export(os.path.join(OUT, "props.glb"))


character()
props()
print("ASSETS_OK", OUT)
