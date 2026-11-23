"""Beat-synced music + SFX for the studio Short (fully synthesised). Writes music.wav, sfx.wav, mix.wav."""
import json, wave, subprocess, numpy as np

ST = '/tmp/claude-0/-home-user-amoral-track-bot/f91e2272-a479-5871-8b79-e1da23093bfd/scratchpad/studio'
TL = json.load(open(f'{ST}/timeline.json', encoding='utf-8'))
SR = 44100; DUR = TL['total']; N = int(DUR * SR) + SR
rng = np.random.default_rng(7)
SH = TL['shots']


def T(name, off=0.0): return SH[name]['start'] + off
def tt(d): return np.arange(int(d * SR)) / SR


def add(buf, start, sig, g=1.0):
    i = int(start * SR); j = min(i + len(sig), len(buf))
    if 0 <= i < len(buf) and j > i: buf[i:j] += sig[:j - i] * g


def env(n, a=0.005, r=0.1): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
def sine(f, d): return np.sin(2 * np.pi * f * tt(d))
def saw(f, d): t = tt(d); return 2 * ((t * f) % 1) - 1
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def smooth(x, k): return np.convolve(x, np.ones(k) / k, mode='same') if k > 1 else x
def note(m): return 440.0 * 2 ** ((m - 69) / 12)


def sweep(f0, f1, d, wave_='sine'):
    f = np.geomspace(max(f0, 1), max(f1, 1), int(d * SR)); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) if wave_ == 'sine' else 2 * ((ph / (2 * np.pi)) % 1) - 1


def whoosh(d=0.5, bright=6):
    n = noise(d); lo = smooth(n, bright); shape = np.sin(np.linspace(0, np.pi, len(n))) ** 1.5
    return (n - lo) * 0.4 * shape + lo * 1.5 * shape


def impact(d=1.2):
    sub = sweep(90, 32, d) * env(int(d * SR), 0.002, 0.35)
    crack = noise(0.25) * env(int(0.25 * SR), 0.001, 0.05)
    out = sub.copy(); out[:len(crack)] += crack * 0.6; return out


