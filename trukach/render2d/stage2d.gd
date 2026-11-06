class_name Stage2D
extends Node2D
## Style A: clean vector rooftops at dusk. Draws level, props, the acrobat, shadows and particles.

var world: World
var ppm := 92.0
var t := 0.0
var parts: Array = []
var ghosts: Array = []
var ghost_tick := 0

# character palette ("Тим": cap, red hoodie, navy joggers, white sneakers)
const SKIN := Color("efc19b")
const SKIN_D := Color("cf9472")
const HOOD := Color("e2523b")
const HOOD_D := Color("a33a2c")
const HOOD_STRIPE := Color("f5efe3")
const PANTS := Color("2e3a5a")
const PANTS_D := Color("212942")
const SHOE := Color("f6f2ea")
const SOLE := Color("ff9d3b")
const CAP := Color("1d2236")
const OUTLINE := Color("120e1b")
const RIM := Color("ffb46b")


func px(v: Vector2) -> Vector2:
	return Vector2(v.x * ppm, -v.y * ppm)


func _process(d: float) -> void:
	t += d
	_fx(d)
	queue_redraw()


# ------------------------------------------------------------------ particles

func _fx(d: float) -> void:
	for e in world.fx:
		var name: String = e[0]
		var a := world.actor
		var foot := Vector2(a.c.x, a.feet())
		match name:
			"land", "roll", "skid", "jump":
				_dust(foot, 8 if name != "jump" else 5, 1.0)
			"hard_land":
				_dust(foot, 16, 1.6)
			"crash":
				_dust(foot, 18, 1.8)
			"trick":
				for i in 14:
					var ang := randf() * TAU
					parts.append({"p": a.c + Vector2(0, 0.4), "v": Vector2(cos(ang), sin(ang)) * randf_range(2.0, 4.5), "life": 0.6, "t": 0.0, "r": randf_range(0.025, 0.05), "c": Color("ffd27a"), "g": 0.0})
			"grab", "bar":
				for i in 6:
					parts.append({"p": a.c + Vector2(a.f * 0.2, 1.1), "v": Vector2(randf_range(-1, 1), randf_range(0.2, 1.5)), "life": 0.45, "t": 0.0, "r": 0.03, "c": Color(1, 1, 1, 0.8), "g": 2.0})
	world.fx.clear()
	for p in parts:
		p["t"] += d
		p["v"].y -= p["g"] * d
		p["v"] *= exp(-2.2 * d)
		p["p"] += p["v"] * d
	parts = parts.filter(func(p): return p["t"] < p["life"])


func _dust(at: Vector2, n: int, k: float) -> void:
	for i in n:
		var dir := randf_range(-1.0, 1.0)
		parts.append({"p": at + Vector2(dir * 0.2, 0.05), "v": Vector2(dir * randf_range(1.0, 3.0) * k, randf_range(0.2, 1.2) * k), "life": randf_range(0.45, 0.8), "t": 0.0, "r": randf_range(0.06, 0.13) * k, "c": Color(0.85, 0.75, 0.72, 0.5), "g": -0.3})


# ------------------------------------------------------------------ primitives

func _capsule(a: Vector2, b: Vector2, ra: float, rb: float, seg: int = 8) -> PackedVector2Array:
	var pa := px(a)
	var pb := px(b)
	var d := pb - pa
	var L := d.length()
	ra *= ppm
	rb *= ppm
	if L < 0.5:
		var circ := PackedVector2Array()
		for i in seg * 2:
			circ.append(pa + Vector2.RIGHT.rotated(TAU * i / (seg * 2)) * maxf(ra, rb))
		return circ
	var ang := d.angle()
	var pts := PackedVector2Array()
	for i in seg + 1:
		pts.append(pb + Vector2.RIGHT.rotated(ang - PI * 0.5 + PI * i / seg) * rb)
	for i in seg + 1:
		pts.append(pa + Vector2.RIGHT.rotated(ang + PI * 0.5 + PI * i / seg) * ra)
	return pts


func _limb(a: Vector2, b: Vector2, ra: float, rb: float, col: Color) -> void:
	draw_colored_polygon(_capsule(a, b, ra + 0.022, rb + 0.022), OUTLINE)
	draw_colored_polygon(_capsule(a, b, ra, rb), col)


