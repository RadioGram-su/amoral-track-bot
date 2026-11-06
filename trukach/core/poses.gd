class_name Poses
extends RefCounted
## Hand-authored pose library + procedural cycles. All values are joint angles (see Rig).
## Order: B, N, HL, KL, AL, HR, KR, AR, SL, EL, SR, ER

const STAND := [0.03, -0.02, 0.05, 0.06, 0.06, 0.02, 0.05, 0.05, 0.10, 0.22, -0.05, 0.25]
const CROUCH := [0.45, -0.35, 1.25, 1.95, 0.0, 1.15, 1.85, 0.0, 0.95, 0.45, 0.70, 0.55]
const TAKEOFF := [0.20, -0.15, 0.25, 0.25, 0.55, -0.20, 0.15, 0.65, 2.70, 0.25, 2.50, 0.35]
const RISE := [0.10, -0.10, 1.25, 1.55, 0.25, 0.15, 0.55, 0.45, 2.55, 0.40, 2.25, 0.55]
const FALL := [0.05, 0.0, 0.85, 0.70, 0.15, 0.45, 0.45, 0.20, 1.55, 0.35, 1.25, 0.45]
const LAND_READY := [0.20, -0.10, 0.95, 0.85, 0.05, 0.80, 0.75, 0.05, 1.20, 0.40, 1.00, 0.50]
const TUCK := [0.55, -0.20, 2.50, 2.55, 0.45, 2.42, 2.55, 0.45, 1.05, 1.30, 0.95, 1.40]
const LAYOUT := [-0.05, 0.05, 0.05, 0.08, 0.40, -0.05, 0.10, 0.40, 0.25, 0.20, 0.35, 0.25]
const HANG := [-0.05, 0.25, 0.25, 0.45, 0.30, 0.05, 0.25, 0.35, 3.05, 0.15, 3.05, 0.15]
const WALL := [-0.10, 0.20, 1.35, 1.35, -0.10, 0.70, 0.90, 0.15, 2.90, 0.30, 2.60, 0.45]
const SKID := [-0.25, 0.10, 0.75, 0.45, -0.20, 0.25, 0.70, 0.10, 1.10, 0.60, 0.40, 0.80]
const STUMBLE := [0.75, -0.45, 1.45, 2.15, -0.05, 1.20, 2.00, 0.0, 1.30, 0.50, 0.85, 0.40]
const KONG := [0.75, -0.55, 1.85, 2.35, 0.40, 1.70, 2.30, 0.40, 1.50, 0.15, 1.45, 0.20]
const VAULT_OVER := [0.15, -0.10, 1.65, 0.90, 0.25, 1.50, 0.80, 0.25, 0.90, 0.10, 0.80, 0.15]
const PULL := [0.10, 0.30, 0.60, 1.20, 0.30, 1.30, 1.90, 0.20, 2.90, 1.60, 2.90, 1.60]
const KNEE_UP := [0.70, -0.30, 2.25, 2.45, 0.40, 0.70, 1.20, 0.30, 1.45, 0.70, 1.45, 0.70]
const BAR_ARCH := [-0.22, 0.30, -0.35, 0.10, 0.50, -0.30, 0.05, 0.50, 3.10, 0.05, 3.10, 0.05]
const BAR_PIKE := [0.10, -0.10, 0.95, 0.05, 0.40, 0.90, 0.05, 0.40, 3.10, 0.05, 3.10, 0.05]

# one-leg running cycle keys, u = 0 at foot strike: [u, hip (world, from vertical), knee, ankle]
const RUN_KEYS := [
	[0.00, 0.50, 0.32, 0.10],
	[0.12, 0.28, 0.62, -0.25],
	[0.32, -0.38, 0.42, 0.55],
	[0.45, -0.32, 1.35, 0.50],
	[0.60, 0.30, 2.15, 0.15],
	[0.80, 0.92, 1.20, -0.05],
	[0.92, 0.70, 0.55, 0.00],
	[1.00, 0.50, 0.32, 0.10],
]


