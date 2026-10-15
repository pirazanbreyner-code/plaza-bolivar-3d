"""Hoja de contacto con miniaturas de Poly Haven (se ejecuta en el pod).

Uso: python3 contact_sheet.py salida.jpg id1 id2 ...
"""
import io, sys, urllib.request
from PIL import Image, ImageDraw

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (blender research)"}
out, ids = sys.argv[1], sys.argv[2:]
W = 256
cols = 6
rows = (len(ids) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * (W + 22)), (30, 30, 30))
d = ImageDraw.Draw(sheet)
for i, a in enumerate(ids):
    url = f"https://cdn.polyhaven.com/asset_img/thumbs/{a}.png?width={W}&height={W}"
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read())).convert("RGB")
        im = im.resize((W, int(W * im.height / im.width)))
    except Exception as e:
        im = Image.new("RGB", (W, W), (90, 0, 0))
    x, y = (i % cols) * W, (i // cols) * (W + 22)
    sheet.paste(im.crop((0, 0, W, min(W, im.height))), (x, y + 22))
    d.text((x + 4, y + 4), a[:40], fill=(255, 255, 255))
sheet.save(out, quality=85)
print("ok", out, sheet.size)
