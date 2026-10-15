"""Todas las medidas y parametros de la escena (metros, grados).

Marco del modelo = marco de la reticula (references/research_raw.md, seccion 0.1):
  origen = centroide de la plataforma de la plaza (4.5981062, -74.0760391)
  +X = u = "este de reticula" (azimut real 121 deg, a lo largo de las calles)
  +Y = v = "norte de reticula" (azimut real 31 deg, a lo largo de las carreras)
Las coordenadas (u, v) vienen de OSM via Overture 2026-09-23.1 (confianza media-alta, +-1-2 m)
salvo que se indique otra cosa. Las alturas casi siempre son ESTIMADAS (ver APROXIMACIONES.md).
"""

GEO = {
    "origin": (4.5981062, -74.0760391),  # OSM r13663349 | alta
    "tz": -5,
    "plaza_elev": 2614.0,                # DEM AWS Terrain Tiles en el centro | media
    "grid_rot_deg": 31.0,                # azimut de las carreras | alta (OSM, 29.5-32.4)
}

# Plataforma de la plaza (poligono OSM simplificado) y plataforma de la estatua
PLAZA = {
    "outline": [(-39.6, -50.1), (39.8, -50.2), (39.2, 47.8), (36.6, 50.1), (-28.0, 49.8),
                (-28.0, 47.5), (-39.3, 47.5)],
    "statue_platform": {"center": (6.4, -15.25), "size": 14.0, "height": 0.55,  # alto: estimado
                        "steps": 3},
}

# Lineas de fachada que delimitan el espacio publico (OSM)
FRAME = {"u_w": -55.6, "u_e": 61.0, "v_s": -67.4, "v_n": 67.0}

STREETS = {
    # Carrera 8: unica calle vehicular frente a la plaza (un sentido, hacia el sur) | media
    "cra8": {"u0": -55.6, "u1": -39.6, "road": (-50.5, -43.0), "kind": "vehicular"},
    "sidewalk_curb_h": 0.15,
}

