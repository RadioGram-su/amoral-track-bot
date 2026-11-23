"""Assemble the Short: frames + post FX + kinetic captions + audio -> 1080x1920 MP4."""
import json, os, subprocess

ST = '/tmp/claude-0/-home-user-amoral-track-bot/f91e2272-a479-5871-8b79-e1da23093bfd/scratchpad/studio'
TL = json.load(open(f'{ST}/timeline.json', encoding='utf-8'))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
Y, W, C, O = '#FFD23F', '#FFFFFF', '#7CF8FF', '#FF7A2A'
# per voice line: list of (text, colour, emphasis)
CH = {
    1: [('ТЫ ПИШЕШЬ НЕЙРОСЕТИ', W, 0), ('«ПРИВЕТ»', Y, 1)],
    2: [('…А ОН ЛЕТИТ', W, 0), ('СЮДА', Y, 1)],
    3: [('ЭТО ДАТА-ЦЕНТР', W, 0), ('НЕЙРОСЕТЕЙ', C, 1), ('РАЗМЕРОМ С КВАРТАЛ', W, 0)],
    4: [('ВНУТРИ —', W, 0), ('ТЫСЯЧИ ШКАФОВ', Y, 1), ('С СЕРВЕРАМИ', W, 0)],
    5: [('А В НИХ — ЧИПЫ', W, 0), ('ТРИЛЛИОНЫ', Y, 1), ('ОПЕРАЦИЙ В СЕКУНДУ', W, 0)],
    6: [('И ТАКИХ ЧИПОВ', W, 0), ('ДЕСЯТКИ ТЫСЯЧ', Y, 1)],
    7: [('ОНИ ТАК ГРЕЮТСЯ…', O, 0), ('ЧТО ВОЗДУХА МАЛО', O, 1)],
    8: [('…ПОЭТОМУ —', W, 0), ('ЖИДКОСТЬ', C, 1)],
    9: [('А ЭЛЕКТРИЧЕСТВА ЕСТ', W, 0), ('КАК НЕБОЛЬШОЙ', W, 0), ('ГОРОД', Y, 1)],
    10: [('И ВСЁ ЭТО —', W, 0), ('ЧТОБЫ ОТВЕТИТЬ', W, 0), ('НА ТВОЙ «ПРИВЕТ»', Y, 1)],
}
os.makedirs(f'{ST}/caps', exist_ok=True)
voice = TL['voice']; filters = []; n = 0
for idx, v in enumerate(voice):
    chunks = CH[v['i']]; total = sum(len(c[0]) for c in chunks)
    nxt = voice[idx + 1]['start'] if idx + 1 < len(voice) else TL['total']
    t = v['start']; end_all = min(nxt, v['start'] + v['dur'] + 0.6)
    for j, (txt, col, emph) in enumerate(chunks):
        d = v['dur'] * len(txt) / total
        a = t; b = (t + d) if j < len(chunks) - 1 else end_all
        t += d
        base = 92 if emph else 70
        size = min(base, int(960 / (0.66 * len(txt))))
        p = f'{ST}/caps/c{n}.txt'; open(p, 'w', encoding='utf-8').write(txt); n += 1
        fs = f"{size}*if(lt(t-{a:.3f},0.07),0.78+4.0*(t-{a:.3f}),if(lt(t-{a:.3f},0.15),1.06-0.75*(t-{a:.3f}-0.07),1))"
        filters.append(f"drawtext=fontfile={FONT}:textfile={p}:fontcolor={col}:borderw={8 if emph else 6}:bordercolor=black@0.95:"
                       f"shadowcolor=black@0.6:shadowx=0:shadowy=6:fontsize='{fs}':x=(w-text_w)/2:y=h*0.64-text_h/2:"
                       f"enable='between(t,{a:.3f},{b:.3f})'")
vf = ('[0:v]scale=1080:1920:flags=lanczos,unsharp=5:5:0.45,eq=contrast=1.04:saturation=1.1,'
      'rgbashift=rh=-2:bh=2,vignette=angle=PI/5,noise=alls=4:allf=t,' + ','.join(filters) + ',format=yuv420p[v]')
open(f'{ST}/caps/filter.txt', 'w', encoding='utf-8').write(vf)
os.makedirs(f'{ST}/all', exist_ok=True)
for d_ in ('anim', 'frames'):
    for fn in os.listdir(f'{ST}/{d_}'):
        if fn.endswith('.png'):
            dst = f'{ST}/all/{fn}'
            if os.path.lexists(dst): os.remove(dst)
            os.symlink(f'{ST}/{d_}/{fn}', dst)
nf = len([x for x in os.listdir(f'{ST}/all') if x.endswith('.png')])
print('frames', nf, 'captions', n)
subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-framerate', '30', '-i', f'{ST}/all/f%04d.png', '-i', f'{ST}/mix.wav',
                '-filter_complex_script', f'{ST}/caps/filter.txt', '-map', '[v]', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
                '-crf', '17', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest',
                f'{ST}/hex_datacenter_short_ru.mp4'], check=True)
print(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', '-of', 'default=nw=1', f'{ST}/hex_datacenter_short_ru.mp4']).decode())
