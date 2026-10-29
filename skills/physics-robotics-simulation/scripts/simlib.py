"""Shared MuJoCo helpers for the physics-robotics-simulation kit.

Observation timing, used by every trace this kit writes:
  row i is the state at time t_i = i * timestep. Before row i is recorded the
  control u_i is written to data.ctrl and mj_forward runs, so every derived
  quantity in the row (body poses, sensors, contacts, energy, actuator force)
  is consistent with qpos/qvel at t_i and with u_i. u_i is then held for the
  step from t_i to t_{i+1} (mj_step). The last row repeats the last control.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import signal
import sys
import time
from pathlib import Path

import numpy as np
import mujoco

PINNED_MUJOCO = "3.17.0"
SCRIPTS = Path(__file__).resolve().parent
KIT = SCRIPTS.parent


class KitError(Exception):
    """A refusal a person can act on. The message says what to change."""


def check_engine() -> None:
    if mujoco.__version__ != PINNED_MUJOCO:
        raise KitError(
            f"mujoco {mujoco.__version__} is installed; this kit is tested with {PINNED_MUJOCO}. "
            f"Run: python -m pip install -r {rel(KIT / 'requirements.txt')}"
        )


def rel(path: Path) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compiled_model_sha256(model: mujoco.MjModel) -> str:
    """Hash of every compiled model array and option except file paths, so a bundle hashes the same in any folder."""
    h = hashlib.sha256()
    for name in sorted(dir(model)):
        if name.startswith("_") or name == "paths" or name.endswith("pathadr"):
            continue
        try:
            value = getattr(model, name)
        except Exception:
            continue
        if isinstance(value, np.ndarray):
            h.update(name.encode())
            h.update(np.ascontiguousarray(value).tobytes())
    for field in ("timestep", "integrator", "solver", "cone", "iterations", "tolerance", "gravity",
                  "disableflags", "enableflags", "impratio", "noslip_iterations", "jacobian"):
        h.update(field.encode())
        h.update(repr(np.asarray(getattr(model.opt, field)).tolist()).encode())
    return h.hexdigest()


def load_model(bundle_dir: Path) -> mujoco.MjModel:
    xml = Path(bundle_dir) / "model.xml"
    if not xml.is_file():
        raise KitError(f"{rel(xml)} does not exist: a bundle folder holds model.xml and its assets")
    try:
        return mujoco.MjModel.from_xml_path(str(xml))
    except ValueError as e:
        raise KitError(f"MuJoCo refused {rel(xml)}: {e}") from None


def name_of(model, objtype, i) -> str:
    return mujoco.mj_id2name(model, objtype, i) or f"#{i}"


def reset_to_start(model, data) -> None:
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "start")
    if key >= 0:
        mujoco.mj_resetDataKeyframe(model, data, key)
    else:
        mujoco.mj_resetData(model, data)


def get_state(model, data, spec=mujoco.mjtState.mjSTATE_INTEGRATION) -> np.ndarray:
    state = np.empty(mujoco.mj_stateSize(model, spec))
    mujoco.mj_getState(model, data, state, spec)
    return state


def set_state(model, data, state, spec=mujoco.mjtState.mjSTATE_INTEGRATION) -> None:
    mujoco.mj_setState(model, data, state, spec)


# ---------------------------------------------------------------- controls

def minjerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (10 - 15 * s + 6 * s * s)


def control_sequence(model, controls: dict | None, nsteps: int) -> np.ndarray:
    """One row of controls per step, clamped to each actuator's ctrlrange."""
    seq = np.zeros((nsteps, model.nu))
    if controls is None or model.nu == 0:
        return seq
    names = controls["actuators"]
    ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, n) for n in names]
    missing = [n for n, i in zip(names, ids) if i < 0]
    if missing:
        raise KitError(f"controls.json names actuators the model does not have: {missing}")
    segs = sorted(controls["segments"], key=lambda s: s["t"])
    dt = model.opt.timestep

    def value(k, t, start):
        seg = segs[k]
        ramp = max(seg.get("ramp_s", 0.0), 1e-9)
        goal = np.asarray(seg["target"], dtype=float)
        return start + (goal - start) * minjerk((t - seg["t"]) / ramp)

    starts = [np.zeros(len(ids))]
    for k in range(1, len(segs)):
        starts.append(value(k - 1, segs[k]["t"], starts[k - 1]))
    for i in range(nsteps):
        t = i * dt
        k = max((j for j, seg in enumerate(segs) if seg["t"] <= t + 1e-12), default=None)
        target = starts[0] if k is None else value(k, t, starts[k])
        for j, a in enumerate(ids):
            seq[i, a] = target[j]
    lo = model.actuator_ctrlrange[:, 0]
    hi = model.actuator_ctrlrange[:, 1]
    limited = model.actuator_ctrllimited.astype(bool)
    seq[:, limited] = np.clip(seq[:, limited], lo[limited], hi[limited])
    return seq


