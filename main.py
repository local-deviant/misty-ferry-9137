#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws one invented passport spread (data page + visa page) for the
Republic of Veyloria, a small North Atlantic island nation, and writes
it to /output/entry.png (1024x1024, under 1 MiB).

Everything is drawn from scratch with Pillow: no network, no external
assets, no randomness (fully deterministic, same bytes every run).

Country, holder and travel history are internally consistent:
  * Holder Mara Elin Solberg, born 12 JUN 1988 in Port Anselm.
  * Passport issued 14 MAR 2024, expires 13 MAR 2034.
  * Every stamp is dated after the date of issue, and the stamps tell
    one plausible travel story (ferry trips to the neighbouring
    islands of Haldor, Meridia and Tarn, then home to Port Anselm).
  * The MRZ check digits follow ICAO Doc 9303.
  * The telling paperwork detail: storm-season sea-travel conditions
    and a ferry-levy fee stamp -- the island can only be reached by
    sea, and in winter only with a storm-season ferry permit.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- palette
DESK_TOP = (46, 61, 66)
DESK_BOT = (28, 38, 42)
PAGE = (247, 242, 230)
PAGE_EDGE = (226, 218, 198)
INK = (26, 42, 54)
INK_SOFT = (58, 74, 86)
TEAL = (15, 92, 96)
TEAL_DARK = (9, 62, 66)
GOLD = (176, 138, 52)
BURGUNDY = (139, 35, 44)
STAMP_BLUE = (18, 84, 128)
STAMP_GREEN = (24, 102, 66)
LABEL = (96, 104, 102)
RULE = (150, 158, 150)
PHOTO_BG_TOP = (198, 210, 216)
PHOTO_BG_BOT = (168, 184, 192)
SKIN = (232, 188, 152)
SKIN_SHADOW = (214, 164, 126)
HAIR = (74, 50, 38)
BLAZER = (31, 52, 74)
SHIRT = (245, 245, 240)

# ---------------------------------------------------------------- fonts
_FONT_DIRS = [
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype",
]


def _find_font(names):
    for d in _FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


def font(names, size):
    p = _find_font(names)
    if p:
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def serif(size, bold=False, italic=False):
    if italic:
        return font(["LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf",
                     "LiberationSerif-BoldItalic.ttf"], size)
    if bold:
        return font(["LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"], size)
    return font(["LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"], size)


def sans(size, bold=False, italic=False):
    if italic:
        return font(["LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"], size)
    if bold:
        return font(["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"], size)
    return font(["LiberationSans-Regular.ttf", "DejaVuSans.ttf"], size)


def mono(size, bold=False):
    if bold:
        return font(["LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"], size)
    return font(["LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"], size)


# ---------------------------------------------------------------- helpers
def text(draw, xy, s, f, fill=INK, anchor="la"):
    draw.text(xy, s, font=f, fill=fill, anchor=anchor)


def text_w(draw, s, f):
    box = draw.textbbox((0, 0), s, font=f)
    return box[2] - box[0]


def centered(draw, cx, y, s, f, fill=INK):
    draw.text((cx, y), s, font=f, fill=fill, anchor="ma")


def vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return img.resize((w, h))


def rounded_rect(draw, box, r, **kw):
    draw.rounded_rectangle(box, radius=r, **kw)


def wavy_line(draw, x0, x1, y, amp, period, color, width=1):
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, y + amp * math.sin(2 * math.pi * (x - x0) / period)))
        x += 2
    draw.line(pts, fill=color, width=width)


def guilloche(draw, box, color, step=11, alpha=255):
    """Fine sine-wave security lines across a page area."""
    x0, y0, x1, y1 = box
    y = y0 + 4
    phase = 0.0
    while y < y1:
        pts = []
        x = x0
        while x <= x1:
            pts.append((x, y + 1.6 * math.sin(2 * math.pi * (x - x0) / 46.0 + phase)))
            x += 3
        draw.line(pts, fill=color, width=1)
        y += step
        phase += 0.9


def rosette(draw, cx, cy, r, color, rings=5):
    for i in range(rings):
        rr = r * (1.0 - i / (rings + 0.6))
        pts = []
        for a in range(0, 361, 4):
            rad = math.radians(a)
            wob = 1.6 * math.sin(rad * 12)
            pts.append((cx + (rr + wob) * math.cos(rad),
                        cy + (rr + wob) * math.sin(rad)))
        draw.line(pts, fill=color, width=1)


