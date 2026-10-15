#!/usr/bin/env bash
# Prepara web/public/scene a partir de la salida de scripts/export_web.py.
#
#   web/build_scene.sh <carpeta web_out>
#
# Pasos: soldar vertices, simplificar el terreno al 30 %, reordenar y cuantizar (KHR_mesh_quantization),
# comprimir con gzip y guardar en base64 (.b64.txt): los artifacts no sirven .glb ni .hdr y asi la
# pagina no necesita WebAssembly. El navegador lo decodifica en src/main.js (fetchBinary).
set -euo pipefail
SRC="$(cd "${1:?uso: web/build_scene.sh <web_out>}" && pwd)"
cd "$(dirname "$0")"
OUT=public/scene
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT/tex"

cp "$SRC/scene.json" "$SRC/sky_bg.jpg" "$SRC/minimapa.jpg" "$OUT/"
cp "$SRC"/tex/*.jpg "$OUT/tex/"

GT="npx --no-install gltf-transform"
for f in nucleo ciudad terreno; do
  $GT weld "$SRC/$f.glb" "$TMP/$f.w.glb"
  if [ "$f" = terreno ]; then
    $GT simplify "$TMP/$f.w.glb" "$TMP/$f.s.glb" --ratio 0.3 --error 0.0004
    mv "$TMP/$f.s.glb" "$TMP/$f.w.glb"
  fi
  $GT reorder "$TMP/$f.w.glb" "$TMP/$f.r.glb"
  $GT quantize "$TMP/$f.r.glb" "$TMP/$f.q.glb"
  gzip -9 -n -c "$TMP/$f.q.glb" | base64 -w 0 > "$OUT/$f.glb.b64.txt"
done
gzip -9 -n -c "$SRC/sky_env.hdr" | base64 -w 0 > "$OUT/sky_env.hdr.b64.txt"

# factores de color segun config.TEXTURES (por si cambiaron los tintes despues de exportar)
../.venv/bin/python ../scripts/web_colors.py || echo "(aviso: no se recalcularon los colores)"
du -sh "$OUT"
