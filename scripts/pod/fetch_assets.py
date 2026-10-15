"""Descarga texturas PBR (CC0, Poly Haven) y el HDRI del cielo. Se ejecuta en una maquina con internet.

Uso: python3 fetch_assets.py /workspace/assets [res_texturas=2k] [res_hdri=8k]
Licencia de los recursos: CC0 (https://polyhaven.com/license).
"""
import json, os, sys, urllib.request

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (blender research)"}
TEXTURES = ["sandstone_blocks_08", "sandstone_blocks_04", "stone_tile_wall", "concrete_pavement",
            "pavement_03", "stone_pavers", "asphalt_02", "painted_plaster_wall", "white_stucco",
            "clay_roof_tiles_02", "roof_slates_02", "dark_wood", "aerial_grass_rock"]
MAPS = {"Diffuse": "diff", "nor_gl": "nor", "Rough": "rough", "Displacement": "disp", "AO": "ao"}
HDRI = "kloofendal_48d_partly_cloudy_puresky"


def get_json(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA)))


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets"
    res = sys.argv[2] if len(sys.argv) > 2 else "2k"
    hres = sys.argv[3] if len(sys.argv) > 3 else "8k"
    os.makedirs(os.path.join(out, "tex"), exist_ok=True)
    os.makedirs(os.path.join(out, "hdri"), exist_ok=True)
    for t in TEXTURES:
        files = get_json(f"https://api.polyhaven.com/files/{t}")
        for key, short in MAPS.items():
            if key not in files or res not in files[key]:
                continue
            fmt = "jpg" if "jpg" in files[key][res] else "png"
            url = files[key][res][fmt]["url"]
            p = os.path.join(out, "tex", f"{t}_{short}_{res}.{fmt}")
            download(url, p)
        print("textura", t, "ok", flush=True)
    files = get_json(f"https://api.polyhaven.com/files/{HDRI}")
    for r in (hres, "2k"):
        url = files["hdri"][r]["hdr"]["url"]
        p = os.path.join(out, "hdri", f"{HDRI}_{r}.hdr")
        download(url, p)
        print("hdri", r, os.path.getsize(p) // 1_000_000, "MB", flush=True)
    info = get_json(f"https://api.polyhaven.com/info/{HDRI}")
    json.dump(info, open(os.path.join(out, "hdri", f"{HDRI}_info.json"), "w"), indent=1)
    print("listo")


if __name__ == "__main__":
    main()
