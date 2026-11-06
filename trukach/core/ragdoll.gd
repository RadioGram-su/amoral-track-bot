class_name Ragdoll
extends RefCounted
## Position-based (Verlet) ragdoll with anatomical angle limits, so a falling body never
## bends a knee or an elbow the wrong way. Same joint names as Rig.fk().

const G := 22.0
const SUB := 3
const ITER := 6
const DAMP := 0.998
const FRICTION := 0.45
const RESTITUTION := 0.12

const NAMES := ["pelvis", "chest", "neck", "head", "knee_l", "ankle_l", "toe_l", "knee_r", "ankle_r", "toe_r", "elbow_l", "hand_l", "elbow_r", "hand_r"]
const MASS := [3.0, 3.0, 1.0, 1.2, 1.2, 0.6, 0.3, 1.2, 0.6, 0.3, 0.6, 0.4, 0.6, 0.4]
const PELVIS := 0
const CHEST := 1
const NECKI := 2
const HEAD := 3
const KNEE_L := 4
const ANKLE_L := 5
const TOE_L := 6
const KNEE_R := 7
const ANKLE_R := 8
const TOE_R := 9
const ELBOW_L := 10
const HAND_L := 11
const ELBOW_R := 12
const HAND_R := 13

var level: Level
var p := PackedVector2Array()
var pp := PackedVector2Array()
var im := PackedFloat32Array()
var rad := PackedFloat32Array()
var links: Array = []
var f := 1
var active := false


func _init(lv: Level) -> void:
	level = lv


func start(j: Dictionary, jprev: Dictionary, dt: float, vel: Vector2, facing: int) -> void:
	f = facing
	var n := NAMES.size()
	p.resize(n)
	pp.resize(n)
	im.resize(n)
	rad.resize(n)
	var sdt := 1.0 / 120.0 / SUB
	for i in n:
		var key: String = NAMES[i]
		p[i] = j[key]
		var pv: Vector2 = (j[key] - jprev.get(key, j[key])) / maxf(dt, 0.001)
		if pv.length() > 20.0:
			pv = pv.normalized() * 20.0
		var w := 1.0
		if i == HEAD or i == NECKI or i == CHEST:
			w = 1.25
		pp[i] = p[i] - (pv * 0.35 + vel * w) * sdt
		im[i] = 1.0 / MASS[i]
		rad[i] = 0.12 if i == HEAD else 0.055
	links.clear()
	for pair in [[PELVIS, CHEST], [CHEST, NECKI], [NECKI, HEAD], [PELVIS, NECKI],
			[PELVIS, KNEE_L], [KNEE_L, ANKLE_L], [ANKLE_L, TOE_L],
			[PELVIS, KNEE_R], [KNEE_R, ANKLE_R], [ANKLE_R, TOE_R],
			[CHEST, ELBOW_L], [ELBOW_L, HAND_L], [CHEST, ELBOW_R], [ELBOW_R, HAND_R]]:
		links.append([pair[0], pair[1], p[pair[0]].distance_to(p[pair[1]])])
	active = true


func _abs(v: Vector2) -> float:
	# angle from "down", positive towards facing direction
	return atan2(f * v.x, -v.y)


func _upang(v: Vector2) -> float:
	# angle from "up", positive towards facing direction
	return atan2(f * v.x, v.y)


func _dn(a: float) -> Vector2:
	return Vector2(f * sin(a), -cos(a))


func _upv(a: float) -> Vector2:
	return Vector2(f * sin(a), cos(a))


func _lim(x: float, lo: float, hi: float) -> float:
	var mid := (lo + hi) * 0.5
	return clampf(wrapf(x, mid - PI, mid + PI), lo, hi)


func _move_sub(idx: Array, delta: Vector2) -> void:
	for i in idx:
		p[i] += delta


