class_name Level
extends RefCounted
## Level geometry in metres, y up. Solids are axis-aligned boxes (Rect2 with min corner + size).

var solids: Array[Rect2] = []
var kinds: PackedStringArray = []
var bars: Array[Vector2] = []
var ledges: Array = []          # [Vector2 corner, int side]; side +1 = grab while facing +x
var checkpoints: Array[Vector2] = []
var decor: Array = []           # {type, pos, size, ...} purely visual
var spawn := Vector2.ZERO
var finish_x := 1e9
var kill_y := -12.0
var name := ""


func add(x0: float, y0: float, x1: float, y1: float, kind: String = "roof") -> void:
	solids.append(Rect2(Vector2(minf(x0, x1), minf(y0, y1)), Vector2(absf(x1 - x0), absf(y1 - y0))))
	kinds.append(kind)


func add_decor(type: String, pos: Vector2, size: Vector2 = Vector2.ONE, extra: Dictionary = {}) -> void:
	var d := {"type": type, "pos": pos, "size": size}
	d.merge(extra)
	decor.append(d)


func solid_at(pt: Vector2) -> bool:
	for r in solids:
		if r.has_point(pt) and pt.x > r.position.x and pt.y > r.position.y:
			return true
	return false


func box_free(r: Rect2) -> bool:
	for s in solids:
		if s.intersects(r):
			return false
	return true


## Call after all solids are added: finds grabbable ledge corners.
func finalize() -> void:
	ledges.clear()
	const E := 0.06
	for r in solids:
		var top := r.end.y
		for side in [1, -1]:
			var cx := r.position.x if side == 1 else r.end.x
			var corner := Vector2(cx, top)
			var outside := Vector2(cx - side * E, top - E)
			var above_out := Vector2(cx - side * E, top + E)
			var above_in := Vector2(cx + side * E, top + E)
			if solid_at(outside) or solid_at(above_out) or solid_at(above_in):
				continue
			ledges.append([corner, side])


## Highest floor surface directly below a point (or -INF).
func floor_below(x: float, y: float) -> float:
	var best := -INF
	for r in solids:
		if x > r.position.x and x < r.end.x and r.end.y <= y + 0.001:
			best = maxf(best, r.end.y)
	return best


func checkpoint_for(x: float) -> Vector2:
	var cp := spawn
	for c in checkpoints:
		if c.x <= x + 0.01:
			cp = c
	return cp
