"""Blender asset preparation for the arm bundle and the orientation fixture (run with blender -b).

USAGE (through the launcher, which finds Blender and bounds the run):
  python scripts/blender_run.py blender/make_assets.py -- \
      --arm-meshes examples/arm/meshes --fixture-dir examples/fixtures/orientation

Builds each visual mesh with the data API in its body's own frame (origin at the joint,
+X along the link, Z up, meters), applies object scale, and exports one OBJ per object with
forward +Y and up +Z, so OBJ coordinates are MuJoCo coordinates with no conversion.
The fixture is also exported with Y-up axes and at centimeter scale; the contract check
must refuse both. Writes blender_export.json beside the meshes.
"""
import argparse
import json
import os
import sys

import bmesh
import bpy
from mathutils import Matrix


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-meshes", required=True)
    ap.add_argument("--fixture-dir", required=True)
    return ap.parse_args(argv)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def box_mesh(name, lo, hi, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = lo[0] if v.co.x < 0 else hi[0]
        v.co.y = lo[1] if v.co.y < 0 else hi[1]
        v.co.z = lo[2] if v.co.z < 0 else hi[2]
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=bevel, segments=2,
                        affect='EDGES', profile=0.5)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def union_mesh(name, boxes, divide=1.0):
    bm = bmesh.new()
    for b in boxes:
        tmp = box_mesh("tmp", [c / divide for c in b["min"]], [c / divide for c in b["max"]])
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def add_object(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def export_obj(obj, path, forward='Y', up='Z', scale=1.0):
    for o in bpy.context.scene.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.obj_export(
        filepath=path, export_selected_objects=True, forward_axis=forward, up_axis=up,
        global_scale=scale, apply_modifiers=True, export_materials=False, export_uv=False,
        export_normals=True, export_triangulated_mesh=True,
    )


def world_aabb(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]


def main():
    a = args()
    clear_scene()
    report = {"blender": bpy.app.version_string, "units": "meters", "axes": {"up": "+Z", "forward": "+Y"},
              "objects": []}

    links = [
        ("base", [-0.06, -0.06, 0.0], [0.06, 0.06, 0.15], 0.008),
        ("upper_link", [-0.03, -0.03, -0.03], [0.33, 0.03, 0.03], 0.012),
        ("fore_link", [-0.025, -0.025, -0.025], [0.275, 0.025, 0.025], 0.01),
    ]
    for name, lo, hi, bevel in links:
        obj = add_object(name, box_mesh(name, lo, hi, bevel))
        path = os.path.join(a.arm_meshes, f"{name}.obj")
        export_obj(obj, path)
        report["objects"].append({"object": name, "file": os.path.relpath(path, a.arm_meshes),
                                  "vertices": len(obj.data.vertices), "aabb": world_aabb(obj),
                                  "origin": list(obj.location), "export": {"forward": "Y", "up": "Z", "scale": 1.0}})
        bpy.data.objects.remove(obj, do_unlink=True)

    spec = json.load(open(os.path.join(a.fixture_dir, "fixture.json")))
    sx, sy, sz = spec["scale_in_blender"]
    obj = add_object("fixture", union_mesh("fixture", spec["boxes"], divide=sx))
    obj.scale = (sx, sy, sz)
    for o in bpy.context.scene.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    applied = list(obj.scale)
    for fname, fwd, up, scale in [("fixture.obj", "Y", "Z", 1.0),
                                  ("fixture_wrong_axes.obj", "NEGATIVE_Z", "Y", 1.0),
                                  ("fixture_centimeters.obj", "Y", "Z", 100.0)]:
        path = os.path.join(a.fixture_dir, fname)
        export_obj(obj, path, fwd, up, scale)
        report["objects"].append({"object": "fixture", "file": fname, "vertices": len(obj.data.vertices),
                                  "aabb": world_aabb(obj), "scale_after_apply": applied,
                                  "export": {"forward": fwd, "up": up, "scale": scale}})
    for d in (a.arm_meshes, a.fixture_dir):
        with open(os.path.join(d, "blender_export.json"), "w") as f:
            json.dump({**report, "objects": [o for o in report["objects"]
                                             if (d == a.fixture_dir) == (o["object"] == "fixture")]}, f, indent=2)
    print(json.dumps({"exported": [o["file"] for o in report["objects"]], "blender": bpy.app.version_string}))


main()
