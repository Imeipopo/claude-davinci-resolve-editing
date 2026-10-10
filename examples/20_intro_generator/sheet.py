import json, os, sys
from PIL import Image, ImageDraw, ImageFont

rows = json.load(open(sys.argv[1]))
H = 420
CARD_PAD = 16
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public', 'fonts', 'NotoSansTC.ttf')
font = ImageFont.truetype(FONT, 26)
font.set_variation_by_axes([700])
small = ImageFont.truetype(FONT, 21)
small.set_variation_by_axes([400])
cards = []
for r in rows:
    im = Image.open(r['file']).convert('RGB')
    w = round(im.width * H / im.height)
    im = im.resize((w, H), Image.LANCZOS)
    cw = max(w, 330) + CARD_PAD * 2
    card = Image.new('RGB', (cw, H + CARD_PAD * 2 + 104), '#1B1D21')
    card.paste(im, (CARD_PAD, CARD_PAD))
    d = ImageDraw.Draw(card)
    y = H + CARD_PAD + 10
    d.text((CARD_PAD, y), r['title'], font=font, fill='#FFFFFF')
    d.text((CARD_PAD, y + 36), ' / '.join(r['labels'][:2]), font=small, fill='#C9CDD3')
    d.text((CARD_PAD, y + 64), ' / '.join(r['labels'][2:]) + ('　（有重抽）' if r['rerolls'] else ''), font=small, fill='#C9CDD3')
    cards.append(card)
MAXW = 2400
lines, cur, cw = [], [], 0
for c in cards:
    if cur and cw + c.width > MAXW:
        lines.append(cur); cur, cw = [], 0
    cur.append(c); cw += c.width
if cur:
    lines.append(cur)
W = max(sum(c.width for c in l) for l in lines)
sheet = Image.new('RGB', (W, sum(max(c.height for c in l) for l in lines)), '#1B1D21')
y = 0
for l in lines:
    x = 0
    for c in l:
        sheet.paste(c, (x, y)); x += c.width
    y += max(c.height for c in l)
sheet.save(sys.argv[2])
print(sys.argv[2], sheet.size)
