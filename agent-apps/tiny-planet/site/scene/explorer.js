// The round explorer, built from primitives: a body, a face, a backpack with a bedroll, a scarf with a tail, two
// feet, two hands, and a lantern antenna lit in the crystal color. It squashes on landing and stretches on the jump
// (a spring on scale), stays stretched while it rises and tucks as it falls, swings its feet and hands with the
// stride, and leans into the slope and the turn. A soft contact shadow sits on the ground under it, shrinking and
// fading as it jumps, so a hop always reads as one.
import * as THREE from "three";
import { contactShadowMaterial, explorerMaterial, gemMaterial } from "./materials.js";

export function buildExplorer(colors) {
  const root = new THREE.Group();
  root.name = "explorer";
  const lean = new THREE.Group();
  const squash = new THREE.Group();
  const body = new THREE.Group();
  root.add(lean);
  lean.add(squash);
  squash.add(body);

  const bodyMat = explorerMaterial(colors.explorerBody);
  const scarfMat = explorerMaterial(colors.explorerScarf);
  const packMat = explorerMaterial(colors.explorerPack);
  const dark = explorerMaterial(new THREE.Color(0.06, 0.05, 0.06));
  const white = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const bellyMat = explorerMaterial(colors.explorerBody.clone().lerp(new THREE.Color(1, 1, 1), 0.45));

  const torso = new THREE.Mesh(new THREE.SphereGeometry(0.5, 24, 16), bodyMat);
  torso.scale.set(1, 1.04, 0.96);
  torso.position.y = 0.62;
  const belly = new THREE.Mesh(new THREE.SphereGeometry(0.34, 18, 12), bellyMat);
  belly.scale.set(1, 1.05, 0.5);
  belly.position.set(0, 0.52, 0.31);

  const eyeGeo = new THREE.SphereGeometry(0.075, 12, 8);
  const shineGeo = new THREE.SphereGeometry(0.025, 8, 6);
  const eyes = new THREE.Group();
  for (const x of [-0.16, 0.16]) {
    const eye = new THREE.Mesh(eyeGeo, dark);
    eye.scale.set(0.85, 1.15, 0.6);
    eye.position.set(x, 0.78, 0.43);
    const shine = new THREE.Mesh(shineGeo, white);
    shine.position.set(x + 0.025, 0.81, 0.48);
    eyes.add(eye, shine);
  }

  const scarf = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.075, 8, 24), scarfMat);
  scarf.rotation.x = Math.PI / 2;
  scarf.position.y = 0.43;
  scarf.scale.set(1, 1, 1.1);
  const tailPivot = new THREE.Group();
  tailPivot.position.set(0.18, 0.43, -0.34);
  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.05, 0.36), scarfMat);
  tail.position.z = -0.17;
  tailPivot.add(tail);

  const pack = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.52, 0.26, 2, 2, 2), packMat);
  pack.position.set(0, 0.62, -0.47);
  const roll = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.56, 12), scarfMat);
  roll.rotation.z = Math.PI / 2;
  roll.position.set(0, 0.95, -0.47);

  const stalk = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.022, 0.32, 6), dark);
  stalk.position.set(0, 1.25, 0);
  const lamp = new THREE.Mesh(new THREE.OctahedronGeometry(0.075, 0), gemMaterial(colors.crystal));
  lamp.scale.set(1, 1.4, 1);
  lamp.position.set(0, 1.45, 0);

  const footGeo = new THREE.SphereGeometry(0.15, 12, 8);
  const feet = [-0.2, 0.2].map((x) => {
    const foot = new THREE.Mesh(footGeo, dark);
    foot.scale.set(0.95, 0.6, 1.3);
    foot.position.set(x, 0.08, 0.04);
    return foot;
  });
  const handGeo = new THREE.SphereGeometry(0.11, 10, 8);
  const hands = [-0.52, 0.52].map((x) => {
    const hand = new THREE.Mesh(handGeo, bodyMat);
    hand.position.set(x, 0.55, 0.06);
    return hand;
  });

  body.add(torso, belly, eyes, scarf, tailPivot, pack, roll, stalk, lamp, ...hands);
  lean.add(...feet);
  root.traverse((o) => {
    if (o.isMesh && o !== lamp) o.castShadow = true;
  });

  const contact = new THREE.Mesh(new THREE.CircleGeometry(0.62, 28).rotateX(-Math.PI / 2), contactShadowMaterial());
  contact.renderOrder = 3;
  const contactUp = new THREE.Vector3(0, 1, 0);

  const spring = { s: 0, v: 0 };
  let phase = 0;
  let blink = 2;
  let leanForward = 0;
  let leanSide = 0;
  const qLean = new THREE.Quaternion();
  const eLean = new THREE.Euler();

  return {
    root,
    lamp,
    contact,
    // Place the contact shadow on the ground under the explorer: `up` is its local up, `ground` the ground's radius
    // there, `height` how far above the ground the explorer is.
    placeContact(up, ground, height) {
      contact.position.copy(up).multiplyScalar(ground + 0.06);
      contact.quaternion.setFromUnitVectors(contactUp, up);
      const k = 1 / (1 + Math.max(height, 0) * 0.55);
      contact.scale.setScalar(0.55 + 0.45 * k);
      contact.material.uniforms.uOpacity.value = 0.5 * k;
    },
    // Kick the scale spring: positive stretches, negative squashes.
    kick(amount) {
      spring.v += amount;
    },
    update(dt, { speed, turn, grounded, vy, slopePitch, slopeRoll, reduced, time }) {
      const k = 260;
      const c = 15;
      spring.v += (-k * spring.s - c * spring.v) * dt;
      spring.s += spring.v * dt;
      const air = grounded ? 0 : THREE.MathUtils.clamp(vy / 7.2, -0.5, 1) * 0.24;
      const s = reduced ? 0 : THREE.MathUtils.clamp(spring.s + air, -0.35, 0.4);
      squash.scale.set(1 - s * 0.45, 1 + s, 1 - s * 0.45);

      const stride = Math.min(speed / 4.2, 1.6);
      phase += dt * (5 + speed * 1.9) * (grounded ? 1 : 0.2);
      const swing = Math.sin(phase) * 0.17 * Math.min(stride, 1.2);
      const lift = Math.max(0, Math.cos(phase)) * 0.08 * Math.min(stride, 1);
      const lift2 = Math.max(0, -Math.cos(phase)) * 0.08 * Math.min(stride, 1);
      feet[0].position.z = 0.04 + swing;
      feet[1].position.z = 0.04 - swing;
      feet[0].position.y = 0.08 + (grounded ? lift : 0.06);
      feet[1].position.y = 0.08 + (grounded ? lift2 : 0.06);
      hands[0].position.z = 0.06 - swing * 0.8;
      hands[1].position.z = 0.06 + swing * 0.8;
      const bob = grounded ? Math.abs(Math.sin(phase)) * 0.05 * Math.min(stride, 1) : 0;
      body.position.y = bob;
      tailPivot.rotation.y = Math.sin(time * 7 + phase) * (0.15 + stride * 0.3);
      tailPivot.rotation.x = -0.2 - stride * 0.35;

      leanForward = THREE.MathUtils.damp(leanForward, stride * 0.16 + slopePitch * 0.45, 10, dt);
      leanSide = THREE.MathUtils.damp(leanSide, -turn * 0.08 * stride + slopeRoll * 0.4, 8, dt);
      eLean.set(leanForward, 0, leanSide);
      qLean.setFromEuler(eLean);
      lean.quaternion.copy(qLean);

      blink -= dt;
      const closed = blink < 0.12 ? 0.15 : 1;
      eyes.scale.y = closed;
      eyes.position.y = closed < 1 ? 0.66 : 0;
      if (blink < 0) blink = 2 + Math.random() * 3;
      lamp.rotation.y = time * 1.6;
    },
  };
}
