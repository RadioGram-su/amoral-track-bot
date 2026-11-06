extends SceneTree
## Headless run of the demo: prints every state change and event.
func _init() -> void:
	var lv := DemoCourse.build()
	var w := World.new(lv, DemoCourse.demo_steps())
	var last := -1
	var t := 0.0
	var crashes := 0
	while t < 75.0:
		w.update(1.0 / 60.0)
		t += 1.0 / 60.0
		var a := w.actor
		if a.st != last:
			print("%6.2f  %-6s x=%6.2f y=%6.2f vx=%5.2f vy=%5.2f rho=%5.2f" % [t, Actor.STATE_NAMES[a.st], a.c.x, a.feet(), a.v.x, a.v.y, a.rho])
			last = a.st
		for e in w.fx:
			if e[0] in ["trick", "crash", "checkpoint", "finish", "grab", "bar", "release", "wall", "wallflip", "vault", "save", "hard_land"]:
				print("        > %s %s" % [e[0], str(e[1])])
			if e[0] == "crash":
				crashes += 1
		w.fx.clear()
		if w.autopilot.done and w.autopilot.done_t > 1.0:
			break
	print("SCORE ", w.score, " crashes ", crashes, " steps ", w.autopilot.i, "/", w.autopilot.steps.size(), " finished ", w.finished)
	quit()
