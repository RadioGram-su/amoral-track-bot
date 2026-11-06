class_name Actor
extends RefCounted
## Acrobat controller: deterministic fixed-step physics + state machine + procedural visuals.
## Coordinates: metres, y up. `c` is the centre of the collision box (width W, height h).

enum { IDLE, RUN, SKID, AIR, LAND, ROLL, HANG, CLIMB, VAULT, WALL, SWING, CRASH }
const STATE_NAMES := ["idle", "run", "skid", "air", "land", "roll", "hang", "climb", "vault", "wall", "swing", "crash"]
const FWD := 0
const BACK := 1
const UP := 2
const DOWN := 3

const G := 22.0
const MAX_FALL := 26.0
const RUN_SPEED := 7.0
const ACCEL := 9.0
const DECEL := 16.0
const JUMP_RUN := 7.6
const JUMP_STAND := 7.8
const W := 0.46
const H_STAND := 1.76
const H_TUCK := 1.15
const H_ROLL := 0.95
const STEP_H := 0.32
const BONK_SPEED := 4.5
const COYOTE := 0.09
const BUFFER_T := 0.16
const OMEGA_TUCK := 15.0
const SPIN_ACC := 100.0
const OPEN_DECEL := 70.0
const LAND_TOL := 0.55
const HARD_LAND := 12.5
const CRASH_LAND := 16.5
const ROLL_WINDOW := 0.5
const ROLL_T := 0.62
const REACH := 1.08          # hands-overhead height above box centre
const HANG_DROP := 1.02
const CLIMB_T := 0.78
const VAULT_RANGE := 1.45
const WALL_HOLD := 0.42
const WALL_STEP_V := 6.2
const BAR_L := 1.12
const BAR_GRAB := 0.52
const BAR_CATCH := 0.65
const PUMP := 1.15
const CRASH_T := 1.9

var level: Level
var events: Array = []

var st := IDLE
var t_state := 0.0
var f := 1
var c := Vector2.ZERO
var h := H_STAND
var v := Vector2.ZERO
var running := false
var ground_y := 0.0
var coyote := 0.0
var air_t := 0.0
var air_kind := "fall"
var rho := 0.0
var omega := 0.0
var rho_target := 0.0
var tuck := 0.0
var roll_intent := 0.0
var roll_rho := 0.0
var roll_end := TAU
var roll_speed := 5.0
var land_hard := false
var land_dur := 0.15
var land_depth := 0.5
var grab_cd := 0.0
var wall_cd := 0.0
var wall_steps := 0
var wall_face := 0.0
var ledge := Vector2.ZERO
var climb_dest := Vector2.ZERO
var s_from := Vector2.ZERO
var vault_end := Vector2.ZERO
var vault_rect := Rect2()
var vault_t := 0.4
var vault_speed := 6.0
var vault_pending := false
var bar := Vector2.ZERO
var phi := 0.0
var dphi := 0.0
var buf_cmd := -1
var buf_t := 0.0
var checkpoint := Vector2.ZERO
var time := 0.0
var hit_x := -1
var hit_y := -1
var on_floor := false
var ragdoll: Ragdoll

# visuals
var pose := PackedFloat32Array()
var joints := {}
var prev_joints := {}
var run_u := 0.0
var lean := 0.0
var last_vx := 0.0
var vis_dirty := false
var teleport := true
var off_pos := Vector2.ZERO
var off_rot := 0.0
var last_pelvis := Vector2.ZERO
var last_rot := 0.0
var vis_rot := 0.0          # world rotation of the rig (math CCW), for renderers


func _init(lv: Level) -> void:
	level = lv
	ragdoll = Ragdoll.new(lv)
	pose = Poses.p(Poses.STAND)
	checkpoint = lv.spawn
	respawn(lv.spawn, false)


func _emit(name: String, data: Dictionary = {}) -> void:
	events.append([name, data])


func _set_state(s: int) -> void:
	st = s
	t_state = 0.0
	vis_dirty = true


func feet() -> float:
	return c.y - h * 0.5


func box(cc: Vector2 = c, hh: float = h) -> Rect2:
	return Rect2(Vector2(cc.x - W * 0.5, cc.y - hh * 0.5), Vector2(W, hh))


func grounded() -> bool:
	return st in [IDLE, RUN, SKID, LAND, ROLL]