BUILDINGS = {
    # ---------------------------------------------------------------- lado sur
    "capitolio": dict(
        name="Capitolio Nacional", builder="capitolio",
        root=(47.8, -67.4), facing="N", length=88.6, depth=95.5,   # OSM | media-alta
        axis_local=44.3,             # eje de simetria u=3.5 -> x local = 47.8-3.5
        height=20.0,                 # a parapeto | estimado (podio 2.5 + col 14 + entabl. 3.5)
        podium_h=2.5,                # estimado
        steps_front=8.0, step_tread=0.45,             # escalinata | estimado
        portico_w=30.0,              # cuerpo central | estimado (patio Mosquera 24 m)
        col_across=6, col_deep=3,    # "seis filas de tres columnas jonicas" | media
        col_h=14.0, col_r=0.70,      # 14 m segun blog (baja); diametro ajustado a proporcion jonica
        col_spacing_deep=4.6, entablature_h=3.5,
        side_bays=7, patio=(24.0, 30.0),   # 7 ejes por lado (foto) | Patio Mosquera 24 x 30
    ),
    # ---------------------------------------------------------------- lado oriental (N->S)
    "catedral": dict(
        name="Catedral Primada", builder="catedral",
        root=(61.0, 50.8), facing="W", length=41.3, depth=107.0,  # fachada v 9.5->50.8 | media
        tower_w=9.0,                 # estimado
        level1_h=13.5, level2_h=10.5, pediment_h=5.0,  # cuerpo central ~24-29 m | estimado
        belfry_h=8.5, belfry_inset=0.9,
        z=1.2, atrium_h=0.0,         # se apoya sobre el atrio (ATRIUM)
        nave_h=22.0,                 # 20-24 m | estimado
        door_main=(3.6, 7.2), door_side=(2.8, 5.6),   # advisor.travel | media
        # torres: 52 m (Wikipedia, con cruz) vs 42 m: se usa cruz a ~50 m
    ),
    "conector": dict(
        name="Cuerpo entre Catedral y Sagrario", builder="generico",
        root=(61.0, 9.5), facing="W", z=1.2, length=13.1, depth=28.0, height=13.0,  # alt. est.
        floors=3, bays=3, portal_bay=None, wall_mat="crema", trim_mat="molduras_blancas",
        cornice_h=1.0, win_w=1.2, roof="tile",
    ),
    "sagrario": dict(
        name="Capilla del Sagrario", builder="sagrario",
        root=(61.0, -3.6), facing="W", z=1.2, length=11.4, depth=48.0,
        height=17.0, drum_h=4.5,     # cuerpo; espadana llega a ~22.5 (fachada 11 x 22 m, Viajandox) | media
        dome_r=4.2, dome_top=30.0,   # cupula ~30 m | media
    ),
    # Fotos de referencia: edificio largo crema-amarillo de 4 pisos sobre la Cra 7 a la derecha
    # del Sagrario (OSM lo dibuja retranqueado tras un jardin: se sigue la foto) | media
    "arzobispal": dict(
        name="Palacio Arzobispal", builder="generico",
        root=(61.3, -15.0), facing="W", length=28.1, depth=24.0, height=17.5,
        floors=4, bays=8, portal_bay=4, wall_mat="crema", trim_mat="molduras_blancas",
        cornice_h=1.2, win_w=1.3, portal_h=7.0, portal_w=3.4, pediments=True,
    ),
    "arzobispal_esquina": dict(
        name="Edificio esquina Cra 7 con Calle 10", builder="generico",
        root=(61.3, -43.1), facing="W", length=11.5, depth=11.8, height=14.0,
        floors=3, bays=3, portal_bay=None, wall_mat="ocre_rojo", trim_mat="molduras_blancas",
        cornice_h=0.9, win_w=1.2,
    ),
    # ---------------------------------------------------------------- lado norte
    "justicia": dict(
        name="Palacio de Justicia", builder="justicia",
        root=(-39.5, 67.0), facing="S", length=83.2, depth=93.7,   # OSM | media
        # composicion segun foto de referencia (usuario): alas con marco rehundido, cuerpo
        # central saliente con portal, volumen superior retranqueado y cupula de vidrio
        height=24.0, wing_h=16.0, center_w=24.0, center_h=14.5, center_proj=5.0,  # estimado
        recess_depth=3.5, wing_pillars=3, portal=(12.0, 9.0), upper_setback=9.0,
        upper_windows=22, dome_r=5.0,
        inscription=("COLOMBIANOS LAS ARMAS OS HAN DADO LA INDEPENDENCIA\n"
                     "LAS LEYES OS DARAN LA LIBERTAD"),
        inscription_size=0.55,
    ),
    "florero": dict(
        name="Casa del Florero", builder="generico",
        root=(65.1, 59.6), facing="S", length=21.2, depth=13.8, height=9.0,  # 2 pisos | est.
        floors=2, bays=5, portal_bay=None, wall_mat="colonial_blanco", trim_mat="colonial_zocalo",
        cornice_h=0.6, win_w=1.3, roof="tile", balconies=True, colonial=True,
    ),
    "florero_cra7": dict(
        name="Casa del Florero (Cra 7)", builder="generico",
        root=(65.1, 90.3), facing="W", length=17.0, depth=13.5, height=9.0,
        floors=2, bays=4, portal_bay=None, wall_mat="colonial_blanco", trim_mat="colonial_zocalo",
        cornice_h=0.6, win_w=1.3, roof="tile", balconies=True, colonial=True,
    ),
    # ---------------------------------------------------------------- lado occidental
    "lievano": dict(
        name="Edificio Lievano", builder="lievano",
        root=(-57.0, -52.9), facing="E", rot_adjust=-1.43,  # fachada no paralela (OSM)
        length=108.1, depth=20.0,    # ala sobre la plaza ~20 m | baja-media
        height=16.0,                 # Manual IDPC 2024 (indirecto) | media
        mansard_h=4.5,               # estimado
        arcade_depth=4.5, arcade_h=5.6, bays=32, pier_w=1.0,       # 32 vanos | media-alta
        floors_upper=2, cornice_h=1.1, win_w=1.35,
        pavilions=[(0, 3), (28, 31)],          # mansardas en las dos esquinas | media-alta
        center_pediment=(13, 18),              # cuerpo central con fronton | media
    ),
}

