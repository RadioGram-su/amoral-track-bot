class_name Autopilot
extends RefCounted
## Scripted demo player: issues exactly the swipes a human would, at the right moments.

var world: World
var steps: Array
var i := 0
var since := 0.0
var done := false
var done_t := 0.0
var crashed := false


func _init(w: World, s: Array) -> void:
	world = w
	steps = s


func tick(dt: float) -> void:
	since += dt
	var a := world.actor
	if a.st == Actor.CRASH:
		crashed = true
	if i >= steps.size():
		done = true
		done_t += dt
		return
	var s: Dictionary = steps[i]
	if not _ready(s, a):
		return
	if s.has("caption"):
		world.set_caption(s["caption"], s.get("glyphs", []))
	if s.has("cmd"):
		a.command(int(s["cmd"]))
	i += 1
	since = 0.0


func _ready(s: Dictionary, a: Actor) -> bool:
	var v = s.get("v", 0.0)
	match s.get("when", "wait"):
		"wait":
			return since >= float(v)
		"x":
			return a.c.x >= float(v) and (not s.get("ground", false) or a.grounded())
		"state":
			return a.st == int(v) and a.t_state >= float(s.get("after", 0.0))
		"air_t":
			return a.st == Actor.AIR and a.air_t >= float(v)
		"falling_h":
			if a.st != Actor.AIR or a.v.y >= 0.0:
				return false
			var fl := world.level.floor_below(a.c.x, a.feet())
			return a.feet() - fl < float(v)
		"swing_bottom":
			return a.st == Actor.SWING and absf(a.phi) < 0.35 and a.dphi * float(v) > 0.6
		"swing_release":
			return a.st == Actor.SWING and a.dphi > 0.5 and a.phi >= float(v[0]) and a.phi <= float(v[1])
		"respawned":
			return crashed and a.st == Actor.IDLE and a.t_state >= float(v)
	return false