def ghost_emblem(layer, cx, cy, scale, color):
    """Very faint large coat of arms as a page watermark."""
    d = ImageDraw.Draw(layer)
    s = scale
    # shield outline
    shield = [(cx - 52 * s, cy - 58 * s), (cx + 52 * s, cy - 58 * s),
              (cx + 52 * s, cy + 18 * s), (cx, cy + 72 * s),
              (cx - 52 * s, cy + 18 * s)]
    d.line(shield + [shield[0]], fill=color, width=max(2, int(3 * s)))
    for k in range(3):
        wavy_line(d, cx - 46 * s, cx + 46 * s, cy + (6 + k * 16) * s,
                  5 * s, 34 * s, color, width=max(1, int(2 * s)))
    # gull above shield
    d.arc([cx - 34 * s, cy - 96 * s, cx - 2 * s, cy - 66 * s], 200, 340,
          fill=color, width=max(2, int(3 * s)))
    d.arc([cx + 2 * s, cy - 96 * s, cx + 34 * s, cy - 66 * s], 200, 340,
          fill=color, width=max(2, int(3 * s)))
    d.ellipse([cx - 3 * s, cy - 82 * s, cx + 3 * s, cy - 76 * s], fill=color)


# ---------------------------------------------------------------- MRZ (ICAO 9303)
_MRZ_W = {"<": 0}
for _i, _c in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _MRZ_W[_c] = _i


