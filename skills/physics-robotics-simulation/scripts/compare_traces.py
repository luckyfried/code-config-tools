#!/usr/bin/env python3
"""Compare two traces of the same run, row by row: the Python run and its WebAssembly replay.

USAGE:
  python scripts/compare_traces.py PYTHON_TRACE.json WASM_TRACE.json
         [--tol-pos 1e-6] [--tol-vel 1e-5] [--tol-force 1e-4]

Both traces record the same observation timing (u_i written, mj_forward, row i, mj_step), so
row i of each is the state at the same t_i under the same control. Positions (qpos, body
positions in m, joint angles in rad, quaternion components) must agree within --tol-pos,
velocities within --tol-vel, actuator forces within --tol-force, and contact counts exactly.
Prints the largest measured difference of each and the row it occurred at. Exit 0 when every
difference is inside its tolerance, 1 otherwise.

Same engine version, same compiled model and same controls normally give differences at the
level of floating-point rounding (1e-12 or below). A larger difference that still passes means
the two builds round differently; a failure means the inputs differ (version, model, controls,
initial state) or the run is chaotic enough that rounding has grown, which a contact-rich scene
can do over a long horizon: compare a shorter run.
"""
import argparse
import json
import sys

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("python_trace")
    ap.add_argument("wasm")
    ap.add_argument("--tol-pos", type=float, default=1e-6)
    ap.add_argument("--tol-vel", type=float, default=1e-5)
    ap.add_argument("--tol-force", type=float, default=1e-4)
    a = ap.parse_args()
    na = json.load(open(a.python_trace))
    wa = json.load(open(a.wasm))
    rec_every = na.get("meta", {}).get("record_every", 1)
    if rec_every != 1:
        print(f"the Python trace recorded every {rec_every} steps; rerun simulate.py with --record-every 1")
        return 1
    nr, wr = na["rows"], wa["rows"]
    if len(nr) != len(wr):
        print(f"row counts differ: python {len(nr)}, wasm {len(wr)}")
        return 1
    worst = {k: (0.0, None) for k in ("t", "qpos", "qvel", "body_pos", "body_quat", "actuator_force")}
    contact_mismatch = []

    def note(key, diff, i):
        if diff > worst[key][0]:
            worst[key] = (diff, i)

    for i, (n, w) in enumerate(zip(nr, wr)):
        note("t", abs(n["t"] - w["t"]), i)
        note("qpos", float(np.max(np.abs(np.subtract(n["qpos"], w["qpos"])), initial=0)), i)
        note("qvel", float(np.max(np.abs(np.subtract(n["qvel"], w["qvel"])), initial=0)), i)
        note("actuator_force", float(np.max(np.abs(np.subtract(n["actuator_force"], w["actuator_force"])),
                                            initial=0)), i)
        for name, b in n["bodies"].items():
            wb = w["bodies"][name]
            note("body_pos", float(np.max(np.abs(np.subtract(b["pos"], wb["pos"])))), i)
            q, wq = np.array(b["quat_wxyz"]), np.array(wb["quat_wxyz"])
            note("body_quat", float(min(np.max(np.abs(q - wq)), np.max(np.abs(q + wq)))), i)
        ncon_n = len(n["contacts"]) if "contacts" in n else n.get("ncon")
        if ncon_n != w["ncon"]:
            contact_mismatch.append((i, ncon_n, w["ncon"]))
    tol = {"t": 1e-12, "qpos": a.tol_pos, "qvel": a.tol_vel, "body_pos": a.tol_pos, "body_quat": a.tol_pos,
           "actuator_force": a.tol_force}
    ok = True
    print(f"{len(nr)} rows compared")
    for k, (d, i) in worst.items():
        good = d <= tol[k]
        ok &= good
        where = f"(row {i}, t={nr[i]['t']:.3f})" if i is not None else ""
        print(f"  {'PASS' if good else 'FAIL'}  {k:<15} max |diff| {d:.3e}  tolerance {tol[k]:.0e} {where}")
    if contact_mismatch:
        ok = False
        i, cn, cw = contact_mismatch[0]
        print(f"  FAIL  contacts        {len(contact_mismatch)} rows differ; first at row {i}: python {cn}, wasm {cw}")
    else:
        print("  PASS  contacts        same count in every row")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
