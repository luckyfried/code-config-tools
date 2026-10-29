#!/usr/bin/env python3
"""Run the three examples and check what the physics did, not how it looks.

USAGE:
  python scripts/check_examples.py [--out runs/examples] [--only pendulum|drop|arm]

For each example: a bounded rollout with its state progression printed, physical checks
against numbers worked out independently of the engine, and reset correctness (a reset or a
restored checkpoint replays the rollout bit for bit). Writes OUT/<example>/trace.json and
run.json. Exit 0 only when every check passes.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import mujoco  # noqa: E402
import simlib  # noqa: E402

KIT = simlib.KIT
RESULTS = []


def check(example, name, ok, detail):
    RESULTS.append((example, name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<34} {detail}")


def run(example, seconds, out, record_every=1):
    bundle = KIT / "examples" / example
    model = simlib.load_model(bundle)
    data = mujoco.MjData(model)
    simlib.reset_to_start(model, data)
    cpath = bundle / "controls.json"
    controls = json.loads(cpath.read_text()) if cpath.is_file() else None
    seconds = controls.get("seconds", seconds) if controls else seconds
    nsteps = round(seconds / model.opt.timestep)
    seq = simlib.control_sequence(model, controls, nsteps)
    initial = simlib.get_state(model, data)
    result = simlib.rollout(model, data, seq, nsteps, record_every)
    rec = simlib.run_record(bundle, model, initial, seq, result, {"bundle": f"examples/{example}"})
    simlib.write_json(out / example / "trace.json", {"meta": {"bundle": f"examples/{example}",
                                                              "timestep": model.opt.timestep,
                                                              "record_every": record_every,
                                                              "stopped": result["stopped"]},
                                                     "rows": result["rows"]})
    simlib.write_json(out / example / "run.json", rec)
    print(f"\n{example}: mujoco {mujoco.mj_versionString()}, dt {model.opt.timestep} s, {nsteps} steps, "
          f"{mujoco.mjtIntegrator(int(model.opt.integrator)).name}, "
          f"wall {result['wall_s'] * 1000:.1f} ms, warnings {result['warnings'] or 'none'}")
    rows = result["rows"]
    stride = max(1, len(rows) // 8)
    shown = rows[::stride]
    for r in shown + ([rows[-1]] if shown[-1] is not rows[-1] else []):
        q = " ".join(f"{v:+.5f}" for v in r["qpos"][:3])
        print(f"    t={r['t']:6.3f}  qpos[:3]=[{q}]  E={r['energy'][0] + r['energy'][1]:+.6f} J  "
              f"contacts={len(r['contacts'])}")
    check(example, "rollout finished", result["stopped"] is None and not result["warnings"],
          f"stopped={result['stopped']} warnings={result['warnings']}")
    reset_checks(example, model, seq, nsteps, rows)
    return model, rows


def reset_checks(example, model, seq, nsteps, rows):
    def final_state(data, start, end):
        for i in range(start, end):
            data.ctrl[:] = seq[i] if model.nu else 0
            mujoco.mj_forward(model, data)
            mujoco.mj_step(model, data)
        return simlib.get_state(model, data)

    d = mujoco.MjData(model)
    simlib.reset_to_start(model, d)
    s0 = simlib.get_state(model, d)
    k = nsteps // 2
    sk = final_state(d, 0, k)
    s_end = final_state(d, k, nsteps)
    check(example, "rollout reproduces its trace", np.array_equal(d.qpos, rows[-1]["qpos"]),
          "a second rollout ends on the recorded final qpos bit for bit")
    simlib.reset_to_start(model, d)
    check(example, "reset restores the initial state", np.array_equal(simlib.get_state(model, d), s0),
          "mj_resetDataKeyframe('start') state equals the recorded initial state")
    check(example, "rollout after reset is identical", np.array_equal(final_state(d, 0, nsteps), s_end),
          "same final state, bit for bit")
    d2 = mujoco.MjData(model)
    simlib.set_state(model, d2, sk)
    check(example, "checkpoint restore is identical", np.array_equal(final_state(d2, k, nsteps), s_end),
          f"restore mjSTATE_INTEGRATION at step {k} into fresh data, replay to the end")


def pendulum(out):
    model, rows = run("pendulum", 3.0, out)
    m, d, g = 1.0, 0.5, 9.81
    I_pivot = 1e-4 + m * d * d
    theta0 = rows[0]["qpos"][0]
    k = math.sin(theta0 / 2)
    a, b = 1.0, math.sqrt(1 - k * k)
    for _ in range(30):
        a, b = (a + b) / 2, math.sqrt(a * b)
    K = math.pi / (2 * a)
    T_theory = 4 * math.sqrt(I_pivot / (m * g * d)) * K
    t = np.array([r["t"] for r in rows])
    w = np.array([r["qvel"][0] for r in rows])
    cross = [t[i] - w[i] * (t[i + 1] - t[i]) / (w[i + 1] - w[i])
             for i in range(len(w) - 1) if w[i] < 0 <= w[i + 1]]
    T_meas = float(np.mean(np.diff(cross))) if len(cross) >= 2 else float("nan")
    check("pendulum", "period matches large-angle theory", abs(T_meas - T_theory) / T_theory < 1e-3,
          f"measured {T_meas:.5f} s, theory {T_theory:.5f} s (elliptic integral, theta0 {theta0} rad)")
    E = np.array([r["energy"][0] + r["energy"][1] for r in rows])
    swing = m * g * d * (1 - math.cos(theta0))
    drift = float(np.max(np.abs(E - E[0]))) / swing
    check("pendulum", "energy conserved (RK4, no damping)", drift < 1e-6,
          f"max |E - E0| / swing energy = {drift:.2e}")
    bob = np.array(rows[-1]["sensors"]["bob_pos"])
    q = rows[-1]["qpos"][0]
    fk = np.array([-d * math.sin(q), 0.0, 1.0 - d * math.cos(q)])
    check("pendulum", "bob sensor matches kinematics", np.allclose(bob, fk, atol=1e-12),
          f"sensor {np.round(bob, 6).tolist()} vs (0,0,1) + 0.5*(-sin q, 0, -cos q), rotation about +Y")


def drop(out):
    model, rows = run("drop", 1.5, out)
    half, z0, g = 0.05, 0.5, 9.81
    t_contact_theory = math.sqrt(2 * (z0 - half) / g)
    first = next((r["t"] for r in rows if r["contacts"]), None)
    dt = model.opt.timestep
    check("drop", "first contact at free-fall time", first is not None and abs(first - t_contact_theory) < 2 * dt,
          f"first contact {first} s, theory {t_contact_theory:.5f} s, tolerance {2 * dt} s")
    fall = [r for r in rows if r["t"] < t_contact_theory - 2 * dt]
    # Semi-implicit Euler updates velocity first, so after n steps z = z0 - g dt^2 n (n + 1) / 2,
    # which is the continuous z0 - g t^2 / 2 less a further g t dt / 2.
    err = max(abs(r["qpos"][2] - (z0 - 0.5 * g * r["t"] * (r["t"] + dt))) for r in fall)
    lag = max(abs(r["qpos"][2] - (z0 - 0.5 * g * r["t"] ** 2)) for r in fall)
    check("drop", "free fall follows the Euler step exactly", err < 1e-9,
          f"max |z - (z0 - g t (t + dt) / 2)| {err:.1e} m; vs continuous z0 - g t^2 / 2 {lag:.2e} m (= g t dt / 2)")
    last = rows[-1]
    z_rest = last["qpos"][2]
    check("drop", "rests on the floor at half its size", abs(z_rest - half) < 2e-3,
          f"z {z_rest:.5f} m, half size {half} m (soft-contact penetration {half - z_rest:.2e} m)")
    speed = float(np.linalg.norm(last["qvel"][:3]))
    check("drop", "comes to rest", speed < 1e-3, f"|v| {speed:.2e} m/s at t={last['t']:.2f} s")
    n = len(last["contacts"])
    support = sum(c["normal_force"] for c in last["contacts"])
    check("drop", "four contacts carry its weight", n == 4 and abs(support - 0.5 * g) / (0.5 * g) < 0.01,
          f"{n} contacts, total normal force {support:.4f} N vs m g {0.5 * g:.4f} N")
    E = [r["energy"][0] + r["energy"][1] for r in rows]
    check("drop", "impact dissipates energy", E[-1] < E[0] - 0.5 * 9.81 * (z0 - half) * 0.9,
          f"E {E[0]:.4f} J -> {E[-1]:.4f} J")


def arm(out):
    model, rows = run("arm", 3.5, out)

    def at(t):
        return min(rows, key=lambda r: abs(r["t"] - t))

    def window(t0, t1):
        return [r for r in rows if t0 <= r["t"] <= t1]

    held = window(1.0, 1.2)
    err1 = max(max(abs(q - c) for q, c in zip(r["qpos"], r["ctrl"])) for r in held)
    check("arm", "reaches and holds the raised pose", err1 < 0.06 and not any(r["contacts"] for r in held),
          f"max |q - target| {err1:.4f} rad over t 1.0-1.2 s (gravity sag at kp 60), no contacts")
    press = window(2.0, 2.4)
    pad = [c for r in press for c in r["contacts"] if sorted(c["geoms"]) == ["fore_col", "pad"]]
    force = min((sum(c["normal_force"] for c in r["contacts"]) for r in press), default=0.0)
    check("arm", "presses the pad", len(pad) >= len(press) and force > 1.0,
          f"fore_col-pad contact in every row of t 2.0-2.4 s, least normal force {force:.3f} N")
    lo, hi = model.actuator_forcerange[:, 0], model.actuator_forcerange[:, 1]
    sat = max(abs(r["actuator_force"][0]) for r in press)
    check("arm", "the pad blocks the shoulder servo", abs(sat - hi[0]) < 1e-9 and
          max(abs(r["qpos"][0] - r["ctrl"][0]) for r in press) > 0.1,
          f"shoulder force {sat:.3f} N m at its {hi[0]} N m limit; target unreachable through the pad")
    inside = all(np.all(np.array(r["actuator_force"]) >= lo - 1e-9) and
                 np.all(np.array(r["actuator_force"]) <= hi + 1e-9) for r in rows)
    check("arm", "actuator forces stay in forcerange", inside, f"forcerange {lo.tolist()}..{hi.tolist()}")
    final = window(3.2, 3.5)
    err3 = max(max(abs(q - c) for q, c in zip(r["qpos"], r["ctrl"])) for r in final)
    check("arm", "releases and tracks the last pose", err3 < 0.06 and not any(r["contacts"] for r in final),
          f"max |q - target| {err3:.4f} rad over t 3.2-3.5 s, no contacts")
    r = at(2.2)
    q1, q2 = r["qpos"]
    fk = np.array([0.3 * math.cos(q1) + 0.25 * math.cos(q1 + q2), 0.0,
                   0.18 - 0.3 * math.sin(q1) - 0.25 * math.sin(q1 + q2)])
    tip = np.array(r["sensors"]["tip_pos"])
    check("arm", "tip sensor matches kinematics", np.allclose(tip, fk, atol=1e-12),
          f"tip {np.round(tip, 5).tolist()} vs planar two-link forward kinematics")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("runs/examples"))
    ap.add_argument("--only", choices=["pendulum", "drop", "arm"])
    a = ap.parse_args()
    try:
        simlib.check_engine()
        for name, fn in (("pendulum", pendulum), ("drop", drop), ("arm", arm)):
            if a.only in (None, name):
                fn(a.out)
    except simlib.KitError as e:
        simlib.fail(str(e))
    failed = [f"{e}: {n}" for e, n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for f in failed:
        print(f"FAILED {f}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
