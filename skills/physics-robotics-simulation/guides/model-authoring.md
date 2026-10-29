# Model authoring (MJCF)

Write the model as a small MJCF file a person can read. Grow it one body at a time, and run
a short `scripts/simulate.py` run after each body. For a model with Blender meshes, also seal
and check its `bundle.json` with `scripts/bundle.py` (see `exchange-contract.md`).

## Units and frames

- SI only: meters, kilograms, seconds, radians, newtons, newton-meters. Put
  `<compiler angle="radian"/>` in every model; MJCF's own default is degrees, and a mix of the two is
  the most common silent error.
- +Z is up and the frame is right-handed. Quaternions are `w x y z`.
- A body's `pos` and `quat` are relative to its parent. A geom's are relative to its body.

## Mass and inertia

- Give every moving body an explicit `<inertial pos mass diaginertia>` (or `fullinertia`). Mass
  computed from geom density is fine for a sketch, but the contract check refuses it, because the
  value then depends on the collision shapes you happen to use.
- Check the numbers: a solid box of side a, b, c and mass m has `I = m/12 * (b²+c², a²+c², a²+b²)`;
  a rod of length L about its end has `m L² / 3`. The principal moments must be positive and obey
  `A + B >= C` (MuJoCo refuses the model otherwise). The center of mass must sit inside the body's
  collision shape (`bundle.py check` tests it).
- MuJoCo computes a mesh's mass properties from its convex hull unless the mesh says
  `inertia="exact"`. For a concave part, the hull moves the center of mass (6 mm on the L-shaped
  test fixture in `examples/fixtures/orientation`). Author the inertial instead, or use `exact`
  on a closed mesh.
- Very light bodies under stiff joints or high gains make the step unstable. Add `armature` to
  joints (0.01 in the arm example) before you shrink the timestep.

## Joints, actuators and limits

- `hinge` and `slide` joints take an `axis` in the body frame; `ball` and `free` take none. Set
  `range` for every limited joint, and `<compiler autolimits="true"/>` turns limits on when a
  range is given.
- `damping` belongs on the joint, not in a controller.
- Prefer `position` actuators with `kp` (and `kv` or joint damping) for servos, `motor` for torque
  control, `velocity` for wheels. Give each one `ctrlrange` (what a command may ask) and
  `forcerange` (what the motor can give). The arm example's shoulder hits its 8 N·m force limit
  against the pad, which `check_examples.py` checks.
- A position servo under gravity sits below its target by `torque / kp`; that is physics, not a
  bug (0.04 rad on the arm at kp 60).

## Contacts

- Collision geoms are primitives where you can (box, capsule, sphere, cylinder); a mesh collides
  as its convex hull. Visual meshes take no part in contacts: `contype="0" conaffinity="0"`, and
  a separate group (`group="1"`) from the collision geoms (`group="3"`).
- Exclude contacts between parent and child bodies that overlap at the joint
  (`<contact><exclude body1 body2/>`).
- Read contact results from `data.contact` and `mj_contactForce`; the kit's
  `simlib.observe` records each contact's geoms, distance, position and normal force.
- Penetration of a resting body (0.1 mm for the drop example) comes from MuJoCo's soft contacts
  and is set by `solref`/`solimp`. Change those only with a measurement before and after.

## Sensors

Name every sensor you will plot. `jointpos`, `jointvel`, `actuatorfrc`, `framepos`,
`framequat`, `touch`, `accelerometer`, `gyro` cover most work. The kit writes every named sensor
into each trace row by name.

## Options

- `timestep` 0.001 to 0.002 s for robots of this size; smaller for stiff contacts or light
  bodies. Choose the integrator on purpose: `RK4` for smooth systems with no contact (the
  pendulum conserves energy to 1e-12 of its swing energy), `implicitfast` for actuated robots
  with damping and contact, `Euler` (the default) for simple contact scenes.
- `<flag energy="enable"/>` makes MuJoCo compute potential and kinetic energy, which the traces
  record and the checks use.

## URDF

MuJoCo compiles URDF directly (`mujoco.MjModel.from_xml_path("robot.urdf")`), then
`mujoco.mj_saveLastXML("robot.xml", model)` writes MJCF you can edit. Before trusting a URDF:

- mesh paths with `package://` do not resolve; copy the meshes next to the file and use relative
  paths;
- URDF has no actuators: add them in the MJCF;
- check every link's inertial (URDF exporters often write zero or identity inertia), and that
  `fixed` joints really merge (MuJoCo fuses them unless `<compiler fusestatic="false"/>`);
- URDF collision meshes become convex hulls.

## Keyframes

Name one keyframe `start`. The kit's reset, checkpoint and replay tools use it as the initial
state; without it they use the model's defaults.
