"""Construye frontend/modelos/cuerpo.glb a partir de BodyParts3D (CC BY 4.0).

Uso (Blender en modo consola):
    blender -b --factory-startup --python scripts/construir_cuerpo_blender.py -- \
        <carpeta_obj> <grupos.json> <salida.glb>

- grupos.json: {"corazon": ["FJ1234", ...], "pulmones": [...], ...}
- Une las piezas de cada órgano, las simplifica (Decimate), pasa de mm a metros,
  apoya los pies en y=0 y exporta un solo .glb con un objeto por órgano.
- Los nombres de objeto son el CONTRATO con el visor 3D:
  corazon, cerebro, pulmones, huesos, ojos, sangre, piel.

Atribución obligatoria: "BodyParts3D, © The Database Center for Life Science
licensed under CC Attribution 4.0 International".

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import sys
import time

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
CARPETA, GRUPOS, SALIDA = args[0], args[1], args[2]

# Vértices objetivo por órgano (equilibrio entre detalle y peso para la web).
OBJETIVO = {"piel": 14000, "huesos": 45000, "sangre": 28000, "cerebro": 16000,
            "pulmones": 14000, "corazon": 12000, "ojos": 3000}

# Colores base (el visor los tiñe con el semáforo).
COLOR = {"piel": (0.31, 0.82, 1.0, 0.15), "huesos": (0.93, 0.9, 0.82, 1), "sangre": (0.8, 0.12, 0.15, 1),
         "cerebro": (0.95, 0.66, 0.72, 1), "pulmones": (0.95, 0.6, 0.65, 1),
         "corazon": (0.75, 0.1, 0.15, 1), "ojos": (0.95, 0.95, 0.95, 1)}

bpy.ops.wm.read_factory_settings(use_empty=True)
grupos = json.load(open(GRUPOS))
inicio = time.time()

for organo, archivos in grupos.items():
    piezas = []
    for fj in archivos:
        antes = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=f"{CARPETA}/{fj}.obj", forward_axis="Y", up_axis="Z")
        piezas += [o for o in bpy.data.objects if o not in antes and o.type == "MESH"]
    if not piezas:
        print("Sin piezas:", organo)
        continue

    bpy.ops.object.select_all(action="DESELECT")
    for o in piezas:
        o.select_set(True)
    bpy.context.view_layer.objects.active = piezas[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = organo

    # Limpiar vértices duplicados y simplificar.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.05)
    bpy.ops.object.mode_set(mode="OBJECT")
    n = len(obj.data.vertices)
    ratio = min(1.0, OBJETIVO.get(organo, 15000) / max(n, 1))
    if ratio < 1.0:
        mod = obj.modifiers.new("simplificar", "DECIMATE")
        mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.shade_smooth()

    mat = bpy.data.materials.new(organo)
    mat.diffuse_color = COLOR[organo]
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print(f"{organo:9s} {len(archivos):4d} piezas  {n:7d} -> {len(obj.data.vertices):6d} vértices")

# mm -> m, centrar en x/y del cuerpo y apoyar los pies en z=0 (y=0 en glTF).
todos = [o for o in bpy.data.objects if o.type == "MESH"]
for o in todos:
    o.scale = (0.001, 0.001, 0.001)
bpy.context.view_layer.update()
puntos = [o.matrix_world @ Vector(c) for o in todos for c in o.bound_box]
minimo = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
maximo = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
centro = (minimo + maximo) / 2
for o in todos:
    o.location = (-centro.x, -centro.y, -minimo.z)
bpy.context.view_layer.update()
print("Altura del cuerpo: %.2f m" % (maximo.z - minimo.z))

bpy.ops.export_scene.gltf(filepath=SALIDA, export_format="GLB", export_yup=True,
                          export_apply=True, export_materials="EXPORT")
print(f"Exportado {SALIDA} en {time.time() - inicio:.0f} s")
