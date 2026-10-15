---
name: blender-arquitectura
description: Modelar y renderizar arquitectura real en Blender (bpy, sin interfaz) a partir de referencias, con proporciones verificables, materiales procedurales y Cycles. Usar al crear o modificar la escena de la Plaza de Bolívar (u otro conjunto urbano), al revisar renders, al cambiar medidas o cámaras, o al entregar archivos .blend/PNG.
---

# blender-arquitectura

Flujo para reconstruir arquitectura existente en Blender usando solo Python (`bpy`),
de forma reproducible y editable. Pensado para un entorno sin GPU ni interfaz gráfica.

## 0. Entorno

- Blender se usa como módulo de Python: `.venv/bin/python` con `bpy==5.2.2`
  (se instala con `uv venv .venv --python 3.13 && uv pip install --python .venv/bin/python bpy==5.2.2`).
- Antes de nada: `.venv/bin/python scripts/00_check_env.py`. Lista los backends de Cycles
  (CUDA/OptiX/HIP/oneAPI), elige GPU si existe y hace un render de 320×180 en `renders/test/`.
- Sin GPU, todo el render es en CPU: usar muestreo adaptativo + OpenImageDenoise y
  presets de calidad (`--quality preview|final`), nunca subir muestras a ciegas.
- Renders largos: lanzarlos en segundo plano y redirigir el log a `renders/logs/`.

## 1. Referencias antes que geometría

1. Reunir medidas en `references/` (fuente, valor, confianza **alta/media/baja/estimado**).
2. Pasar **cada** número usado a `scripts/plaza/config.py`, con un comentario
   `# fuente: … | confianza: …`. Ningún número "mágico" dentro de los generadores.
3. Todo lo que no tenga fuente directa se registra en `APROXIMACIONES.md`
   (qué es, valor usado, cómo se estimó, cómo verificarlo).

### Fuentes de datos que funcionan en este entorno (sin acceso a Wikipedia ni a OSM directo)
- Huellas de edificios, calles y usos del suelo: Overture Maps en S3 público
  (`overturemaps-us-west-2.s3.amazonaws.com`), datos de OSM. Proyectarlos al marco local de la
  retícula (para Bogotá, 31°) y extruirlos (`terrain.osm_city`).
- Relieve: AWS Terrain Tiles (`s3.amazonaws.com/elevation-tiles-prod/terrarium/z/x/y.png`,
  zoom 13 ≈ 19 m/px) → `scripts/fetch_data.py`. Validar contra cotas conocidas antes de usarlo.
- Búsqueda web (WebSearch) para alturas y descripciones; marcar siempre su confianza.
- **Fotos del usuario**: mandan sobre OSM y la web en color, composición y volumetría.
  Registrar cada decisión en `references/fotos_usuario.md`.

## 2. Volúmenes primero (massing)

- `scripts/01_massing.py` construye solo cajas: plaza, calles, huellas y alturas de edificios,
  estatua como cilindro. Material gris neutro, cámaras definitivas.
- Revisar con renders aéreo + a nivel de peatón **antes** de detallar:
  - distribución: qué edificio está en cada lado y hacia dónde mira su fachada;
  - proporciones: ancho de plaza vs. alturas (relación de encierro), longitud de fachadas;
  - cámara: altura de ojo 1,6–1,7 m, focal 24–35 mm, verticales rectas (cámara sin inclinación
    o con *shift* vertical en lugar de cabeceo).
- Solo cuando el massing está bien se pasa al detalle.

## 3. Detalle (LOD por capas)

Convenciones de `scripts/plaza/`:
- Unidades en metros. Origen = centro de la plaza (estatua). +X = este (Carrera 7),
  +Y = norte (Calle 11), +Z = arriba.
- Cada edificio se modela en un **marco de fachada local**: x a lo largo de la fachada
  (izquierda→derecha vista desde la plaza), z arriba, fachada en y=0 y el edificio hacia +y.
  Un *Empty* padre lo coloca y lo rota en el mundo (`geo.facade_root`).
- Vanos (ventanas, arcos, puertas) con modificador Boolean **MANIFOLD** vivo; los cortadores
  son prismas manifold (`geo.outline_prism`) unidos en un objeto oculto por fachada.
  Así el .blend sigue siendo editable (mover un cortador mueve el vano).