# ---------------------------------------------------------------- observe

def observe(model, data) -> dict:
    sensors = {}
    for i in range(model.nsensor):
        adr, dim = model.sensor_adr[i], model.sensor_dim[i]
        sensors[name_of(model, mujoco.mjtObj.mjOBJ_SENSOR, i)] = data.sensordata[adr:adr + dim].tolist()
    bodies = {}
    for b in range(1, model.nbody):
        bodies[name_of(model, mujoco.mjtObj.mjOBJ_BODY, b)] = {
            "pos": data.xpos[b].tolist(),
            "quat_wxyz": data.xquat[b].tolist(),
        }
    contacts = []
    f6 = np.zeros(6)
    for c in range(data.ncon):
        con = data.contact[c]
        mujoco.mj_contactForce(model, data, c, f6)
        contacts.append({
            "geoms": [name_of(model, mujoco.mjtObj.mjOBJ_GEOM, int(g)) for g in con.geom],
            "dist": float(con.dist),
            "pos": con.pos.tolist(),
            "normal_force": float(f6[0]),
        })
    return {
        "t": float(data.time),
        "qpos": data.qpos.tolist(),
        "qvel": data.qvel.tolist(),
        "ctrl": data.ctrl.tolist(),
        "actuator_force": data.actuator_force.tolist(),
        "energy": [float(data.energy[0]), float(data.energy[1])],
        "sensors": sensors,
        "bodies": bodies,
        "contacts": contacts,
    }


# ---------------------------------------------------------------- rollout

class Bounds:
    def __init__(self, max_steps=200_000, max_wall_s=120.0, max_rows=50_000):
        self.max_steps, self.max_wall_s, self.max_rows = max_steps, max_wall_s, max_rows


_cancel = {"flag": False}


def _on_signal(signum, frame):
    _cancel["flag"] = True


def install_cancel() -> None:
    """Ctrl-C or SIGTERM stops a rollout at the next step; the partial trace is kept and marked."""
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)


BAD_STATE = (mujoco.mjtWarning.mjWARN_BADQACC, mujoco.mjtWarning.mjWARN_BADQVEL, mujoco.mjtWarning.mjWARN_BADQPOS)


def check_size(nsteps: int, record_every: int, bounds: Bounds) -> None:
    """Refuse a rollout larger than its bounds before any work is done for it."""
    if nsteps > bounds.max_steps:
        raise KitError(f"{nsteps} steps asked; the bound is {bounds.max_steps} (raise --max-steps on purpose)")
    if nsteps // max(record_every, 1) + 1 > bounds.max_rows:
        raise KitError(f"the trace would hold more than {bounds.max_rows} rows; raise --record-every")


def bad_state_count(data) -> int:
    """MuJoCo resets an unstable state itself and counts it in these warnings; any count is a divergence."""
    return sum(int(data.warning[int(w)].number) for w in BAD_STATE)