func respawn(at: Vector2, ev: bool = true) -> void:
	c = Vector2(at.x, at.y + H_STAND * 0.5 + 0.0005)
	h = H_STAND
	v = Vector2.ZERO
	f = 1
	running = false
	rho = 0.0
	omega = 0.0
	rho_target = 0.0
	roll_rho = 0.0
	tuck = 0.0
	ground_y = at.y
	_set_state(IDLE)
	teleport = true
	if ev:
		_emit("respawn")


# ---------------------------------------------------------------- collision

func _set_height(nh: float, anchor_feet: bool) -> bool:
	if absf(nh - h) < 0.0001:
		return true
	var nc := c
	if anchor_feet:
		nc.y = feet() + nh * 0.5
	if nh > h and not level.box_free(box(nc, nh).grow(-0.003)):
		return false
	c = nc
	h = nh
	return true


func _move(d: Vector2, can_step: bool) -> void:
	hit_x = -1
	hit_y = -1
	on_floor = false
	var half := Vector2(W * 0.5, h * 0.5)
	if d.x != 0.0:
		c.x += d.x
		for i in level.solids.size():
			var r: Rect2 = level.solids[i]
			if not box().intersects(r):
				continue
			var step := r.end.y - feet()
			if can_step and step > 0.0 and step <= STEP_H:
				var raised := Vector2(c.x, r.end.y + half.y + 0.001)
				if level.box_free(box(raised).grow(-0.003)):
					c = raised
					continue
			if d.x > 0.0:
				c.x = r.position.x - half.x - 0.0005
			else:
				c.x = r.end.x + half.x + 0.0005
			hit_x = i
	if d.y != 0.0:
		c.y += d.y
		for i in level.solids.size():
			var r: Rect2 = level.solids[i]
			if not box().intersects(r):
				continue
			if d.y < 0.0:
				c.y = r.end.y + half.y + 0.0005
				on_floor = true
				ground_y = r.end.y
			else:
				c.y = r.position.y - half.y - 0.0005
			hit_y = i


# ---------------------------------------------------------------- commands

func command(cmd: int) -> void:
	buf_cmd = cmd
	buf_t = BUFFER_T
	_consume_buffer()


func _consume_buffer() -> void:
	if buf_t > 0.0 and buf_cmd >= 0 and _handle(buf_cmd):
		buf_t = 0.0
		buf_cmd = -1


func _handle(cmd: int) -> bool:
	match st:
		IDLE, RUN, LAND:
			if st == LAND and land_hard:
				return false
			match cmd:
				FWD:
					running = true
					if st == IDLE:
						_set_state(RUN)
					return true
				BACK:
					if absf(v.x) > 1.2:
						_set_state(SKID)
						_emit("skid")
					else:
						f = -f
						running = false
						v.x = 0.0
						_set_state(IDLE)
						_emit("turn")
					return true
				UP:
					if _find_vault():
						return true
					if absf(v.x) > 3.0:
						_jump(JUMP_RUN)
					else:
						_jump(JUMP_STAND)
					return true
				DOWN:
					_start_roll(false, 0.0)
					return true
		SKID:
			if cmd == UP:
				_jump(JUMP_STAND)
				return true
			return cmd == BACK
		AIR:
			match cmd:
				FWD:
					if omega > -2.5:
						rho_target += TAU
						_emit("flip_cmd", {"dir": 1})
					return true
				BACK:
					if omega < 2.5:
						rho_target -= TAU
						_emit("flip_cmd", {"dir": -1})
					return true
				DOWN:
					roll_intent = ROLL_WINDOW
					return true
				UP:
					if coyote > 0.0 and air_kind == "fall":
						_jump(JUMP_RUN if absf(v.x) > 3.0 else JUMP_STAND)
					return true
		HANG:
			match cmd:
				UP, FWD:
					if _can_climb():
						s_from = c
						_set_state(CLIMB)
						_emit("climb")
						return true
					return false
				DOWN:
					grab_cd = 0.35
					_enter_air("fall", true)
					return true
				BACK:
					f = -f
					v = Vector2(f * 4.2, 6.6)
					grab_cd = 0.3
					_enter_air("kick", true)
					_emit("kick")
					return true
		WALL:
			match cmd:
				UP:
					if wall_steps < 2:
						wall_steps += 1
						v.y = WALL_STEP_V
						t_state = 0.0
						_emit("wallstep")
						if wall_steps == 1:
							_emit("trick", {"name": "Забег по стене", "pts": 100})
					return true
				BACK:
					v = Vector2(-f * 3.6, 7.2)
					running = false
					rho = 0.0
					omega = -4.0
					rho_target = -TAU
					wall_cd = 0.5
					grab_cd = 0.3
					_enter_air("wall", false)
					_emit("wallflip")
					return true
				DOWN:
					wall_cd = 0.45
					_enter_air("fall", true)
					return true
				FWD:
					return true
		SWING:
			match cmd:
				FWD:
					if dphi > 0.25 and absf(phi) < 0.8:
						dphi = minf(dphi + PUMP, 7.5)
						_emit("pump")
					return true
				BACK:
					if dphi < -0.25 and absf(phi) < 0.8:
						dphi = maxf(dphi - PUMP, -7.5)
						_emit("pump")
					return true
				UP, DOWN:
					_release_bar(cmd == UP)
					return true
		CRASH:
			return true
	return false


