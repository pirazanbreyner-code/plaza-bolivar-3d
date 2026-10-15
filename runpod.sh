#!/usr/bin/env bash
# Render en un pod de Runpod (o cualquier Linux con GPU NVIDIA).
#
#   git clone https://github.com/pirazanbreyner-code/plaza-bolivar-3d.git && cd plaza-bolivar-3d && ./runpod.sh [ultra|final|final4k] [camaras]
#
# Ejemplos:
#   ./runpod.sh                       # las 4 camaras en calidad "ultra" (1920x1080, hasta 1536 muestras)
#   ./runpod.sh final4k               # las 4 camaras en 4K
#   ./runpod.sh ultra Cam_Referencia  # solo una camara
#
# Resultado: renders/detalle/*.png, blend/plaza_detalle.blend y el paquete resultados_<calidad>.tgz
set -euo pipefail
cd "$(dirname "$0")"
Q="${1:-ultra}"
CAMS="${2:-}"

echo "== GPU =="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || echo "(nvidia-smi no disponible)"

# librerias de sistema que necesita el modulo bpy (sin interfaz grafica)
if command -v apt-get >/dev/null; then
  (apt-get update -qq && apt-get install -y -qq libgl1 libegl1 libxi6 libxrender1 libxkbcommon0 \
     libsm6 libxxf86vm1 libxfixes3 libx11-6 >/dev/null) || echo "(aviso: no se pudieron instalar libs con apt)"
fi

# Python 3.13 + Blender 5.2.2 como modulo (bpy) en un entorno aislado
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
[ -x .venv/bin/python ] || uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -q bpy==5.2.2 pillow numpy

.venv/bin/python scripts/00_check_env.py            # debe listar la GPU (OPTIX o CUDA)
time .venv/bin/python scripts/build.py --stage detail --render "$Q" --device gpu ${CAMS:+--cams "$CAMS"}

tar czf "resultados_${Q}.tgz" renders/detalle/*_"${Q}".png blend/plaza_detalle.blend
echo "Listo: resultados_${Q}.tgz (descargalo desde el navegador de archivos de Runpod / JupyterLab)"
