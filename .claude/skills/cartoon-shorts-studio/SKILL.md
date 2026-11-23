---
name: cartoon-shorts-studio
description: >
  Phone-first production pipeline for original 2D / 3D cartoon YouTube Shorts (also Reels / TikTok):
  idea and hook, original character bible with a consistent look, a unique art style, shot-by-shot
  storyboard with ready-to-paste prompts for image and video generators, voice, music, CapCut edit,
  cover, title, and upload with the right AI disclosure. Use whenever the user wants to make
  cartoons, animated shorts, AI animation, "мультики", "мультфильм", "2D", "3D", "анимация",
  "шортс", "Shorts", "Reels", "ролик с телефона", "персонаж", "рисовка", "стиль рисовки",
  "сделай мультик", "сценарий для шортса", or a series with a recurring character.
---

# Cartoon Shorts Studio

Goal: help the user ship original animated Shorts **from a phone**, fast and repeatedly, with a look
that is recognisably theirs. Answer in the user's language (usually Russian).

Pair with:
- `youtube`: hooks, titles, metadata, Shorts strategy, analytics (`/youtube shorts`, `/youtube hook`, `/youtube ideate`).
- `kling-ai`: exact Kling prompts, Element / Omni Reference for character consistency.
- `video-thumbnail`: covers (needs `GEMINI_API_KEY`).
- `remotion-best-practices`: the "animate with code" route (see Route B).

## Ground rules

1. **Original characters and worlds only.** Never recreate an existing franchise, its characters,
   names, logos, music or a specific studio's signature look (no "make it Pixar/Disney/Simpsons/
   Smeshariki", no named-artist imitation). Describe the *qualities* of a style instead
   (e.g. "soft clay texture, rounded shapes, warm rim light"). This also protects the channel from
   copyright strikes.
2. **Be honest about outcomes.** Nobody can guarantee a million views. Promise a process
   that raises the odds: strong hook, high retention, consistent series, frequent testing.
3. **Monetisation-safe.** YouTube does not monetise mass-produced, repetitive, low-effort
   ("inauthentic") content. Every episode needs a real story beat, a recurring character with
   personality, and variety. Turn on the "altered or synthetic content" label when footage
   looks realistic. Policies change: tell the user to check the current YouTube Partner Program
   rules before relying on them.
4. Prices, model names and app features change monthly. Name tools as options and tell the user
   to check current pricing and free tiers. Do not invent numbers.

## Step 0: gather (ask only what is missing)

- Niche or theme and target audience (kids vs. adults matters: "made for kids" limits comments and ads).
- Language of voice-over and captions.
- 2D or 3D, and any style preference. If none, offer 3 options from `references/styles.md`.
- Budget: free only / small subscription / paid generators OK.
- Phone: iOS or Android.

## Route A: AI generators on the phone (main route)

Deliver, in this order and in one message per step unless the user asks for everything at once:

1. **Series concept.** Channel name ideas, a one-line premise, a recurring hero with a flaw and a
   goal, 10 episode ideas, a repeatable format (same opening beat, same ending twist or loop).
2. **Character bible** (`references/character-bible.md`): fixed visual description (shape, colours
   as HEX, outfit, silhouette, one signature detail), personality, voice. Produce one **master
   prompt** for a front view plus a turnaround sheet (front / 3/4 / side / back) on a plain background.
   The user generates it once in an image tool and keeps that image as the reference for every shot.
3. **Script** 20–45 s (or up to the current Shorts limit when the story needs it):
   - 0–1.5 s: visual hook. Something strange, a question, or a moment of danger. No logo, no intro.
   - Every 2–4 s: a new beat or a cut.
   - Ending: a twist, punchline or seamless loop back to frame 1 (loops lift replays).
4. **Storyboard table**: shot #, duration (3–5 s), framing, action, dialogue/SFX, and two prompts per shot:
   an **image prompt** for the keyframe and a **motion prompt** for image-to-video. Always prepend the
   same style block and character block so every shot matches. Use `kling-ai` for Kling syntax.
