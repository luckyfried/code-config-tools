"""Blender batch render probe (run with blender -b; no add-on and no MCP involved).

USAGE:
  python scripts/blender_run.py blender/render_probe.py -- --out runs/render_probe.png [--engine CYCLES]

Renders one small frame of a lit cube and reads the pixels back. Exit 0 and one JSON line
when the image has real content; exit 1 with the reason when it does not.
"""
import argparse
import json
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"])
    a = ap.parse_args(argv)
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (3, -3, 2.2)
    cam.rotation_euler = (1.1, 0, 0.785)
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", type="SUN"))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.6, 0.2, 0.3)
    scene.render.engine = a.engine
    if a.engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 4
    scene.render.resolution_x, scene.render.resolution_y = 64, 48
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = a.out
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(a.out)
    px = list(img.pixels)
    lum = [0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2] for i in range(0, len(px), 4)]
    spread = max(lum) - min(lum)
    result = {"blender": bpy.app.version_string, "engine": a.engine, "size": list(img.size),
              "luminance_min": min(lum), "luminance_max": max(lum)}
    print(json.dumps(result))
    if spread < 0.05:
        print("render produced a flat image: the engine ran but drew nothing usable", file=sys.stderr)
        sys.exit(1)


main()
