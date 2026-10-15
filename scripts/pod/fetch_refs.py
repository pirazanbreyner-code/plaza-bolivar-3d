"""Busca fotos de referencia en Wikimedia Commons y arma hojas de contacto (solo para consulta).

Uso: python3 fetch_refs.py /workspace/refs
"""
import io, json, os, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw

UA = {"User-Agent": "plaza-bolivar-3d/1.0 (research; blender model)"}
QUERIES = {
    "catedral": "Catedral Primada de Colombia fachada",
    "capitolio": "Capitolio Nacional de Colombia fachada Plaza de Bolivar",
    "justicia": "Palacio de Justicia Bogota Plaza de Bolivar",
    "lievano": "Palacio Lievano Bogota",
    "sagrario": "Capilla del Sagrario Bogota",
    "estatua": "Estatua Simon Bolivar Tenerani Plaza de Bolivar Bogota",
    "plaza": "Plaza de Bolivar Bogota",
}


def api(params):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA)))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "refs"
    os.makedirs(out, exist_ok=True)
    meta = {}
    for key, q in QUERIES.items():
        r = api({"action": "query", "format": "json", "generator": "search", "gsrsearch": q,
                 "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
                 "iiprop": "url|size|extmetadata", "iiurlwidth": 640})
        pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        ims, names = [], []
        for p in pages:
            ii = p.get("imageinfo", [{}])[0]
            th = ii.get("thumburl")
            if not th or not th.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
                continue
            try:
                im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(th, headers=UA)).read())).convert("RGB")
            except Exception:
                continue
            ims.append(im)
            names.append(p["title"])
            meta.setdefault(key, []).append({"title": p["title"], "url": ii.get("descriptionurl"),
                                             "thumb": th})
            if len(ims) >= 9:
                break
        if not ims:
            continue
        W, H = 420, 300
        sheet = Image.new("RGB", (3 * W, ((len(ims) + 2) // 3) * (H + 18)), (25, 25, 25))
        d = ImageDraw.Draw(sheet)
        for i, (im, n) in enumerate(zip(ims, names)):
            im.thumbnail((W, H))
            x, y = (i % 3) * W, (i // 3) * (H + 18)
            sheet.paste(im, (x, y + 18))
            d.text((x + 3, y + 3), f"{i}: {n[5:60]}", fill=(255, 255, 255))
        sheet.save(os.path.join(out, f"ref_{key}.jpg"), quality=82)
        print(key, len(ims), flush=True)
    json.dump(meta, open(os.path.join(out, "refs.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