5. **Voice and sound**: voice-over text with timing, voice character description for a TTS app, SFX list,
   music mood. Only use music the user has rights to (in-app libraries, or tracks they generated with a
   commercial licence).
6. **Edit plan for CapCut** (or another phone editor): 9:16, 1080×1920, cut order, speed ramps,
   zoom punches on beats, burned-in captions (big, 2–4 words at a time, safe zone away from the bottom UI),
   SFX on every action, the last frame matching the first for the loop.
7. **Packaging** via `youtube` metadata: 3 title options (under 50 characters, curiosity + clarity),
   description with 1–3 hashtags, cover frame idea, pinned comment that asks a question.
8. **After posting**: what to check in YouTube Studio after 1 hour, 24 hours and 72 hours (viewed vs.
   swiped away, average % viewed, replays) and what to change in the next episode.

Typical phone toolchain (offer as options, user picks):
- Keyframes and character: Gemini app image generation, ChatGPT images, Midjourney, Ideogram, Leonardo.
- Image-to-video: Kling app, Hailuo / MiniMax, Pika, Runway, Google Veo (Gemini / Flow), Sora app.
- Voice: ElevenLabs, CapCut text-to-speech. Music: CapCut library, Suno.
- Edit and captions: CapCut, VN, InShot.

## Route B: animate with code (Remotion, rendered in the cloud)

For motion-graphics cartoons, kinetic text, flat 2D vector characters, simple 3D (via `@remotion/three`),
or batch-producing series episodes from a template. Claude writes the composition, renders a 1080×1920 MP4,
and sends the file to the user's phone. Follow `remotion-best-practices` → `remotion-create` → `remotion-render`.
Rendering needs Node packages and a headless browser in the session; if the environment blocks that,
say so and fall back to Route A. Check `remotion-license` if the user's company is above the free-use
threshold.

## Route C: own 3D in Blender (no AI generators, rendered in the cloud)

For users who want fully original art. Claude models, shades and renders the scene with Blender's
Python API in the cloud container and sends the PNG/MP4 to the phone.

- Setup: `apt-get install -y blender xvfb` (Ubuntu 24.04 ships Blender 4.0). Render headless with
  `xvfb-run -a blender -b --factory-startup -P script.py -- OUTDIR`.
- House style "Living Blueprint" (`scripts/blueprint_style_frames.py`): graph-paper background,
  toon shading with 3 flat bands, halftone ink dots in shadows, Freestyle ink outlines, red hatched
  section cuts, exploded views with dash-dot centre lines, numbered callouts, bilingual RU/EN overlays.
  Mascot: Hex, a brass hex nut with one eye in the hole. Reuse the helpers (`toon`, `hatch`, `lathe`,
  `cut`, `part`/`pose`, `label`, `title`) for every new object.
- EEVEE + Freestyle renders a 1080×1920 frame in a few seconds on 4 CPUs; budget ~1 h CPU per 40 s clip.
- User-made assets: the user can sculpt on Android (e.g. Nomad Sculpt) and send `.glb`; import with
  `bpy.ops.import_scene.gltf` and apply the house materials.

## Quality checklist before posting

- [ ] Hook in the first 1.5 s works with the sound off.
- [ ] The same character looks the same in every shot.
- [ ] No shot longer than ~4 s without a change.
- [ ] Captions readable on a small screen, nothing important in the bottom 20 % or right edge.
- [ ] Ending loops or pays off.
- [ ] Original IP only; music rights clear; AI label set if realistic.
- [ ] Title and cover promise exactly what the video delivers.

## Growth rhythm (tell the user)

- Ship a series, not one-offs: same hero, same format, new situation.
- Post consistently (for example 1 per day for 30 days) and judge by trends across episodes, not single videos.
- Double down on the top 10 % of episodes: make sequels and variations of what worked.
- Repurpose every Short to Reels and TikTok.
