"""Replay a simulation trace in Blender, prove the replay matches it, and render frames.

USAGE (headless, through the kit's runner):
  python scripts/blender_run.py blender/replay_render.py -- BUNDLE_DIR TRACE_JSON --out DIR
         [--fps 50] [--max-frames 400] [--render-every 5] [--size 480x270] [--samples 16]
         [--engine CYCLES|BLENDER_EEVEE|BLENDER_WORKBENCH] [--no-render] [--save-blend]

Builds the scene from bundle.json alone: each body's visual mesh (the same OBJ MuJoCo loaded,
imported with the bundle's axes), the static scenery, and the camera. Frame f shows the trace at
t = f / fps (rows interpolated, positions linearly and rotations by slerp, when f / fps falls
between steps). Every body gets a location and rotation_quaternion key on every frame.

Then it checks that each imported mesh kept the file's own coordinates (MuJoCo reads them as the
body frame) and reads matrix_world of every body back on every frame and compares it with the
trace: positions within 1e-5 m and rotations within 1e-4 rad. Writes DIR/replay_report.json (the
measured worst errors) and DIR/frames.json (frame -> t, trace row, qpos, contact count), and
renders every --render-every frame to DIR/frames/frame_NNNN.png. Exit 1 when the replay is
outside tolerance or the trace does not name the bundle's bodies.
"""
import argparse
import bisect
import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

POS_TOL = 1e-5
ROT_TOL = 1e-4


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="replay_render.py")
    ap.add_argument("bundle", type=Path)
    ap.add_argument("trace", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=int, default=50)
    ap.add_argument("--max-frames", type=int, default=400)
    ap.add_argument("--render-every", type=int, default=5)
    ap.add_argument("--size", default="480x270")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"])
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--save-blend", action="store_true")
    return ap.parse_args(argv)


def fail(msg):
    print(f"replay_render: {msg}", file=sys.stderr)
    sys.exit(1)


def material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def geom_rgba(model_xml):
    root = ET.parse(model_xml).getroot()
    return {g.get("name"): [float(v) for v in g.get("rgba").split()]
            for g in root.iter("geom") if g.get("name") and g.get("rgba")}


def import_obj(path, fwd, up):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis=fwd, up_axis=up)
    new = [o for o in bpy.data.objects if o not in before]
    if len(new) != 1:
        fail(f"{path} imported as {len(new)} objects; a visual mesh is one object")
    return new[0]


def obj_file_bounds(path):
    vs = [[float(v) for v in line.split()[1:4]] for line in open(path) if line.startswith("v ")]
    return [min(c) for c in zip(*vs)], [max(c) for c in zip(*vs)]


def mesh_frame_error(obj, path):
    """How far the imported mesh sits from the file's own coordinates, which MuJoCo reads as the
    body frame. Measured in world space straight after import, so an axis or scale conversion
    shows up whether the importer put it in the vertices or in the object's transform."""
    bpy.context.view_layer.update()
    lo, hi = obj_file_bounds(path)
    co = [obj.matrix_world @ v.co for v in obj.data.vertices]
    blo = [min(c[k] for c in co) for k in range(3)]
    bhi = [max(c[k] for c in co) for k in range(3)]
    return max(abs(x - y) for x, y in zip(lo + hi, blo + bhi))


def sample(rows, times, t):
    """Body poses at time t from the recorded row times: the row itself when t is a recorded time,
    else interpolated between the two rows around t. Returns (row index, exact, poses)."""
    i = max(bisect.bisect_right(times, t + 1e-9) - 1, 0)
    if i >= len(rows) - 1 or abs(times[i] - t) < 1e-9:
        r = rows[i]
        return i, abs(times[i] - t) < 1e-9, {n: (Vector(b["pos"]), Quaternion(b["quat_wxyz"]))
                                             for n, b in r["bodies"].items()}
    a, b = rows[i], rows[i + 1]
    frac = (t - times[i]) / (times[i + 1] - times[i])
    out = {}
    for n in a["bodies"]:
        pa, pb = Vector(a["bodies"][n]["pos"]), Vector(b["bodies"][n]["pos"])
        qa, qb = Quaternion(a["bodies"][n]["quat_wxyz"]), Quaternion(b["bodies"][n]["quat_wxyz"])
        out[n] = (pa.lerp(pb, frac), qa.slerp(qb, frac))
    return i, False, out


