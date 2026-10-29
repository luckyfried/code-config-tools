#!/usr/bin/env python3
"""Prove the exchange contract catches what it claims to catch.

USAGE:
  python scripts/contract_check.py [--bundle examples/arm] [--fixture examples/fixtures/orientation]

Part 1, the orientation fixture: a known-size asymmetric shape exported from Blender. The good
export must match the fixture's numbers (extents, volume, center of volume) and MuJoCo must
place the same center of mass. The wrong-axes export, the centimeter export, and a mirrored copy
must each be refused, with the reason.

Part 2, broken bundles: the good bundle passes `bundle.py check`, then each copy carries one
defect (missing asset, absolute path, path outside the folder, changed asset, nonphysical
inertia, center of mass outside the body, no inertial, visual geom that collides, wrong joint
mapping, unmapped joint, mesh exported with swapped axes, mesh exported in centimeters, a mesh
scale or a geom offset in the MJCF that Blender would not see) and must
fail the rule named for it. Copies live in a temporary folder under $TMPDIR.

Exit 0 when every expectation holds. The product does not run this for you: run it before you
trust a new Blender export or a changed contract.
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import mujoco  # noqa: E402
import bundle as bundle_tool  # noqa: E402
import simlib  # noqa: E402

RESULTS = []


def check(name, ok, detail):
    RESULTS.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<44} {detail}")


def fixture_truth(spec):
    vol, mom = 0.0, np.zeros(3)
    for b in spec["boxes"]:
        lo, hi = np.array(b["min"]), np.array(b["max"])
        v = float(np.prod(hi - lo))
        vol += v
        mom += v * (lo + hi) / 2
    lo = np.min([b["min"] for b in spec["boxes"]], axis=0)
    hi = np.max([b["max"] for b in spec["boxes"]], axis=0)
    return lo, hi, vol, mom / vol


def judge_mesh(verts, tris, truth, tol=1e-6):
    """None when the mesh is the fixture in meters, Z up, right-handed; else the reason."""
    lo, hi, vol, cen = truth
    vlo, vhi = verts.min(axis=0), verts.max(axis=0)
    ext, want = vhi - vlo, hi - lo
    if not np.allclose(ext, want, atol=tol):
        ratio = ext / want
        if np.allclose(ratio, ratio[0], rtol=1e-3) and abs(ratio[0] - 100) < 0.1:
            return f"extents {np.round(ext, 4).tolist()} are 100x the fixture: exported in centimeters"
        if np.allclose(sorted(ext), sorted(want), atol=tol):
            return f"extents {np.round(ext, 4).tolist()} are the fixture's in another order: axes swapped"
        return f"extents {np.round(ext, 4).tolist()}, fixture {want.tolist()}: wrong scale"
    mvol, mcen = bundle_tool.mesh_volume_centroid(verts, tris)
    if mvol < 0:
        return f"signed volume {mvol:.3e} is negative: faces wound inside out (a mirror flips winding)"
    if not np.allclose(cen, mcen, atol=tol):
        return f"center of volume {np.round(mcen, 5).tolist()}, fixture {np.round(cen, 5).tolist()}: mirrored or rotated"
    if abs(mvol - vol) > tol * vol + 1e-12:
        return f"volume {mvol:.6e}, fixture {vol:.6e}"
    return None


def mujoco_com(obj_path, workdir):
    """Load the mesh as the only geom of a body and read back MuJoCo's center of mass and volume.
    inertia="exact" integrates the mesh itself; MuJoCo's default uses its convex hull, which for
    this L-shaped fixture moves the center of mass by about 6 mm."""
    d = Path(workdir) / "com"
    d.mkdir(exist_ok=True)
    shutil.copy(obj_path, d / "m.obj")
    (d / "model.xml").write_text(
        '<mujoco><asset><mesh name="m" file="m.obj" inertia="exact"/></asset><worldbody>'
        '<body name="b"><freejoint/><geom type="mesh" mesh="m" density="1000"/></body></worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_path(str(d / "model.xml"))
    return m.body_ipos[1].copy(), m.body_mass[1] / 1000.0


def part_fixture(fixture, work):
    print("\norientation fixture")
    spec = json.loads((fixture / "fixture.json").read_text())
    truth = fixture_truth(spec)
    lo, hi, vol, cen = truth
    print(f"    fixture: extents {np.round(hi - lo, 4).tolist()} m, volume {vol:.6e} m^3, "
          f"center of volume {np.round(cen, 6).tolist()}")
    verts, tris = bundle_tool.read_obj(fixture / "fixture.obj")
    why = judge_mesh(verts, tris, truth)
    check("good export matches the fixture", why is None, why or f"{len(verts)} vertices, {len(tris)} triangles")
    com, mvol = mujoco_com(fixture / "fixture.obj", work)
    check("MuJoCo places the same center of mass", np.allclose(com, cen, atol=1e-6) and abs(mvol - vol) < 1e-9,
          f"body_ipos {np.round(com, 6).tolist()}, mass/density {mvol:.6e} m^3")
    for name, expect in (("fixture_wrong_axes.obj", "axes swapped"), ("fixture_centimeters.obj", "centimeters")):
        v, t = bundle_tool.read_obj(fixture / name)
        why = judge_mesh(v, t, truth)
        check(f"{name} is refused", why is not None and expect in why, why or "accepted")
    mv = verts * np.array([-1.0, 1.0, 1.0])
    why = judge_mesh(mv, tris, truth)
    check("mirrored copy (x -> -x) is refused", why is not None, why or "accepted")
    why = judge_mesh(mv, tris[:, ::-1], truth)
    check("mirrored copy with faces rewound is refused", why is not None, why or "accepted")


def edit(path, old, new):
    s = path.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"contract_check: expected exactly one '{old}' in {path.name}")
    path.write_text(s.replace(old, new))


def edit_json(path, fn):
    spec = json.loads(path.read_text())
    fn(spec)
    path.write_text(json.dumps(spec, indent=2))


def transform_obj(path, fn):
    lines = []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            v = fn(np.array([float(x) for x in line.split()[1:4]]))
            line = "v " + " ".join(f"{x:.6f}" for x in v)
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def run_check(path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = bundle_tool.check(path, as_json=True)
    return code, {r["rule"]: r for r in json.loads(out.getvalue())}


def reseal(path):
    with contextlib.redirect_stdout(io.StringIO()):
        bundle_tool.seal(path)


def part_mutations(good, work):
    print("\nbroken bundles")
    code, rules = run_check(good)
    check("the good bundle passes every rule", code == 0, ", ".join(f"{k} {'ok' if r['ok'] else 'FAIL'}"
                                                                     for k, r in rules.items()))
    fore = "meshes/fore_link.obj"
    cases = [
        ("missing asset", {"compile", "assets"}, lambda b: (b / fore).unlink()),
        ("absolute mesh path", {"assets"},
         lambda b: edit(b / "model.xml", 'meshdir="meshes"', f'meshdir="{(b / "meshes").resolve()}"')),
        ("mesh path outside the folder", {"assets", "compile"},
         lambda b: (shutil.copytree(b / "meshes", b.parent / f"{b.name}-outside"),
                    edit(b / "model.xml", 'meshdir="meshes"', f'meshdir="../{b.name}-outside"'))),
        ("asset changed after sealing", {"assets"},
         lambda b: (b / fore).write_text((b / fore).read_text() + "# edited\n")),
        ("inertia breaks the triangle inequality", {"compile", "inertia"},
         lambda b: edit(b / "model.xml", 'diaginertia="0.00027 0.004635 0.004635"',
                        'diaginertia="0.00027 0.0001 0.004635"')),
        ("center of mass outside the body", {"inertia"},
         lambda b: edit(b / "model.xml", '<inertial pos="0.125 0 0" mass="0.4"', '<inertial pos="0.6 0 0" mass="0.4"')),
        ("body without an inertial", {"inertia"},
         lambda b: edit(b / "model.xml", '<inertial pos="0.125 0 0" mass="0.4" diaginertia="0.000125 0.0021458 0.0021458"/>',
                        "")),
        ("visual geom takes part in contacts", {"visual_collision"},
         lambda b: edit(b / "model.xml", 'mesh="fore_visual"', 'mesh="fore_visual" contype="1"')),
        ("joint mapped with the wrong axis", {"joints"},
         lambda b: edit_json(b / "bundle.json", lambda s: s["joints"]["elbow"].update(axis=[0, 0, 1]))),
        ("joint mapped to the wrong parent", {"joints"},
         lambda b: edit_json(b / "bundle.json", lambda s: s["joints"]["elbow"].update(parent="base"))),
        ("joint not mapped", {"joints"}, lambda b: edit_json(b / "bundle.json", lambda s: s["joints"].pop("elbow"))),
        ("mesh exported with Y and Z swapped", {"visual_collision"},
         lambda b: (transform_obj(b / "meshes/base.obj", lambda v: v[[0, 2, 1]]), reseal(b))),
        ("mesh exported in centimeters", {"visual_collision"},
         lambda b: (transform_obj(b / fore, lambda v: v * 100), reseal(b))),
        ("mesh scaled in the MJCF instead of the export", {"visual_collision"},
         lambda b: (edit(b / "model.xml", 'file="base.obj"', 'file="base.obj" scale="100 100 100"'), reseal(b))),
        ("visual geom moved off its body frame", {"visual_collision"},
         lambda b: (edit(b / "model.xml", 'mesh="upper_visual"', 'mesh="upper_visual" pos="0 0 1"'), reseal(b))),
    ]
    for i, (name, expect, mutate) in enumerate(cases):
        b = work / f"case{i:02d}" / "bundle"
        shutil.copytree(good, b)
        mutate(b)
        code, rules = run_check(b)
        failed = {k for k, r in rules.items() if not r["ok"]}
        hit = failed & expect
        reason = " ".join("; ".join(rules[k]["detail"] for k in sorted(hit)).split())[:150] if hit else f"failed rules {sorted(failed)}"
        check(f"{name} is refused", code != 0 and hit, f"[{', '.join(sorted(hit)) or 'none'}] {reason}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", type=Path, default=simlib.KIT / "examples" / "arm")
    ap.add_argument("--fixture", type=Path, default=simlib.KIT / "examples" / "fixtures" / "orientation")
    a = ap.parse_args()
    simlib.check_engine()
    with tempfile.TemporaryDirectory(prefix="contract-", dir=os.environ.get("TMPDIR")) as tmp:
        part_fixture(a.fixture, Path(tmp))
        part_mutations(a.bundle.resolve(), Path(tmp))
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} expectations held")
    for n in failed:
        print(f"FAILED {n}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
