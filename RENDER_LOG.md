# Registro de renders y revisiones

Entorno: 4 núcleos Xeon a 2,1 GHz, sin GPU; Cycles en CPU con OpenImageDenoise.
Imágenes de cada iteración en `renders/iteraciones/`.

| Iteración | Cambios | Hallazgos de la revisión | Tiempo |
|---|---|---|---|
| Prueba de entorno | Esfera y cubo a 320×180, 32 muestras | Blender 5.2.2 funciona sin interfaz. Hay backends CUDA, OptiX, HIP y oneAPI, pero **sin dispositivos GPU**: se usa CPU | 1,5 s |
| Massing (preliminar) | Cajas con medidas estimadas | Flujo completo correcto. Sobreexposición → se calibró la relación sol/cielo (`calibrate_light.py`): sol 50, exposición −3,5. Nubes marrones → su brillo pasa a ser relativo a la luminancia del cielo | 5 s por cámara |
| v1 | Primer detalle con medidas preliminares | Plaza reconocible, pero los cerros son inventados y la distribución está equivocada (lado oriental en orden incorrecto, retícula sin girar) | ~60 s (960×540) |
| Massing (datos reales) | Planta OSM, retícula girada 31°, terreno del modelo de elevación y 1.474 edificios OSM | Verificado: Guadalupe a unos 15° sobre el horizonte desde la plaza, por debajo de la cornisa de la Catedral; proporciones de Capitolio (88,6 × 20 m) y plaza (79 × 100 m) coherentes | 5–7 s |
| v2 | Detalle con los datos reales | Cerros con el perfil real de Monserrate y Guadalupe. Bruma demasiado azul (7 km → 14 km); piso demasiado contrastado; cubiertas del Capitolio visibles sobre la balaustrada (se bajaron) | 70–85 s |
| v3 | Personas (70 grupos), 260 palomas, charcos, piedra más cálida | Las personas dan escala. Barrios de las laderas con aspecto de confeti (se suavizaron) | 80–90 s |
| v4 | **Fotos del usuario**: arenisca cálida, Justicia rediseñado, Arzobispal sobre la Cra 7 en crema, cupulines acampanados, reloj, banderas, piso seco con franjas, cámaras que replican las fotos | Gran salto de parecido. **Cubierta del Palacio de Justicia negra**: remate coplanar con la cubierta, los rayos de sombra chocan entre sí (se corrigió subiendo los remates). Estatua demasiado tosca | 66–105 s |
| v5 | Estatua con esqueleto y modificador Skin, nubes tipo cúmulo, cámara del Capitolio con tele (46 mm) como en la foto | Composición muy cercana a la foto 4 | 103 s |
| **Final** | 1920×1080, adaptativo hasta 384 muestras, umbral 0,015, OIDN | `Cam_Referencia`: correcta; Monserrate visible entre Justicia y la Catedral | 1.127 s (~19 min) |

## Comandos

```bash
.venv/bin/python scripts/build.py --stage massing --render test
.venv/bin/python scripts/build.py --stage detail --render final --cams Cam_Referencia
.venv/bin/python scripts/build.py --stage detail --render final --cams Cam_Capitolio,Cam_Catedral,Cam_Aerea --no-save
```

## GPU (Runpod, RTX 5080 16 GB, OptiX, driver 580)

Calidad `ultra`: 1920×1080, adaptativo hasta 1536 muestras (4× la versión final en CPU), umbral 0,006, denoising OIDN en la GPU.
Verificado durante el render: backend OPTIX, GPU al 100 %, unos 250 W, 2,6 GHz, 4,5 GB de VRAM; la CPU solo usa 1 núcleo.

| Cámara | CPU `final` (384 muestras) | GPU `ultra` (1536 muestras) |
|---|---|---|
| Cam_Referencia | 1.105 s | 125 s |
| Cam_Capitolio | 2.035 s | 193 s |
| Cam_Catedral | 1.652 s | 172 s |
| Cam_Aerea | — | 182 s |

Unas 10 veces más rápido con 4 veces más muestras (unas 40 veces por muestra).
Nota: el primer pod (RTX 3080 Ti) tenía la GPU averiada (`cuInit` devolvía 999 incluso con PyTorch) y se reemplazó.
Lección: lanzar los renders largos con `setsid nohup ... &` para que no dependan de la sesión remota.

## Texturas PBR, cielo HDRI y simulador web

- Texturas CC0 de Poly Haven teñidas por material y cielo HDRI `kloofendal_48d_partly_cloudy_puresky`
  (8K) con el sol alineado al de Bogotá el 15-10 a las 14:23 (elevación 47,9°): rotación 277,2°,
  exposición −1,25 y refuerzo solar de 2,5.
- Exportación web en el pod (RTX 5080): unos 2 min. Núcleo 704.574 triángulos, terreno 720.784
  (se simplifica a 216.000), ciudad 55.676. Escena web final unos 26 MB.
- Simulador probado en Chromium sin GPU (SwiftShader): carga en 10–17 s, colisiones, fichas,
  minimapa y trazado de rayos funcionando. Revisión: la Catedral salía casi blanca con AgX → mapeo
  Neutral y tinte de arenisca más tostado (0,50, 0,37, 0,23). El trazado de rayos salía vacío
  (atributos cuantizados) → se pasan a float al cargar.
- Render `ultra` con las texturas nuevas: **falló** (`illegal memory access`, CUDA 700) porque
  ComfyUI, que viene en la plantilla del pod, retenía 12 GB de los 16 GB de VRAM.
