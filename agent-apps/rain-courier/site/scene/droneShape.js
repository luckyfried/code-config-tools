// The courier drone built from parts: a ducted quad with a top deck, a nose camera, skids, a winch, and nav lights.
// models/drone.glb is this shape exported once; the page uses this module only when the model cannot load.
import * as THREE from "three";

export function droneMaterials() {
  return {
    Body: new THREE.MeshStandardMaterial({ name: "Body", color: 0x23262f, roughness: 0.32, metalness: 0.55 }),
    Trim: new THREE.MeshStandardMaterial({ name: "Trim", color: 0xff2d95, roughness: 0.35, metalness: 0.2, emissive: 0xff2d95, emissiveIntensity: 0.35 }),
    Metal: new THREE.MeshStandardMaterial({ name: "Metal", color: 0x8a8f99, roughness: 0.25, metalness: 0.95 }),
    Rubber: new THREE.MeshStandardMaterial({ name: "Rubber", color: 0x0d0e11, roughness: 0.8, metalness: 0 }),
    Glass: new THREE.MeshStandardMaterial({ name: "Glass", color: 0x05070c, roughness: 0.05, metalness: 0.9 }),
    Lamp: new THREE.MeshStandardMaterial({ name: "Lamp", color: 0xffffff, emissive: 0xfff2dc, emissiveIntensity: 3 }),
    NavRed: new THREE.MeshStandardMaterial({ name: "NavRed", color: 0x330000, emissive: 0xff1a1a, emissiveIntensity: 4 }),
    NavGreen: new THREE.MeshStandardMaterial({ name: "NavGreen", color: 0x003300, emissive: 0x1aff5a, emissiveIntensity: 4 }),
  };
}

function roundedRect(w, h, r) {
  const s = new THREE.Shape();
  s.moveTo(-w / 2 + r, -h / 2);
  s.lineTo(w / 2 - r, -h / 2);
  s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
  s.lineTo(w / 2, h / 2 - r);
  s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2);
  s.lineTo(-w / 2 + r, h / 2);
  s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
  s.lineTo(-w / 2, -h / 2 + r);
  s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  return s;
}

export const ROTORS = [
  [-0.62, 0.5],
  [0.62, 0.5],
  [-0.62, -0.5],
  [0.62, -0.5],
];

