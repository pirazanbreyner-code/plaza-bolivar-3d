"""Descarga los datos geograficos usados por la escena (reproducible).

1. Elevacion: AWS Terrain Tiles (formato terrarium, zoom 13, ~19 m/pixel; fuente SRTM/otros)
   https://registry.opendata.aws/terrain-tiles/  ->  references/data/dem_bogota.npz
2. Huellas de edificios de OpenStreetMap (via Overture Maps 2026-09-23.1) ya extraidas en
   references/osm/*.geojson (licencia ODbL, (c) colaboradores de OpenStreetMap).

Uso: .venv/bin/python scripts/fetch_data.py
"""
import io, math, os, urllib.request
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z = 13
LAT = (4.53, 4.68)
LON = (-74.13, -73.98)
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def main():
    from PIL import Image
    x0, y0 = tile_xy(LAT[1], LON[0], Z)
    x1, y1 = tile_xy(LAT[0], LON[1], Z)
    xs = range(int(x0), int(x1) + 1)
    ys = range(int(y0), int(y1) + 1)
    rows = []
    for ty in ys:
        row = []
        for tx in xs:
            url = URL.format(z=Z, x=tx, y=ty)
            data = urllib.request.urlopen(url, timeout=60).read()
            im = np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float64)
            elev = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768
            row.append(elev)
            print("tile", Z, tx, ty, "min/max", elev.min().round(1), elev.max().round(1))
        rows.append(np.hstack(row))
    dem = np.vstack(rows).astype(np.float32)
    # georreferencia: pixel (i,j) -> lat/lon del centro del pixel (Web Mercator)
    n = 2 ** Z * 256
    px0, py0 = xs[0] * 256, ys[0] * 256
    out = os.path.join(ROOT, "references", "data", "dem_bogota.npz")
    np.savez_compressed(out, dem=dem, z=Z, px0=px0, py0=py0, n=n)
    print("guardado", out, dem.shape)


if __name__ == "__main__":
    main()