def rollout(model, data, ctrl_seq: np.ndarray, nsteps: int, record_every: int = 1,
            bounds: Bounds | None = None) -> dict:
    bounds = bounds or Bounds()
    check_size(nsteps, record_every, bounds)
    bad_before = bad_state_count(data)
    rows, stopped = [], None
    start = time.monotonic()
    for i in range(nsteps + 1):
        if model.nu:
            data.ctrl[:] = ctrl_seq[min(i, nsteps - 1)] if nsteps else 0.0
        mujoco.mj_forward(model, data)
        if i % record_every == 0 or i == nsteps:
            rows.append(observe(model, data))
        if i == nsteps:
            break
        if _cancel["flag"]:
            stopped = "cancelled"
            break
        if time.monotonic() - start > bounds.max_wall_s:
            stopped = "wall_time_bound"
            break
        mujoco.mj_step(model, data)
        if bad_state_count(data) > bad_before or not np.all(np.isfinite(data.qacc)):
            stopped = "diverged"
            break
    warnings = {}
    for w in range(len(data.warning)):
        n = int(data.warning[w].number)
        if n:
            warnings[mujoco.mjtWarning(w).name] = n
    return {
        "rows": rows,
        "steps_run": i,
        "stopped": stopped,
        "wall_s": time.monotonic() - start,
        "warnings": warnings,
    }


def run_record(bundle_dir: Path, model, initial_state, ctrl_seq, result, extra=None) -> dict:
    bundle_dir = Path(bundle_dir)
    assets = [{"path": relp, "sha256": sha256_file(bundle_dir / relp)}
              for relp in (os.path.normpath(os.path.join(base, f)) for _, base, f in referenced_files(bundle_dir))]
    opt = model.opt
    return {
        "engine": {"name": "mujoco", "version": mujoco.mj_versionString(), "python_package": mujoco.__version__},
        "host": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
        "model": {
            "file": "model.xml",
            "sha256": sha256_file(bundle_dir / "model.xml"),
            "compiled_sha256": compiled_model_sha256(model),
            "assets": assets,
        },
        "options": {
            "timestep": opt.timestep,
            "integrator": mujoco.mjtIntegrator(opt.integrator).name,
            "solver": mujoco.mjtSolver(opt.solver).name,
            "cone": mujoco.mjtCone(opt.cone).name,
            "iterations": int(opt.iterations),
            "tolerance": opt.tolerance,
            "noslip_iterations": int(opt.noslip_iterations),
            "gravity": opt.gravity.tolist(),
            "disableflags": int(opt.disableflags),
            "enableflags": int(opt.enableflags),
        },
        "initial_state": {"spec": "mjSTATE_INTEGRATION", "values": initial_state.tolist()},
        "controls": {
            "per_step": ctrl_seq.tolist(),
            "sha256": hashlib.sha256(np.ascontiguousarray(ctrl_seq).tobytes()).hexdigest(),
        },
        "observation_timing": "row i = state at t_i after mj_forward with u_i written; u_i is held over [t_i, t_i+dt)",
        "steps_run": result["steps_run"],
        "stopped": result["stopped"],
        "wall_s": result["wall_s"],
        "warnings": result["warnings"],
        **(extra or {}),
    }


def referenced_files(bundle_dir: Path):
    """(tag, directory from <compiler>, file) for every file model.xml names."""
    import xml.etree.ElementTree as ET
    root = ET.parse(Path(bundle_dir) / "model.xml").getroot()
    comp = root.find("compiler")
    meshdir = comp.get("meshdir", "") if comp is not None else ""
    texdir = comp.get("texturedir", "") if comp is not None else ""
    files = []
    for el in root.iter():
        f = el.get("file")
        if f:
            base = meshdir if el.tag in ("mesh", "hfield", "skin") else texdir if el.tag == "texture" else ""
            files.append((el.tag, base, f))
    return files


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=None, separators=(",", ":"))
    os.replace(tmp, path)


def fail(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)