func _jump(vy: float) -> void:
	v.y = vy
	_enter_air("jump", true)
	_emit("jump")


func _enter_air(kind: String, reset_spin: bool) -> void:
	air_kind = kind
	air_t = 0.0
	if reset_spin:
		rho = 0.0
		omega = 0.0
		rho_target = 0.0
	_set_state(AIR)


# ---------------------------------------------------------------- simulation

func step(dt: float) -> void:
	time += dt
	t_state += dt
	grab_cd = maxf(0.0, grab_cd - dt)
	wall_cd = maxf(0.0, wall_cd - dt)
	roll_intent = maxf(0.0, roll_intent - dt)
	buf_t = maxf(0.0, buf_t - dt)
	match st:
		IDLE, RUN, SKID, LAND:
			_ground(dt)
		AIR:
			_air(dt)
		ROLL:
			_roll(dt)
		HANG:
			v = Vector2.ZERO
		CLIMB:
			_climb(dt)
		VAULT:
			_vault(dt)
		WALL:
			_wall(dt)
		SWING:
			_swing(dt)
		CRASH:
			ragdoll.step(dt)
			if t_state >= CRASH_T:
				respawn(checkpoint)
	if st != CRASH and grounded():
		for cp in level.checkpoints:
			if cp.x > checkpoint.x and c.x >= cp.x and absf(feet() - cp.y) < 0.3:
				checkpoint = cp
				_emit("checkpoint")
	_consume_buffer()


func _ground(dt: float) -> void:
	var target := 0.0
	var acc := DECEL
	match st:
		RUN:
			target = RUN_SPEED * f
			if signf(v.x) != -f and absf(v.x) < RUN_SPEED:
				acc = ACCEL
		SKID:
			acc = 22.0
		LAND:
			if land_hard:
				acc = 18.0
			else:
				target = RUN_SPEED * f if running else 0.0
				acc = 4.0 if running else 10.0
	v.x = move_toward(v.x, target, acc * dt)
	v.y -= G * dt
	_move(v * dt, true)
	if hit_x >= 0:
		if st == RUN and absf(v.x) > BONK_SPEED and signf(v.x) == f:
			_crash(Vector2(-f * 2.4, 1.6), "Удар о препятствие")
			return
		v.x = 0.0
		if st == RUN:
			running = false
			_set_state(IDLE)
	if on_floor:
		v.y = 0.0
	else:
		coyote = COYOTE
		_enter_air("fall", true)
		return
	match st:
		LAND:
			if t_state >= land_dur:
				_set_state(RUN if running else IDLE)
		SKID:
			if absf(v.x) < 0.25:
				v.x = 0.0
				f = -f
				running = false
				_set_state(IDLE)
				_emit("turn")
		RUN:
			if not running:
				_set_state(IDLE)
		IDLE:
			if running:
				_set_state(RUN)
	if st == RUN and vault_pending:
		_find_vault()


func _spin(dt: float) -> void:
	var rem := rho_target - rho
	if absf(rem) < 0.004 and absf(omega) < 0.8:
		rho = rho_target
		omega = move_toward(omega, 0.0, SPIN_ACC * dt)
	else:
		var des := signf(rem) * minf(OMEGA_TUCK, sqrt(2.0 * OPEN_DECEL * absf(rem)))
		omega = move_toward(omega, des, SPIN_ACC * dt)
		var before := signf(rho_target - rho)
		rho += omega * dt
		if signf(rho_target - rho) != before and before != 0.0:
			rho = rho_target
			omega = 0.0
	tuck = clampf(absf(omega) / OMEGA_TUCK * 1.15, 0.0, 1.0)


