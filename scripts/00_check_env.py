"""Comprueba Blender (bpy), dispositivos de Cycles y hace un render de prueba pequeno.

Uso:  .venv/bin/python scripts/00_check_env.py
"""
import os, sys, time, platform
import bpy

OUT = os.path.join(os.path.dirname(__file__), "..", "renders", "test")
os.makedirs(OUT, exist_ok=True)

print("Blender:", bpy.app.version_string, "| Python:", platform.python_version())
print("CPU threads:", os.cpu_count())

prefs = bpy.context.preferences.addons["cycles"].preferences
backends = [t[0] for t in prefs.get_device_types(bpy.context)]
print("Backends de Cycles compilados:", backends)

gpu_found = None
for be in backends:
    if be == "NONE":
        continue
    try:
        prefs.compute_device_type = be
        prefs.refresh_devices()
        devs = [(d.name, d.type) for d in prefs.devices if d.type != "CPU"]
        print(f"  {be}: {devs if devs else 'sin dispositivos'}")
        if devs and gpu_found is None:
            gpu_found = be
    except Exception as e:  # backend no disponible en este build/maquina
        print(f"  {be}: error -> {e}")

prefs.compute_device_type = gpu_found or "NONE"
prefs.refresh_devices()
for d in prefs.devices:
    d.use = True if gpu_found is None else d.type != "CPU"
print("Dispositivo elegido:", gpu_found or "CPU")

# Escena minima: suelo, esfera metalica, cubo, sol + cielo
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU" if gpu_found else "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 320, 180
scene.render.filepath = os.path.join(OUT, f"test_{'gpu' if gpu_found else 'cpu'}.png")

bpy.ops.mesh.primitive_plane_add(size=20)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1))
sph = bpy.context.object
m = bpy.data.materials.new("metal"); m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Metallic"].default_value = 1; b.inputs["Roughness"].default_value = 0.15
sph.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add(size=1.5, location=(2.2, 0.5, 0.75))
bpy.ops.object.light_add(type="SUN", rotation=(0.8, 0.2, 0.6)); bpy.context.object.data.energy = 4
world = bpy.data.worlds.new("w"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.65, 0.9, 1)
scene.world = world
bpy.ops.object.camera_add(location=(6, -6, 3.5), rotation=(1.2, 0, 0.785))
scene.camera = bpy.context.object

t = time.time()
bpy.ops.render.render(write_still=True)
print(f"Render de prueba OK en {time.time()-t:.1f}s -> {scene.render.filepath}")
