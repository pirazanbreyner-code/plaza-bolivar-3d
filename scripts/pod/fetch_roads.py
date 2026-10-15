"""Ejes viales reales (OSM via Overture Maps, tema transportation) alrededor de la plaza.

Uso (en una maquina con internet; instala duckdb si falta):
  python3 fetch_roads.py <salida.geojson> [release=2026-09-23.1] [radio_grados=0.0085]
"""
import json
import subprocess
import sys

try:
    import duckdb
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "duckdb"])
    import duckdb

out = sys.argv[1]
rel = sys.argv[2] if len(sys.argv) > 2 else "2026-09-23.1"
r = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0085
lat, lon = 4.5981062, -74.0760391
con = duckdb.connect()
for ext in ("httpfs", "spatial"):
    con.execute(f"INSTALL {ext}; LOAD {ext};")
con.execute("SET s3_region='us-west-2';")
q = f"""
SELECT id, subtype, class, names.primary AS name, road_surface, road_flags, speed_limits, width_rules,
       access_restrictions, level_rules,
       ST_AsGeoJSON(geometry) AS geom
FROM read_parquet('s3://overturemaps-us-west-2/release/{rel}/theme=transportation/type=segment/*', hive_partitioning=1)
WHERE bbox.xmin < {lon + r} AND bbox.xmax > {lon - r} AND bbox.ymin < {lat + r} AND bbox.ymax > {lat - r}
  AND subtype = 'road'
"""
rows = con.execute(q).fetchall()
cols = [d[0] for d in con.description]
feats = []
for row in rows:
    d = dict(zip(cols, row))
    g = json.loads(d.pop("geom"))
    props = {k: (v if isinstance(v, (str, int, float, type(None))) else json.loads(json.dumps(v, default=str)))
             for k, v in d.items()}
    feats.append({"type": "Feature", "geometry": g, "properties": props})
json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w"))
from collections import Counter
print(len(feats), "segmentos", Counter(f["properties"]["class"] for f in feats).most_common())