func _air(dt: float) -> void:
	air_t += dt
	coyote = maxf(0.0, coyote - dt)
	var vy0 := v.y
	var vx0 := v.x
	v.y = maxf(v.y - G * dt, -MAX_FALL)
	_spin(dt)
	_set_height(lerpf(H_STAND, H_TUCK, tuck), false)
	_move(v * dt, false)
	if hit_x >= 0:
		if _try_ledge():
			return
		if _try_wall(vx0):
			return
		v.x = 0.0
	if hit_y >= 0:
		if on_floor:
			_land(-vy0)
			return
		v.y = minf(v.y, 0.0)
	if _try_ledge() or _try_bar():
		return
	if c.y < level.kill_y:
		_crash(Vector2.ZERO, "Сорвался вниз")


func _stand_on_floor() -> void:
	c.y = ground_y + h * 0.5 + 0.0005
	if not _set_height(H_STAND, true):
		_set_height(H_ROLL, true)


func _land(imp: float) -> void:
	var turns := roundf(rho / TAU)
	var e := rho - turns * TAU
	var spd := absf(v.x)
	var forward := signf(v.x) == float(f) or spd < 1.0
	var kind := air_kind
	rho = 0.0
	omega = 0.0
	rho_target = 0.0
	if absf(e) <= LAND_TOL:
		if roll_intent > 0.0 and (spd > 1.2 or imp > 9.0):
			_award_flips(int(turns), kind)
			_start_roll(true, imp)
			return
		if imp > CRASH_LAND:
			_crash(Vector2(v.x * 0.3, 0.4), "Слишком высоко без кувырка")
			return
		_award_flips(int(turns), kind)
		_stand_on_floor()
		if imp > HARD_LAND:
			land_hard = true
			land_dur = 0.55
			land_depth = 1.0
			v.x *= 0.3
			_emit("hard_land")
		else:
			land_hard = false
			land_dur = clampf(imp / 45.0, 0.07, 0.2)
			land_depth = clampf(imp / 13.0, 0.25, 0.85)
			_emit("land", {"imp": imp})
		_set_state(LAND)
	elif e > LAND_TOL and e < 1.75 and forward and imp < CRASH_LAND + 3.0:
		_start_roll(true, imp)
		_emit("save")
	else:
		_crash(Vector2(v.x * 0.4, 0.0), "Неудачное приземление")


func _award_flips(n: int, kind: String) -> void:
	if n == 0:
		if kind == "bar":
			_emit("trick", {"name": "Соскок", "pts": 150})
		return
	var names_f := ["", "Сальто вперёд", "Двойное сальто", "Тройное сальто"]
	var names_b := ["", "Сальто назад", "Двойное назад", "Тройное назад"]
	var k := mini(absi(n), 3)
	var name: String = names_f[k] if n > 0 else names_b[k]
	var base := 150 if n > 0 else 200
	var mult: float = [0.0, 1.0, 2.5, 4.5][k]
	var pts := int(base * mult)
	if kind == "bar":
		name = "Соскок · " + name.to_lower()
		pts += 150
	elif kind == "wall":
		name = "Сальто от стены"
		pts += 100
	_emit("trick", {"name": name, "pts": pts})


func _start_roll(from_air: bool, imp: float) -> void:
	roll_speed = clampf(maxf(absf(v.x), 4.2), 4.2, 7.6)
	v.x = f * roll_speed
	v.y = 0.0
	h = H_ROLL
	c.y = ground_y + h * 0.5 + 0.0005
	roll_rho = 0.0
	roll_end = TAU
	_set_state(ROLL)
	if from_air:
		_emit("trick", {"name": "Кувырок с высоты" if imp > 9.5 else "Кувырок", "pts": 100 if imp > 9.5 else 50})
	else:
		_emit("trick", {"name": "Кувырок", "pts": 50})
	_emit("roll")


