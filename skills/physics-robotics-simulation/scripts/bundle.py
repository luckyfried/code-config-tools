#!/usr/bin/env python3
"""Seal or check an MJCF + local assets + bundle.json bundle (the Blender <-> MuJoCo exchange contract).

USAGE:
  python scripts/bundle.py seal  BUNDLE_DIR   # write asset hashes and static scenery into bundle.json
  python scripts/bundle.py check BUNDLE_DIR [--json]

check runs every contract rule and prints one line per rule; exit 0 only when all pass.
Rules: layout, engine, compile, assets, inertia, visual_collision, joints, portability.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import mujoco  # noqa: E402
import simlib  # noqa: E402

OBJ = mujoco.mjtObj


def read_obj(path: Path):
    """Vertices and triangles of an OBJ file (faces fanned into triangles)."""
    verts, tris = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
            idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
            tris += [[idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1)]
    return np.array(verts, dtype=float), np.array(tris, dtype=int)


def mesh_volume_centroid(verts, tris):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, c))
    vol = vol6.sum() / 6.0
    cen = ((a + b + c) * vol6[:, None]).sum(axis=0) / (24.0 * vol) if vol else np.zeros(3)
    return vol, cen


def static_scenery(model):
    out = []
    for g in range(model.ngeom):
        if model.geom_bodyid[g] != 0:
            continue
        gtype = mujoco.mjtGeom(model.geom_type[g]).name.replace("mjGEOM_", "").lower()
        out.append({"name": simlib.name_of(model, OBJ.mjOBJ_GEOM, g), "type": gtype,
                    "size": model.geom_size[g].tolist(), "pos": model.geom_pos[g].tolist(),
                    "quat_wxyz": model.geom_quat[g].tolist(), "rgba": model.geom_rgba[g].tolist()})
    return out


def seal(bundle: Path) -> int:
    spec = json.loads((bundle / "bundle.json").read_text())
    model = simlib.load_model(bundle)
    assets = []
    for tag, base, f in simlib.referenced_files(bundle):
        p = (bundle / base / f)
        role = "visual" if tag == "mesh" else tag
        body = next((b for b, m in spec["bodies"].items()
                     if os.path.normpath(m.get("visual_mesh", "")) == os.path.normpath(os.path.join(base, f))), None)
        assets.append({"path": os.path.normpath(os.path.join(base, f)), "sha256": simlib.sha256_file(p),
                       "role": role, "body": body})
    spec["assets"] = assets
    spec["static"] = static_scenery(model)
    spec["compiled_sha256"] = simlib.compiled_model_sha256(model)
    (bundle / "bundle.json").write_text(json.dumps(spec, indent=2) + "\n")
    print(f"sealed {simlib.rel(bundle / 'bundle.json')}: {len(assets)} assets, {len(spec['static'])} static geoms")
    return 0


def aabb_of_geom(model, g):
    """Axis-aligned box of a primitive collision geom in its body's frame."""
    t = mujoco.mjtGeom(int(model.geom_type[g]))
    s = model.geom_size[g]
    pos = model.geom_pos[g]
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, model.geom_quat[g])
    R = R.reshape(3, 3)
    if t == mujoco.mjtGeom.mjGEOM_BOX:
        half = np.abs(R) @ s
    elif t == mujoco.mjtGeom.mjGEOM_SPHERE:
        half = np.full(3, s[0])
    elif t in (mujoco.mjtGeom.mjGEOM_CAPSULE, mujoco.mjtGeom.mjGEOM_CYLINDER):
        ext = np.abs(R[:, 2]) * s[1]
        half = ext + (s[0] if t == mujoco.mjtGeom.mjGEOM_CAPSULE else s[0] * np.sqrt(1 - R[:, 2] ** 2))
    else:
        half = np.full(3, model.geom_rbound[g])
    return pos - half, pos + half


PLACE_TOL = 1e-5  # meters; OBJ text and MuJoCo's float32 vertices agree far closer than this


def placed_mesh_box(model, g):
    """Bounding box of a mesh geom's vertices in its body frame, as MuJoCo compiled them."""
    if model.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or model.geom_dataid[g] < 0:
        return None
    mid = model.geom_dataid[g]
    a, n = model.mesh_vertadr[mid], model.mesh_vertnum[mid]
    rot = np.zeros(9)
    mujoco.mju_quat2Mat(rot, model.geom_quat[g])
    placed = model.mesh_vert[a:a + n].astype(float) @ rot.reshape(3, 3).T + model.geom_pos[g]
    return placed.min(axis=0), placed.max(axis=0)