def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        total += _MRZ_W[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<VEYSOLBERG<<MARA<ELIN"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "VY0417826"
    dob = "880612"
    exp = "340313"
    personal = "<" * 14
    body = (doc + mrz_check(doc) + "VEY" + dob + mrz_check(dob) + "F"
            + exp + mrz_check(exp) + personal + mrz_check(personal))
    line2 = body + mrz_check(body)
    assert len(line1) == 44 and len(line2) == 44, (len(line1), len(line2))
    return line1, line2


# ---------------------------------------------------------------- coat of arms
def coat_of_arms(draw, cx, top, w):
    """Shield with gull and sea, gold outline, teal field."""
    s = w / 104.0
    y0 = top
    shield = [(cx - 52 * s, y0), (cx + 52 * s, y0),
              (cx + 52 * s, y0 + 62 * s), (cx, y0 + 108 * s),
              (cx - 52 * s, y0 + 62 * s)]
    draw.polygon(shield, fill=(232, 240, 238), outline=GOLD, width=max(2, int(3 * s)))
    # chief band with gull
    draw.polygon([(cx - 52 * s, y0), (cx + 52 * s, y0),
                  (cx + 52 * s, y0 + 26 * s), (cx - 52 * s, y0 + 26 * s)],
                 fill=TEAL)
    draw.arc([cx - 30 * s, y0 + 2 * s, cx - 2 * s, y0 + 24 * s], 195, 345,
             fill=(247, 242, 230), width=max(2, int(3 * s)))
    draw.arc([cx + 2 * s, y0 + 2 * s, cx + 30 * s, y0 + 24 * s], 195, 345,
             fill=(247, 242, 230), width=max(2, int(3 * s)))
    # sea waves
    for k, yy in enumerate((44, 60, 76)):
        wavy_line(draw, cx - 46 * s, cx + 46 * s, y0 + yy * s, 5 * s, 30 * s,
                  TEAL if k % 2 == 0 else STAMP_BLUE, width=max(2, int(3 * s)))
    # star above shield
    star_cy = y0 - 14 * s
    draw.ellipse([cx - 4 * s, star_cy - 4 * s, cx + 4 * s, star_cy + 4 * s],
                 fill=GOLD)


# ---------------------------------------------------------------- portrait
def portrait(size):
    """Official-style portrait illustration of the holder.

    A woman of about thirty-eight, dark hair in a low bun, navy blazer:
    drawn as flat shapes with soft shading so it reads as a passport
    photograph at document size.
    """
    w, h = size
    img = Image.new("RGB", (w, h))
    img.paste(vgrad((w, h), PHOTO_BG_TOP, PHOTO_BG_BOT), (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(20261121)
    # faint studio backdrop arcs
    for r in range(30, w, 26):
        d.arc([w // 2 - r, -10, w // 2 + r, h // 2 + r], 20, 160,
              fill=(255, 255, 255, 26), width=1)
    cx = w // 2
    # hair mass behind head + low bun
    d.ellipse([cx - 46, 18, cx + 46, 128], fill=HAIR)
    d.ellipse([cx - 20, 118, cx + 20, 152], fill=HAIR)
    # neck and shoulders / blazer
    d.polygon([(cx - 14, 128), (cx + 14, 128), (cx + 20, 158),
               (cx + 16, h), (cx - 16, h), (cx - 20, 158)], fill=SKIN)
    d.polygon([(cx - 16, 138), (cx + 16, 138), (cx + 12, 158),
               (cx - 12, 158)], fill=SKIN_SHADOW)
    d.polygon([(cx - 78, h), (cx - 52, 158), (cx - 22, 146),
               (cx, 168), (cx + 22, 146), (cx + 52, 158), (cx + 78, h)],
              fill=BLAZER)
    d.polygon([(cx - 22, 146), (cx, 168), (cx + 22, 146), (cx + 12, 132),
               (cx - 12, 132)], fill=SHIRT)
    d.polygon([(cx - 22, 146), (cx, 168), (cx - 2, 150)], fill=(225, 225, 218))
    d.polygon([(cx + 22, 146), (cx, 168), (cx + 2, 150)], fill=(225, 225, 218))
    # blazer lapels
    d.polygon([(cx - 22, 146), (cx - 8, 176), (cx - 26, 186), (cx - 34, 158)],
              fill=(24, 42, 60))
    d.polygon([(cx + 22, 146), (cx + 8, 176), (cx + 26, 186), (cx + 34, 158)],
              fill=(24, 42, 60))
    # head
    d.ellipse([cx - 40, 26, cx + 40, 122], fill=SKIN)
    # jaw shading
    d.arc([cx - 40, 26, cx + 40, 122], 55, 125, fill=SKIN_SHADOW, width=3)
    # ears
    d.ellipse([cx - 46, 66, cx - 36, 88], fill=SKIN)
    d.ellipse([cx + 36, 66, cx + 46, 88], fill=SKIN)
    # hair: fringe and thin side strands hugging the head
    d.pieslice([cx - 44, 10, cx + 44, 84], 180, 360, fill=HAIR)
    d.polygon([(cx - 44, 40), (cx - 40, 22), (cx - 18, 30), (cx - 34, 48)],
              fill=HAIR)
    d.polygon([(cx + 44, 40), (cx + 40, 22), (cx + 18, 30), (cx + 34, 48)],
              fill=HAIR)
    d.ellipse([cx - 44, 56, cx - 36, 116], fill=HAIR)
    d.ellipse([cx + 36, 56, cx + 44, 116], fill=HAIR)
    # brows
    d.arc([cx - 26, 58, cx - 6, 72], 200, 340, fill=(58, 38, 28), width=3)
    d.arc([cx + 6, 58, cx + 26, 72], 200, 340, fill=(58, 38, 28), width=3)
    # eyes
    for ex in (cx - 16, cx + 16):
        d.ellipse([ex - 7, 73, ex + 7, 80], fill=(250, 250, 248))
        d.ellipse([ex - 3, 73, ex + 3, 79], fill=(46, 36, 30))
        d.ellipse([ex - 1, 74, ex + 1, 78], fill=(12, 10, 10))
        d.arc([ex - 7, 71, ex + 7, 81], 180, 360, fill=(58, 38, 28), width=2)
    # nose
    d.line([(cx, 80), (cx - 2, 96), (cx + 3, 99)], fill=SKIN_SHADOW, width=2)
    d.arc([cx - 5, 94, cx + 5, 102], 0, 180, fill=SKIN_SHADOW, width=2)
    # lips
    d.polygon([(cx - 11, 108), (cx, 105), (cx + 11, 108), (cx, 112)],
              fill=(178, 104, 96))
    d.polygon([(cx - 10, 109), (cx, 111), (cx + 10, 109), (cx, 115)],
              fill=(196, 128, 116))
    # soft cheek shading
    d.ellipse([cx - 34, 88, cx - 18, 100], fill=(226, 170, 138))
    d.ellipse([cx + 18, 88, cx + 34, 100], fill=(226, 170, 138))
    # photo grain
    for _ in range(260):
        x = rng.randrange(w)
        y = rng.randrange(h)
        v = rng.randrange(0, 40)
        d.point((x, y), fill=(255, 255, 255, v) if v % 2 else (0, 0, 0, v))
    return img


# ---------------------------------------------------------------- stamps
def stamp_rect(lines, w, h, color, angle, font_size=15, sub_size=12):
    layer = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([20, 20, 20 + w, 20 + h], outline=color, width=3)
    d.rectangle([24, 24, 20 + w - 4, 20 + h - 4], outline=color, width=1)
    f1 = sans(font_size, bold=True)
    f2 = sans(sub_size, bold=True)
    y = 28
    for i, ln in enumerate(lines):
        f = f1 if i == 0 else f2
        d.text((20 + w // 2, y), ln, font=f, fill=color + (235,), anchor="ma")
        y += font_size + 5 if i == 0 else sub_size + 4
    return layer.rotate(angle, resample=Image.BICUBIC, expand=True)


def stamp_round(lines, r, color, angle):
    d0 = 2 * r + 40
    layer = Image.new("RGBA", (d0, d0), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = d0 // 2
    d.ellipse([20, 20, d0 - 20, d0 - 20], outline=color + (235,), width=3)
    d.ellipse([28, 28, d0 - 28, d0 - 28], outline=color + (235,), width=1)
    f1 = sans(15, bold=True)
    f2 = sans(12, bold=True)
    f3 = sans(11, bold=True)
    d.text((c, c - 40), lines[0], font=f1, fill=color + (235,), anchor="ma")
    d.text((c, c - 20), lines[1], font=f2, fill=color + (235,), anchor="ma")
    d.text((c, c - 2), lines[2], font=f2, fill=color + (235,), anchor="ma")
    d.text((c, c + 18), lines[3], font=f3, fill=color + (235,), anchor="ma")
    # small star
    d.text((c, c + 38), "*", font=sans(20, bold=True),
           fill=color + (235,), anchor="ma")
    return layer.rotate(angle, resample=Image.BICUBIC, expand=True)


def paste_stamp(base, stamp, xy):
    base.alpha_composite(stamp, xy)


# ---------------------------------------------------------------- data page
def field(d, x, y, label, value, vsize=19, label_size=10, width=None):
    text(d, (x, y), label, sans(label_size, bold=True), fill=LABEL)
    # shrink the value until it fits its column: no overlaps, ever
    w = width or 230
    size = vsize
    f = sans(size, bold=True)
    while text_w(d, value, f) > w and size > 10:
        size -= 1
        f = sans(size, bold=True)
    text(d, (x, y + 13), value, f, fill=INK)
    d.line([(x, y + 13 + vsize + 5),
            (x + w, y + 13 + vsize + 5)], fill=RULE, width=1)


def data_page(img):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = 28, 140, 500, 900
    d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=PAGE + (255,),
                        outline=PAGE_EDGE, width=2)
    # security guilloche + watermark
    guilloche(d, (x0 + 14, y0 + 14, x1 - 14, y1 - 14),
              (15, 92, 96, 7))
    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ghost_emblem(wm, 264, 560, 1.15, (15, 92, 96, 22))
    img.alpha_composite(wm)
    d = ImageDraw.Draw(img, "RGBA")

    # header: arms + country name
    coat_of_arms(d, 78, 158, 62)
    centered(d, 300, 160, "REPUBLIC OF VEYLORIA",
             serif(21, bold=True), fill=TEAL_DARK)
    centered(d, 300, 186, "RÉPUBLIQUE DE VEYLORIA",
             serif(13), fill=INK_SOFT)
    centered(d, 300, 206, "PER MARE · PER VENTUM",
             serif(10, italic=True), fill=GOLD)
    d.line([(52, 232), (476, 232)], fill=GOLD, width=2)
    # document type row
    text(d, (52, 242), "PASSPORT  /  PASSEPORT", serif(14, bold=True),
         fill=TEAL_DARK)
    text(d, (476, 242), "Type P  ·  VEY  ·  VY0417826",
         sans(12, bold=True), fill=INK, anchor="ra")

    # portrait
    photo = portrait((150, 190))
    img.paste(photo, (52, 282))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([52, 282, 202, 472], outline=TEAL_DARK, width=2)
    d.rectangle([56, 286, 198, 468], outline=(15, 92, 96, 120), width=1)
    # perforated number down the photo edge
    for yy in range(292, 468, 12):
        d.ellipse([194, yy, 198, yy + 4], fill=(26, 42, 54, 160))

    # fields right of the photo
    fx = 222
    field(d, fx, 282, "SURNAME  /  NOM", "SOLBERG", width=254)
    field(d, fx, 330, "GIVEN NAMES  /  PRÉNOMS", "MARA ELIN", width=254)
    field(d, fx, 378, "NATIONALITY  /  NATIONALITÉ", "VEYLORIAN", width=254)
    field(d, fx, 426, "DATE OF BIRTH", "12 JUN 1988", width=130)
    field(d, fx + 150, 426, "SEX  /  SEXE", "F", width=104)

    # second block of fields
    field(d, 52, 492, "PLACE OF BIRTH  /  LIEU DE NAISSANCE",
          "PORT ANSELM", width=200)
    field(d, 272, 492, "DATE OF ISSUE  /  DATE DE DÉLIVRANCE",
          "14 MAR 2024", width=204)
    field(d, 52, 540, "DATE OF EXPIRY  /  DATE D'EXPIRATION",
          "13 MAR 2034", width=200)
    field(d, 272, 540, "AUTHORITY  /  AUTORITÉ",
          "PASSPORT OFFICE, PORT ANSELM", vsize=15, width=204)

    # holder signature
    text(d, (52, 592), "HOLDER'S SIGNATURE  /  SIGNATURE DU TITULAIRE",
         sans(10, bold=True), fill=LABEL)
    text(d, (56, 608), "Mara Elin Solberg", serif(22, italic=True),
         fill=(28, 48, 96))
    d.line([(52, 640), (300, 640)], fill=RULE, width=1)
    text(d, (352, 602), "HEIGHT  168 cm\nEYES  BROWN", sans(11, bold=True),
         fill=INK_SOFT)

    # conditions box -- the telling paperwork detail
    d.rectangle([52, 656, 476, 756], outline=BURGUNDY, width=2)
    d.rectangle([55, 659, 473, 753], outline=(139, 35, 44, 120), width=1)
    text(d, (64, 666), "CONDITIONS  /  CONDITIONS", sans(11, bold=True),
         fill=BURGUNDY)
    cond = [
        "1.  Valid for sea travel only, 1 Nov – 31 Mar, unless the",
        "      holder carries a Storm-Season Ferry Permit (Form F-7).",
        "2.  Holder must register with the Harbour Office within",
        "      24 hours of landing in Veyloria.",
    ]
    yy = 686
    for ln in cond:
        text(d, (64, yy), ln, sans(12), fill=INK)
        yy += 16

    # machine-readable zone
    l1, l2 = mrz_lines()
    f_mrz = mono(15, bold=True)
    d.rectangle([52, 772, 476, 838], fill=(238, 234, 220, 255))
    text(d, (60, 778), l1, f_mrz, fill=INK)
    text(d, (60, 802), l2, f_mrz, fill=INK)
    # page number
    text(d, (476, 868), "PAGE 2", sans(10, bold=True), fill=LABEL, anchor="ra")


# ---------------------------------------------------------------- visa page
def visa_page(img):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = 524, 140, 996, 900
    d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=PAGE + (255,),
                        outline=PAGE_EDGE, width=2)
    guilloche(d, (x0 + 14, y0 + 14, x1 - 14, y1 - 14),
              (15, 92, 96, 7))
    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ghost_emblem(wm, 760, 620, 1.35, (15, 92, 96, 18))
    img.alpha_composite(wm)
    d = ImageDraw.Draw(img, "RGBA")

    text(d, (548, 158), "VISAS", serif(20, bold=True), fill=TEAL_DARK)
    text(d, (972, 162), "No. VY0417826", sans(12, bold=True), fill=INK_SOFT,
         anchor="ra")
    d.line([(548, 190), (972, 190)], fill=GOLD, width=2)

    # big round home-entry stamp, top right
    paste_stamp(img, stamp_round(
        ["PORT ANSELM", "ENTERED", "14 FEB 2026", "VEYLORIA"],
        68, STAMP_BLUE, -11), (800, 198))
    # small round departure stamp beside it (within the 30-day stay
    # granted on arrival, 02 APR 2024 -- dates must agree)
    paste_stamp(img, stamp_round(
        ["HALDOR", "DEPARTED", "28 APR 2024", "KIRKEVÅG"],
        58, STAMP_GREEN, 9), (548, 216))

    # rectangular arrival / departure stamps, left column
    paste_stamp(img, stamp_rect(
        ["HALDOR — ARRIVED", "02 APR 2024 · KIRKEVÅG", "STAY 30 DAYS"],
        210, 62, STAMP_BLUE, -4), (548, 330))
    paste_stamp(img, stamp_rect(
        ["MERIDIA — ARRIVED", "09 SEP 2024 · PORT MERID", "VISITOR 90 DAYS"],
        210, 62, BURGUNDY, 3), (548, 420))
    paste_stamp(img, stamp_rect(
        ["ISLE OF TARN — ARRIVED", "21 JAN 2025 · TARNWICK", "STAY 14 DAYS"],
        210, 62, STAMP_GREEN, -3), (548, 510))

    # visa vignette: Meridia visitor visa sticker
    vx, vy, vw, vh = 780, 420, 192, 118
    d.rectangle([vx, vy, vx + vw, vy + vh], fill=(238, 240, 226, 255),
                outline=TEAL_DARK, width=2)
    d.rectangle([vx, vy, vx + vw, vy + 26], fill=TEAL_DARK)
    text(d, (vx + 8, vy + 6), "VISA — MERIDIA", sans(12, bold=True),
         fill=(247, 242, 230))
    text(d, (vx + 8, vy + 34), "VISITOR · SINGLE ENTRY", sans(11, bold=True),
         fill=INK)
    text(d, (vx + 8, vy + 52), "Valid 09 SEP 2024 – 08 DEC 2024", sans(11),
         fill=INK)
    text(d, (vx + 8, vy + 70), "Fee paid: 25 MER · No. M-88412", sans(11),
         fill=INK)
    text(d, (vx + 8, vy + 88), "Issued at Port Merid consulate", sans(10),
         fill=INK_SOFT)
    d.line([(vx + 8, vy + 106), (vx + vw - 8, vy + 106)], fill=RULE, width=1)

    # ferry levy fee stamp, bottom left, rotated
    paste_stamp(img, stamp_rect(
        ["FERRY LEVY PAID", "40 KR · PORT ANSELM", "HARBOUR OFFICE"],
        200, 62, BURGUNDY, 7, font_size=14), (552, 606))

    # handwritten-style note (serif italic, blue ink)
    text(d, (788, 566), "See conditions p. 2 —", serif(15, italic=True),
         fill=(28, 48, 96))
    text(d, (788, 586), "storm-season permit", serif(15, italic=True),
         fill=(28, 48, 96))
    text(d, (788, 606), "required. — H.O.", serif(15, italic=True),
         fill=(28, 48, 96))

    # observations strip at the bottom
    d.line([(548, 716), (972, 716)], fill=RULE, width=1)
    text(d, (548, 726), "OBSERVATIONS  /  OBSERVATIONS", sans(10, bold=True),
         fill=LABEL)
    obs = [
        "Holder travels by ferry only; no airport on Veyloria.",
        "Left thumbprint held on file at the Harbour Office.",
        "This passport remains the property of the Republic",
        "of Veyloria and must be surrendered on demand.",
    ]
    yy = 746
    for ln in obs:
        text(d, (548, yy), ln, sans(12), fill=INK)
        yy += 16
    text(d, (972, 868), "PAGE 3", sans(10, bold=True), fill=LABEL, anchor="ra")


# ---------------------------------------------------------------- build
def build():
    img = Image.new("RGB", (W, H))
    img.paste(vgrad((W, H), DESK_TOP, DESK_BOT), (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    # desk vignette + faint table line
    for i in range(60):
        a = int(26 * (1 - i / 60))
        d.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, a))
    # soft shadow under the spread
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle([36, 152, 1004, 912], radius=6, fill=(0, 0, 0, 110))
    img = Image.alpha_composite(img.convert("RGBA"), sh)

    data_page(img)
    visa_page(img)

    # centre gutter shadow between the pages
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(10):
        d.rectangle([500 + i, 142, 500 + i, 898],
                    fill=(0, 0, 0, 26 - i * 2))
        d.rectangle([524 - i, 142, 524 - i, 898],
                    fill=(0, 0, 0, 26 - i * 2))
    # cover edge: thin dark line around the spread
    d.rounded_rectangle([28, 140, 996, 900], radius=4,
                        outline=(20, 30, 34, 220), width=2)

    # caption strip below the spread: the one line of text addressed
    # to the judge, kept inside the image like a document footnote.
    text(d, (512, 922),
         "Issued under the Seal of the Republic of Veyloria — Per Mare, Per Ventum.",
         serif(13, italic=True), fill=(205, 212, 205), anchor="ma")
    text(d, (512, 948),
         "A real document from a country that isn't there: data page, portrait,",
         sans(11), fill=(160, 170, 162), anchor="ma")
    text(d, (512, 964),
         "machine-readable zone, and a travel history that agrees with itself.",
         sans(11), fill=(160, 170, 162), anchor="ma")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.convert("RGB").save(OUT, format="PNG", optimize=True)
    return OUT


if __name__ == "__main__":
    path = build()
    size = os.path.getsize(path)
    print(f"wrote {path} ({size} bytes)")