func _roll(dt: float) -> void:
	var w := TAU / ROLL_T * clampf(0.35 + t_state / 0.12, 0.0, 1.15)
	roll_rho += w * dt
	v.x = move_toward(v.x, f * roll_speed * 0.85, 3.0 * dt)
	v.y -= G * dt
	_move(v * dt, true)
	if hit_x >= 0:
		v.x = 0.0
	if on_floor:
		v.y = 0.0
	else:
		rho = roll_rho
		omega = w
		rho_target = ceilf(roll_rho / TAU - 0.05) * TAU
		_set_height(H_TUCK, false)
		_enter_air("fall", false)
		return
	if roll_rho >= roll_end:
		if _set_height(H_STAND, true):
			roll_rho = 0.0
			_set_state(RUN if running else IDLE)
		else:
			roll_end += TAU


func _try_ledge() -> bool:
	if grab_cd > 0.0 or absf(wrapf(rho, -PI, PI)) > 0.7 or v.y > 3.2:
		return false
	var reach := Vector2(c.x + f * 0.18, c.y + REACH)
	for L in level.ledges:
		var corner: Vector2 = L[0]
		if int(L[1]) != f:
			continue
		var dx := (corner.x - reach.x) * f
		var dy := corner.y - reach.y
		if dx < -0.25 or dx > 0.42 or dy < -0.42 or dy > 0.3:
			continue
		var hc := Vector2(corner.x - f * (W * 0.5 + 0.03), corner.y - HANG_DROP)
		if not level.box_free(box(hc, H_STAND).grow(-0.01)):
			continue
		c = hc
		h = H_STAND
		v = Vector2.ZERO
		rho = 0.0
		omega = 0.0
		rho_target = 0.0
		ledge = corner
		grab_cd = 0.25
		_set_state(HANG)
		_emit("grab")
		return true
	return false


func _can_climb() -> bool:
	climb_dest = Vector2(ledge.x + f * 0.42, ledge.y + H_STAND * 0.5 + 0.0005)
	return level.box_free(box(climb_dest, H_STAND).grow(-0.01))


func _climb(_dt: float) -> void:
	var k := clampf(t_state / CLIMB_T, 0.0, 1.0)
	var p1 := Vector2(ledge.x - f * 0.22, ledge.y - 0.32)
	var p2 := Vector2(ledge.x + f * 0.06, ledge.y + 0.40)
	if k < 0.45:
		c = s_from.lerp(p1, smoothstep(0.0, 1.0, k / 0.45))
	elif k < 0.75:
		c = p1.lerp(p2, smoothstep(0.0, 1.0, (k - 0.45) / 0.3))
	else:
		c = p2.lerp(climb_dest, smoothstep(0.0, 1.0, (k - 0.75) / 0.25))
	if k >= 1.0:
		c = climb_dest
		v = Vector2.ZERO
		ground_y = ledge.y
		_set_state(RUN if running else IDLE)
		_emit("trick", {"name": "Подъём на край", "pts": 50})


func _find_vault() -> bool:
	var ft := feet()
	for r in level.solids:
		var front := r.position.x if f > 0 else r.end.x
		var dist := (front - c.x) * f - W * 0.5
		if dist < -0.05 or dist > VAULT_RANGE:
			continue
		if r.position.y > ft + 0.05:
			continue
		var ht := r.end.y - ft
		if ht < 0.3 or ht > 1.25:
			continue
		var over := Rect2(Vector2(r.position.x - 0.3, r.end.y + 0.01), Vector2(r.size.x + 0.6, 1.4))
		if not level.box_free(over):
			continue
		if dist > 0.55 and st == RUN and absf(v.x) > 2.0:
			vault_pending = true
			return true
		var end := Vector2.ZERO
		if r.size.x <= 1.7:
			var back := r.end.x if f > 0 else r.position.x
			end = Vector2(back + f * (W * 0.5 + 0.35), ft + H_STAND * 0.5 + 0.0005)
		else:
			end = Vector2(front + f * 0.65, r.end.y + H_STAND * 0.5 + 0.0005)
		if not level.box_free(box(end, H_STAND).grow(-0.01)):
			continue
		vault_pending = false
		vault_rect = r
		vault_end = end
		s_from = c
		vault_speed = maxf(absf(v.x), 4.5)
		vault_t = clampf(absf(end.x - c.x) / vault_speed, 0.34, 0.62)
		_set_state(VAULT)
		_emit("vault")
		return true
	vault_pending = false
	return false


