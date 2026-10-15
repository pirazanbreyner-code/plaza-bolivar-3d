"""Cielo nublado (lluvia, niebla) para el simulador web, con el mismo formato que export_web.export_sky:
sky2_bg.jpg (4K, valor lineal = 8 * jpg^2.2) y sky2_env.hdr (1K, Radiance). Imprime la irradiancia
horizontal y el color del horizonte para calibrar la exposicion en el navegador.

Uso: .venv/bin/python scripts/web_sky.py <hdri_4k.hdr> <hdri_1k.hdr>
"""
import json
import os
import sys

import bpy  # noqa: F401  (lector de HDR)
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from export_web import write_rgbe  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web/public/scene")


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(buf)
    bpy.data.images.remove(im)
    px = buf.reshape(h, w, 4)[::-1, :, :3]
    return np.roll(px, w // 2, axis=1)


def irradiance(px):
    h, w, _ = px.shape
    el = np.pi / 2 - (np.arange(h) + 0.5) / h * np.pi
    wgt = (np.sin(el) * np.cos(el) * (el > 0))[:, None, None] * (np.pi / h) * (2 * np.pi / w)
    return (px * wgt).sum((0, 1))


big = load(sys.argv[1])
hor = big[big.shape[0] // 2 - big.shape[0] // 40: big.shape[0] // 2].reshape(-1, 3)
fog = [round(float(x), 4) for x in np.median(hor, axis=0)]
enc = np.power(np.clip(big / 8.0, 0, 1), 1 / 2.2)
Image.fromarray((enc * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "sky2_bg.jpg"), quality=88)
small = load(sys.argv[2])
write_rgbe(os.path.join(OUT, "sky2_env.hdr"), small.astype(np.float32))
E = irradiance(small)
print(json.dumps({"fogColor": fog, "E_horizontal": [round(float(x), 3) for x in E], "max": float(big.max())}))