# Atrio de la Catedral y el Sagrario: plataforma con gradas hacia la Cra 7 | estimado
# (OSM: plataforma->fachada 20.8 m incluye atrio; alto 1-1.5 m, fondo 8-10 m)
ATRIUM = {"u0": 52.0, "u1": 61.2, "v0": -15.0, "v1": 50.8, "h": 1.2, "riser": 0.15,
          "tread": 0.38}
GARDEN_WALL = None  # (OSM sugiere jardin con muro; las fotos muestran fachada sobre la Cra 7)

# Volumenes de relleno (vista aerea) de manzanas cuyo frente se modela en detalle | estimado
FILLERS = [
    ("Lievano resto de manzana", [(-77.0, -50.0), (-165.3, -50.7), (-165.9, 59.8), (-77.0, 56.0)],
     13.0),
]

STATUE = {
    "pedestal_h": 4.6,       # 4-5 m | baja (estimado por proporcion)
    "statue_h": 2.6,         # Tenerani, 2.6 m | media
    "base_w": 3.0,
    "steps": [(5.6, 0.2), (4.8, 0.2)],
    "rotation_deg": 180.0,   # mira al norte (Palacio de Justicia), de espaldas al Capitolio | baja
}

CITY = {
    "osm": "references/osm/buildings.geojson",
    "floor_h": 3.5,
    "exclude_names": ["Capitolio Nacional", "Catedral Primada", "Palacio Cardenalicio",
                      "Palacio de Justicia", "Casa del Florero"],
    # cajas (u0, v0, u1, v1) donde no se extruye OSM porque hay modelo propio
    "exclude_boxes": [(-58.0, -165.0, 52.0, -66.5), (59.5, -55.5, 170.0, 51.5),
                      (-40.0, 66.0, 45.0, 161.0), (-167.0, -54.0, -53.0, 61.0),
                      (64.5, 59.0, 91.0, 91.0), (-60.0, -68.0, 62.0, 68.0)],
    "flatten_r": (380.0, 900.0),     # radio donde el terreno se aplana a la cota de la plaza
}

TERRAIN = {
    "dem": "references/data/dem_bogota.npz",
    "u_range": (-4500.0, 7500.0),
    "v_range": (-6500.0, 8000.0),
    "step": 22.0,
    "urban_max_elev": 2760.0,   # limite aprox. de barrios en las laderas | estimado
    "paramo_elev": 3150.0,
}

LANDMARKS = [
    # santuarios en las cumbres (coordenadas aproximadas, se ajustan al DEM)
    {"name": "Santuario de Monserrate", "lat": 4.6058, "lon": -74.0563, "size": (34.0, 16.0, 13.0),
     "tower": 22.0},
    {"name": "Virgen de Guadalupe", "lat": 4.5915, "lon": -74.0542, "size": (10.0, 10.0, 6.0),
     "tower": 15.0},
]

# Recursos externos (CC0, Poly Haven). Se descargan con scripts/pod/fetch_assets.py.
# Si no existen, la escena usa los materiales procedurales y el cielo fisico.
ASSETS = {
    "dir": "/workspace/assets",            # tex/<id>_<mapa>_2k.jpg, hdri/<id>_8k.hdr
    "info": "references/data/assets_info.json",
    "hdri": "kloofendal_48d_partly_cloudy_puresky",
    "hdri_res": "8k",
    # sol del HDRI: elevacion 47.9, angulo xy 145.81 -> rotacion para el 15-10 a las 14:23
    "hdri_sun_alpha": 145.81,
    "hdri_datetime": "2026-10-15T14:23:00",
    "exposure": -1.25,                     # E_total HDRI 4.86 + refuerzo solar (ver RENDER_LOG)
    # el sol del HDRI esta algo velado (directa/difusa 1.7); se refuerza con una lampara alineada
    # para acercarlo al sol de altura de Bogota (2.600 m). Irradiancia normal anadida (W/m2 Blender)
    "sun_boost": 2.5,
}