func _vault(_dt: float) -> void:
	var k := clampf(t_state / vault_t, 0.0, 1.0)
	var apex := vault_rect.end.y + 0.55
	var mid := lerpf(s_from.y, vault_end.y, 0.5)
	var y := lerpf(s_from.y, vault_end.y, smoothstep(0.0, 1.0, k)) + maxf(0.0, apex - mid) * pow(sin(PI * k), 0.85)
	c = Vector2(lerpf(s_from.x, vault_end.x, k), y)
	v = Vector2(f * vault_speed, 0.0)
	if k >= 1.0:
		c = vault_end
		h = H_STAND
		ground_y = vault_end.y - H_STAND * 0.5
		_emit("trick", {"name": "Перелёт", "pts": 100})
		_set_state(RUN if running else IDLE)


func _try_wall(vx0: float) -> bool:
	if wall_cd > 0.0 or absf(omega) > 4.0 or absf(wrapf(rho, -PI, PI)) > 0.6:
		return false
	if absf(vx0) < 2.5 or signf(vx0) != float(f):
		return false
	var r: Rect2 = level.solids[hit_x]
	if r.end.y < c.y + 1.25:
		return false
	wall_face = r.position.x if f > 0 else r.end.x
	v = Vector2(0.0, maxf(v.y, -0.5))
	wall_steps = 0
	_set_state(WALL)
	_emit("wall")
	return true


func _wall(dt: float) -> void:
	v.y -= G * dt * (0.5 if v.y < 0.0 else 1.0)
	v.y = maxf(v.y, -3.0)
	_move(Vector2(f * 0.4 * dt, v.y * dt), false)
	if on_floor:
		_stand_on_floor()
		_set_state(IDLE)
		return
	if _try_ledge():
		return
	if hit_x < 0 or (t_state > WALL_HOLD and v.y < 0.3):
		wall_cd = 0.45
		_enter_air("fall", true)


func _try_bar() -> bool:
	if grab_cd > 0.0 or absf(wrapf(rho, -PI, PI)) > 0.8:
		return false
	var reach := c + Vector2(f * 0.18, REACH)
	for b in level.bars:
		if reach.distance_to(b) < BAR_GRAB:
			bar = b
			var rel := c - b
			phi = atan2(f * rel.x, -rel.y)
			var tg := Vector2(f * cos(phi), sin(phi))
			dphi = v.dot(tg) / BAR_L * BAR_CATCH
			c = b + Vector2(f * sin(phi), -cos(phi)) * BAR_L
			v = Vector2.ZERO
			rho = 0.0
			omega = 0.0
			rho_target = 0.0
			h = H_STAND
			_set_state(SWING)
			_emit("bar")
			return true
	return false


func _swing(dt: float) -> void:
	dphi += (-(G / BAR_L) * sin(phi) - 0.22 * dphi) * dt
	phi += dphi * dt
	c = bar + Vector2(f * sin(phi), -cos(phi)) * BAR_L


func _release_bar(boost: bool) -> void:
	v = BAR_L * dphi * Vector2(f * cos(phi), sin(phi)) * (1.06 if boost else 1.0)
	rho = -phi
	omega = -dphi
	if omega < -1.0:
		rho_target = floorf(rho / TAU - 0.02) * TAU
	elif omega > 1.0:
		rho_target = ceilf(rho / TAU + 0.02) * TAU
	else:
		rho_target = roundf(rho / TAU) * TAU
	grab_cd = 0.45
	_enter_air("bar", false)
	_emit("release")


func _crash(impulse: Vector2, reason: String) -> void:
	if joints.is_empty():
		update_visual(1.0 / 60.0)
	ragdoll.start(joints, prev_joints if not prev_joints.is_empty() else joints, 1.0 / 60.0, v * 0.85 + impulse, f)
	running = false
	_set_state(CRASH)
	_emit("crash", {"reason": reason})


# ---------------------------------------------------------------- visuals

func _mirror(q: Vector2) -> Vector2:
	return Vector2(q.x * f, q.y)


func _to_local(w: Vector2, origin: Vector2, rot: float) -> Vector2:
	return _mirror((w - origin).rotated(-rot))


func _ik_hands(fp: PackedFloat32Array, tl: Vector2, tr: Vector2, wgt: float) -> void:
	if wgt <= 0.001:
		return
	var q := fp.duplicate()
	Rig.ik_arm(q, true, tl)
	Rig.ik_arm(q, false, tr)
	for i in [Rig.SL, Rig.EL, Rig.SR, Rig.ER]:
		fp[i] = lerpf(fp[i], q[i], wgt)