def check(bundle: Path, as_json=False) -> int:
    results = []

    def rule(name, ok, msg):
        results.append({"rule": name, "ok": bool(ok), "detail": msg})

    spec_path = bundle / "bundle.json"
    if not (bundle / "model.xml").is_file() or not spec_path.is_file():
        rule("layout", False, f"{simlib.rel(bundle)} needs model.xml and bundle.json")
        return report(results, as_json)
    spec = json.loads(spec_path.read_text())
    si = spec.get("units") == {"length": "m", "mass": "kg", "time": "s", "angle": "rad"}
    fr = spec.get("frame", {})
    frame_ok = fr.get("handedness") == "right" and fr.get("up") == "+Z" and fr.get("quaternion") == "wxyz"
    rule("layout", si and frame_ok, "SI units, right-handed, +Z up, wxyz quaternions" if si and frame_ok
         else f"units {spec.get('units')} frame {fr}: the contract is SI, right-handed, +Z up, wxyz")
    want = spec.get("engine", {}).get("mujoco")
    rule("engine", want == mujoco.__version__, f"bundle wants mujoco {want}, running {mujoco.__version__}")

    try:
        model = simlib.load_model(bundle)
    except simlib.KitError as e:
        rule("compile", False, str(e))
        return report(results, as_json)
    rule("compile", True, f"{model.nbody - 1} bodies, {model.njnt} joints, {model.nu} actuators, {model.ngeom} geoms")

    # assets: relative, inside the bundle, present, and hashed as sealed
    sealed = {a["path"]: a["sha256"] for a in spec.get("assets", [])}
    problems = []
    for tag, base, f in simlib.referenced_files(bundle):
        relp = os.path.normpath(os.path.join(base, f))
        if os.path.isabs(base) or os.path.isabs(f):
            problems.append(f"{tag} {f}: absolute path (a bundle uses paths relative to model.xml)")
            continue
        if relp.startswith(".."):
            problems.append(f"{tag} {relp}: points outside the bundle folder")
            continue
        p = bundle / relp
        if not p.is_file():
            problems.append(f"{tag} {relp}: file missing")
        elif relp not in sealed:
            problems.append(f"{tag} {relp}: not listed in bundle.json assets (run bundle.py seal)")
        elif simlib.sha256_file(p) != sealed[relp]:
            problems.append(f"{tag} {relp}: content differs from the sealed hash")
    rule("assets", not problems, "; ".join(problems) or f"{len(sealed)} assets relative, present, hashes match")

    # inertia: explicit, positive, physical, center of mass inside the collision geometry
    root = ET.parse(bundle / "model.xml").getroot()
    explicit = {b.get("name") for b in root.iter("body") if b.find("inertial") is not None}
    problems = []
    for b in range(1, model.nbody):
        name = simlib.name_of(model, OBJ.mjOBJ_BODY, b)
        if name not in spec.get("bodies", {}):
            continue
        m, I = model.body_mass[b], model.body_inertia[b]
        if name not in explicit:
            problems.append(f"{name}: no <inertial>; mass would come from geometry density, not an authored value")
        if m <= 0 or np.any(I <= 0):
            problems.append(f"{name}: mass {m} inertia {I.tolist()} must be positive")
        a, bb, c = sorted(I)
        if a + bb < c * (1 - 1e-9):
            problems.append(f"{name}: inertia {I.tolist()} breaks the triangle inequality")
        cols = [mujoco.mj_name2id(model, OBJ.mjOBJ_GEOM, g) for g in spec["bodies"][name].get("collision_geoms", [])]
        if cols and all(c >= 0 for c in cols):
            lo = np.min([aabb_of_geom(model, g)[0] for g in cols], axis=0)
            hi = np.max([aabb_of_geom(model, g)[1] for g in cols], axis=0)
            com = model.body_ipos[b]
            tol = spec.get("tolerances", {}).get("com_outside_collision_m", 0.0)
            if np.any(com < lo - tol) or np.any(com > hi + tol):
                problems.append(f"{name}: center of mass {com.tolist()} lies outside its collision geometry")
    rule("inertia", not problems, "; ".join(problems) or "every mapped body has an authored, physical inertial")

    # visual vs collision: visual meshes never collide and sit inside the collision primitives
    problems = []
    tol = spec.get("tolerances", {}).get("visual_outside_collision_m", 0.005)
    for name, m in spec.get("bodies", {}).items():
        b = mujoco.mj_name2id(model, OBJ.mjOBJ_BODY, name)
        vg = mujoco.mj_name2id(model, OBJ.mjOBJ_GEOM, m.get("visual_geom", ""))
        if b < 0 or vg < 0:
            problems.append(f"{name}: body or visual geom {m.get('visual_geom')} not in the model")
            continue
        if model.geom_bodyid[vg] != b:
            problems.append(f"{name}: visual geom {m['visual_geom']} belongs to another body")
        if model.geom_contype[vg] or model.geom_conaffinity[vg]:
            problems.append(f"{name}: visual geom {m['visual_geom']} takes part in contacts (set contype=0 conaffinity=0)")
        cols = [mujoco.mj_name2id(model, OBJ.mjOBJ_GEOM, g) for g in m.get("collision_geoms", [])]
        if not cols or any(c < 0 for c in cols):
            problems.append(f"{name}: collision geoms {m.get('collision_geoms')} missing")
            continue
        if not any(model.geom_contype[c] or model.geom_conaffinity[c] for c in cols):
            problems.append(f"{name}: no collision geom takes part in contacts")
        obj = bundle / m.get("visual_mesh", "")
        if not obj.is_file():
            continue
        verts, _ = read_obj(obj)
        vlo, vhi = verts.min(axis=0), verts.max(axis=0)
        placed = placed_mesh_box(model, vg)
        if placed is None:
            problems.append(f"{name}: visual geom {m['visual_geom']} is not a mesh")
            continue
        drift = max(float(np.max(np.abs(placed[0] - vlo))), float(np.max(np.abs(placed[1] - vhi))))
        if drift > PLACE_TOL:
            problems.append(f"{name}: MuJoCo places {m['visual_mesh']} {drift:.4f} m away from the file's own "
                            f"coordinates (a mesh scale, a geom pos or quat, or another file); Blender draws the "
                            f"file's coordinates in the body frame, so bake the transform into the export")
        lo = np.min([aabb_of_geom(model, c)[0] for c in cols], axis=0)
        hi = np.max([aabb_of_geom(model, c)[1] for c in cols], axis=0)
        out = max(float(np.max(lo - vlo)), float(np.max(vhi - hi)), 0.0)
        under = max(float(np.max(vlo - lo)), float(np.max(hi - vhi)), 0.0)
        if out > tol or under > tol:
            problems.append(f"{name}: visual mesh box {np.round(vlo, 4).tolist()}..{np.round(vhi, 4).tolist()} and "
                            f"collision box {np.round(lo, 4).tolist()}..{np.round(hi, 4).tolist()} differ by "
                            f"{max(out, under):.4f} m (tolerance {tol} m): check export axes, scale, and origin")
    rule("visual_collision", not problems, "; ".join(problems) or
         f"visual meshes are display-only and match their collision primitives within {tol} m")

    # joint mapping
    problems = []
    mapped = spec.get("joints", {})
    for j in range(model.njnt):
        jn = simlib.name_of(model, OBJ.mjOBJ_JOINT, j)
        if mujoco.mjtJoint(model.jnt_type[j]) == mujoco.mjtJoint.mjJNT_FREE:
            continue
        if jn not in mapped:
            problems.append(f"joint {jn} is not mapped in bundle.json")
    for jn, m in mapped.items():
        j = mujoco.mj_name2id(model, OBJ.mjOBJ_JOINT, jn)
        if j < 0:
            problems.append(f"joint {jn} is mapped but not in the model")
            continue
        child = simlib.name_of(model, OBJ.mjOBJ_BODY, model.jnt_bodyid[j])
        parent = simlib.name_of(model, OBJ.mjOBJ_BODY, model.body_parentid[model.jnt_bodyid[j]])
        jtype = mujoco.mjtJoint(model.jnt_type[j]).name.replace("mjJNT_", "").lower()
        if m.get("child") != child or m.get("parent") != parent:
            problems.append(f"joint {jn}: mapped {m.get('parent')}->{m.get('child')}, model has {parent}->{child}")
        if m.get("type") != jtype:
            problems.append(f"joint {jn}: mapped type {m.get('type')}, model has {jtype}")
        if not np.allclose(m.get("axis", [0, 0, 0]), model.jnt_axis[j], atol=1e-9):
            problems.append(f"joint {jn}: mapped axis {m.get('axis')}, model has {model.jnt_axis[j].tolist()}")
    objects = [m.get("blender_object") for m in spec.get("bodies", {}).values()]
    if len(set(objects)) != len(objects):
        problems.append(f"blender_object names repeat: {objects}")
    rule("joints", not problems, "; ".join(problems) or f"{len(mapped)} joints map one-to-one with parent, child, axis")

    # portability: the bundle copied elsewhere compiles to the same model
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        dst = Path(tmp) / "bundle"
        shutil.copytree(bundle, dst)
        try:
            same = simlib.compiled_model_sha256(simlib.load_model(dst)) == simlib.compiled_model_sha256(model)
            rule("portability", same, "a copy in a fresh folder compiles to the same model" if same
                 else "a copy in a fresh folder compiles differently: something outside the folder is read")
        except simlib.KitError as e:
            rule("portability", False, f"a copy in a fresh folder does not compile: {e}")
    return report(results, as_json)


def report(results, as_json):
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['rule']:<17} {r['detail']}")
    return 0 if results and all(r["ok"] for r in results) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["seal", "check"])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        return seal(a.bundle) if a.command == "seal" else check(a.bundle, a.json)
    except simlib.KitError as e:
        simlib.fail(str(e))


if __name__ == "__main__":
    sys.exit(main())
