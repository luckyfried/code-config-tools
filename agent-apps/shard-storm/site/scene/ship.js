// The ship: a faceted arrowhead in the person's color, the white core that is its only hitbox, the graze ring at
// one and a half ship radii, an engine flame, a wake that tapers behind it, and the lens that opens around it while
// time is slowed.
import * as THREE from "three";
import { hullMaterial, flatMaterial, trailMaterial } from "./materials.js";

export const SHIP_RADIUS = 2.6;
export const GRAZE_RADIUS = SHIP_RADIUS * 1.5;
export const CORE_RADIUS = 0.5;
const TRAIL = 26;
const LENS = 11;

function hullGeometry() {
  // Nose, wing tips, the notch at the tail, and a raised spine so the two halves catch light differently.
  const nose = [0, 2.9, 0];
  const spine = [0, 0.2, 0.9];
  const right = [1.9, -1.9, 0];
  const left = [-1.9, -1.9, 0];
  const notch = [0, -0.9, 0.2];
  const tris = [nose, left, spine, nose, spine, right, left, notch, spine, spine, notch, right];
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(tris.flat(), 3));
  return geo;
}

function edgeGeometry() {
  const pts = [[0, 2.9], [1.9, -1.9], [0, -0.9], [-1.9, -1.9], [0, 2.9]].map(([x, y]) => new THREE.Vector3(x, y, 0.3));
  return new THREE.BufferGeometry().setFromPoints(pts);
}