- Elementos repetidos (columnas, balaustres, ventanas) como **duplicados enlazados**
  (misma malla) para ahorrar memoria y poder editar todos a la vez.
- Bisel pequeño (1–3 cm) en aristas visibles: sin él, la piedra parece CG.
- **Nunca dejar caras coplanares superpuestas** (por ejemplo, un remate cuya cara superior coincide
  con la cubierta): los rayos de sombra chocan entre ellas y la superficie sale negra. Subir los
  remates unos centímetros o hacerlos perimetrales. Para encontrar el objeto culpable, usar
  `scene.ray_cast` sobre el .blend.
- Cortadores de vanos que se cruzan (arcos pasantes en dos ejes) funcionan con MANIFOLD si cada
  prisma es cerrado. Revisar el render de todas formas.

## 4. Materiales

- Preferir texturas PBR CC0 (Poly Haven, descargadas en el pod: `scripts/pod/fetch_assets.py`;
  la API exige un User-Agent). `M.pbr()` las tiñe al color medio deseado: factor = tinte / media
  lineal de la textura (`references/data/assets_info.json`). Sin texturas, quedan las procedurales.
- UV en metros con el grupo de nodos `geo.box_uv_group()` (atributo FLOAT2 "UVMap" por esquina,
  proyección por normal); nunca UVs automáticas.
- Sillería (bloques de piedra) con Brick Texture en proyección por normal (x,z)/(y,z).
- Añadir siempre: variación de color de baja frecuencia, rugosidad variable,
  suciedad en los primeros ~1,5 m y chorreaduras verticales. Es lo que más realismo aporta.

## 5. Luz y render

- Cielo `MULTIPLE_SCATTERING` + lámpara Sun con la misma dirección (disco solar del cielo
  apagado para no duplicar). Nubes procedurales en el World.
- Gestión de color AgX (look *Base Contrast* o *Medium High Contrast*), exposición ajustada a ojo.
- Presets: `preview` (960×540, hasta 64 muestras), `final` (1920×1080, adaptativo hasta 384, umbral 0,015; unos 15–25 min por cámara en 4 núcleos).

- Cielo HDRI real: localizar su sol (píxel más brillante), calcular la hora de Bogotá con esa
  elevación y girar el HDRI para que el azimut coincida (`build.hdri_rotation`). Reforzar con una
  lámpara Sun alineada si el sol del HDRI está velado.
- GPU compartida: comprobar `nvidia-smi` antes de lanzar. Otro proceso (p. ej. ComfyUI de la
  plantilla) puede retener 12 GB de VRAM y Cycles falla con `illegal memory access` (CUDA 700).

## 5b. Exportar al simulador web

- `scripts/export_web.py`: aplicar modificadores, unir por material, exportar GLB con
  materiales PLACEHOLDER y nombres de malla `<bloque>:<material>`; los materiales se describen en
  `scene.json` y se recrean en three.js. Hornear lo procedural (terreno, fachadas de la ciudad).
- Los artifacts no sirven .glb ni .hdr, y la página no debe depender de WebAssembly:
  cuantizar + gzip + base64 (`web/build_scene.sh`). Pasar los atributos cuantizados a float al
  cargar: el path tracer de three-gpu-pathtracer no los desnormaliza (la escena sale vacía).
- En three.js, AgX lava la arenisca; usar el mapeo Neutral con +0,5 EV.

## 6. Revisión de renders (obligatorio tras cada render)

Abrir el PNG (herramienta Read) y comprobar:
1. ¿Proporciones creíbles comparadas con `references/`? (alturas relativas, anchos).
2. ¿Escala humana? Puertas ~2,5–4 m, barandas ~1 m, peldaños 15–18 cm.
3. ¿Verticales rectas, horizonte coherente, sin objetos atravesados ni caras negras?
4. ¿Exposición: cielo sin quemar, sombras con detalle? ¿Ruido o luciérnagas?
5. ¿Texturas a escala correcta (bloques ~0,4–0,6 m de alto, losas del piso)?
Anotar hallazgos y correcciones en `RENDER_LOG.md`.

## 7. Entregables editables

- `blend/*.blend` guardados con colecciones con nombre (Plaza, Calles, Capitolio, Catedral, …),
  modificadores sin aplicar y cortadores ocultos.
- `renders/<etapa>/*.png` y la línea de comando exacta que los generó.
- Todo se regenera con `./build.sh` (massing, detalle, renders).
