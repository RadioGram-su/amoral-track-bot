# Episode 02, studio cut — «Куда летит твой «привет»?» (cinematic look)

Upgrade over the retro cut: PBR materials, SSR reflections, bloom, volumetric haze and light shafts,
motion blur, AgX "Punchy" grade, depth of field, thermal compositor pass; Hex v2 (glossy brass,
glowing iris, eyelids/blinks, stances); fast camera language (whip-orbit, FOV punches, exponential
pull-back); kinetic captions with keyword colours; beat-synced synthesised music and SFX.

Order: `vo/lines.txt` -> RHVoice (aleksandr-hq, -r 128 -t 110) -> timeline.json ->
`surf.py` (tunnel + reveal, frames 0-137) and `render_all.sh` (`short.py` shots: dive hall chip scale
heat cool power ret) -> `audio_short.py` (music/sfx/voice mix, -14 LUFS) -> `assemble_short.py`
(lanczos 2x, grade, grain, captions, h264). Render 540x960 EEVEE on CPU: ~5-10 s per frame.
Paths point at the session scratchpad; adjust ST before reuse.
