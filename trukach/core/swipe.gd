class_name SwipeInput
extends Node
## Swipe recognizer. Fires as soon as the finger travels past the threshold (no need to lift),
## then re-anchors, so one continuous stroke can chain moves: up -> forward -> forward.
## Directions are converted to commands relative to the character's facing.

signal swiped(dir: Vector2i)

var actor: Actor
var threshold_mm := 6.0
var _down := false
var _anchor := Vector2.ZERO
var _last_dir := Vector2i.ZERO
var _cool := 0.0


func _px_threshold() -> float:
	var dpi := DisplayServer.screen_get_dpi()
	if dpi <= 0:
		dpi = 160
	return maxf(24.0, threshold_mm / 25.4 * dpi)


func _process(d: float) -> void:
	_cool = maxf(0.0, _cool - d)


func _input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		if e.index != 0:
			return
		_down = e.pressed
		_anchor = e.position
		_last_dir = Vector2i.ZERO
	elif e is InputEventScreenDrag and _down and e.index == 0:
		var d: Vector2 = e.position - _anchor
		var th := _px_threshold()
		if d.length() < th:
			return
		var dir := Vector2i(signi(int(d.x)), 0) if absf(d.x) > absf(d.y) * 1.15 else Vector2i(0, signi(int(d.y)))
		if absf(d.x) <= absf(d.y) * 1.15 and absf(d.y) <= absf(d.x) * 1.15:
			# diagonal: prefer vertical for jumps/rolls (most common in a chain)
			dir = Vector2i(0, signi(int(d.y)))
		_anchor = e.position
		if dir == _last_dir and _cool > 0.0:
			return
		_last_dir = dir
		_cool = 0.12
		_fire(dir)
	elif e is InputEventKey and e.pressed and not e.echo:
		match e.keycode:
			KEY_RIGHT, KEY_D:
				_fire(Vector2i(1, 0))
			KEY_LEFT, KEY_A:
				_fire(Vector2i(-1, 0))
			KEY_UP, KEY_W, KEY_SPACE:
				_fire(Vector2i(0, -1))
			KEY_DOWN, KEY_S:
				_fire(Vector2i(0, 1))


func _fire(dir: Vector2i) -> void:
	swiped.emit(dir)
	if actor == null:
		return
	if dir.y < 0:
		actor.command(Actor.UP)
	elif dir.y > 0:
		actor.command(Actor.DOWN)
	elif dir.x == actor.f:
		actor.command(Actor.FWD)
	else:
		actor.command(Actor.BACK)