# Material -> textura escaneada: (id, tamano real en m, color lineal medio deseado)
TEXTURES = {
    "catedral_sillar": ("sandstone_blocks_08", 3.0, (0.50, 0.37, 0.23)),   # arenisca tostada (fotos)
    "catedral_piedra": ("sandstone_blocks_04", 3.0, (0.56, 0.43, 0.28)),
    "capitolio_sillar": ("sandstone_blocks_08", 3.6, (0.46, 0.43, 0.37)),
    "capitolio_piedra": ("sandstone_blocks_04", 3.0, (0.50, 0.47, 0.41)),
    "justicia_piedra": ("stone_tile_wall", 4.0, (0.66, 0.60, 0.50)),
    "sagrario_piedra": ("sandstone_blocks_08", 2.2, (0.30, 0.28, 0.25)),
    "sagrario_estuco": ("white_stucco", 2.0, (0.78, 0.76, 0.70)),
    "arzobispal_sillar": ("painted_plaster_wall", 2.0, (0.80, 0.68, 0.44)),
    "arzobispal_piedra": ("white_stucco", 2.0, (0.84, 0.83, 0.79)),
    "crema": ("painted_plaster_wall", 2.0, (0.80, 0.68, 0.44)),
    "ocre_rojo": ("painted_plaster_wall", 2.0, (0.55, 0.28, 0.17)),
    "molduras_blancas": ("white_stucco", 2.0, (0.85, 0.84, 0.80)),
    "lievano_estuco": ("painted_plaster_wall", 2.0, (0.80, 0.56, 0.20)),   # amarillo ocre (fotos)
    "lievano_molduras": ("white_stucco", 2.0, (0.86, 0.85, 0.81)),
    "lievano_piedra": ("sandstone_blocks_08", 3.0, (0.52, 0.49, 0.44)),
    "colonial_blanco": ("white_stucco", 2.0, (0.86, 0.85, 0.81)),
    "cupula": ("sandstone_blocks_04", 3.0, (0.60, 0.52, 0.39)),
    "pedestal": ("sandstone_blocks_04", 2.0, (0.22, 0.21, 0.19)),
    "teja": ("clay_roof_tiles_02", 2.5, None),
    "cupula_roja": ("clay_roof_tiles_02", 1.6, (0.42, 0.05, 0.035)),     # cupula del Sagrario
    "pizarra": ("roof_slates_02", 3.0, (0.16, 0.17, 0.19)),
    "plaza": ("concrete_pavement", 1.8, (0.24, 0.23, 0.21)),          # losas grises (fotos)
    "plaza_franjas": ("concrete_pavement", 1.8, (0.40, 0.37, 0.32)),  # franjas claras
    "adoquin": ("pavement_03", 2.0, None),
    "anden": ("stone_pavers", 2.0, (0.30, 0.28, 0.25)),
    "asfalto": ("asphalt_02", 3.0, None),
    "madera": ("dark_wood", 2.0, None),
    "bordillo": ("sandstone_blocks_04", 2.0, (0.42, 0.41, 0.39)),
}

