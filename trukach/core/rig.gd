class_name Rig
extends RefCounted
## Planar skeleton of the acrobat.
## Local space: metres, y up, pelvis at the origin, character faces +x.
## Limb angles are measured from "straight down", positive = towards the front (CCW).
## Spine / neck angles are measured from "straight up", positive = leaning forward (CW).
## So a rigid forward lean of the trunk by B changes every limb's absolute angle by -B.

const SPINE := 0.50      # pelvis -> neck base
const SHOULDER := 0.445  # pelvis -> shoulder joint, along the spine
const NECK := 0.155      # neck base -> head centre
const HEAD_R := 0.118
const THIGH := 0.445
const SHIN := 0.43
const FOOT := 0.19       # ankle -> toe (along the sole)
const HEEL := 0.06       # ankle -> heel
const SOLE := 0.06       # ankle height above the sole
const UARM := 0.29
const FARM := 0.255
const HAND := 0.085
const LEG := THIGH + SHIN + SOLE

# pose indices
const B := 0   # trunk lean
const N := 1   # neck
const HL := 2
const KL := 3
const AL := 4
const HR := 5
const KR := 6
const AR := 7
const SL := 8
const EL := 9
const SR := 10
const ER := 11
const COUNT := 12

# anatomical limits (radians). Knees and elbows never go below 0 -> they cannot bend backwards.
const LO := [-0.9, -0.7, -0.6, 0.0, -0.6, -0.6, 0.0, -0.6, -1.0, 0.0, -1.0, 0.0]
const HI := [1.7, 0.8, 2.6, 2.62, 0.9, 2.6, 2.62, 0.9, 3.25, 2.55, 3.25, 2.55]

const POINTS := ["pelvis", "chest", "neck", "head",
	"knee_l", "ankle_l", "toe_l", "heel_l", "knee_r", "ankle_r", "toe_r", "heel_r",
	"elbow_l", "wrist_l", "hand_l", "elbow_r", "wrist_r", "hand_r"]


static func dn(a: float) -> Vector2:
	return Vector2(sin(a), -cos(a))


static func upv(a: float) -> Vector2:
	return Vector2(sin(a), cos(a))


static func make(vals: Array) -> PackedFloat32Array:
	var p := PackedFloat32Array()
	p.resize(COUNT)
	for i in COUNT:
		p[i] = vals[i]
	return p


static func clamp_pose(p: PackedFloat32Array) -> void:
	for i in COUNT:
		p[i] = clampf(p[i], LO[i], HI[i])


static func lerp_pose(a: PackedFloat32Array, b: PackedFloat32Array, t: float) -> PackedFloat32Array:
	var o := PackedFloat32Array()
	o.resize(COUNT)
	for i in COUNT:
		o[i] = lerpf(a[i], b[i], t)
	return o


## Forward kinematics -> Dictionary of local joint positions.
static func fk(p: PackedFloat32Array) -> Dictionary:
	var j := {}
	var b := p[B]
	var u := upv(b)
	var chest := u * SHOULDER
	var neck := u * SPINE
	j["pelvis"] = Vector2.ZERO
	j["chest"] = chest
	j["neck"] = neck
	j["head"] = neck + upv(b + p[N]) * NECK
	for s in 2:
		var sx := "_l" if s == 0 else "_r"
		var hi := HL if s == 0 else HR
		var si := SL if s == 0 else SR
		var a := p[hi] - b
		var knee := dn(a) * THIGH
		var sig := a - p[hi + 1]
		var ankle := knee + dn(sig) * SHIN
		var fa := sig + PI * 0.5 - p[hi + 2]
		var fd := dn(fa)
		j["knee" + sx] = knee
		j["ankle" + sx] = ankle
		j["toe" + sx] = ankle + fd * FOOT
		j["heel" + sx] = ankle - fd * HEEL
		var al := p[si] - b
		var elbow := chest + dn(al) * UARM
		var fal := al + p[si + 1]
		var wrist := elbow + dn(fal) * FARM
		j["elbow" + sx] = elbow
		j["wrist" + sx] = wrist
		j["hand" + sx] = wrist + dn(fal) * HAND
	return j


## Sole points (under heel / toe) for ground contact.
static func sole_points(j: Dictionary, sx: String) -> Array:
	var d: Vector2 = (j["toe" + sx] - j["heel" + sx]).normalized()
	var perp := Vector2(d.y, -d.x) * SOLE
	return [j["heel" + sx] + perp, j["toe" + sx] + perp]


static func lowest_y(j: Dictionary) -> float:
	var m := INF
	for sx in ["_l", "_r"]:
		for q in sole_points(j, sx):
			m = minf(m, q.y)
	return m


## Approximate centre of mass (segment-mass weighted).
static func com(j: Dictionary) -> Vector2:
	var c: Vector2 = (j["pelvis"] + j["neck"]) * 0.5 * 0.46 + j["head"] * 0.08
	for sx in ["_l", "_r"]:
		c += (j["chest"] + j["elbow" + sx]) * 0.5 * 0.028
		c += (j["elbow" + sx] + j["wrist" + sx]) * 0.5 * 0.022
		c += (j["pelvis"] + j["knee" + sx]) * 0.5 * 0.1
		c += (j["knee" + sx] + j["ankle" + sx]) * 0.5 * 0.045
		c += j["ankle" + sx] * 0.015
	return c / (0.46 + 0.08 + 2.0 * (0.028 + 0.022 + 0.1 + 0.045 + 0.015))


## Analytic two-bone IK for an arm. Elbow always bends backwards (anatomical).
## grip: 0..1 how far along the hand the target is held.
static func ik_arm(p: PackedFloat32Array, left: bool, target: Vector2, grip: float = 0.5) -> void:
	var b := p[B]
	var root := upv(b) * SHOULDER
	var l1 := UARM
	var l2 := FARM + HAND * grip
	var d := target - root
	var dist := clampf(d.length(), absf(l1 - l2) + 0.002, l1 + l2 - 0.002)
	var th := atan2(d.x, -d.y)
	var g := acos(clampf((l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist), -1.0, 1.0))
	var flex := PI - acos(clampf((l1 * l1 + l2 * l2 - dist * dist) / (2.0 * l1 * l2), -1.0, 1.0))
	var si := SL if left else SR
	p[si] = clampf(wrapf(th - g + b, -1.5, 4.78), LO[si], HI[si])
	p[si + 1] = clampf(flex, LO[si + 1], HI[si + 1])


## Analytic two-bone IK for a leg (target = ankle). Knee always bends forwards.
static func ik_leg(p: PackedFloat32Array, left: bool, target: Vector2) -> void:
	var b := p[B]
	var l1 := THIGH
	var l2 := SHIN
	var d := target
	var dist := clampf(d.length(), absf(l1 - l2) + 0.002, l1 + l2 - 0.002)
	var th := atan2(d.x, -d.y)
	var g := acos(clampf((l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist), -1.0, 1.0))
	var flex := PI - acos(clampf((l1 * l1 + l2 * l2 - dist * dist) / (2.0 * l1 * l2), -1.0, 1.0))
	var hi := HL if left else HR
	p[hi] = clampf(wrapf(th + g + b, -1.5, 4.78), LO[hi], HI[hi])
	p[hi + 1] = clampf(flex, LO[hi + 1], HI[hi + 1])


## Ankle angle that keeps the foot flat on a horizontal floor (rig not rotated).
static func flat_ankle(p: PackedFloat32Array, left: bool) -> float:
	var hi := HL if left else HR
	var sig := p[hi] - p[B] - p[hi + 1]
	return clampf(sig, LO[hi + 2], HI[hi + 2])