func _disc(at: Vector2, r: float, col: Color, outline: bool = true) -> void:
	if outline:
		draw_circle(px(at), (r + 0.022) * ppm, OUTLINE)
	draw_circle(px(at), r * ppm, col)


func _shoe(j: Dictionary, sx: String, far: bool) -> void:
	var heel: Vector2 = j["heel" + sx]
	var toe: Vector2 = j["toe" + sx]
	var d := (toe - heel).normalized()
	var f := float(world.actor.f)
	var down := Vector2(d.y, -d.x) * f
	var a := heel + down * 0.035
	var b := toe + down * 0.03 + d * 0.02
	_limb(a, b, 0.05, 0.043, SHOE.darkened(0.25) if far else SHOE)
	var sa := heel + down * 0.075
	var sb := toe + down * 0.07 + d * 0.025
	draw_line(px(sa), px(sb), SOLE.darkened(0.2) if far else SOLE, 0.028 * ppm, true)


# ------------------------------------------------------------------ level

func _draw() -> void:
	if world == null:
		return
	var L := world.level
	var a := world.actor
	_draw_decor(L, true)
	for i in L.solids.size():
		_draw_solid(L.solids[i], L.kinds[i], i)
	_draw_decor(L, false)
	for b in L.bars:
		var p := px(b)
		draw_circle(p, 0.07 * ppm, OUTLINE)
		draw_circle(p, 0.05 * ppm, Color("b9c0cc"))
		draw_circle(p + Vector2(-0.015, -0.015) * ppm, 0.018 * ppm, Color.WHITE)
	# contact shadow
	var foot_x := a.c.x
	var fl := L.floor_below(foot_x, a.feet() + 0.05)
	if a.st == Actor.CRASH:
		var pj: Vector2 = a.joints.get("pelvis", a.c)
		foot_x = pj.x
		fl = L.floor_below(foot_x, pj.y)
	if fl > -INF:
		var hgt := maxf(0.0, (a.feet() if a.st != Actor.CRASH else a.joints["pelvis"].y - 0.3) - fl)
		var k := clampf(1.0 - hgt / 5.0, 0.0, 1.0)
		draw_set_transform(px(Vector2(foot_x, fl)), 0.0, Vector2(1.0, 0.22))
		draw_circle(Vector2.ZERO, (0.32 + 0.18 * k) * ppm, Color(0.05, 0.03, 0.08, 0.38 * k))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# afterimages during fast rotations
	ghost_tick += 1
	if (a.st == Actor.AIR and absf(a.omega) > 7.0) or a.st == Actor.ROLL:
		if ghost_tick % 2 == 0:
			ghosts.append({"j": a.joints.duplicate(), "t": 0.0})
	for g in ghosts:
		g["t"] += 1.0 / 60.0
	ghosts = ghosts.filter(func(g): return g["t"] < 0.14)
	for g in ghosts:
		_ghost(g["j"], 0.16 * (1.0 - g["t"] / 0.14))
	if not a.joints.is_empty():
		_draw_actor(a.joints, a.f)
	for p in parts:
		var k: float = p["t"] / p["life"]
		draw_circle(px(p["p"]), p["r"] * ppm * (1.0 + k * 0.8), Color(p["c"], p["c"].a * (1.0 - k)))


