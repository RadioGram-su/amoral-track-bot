"""Synthesised retro music + SFX for episode 02 (all generated, no samples). Writes music.wav and sfx.wav."""
import json, wave, numpy as np

EP = '/tmp/claude-0/-home-user-amoral-track-bot/f91e2272-a479-5871-8b79-e1da23093bfd/scratchpad/ep02'
TL = json.load(open(f'{EP}/timeline.json', encoding='utf-8'))
SR = 44100; DUR = TL['total']; N = int(DUR * SR)
rng = np.random.default_rng(3)
S = {s['name']: s for s in TL['shots']}


def at(name, u): s = S[name]; return s['start'] + (s['end'] - s['start']) * u


def t_(d): return np.arange(int(d * SR)) / SR


def add(buf, start, sig, g=1.0):
    i = int(start * SR); j = min(i + len(sig), len(buf))
    if i < len(buf) and j > i: buf[i:j] += sig[:j - i] * g


def env(n, a=0.005, r=0.08):
    t = np.arange(n) / SR; e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4)); return e


def sq(f, d, duty=0.5): t = t_(d); return np.where((t * f) % 1 < duty, 1.0, -1.0)
def sine(f, d): return np.sin(2 * np.pi * f * t_(d))
def noise(d): return rng.uniform(-1, 1, int(d * SR))


def sweep(f0, f1, d):
    t = t_(d); f = np.linspace(f0, f1, len(t)); return np.sin(2 * np.pi * np.cumsum(f) / SR)