func _angles() -> void:
	var b := _upang(p[CHEST] - p[PELVIS])
	# neck
	var nb := _upang(p[HEAD] - p[NECKI])
	var nn := _lim(nb - b, -0.7, 0.8)
	if absf(nn - (nb - b)) > 1e-4:
		p[HEAD] = p[NECKI] + _upv(b + nn) * p[HEAD].distance_to(p[NECKI])
	for s in 2:
		var kn := KNEE_L if s == 0 else KNEE_R
		var an := ANKLE_L if s == 0 else ANKLE_R
		var to := TOE_L if s == 0 else TOE_R
		var el := ELBOW_L if s == 0 else ELBOW_R
		var ha := HAND_L if s == 0 else HAND_R
		# hip relative to trunk
		var at := _abs(p[kn] - p[PELVIS])
		var hh := _lim(at + b, -0.6, 2.6)
		if absf(hh - (at + b)) > 1e-4:
			var old: Vector2 = p[kn]
			p[kn] = p[PELVIS] + _dn(hh - b) * p[kn].distance_to(p[PELVIS])
			_move_sub([an, to], p[kn] - old)
			at = hh - b
		# knee: only bends forwards
		var sg := _abs(p[an] - p[kn])
		var kk := _lim(at - sg, 0.0, 2.62)
		if absf(kk - (at - sg)) > 1e-4:
			var old2: Vector2 = p[an]
			p[an] = p[kn] + _dn(at - kk) * p[an].distance_to(p[kn])
			_move_sub([to], p[an] - old2)
			sg = at - kk
		# ankle
		var fa := _abs(p[to] - p[an])
		var aa := _lim(sg + PI * 0.5 - fa, -0.6, 0.9)
		if absf(aa - (sg + PI * 0.5 - fa)) > 1e-4:
			p[to] = p[an] + _dn(sg + PI * 0.5 - aa) * p[to].distance_to(p[an])
		# shoulder
		var au := _abs(p[el] - p[CHEST])
		var ss := _lim(au + b, -1.0, 3.25)
		if absf(ss - (au + b)) > 1e-4:
			var old3: Vector2 = p[el]
			p[el] = p[CHEST] + _dn(ss - b) * p[el].distance_to(p[CHEST])
			_move_sub([ha], p[el] - old3)
			au = ss - b
		# elbow: only bends one way
		var af := _abs(p[ha] - p[el])
		var ee := _lim(af - au, 0.0, 2.55)
		if absf(ee - (af - au)) > 1e-4:
			p[ha] = p[el] + _dn(au + ee) * p[ha].distance_to(p[el])


func _collide(friction: bool) -> void:
	for i in p.size():
		for r in level.solids:
			var g: Rect2 = r.grow(rad[i])
			var q: Vector2 = p[i]
			if not (q.x > g.position.x and q.x < g.end.x and q.y > g.position.y and q.y < g.end.y):
				continue
			var dl := q.x - g.position.x
			var dr := g.end.x - q.x
			var db := q.y - g.position.y
			var dt := g.end.y - q.y
			var m := minf(minf(dl, dr), minf(db, dt))
			var nrm := Vector2.ZERO
			if m == dt:
				q.y = g.end.y
				nrm = Vector2(0, 1)
			elif m == db:
				q.y = g.position.y
				nrm = Vector2(0, -1)
			elif m == dl:
				q.x = g.position.x
				nrm = Vector2(-1, 0)
			else:
				q.x = g.end.x
				nrm = Vector2(1, 0)
			p[i] = q
			if friction:
				var vel: Vector2 = p[i] - pp[i]
				var vn := vel.dot(nrm)
				var vt := vel - nrm * vn
				if vn < 0.0:
					vn = -vn * RESTITUTION
				vel = vt * (1.0 - FRICTION) + nrm * vn
				pp[i] = p[i] - vel


func step(dt: float) -> void:
	if not active:
		return
	var sdt := dt / SUB
	for _s in SUB:
		for i in p.size():
			var vel: Vector2 = (p[i] - pp[i]) * DAMP
			pp[i] = p[i]
			p[i] += vel + Vector2(0.0, -G) * sdt * sdt
		for _it in ITER:
			for L in links:
				var a: int = L[0]
				var b: int = L[1]
				var d: Vector2 = p[b] - p[a]
				var len := d.length()
				if len < 1e-6:
					continue
				var w := im[a] + im[b]
				var diff := (len - float(L[2])) / (len * w)
				p[a] += d * diff * im[a]
				p[b] -= d * diff * im[b]
			_angles()
			_collide(false)
		_collide(true)


func joints() -> Dictionary:
	var j := {}
	for i in NAMES.size():
		j[NAMES[i]] = p[i]
	for sx in ["_l", "_r"]:
		var e: Vector2 = j["elbow" + sx]
		var hnd: Vector2 = j["hand" + sx]
		j["wrist" + sx] = hnd + (e - hnd).normalized() * Rig.HAND
		var a: Vector2 = j["ankle" + sx]
		var t: Vector2 = j["toe" + sx]
		j["heel" + sx] = a - (t - a).normalized() * Rig.HEEL
	return j