func _draw_solid(r: Rect2, kind: String, idx: int) -> void:
	var tl := px(Vector2(r.position.x, r.end.y))
	var sz := Vector2(r.size.x, r.size.y) * ppm
	var rect := Rect2(tl, sz)
	match kind:
		"crate":
			draw_rect(rect.grow(0.025 * ppm), OUTLINE)
			draw_rect(rect, Color("b8824c"))
			var n := 3
			for i in range(1, n):
				var y := tl.y + sz.y * i / n
				draw_line(Vector2(tl.x, y), Vector2(tl.x + sz.x, y), Color("7a4c27"), 3.0)
			draw_line(tl + Vector2(6, 6), tl + sz - Vector2(6, 6), Color("8e5b31"), 5.0)
			draw_rect(Rect2(tl, sz), Color("5d3a1d"), false, 4.0)
			draw_line(tl + Vector2(0, 2), tl + Vector2(sz.x, 2), Color(RIM, 0.7), 3.0)
		"duct":
			draw_rect(rect.grow(0.025 * ppm), OUTLINE)
			draw_polygon(PackedVector2Array([tl, tl + Vector2(sz.x, 0), tl + sz, tl + Vector2(0, sz.y)]),
				PackedColorArray([Color("8d97a8"), Color("8d97a8"), Color("5b6373"), Color("5b6373")]))
			var x := tl.x + 0.5 * ppm
			while x < tl.x + sz.x - 4:
				draw_line(Vector2(x, tl.y), Vector2(x, tl.y + sz.y), Color("4a5160"), 2.0)
				x += 0.5 * ppm
			draw_rect(Rect2(tl + Vector2(0, sz.y - 0.1 * ppm), Vector2(sz.x, 0.1 * ppm)), Color("3a3f4c"))
			draw_line(tl + Vector2(0, 2), tl + Vector2(sz.x, 2), Color(RIM, 0.8), 3.0)
			# warning stripes on the lower edge
			var sx := tl.x
			var k := 0
			while sx < tl.x + sz.x:
				if k % 2 == 0:
					draw_colored_polygon(PackedVector2Array([Vector2(sx, tl.y + sz.y - 0.1 * ppm), Vector2(minf(sx + 18, tl.x + sz.x), tl.y + sz.y - 0.1 * ppm), Vector2(minf(sx + 10, tl.x + sz.x), tl.y + sz.y), Vector2(maxf(sx - 8, tl.x), tl.y + sz.y)]), Color("f2c14e"))
				sx += 18
				k += 1
		_:
			var top_c := Color("3f3858")
			var bot_c := Color("1a1628")
			if kind == "wall":
				top_c = Color("5a3546")
				bot_c = Color("24141f")
			draw_polygon(PackedVector2Array([tl, tl + Vector2(sz.x, 0), tl + sz, tl + Vector2(0, sz.y)]),
				PackedColorArray([top_c, top_c, bot_c, bot_c]))
			# facade windows for buildings / walls
			if kind != "roof":
				var rng := RandomNumberGenerator.new()
				rng.seed = idx * 977 + 13
				var wy := tl.y + 0.55 * ppm
				while wy < tl.y + sz.y - 0.4 * ppm:
					var wx := tl.x + 0.35 * ppm
					while wx < tl.x + sz.x - 0.6 * ppm:
						var lit := rng.randf() < 0.35
						draw_rect(Rect2(wx, wy, 0.5 * ppm, 0.7 * ppm), Color("ffcf7a") if lit else Color("1b1729"))
						if lit:
							draw_rect(Rect2(wx, wy + 0.35 * ppm, 0.5 * ppm, 0.04 * ppm), Color("e0a855"))
						wx += 0.95 * ppm
					wy += 1.25 * ppm
				if kind == "wall":
					var by := tl.y + 0.3 * ppm
					var row := 0
					while by < tl.y + sz.y:
						var bx := tl.x + (0.25 * ppm if row % 2 == 1 else 0.0)
						while bx < tl.x + sz.x:
							draw_line(Vector2(bx, by - 0.3 * ppm), Vector2(bx, by), Color(0, 0, 0, 0.18), 2.0)
							bx += 0.5 * ppm
						draw_line(Vector2(tl.x, by), Vector2(tl.x + sz.x, by), Color(0, 0, 0, 0.18), 2.0)
						by += 0.3 * ppm
						row += 1
			# roof slab + parapet + rim light
			draw_rect(Rect2(tl, Vector2(sz.x, 0.2 * ppm)), Color("514a6e"))
			draw_rect(Rect2(tl + Vector2(0, 0.2 * ppm), Vector2(sz.x, 0.05 * ppm)), Color(0, 0, 0, 0.25))
			draw_line(tl + Vector2(0, 1.5), tl + Vector2(sz.x, 1.5), Color(RIM, 0.9), 3.0)
			draw_line(tl + Vector2(sz.x - 1.5, 0), tl + Vector2(sz.x - 1.5, sz.y), Color(RIM, 0.35), 3.0)
			draw_line(tl + Vector2(1.0, 0), tl + Vector2(1.0, sz.y), Color(0, 0, 0, 0.35), 2.0)