static func p(a: Array) -> PackedFloat32Array:
	return Rig.make(a)


static func _cubic(y0: float, y1: float, y2: float, y3: float, t: float) -> float:
	# Catmull-Rom
	var t2 := t * t
	return 0.5 * ((2.0 * y1) + (-y0 + y2) * t + (2.0 * y0 - 5.0 * y1 + 4.0 * y2 - y3) * t2 + (-y0 + 3.0 * y1 - 3.0 * y2 + y3) * t2 * t)


static func _run_leg(u: float) -> Vector3:
	u = fposmod(u, 1.0)
	var n := RUN_KEYS.size()
	for i in n - 1:
		var k0: Array = RUN_KEYS[i]
		var k1: Array = RUN_KEYS[i + 1]
		if u <= k1[0]:
			var t: float = (u - float(k0[0])) / (float(k1[0]) - float(k0[0]))
			var km: Array = RUN_KEYS[(i - 1 + n - 1) % (n - 1)]
			var kp: Array = RUN_KEYS[(i + 2) % (n - 1)]
			return Vector3(_cubic(km[1], k0[1], k1[1], kp[1], t), maxf(0.0, _cubic(km[2], k0[2], k1[2], kp[2], t)), _cubic(km[3], k0[3], k1[3], kp[3], t))
	return Vector3(RUN_KEYS[0][1], RUN_KEYS[0][2], RUN_KEYS[0][3])


## Procedural run. u: cycle phase (0..1), s: intensity 0 (walk-ish) .. 1 (full run), lean: extra trunk lean.
static func run(u: float, s: float, lean: float) -> PackedFloat32Array:
	var o := p(STAND)
	var b := 0.08 + 0.16 * s + lean
	o[Rig.B] = b
	o[Rig.N] = -b * 0.65
	var l := _run_leg(u)
	var r := _run_leg(u + 0.5)
	var amp := lerpf(0.45, 1.0, s)
	o[Rig.HL] = l.x * amp + b
	o[Rig.KL] = lerpf(0.15, l.y, amp)
	o[Rig.AL] = l.z * amp
	o[Rig.HR] = r.x * amp + b
	o[Rig.KR] = lerpf(0.15, r.y, amp)
	o[Rig.AR] = r.z * amp
	# arms counter-swing (left arm follows right leg), elbows flexed ~90°
	o[Rig.SL] = (r.x - 0.2) * 1.05 * amp + b + 0.15
	o[Rig.SR] = (l.x - 0.2) * 1.05 * amp + b + 0.15
	o[Rig.EL] = 1.45 + 0.25 * sin(TAU * (u + 0.5)) * amp
	o[Rig.ER] = 1.45 + 0.25 * sin(TAU * u) * amp
	Rig.clamp_pose(o)
	return o


static func idle(t: float) -> PackedFloat32Array:
	var o := p(STAND)
	var br := sin(t * 1.7)
	o[Rig.B] += 0.015 * br
	o[Rig.SL] += 0.03 * br
	o[Rig.SR] -= 0.03 * br
	o[Rig.KL] += 0.03 * (0.5 + 0.5 * sin(t * 0.6))
	o[Rig.KR] += 0.03 * (0.5 - 0.5 * sin(t * 0.6))
	return o


## Landing absorb: a = 0..1 depth.
static func land(a: float) -> PackedFloat32Array:
	return Rig.lerp_pose(p(STAND), p(CROUCH), clampf(a, 0.0, 1.0))


## Airborne pose from vertical speed and tuck amount.
static func air(vy: float, tuck: float, t_air: float) -> PackedFloat32Array:
	var k := clampf(0.5 - vy / 14.0, 0.0, 1.0)  # 0 rising fast .. 1 falling fast
	var base := Rig.lerp_pose(p(RISE), p(FALL), k)
	if t_air < 0.12:
		base = Rig.lerp_pose(p(TAKEOFF), base, t_air / 0.12)
	return Rig.lerp_pose(base, p(TUCK), clampf(tuck, 0.0, 1.0))
