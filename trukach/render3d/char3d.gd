class_name Char3D
extends Node3D
## Drives the Blender-made segmented character from the 2D skeleton joints.
## Every segment is rigid and rounded at both ends -> no skin stretching or candy-wrapper twists.

const UP := 0
const DOWN := 1
const ARM_Z := 0.165
const LEG_Z := 0.085

var parts := {}


func setup(scene: Node) -> void:
	for n in ["torso", "pelvis", "neck", "head"]:
		_take(scene, n, n)
	for n in ["upper_arm", "forearm", "hand", "thigh", "shin", "foot"]:
		_take(scene, n, n + "_l")
		_take(scene, n, n + "_r")


func _take(scene: Node, src_name: String, key: String) -> void:
	var src := scene.find_child(src_name, true, false) as MeshInstance3D
	if src == null:
		push_error("missing segment " + src_name)
		return
	var mi := MeshInstance3D.new()
	mi.mesh = src.mesh
	for s in src.get_surface_override_material_count():
		mi.set_surface_override_material(s, src.get_surface_override_material(s))
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mi)
	parts[key] = mi


func _seg(key: String, a: Vector2, b: Vector2, kind: int, z: float, f: int) -> void:
	var mi: MeshInstance3D = parts.get(key)
	if mi == null:
		return
	var d := b - a
	if d.length() < 1e-5:
		d = Vector2(0, 1 if kind == UP else -1)
	d = d.normalized()
	var fr := d.rotated((-PI * 0.5 if kind == UP else PI * 0.5) * f)
	var y := Vector3(d.x, d.y, 0.0)
	var x := Vector3(fr.x, fr.y, 0.0)
	mi.transform = Transform3D(Basis(x, y, x.cross(y)), Vector3(a.x, a.y, z))


func _foot(key: String, j: Dictionary, sx: String, z: float, f: int) -> void:
	var mi: MeshInstance3D = parts.get(key)
	if mi == null:
		return
	var d: Vector2 = (j["toe" + sx] - j["heel" + sx]).normalized()
	var up := d.rotated(PI * 0.5 * f)
	var x := Vector3(d.x, d.y, 0.0)
	var y := Vector3(up.x, up.y, 0.0)
	var a: Vector2 = j["ankle" + sx]
	mi.transform = Transform3D(Basis(x, y, x.cross(y)), Vector3(a.x, a.y, z))


func update_from(j: Dictionary, f: int) -> void:
	if j.is_empty():
		return
	_seg("pelvis", j["pelvis"], j["neck"], UP, 0.0, f)
	_seg("torso", j["pelvis"], j["neck"], UP, 0.0, f)
	_seg("neck", j["neck"], j["head"], UP, 0.0, f)
	var hm: MeshInstance3D = parts.get("head")
	if hm:
		_seg("head", j["head"], j["head"] + (j["head"] - j["neck"]), UP, 0.0, f)
	for sx in ["_l", "_r"]:
		var side := (1.0 if sx == "_r" else -1.0) * f
		var az := ARM_Z * side
		var lz := LEG_Z * side
		_seg("upper_arm" + sx, j["chest"], j["elbow" + sx], DOWN, az, f)
		_seg("forearm" + sx, j["elbow" + sx], j["wrist" + sx], DOWN, az, f)
		_seg("hand" + sx, j["wrist" + sx], j["hand" + sx], DOWN, az, f)
		_seg("thigh" + sx, j["pelvis"], j["knee" + sx], DOWN, lz, f)
		_seg("shin" + sx, j["knee" + sx], j["ankle" + sx], DOWN, lz, f)
		_foot("foot" + sx, j, sx, lz, f)