# ---------------------------------------------------------------- music: 128 bpm synthwave/techno
music = np.zeros(N); bpm = 128; beat = 60 / bpm; s16 = beat / 4
prog = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]   # Am F C G
DROP = 2.6; BREAK0, BREAK1 = T('heat'), T('cool'); OUT0 = T('ret')
k = 0; t = 0.0
while t < DUR:
    bar = int(t / (beat * 4)); bass, chord = prog[bar % 4]
    full = (t >= DROP and not (BREAK0 <= t < BREAK1))
    lite = t >= OUT0
    if k % 4 == 0 and full:   # kick
        add(music, t, sweep(140, 42, 0.22) * env(int(0.22 * SR), 0.001, 0.09), 0.9 if not lite else 0.55)
    if k % 4 == 2 and full:   # offbeat hat
        add(music, t, (noise(0.05) - smooth(noise(0.05), 3)) * env(int(0.05 * SR), 0.001, 0.015), 0.35)
    if k % 8 == 4 and full and not lite:   # clap
        add(music, t, smooth(noise(0.12), 2) * env(int(0.12 * SR), 0.001, 0.04), 0.35)
    if t >= DROP:   # rolling bass 16ths
        f = note(bass - 12 + (12 if k % 4 == 2 else 0))
        b = smooth(saw(f, s16 * 0.9), 6) * env(int(s16 * 0.9 * SR), 0.003, 0.08)
        add(music, t, b, 0.32 if not (BREAK0 <= t < BREAK1) else 0.12)
    if k % 2 == 0:   # arp
        m = chord[(k // 2) % 3] + 12 * ((k // 6) % 2)
        a = smooth(saw(note(m), s16 * 1.6), 3) * env(int(s16 * 1.6 * SR), 0.002, 0.09)
        add(music, t, a, 0.07 if t < DROP else 0.09)
    if k % 16 == 0:   # pad
        for m in chord:
            p = smooth(saw(note(m) * 1.003, beat * 4), 20) + smooth(saw(note(m) * 0.997, beat * 4), 20)
            p *= np.minimum(1, np.linspace(0, 6, len(p))) * np.minimum(1, np.linspace(6, 0, len(p)))
            add(music, t, p, 0.035)
    t += s16; k += 1
# riser into the drop
r = sweep(150, 1800, DROP - 0.2, 'saw') * np.linspace(0, 1, int((DROP - 0.2) * SR)) ** 2
add(music, 0.2, smooth(r, 4), 0.12)
add(music, 0.2, whoosh(DROP - 0.2, 40) * np.linspace(0, 1, int((DROP - 0.2) * SR)), 0.25)

# ---------------------------------------------------------------- sfx
sfx = np.zeros(N)
for i in range(26):   # tunnel ring ticks
    add(sfx, 0.1 + i * 0.1, sine(2400, 0.02) * env(int(0.02 * SR), 0.001, 0.006), 0.05)
cuts = [2.15] + [SH[k_]['start'] for k_ in ('dive', 'hall', 'chip', 'scale', 'heat', 'cool', 'power', 'ret')]
for c in cuts:
    add(sfx, c - 0.25, whoosh(0.5), 0.5)
for c in (2.6, T('dive', 1.55), T('chip', 0.3), T('scale', 0.05), T('cool', 0.05)):
    add(sfx, c, impact(), 0.7)
add(sfx, 2.6, noise(1.5) * env(int(1.5 * SR), 0.001, 0.4), 0.18)   # crash
for i in range(7):   # chip parts separating
    add(sfx, T('chip', 0.3 + i * 0.16), (sine(1700 + 230 * i, 0.3) + 0.4 * sine(2900 + 170 * i, 0.3)) * env(int(0.3 * SR), 0.001, 0.08), 0.14)
add(sfx, T('chip'), sine(120, SH['chip']['end'] - SH['chip']['start']) * 0.4 + 0.2 * smooth(noise(SH['chip']['end'] - SH['chip']['start']), 30), 0.12)
add(sfx, T('scale'), sweep(40, 160, 2.4) * np.sin(np.linspace(0, np.pi, int(2.4 * SR))), 0.35)   # scale swell
h0, h1 = SH['heat']['start'], SH['heat']['end']; ta = h0; i = 0
while ta < h1 - 0.1:   # siren
    add(sfx, ta, smooth(saw(780 if i % 2 == 0 else 590, 0.22), 4) * env(int(0.22 * SR), 0.005, 0.3), 0.07); ta += 0.25; i += 1
add(sfx, h0, (noise(h1 - h0) - smooth(noise(h1 - h0), 8)) * 0.5, 0.06)   # sizzle
add(sfx, T('cool', 0.05), noise(1.6) * env(int(1.6 * SR), 0.01, 0.5), 0.3)   # hiss
for i in range(14):   # liquid blips
    add(sfx, T('cool', 0.2 + i * 0.11), sweep(300 + 80 * (i % 5), 900 + 60 * (i % 4), 0.06) * env(int(0.06 * SR), 0.002, 0.03), 0.12)
p0, p1 = SH['power']['start'], SH['power']['end']
cr = noise(p1 - p0) * (rng.random(int((p1 - p0) * SR)) < 0.02); add(sfx, p0, smooth(cr, 30) * 5, 0.25)
add(sfx, p0, sweep(55, 110, p1 - p0) * 0.5, 0.15)
r0 = SH['ret']['start']
add(sfx, r0 + 0.42, sine(note(96), 0.3) * env(int(0.3 * SR), 0.001, 0.1), 0.25)
add(sfx, r0 + 0.47, sine(note(88), 0.25) * env(int(0.25 * SR), 0.002, 0.12), 0.35)
add(sfx, r0 + 0.6, sine(note(93), 0.5) * env(int(0.5 * SR), 0.002, 0.25), 0.35)
add(sfx, r0 + 0.75, sweep(300, 1200, 0.15) * env(int(0.15 * SR), 0.002, 0.08), 0.3)   # jump boop
add(sfx, r0 + 1.12, sweep(900, 250, 0.12) * env(int(0.12 * SR), 0.002, 0.06), 0.25)   # land
add(sfx, DUR - 0.45, whoosh(0.5, 10) * np.linspace(0, 1, int(0.5 * SR)), 0.5)   # loop whoosh


def wr(name, x, ch=1):
    x = np.clip(x, -1, 1); d = (x * 32000).astype(np.int16)
    with wave.open(f'{ST}/{name}', 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())


m_ = music / max(1e-6, np.abs(music).max()) * 0.8; s_ = sfx / max(1e-6, np.abs(sfx).max()) * 0.8
wr('music.wav', m_); wr('sfx.wav', s_)
v = TL['voice']; ins = []; chains = []
for i, x in enumerate(v):
    ins += ['-i', f'{ST}/vo/l{x["i"]}.wav']; chains.append(f'[{i + 2}:a]adelay={int(x["start"] * 1000)}:all=1[v{i}]')
fc = ';'.join(chains) + ';' + ''.join(f'[v{i}]' for i in range(len(v))) + f'amix=inputs={len(v)}:normalize=0[voice];'
fc += '[voice]asplit=2[vo][sc];[0:a][sc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=250[duck];'
fc += f'[duck]volume=0.55[m];[1:a]volume=0.8[s];[vo]volume=1.15[vv];[vv][m][s]amix=inputs=3:normalize=0,atrim=0:{DUR},loudnorm=I=-14:TP=-1.2:LRA=8'
subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', f'{ST}/music.wav', '-i', f'{ST}/sfx.wav'] + ins +
               ['-filter_complex', fc, '-ar', '44100', '-ac', '2', f'{ST}/mix.wav'], check=True)
print('mix ok', DUR)
