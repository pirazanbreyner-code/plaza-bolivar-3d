"""Describe los materiales PBR del simulador web en web/public/scene/scene.json a partir de
config.WEB_MATERIALS y del color medio de cada textura (web/public/scene/tex/info.json), sin volver a
exportar la geometria. Factor de color = tinte deseado / color medio lineal de la textura."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from plaza import config as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scene = os.path.join(ROOT, "web/public/scene/scene.json")
info = json.load(open(os.path.join(ROOT, "web/public/scene/tex/info.json")))
d = json.load(open(scene))
for key, (tex, tile, tint, pom, nrm) in C.WEB_MATERIALS.items():
    name = f"{key} (PBR)"
    avg = info[tex]["avg_linear"]
    d["materials"][name] = {
        "type": "pbr", "tex": tex, "tile": [tile, tile],
        "color": [round(t / max(a, 1e-3), 4) for t, a in zip(tint, avg)] if tint else [1, 1, 1],
        "pom": pom, "normalScale": nrm,
    }
for k, (tex, tile, tint, bay) in enumerate(C.WEB_CITY):
    avg = info[tex]["avg_linear"]
    d["materials"][f"Ciudad fachada {k}"] = {
        "type": "city", "tex": tex, "tile": [tile, tile], "bay": bay, "seed": k * 17.3,
        "color": [round(t / max(a, 1e-3), 4) for t, a in zip(tint, avg)],
    }
json.dump(d, open(scene, "w"), indent=1, ensure_ascii=False)
print("actualizado", scene, len(C.WEB_MATERIALS), "materiales PBR")
