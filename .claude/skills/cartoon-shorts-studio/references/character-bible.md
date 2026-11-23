# Character bible template

Fill this once per recurring character. Prepend the **Character block** to every shot prompt,
right after the style block, and attach the master image as a reference wherever the generator
allows it (for example Kling Element / Omni Reference, or "use this image as reference" in image apps).

```
NAME:
ROLE IN SERIES: (hero / sidekick / rival)
ONE-LINE PERSONALITY: (flaw + desire, e.g. "brave but clumsy fox who wants to be a famous chef")
CATCHPHRASE / SIGNATURE REACTION:
VOICE: (age, pitch, pace, accent, mood)

VISUAL
- Species / body type:
- Proportions: (e.g. head = 1/3 of height, short legs)
- Silhouette hook: (what makes it recognisable as a black silhouette)
- Colours (HEX): main ___ , secondary ___ , accent ___
- Face: (eye shape and colour, brows, mouth)
- Outfit / accessories: (keep the same every episode)
- Signature detail: (scar, patch, hat, glowing tail ...)

CHARACTER BLOCK (paste into prompts):
"<name>, a <species/body> with <proportions>, <colours with HEX>, <face>, wearing <outfit>,
<signature detail>, same character design in every shot"
```

## Master image prompt (front view)

`<STYLE BLOCK>, <CHARACTER BLOCK>, full body, front view, neutral pose, plain light grey background, even lighting, character design sheet`

## Turnaround sheet prompt

`<STYLE BLOCK>, <CHARACTER BLOCK>, character turnaround sheet, front view, three-quarter view, side view, back view, same scale, plain background, no text`

## Expression sheet prompt

`<STYLE BLOCK>, <CHARACTER BLOCK>, expression sheet, 6 expressions: happy, angry, surprised, sad, sly, scared, head and shoulders, plain background`

## Consistency tips

- Regenerate until the master image is right; then never change it.
- Keep prompts short around the character: long scene descriptions make the model drift.
- Generate the keyframe image first, then animate it (image-to-video) instead of text-to-video.
- If a shot drifts, re-run with the master image attached and the character block moved to the start.
