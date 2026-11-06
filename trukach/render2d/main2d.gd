extends Node2D
## Style A entry point. `godot -- --play` for manual swipe play, default = scripted demo.

const PPM := 112.0

var world: World
var stage: Stage2D
var bg: Bg2D
var hud: Hud
var cam: Camera2D
var cam_m := Vector2.ZERO
var look := 2.6
var demo := true
var end_t := 0.0


func _ready() -> void:
	demo = not ("--play" in OS.get_cmdline_user_args())
	var lv := DemoCourse.build()
	world = World.new(lv, DemoCourse.demo_steps() if demo else [])
	var bl := CanvasLayer.new()
	bl.layer = -10
	add_child(bl)
	bg = Bg2D.new()
	bg.ppm = PPM
	bl.add_child(bg)
	stage = Stage2D.new()
	stage.world = world
	stage.ppm = PPM
	add_child(stage)
	cam = Camera2D.new()
	add_child(cam)
	cam.make_current()
	var hl := CanvasLayer.new()
	hl.layer = 10
	add_child(hl)
	hud = Hud.new()
	hud.world = world
	hud.style_label = "Вариант A · вектор 2D"
	hud.project = func(w: Vector2) -> Vector2: return get_viewport().get_canvas_transform() * stage.px(w)
	hl.add_child(hud)
	if not demo:
		var sw := SwipeInput.new()
		sw.actor = world.actor
		add_child(sw)
	cam_m = _target()
	world.update(0.0)


func _target() -> Vector2:
	var a := world.actor
	var p := a.c
	if a.st == Actor.CRASH and a.joints.has("pelvis"):
		p = a.joints["pelvis"]
	return p + Vector2(look, 0.9)


func _process(delta: float) -> void:
	world.update(delta)
	var a := world.actor
	var want := 2.6 * a.f if a.st != Actor.CRASH else 0.0
	look = lerpf(look, want, 1.0 - exp(-2.5 * delta))
	var tg := _target()
	if a.teleport or (cam_m - tg).length() > 25.0:
		cam_m = tg
	cam_m.x = lerpf(cam_m.x, tg.x, 1.0 - exp(-6.0 * delta))
	cam_m.y = lerpf(cam_m.y, tg.y, 1.0 - exp(-3.2 * delta))
	cam.position = stage.px(cam_m)
	bg.cam_m = cam_m
	if demo and world.autopilot.done:
		end_t += delta
		if end_t > 0.4:
			get_tree().quit()
