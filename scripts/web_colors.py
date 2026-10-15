"""Recalcula los factores de color de los materiales PBR en web/public/scene/scene.json a partir de
config.TEXTURES (tinte lineal deseado / color medio de la textura), sin volver a exportar la escena."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from plaza import config as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scene = os.path.join(ROOT, "web/public/scene/scene.json")
info = json.load(open(os.path.join(ROOT, C.ASSETS["info"])))
d = json.load(open(scene))
for key, (tex, tile, tint) in C.TEXTURES.items():
    name = f"{key} (PBR)"
    if name not in d["materials"]:
        continue
    avg = info[tex]["avg_linear"]
    d["materials"][name]["color"] = ([t / max(a, 1e-3) for t, a in zip(tint, avg)] if tint else [1, 1, 1])
    d["materials"][name]["tile"] = [tile, tile]
json.dump(d, open(scene, "w"), indent=1, ensure_ascii=False)
print("actualizado", scene)
