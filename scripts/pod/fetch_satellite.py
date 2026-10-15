"""Textura satelital del terreno para el simulador web.

Descarga el mosaico Sentinel-2 cloudless 2016 de EOX (CC BY 4.0: "Sentinel-2 cloudless - https://s2maps.eu
by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016)") y lo reproyecta al espacio UV
del terreno exportado (u -4500..7500 m, v -6500..8020 m en el marco de la reticula girada 31 grados).

Uso: python3 fetch_satellite.py <salida.jpg> [lado_px=2048] [zoom=14]
"""
import io
import json
import math
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (research)"}
LAYER = os.environ.get("S2_LAYER", "s2cloudless_3857")   # 2016: CC BY 4.0; 2018+: CC BY-NC-SA 4.0
URL = "https://tiles.maps.eox.at/wmts/1.0.0/" + LAYER + "/default/g/{z}/{y}/{x}.jpg"
ORIGIN = (4.5981062, -74.0760391)
ROT = 31.0
U0, U1, V0, V1 = -4500.0, 7500.0, -6500.0, 8020.0
M_PER_DEG_LAT = 110574.0


def to_latlon(u, v):
    r = math.radians(ROT)
    mlon = 111320.0 * math.cos(math.radians(ORIGIN[0]))
    E = u * math.cos(r) + v * math.sin(r)
    N = -u * math.sin(r) + v * math.cos(r)
    return ORIGIN[0] + N / M_PER_DEG_LAT, ORIGIN[1] + E / mlon


def merc_px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def main():
    out = sys.argv[1]
    S = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
    z = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    corners = [to_latlon(u, v) for u in (U0, U1) for v in (V0, V1)]
    pts = [merc_px(la, lo, z) for la, lo in corners]
    x0 = int(min(p[0] for p in pts) // 256) - 1
    x1 = int(max(p[0] for p in pts) // 256) + 1
    y0 = int(min(p[1] for p in pts) // 256) - 1
    y1 = int(max(p[1] for p in pts) // 256) + 1
    W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    mosaic = np.zeros((H, W, 3), np.uint8)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            req = urllib.request.Request(URL.format(z=z, x=tx, y=ty), headers=UA)
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")
            mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(im)
    print("mosaico", W, H, "teselas", (x1 - x0 + 1) * (y1 - y0 + 1), flush=True)
    # reproyectar: fila r -> v = V1 - (r+0.5)/S*(V1-V0); columna c -> u = U0 + (c+0.5)/S*(U1-U0)
    cs = (np.arange(S) + 0.5) / S
    U = U0 + cs[None, :] * (U1 - U0)
    V = V1 - cs[:, None] * (V1 - V0)
    r = math.radians(ROT)
    mlon = 111320.0 * math.cos(math.radians(ORIGIN[0]))
    E = U * math.cos(r) + V * math.sin(r)
    N = -U * math.sin(r) + V * math.cos(r)
    lat = ORIGIN[0] + N / M_PER_DEG_LAT
    lon = ORIGIN[1] + E / mlon
    n = 256 * 2 ** z
    px = (lon + 180) / 360 * n - x0 * 256
    py = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n - y0 * 256
    # bilineal
    xf, yf = np.clip(px - 0.5, 0, W - 1.001), np.clip(py - 0.5, 0, H - 1.001)
    xi, yi = xf.astype(int), yf.astype(int)
    fx, fy = (xf - xi)[..., None], (yf - yi)[..., None]
    m = mosaic.astype(np.float32)
    img = (m[yi, xi] * (1 - fx) * (1 - fy) + m[yi, xi + 1] * fx * (1 - fy)
           + m[yi + 1, xi] * (1 - fx) * fy + m[yi + 1, xi + 1] * fx * fy)
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(out, quality=88, optimize=True)
    json.dump({"source": f"Sentinel-2 cloudless ({LAYER}), EOX IT Services GmbH", "zoom": z,
               "u": [U0, U1], "v": [V0, V1], "size": S}, open(os.path.splitext(out)[0] + ".json", "w"))
    a = img.clip(0, 255) / 255.0
    cloud = ((a.min(-1) > 0.55) & (a.max(-1) - a.min(-1) < 0.12)).mean()
    print("listo", out, os.path.getsize(out) // 1024, "KB", "nubes %.1f%%" % (cloud * 100))


if __name__ == "__main__":
    main()