def main():
    a = args()
    t_start = time.time()
    bundle = json.loads((a.bundle / "bundle.json").read_text())
    trace = json.loads(a.trace.read_text())
    rows = trace["rows"]
    times = [r["t"] for r in rows]
    names = set(rows[0]["bodies"])
    missing = [b for b in bundle["bodies"] if b not in names]
    if missing:
        fail(f"the trace has no poses for {missing}; it was recorded from another model")
    rgba = geom_rgba(a.bundle / bundle["model"])
    exp = bundle["source"]["export"]

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    objs = {}
    mesh_err = {}
    for body, spec in bundle["bodies"].items():
        obj = import_obj(a.bundle / spec["visual_mesh"], exp["forward"], exp["up"])
        obj.name = spec["blender_object"]
        mesh_err[body] = mesh_frame_error(obj, a.bundle / spec["visual_mesh"])
        obj.rotation_mode = "QUATERNION"
        obj.data.materials.clear()
        obj.data.materials.append(material(body, rgba.get(spec["visual_geom"], [0.7, 0.7, 0.7, 1])))
        objs[body] = obj
    for s in bundle.get("static", []):
        if s["type"] == "plane":
            bpy.ops.mesh.primitive_plane_add(size=2.0)
            o = bpy.context.object
            o.scale = (s["size"][0] or 5.0, s["size"][1] or 5.0, 1.0)
        elif s["type"] == "box":
            bpy.ops.mesh.primitive_cube_add(size=2.0)
            o = bpy.context.object
            o.scale = s["size"]
        else:
            print(f"replay_render: static {s['type']} '{s['name']}' is not drawn", file=sys.stderr)
            continue
        o.name = s["name"]
        o.location = s["pos"]
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = s["quat_wxyz"]
        o.data.materials.append(material(s["name"], s["rgba"]))

    cam_spec = bundle["camera"]
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    cam.data.lens = cam_spec["lens_mm"]
    cam.location = cam_spec["pos"]
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(cam_spec["look_at"]) - Vector(cam_spec["pos"])).to_track_quat("-Z", "Y")
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", type="SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.7, 0.2, 0.5)
    scene.collection.objects.link(sun)
    world = scene.world or bpy.data.worlds.new("world")
    scene.world = world
    world.color = (0.05, 0.055, 0.065)

    duration = rows[-1]["t"] - rows[0]["t"]
    nframes = min(int(math.floor(duration * a.fps + 1e-9)) + 1, a.max_frames)
    scene.render.fps = a.fps
    scene.frame_start, scene.frame_end = 1, nframes
    frames = []
    for f in range(nframes):
        t = times[0] + f / a.fps
        i, exact, poses = sample(rows, times, t)
        for body, obj in objs.items():
            pos, q = poses[body]
            obj.location = pos
            obj.rotation_quaternion = q
            obj.keyframe_insert("location", frame=f + 1)
            obj.keyframe_insert("rotation_quaternion", frame=f + 1)
        frames.append({"frame": f + 1, "t": t, "row": i, "exact": exact,
                       "qpos": rows[i]["qpos"], "contacts": len(rows[i].get("contacts", []))})

    worst_pos, worst_rot, worst_at = 0.0, 0.0, None
    for fr in frames:
        scene.frame_set(fr["frame"])
        _, _, poses = sample(rows, times, fr["t"])
        for body, obj in objs.items():
            loc, rot, _ = obj.matrix_world.decompose()
            pos, q = poses[body]
            dp = (loc - pos).length
            dr = 2 * math.acos(min(1.0, abs(rot.normalized().dot(q.normalized()))))
            if dp > worst_pos or dr > worst_rot:
                worst_at = (fr["frame"], body)
            worst_pos, worst_rot = max(worst_pos, dp), max(worst_rot, dr)
    worst_mesh = max(mesh_err.values())
    ok = worst_pos <= POS_TOL and worst_rot <= ROT_TOL and worst_mesh <= POS_TOL

    rendered = []
    w, h = (int(v) for v in a.size.split("x"))
    if ok and not a.no_render:
        scene.render.engine = a.engine
        if a.engine == "CYCLES":
            scene.cycles.device = "CPU"
            scene.cycles.samples = a.samples
        scene.render.resolution_x, scene.render.resolution_y = w, h
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        (a.out / "frames").mkdir(parents=True, exist_ok=True)
        for fr in frames[::a.render_every]:
            scene.frame_set(fr["frame"])
            scene.render.filepath = str(a.out / "frames" / f"frame_{fr['frame']:04d}.png")
            bpy.ops.render.render(write_still=True)
            rendered.append(fr["frame"])
    a.out.mkdir(parents=True, exist_ok=True)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(a.out / "replay.blend"))
    report = {
        "blender": bpy.app.version_string, "engine": a.engine, "fps": a.fps, "frames": nframes,
        "trace_rows": len(rows), "trace_timestep": trace["meta"]["timestep"],
        "exact_frames": sum(f["exact"] for f in frames),
        "tolerance": {"position_m": POS_TOL, "rotation_rad": ROT_TOL},
        "max_mesh_frame_error_m": worst_mesh,
        "max_position_error_m": worst_pos, "max_rotation_error_rad": worst_rot,
        "worst": {"frame": worst_at[0], "body": worst_at[1]} if worst_at else None,
        "within_tolerance": ok, "rendered_frames": rendered, "size": [w, h],
        "wall_s": round(time.time() - t_start, 2),
    }
    (a.out / "replay_report.json").write_text(json.dumps(report, indent=1))
    (a.out / "frames.json").write_text(json.dumps(frames))
    print(json.dumps({k: report[k] for k in ("frames", "exact_frames", "max_mesh_frame_error_m", "max_position_error_m",
                                             "max_rotation_error_rad", "within_tolerance", "wall_s")}))
    print(f"rendered {len(rendered)} frames" if rendered else "no frames rendered")
    if not ok:
        fail(f"the replay is off the trace: mesh frame {worst_mesh:.2e} m, pose {worst_pos:.2e} m, "
             f"{worst_rot:.2e} rad at {worst_at}")


main()
