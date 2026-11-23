# Episode 02 — «Как работают дата-центры ИИ» (PS1 style)

Pipeline used to produce the episode (all in the cloud container, no AI imagery):

1. Voice: `RHVoice-test -p aleksandr-hq -r 118 -t 108` per line of `voice/lines.txt`
   (apt: `rhvoice rhvoice-russian`; voice licence CC BY-SA 4.0, credit Artem Plaksin), then
   ffmpeg trim + compressor + loudnorm.
2. `timeline.json`: shot boundaries derived from voice durations (15 fps).
3. `ep02.py` (exec's `ps1lib.py`, the retro-console style kit): builds scenes and renders 360x640 frames.
   `blender -b --factory-startup -P ep02.py -- frames frames FIRST LAST` under `xvfb-run`.
4. `audio.py`: synthesised chiptune + SFX (typewriter blips, steps, alarms, chimes); `mix.sh` ducks
   music under the voice and normalises to -14 LUFS.
5. `assemble.sh`: per-frame 64-colour palette + Bayer dither, nearest x3 to 1080x1920, scanlines, 30 fps.

Paths inside the scripts point at the session scratchpad; adjust `EP` before reuse.