def note(m): return 440.0 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- music (chiptune, 112 bpm)
music = np.zeros(N); bpm = 112; beat = 60 / bpm; step = beat / 2
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [62, 67, 71])]   # Am F C G
t = 0.0; k = 0; end_music = S['end']['start']
while t < end_music:
    bass, chord = prog[(k // 8) % 4]
    if k % 2 == 0:
        sig = sq(note(bass - 12), step * 0.9, 0.5) * env(int(step * 0.9 * SR), 0.003, 0.18); add(music, t, sig, 0.22)
    arp = chord[k % 3] + (12 if (k // 3) % 2 else 0)
    sig = sq(note(arp), step * 0.6, 0.25) * env(int(step * 0.6 * SR), 0.002, 0.07); add(music, t, sig, 0.10)
    hh = noise(0.03) * env(int(0.03 * SR), 0.001, 0.01); add(music, t, hh, 0.10 if k % 2 else 0.05)
    if k % 4 == 0:
        kick = sweep(150, 45, 0.12) * env(int(0.12 * SR), 0.001, 0.05); add(music, t, kick, 0.45)
    t += step; k += 1
# end jingle
for i, m in enumerate([72, 76, 79, 84, 88]):
    add(music, end_music + 0.1 + i * 0.11, sq(note(m), 0.35, 0.25) * env(int(0.35 * SR), 0.002, 0.2), 0.18)
add(music, end_music + 0.75, sq(note(84), 1.2, 0.5) * env(int(1.2 * SR), 0.01, 0.6), 0.12)

# ---------------------------------------------------------------- sfx
sfx = np.zeros(N)
# typewriter blips for each dialog line
for s in TL['shots']:
    if not s['vstart']: continue
    n = len(s['text']); dur = s['vdur'] * 0.92
    for i in range(n):
        if s['text'][i] in ' .,—«»:': continue
        add(sfx, s['vstart'] + dur * i / n, sq(1300 + (i % 3) * 120, 0.018, 0.5) * env(int(0.018 * SR), 0.001, 0.008), 0.05)
# hook: message send pop + whoosh
tp = at('hook', 0.5)
add(sfx, tp, sweep(500, 1400, 0.12) * env(int(0.12 * SR), 0.002, 0.06), 0.35)
wh = noise(0.9) * np.sin(np.linspace(0, np.pi, int(0.9 * SR))) ** 2; add(sfx, tp + 0.05, wh, 0.22)
# outside: wind swell + dive zip
add(sfx, S['outside']['start'], noise(4.6) * np.sin(np.linspace(0, np.pi, int(4.6 * SR))) * 0.5, 0.18)
add(sfx, at('outside', 0.72), sweep(1800, 300, 0.35) * env(int(0.35 * SR), 0.005, 0.2), 0.3)
# hall/gpu/heat-inside: server hum
h0, h1 = S['hall']['start'], at('heat', 0.62)
th = t_(h1 - h0); hum = 0.5 * np.sin(2 * np.pi * 60 * th) + 0.3 * np.sin(2 * np.pi * 120 * th) + 0.15 * noise(h1 - h0)
add(sfx, h0, hum, 0.12)
# footsteps in hall
ts = S['hall']['start']; te = S['hall']['end']; tt = ts + 0.2
while tt < te:
    add(sfx, tt, noise(0.05) * env(int(0.05 * SR), 0.001, 0.015) + sine(140, 0.05) * env(int(0.05 * SR), 0.001, 0.02), 0.35); tt += 0.33
# packet zoom in hall
add(sfx, at('hall', 0.05), sweep(300, 1600, 1.2) * np.sin(np.linspace(0, np.pi, int(1.2 * SR))), 0.18)
# gpu: clanks as parts separate, combo chime, counter ticks
for i in range(6):
    tc = at('gpu', 0.13 + i * 0.065)
    add(sfx, tc, (sine(1800 + i * 210, 0.25) + 0.5 * sine(2900 + i * 150, 0.25)) * env(int(0.25 * SR), 0.001, 0.07), 0.18)
for i in range(18):
    add(sfx, at('gpu', 0.45 + i * 0.009), sq(2000, 0.02) * env(int(0.02 * SR), 0.001, 0.008), 0.06)
tc = at('gpu', 0.5)
add(sfx, tc, sq(note(84), 0.12, 0.25) * env(int(0.12 * SR), 0.001, 0.08), 0.25)
add(sfx, tc + 0.12, sq(note(91), 0.4, 0.25) * env(int(0.4 * SR), 0.001, 0.2), 0.25)
# heat: alarm, then cooling hiss
ta = S['heat']['start']; tb = at('heat', 0.3); i = 0
while ta < tb:
    add(sfx, ta, sq(880 if i % 2 == 0 else 660, 0.16, 0.5) * env(int(0.16 * SR), 0.002, 0.2), 0.12); ta += 0.18; i += 1
add(sfx, at('heat', 0.3), noise(1.6) * np.exp(-np.arange(int(1.6 * SR)) / SR / 0.6), 0.25)
add(sfx, at('heat', 0.62), noise(2.9) * np.sin(np.linspace(0, np.pi, int(2.9 * SR))) * 0.6, 0.2)
# power: electric crackle + energy bar blips
p0, p1 = S['power']['start'], S['power']['end']
cr = noise(p1 - p0) * (rng.random(int((p1 - p0) * SR)) < 0.03) * 1.0
cr = np.convolve(cr, np.ones(40) / 6, mode='same'); add(sfx, p0, cr, 0.35)
add(sfx, p0, sine(50, p1 - p0) * 0.5 + 0.3 * np.sign(sine(100, p1 - p0)) * 0.2, 0.1)
for i in range(11):
    add(sfx, at('power', 0.05 + i * 0.05), sq(note(60 + i * 2), 0.06, 0.5) * env(int(0.06 * SR), 0.001, 0.04), 0.12)
# return: whoosh back + notification ding
add(sfx, S['return']['start'], noise(1.2) * np.sin(np.linspace(0, np.pi, int(1.2 * SR))) ** 2, 0.2)
tn = at('return', 0.45)
add(sfx, tn, sine(note(88), 0.25) * env(int(0.25 * SR), 0.002, 0.12), 0.35)
add(sfx, tn + 0.13, sine(note(93), 0.5) * env(int(0.5 * SR), 0.002, 0.25), 0.35)


def write(name, x):
    x = np.clip(x, -1, 1); d = (x * 32000).astype(np.int16)
    with wave.open(f'{EP}/{name}', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())


write('music.wav', music * 0.9); write('sfx.wav', sfx * 0.9)
print('audio ok', DUR)