func _draw_decor(L: Level, back: bool) -> void:
	for d in L.decor:
		var type: String = d["type"]
		var is_back := type in ["rail", "tank", "antenna", "post"]
		if is_back != back:
			continue
		var p: Vector2 = d["pos"]
		var s: Vector2 = d["size"]
		var base := px(p)
		var dark := Color("2a2440")
		match type:
			"rail":
				var x := p.x + 0.2
				while x < p.x + s.x:
					draw_line(px(Vector2(x, p.y)), px(Vector2(x, p.y + 0.95)), Color(dark, 0.9), 3.0)
					x += 1.1
				draw_line(px(Vector2(p.x, p.y + 0.95)), px(Vector2(p.x + s.x, p.y + 0.95)), Color(dark, 0.9), 4.0)
				draw_line(px(Vector2(p.x, p.y + 0.5)), px(Vector2(p.x + s.x, p.y + 0.5)), Color(dark, 0.6), 2.0)
			"ac":
				var r := Rect2(px(Vector2(p.x - s.x * 0.5, p.y + s.y)), s * ppm)
				draw_rect(r.grow(2), OUTLINE)
				draw_rect(r, Color("9aa3b3"))
				draw_rect(Rect2(r.position, Vector2(r.size.x, 5)), Color(RIM, 0.8))
				var fc := r.position + Vector2(r.size.x * 0.62, r.size.y * 0.52)
				var fr := minf(r.size.x, r.size.y) * 0.32
				draw_circle(fc, fr, Color("4b5262"))
				for k in 4:
					var ang := t * 9.0 + k * PI * 0.5
					draw_line(fc, fc + Vector2.RIGHT.rotated(ang) * fr * 0.9, Color("aab2c1"), 3.0)
				for k in 4:
					var yy := r.position.y + r.size.y * (0.25 + k * 0.17)
					draw_line(Vector2(r.position.x + 6, yy), Vector2(r.position.x + r.size.x * 0.32, yy), Color("6c7485"), 2.0)
			"vent":
				var r := Rect2(px(Vector2(p.x - s.x * 0.25, p.y + s.y)), Vector2(s.x * 0.5, s.y) * ppm)
				draw_rect(r.grow(2), OUTLINE)
				draw_rect(r, Color("7d8696"))
				var cap := Rect2(px(Vector2(p.x - s.x * 0.5, p.y + s.y + 0.12)), Vector2(s.x, 0.14) * ppm)
				draw_rect(cap.grow(2), OUTLINE)
				draw_rect(cap, Color("a8b0bd"))
			"tank":
				var legs := [p.x - s.x * 0.38, p.x + s.x * 0.38]
				for lx in legs:
					draw_line(px(Vector2(lx, p.y)), px(Vector2(lx * 0.9 + p.x * 0.1, p.y + s.y * 0.42)), dark, 6.0)
				draw_line(px(Vector2(legs[0], p.y + 0.25)), px(Vector2(legs[1], p.y + 0.9)), Color(dark, 0.8), 3.0)
				draw_line(px(Vector2(legs[1], p.y + 0.25)), px(Vector2(legs[0], p.y + 0.9)), Color(dark, 0.8), 3.0)
				var body := Rect2(px(Vector2(p.x - s.x * 0.5, p.y + s.y * 0.88)), Vector2(s.x, s.y * 0.46) * ppm)
				draw_rect(body.grow(2), OUTLINE)
				draw_rect(body, Color("6e4a3a"))
				for k in 4:
					var yy := body.position.y + body.size.y * (0.2 + k * 0.2)
					draw_line(Vector2(body.position.x, yy), Vector2(body.end.x, yy), Color("4b3127"), 2.0)
				draw_line(Vector2(body.end.x - 3, body.position.y), Vector2(body.end.x - 3, body.end.y), Color(RIM, 0.6), 4.0)
				draw_colored_polygon(PackedVector2Array([px(Vector2(p.x - s.x * 0.55, p.y + s.y * 0.88)), px(Vector2(p.x + s.x * 0.55, p.y + s.y * 0.88)), px(Vector2(p.x, p.y + s.y * 1.08))]), Color("3d2a24"))
			"chimney":
				var r := Rect2(px(Vector2(p.x - s.x * 0.5, p.y + s.y)), s * ppm)
				draw_rect(r.grow(2), OUTLINE)
				draw_rect(r, Color("7b3f3a"))
				var yy := r.position.y + 10
				while yy < r.end.y:
					draw_line(Vector2(r.position.x, yy), Vector2(r.end.x, yy), Color(0, 0, 0, 0.2), 2.0)
					yy += 12
				draw_rect(Rect2(r.position - Vector2(5, 8), Vector2(r.size.x + 10, 10)), Color("4f2a27"))
			"post":
				draw_line(px(p), px(p + Vector2(0, s.y)), Color("1f1b2c"), 9.0)
				draw_line(px(p), px(p + Vector2(0, s.y)), Color("566072"), 5.0)
				draw_rect(Rect2(px(p) - Vector2(16, 6), Vector2(32, 6)), Color("1f1b2c"))
			"antenna":
				draw_line(px(p), px(p + Vector2(0, s.y)), dark, 4.0)
				for k in 3:
					var y := p.y + s.y * (0.45 + k * 0.17)
					draw_line(px(Vector2(p.x - 0.35 + k * 0.08, y)), px(Vector2(p.x + 0.35 - k * 0.08, y)), dark, 3.0)
				draw_circle(px(p + Vector2(0, s.y)), 5, Color(1, 0.2, 0.2, 0.5 + 0.5 * sin(t * 4.0)))
			"skylight":
				var a := px(p + Vector2(-s.x * 0.5, 0))
				var b := px(p + Vector2(s.x * 0.5, 0))
				var c := px(p + Vector2(s.x * 0.2, s.y))
				var e := px(p + Vector2(-s.x * 0.4, s.y))
				draw_colored_polygon(PackedVector2Array([a, b, c, e]), Color("7fb7d6"))
				draw_polyline(PackedVector2Array([a, e, c, b]), OUTLINE, 3.0)
				draw_line(a.lerp(e, 0.5), b.lerp(c, 0.5), Color(1, 1, 1, 0.5), 2.0)
			"flag":
				draw_line(px(p), px(p + Vector2(0, s.y)), OUTLINE, 6.0)
				draw_line(px(p), px(p + Vector2(0, s.y)), Color("d7d9e0"), 3.0)
				var cols := 6
				var rows := 4
				var fw := s.x
				var fh := 0.6
				for cx in cols:
					for cy in rows:
						var u0 := float(cx) / cols
						var u1 := float(cx + 1) / cols
						var w0 := sin(t * 5.0 - u0 * 5.0) * 0.06 * u0
						var w1 := sin(t * 5.0 - u1 * 5.0) * 0.06 * u1
						var y0 := p.y + s.y - fh * cy / rows
						var y1 := p.y + s.y - fh * (cy + 1) / rows
						var col := Color.WHITE if (cx + cy) % 2 == 0 else OUTLINE
						draw_colored_polygon(PackedVector2Array([px(Vector2(p.x + u0 * fw, y0 + w0)), px(Vector2(p.x + u1 * fw, y0 + w1)), px(Vector2(p.x + u1 * fw, y1 + w1)), px(Vector2(p.x + u0 * fw, y1 + w0))]), col)


