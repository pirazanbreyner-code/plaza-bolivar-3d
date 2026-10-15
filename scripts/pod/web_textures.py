"""Texturas PBR para el simulador web (CC0, Poly Haven). Se ejecuta en una maquina con internet.

Por textura escribe, en <salida>/:
  <id>_diff.jpg   color (sRGB)
  <id>_nor.jpg    normal OpenGL (+Y), como la espera three.js
  <id>_arh.jpg    R = oclusion ambiental, G = rugosidad, B = altura (para parallax)
y <salida>/info.json con el color medio lineal y el tamano real de cada textura (para teñir).
Tambien descarga cielos HDRI (equirectangulares) a <salida>/hdri/.

Uso: python3 web_textures.py <salida> [res_principal=2048] [res_secundaria=1024]
"""
import io
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (blender research)"}
# texturas de mayor detalle (se ven de cerca o cubren mucha superficie)
PRINCIPALES = ["sandstone_blocks_08", "large_sandstone_blocks", "white_sandstone_blocks_02", "granite_tile_04", "asphalt_02",
               "brick_pavement_02", "yellow_plaster", "stone_tile_wall", "beige_wall_001"]
SECUNDARIAS = ["granite_tile_03", "red_sandstone_wall", "plastered_wall_04", "white_stucco",
               "concrete_tiles", "granite_tile", "clay_roof_tiles_02", "roof_slates_02", "dark_wood",
               # ciudad de fondo: ladrillo bogotano y estuco
               "red_brick", "brick_wall_09", "red_bricks_04", "painted_plaster_wall"]
HDRIS = {"kloofendal_overcast_puresky": ["4k", "1k"]}
MAPAS = {"diff": ["Diffuse"], "nor": ["nor_gl"], "rough": ["Rough"], "ao": ["AO"], "disp": ["Displacement"]}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()


def fetch_map(files, keys, res="2k"):
    for k in keys:
        if k in files and res in files[k]:
            d = files[k][res]
            fmt = "jpg" if "jpg" in d else "png"
            return Image.open(io.BytesIO(get(d[fmt]["url"])))
    return None


def to_gray(im, size):
    if im is None:
        return None
    a = np.asarray(im)
    if a.ndim == 3:
        a = a[..., 0]
    a = a.astype(np.float32)
    a /= 65535.0 if a.max() > 255 else 255.0
    return np.asarray(Image.fromarray((a * 255).clip(0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS),
                      dtype=np.float32) / 255.0


def main():
    out = sys.argv[1]
    r1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
    r2 = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    os.makedirs(out, exist_ok=True)
    info_path = os.path.join(out, "info.json")
    info = json.load(open(info_path)) if os.path.exists(info_path) else {}
    for tid in PRINCIPALES + SECUNDARIAS:
        R = r1 if tid in PRINCIPALES else r2
        if tid in info and info[tid].get("res") == R:
            print("ya existe", tid)
            continue
        files = json.loads(get(f"https://api.polyhaven.com/files/{tid}"))
        meta = json.loads(get(f"https://api.polyhaven.com/info/{tid}"))
        src_res = "4k" if R > 2048 else "2k"
        diff = fetch_map(files, MAPAS["diff"], src_res).convert("RGB").resize((R, R), Image.LANCZOS)
        diff.save(os.path.join(out, f"{tid}_diff.jpg"), quality=86, optimize=True)
        nor = fetch_map(files, MAPAS["nor"], src_res).convert("RGB").resize((R, R), Image.LANCZOS)
        nor.save(os.path.join(out, f"{tid}_nor.jpg"), quality=90, optimize=True)
        rough = to_gray(fetch_map(files, MAPAS["rough"], src_res), R)
        ao = to_gray(fetch_map(files, MAPAS["ao"], src_res), R)
        disp = to_gray(fetch_map(files, MAPAS["disp"], src_res), R)
        if ao is None:
            ao = np.ones((R, R), np.float32)
        if disp is None:
            disp = np.full((R, R), 0.5, np.float32)
        else:   # normalizar el rango de altura para aprovechar los 8 bits
            lo, hi = np.percentile(disp, 0.5), np.percentile(disp, 99.5)
            disp = ((disp - lo) / max(hi - lo, 1e-3)).clip(0, 1)
        arh = np.stack([ao, rough, disp], -1)
        Image.fromarray((arh * 255).round().astype(np.uint8)).save(os.path.join(out, f"{tid}_arh.jpg"),
                                                                    quality=90, optimize=True)
        a = np.asarray(diff, dtype=np.float32) / 255.0
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        dims = meta.get("dimensions") or [2000, 2000]
        info[tid] = {"res": R, "avg_linear": [round(float(x), 4) for x in lin.reshape(-1, 3).mean(0)],
                     "size_m": [round(dims[0] / 1000, 3), round(dims[1] / 1000, 3)],
                     "rough_mean": round(float(rough.mean()), 3) if rough is not None else None,
                     "authors": list((meta.get("authors") or {}).keys())}
        json.dump(info, open(info_path, "w"), indent=1)
        print("textura", tid, R, info[tid]["avg_linear"], flush=True)
    os.makedirs(os.path.join(out, "hdri"), exist_ok=True)
    for hid, ress in HDRIS.items():
        files = json.loads(get(f"https://api.polyhaven.com/files/{hid}"))
        for r in ress:
            p = os.path.join(out, "hdri", f"{hid}_{r}.hdr")
            if not os.path.exists(p):
                open(p, "wb").write(get(files["hdri"][r]["hdr"]["url"]))
            print("hdri", hid, r, os.path.getsize(p) // 1000, "KB", flush=True)
    print("listo")


if __name__ == "__main__":
    main()