# Simulador web: material -> (textura, tamano real en m, color lineal medio deseado o None,
#                             profundidad del relieve en m para parallax, intensidad del normal)
# Texturas de scripts/pod/web_textures.py (2K las principales). Elegidas comparando con las fotos.
WEB_MATERIALS = {
    "catedral_sillar": ("sandstone_blocks_08", 3.0, (0.50, 0.37, 0.23), 0.022, 1.5),
    "catedral_piedra": ("beige_wall_001", 3.0, (0.56, 0.43, 0.28), 0.0, 1.2),
    "capitolio_sillar": ("large_sandstone_blocks", 3.0, (0.40, 0.38, 0.33), 0.03, 1.4),  # gris envejecido
    "capitolio_piedra": ("beige_wall_001", 3.0, (0.48, 0.45, 0.39), 0.0, 1.2),
    "justicia_piedra": ("stone_tile_wall", 4.0, (0.66, 0.60, 0.50), 0.008, 1.2),
    "sagrario_piedra": ("red_sandstone_wall", 2.2, (0.26, 0.24, 0.21), 0.02, 1.5),
    "sagrario_estuco": ("white_stucco", 2.0, (0.78, 0.76, 0.70), 0.0, 1.0),
    "arzobispal_sillar": ("plastered_wall_04", 3.2, (0.80, 0.68, 0.44), 0.0, 1.2),
    "arzobispal_piedra": ("white_stucco", 2.0, (0.84, 0.83, 0.79), 0.0, 1.0),
    "crema": ("plastered_wall_04", 3.2, (0.80, 0.68, 0.44), 0.0, 1.2),
    "ocre_rojo": ("yellow_plaster", 2.0, (0.55, 0.28, 0.17), 0.0, 1.2),
    "molduras_blancas": ("white_stucco", 2.0, (0.85, 0.84, 0.80), 0.0, 1.0),
    "lievano_estuco": ("yellow_plaster", 2.0, (0.80, 0.56, 0.20), 0.0, 1.2),
    "lievano_molduras": ("white_stucco", 2.0, (0.86, 0.85, 0.81), 0.0, 1.0),
    "lievano_piedra": ("white_sandstone_blocks_02", 2.0, (0.52, 0.49, 0.44), 0.02, 1.4),
    "colonial_blanco": ("plastered_wall_04", 3.2, (0.86, 0.85, 0.81), 0.0, 1.2),
    "cupula": ("sandstone_blocks_08", 3.0, (0.60, 0.52, 0.39), 0.015, 1.3),
    "pedestal": ("granite_tile", 2.3, (0.22, 0.21, 0.19), 0.006, 1.0),
    "teja": ("clay_roof_tiles_02", 2.5, (0.2, 0.085, 0.055), 0.035, 1.3),    # teja de barro envejecida
    "cupula_roja": ("clay_roof_tiles_02", 1.6, (0.42, 0.05, 0.035), 0.03, 1.3),
    "pizarra": ("roof_slates_02", 3.0, (0.16, 0.17, 0.19), 0.015, 1.2),
    "plaza": ("granite_tile_04", 3.2, (0.24, 0.23, 0.21), 0.006, 1.2),   # losas de 0,8 m
    "plaza_franjas": ("granite_tile_03", 2.4, (0.40, 0.37, 0.32), 0.006, 1.2),
    "adoquin": ("brick_pavement_02", 2.0, (0.20, 0.13, 0.10), 0.02, 1.5),   # ladrillo de la Cra 7
    "anden": ("concrete_tiles", 1.85, (0.30, 0.28, 0.25), 0.008, 1.2),
    "asfalto": ("asphalt_02", 3.0, None, 0.008, 1.3),
    "madera": ("dark_wood", 2.0, None, 0.0, 1.0),
    "bordillo": ("granite_tile", 2.3, (0.42, 0.41, 0.39), 0.0, 1.0),
}

# Simulador web: fachadas de la ciudad de fondo (7 variantes de Blender "Ciudad fachada k"):
# (textura, tamano en m, color lineal medio, ancho de vano de ventana en m)
WEB_CITY = [
    ("red_brick", 1.4, (0.30, 0.13, 0.07), 3.2),           # ladrillo tolete
    ("brick_wall_09", 2.0, (0.34, 0.19, 0.12), 2.8),
    ("red_bricks_04", 2.5, (0.22, 0.09, 0.05), 3.4),
    ("painted_plaster_wall", 2.0, (0.70, 0.62, 0.48), 2.9),  # estuco crema
    ("painted_plaster_wall", 2.0, (0.80, 0.78, 0.74), 3.1),  # estuco blanco
    ("plastered_wall_04", 3.2, (0.72, 0.52, 0.36), 2.7),     # estuco ocre
    ("plastered_wall_04", 3.2, (0.42, 0.42, 0.41), 3.6),     # concreto gris
]

LIGHT = {
    "datetime": "2026-10-15T15:45:00",
    # calibrado con scripts/calibrate_light.py: relacion directa/difusa ~3
    "sun_strength": 42.0,
    "sky": {"clouds": 0.68, "cloud_bright": 2.6, "strength": 1.0, "air": 1.0, "aerosol": 2.0},
    "exposure": -3.5,
    "look": "AgX - Base Contrast",
    "haze_dist": 14000.0,       # distancia caracteristica de la bruma (visibilidad ~40 km)
}

# Astas con bandera (u, v, z base, altura del asta): Justicia (foto) y Capitolio (foto) | estimado
FLAGS = [(-27.0, 62.5, -0.12, 12.0), (-13.0, 62.5, -0.12, 12.0), (3.5, -71.0, 20.0, 7.0)]

# Retícula de franjas claras del piso de la plaza (fotos) | estimado
PLAZA_BANDS = {"every": 7.2, "width": 0.45, "u": (-39.6, 39.8), "v": (-50.1, 47.5)}

