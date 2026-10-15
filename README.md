# Plaza de Bolívar (Bogotá) en 3D: Blender + Cycles

Reconstrucción 3D reproducible de la Plaza de Bolívar con Blender 5.2 (módulo `bpy`, sin interfaz)
y render con trazado de rayos (Cycles). El modelo usa datos geográficos reales y fotos de referencia:

- **Planta y fachadas**: huellas de OpenStreetMap (vía Overture Maps), ±1–2 m.
- **Cerros Orientales** (Monserrate, Guadalupe y la cadena completa): modelo de elevación real
  (AWS Terrain Tiles, unos 19 m/píxel) en un área de 12 × 14,5 km.
- **Ciudad de fondo**: 1.474 edificios de OSM extruidos.
- **Sol**: posición astronómica real para la fecha y hora de cada cámara, en la retícula girada 31°.
- **Materiales procedurales**: sillería de arenisca, losas, estuco, bronce, pizarra, teja, vidrio.
  También bruma atmosférica, cielo físico con nubes, personas y palomas.

Qué es exacto y qué es aproximado: **[APROXIMACIONES.md](APROXIMACIONES.md)**.

## Estructura

```
scripts/
  00_check_env.py        # dispositivos de Cycles (GPU/CPU) + render de prueba
  fetch_data.py          # descarga el modelo de elevación
  calibrate_light.py     # relación sol/cielo y exposición
  build.py               # construye la escena (massing | detail), guarda .blend y renderiza
  plaza/
    config.py            # TODAS las medidas, cámaras, luz y colores (con fuente y confianza)
    geo.py               # primitivas: cajas, tornos, prismas, barridos, columnas, balaustradas
    buildings.py         # Capitolio, Catedral, Sagrario, Justicia, Liévano, genéricos y estatua
    materials.py         # materiales procedurales + bruma
    terrain.py           # terreno (modelo de elevación) y ciudad (OSM)
    people.py            # personas y palomas
    scene.py             # cielo, sol, cámaras, presets de render
references/              # informe de medidas, datos OSM y de elevación, notas de las fotos
blend/                   # archivos .blend editables
renders/                 # PNG (massing, detalle)
.claude/skills/blender-arquitectura/SKILL.md   # flujo de trabajo (skill del proyecto)
```

## Reproducir

```bash
./build.sh            # entorno + datos + massing + detalle (vista previa)
./build.sh final      # igual, con los renders finales a 1920×1080
# o por partes:
.venv/bin/python scripts/build.py --stage detail --render final --cams Cam_Referencia
```

Cámaras: `Cam_Referencia` (Justicia, Monserrate y Catedral, como la foto de referencia),
`Cam_Capitolio`, `Cam_Catedral` (con el Sagrario y el Palacio Arzobispal) y `Cam_Aerea`.

## Entorno probado

Contenedor Ubuntu 24.04 en la nube, 4 núcleos Xeon a 2,1 GHz, 15 GB de RAM y **sin GPU**:
Blender detecta los backends CUDA, OptiX, HIP y oneAPI, pero no hay dispositivos.
Todo se renderiza en CPU con muestreo adaptativo y denoising OpenImageDenoise.

## Licencias de datos

- OpenStreetMap © colaboradores de OpenStreetMap, ODbL 1.0 (vía Overture Maps Foundation).
- AWS Terrain Tiles (Mapzen/Linux Foundation; SRTM y otras fuentes públicas).
