#!/usr/bin/env bash
# Regenera todo el proyecto: entorno, datos, massing, detalle y renders.
# Uso: ./build.sh [preview|final]   (por defecto: preview)
set -euo pipefail
cd "$(dirname "$0")"
Q="${1:-preview}"
if [ ! -x .venv/bin/python ]; then
  uv venv .venv --python 3.13
  uv pip install --python .venv/bin/python bpy==5.2.2 pillow numpy
fi
PY=.venv/bin/python
$PY scripts/00_check_env.py                       # dispositivos de Cycles + render de prueba
[ -f references/data/dem_bogota.npz ] || $PY scripts/fetch_data.py
$PY scripts/build.py --stage massing --render test    # volumenes -> blend/plaza_massing.blend
$PY scripts/build.py --stage detail --render "$Q"     # detalle  -> blend/plaza_detalle.blend
