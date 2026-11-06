class_name World
extends RefCounted
## Glue: level + actor + scoring/combo + demo autopilot. Fixed 120 Hz simulation.

const DT := 1.0 / 120.0

var level: Level
var actor: Actor
var autopilot: Autopilot
var acc := 0.0
var time := 0.0
var score := 0
var combo := 0
var combo_t := 0.0
var idle_t := 0.0
var popups: Array = []      # {name, pts, combo, t, pos}
var caption := ""
var glyphs: Array = []
var caption_t := 0.0
var banner := ""
var banner_t := 99.0
var finished := false
var fx: Array = []          # events for renderers (sound / particles): [name, data, pos]


func _init(lv: Level, steps: Array = []) -> void:
	level = lv
	actor = Actor.new(lv)
	if not steps.is_empty():
		autopilot = Autopilot.new(self, steps)


func set_caption(text: String, g: Array) -> void:
	caption = text
	glyphs = g
	caption_t = 0.0


func update(dt: float) -> void:
	acc += dt
	while acc >= DT:
		acc -= DT
		if autopilot:
			autopilot.tick(DT)
		actor.step(DT)
		time += DT
		_events()
		combo_t -= DT
		if actor.st == Actor.IDLE and not actor.running:
			idle_t += DT
		else:
			idle_t = 0.0
		if combo_t <= 0.0 or idle_t > 0.6:
			combo = 0
		if not finished and actor.grounded() and actor.c.x >= level.finish_x:
			finished = true
			banner = "ФИНИШ · " + str(score)
			banner_t = 0.0
			fx.append(["finish", {}, actor.c])
	actor.update_visual(dt)
	caption_t += dt
	banner_t += dt
	for p in popups:
		p["t"] += dt
	popups = popups.filter(func(p): return p["t"] < 1.9)


func _events() -> void:
	for e in actor.events:
		var name: String = e[0]
		var data: Dictionary = e[1]
		fx.append([name, data, actor.c])
		match name:
			"trick":
				combo = combo + 1 if combo_t > 0.0 else 1
				combo_t = 2.2
				var pts := int(data["pts"]) * combo
				score += pts
				popups.append({"name": data["name"], "pts": pts, "combo": combo, "t": 0.0, "pos": actor.c})
			"crash":
				combo = 0
				combo_t = 0.0
				banner = data["reason"]
				banner_t = 0.0
	actor.events.clear()