# Faroles de hierro (fotos: frente al Lievano y en la Cra 7) | posiciones estimadas
LAMPS = {
    "height": 4.6,
    "rows": [  # (u0, v0, u1, v1, separacion)
        (-51.6, -48.0, -51.6, 52.0, 10.0),     # anden de la Cra 8, frente a los portales
        (47.6, -44.0, 47.6, 46.0, 12.0),       # Cra 7, al pie de las gradas del atrio
    ],
    "points": [(-39.0, -49.5), (39.2, -49.6), (38.6, 47.2), (-38.7, 47.0)],  # esquinas
}

PEOPLE = {"n": 70, "seed": 4, "pigeons": 260, "cam_clear_r": 9.0}

# Camaras. Cada una puede tener su propia hora (iluminacion de la fachada principal).
CAMERAS = {
    # Replica la foto grande de referencia: Justicia (izq.), Monserrate (centro), Catedral (der.)
    "Cam_Referencia": {"loc": (-30.0, -36.0, 1.6), "target": (18.5, 51.5, 36.0), "focal": 19.0},
    # Replica la foto del Capitolio con la estatua delante
    "Cam_Capitolio": {"loc": (4.0, 32.0, 1.6), "target": (3.5, -67.4, 12.0), "focal": 46.0,
                      "datetime": "2026-07-20T10:30:00"},
    # Replica la foto de la Catedral con el Sagrario y el Palacio Arzobispal
    "Cam_Catedral": {"loc": (-36.0, -28.0, 1.6), "target": (61.0, 8.0, 14.0), "focal": 28.0},
    "Cam_Aerea": {"loc": (-330.0, -250.0, 170.0), "target": (40.0, 40.0, 60.0), "focal": 28.0,
                  "level": False},
}

MATERIALS = {
    # fotos: losas rectangulares de arenisca gris-beige en reticula, con franjas | media
    "plaza": dict(slab=(1.10, 0.70), base=(0.40, 0.35, 0.29), var=0.10, band_every=6.6,
                  band_w=0.35, band_col=(0.30, 0.27, 0.23), wet=0.06),
    "adoquin": dict(size=(0.24, 0.12), base=(0.40, 0.36, 0.32), var=0.2),
    "capitolio_sillar": dict(base=(0.50, 0.38, 0.25), block=(1.1, 0.55), var=0.16, grime=1.3),
    "capitolio_piedra": dict(base=(0.53, 0.41, 0.28), grime=1.2),
    "catedral_sillar": dict(base=(0.50, 0.36, 0.24), block=(0.9, 0.45), var=0.16, grime=1.4),
    "catedral_piedra": dict(base=(0.54, 0.40, 0.27), grime=1.3),
    "sagrario_estuco": dict(base=(0.80, 0.74, 0.58)),
    "sagrario_piedra": dict(base=(0.52, 0.39, 0.27)),
    "arzobispal_sillar": dict(base=(0.52, 0.50, 0.46), block=(1.0, 0.5)),
    "arzobispal_piedra": dict(base=(0.56, 0.54, 0.50)),
    "justicia_piedra": dict(base=(0.55, 0.40, 0.26), block=(2.2, 0.55), mortar=0.006, grime=1.0),
    "lievano_estuco": dict(base=(0.82, 0.76, 0.62)),
    "lievano_molduras": dict(base=(0.86, 0.84, 0.78)),
    "lievano_piedra": dict(base=(0.55, 0.53, 0.49), block=(0.8, 0.4)),
    "colonial_blanco": dict(base=(0.86, 0.85, 0.81)),
    "colonial_zocalo": dict(base=(0.30, 0.22, 0.14)),
    "cupula": dict(base=(0.48, 0.35, 0.24)),
    "pedestal": dict(base=(0.20, 0.19, 0.17)),   # base oscura (foto)
    "crema": dict(base=(0.80, 0.66, 0.36)),              # fotos: crema-amarillo
    "ocre_rojo": dict(base=(0.55, 0.28, 0.17)),
    "molduras_blancas": dict(base=(0.85, 0.84, 0.80)),
    "madera": (0.20, 0.12, 0.07),
    "madera_balcon": (0.12, 0.20, 0.13),
    "carpinteria_oscura": (0.06, 0.07, 0.07),
    "carpinteria_clara": (0.80, 0.80, 0.77),
}