export function buildDroneShape(materials = droneMaterials()) {
  const m = materials;
  const root = new THREE.Group();
  root.name = "Drone";
  const add = (geometry, material, name, parent = root) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = name;
    parent.add(mesh);
    return mesh;
  };

  // Hull: a flattened teardrop, longer at the tail.
  const hullPts = [];
  for (let i = 0; i <= 24; i++) {
    const t = i / 24;
    const a = t * Math.PI;
    hullPts.push(new THREE.Vector2(Math.sin(a) * (0.34 + 0.05 * Math.sin(a)), -Math.cos(a) * 0.6));
  }
  const hull = add(new THREE.LatheGeometry(hullPts, 40), m.Body, "Hull");
  hull.rotation.x = Math.PI / 2;
  hull.scale.set(1, 1, 0.42);

  // Top deck with a trim stripe, the courier's colors.
  const deckGeometry = new THREE.ExtrudeGeometry(roundedRect(0.5, 0.9, 0.16), { depth: 0.035, bevelEnabled: true, bevelThickness: 0.015, bevelSize: 0.015, bevelSegments: 3, curveSegments: 10 });
  deckGeometry.rotateX(-Math.PI / 2);
  const deck = add(deckGeometry, m.Body, "Deck");
  deck.position.y = 0.11;
  const stripe = add(new THREE.BoxGeometry(0.09, 0.012, 0.86), m.Trim, "Stripe");
  stripe.position.set(0, 0.17, 0);
  for (const side of [-1, 1]) {
    const edge = add(new THREE.BoxGeometry(0.018, 0.02, 0.62), m.Trim, side < 0 ? "EdgeL" : "EdgeR");
    edge.position.set(side * 0.255, 0.115, -0.02);
  }

  // Nose: a camera in a gimbal ring, and a headlight bar above it.
  const gimbal = add(new THREE.TorusGeometry(0.085, 0.016, 10, 28), m.Metal, "Gimbal");
  gimbal.position.set(0, -0.06, 0.52);
  const lens = add(new THREE.SphereGeometry(0.07, 24, 16), m.Glass, "Lens");
  lens.position.set(0, -0.06, 0.53);
  const headlight = add(new THREE.BoxGeometry(0.26, 0.03, 0.03), m.Lamp, "Headlight");
  headlight.position.set(0, 0.06, 0.6);

  // Arms, motors, ducts, and two-blade props.
  ROTORS.forEach(([x, z], i) => {
    const from = new THREE.Vector3(Math.sign(x) * 0.22, 0.02, Math.sign(z) * 0.24);
    const to = new THREE.Vector3(x, 0.05, z);
    const len = from.distanceTo(to);
    const arm = add(new THREE.CylinderGeometry(0.032, 0.05, len, 10), m.Body, `Arm${i}`);
    arm.position.copy(from).lerp(to, 0.5);
    arm.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), to.clone().sub(from).normalize());
    const motor = add(new THREE.CylinderGeometry(0.07, 0.085, 0.1, 24), m.Metal, `Motor${i}`);
    motor.position.set(x, 0.07, z);
    const cap = add(new THREE.CylinderGeometry(0.05, 0.07, 0.025, 24), m.Trim, `Cap${i}`);
    cap.position.set(x, 0.13, z);
    const duct = add(new THREE.TorusGeometry(0.3, 0.022, 10, 48), m.Body, `Duct${i}`);
    duct.rotation.x = Math.PI / 2;
    duct.position.set(x, 0.12, z);
    const ductLip = add(new THREE.CylinderGeometry(0.31, 0.31, 0.07, 48, 1, true), m.Body, `DuctWall${i}`);
    ductLip.position.set(x, 0.1, z);
    for (let s = 0; s < 3; s++) {
      const strut = add(new THREE.BoxGeometry(0.24, 0.012, 0.02), m.Body, `Strut${i}_${s}`);
      const a = (s / 3) * Math.PI * 2 + 0.4;
      strut.position.set(x + Math.cos(a) * 0.19, 0.08, z + Math.sin(a) * 0.19);
      strut.rotation.y = -a;
    }
    const hub = new THREE.Group();
    hub.name = `Rotor${i}`;
    hub.position.set(x, 0.15, z);
    root.add(hub);
    const blade = add(new THREE.BoxGeometry(0.54, 0.008, 0.045), m.Rubber, `Prop${i}`, hub);
    blade.rotation.y = i * 0.7;
  });

  // Skids and the winch the package hangs from.
  for (const side of [-1, 1]) {
    const rail = add(new THREE.CapsuleGeometry(0.014, 0.62, 4, 10), m.Rubber, side < 0 ? "SkidL" : "SkidR");
    rail.rotation.x = Math.PI / 2;
    rail.position.set(side * 0.2, -0.24, 0);
    for (const fz of [-0.2, 0.2]) {
      const leg = add(new THREE.CylinderGeometry(0.011, 0.011, 0.2, 8), m.Metal, `Leg${side}${fz}`);
      leg.position.set(side * 0.17, -0.15, fz);
      leg.rotation.z = side * 0.3;
    }
  }
  const winch = add(new THREE.CylinderGeometry(0.05, 0.06, 0.07, 18), m.Metal, "Winch");
  winch.position.set(0, -0.14, -0.05);
  const hook = new THREE.Group();
  hook.name = "Hook";
  hook.position.set(0, -0.18, -0.05);
  root.add(hook);

  // Nav lights: red to port, green to starboard, a white strobe on the tail fin.
  const red = add(new THREE.SphereGeometry(0.03, 12, 8), m.NavRed, "NavRed");
  red.position.set(-0.93, 0.12, 0.5);
  const green = add(new THREE.SphereGeometry(0.03, 12, 8), m.NavGreen, "NavGreen");
  green.position.set(0.93, 0.12, 0.5);
  const fin = add(new THREE.BoxGeometry(0.02, 0.14, 0.16), m.Body, "Fin");
  fin.position.set(0, 0.2, -0.38);
  const strobe = add(new THREE.SphereGeometry(0.026, 12, 8), m.Lamp, "Strobe");
  strobe.position.set(0, 0.28, -0.4);
  const antenna = add(new THREE.CylinderGeometry(0.006, 0.006, 0.22, 6), m.Metal, "Antenna");
  antenna.position.set(0.12, 0.24, -0.3);
  antenna.rotation.x = -0.35;
  return root;
}
