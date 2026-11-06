class_name DemoCourse
extends RefCounted
## Demo course: every move in order, so one run shows the whole move set.

static func build() -> Level:
	var L := Level.new()
	L.name = "Демо-трасса"
	# start roof + crate to vault
	L.add(-8.0, -4.0, 16.0, 0.0, "roof")
	L.add(6.0, 0.0, 6.9, 0.85, "crate")
	# gap for the long jump, second roof with a low duct (roll under it)
	L.add(19.6, -4.0, 31.0, 0.0, "roof")
	L.add(24.5, 1.12, 26.5, 2.6, "duct")
	# building with a grabbable ledge
	L.add(31.0, -4.0, 38.0, 2.5, "building")
	# big drop to a lower roof (landing roll), running backflip, bar over a small gap
	L.add(38.0, -6.0, 56.9, -2.0, "roof")
	L.bars.append(Vector2(55.6, 1.0))
	L.add(58.0, -6.0, 65.0, -2.0, "roof")
	# tall building: wall run to the ledge
	L.add(65.0, -6.0, 73.0, 1.6, "building")
	# drop for the double flip, final wall for the wall flip
	L.add(73.0, -7.0, 101.0, -3.0, "roof")
	L.add(93.0, -7.0, 95.0, 4.0, "wall")
	L.spawn = Vector2(0.0, 0.0)
	L.finish_x = 89.0
	L.kill_y = -9.0
	for cp in [Vector2(0, 0), Vector2(21, 0), Vector2(34, 2.5), Vector2(45, -2), Vector2(60.5, -2), Vector2(68, 1.6), Vector2(83, -3)]:
		L.checkpoints.append(cp)
	# decoration (no collision)
	L.add_decor("ac", Vector2(1.6, 0.0), Vector2(1.1, 0.8))
	L.add_decor("vent", Vector2(10.8, 0.0), Vector2(0.5, 0.9))
	L.add_decor("ac", Vector2(13.0, 0.0), Vector2(0.9, 0.7))
	L.add_decor("rail", Vector2(-8.0, 0.0), Vector2(24.0, 1.0))
	L.add_decor("rail", Vector2(19.6, 0.0), Vector2(11.4, 1.0))
	L.add_decor("vent", Vector2(29.0, 0.0), Vector2(0.4, 1.2))
	L.add_decor("tank", Vector2(36.2, 2.5), Vector2(1.9, 3.2))
	L.add_decor("ac", Vector2(33.2, 2.5), Vector2(1.0, 0.75))
	L.add_decor("ac", Vector2(41.5, -2.0), Vector2(1.2, 0.85))
	L.add_decor("chimney", Vector2(49.5, -2.0), Vector2(0.7, 2.2))
	L.add_decor("post", Vector2(55.6, -2.0), Vector2(0.12, 3.0))
	L.add_decor("rail", Vector2(38.0, -2.0), Vector2(18.9, 1.0))
	L.add_decor("ac", Vector2(61.2, -2.0), Vector2(1.0, 0.8))
	L.add_decor("antenna", Vector2(71.5, 1.6), Vector2(0.1, 4.0))
	L.add_decor("ac", Vector2(68.6, 1.6), Vector2(1.1, 0.8))
	L.add_decor("skylight", Vector2(77.5, -3.0), Vector2(2.2, 0.5))
	L.add_decor("ac", Vector2(84.0, -3.0), Vector2(1.0, 0.8))
	L.add_decor("flag", Vector2(89.0, -3.0), Vector2(0.9, 2.6))
	L.finalize()
	return L


static func demo_steps() -> Array:
	var F := Actor.FWD
	var B := Actor.BACK
	var U := Actor.UP
	var D := Actor.DOWN
	return [
		{"when": "wait", "v": 1.3, "caption": "Свайп вперёд — бег", "glyphs": ["F"], "cmd": F},
		{"when": "x", "v": 4.55, "caption": "Вверх у препятствия — перелёт", "glyphs": ["U"], "cmd": U},
		{"when": "x", "v": 15.05, "ground": true, "caption": "Вверх на бегу — прыжок в длину", "glyphs": ["U"], "cmd": U},
		{"when": "air_t", "v": 0.04, "caption": "Вперёд в воздухе — сальто вперёд", "glyphs": ["U", "F"], "cmd": F},
		{"when": "x", "v": 21.0, "ground": true, "caption": "Не пригнулся — удар о трубу", "glyphs": []},
		{"when": "respawned", "v": 0.7, "caption": "Чекпоинт. Свайп вперёд — снова бег", "glyphs": ["F"], "cmd": F},
		{"when": "x", "v": 22.4, "ground": true, "caption": "Вниз — кувырок под трубой", "glyphs": ["D"], "cmd": D},
		{"when": "x", "v": 29.4, "ground": true, "caption": "Прыжок к стене — зацеп за край", "glyphs": ["U"], "cmd": U},
		{"when": "state", "v": Actor.HANG, "after": 0.45, "caption": "Вверх — подтянуться", "glyphs": ["U"], "cmd": U},
		{"when": "x", "v": 37.0, "caption": "Вниз перед приземлением — кувырок гасит удар", "glyphs": ["D"]},
		{"when": "falling_h", "v": 1.6, "cmd": D},
		{"when": "x", "v": 46.0, "ground": true, "caption": "Вверх, затем назад — сальто назад", "glyphs": ["U", "B"], "cmd": U},
		{"when": "air_t", "v": 0.04, "cmd": B},
		{"when": "x", "v": 53.3, "ground": true, "caption": "Прыжок — хват за перекладину", "glyphs": ["U"], "cmd": U},
		{"when": "state", "v": Actor.SWING, "after": 0.02, "caption": "Вперёд и назад в нижней точке — раскачка", "glyphs": ["F", "B"]},
		{"when": "swing_bottom", "v": 1.0, "cmd": F},
		{"when": "swing_bottom", "v": -1.0, "cmd": B},
		{"when": "swing_bottom", "v": 1.0, "cmd": F},
		{"when": "swing_release", "v": [0.75, 1.05], "caption": "Вверх — соскок с переворотом", "glyphs": ["U"], "cmd": U},
		{"when": "x", "v": 63.5, "ground": true, "caption": "Прыжок к высокой стене", "glyphs": ["U"], "cmd": U},
		{"when": "state", "v": Actor.WALL, "caption": "Вверх на стене — шаг по стене и зацеп", "glyphs": ["U"], "cmd": U},
		{"when": "state", "v": Actor.HANG, "after": 0.3, "caption": "Вверх — подтянуться", "glyphs": ["U"], "cmd": U},
		{"when": "x", "v": 72.25, "ground": true, "caption": "Вверх, вперёд, вперёд — двойное сальто", "glyphs": ["U", "F", "F"], "cmd": U},
		{"when": "air_t", "v": 0.03, "cmd": F},
		{"when": "air_t", "v": 0.10, "cmd": F},
		{"when": "falling_h", "v": 1.5, "caption": "Вниз — кувырок при приземлении", "glyphs": ["D"], "cmd": D},
		{"when": "x", "v": 91.35, "ground": true, "caption": "К стене, затем назад — сальто от стены", "glyphs": ["U", "B"], "cmd": U},
		{"when": "state", "v": Actor.WALL, "after": 0.04, "cmd": B},
		{"when": "wait", "v": 2.6, "caption": "", "glyphs": []},
	]