# ------------------------------------------------------------------ character

func _ghost(j: Dictionary, a: float) -> void:
	var col := Color(1.0, 0.75, 0.45, a)
	for pair in [["pelvis", "neck"], ["pelvis", "knee_l"], ["knee_l", "ankle_l"], ["pelvis", "knee_r"], ["knee_r", "ankle_r"], ["chest", "elbow_l"], ["elbow_l", "wrist_l"], ["chest", "elbow_r"], ["elbow_r", "wrist_r"]]:
		draw_colored_polygon(_capsule(j[pair[0]], j[pair[1]], 0.07, 0.06), col)
	draw_circle(px(j["head"]), 0.13 * ppm, col)


func _draw_actor(j: Dictionary, f: int) -> void:
	var near := "_r" if f > 0 else "_l"
	var far := "_l" if f > 0 else "_r"
	# far leg + far arm (darker)
	_leg(j, far, true)
	_arm(j, far, true)
	# hood behind the head
	var spine: Vector2 = (j["neck"] - j["pelvis"]).normalized()
	var face := spine.rotated(-f * PI * 0.5)
	_disc(j["neck"] - face * 0.07 + spine * 0.02, 0.08, HOOD_D)
	# torso
	_limb(j["pelvis"] + spine * 0.04, j["chest"], 0.118, 0.142, HOOD)
	draw_colored_polygon(_capsule(j["pelvis"] + spine * 0.1 + face * 0.06, j["chest"] - spine * 0.05 + face * 0.08, 0.035, 0.03), Color(1, 1, 1, 0.10))
	# pocket line + zipper
	draw_line(px(j["pelvis"] + spine * 0.12 + face * 0.11), px(j["chest"] + face * 0.13), Color(0, 0, 0, 0.18), 2.5, true)
	# waistband / pelvis
	_disc(j["pelvis"], 0.118, PANTS)
	draw_line(px(j["pelvis"] + spine * 0.1 - face * 0.12), px(j["pelvis"] + spine * 0.1 + face * 0.12), Color("1b2238"), 0.035 * ppm, true)
	# neck + head
	_limb(j["neck"] - spine * 0.03, j["head"] - spine * 0.05, 0.045, 0.045, SKIN_D)
	_head(j, f)
	# near leg + near arm
	_leg(j, near, false)
	_arm(j, near, false)


