class_name Bg2D
extends Node2D
## Screen-space dusk sky with two parallax skylines.

var cam_m := Vector2.ZERO     # camera position in metres
var ppm := 92.0
var far: Array = []
var mid: Array = []
var stars: Array = []
var t := 0.0


func _ready() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7741
	var x := 0.0
	while x < 5200.0:
		var w := rng.randf_range(70, 170)
		far.append({"x": x, "w": w, "h": rng.randf_range(90, 330), "seed": rng.randi()})
		x += w + rng.randf_range(4, 26)
	x = 0.0
	while x < 6400.0:
		var w := rng.randf_range(110, 260)
		var top := rng.randi() % 5
		mid.append({"x": x, "w": w, "h": rng.randf_range(160, 470), "top": top, "seed": rng.randi()})
		x += w + rng.randf_range(10, 60)
	for i in 90:
		stars.append(Vector3(rng.randf(), rng.randf() * 0.42, rng.randf_range(0.6, 1.8)))


func _process(d: float) -> void:
	t += d
	queue_redraw()


func _draw() -> void:
	var vp := get_viewport_rect().size
	var s := vp.y / 1080.0
	var hy := vp.y * (0.70 + clampf(cam_m.y * 0.004, -0.04, 0.04))
	# sky gradient
	var cols := [Color("101330"), Color("2d2452"), Color("7a3a68"), Color("e0705f"), Color("f7b267")]
	var ys := [0.0, hy * 0.38, hy * 0.7, hy * 0.92, hy]
	for i in cols.size() - 1:
		draw_polygon(PackedVector2Array([Vector2(0, ys[i]), Vector2(vp.x, ys[i]), Vector2(vp.x, ys[i + 1]), Vector2(0, ys[i + 1])]),
			PackedColorArray([cols[i], cols[i], cols[i + 1], cols[i + 1]]))
	draw_rect(Rect2(0, hy, vp.x, vp.y - hy), Color("f2a35e"))
	for st in stars:
		draw_circle(Vector2(st.x * vp.x, st.y * vp.y), st.z * s, Color(1, 0.95, 0.9, 0.35 + 0.25 * sin(st.x * 90.0 + t)))
	# sun with glow
	var sun := Vector2(vp.x * 0.74 - cam_m.x * 0.6 * s, hy - 70 * s)
	sun.x = fposmod(sun.x, vp.x * 1.6) - vp.x * 0.1
	for k in 6:
		draw_circle(sun, (110 + k * 60) * s, Color(1.0, 0.75, 0.45, 0.055))
	draw_circle(sun, 92 * s, Color("ffe2b0"))
	# far skyline
	_skyline(far, 0.10, hy + 12 * s, s, Color("3a2650"), Color(1.0, 0.82, 0.5, 0.42), vp, false)
	# haze band
	draw_polygon(PackedVector2Array([Vector2(0, hy - 140 * s), Vector2(vp.x, hy - 140 * s), Vector2(vp.x, hy + 40 * s), Vector2(0, hy + 40 * s)]),
		PackedColorArray([Color(0.96, 0.6, 0.4, 0.0), Color(0.96, 0.6, 0.4, 0.0), Color(0.96, 0.6, 0.4, 0.28), Color(0.96, 0.6, 0.4, 0.28)]))
	# mid skyline
	_skyline(mid, 0.28, hy + 70 * s, s, Color("22183a"), Color(1.0, 0.8, 0.45, 0.55), vp, true)


func _skyline(arr: Array, factor: float, base: float, s: float, col: Color, win: Color, vp: Vector2, details: bool) -> void:
	var total: float = arr[-1]["x"] + arr[-1]["w"] + 40.0
	var off := cam_m.x * ppm * factor * s
	for b in arr:
		var x := fposmod(b["x"] * s - off, total * s) - 200.0 * s
		if x > vp.x + 50 or x + b["w"] * s < -50:
			continue
		var w: float = b["w"] * s
		var h: float = b["h"] * s
		var top := base - h
		draw_rect(Rect2(x, top, w, vp.y - top), col)
		var rng := RandomNumberGenerator.new()
		rng.seed = b["seed"]
		var ww := 9.0 * s
		var wh := 13.0 * s
		var yy := top + 16 * s
		while yy < base - 10 * s:
			var xx := x + 10 * s
			while xx < x + w - 14 * s:
				if rng.randf() < 0.16:
					draw_rect(Rect2(xx, yy, ww, wh), Color(win, win.a * rng.randf_range(0.4, 1.0)))
				xx += 19 * s
			yy += 27 * s
		if details:
			match int(b["top"]):
				0:  # water tower
					var cx := x + w * 0.6
					draw_rect(Rect2(cx - 22 * s, top - 46 * s, 44 * s, 34 * s), col)
					draw_colored_polygon(PackedVector2Array([Vector2(cx - 26 * s, top - 46 * s), Vector2(cx + 26 * s, top - 46 * s), Vector2(cx, top - 66 * s)]), col)
					draw_line(Vector2(cx - 16 * s, top - 12 * s), Vector2(cx - 20 * s, top), col, 4 * s)
					draw_line(Vector2(cx + 16 * s, top - 12 * s), Vector2(cx + 20 * s, top), col, 4 * s)
				1:  # antenna
					var cx := x + w * 0.3
					draw_line(Vector2(cx, top), Vector2(cx, top - 90 * s), col, 3 * s)
					draw_circle(Vector2(cx, top - 92 * s), 4 * s, Color(1, 0.25, 0.2, 0.5 + 0.5 * sin(t * 4.0 + x)))
				2:  # stepped top
					draw_rect(Rect2(x + w * 0.2, top - 30 * s, w * 0.6, 30 * s), col)
