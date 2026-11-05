# Карта проекта

> Сгенерировано `python3 tools/project_map.py`. Не редактировать вручную —
> перегенерируй после изменений. Формат: `путь` — назначение; ниже символы `строка: имя`.

## (корень)

- `.gitignore` (4 стр.)
- `CLAUDE.md` (24 стр.) — Правила работы с репозиторием
- `README.md` (101 стр.) — Habit Tracker Bot (A-Moral Track)
- `package.json` (17 стр.) — ключи: name, version, description, main, scripts, engines, license, type

## assets

- `assets/` — ресурсы (2): amoral-bot-logo.png, bot-avatar.png
- `assets/alerts/` — ресурсы (21): amoral-bot-logo.png, daystage.png, hold-01.png, hold-02.png, hold-03.png, hold-04.png, hold-05.png, hold-06.png, hold-07.png, hold-08.png, hold-09.png, hold-10.png, …ещё 9

## config

- `config/articles.json` (50 стр.) — ключи: smoking, alcohol, masturbation, junkfood, custom, survival_percent
- `config/images.json` (10 стр.) — ключи: smoking, alcohol, masturbation, junkfood, custom, general, urge
- `config/motivation.json` (182 стр.) — ключи: general, smoking, alcohol, masturbation, junkfood
- `config/playlists.json` (12 стр.) — ключи: urge, morning, evening, smoking, alcohol, junkfood, masturbation, custom
- `config/replacements.json` (63 стр.) — ключи: smoking, alcohol, masturbation, junkfood, general
- `config/savings-ideas.json` (19 стр.) — ключи: by_amount, by_type
- `config/tones.json` (28 стр.) — ключи: sos, relapse, general, luck
- `config/images/` — ресурсы (11): alcohol-1.jpg, alcohol-2.jpg, general-1.jpg, general-2.jpg, junkfood-1.jpg, junkfood-2.jpg, masturbation-1.jpg, masturbation-2.jpg, smoking-1.jpg, smoking-2.jpg, urge-1.jpg

## data

- `data/motivation.json` (114 стр.) — ключи: general, smoking, alcohol
- `data/replacements.json` (39 стр.) — ключи: smoking, alcohol, general
- `data/state.json` (33 стр.) — ключи: users

## games/narisuy-geroya

- `games/narisuy-geroya/GDD.md` (183 стр.) — НАРИСУЙ ГЕРОЯ — дизайн-документ
- `games/narisuy-geroya/godot/assets/models/anchors.json` (45 стр.) — ключи: desk, notebook, lamp, clock, clip
- `games/narisuy-geroya/tools/blender/build_props.py` (943 стр.) — Нарисуй героя — процедурные 3D-модели стола.
  - 39: `def reset` · 44: `def mat` · 68: `def obj_from_bm` · 83: `def deselect_all` · 89: `def activate` · 95: `def apply_mods` · 101: `def bevel` · 112: `def subsurf` · 120: `def smooth` · 138: `def set_origin` · 145: `def apply_transform` · 150: `def join` · 162: `def planar_uv` · 187: `def box_uv` · 207: `def cube` · 215: `def lathe` · 241: `def prism` · 259: `def tube_along` · 293: `def export` · 313: `def to_godot` · 335: `def build_desk` · 372: `def page_mesh` · 406: `def build_notebook` · 444: `def build_pencil` · 494: `def build_marker` · 518: `def build_pen` · 542: `def build_eraser` · 557: `def build_sharpener` · 578: `def build_ruler` · 591: `def build_mug` · 618: `def build_lamp` · 676: `def build_clock` · 752: `def build_clip` · 788: `def build_paper_balls` · 815: `def build_inkbottle` · 834: `def build_books` · 858: `def build_window` · 880: `def build_scissors`
- `games/narisuy-geroya/tools/font/build_font.py` (354 стр.) — Шрифт «Каракуля» — собственный рукописный шрифт игры.
  - 31: `def arc` · 41: `def bez` · 51: `def dot` · 55: `def S` · 192: `def hnoise` · 198: `def densify` · 209: `def wobble` · 225: `def outline` · 250: `def glyph_name` · 256: `def poly_to_pen` · 277: `def build`
- `games/narisuy-geroya/godot/assets/fonts/` — ресурсы (1): Karakulya.ttf
- `games/narisuy-geroya/godot/assets/models/` — ресурсы (19): books.glb, clip.glb, clock.glb, desk.glb, eraser.glb, inkbottle.glb, lamp.glb, marker.glb, mug.glb, notebook.glb, paperball0.glb, paperball1.glb, …ещё 7

