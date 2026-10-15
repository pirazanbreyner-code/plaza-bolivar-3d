"""Hojas de contacto de texturas candidatas de Poly Haven (CC0), filtradas por etiquetas.

Uso: python3 texture_catalog.py <salida> grupo1 grupo2 ...   (grupos definidos en GROUPS)
"""
import io, json, os, sys, urllib.request
from PIL import Image, ImageDraw

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (blender research)"}
GROUPS = {
    "piedra": ["sandstone", "ashlar", "limestone", "stone wall", "blocks", "masonry", "castle"],
    "estuco": ["plaster", "stucco", "painted", "facade"],
    "suelo": ["pavement", "paving", "slab", "tiles", "flagstone", "cobblestone", "sidewalk", "concrete floor"],
    "asfalto": ["asphalt", "road", "tarmac"],
    "tejado": ["roof", "tiles roof", "slate"],
}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    assets = json.loads(get("https://api.polyhaven.com/assets?t=textures"))
    json.dump(assets, open(os.path.join(out, "catalogo.json"), "w"))
    for g in sys.argv[2:]:
        keys = GROUPS[g]
        sel = []
        for aid, a in assets.items():
            text = " ".join([aid, a.get("name", "")] + a.get("tags", []) + a.get("categories", [])).lower()
            if any(k in text for k in keys):
                sel.append(aid)
        sel.sort()
        sel = sel[:80]
        n = len(sel); cols = 8; rows = (n + cols - 1) // cols; S = 220
        sheet = Image.new("RGB", (cols * S, rows * (S + 22)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, aid in enumerate(sel):
            try:
                im = Image.open(io.BytesIO(get(f"https://cdn.polyhaven.com/asset_img/thumbs/{aid}.png?width=256&height=256"))).convert("RGB")
                im = im.resize((S, S))
                x, y = (i % cols) * S, (i // cols) * (S + 22)
                sheet.paste(im, (x, y))
                dims = assets[aid].get("dimensions")
                d.text((x + 4, y + S + 4), f"{aid[:26]} {dims[0]/1000:.1f}m" if dims else aid[:30], fill=(240, 230, 200))
            except Exception as e:
                print("fallo", aid, e)
        sheet.save(os.path.join(out, f"hoja_{g}.jpg"), quality=85)
        print(g, n, "->", ", ".join(sel))


if __name__ == "__main__":
    main()
