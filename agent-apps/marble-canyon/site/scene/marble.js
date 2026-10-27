// The marble (clear glass with a painted swirl inside, refracting on the high tier), its contact shadow, and the ghost:
// a 40% marble with its own fading trail.
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  DynamicDrawUsage,
  Group,
  Matrix4,
  Mesh,
  PlaneGeometry,
  Quaternion,
  ShaderMaterial,
  SphereGeometry,
  Vector3,
} from "three";
import { DISH, HALF_WIDTH, MARBLE_RADIUS } from "../game/generate.js";

const R = MARBLE_RADIUS;
const TRAIL = 56;

export function createMarble(tier, materials) {
  const group = new Group();
  const spin = new Group();
  group.add(spin);
  const shell = new Mesh(new SphereGeometry(R, tier.segments, Math.round(tier.segments / 2)), materials.glass);
  spin.add(shell);
  if (!tier.transmission) shell.renderOrder = 2;
  const core = new Mesh(new SphereGeometry(R * 0.8, 32, 16), materials.swirl);
  const inner = new Mesh(new SphereGeometry(R * 0.5, 24, 12), materials.swirl);
  inner.rotation.set(1.2, 0.5, 0.8);
  spin.add(core, inner);
  if (tier.transmission) {
    const glaze = new Mesh(new SphereGeometry(R * 1.002, tier.segments, Math.round(tier.segments / 2)), materials.glaze);
    glaze.renderOrder = 2;
    spin.add(glaze);
  }
  // The shadow under the marble is a soft blob, not a shadow-map silhouette, so it stays round at any map size.
  // Its quad bends across the track to follow the dish.
  const blob = new PlaneGeometry(R * 4.4, R * 4.4, 8, 8);
  const corners = blob.attributes.position;
  for (let i = 0; i < corners.count; i += 1) corners.setZ(i, (DISH / (HALF_WIDTH * HALF_WIDTH)) * corners.getX(i) ** 2);
  const contact = new Mesh(blob, materials.contact);
  contact.matrixAutoUpdate = false;
  contact.renderOrder = 1;

  const q = new Quaternion();
  const axis = new Vector3();
  const basis = new Matrix4();
  const vt = new Vector3();
  const vn = new Vector3();
  const vr = new Vector3();
  const vs = new Vector3();
  const away = new Vector3(0, -1, 0);
  const stretch = { k: 1, v: 0 };
  return {
    group,
    spin,
    contact,
    // Rolls by `distance` about the axis `heading × up`.
    roll(distance, heading, up) {
      axis.crossVectors(up, heading);
      if (axis.lengthSq() < 1e-6) return;
      axis.normalize();
      q.setFromAxisAngle(axis, distance / R);
      spin.quaternion.premultiply(q);
    },
    // The sun's direction (toward the sun); the shadow leans a little away from it.
    sun(dir) {
      away.copy(dir).normalize().negate();
    },
    // Lays the contact shadow on the surface under the marble, tilted to the dish's slope at `u` across the
    // banked track; it fades as the marble rises.
    shadow(point, frame, height, u) {
      vt.set(frame.t[0], frame.t[1], frame.t[2]);
      vn.set(frame.n[0], frame.n[1], frame.n[2]);
      vr.set(frame.r[0], frame.r[1], frame.r[2]);
      const slope = (2 * DISH * Math.max(-1, Math.min(1, u))) / HALF_WIDTH;
      vs.copy(vr);
      vr.addScaledVector(vn, slope).normalize();
      vn.addScaledVector(vs, -slope).normalize();
      basis.makeBasis(vr, vt, vn);
      const s = 1 + Math.min(2, height * 0.25);
      basis.scale(vs.set(s, s, 1));
      const drop = R - 0.04 + height;
      vs.copy(away).addScaledVector(vn, -away.dot(vn)).multiplyScalar(R * 0.8);
      basis.setPosition(point.x - vn.x * drop + vs.x, point.y - vn.y * drop + vs.y, point.z - vn.z * drop + vs.z);
      contact.matrix.copy(basis);
      materials.contact.opacity = 0.8 / (1 + height * 0.5);
    },
    // Squash on landing, stretch on takeoff, settling back on a spring.
    squash(amount) {
      stretch.k = amount;
      stretch.v = 0;
    },
    update(dt, reduced) {
      if (reduced) {
        stretch.k = 1;
      } else {
        stretch.v += (-(stretch.k - 1) * 260 - stretch.v * 16) * dt;
        stretch.k += stretch.v * dt;
      }
      const k = stretch.k;
      group.scale.set(1 / Math.sqrt(k), k, 1 / Math.sqrt(k));
    },
  };
}

