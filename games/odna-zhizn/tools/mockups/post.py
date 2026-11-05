"""
Пост-обработка мокапов: акварель «цвет = память», интерфейс поверх всех трёх стилей.

    python3 tools/mockups/post.py <mock_dir> <font.ttf>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

D = sys.argv[1]
FONT = sys.argv[2]
rng = np.random.default_rng(7)


def load(name, mode="RGB"):
    return np.asarray(Image.open(os.path.join(D, name)).convert(mode)).astype(np.float32) / 255.0


def save(arr, name):
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8)).save(os.path.join(D, name))


def value_noise(h, w, cell, octaves=4, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh, gw = max(2, int(h / cell) + 2), max(2, int(w / cell) + 2)
        g = r.random((gh, gw)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(im).astype(np.float32) / 255.0)
        tot += amp
        amp *= 0.5
        cell = max(1.5, cell / 2)
    return out / tot


def blur(arr, r):
    if arr.ndim == 2:
        im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
        return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0
    return np.stack([blur(arr[..., c], r) for c in range(arr.shape[2])], -1)


def sample(arr, dx, dy):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = np.clip(xx + dx, 0, w - 1.001)
    y = np.clip(yy + dy, 0, h - 1.001)
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    a = arr[y0, x0]
    b = arr[y0, x0 + 1]
    c = arr[y0 + 1, x0]
    d = arr[y0 + 1, x0 + 1]
    if arr.ndim == 2:
        fx, fy = fx[..., 0], fy[..., 0]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def lum(c):
    return c[..., 0] * 0.3 + c[..., 1] * 0.59 + c[..., 2] * 0.11


def paper_tex(h, w, base=(0.975, 0.955, 0.905)):
    g = value_noise(h, w, 3, 3, 1)
    big = value_noise(h, w, 160, 3, 2)
    fib = value_noise(h, w, 1.5, 1, 3)
    p = np.ones((h, w, 3), np.float32) * np.array(base, np.float32)
    p *= (0.955 + 0.045 * g + 0.03 * (big - 0.5) + 0.015 * (fib - 0.5))[..., None]
    return p


# ------------------------------------------------------------ акварель

def watercolor():
    col = load("wc_color.png")
    lines = load("wc_lines.png", "RGBA")
    h, w = col.shape[:2]
    hu, hv = [float(v) for v in open(os.path.join(D, "wc_hero.txt")).read().split()]
    # 1) упрощение в заливки
    im = Image.fromarray((col * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(7)).filter(ImageFilter.MedianFilter(5))
    flat = np.asarray(im).astype(np.float32) / 255.0
    # 2) дрожание руки — смещение заливки относительно линий
    dx = (value_noise(h, w, 90, 3, 11) - 0.5) * 9
    dy = (value_noise(h, w, 90, 3, 12) - 0.5) * 9
    wash = sample(flat, dx, dy)
    # 3) края пигмента темнее (вода сносит пигмент к краю)
    g = lum(wash)
    gx = np.abs(np.roll(g, 1, 1) - np.roll(g, -1, 1))
    gy = np.abs(np.roll(g, 1, 0) - np.roll(g, -1, 0))
    edge = np.clip((gx + gy) * 4.0, 0, 1)
    edge = blur(edge, 1.6)
    # 4) неравномерность заливки + грануляция
    turb = value_noise(h, w, 60, 4, 21)
    gran = value_noise(h, w, 2.0, 2, 22)
    pigment = 1.0 - wash  # «поглощение»
    pigment = pigment * (0.78 + 0.34 * turb[..., None]) * (0.9 + 0.2 * gran[..., None])
    pigment = pigment * (1.0 + 0.75 * edge[..., None])
    pigment = 0.65 * pigment + 0.35 * blur(pigment, 2.2)
    # 5) маска памяти: цвет вокруг героя и обжитой части, даль — набросок
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / w, yy / h
    n = value_noise(h, w, 70, 4, 31)
    blob_hero = np.exp(-(((nx - hu) / 0.55) ** 2 + ((ny - hv) / 0.42) ** 2))
    blob_village = np.exp(-(((nx - 0.72) / 0.42) ** 2 + ((ny - 0.62) / 0.22) ** 2))
    m = np.maximum(blob_hero, blob_village * 0.95) + (n - 0.5) * 0.55
    mask = np.clip((m - 0.32) * 7.0, 0, 1)
    rim = np.clip(1.0 - np.abs(m - 0.36) * 22.0, 0, 1)  # «затёк» по краю пятна
    mask_s = blur(mask, 1.2)
    # 6) набросок: серый лёгкий тон + штриховка в тенях
    shade = 1.0 - lum(col)
    hatch = ((xx + yy * 0.9) % 7.0 < 1.1).astype(np.float32) * np.clip((shade - 0.25) * 2.2, 0, 1)
    hatch2 = ((xx - yy * 1.1) % 9.0 < 1.0).astype(np.float32) * np.clip((shade - 0.5) * 2.5, 0, 1)
    sketch_tone = np.clip(shade * 0.22 + (hatch * 0.35 + hatch2 * 0.3) * (0.6 + 0.4 * gran), 0, 1)
    sketch = np.repeat(sketch_tone[..., None], 3, -1) * np.array([0.55, 0.55, 0.6], np.float32)
    pig = pigment * mask_s[..., None] + sketch * (1 - mask_s[..., None])
    pig = pig + rim[..., None] * 0.12 * mask_s[..., None] * pigment
    # 7) бумага × (1 - пигмент)
    paper = paper_tex(h, w)
    out = paper * np.clip(1.0 - pig, 0, 1)
    # 8) линии: внутри — тёмно-коричневая тушь, снаружи — графит
    la = lines[..., 3:4] * 0.85
    line_col = np.array([0.22, 0.15, 0.12], np.float32) * mask_s[..., None] + np.array([0.33, 0.33, 0.36], np.float32) * (1 - mask_s[..., None])
    out = out * (1 - la) + line_col * la
    # 9) лёгкая виньетка
    vig = 1.0 - 0.18 * (((nx - 0.5) * 1.3) ** 2 + ((ny - 0.5) * 1.0) ** 2)
    out *= vig[..., None]
    save(out, "wc_final.png")


# ------------------------------------------------------------ лаковая миниатюра: кракелюр, рамка

def lacquer():
    raw = load("lacquer_raw.png")
    h, w = raw.shape[:2]
    # глубина лака: лёгкая тёплая дымка и зерно
    gr = value_noise(h, w, 2.0, 2, 41)
    out = raw * (0.96 + 0.06 * gr[..., None])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / w, yy / h
    vig = np.clip(1.0 - 0.55 * (((nx - 0.5) * 1.5) ** 2 + ((ny - 0.5) * 1.2) ** 2), 0, 1)
    out *= vig[..., None]
    img = Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    gold = (214, 166, 74, 255)
    gold2 = (240, 200, 110, 255)
    # орнаментальная рамка: двойная линия + «завитки» в углах + бусины по сторонам
    m = 26
    d.rectangle([m, m, w - m, h - m], outline=gold, width=3)
    d.rectangle([m + 10, m + 10, w - m - 10, h - m - 10], outline=gold, width=1)
    for cx, cy, sx, sy in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
        for k in range(3):
            r = 38 - k * 11
            bbox = [cx + sx * 8 - r, cy + sy * 8 - r, cx + sx * 8 + r, cy + sy * 8 + r]
            start = {(1, 1): 0, (-1, 1): 90, (1, -1): 270, (-1, -1): 180}[(sx, sy)]
            d.arc(bbox, start, start + 90, fill=gold2, width=2)
        for k in range(5):
            a = math.radians(15 + k * 15)
            px = cx + sx * (52 * math.cos(a))
            py = cy + sy * (52 * math.sin(a))
            d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=gold)
    for k in range(18):
        y = m + 60 + k * (h - 2 * m - 120) / 17
        for x in (m + 5, w - m - 5):
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=gold)
    for k in range(9):
        x = m + 60 + k * (w - 2 * m - 120) / 8
        for y in (m + 5, h - m - 5):
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=gold)
    img.save(os.path.join(D, "lacquer_frame.png"))


# ------------------------------------------------------------ интерфейс поверх

def font(size):
    return ImageFont.truetype(FONT, size)


def wobbly_circle(d, cx, cy, r, color, width, frac=1.0, seed=0):
    pts = []
    n = int(120 * frac)
    rr = np.random.default_rng(seed)
    ph = rr.random() * 6
    for i in range(n + 1):
        a = -math.pi / 2 + math.tau * frac * i / 120
        q = r * (1 + 0.025 * math.sin(a * 3 + ph) + 0.012 * math.sin(a * 7 + ph))
        pts.append((cx + q * math.cos(a), cy + q * math.sin(a)))
    d.line(pts, fill=color, width=width, joint="curve")


def ui_watercolor(src, dst):
    img = Image.open(os.path.join(D, src)).convert("RGB")
    w, h = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ink = (52, 38, 32, 255)
    # возраст: кольцо года (карандаш) + надпись
    wobbly_circle(d, 74, 82, 44, (60, 60, 66, 90), 2, 1.0, 1)
    wobbly_circle(d, 74, 82, 44, (196, 92, 60, 230), 5, 0.62, 2)
    d.text((74, 80), "34", font=font(40), fill=ink, anchor="mm")
    d.text((132, 58), "года", font=font(30), fill=ink)
    d.text((132, 92), "лето · 7-я жизнь рода", font=font(22), fill=(90, 70, 60, 255))
    # тост воспоминания: акварельное пятно
    blob = Image.new("L", img.size, 0)
    bd = ImageDraw.Draw(blob)
    bd.rounded_rectangle([40, h - 190, w - 40, h - 70], 40, fill=255)
    blob = blob.filter(ImageFilter.GaussianBlur(10))
    tint = Image.new("RGBA", img.size, (232, 168, 120, 0))
    tint.putalpha(blob.point(lambda v: int(v * 0.42)))
    img = Image.alpha_composite(img.convert("RGBA"), tint)
    d.text((70, h - 172), "новое воспоминание", font=font(22), fill=(150, 80, 50, 255))
    d.text((70, h - 140), "«Первая рыбалка с сыном»", font=font(34), fill=ink)
    d.text((w - 70, h - 140), "+1 ♥", font=font(30), fill=(176, 64, 52, 255), anchor="ra")
    d.text((w / 2, h - 36), "тап — идти   ·   держи — вспомнить", font=font(20), fill=(90, 80, 76, 200), anchor="mm")
    img = Image.alpha_composite(img, ov).convert("RGB")
    img.save(os.path.join(D, dst))


def ui_paper(src, dst):
    img = Image.open(os.path.join(D, src)).convert("RGBA")
    w, h = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # бирка возраста: бумага на гвоздике, с тенью
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    tag = [(46, 52), (236, 44), (244, 140), (52, 150)]
    sd.polygon([(x + 6, y + 8) for x, y in tag], fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img, sh)
    d.polygon(tag, fill=(244, 233, 210, 255), outline=(200, 186, 160, 255))
    d.ellipse([136, 50, 150, 64], fill=(196, 150, 70, 255), outline=(120, 90, 40, 255))
    d.text((70, 76), "34 года", font=font(38), fill=(110, 30, 26, 255))
    d.text((72, 116), "лето", font=font(24), fill=(80, 60, 50, 255))
    # карточка воспоминания — вырезанная бумажка
    card = [(56, h - 214), (w - 60, h - 222), (w - 52, h - 92), (62, h - 84)]
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.polygon([(x + 7, y + 9) for x, y in card], fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(img, sh)
    d.polygon(card, fill=(247, 238, 218, 255))
    d.text((84, h - 196), "новое воспоминание", font=font(22), fill=(140, 60, 40, 255))
    d.text((84, h - 162), "«Первая рыбалка с сыном»", font=font(32), fill=(40, 30, 26, 255))
    d.text((w - 84, h - 124), "+1 ♥", font=font(28), fill=(160, 40, 36, 255), anchor="ra")
    img = Image.alpha_composite(img, ov).convert("RGB")
    img.save(os.path.join(D, dst))


def ui_lacquer(src, dst):
    img = Image.open(os.path.join(D, src)).convert("RGBA")
    w, h = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    gold = (226, 182, 92, 255)
    # медальон возраста
    d.ellipse([52, 52, 152, 152], fill=(12, 10, 10, 230), outline=gold, width=3)
    d.ellipse([60, 60, 144, 144], outline=(226, 182, 92, 140), width=1)
    d.arc([46, 46, 158, 158], -90, -90 + 220, fill=(200, 40, 30, 255), width=4)
    d.text((102, 100), "34", font=font(42), fill=gold, anchor="mm")
    d.text((172, 74), "года · лето", font=font(28), fill=gold)
    d.text((172, 108), "седьмое колено рода", font=font(20), fill=(200, 160, 90, 220))
    # свиток воспоминания
    d.rounded_rectangle([60, h - 220, w - 60, h - 96], 16, fill=(14, 10, 10, 235), outline=gold, width=2)
    d.rounded_rectangle([68, h - 212, w - 68, h - 104], 12, outline=(226, 182, 92, 110), width=1)
    d.text((w / 2, h - 186), "~ новое воспоминание ~", font=font(22), fill=(210, 160, 80, 255), anchor="mm")
    d.text((w / 2, h - 146), "«Первая рыбалка с сыном»", font=font(32), fill=(245, 225, 180, 255), anchor="mm")
    img = Image.alpha_composite(img, ov).convert("RGB")
    img.save(os.path.join(D, dst))


if __name__ == "__main__":
    watercolor()
    ui_watercolor("wc_final.png", "style1_watercolor.png")
    ui_paper("paper.png", "style2_paper.png")
    lacquer()
    ui_lacquer("lacquer_frame.png", "style3_lacquer.png")
    # «стандартный» подход для сравнения — чистый low-poly рендер без стилизации
    Image.open(os.path.join(D, "wc_color.png")).convert("RGB").save(os.path.join(D, "style0_standard.png"))
    print("post done")