func _leg(j: Dictionary, sx: String, is_far: bool) -> void:
	var col := PANTS_D if is_far else PANTS
	_limb(j["pelvis"], j["knee" + sx], 0.085, 0.064, col)
	_limb(j["knee" + sx], j["ankle" + sx], 0.064, 0.047, col)
	# cuff
	var sd: Vector2 = (j["ankle" + sx] - j["knee" + sx]).normalized()
	draw_colored_polygon(_capsule(j["ankle" + sx] - sd * 0.06, j["ankle" + sx] - sd * 0.01, 0.05, 0.05), col.darkened(0.25))
	_shoe(j, sx, is_far)


func _arm(j: Dictionary, sx: String, is_far: bool) -> void:
	var col := HOOD_D if is_far else HOOD
	_limb(j["chest"], j["elbow" + sx], 0.057, 0.047, col)
	_limb(j["elbow" + sx], j["wrist" + sx], 0.047, 0.04, col)
	if not is_far:
		var ua: Vector2 = j["elbow" + sx] - j["chest"]
		var n := ua.normalized().orthogonal() * 0.028
		draw_line(px(j["chest"] + ua * 0.15 + n), px(j["elbow" + sx] + n), Color(HOOD_STRIPE, 0.85), 0.018 * ppm, true)
	var hd: Vector2 = (j["hand" + sx] - j["wrist" + sx])
	_limb(j["wrist" + sx] + hd * 0.2, j["hand" + sx] - hd * 0.15, 0.04, 0.036, SKIN_D if is_far else SKIN)


func _head(j: Dictionary, f: int) -> void:
	var hc: Vector2 = j["head"]
	var up: Vector2 = (hc - j["neck"]).normalized()
	var face := up.rotated(-f * PI * 0.5)
	_disc(hc, Rig.HEAD_R, SKIN)
	# ear
	draw_circle(px(hc - face * 0.012 - up * 0.005), 0.026 * ppm, SKIN_D)
	# eye + brow
	draw_circle(px(hc + face * 0.072 + up * 0.012), 0.014 * ppm, OUTLINE)
	draw_line(px(hc + face * 0.05 + up * 0.045), px(hc + face * 0.095 + up * 0.04), Color("3b2a22"), 0.012 * ppm, true)
	# nose
	draw_colored_polygon(PackedVector2Array([px(hc + face * 0.11 + up * 0.0), px(hc + face * 0.138 - up * 0.03), px(hc + face * 0.105 - up * 0.035)]), SKIN_D)
	# cap: dome over the top half + brim to the front
	var dome := PackedVector2Array()
	var base_ang := Vector2(up.x, -up.y).angle()  # screen-space angle of "up"
	for i in 13:
		var ang := base_ang - PI * 0.5 + PI * i / 12.0
		dome.append(px(hc) + Vector2.RIGHT.rotated(ang) * (Rig.HEAD_R + 0.012) * ppm)
	var outline_dome := PackedVector2Array()
	for q in dome:
		outline_dome.append(px(hc) + (q - px(hc)) * 1.12)
	draw_colored_polygon(outline_dome, OUTLINE)
	draw_colored_polygon(dome, CAP)
	var b0 := hc + face * 0.04 + up * 0.035
	var b1 := hc + face * 0.2 + up * 0.02
	draw_line(px(b0), px(b1), OUTLINE, 0.05 * ppm, true)
	draw_line(px(b0), px(b1), CAP.lightened(0.15), 0.03 * ppm, true)
	draw_circle(px(hc + up * 0.08 - face * 0.02), 0.02 * ppm, HOOD)