## games/odna-zhizn

- `games/odna-zhizn/GDD.md` (157 стр.) — ОДНА ЖИЗНЬ — дизайн-документ
- `games/odna-zhizn/tools/mockups/post.py` (285 стр.) — Пост-обработка мокапов: акварель «цвет = память», интерфейс поверх всех трёх стилей.
  - 18: `def load` · 22: `def save` · 26: `def value_noise` · 41: `def blur` · 48: `def sample` · 64: `def lum` · 68: `def paper_tex` · 79: `def watercolor` · 137: `def lacquer` · 179: `def font` · 183: `def wobbly_circle` · 195: `def ui_watercolor` · 223: `def ui_paper` · 254: `def ui_lacquer`
- `games/odna-zhizn/tools/mockups/scene.py` (865 стр.) — Мокапы трёх стилей «Одной жизни»: одна сцена долины, три способа рисовки.
  - 29: `def reset` · 33: `def new_mat` · 53: `def add_noise_bump` · 65: `def obj` · 76: `def smooth` · 81: `def sphere` · 91: `def cyl` · 105: `def box` · 114: `def camera` · 129: `def light` · 150: `def world` · 158: `def render` · 181: `def freestyle` · 216: `def H` · 227: `def stream_y` · 231: `def path_pts` · 242: `def ribbon` · 267: `def ground` · 287: `def person` · 345: `def house` · 380: `def oak` · 409: `def pine` · 418: `def bridge` · 438: `def build_valley` · 516: `def watercolor` · 572: `def paper_layer` · 593: `def wavy` · 602: `def circle` · 606: `def puppet` · 660: `def paper` · 803: `def lacquer`

## lib

- `lib/admin-stats.js` (57 стр.)
  - 1: `function isAdmin` · 6: `function touchActivity` · 12: `function shouldPersistActivity` · 17: `function markActivitySaved` · 21: `function activeSince` · 28: `function createdSince` · 35: `function buildAdminStats` · 48: `{`
- `lib/bot-helpers.js` (63 стр.) — Banner + support helpers for bot.js
  - 4: `function createBannerSender` · 19: `function supportKeyboard` · 28: `function moodKeyboard` · 40: `function proText` · 62: `{ createBannerSender, supportKeyboard, moodKeyboard, proText`
- `lib/extras.js` (126 стр.)
  - 3: `function isQuietHour` · 11: `function monthKey` · 16: `function weekKey` · 24: `function getDayStory` · 36: `function checkMilestone` · 46: `function goalProgress` · 59: `function shareStreakCard` · 72: `function countGlobalHolding` · 83: `function buddyCompare` · 97: `function triggerLabel` · 101: `function triggersSummary` · 112: `{`
- `lib/gamification.js` (178 стр.)
  - 11: `function totalStreakDays` · 15: `function getLevel` · 25: `function levelLine` · 30: `function checkLevelUp` · 41: `function weeklyBadges` · 49: `function calendarText` · 67: `function moodStats` · 75: `function recordMood` · 81: `function isOnVacation` · 86: `function startVacation` · 90: `function isPro` · 95: `function freeHabitLimit` · 99: `function freezeAllowance` · 105: `function canUseFreeze` · 111: `function markFreezeUsed` · 118: `function weekCompare` · 137: `function checkSavingsMilestone` · 150: `function getDayStage` · 158: `{`
- `lib/habit-metrics.js` (139 стр.)
  - 11: `function getTrackMode` · 18: `function isTimeHabit` · 22: `function isWeightHabit` · 26: `function isMoneyHabit` · 30: `function getMinutesPerDay` · 34: `function savedMinutes` · 38: `function formatMinutes` · 45: `function getMasturbationConsequence` · 53: `function weightProgress` · 66: `function formatHabitMetricBlock` · 93: `function formatElapsedShort` · 101: `function pluralDaysRu` · 110: `function mergeHabitConfig` · 126: `{`
- `lib/tones.js` (43 стр.)
  - 26: `function load` · 37: `function pickTone` · 42: `{ pickTone, load`
- `lib/visual.js` (79 стр.)
  - 33: `function streakHoldTier` · 48: `function readStreakHoldBuffer` · 58: `function bannerPath` · 65: `function readBannerBuffer` · 71: `{`

## tools

- `tools/project_map.py` (159 стр.)
  - 33: `def list_files` · 55: `def describe` · 84: `def symbols` · 98: `def build`
