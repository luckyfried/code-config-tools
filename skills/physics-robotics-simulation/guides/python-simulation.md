# Simulation in Python

Install once, in a virtual environment: `python -m pip install -r requirements.txt` (mujoco
3.17.0, numpy, PyOpenGL). `python scripts/doctor.py` says what is present.

## Run a bundle

```
python scripts/simulate.py examples/arm --seconds 3.5 --out runs/arm
```

It loads `model.xml`, refuses when mujoco is not 3.17.0, resets to keyframe `start`, applies the
controls in `controls.json` (if the bundle has one), and writes `runs/arm/trace.json` (one row per
recorded step) and `runs/arm/run.json` (the reproducibility record, see `reproducibility.md`). It
prints a line of state every `--print-every` seconds. Exit 0 when the run finished, 3 when it
stopped early (diverged, wall-time bound, or Ctrl-C), 1 when it refused to start.

## Observation timing

This is the rule every trace in the kit follows, Python and WebAssembly alike:

1. write control u_i into `data.ctrl`;
2. `mj_forward` (positions, contacts, sensors and energy at t_i, under u_i);
3. record row i;
4. `mj_step` to t_i + dt.

So row i is the state at time t_i with u_i applied, and u_i is held over [t_i, t_i + dt). The
last row repeats the last control. Sensor values in row i are consistent with the qpos in row i.
A trace written any other way cannot be compared row for row with these.

## Controls

`controls.json` lists `actuators` by name and `segments`, each a `t`, a `ramp_s` time and a
`target` per actuator; the ramp is a minimum-jerk blend from the value at the segment's start.
Targets outside an actuator's `ctrlrange` are clamped. `simlib.control_sequence` turns it into
one control row per step, which `run.json` stores in full (`controls.per_step`) with its hash.
`simlib.rollout` takes the whole control sequence in advance. For a feedback controller, use
MuJoCo's step loop directly: compute u_i from current `data.qpos` and `data.qvel`, set `data.ctrl`,
call `mj_forward`, record with `simlib.observe`, then call `mj_step`. If the controller reads
sensors or other derived values, call `mj_forward` before reading those values too.

## Bounds

A run longer than `--max-steps` (default 200000) or one whose trace would pass 50000 rows is
refused before it starts (raise the bound, or `--record-every`). While it runs it stops early, with
the reason in `run.json` and exit 3, at the wall-time bound (`--max-wall-s`, default 120 s:
`stopped: wall_time_bound`), when the state goes unstable (`stopped: diverged`: a NaN or Inf, or
a bad position, velocity or acceleration that MuJoCo caught and reset itself, which would otherwise
look like a short clean run that restarted at t = 0), or on Ctrl-C
(`stopped: cancelled`); the rows up to that point are kept. MuJoCo's own warnings (`data.warning`, for example contact buffer full or
a bad qacc) are counted into `run.json`; a run with warnings is not a clean run.

## Reset and checkpoints

- Reset: `mj_resetDataKeyframe(model, data, key("start"))`, then `mj_forward`.
- Checkpoint: `mj_getState(model, data, state, mjSTATE_INTEGRATION)` and `mj_setState`. The
  INTEGRATION set includes the solver's warm start, so a restored run continues bit for bit
  (`check_examples.py` checks this for all three examples). `mjSTATE_PHYSICS` leaves out the
  warm start: restored mid-contact in the drop example it ends 2e-18 m off, which is small but no
  longer the same run.

## Checks that come with the examples

`python scripts/check_examples.py` runs all three and checks them against numbers worked out
without the engine:

| example | what it checks |
|---|---|
| pendulum | period against the large-angle elliptic-integral value (within 0.1 %), energy constant under RK4, the bob's position sensor against forward kinematics |
| drop | first contact at the free-fall time sqrt(2h/g), free fall matching the Euler step exactly, rest at half its size with four contacts carrying m·g, energy lost on impact |
| arm | reaches and holds its raised pose, presses the pad, the shoulder saturates at its force limit, forces stay in forcerange, it releases, tip sensor against two-link kinematics |

and for each: a second rollout reproduces the trace, reset restores the initial state, a run after
reset matches, and a checkpoint restored into fresh data finishes on the same state.

## Plots

`trace.json` rows hold `t`, `qpos`, `qvel`, `ctrl`, `actuator_force`, `energy` [potential,
kinetic], `sensors` by name, body poses, and contacts. Plot from that file with matplotlib or any
tool; never plot from numbers you did not record.

## Quick look without Blender

`python scripts/render_check.py examples/arm --camera side --out arm.png` renders one frame
offscreen with MuJoCo's renderer: `MUJOCO_GL=egl` first, then `osmesa`, each in a fresh process,
and a frame with no contrast counts as a failure. If neither works it names what to install and
exits 2; simulation does not need a renderer.