export function createShip(mode, tokens) {
  const group = new THREE.Group();
  group.renderOrder = 5;
  const body = new THREE.Group();
  group.add(body);

  let color = tokens.ship.clone();
  const hull = new THREE.Mesh(hullGeometry(), hullMaterial(mode, color));
  hull.renderOrder = 6;
  const edge = new THREE.Line(edgeGeometry(), new THREE.LineBasicMaterial({ transparent: true, depthTest: false }));
  edge.renderOrder = 7;
  body.add(hull, edge);

  const flame = new THREE.Mesh(new THREE.CircleGeometry(1, 20), flatMaterial(mode, color, 0.8));
  flame.position.set(0, -1.6, -0.1);
  flame.renderOrder = 5;
  body.add(flame);

  const ring = new THREE.Mesh(new THREE.RingGeometry(GRAZE_RADIUS - 0.09, GRAZE_RADIUS, 72), flatMaterial(mode, color, 0.2));
  ring.renderOrder = 5;
  group.add(ring);

  // Slow time: a wide lens ring and a soft disc of the ship's color that open out around it.
  const lens = new THREE.Mesh(new THREE.RingGeometry(LENS - 0.16, LENS, 120), flatMaterial(mode, color, 0));
  const lensFill = new THREE.Mesh(new THREE.CircleGeometry(LENS, 120), flatMaterial(mode, color, 0));
  lens.renderOrder = 5;
  lensFill.renderOrder = 1;
  group.add(lensFill, lens);

  const coreOutline = new THREE.Mesh(new THREE.CircleGeometry(CORE_RADIUS + 0.22, 28), flatMaterial(mode, new THREE.Color(0, 0, 0), 1, false));
  coreOutline.renderOrder = 8;
  const core = new THREE.Mesh(new THREE.CircleGeometry(CORE_RADIUS, 28), flatMaterial(mode, new THREE.Color(1, 1, 1), 1, false));
  core.renderOrder = 9;
  core.position.z = 0.5;
  coreOutline.position.z = 0.45;
  group.add(coreOutline, core);

  // The wake: a strip of TRAIL pairs of vertices following the ship's recent positions.
  const trailPos = new Float32Array(TRAIL * 2 * 3);
  const along = new Float32Array(TRAIL * 2);
  const index = [];
  for (let i = 0; i < TRAIL; i++) {
    along[i * 2] = along[i * 2 + 1] = i / (TRAIL - 1);
    if (i < TRAIL - 1) {
      const a = i * 2;
      index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const trailGeo = new THREE.BufferGeometry();
  trailGeo.setAttribute("position", new THREE.BufferAttribute(trailPos, 3).setUsage(THREE.DynamicDrawUsage));
  trailGeo.setAttribute("aAlong", new THREE.BufferAttribute(along, 1));
  trailGeo.setIndex(index);
  const trail = new THREE.Mesh(trailGeo, trailMaterial(mode, color));
  trail.frustumCulled = false;
  trail.renderOrder = 3;
  const history = Array.from({ length: TRAIL }, () => new THREE.Vector2());
  let primed = false;

  let ringPulse = 0;
  let slowTarget = 0;
  let slowAmt = 0;
  let flash = 0;
  let bank = 0;
  let lastX = 0;

  function paint(mode, tokens) {
    color = tokens.ship.clone();
    hull.material.dispose();
    hull.material = hullMaterial(mode, color);
    const day = mode === "day";
    edge.material.color.copy(day ? color.clone().multiplyScalar(0.45) : new THREE.Color(1, 1, 1));
    edge.material.opacity = day ? 0.9 : 0.75;
    edge.material.blending = day ? THREE.NormalBlending : THREE.AdditiveBlending;
    for (const [mesh, opacity, additive] of [[flame, 0.8, true], [ring, 0.22, true], [lens, 0, true], [lensFill, 0, true]]) {
      mesh.material.dispose();
      mesh.material = flatMaterial(mode, color, opacity, additive);
    }
    coreOutline.material.color.copy(day ? new THREE.Color(0.04, 0.03, 0.08) : color);
    coreOutline.material.opacity = day ? 0.9 : 0.85;
    trail.material.dispose();
    trail.material = trailMaterial(mode, color);
  }
  paint(mode, tokens);

  return {
    group,
    trail,
    get color() {
      return color;
    },
    setLook: paint,
    setSlow(on) {
      slowTarget = on ? 1 : 0;
    },
    graze() {
      ringPulse = 1;
    },
    hit() {
      flash = 1;
    },
    resetTrail() {
      primed = false;
    },
    /** Places the ship at (x, y); dt is real time, for the wake and the flame flicker. */
    update(x, y, dt, time, visible) {
      group.visible = visible;
      trail.visible = visible;
      group.position.set(x, y, 0);
      const vx = dt > 0 ? (x - lastX) / dt : 0;
      lastX = x;
      bank += (Math.max(-0.6, Math.min(0.6, -vx * 0.012)) - bank) * Math.min(1, dt * 10);
      body.rotation.y = bank;
      ringPulse = Math.max(0, ringPulse - dt * 4);
      flash = Math.max(0, flash - dt * 3);
      ring.material.opacity = 0.16 + ringPulse * 0.6;
      ring.scale.setScalar(1 + ringPulse * 0.12);
      // The lens springs open with a slight overshoot and closes quickly.
      slowAmt += (slowTarget - slowAmt) * Math.min(1, dt * (slowTarget ? 7 : 10));
      const open = slowAmt < 0.001 ? 0 : slowAmt;
      const ease = 1 - Math.pow(1 - open, 3);
      lens.scale.setScalar(0.45 + 0.55 * ease + 0.04 * Math.sin(time * 5) * open);
      lens.material.opacity = 0.75 * open;
      lensFill.scale.setScalar(0.45 + 0.55 * ease);
      lensFill.material.opacity = (lensFill.material.blending === THREE.AdditiveBlending ? 0.08 : 0.12) * open;
      hull.material.uniforms.uFlash.value = flash;
      const flicker = 0.75 + 0.25 * Math.sin(time * 47) * Math.sin(time * 31);
      flame.scale.set(0.55 * flicker, 1.1 + 0.5 * flicker, 1);

      if (!primed) {
        for (const p of history) p.set(x, y - 1);
        primed = true;
      }
      // The wake streams down behind the ship even when it holds still, as if flying into the storm.
      for (let i = TRAIL - 1; i > 0; i--) history[i].set(history[i - 1].x, history[i - 1].y - 26 * dt);
      history[0].set(x, y - 1.2);
      for (let i = 0; i < TRAIL; i++) {
        const p = history[i];
        const q = history[Math.min(TRAIL - 1, i + 1)];
        let dx = p.x - q.x;
        let dy = p.y - q.y;
        const len = Math.hypot(dx, dy) || 1;
        dx /= len;
        dy /= len;
        const w = 0.9 * (1 - i / TRAIL);
        const o = i * 6;
        trailPos[o] = p.x - dy * w;
        trailPos[o + 1] = p.y + dx * w;
        trailPos[o + 2] = -0.05;
        trailPos[o + 3] = p.x + dy * w;
        trailPos[o + 4] = p.y - dx * w;
        trailPos[o + 5] = -0.05;
      }
      trailGeo.attributes.position.needsUpdate = true;
    },
  };
}
