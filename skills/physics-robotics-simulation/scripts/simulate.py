#!/usr/bin/env python3
"""Run one bounded MuJoCo rollout of a bundle folder and write its trace and run record.

USAGE:
  python scripts/simulate.py BUNDLE_DIR --seconds 3 --out runs/arm
      [--controls BUNDLE_DIR/controls.json] [--record-every 1] [--print-every 0.25]
      [--max-steps 200000] [--max-wall-s 120]

Writes OUT/trace.json (one row per recorded step; timing in simlib.py) and OUT/run.json
(engine version, hashes, options, initial state, the per-step controls, warnings).
Exit 0 on a full rollout, 1 on a refusal, 3 when the rollout stopped early (cancelled,
wall-time bound, or diverged); the trace written so far is kept and says why.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mujoco  # noqa: E402
import simlib  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--controls", type=Path, default=None)
    ap.add_argument("--record-every", type=int, default=1)
    ap.add_argument("--print-every", type=float, default=0.25)
    ap.add_argument("--max-steps", type=int, default=200_000)
    ap.add_argument("--max-wall-s", type=float, default=120.0)
    a = ap.parse_args()
    try:
        simlib.check_engine()
        model = simlib.load_model(a.bundle)
        data = mujoco.MjData(model)
        simlib.reset_to_start(model, data)
        controls_path = a.controls or (a.bundle / "controls.json")
        controls = json.loads(controls_path.read_text()) if controls_path.is_file() else None
        nsteps = round(a.seconds / model.opt.timestep)
        bounds = simlib.Bounds(a.max_steps, a.max_wall_s)
        simlib.check_size(nsteps, a.record_every, bounds)
        seq = simlib.control_sequence(model, controls, nsteps)
        initial = simlib.get_state(model, data)
        simlib.install_cancel()
        result = simlib.rollout(model, data, seq, nsteps, a.record_every, bounds)
    except simlib.KitError as e:
        simlib.fail(str(e))
    record = simlib.run_record(a.bundle, model, initial, seq, result,
                               {"bundle": simlib.rel(a.bundle), "seconds": a.seconds,
                                "record_every": a.record_every})
    simlib.write_json(a.out / "trace.json", {"meta": {"bundle": simlib.rel(a.bundle),
                                                       "timestep": model.opt.timestep,
                                                       "record_every": a.record_every,
                                                       "stopped": result["stopped"]},
                                              "rows": result["rows"]})
    simlib.write_json(a.out / "run.json", record)
    stride = max(1, round(a.print_every / (model.opt.timestep * a.record_every)))
    print(f"mujoco {mujoco.mj_versionString()}  timestep {model.opt.timestep}  steps {result['steps_run']}  "
          f"wall {result['wall_s']:.3f}s  warnings {result['warnings'] or 'none'}")
    for row in result["rows"][::stride]:
        q = " ".join(f"{v:+.5f}" for v in row["qpos"][:7])
        print(f"t={row['t']:7.3f}  qpos [{q}]  E_pot={row['energy'][0]:+.5f}  E_kin={row['energy'][1]:.5f}  "
              f"contacts={len(row['contacts'])}")
    print(f"trace: {simlib.rel(a.out / 'trace.json')}  record: {simlib.rel(a.out / 'run.json')}")
    if result["stopped"]:
        print(f"stopped early: {result['stopped']}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