func _smooth(tgt: PackedFloat32Array, rate: float, dt: float) -> void:
	var k := 1.0 - exp(-rate * dt)
	for i in Rig.COUNT:
		pose[i] = lerpf(pose[i], tgt[i], k)


func update_visual(dt: float) -> void:
	prev_joints = joints
	if st == CRASH:
		joints = ragdoll.joints()
		vis_rot = 0.0
		return
	var acc := (v.x - last_vx) / maxf(dt, 0.001) * f
	last_vx = v.x
	lean = lerpf(lean, clampf(acc * 0.018, -0.18, 0.22), 1.0 - exp(-8.0 * dt))
	var tgt: PackedFloat32Array
	var rate := 18.0
	var mode := 0   # 0 ground, 1 air (com pivot), 2 roll (ground contact), 3 pelvis-anchored, 4 bar
	var rot := 0.0
	var pelvis_w := c + Vector2(0.0, 0.05)
	var ik_w := 0.0
	var ik_l := Vector2.ZERO
	var ik_r := Vector2.ZERO
	var ik_world := true
	var flat_feet := false
	match st:
		IDLE:
			tgt = Poses.idle(time)
			flat_feet = true
		RUN:
			var spd := absf(v.x)
			run_u += dt * spd / (1.2 + 0.42 * spd)
			tgt = Poses.run(run_u, clampf(spd / RUN_SPEED, 0.0, 1.1), lean)
			rate = 40.0
		SKID:
			tgt = Poses.p(Poses.SKID)
			rate = 14.0
			flat_feet = true
		LAND:
			var k := clampf(t_state / maxf(land_dur, 0.01), 0.0, 1.0)
			if land_hard:
				tgt = Rig.lerp_pose(Poses.p(Poses.STUMBLE), Poses.p(Poses.STAND), smoothstep(0.55, 1.0, k))
			else:
				tgt = Poses.land(land_depth * (1.0 - smoothstep(0.35, 1.0, k)))
			rate = 30.0
			flat_feet = true
		AIR:
			tgt = Poses.air(v.y, tuck, air_t)
			if roll_intent > 0.0 and v.y < 0.0 and tuck < 0.3:
				tgt = Rig.lerp_pose(tgt, Poses.p(Poses.LAND_READY), 0.6)
			rate = 22.0
			mode = 1
			rot = rho
		ROLL:
			var k := clampf(roll_rho / roll_end, 0.0, 1.0)
			tgt = Rig.lerp_pose(Poses.p(Poses.TUCK), Poses.p(Poses.CROUCH), smoothstep(0.78, 1.0, k))
			rate = 30.0
			mode = 2
			rot = roll_rho
		HANG:
			pelvis_w = c + Vector2(f * 0.08, 0.05)
			var sw := sin(t_state * 3.2) * exp(-t_state * 1.5)
			tgt = Poses.p(Poses.HANG)
			tgt[Rig.HL] += 0.25 * sw
			tgt[Rig.HR] += 0.18 * sw
			mode = 3
			ik_w = 1.0
			ik_l = ledge + Vector2(-f * 0.02, 0.0)
			ik_r = ledge + Vector2(-f * 0.06, 0.0)
		CLIMB:
			var k := clampf(t_state / CLIMB_T, 0.0, 1.0)
			if k < 0.45:
				tgt = Rig.lerp_pose(Poses.p(Poses.HANG), Poses.p(Poses.PULL), smoothstep(0.0, 1.0, k / 0.45))
			elif k < 0.75:
				tgt = Rig.lerp_pose(Poses.p(Poses.PULL), Poses.p(Poses.KNEE_UP), smoothstep(0.0, 1.0, (k - 0.45) / 0.3))
			else:
				tgt = Rig.lerp_pose(Poses.p(Poses.KNEE_UP), Poses.p(Poses.STAND), smoothstep(0.0, 1.0, (k - 0.75) / 0.25))
			rate = 26.0
			mode = 3
			pelvis_w = c + Vector2(f * 0.08 * (1.0 - k), 0.05)
			ik_w = 1.0 - smoothstep(0.7, 0.86, k)
			ik_l = ledge + Vector2(f * 0.04, 0.0)
			ik_r = ledge + Vector2(-f * 0.02, 0.0)
		VAULT:
			var k := clampf(t_state / vault_t, 0.0, 1.0)
			tgt = Rig.lerp_pose(Poses.p(Poses.KONG), Poses.p(Poses.VAULT_OVER), smoothstep(0.35, 0.75, k))
			if k > 0.8:
				tgt = Rig.lerp_pose(tgt, Poses.run(run_u, 1.0, 0.0), smoothstep(0.8, 1.0, k))
			rate = 30.0
			mode = 3
			pelvis_w = c + Vector2(0.0, 0.05)
			var front := vault_rect.position.x if f > 0 else vault_rect.end.x
			var top := vault_rect.end.y
			ik_w = smoothstep(0.08, 0.3, k) * (1.0 - smoothstep(0.6, 0.72, k))
			ik_l = Vector2(front + f * 0.26, top)
			ik_r = Vector2(front + f * 0.18, top)
		WALL:
			tgt = Poses.p(Poses.WALL)
			var ph := sin(t_state * 14.0) * (1.0 if v.y > 0.5 else 0.0)
			tgt[Rig.HL] += 0.35 * ph
			tgt[Rig.HR] -= 0.35 * ph
			rate = 20.0
			mode = 3
		SWING:
			var k := clampf(0.5 + dphi * 0.12 * signf(cos(phi)), 0.0, 1.0)
			tgt = Rig.lerp_pose(Poses.p(Poses.BAR_ARCH), Poses.p(Poses.BAR_PIKE), k)
			rate = 12.0
			mode = 4
			rot = -phi
			ik_world = false
			ik_w = 1.0
			ik_l = Vector2(0.02, 1.0)
			ik_r = Vector2(-0.02, 1.0)
	_smooth(tgt, rate, dt)
	var fp := pose.duplicate()
	if flat_feet:
		fp[Rig.AL] = Rig.flat_ankle(fp, true)
		fp[Rig.AR] = Rig.flat_ankle(fp, false)
	# tuck: hands hold the shins
	if mode == 1 and tuck > 0.45:
		var jj := Rig.fk(fp)
		_ik_hands(fp, jj["knee_l"].lerp(jj["ankle_l"], 0.42), jj["knee_r"].lerp(jj["ankle_r"], 0.38), smoothstep(0.45, 0.8, tuck))
	if mode == 2 and roll_rho < roll_end * 0.8:
		var jj := Rig.fk(fp)
		_ik_hands(fp, jj["knee_l"].lerp(jj["ankle_l"], 0.4), jj["knee_r"].lerp(jj["ankle_r"], 0.35), 0.8)
	if ik_w > 0.0:
		if ik_world:
			_ik_hands(fp, _to_local(ik_l, pelvis_w, 0.0), _to_local(ik_r, pelvis_w, 0.0), ik_w)
		else:
			_ik_hands(fp, ik_l, ik_r, ik_w)
	Rig.clamp_pose(fp)
	var loc := Rig.fk(fp)
	var wr := -f * rot          # math (CCW) rotation in world
	var origin := Vector2.ZERO  # world position of the pelvis
	match mode:
		0:
			origin = Vector2(c.x, feet() - Rig.lowest_y(loc))
			if st == RUN:
				origin.y += 0.03 * maxf(0.0, sin(TAU * 2.0 * run_u - 0.5))
		1:
			var cm := Rig.com(loc)
			origin = c - _mirror(cm).rotated(wr)
		2:
			var cm := Rig.com(loc)
			var miny := INF
			for key in loc:
				var q: Vector2 = _mirror(loc[key] - cm).rotated(wr)
				var rr := Rig.HEAD_R if key == "head" else 0.05
				miny = minf(miny, q.y - rr)
			origin = Vector2(c.x, feet() - miny) - _mirror(cm).rotated(wr)
		3:
			origin = pelvis_w
		4:
			var grip: Vector2 = (loc["hand_l"] + loc["hand_r"]) * 0.5
			origin = bar - _mirror(grip).rotated(wr)
	# inertialization: hide discontinuities when the state changes
	if teleport:
		off_pos = Vector2.ZERO
		off_rot = 0.0
		teleport = false
	elif vis_dirty:
		off_pos += last_pelvis - origin
		off_rot += wrapf(last_rot - wr, -PI, PI)
	vis_dirty = false
	var dk := exp(-dt * 16.0)
	off_pos *= dk
	off_rot *= dk
	last_pelvis = origin
	last_rot = wr
	var total_rot := wr + off_rot
	vis_rot = total_rot
	var o2 := origin + off_pos
	var out := {}
	for key in loc:
		out[key] = o2 + _mirror(loc[key]).rotated(total_rot)
	joints = out
