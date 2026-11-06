class_name Hud
extends Control
## Shared HUD: score, combo, trick popups, demo captions with animated swipe glyphs, banners.

var world: World
var project: Callable          # world position (Vector2, metres) -> screen pixels
var style_label := ""
var font: FontVariation
var font_bold: FontVariation
var accent := Color("ffb347")
var ink := Color(0.06, 0.05, 0.1, 0.78)
var paper := Color("f6f1e7")


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var base := FontFile.new()
	base.load_dynamic_font("res://assets/fonts/Rubik.ttf")
	font = FontVariation.new()
	font.base_font = base
	font.variation_opentype = {"wght": 500}
	font_bold = FontVariation.new()
	font_bold.base_font = base
	font_bold.variation_opentype = {"wght": 800}


func _process(_d: float) -> void:
	queue_redraw()


func _glyph(center: Vector2, kind: String, r: float, t: float) -> void:
	draw_circle(center, r, Color(1, 1, 1, 0.12))
	draw_arc(center, r, 0.0, TAU, 40, Color(1, 1, 1, 0.55), 2.0, true)
	var dir := Vector2.RIGHT
	match kind:
		"B":
			dir = Vector2.LEFT
		"U":
			dir = Vector2.UP
		"D":
			dir = Vector2.DOWN
	var a := center - dir * r * 0.5
	var b := center + dir * r * 0.5
	draw_line(a, b, paper, 4.0, true)
	var side := dir.orthogonal() * r * 0.28
	draw_colored_polygon(PackedVector2Array([b + dir * r * 0.12, b - dir * r * 0.3 + side, b - dir * r * 0.3 - side]), paper)
	# finger dot sliding along the stroke
	var k := fposmod(t * 1.6, 1.0)
	draw_circle(a.lerp(b, k), r * 0.16, Color(accent, 1.0 - k * 0.6))


func _draw() -> void:
	if world == null:
		return
	var vp := get_viewport_rect().size
	var s := vp.y / 1080.0
	# score
	draw_string(font, Vector2(48, 78) * s, "ОЧКИ", HORIZONTAL_ALIGNMENT_LEFT, -1, int(24 * s), Color(paper, 0.7))
	draw_string(font_bold, Vector2(48, 132) * s, str(world.score), HORIZONTAL_ALIGNMENT_LEFT, -1, int(56 * s), paper)
	if world.combo > 1:
		draw_string(font_bold, Vector2(52, 182) * s, "КОМБО ×" + str(world.combo), HORIZONTAL_ALIGNMENT_LEFT, -1, int(30 * s), accent)
	if style_label != "":
		draw_string(font, Vector2(vp.x - 48 * s - 520 * s, 70 * s), style_label, HORIZONTAL_ALIGNMENT_RIGHT, 520 * s, int(24 * s), Color(paper, 0.75))
	# trick popups near the character
	for p in world.popups:
		var t: float = p["t"]
		var a := clampf(1.0 - (t - 1.2) / 0.7, 0.0, 1.0) * clampf(t / 0.12, 0.0, 1.0)
		var pos: Vector2 = project.call(p["pos"] + Vector2(0.0, 2.3 + t * 0.5))
		var title: String = p["name"]
		var pts := "+" + str(p["pts"]) + ("  ×" + str(p["combo"]) if int(p["combo"]) > 1 else "")
		var fs := int(34 * s)
		var w := font_bold.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		draw_string_outline(font_bold, pos + Vector2(-w * 0.5, 0), title, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, int(8 * s), Color(ink, a))
		draw_string(font_bold, pos + Vector2(-w * 0.5, 0), title, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(paper, a))
		var w2 := font_bold.get_string_size(pts, HORIZONTAL_ALIGNMENT_LEFT, -1, int(28 * s)).x
		draw_string_outline(font_bold, pos + Vector2(-w2 * 0.5, 36 * s), pts, HORIZONTAL_ALIGNMENT_LEFT, -1, int(28 * s), int(7 * s), Color(ink, a))
		draw_string(font_bold, pos + Vector2(-w2 * 0.5, 36 * s), pts, HORIZONTAL_ALIGNMENT_LEFT, -1, int(28 * s), Color(accent, a))
	# banner
	if world.banner != "" and world.banner_t < 2.4:
		var a := clampf(world.banner_t / 0.15, 0.0, 1.0) * clampf((2.4 - world.banner_t) / 0.4, 0.0, 1.0)
		var fs := int(54 * s)
		var w := font_bold.get_string_size(world.banner, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		var pos := Vector2((vp.x - w) * 0.5, 210 * s)
		draw_string_outline(font_bold, pos, world.banner, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, int(10 * s), Color(ink, a))
		draw_string(font_bold, pos, world.banner, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(accent, a))
	# demo caption with swipe glyphs
	if world.caption != "":
		var a := clampf(world.caption_t / 0.2, 0.0, 1.0)
		var fs := int(36 * s)
		var tw := font.get_string_size(world.caption, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		var gr := 30.0 * s
		var gw := world.glyphs.size() * (gr * 2.0 + 14.0 * s)
		var total := tw + gw + (24.0 * s if gw > 0 else 0.0)
		var h := 96.0 * s
		var rect := Rect2(Vector2((vp.x - total) * 0.5 - 36 * s, vp.y - h - 44 * s), Vector2(total + 72 * s, h))
		draw_style_box(_panel(a), rect)
		var x := rect.position.x + 36 * s
		var cy := rect.position.y + h * 0.5
		for i in world.glyphs.size():
			_glyph(Vector2(x + gr, cy), world.glyphs[i], gr, world.caption_t - i * 0.25)
			x += gr * 2.0 + 14.0 * s
		if gw > 0:
			x += 10.0 * s
		draw_string(font, Vector2(x, cy + fs * 0.36), world.caption, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(paper, a))


func _panel(a: float) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(ink, 0.72 * a)
	sb.set_corner_radius_all(22)
	sb.border_color = Color(1, 1, 1, 0.14 * a)
	sb.set_border_width_all(2)
	sb.anti_aliasing = true
	return sb