export function createGhost(tier, materials) {
  const group = new Group();
  const ball = new Mesh(new SphereGeometry(R, 32, 16), materials.ghost);
  group.add(ball);
  group.visible = false;

  const positions = new Float32Array(TRAIL * 2 * 3);
  const alpha = new Float32Array(TRAIL * 2);
  const index = [];
  for (let i = 0; i < TRAIL - 1; i += 1) {
    const a = i * 2;
    index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3).setUsage(DynamicDrawUsage));
  geometry.setAttribute("alpha", new BufferAttribute(alpha, 1));
  geometry.setIndex(index);
  for (let i = 0; i < TRAIL; i += 1) {
    const a = 1 - i / (TRAIL - 1);
    alpha[i * 2] = a * a;
    alpha[i * 2 + 1] = a * a;
  }
  const trailMaterial = new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { color: { value: new Color().copy(materials.ghost.color) }, opacity: { value: 0.5 } },
    vertexShader: /* glsl */ `
      attribute float alpha;
      varying float vAlpha;
      void main() {
        vAlpha = alpha;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 color;
      uniform float opacity;
      varying float vAlpha;
      void main() {
        gl_FragColor = vec4(color, vAlpha * opacity);
        #include <colorspace_fragment>
      }
    `,
  });
  const trail = new Mesh(geometry, trailMaterial);
  trail.frustumCulled = false;
  trail.visible = false;
  let filled = 0;

  const q = new Quaternion();
  const axis = new Vector3();
  return {
    group,
    trail,
    show(on) {
      group.visible = on;
      trail.visible = on;
      if (!on) filled = 0;
    },
    reset() {
      filled = 0;
    },
    place(point, frame, distance) {
      group.position.copy(point);
      axis.set(frame.n[1] * frame.t[2] - frame.n[2] * frame.t[1], frame.n[2] * frame.t[0] - frame.n[0] * frame.t[2], frame.n[0] * frame.t[1] - frame.n[1] * frame.t[0]);
      if (axis.lengthSq() > 1e-6) {
        q.setFromAxisAngle(axis.normalize(), distance / R);
        ball.quaternion.premultiply(q);
      }
      // Shift the trail and lay its newest pair across the track at the marble's center.
      positions.copyWithin(6, 0, (TRAIL - 1) * 6);
      const w = R * 0.75;
      positions[0] = point.x - frame.r[0] * w;
      positions[1] = point.y - frame.r[1] * w;
      positions[2] = point.z - frame.r[2] * w;
      positions[3] = point.x + frame.r[0] * w;
      positions[4] = point.y + frame.r[1] * w;
      positions[5] = point.z + frame.r[2] * w;
      if (filled < TRAIL) {
        for (let i = filled; i < TRAIL; i += 1) positions.copyWithin(i * 6, 0, 6);
        filled = TRAIL;
      }
      geometry.attributes.position.needsUpdate = true;
    },
    // Fades the ghost out as it nears the camera, so a ghost that falls behind never fills or clips the view.
    fade(eye) {
      const d = group.position.distanceTo(eye);
      const k = Math.max(0, Math.min(1, (d - 4.5) / 4));
      const near = k * k * (3 - 2 * k);
      materials.ghost.opacity = 0.4 * near;
      trailMaterial.uniforms.opacity.value = 0.5 * near;
      ball.visible = near > 0.01;
    },
    applyColors() {
      trailMaterial.uniforms.color.value.copy(materials.ghost.color);
    },
  };
}
