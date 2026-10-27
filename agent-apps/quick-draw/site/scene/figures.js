// The two gunslingers, built from primitives so a theme can recolor them. Each is a little rig of named joints
// (hips, torso, head, hat, shoulders, elbows, the gun hand) posed procedurally: an idle sway with a hat-brim tilt,
// the hover over the holster, the draw, the recoil, the flinch when the hat goes, the twirl, and the jam.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { box, cylinder, xf } from "./kit.js";

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const lerp = (a, b, t) => a + (b - a) * t;
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeOutBack = (t) => {
  const c = 1.9;
  return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
};
const damp = (a, b, lambda, dt) => lerp(a, b, 1 - Math.exp(-lambda * dt));

/** Collects colored pieces for one joint and merges them into a single mesh. */
class Piece {
  constructor() {
    this.list = [];
  }
  add(geometry, color, matrix) {
    const g = geometry.index ? geometry.toNonIndexed() : geometry.clone();
    if (matrix) g.applyMatrix4(matrix);
    for (const name of Object.keys(g.attributes)) if (!["position", "normal"].includes(name)) g.deleteAttribute(name);
    const n = g.attributes.position.count;
    const c = new Float32Array(n * 3);
    for (let i = 0; i < n; i += 1) {
      c[i * 3] = color.r;
      c[i * 3 + 1] = color.g;
      c[i * 3 + 2] = color.b;
    }
    g.setAttribute("color", new THREE.Float32BufferAttribute(c, 3));
    this.list.push(g);
    return this;
  }
  mesh(material, name) {
    const geo = mergeGeometries(this.list, false);
    const m = new THREE.Mesh(geo, material);
    m.name = name;
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }
}

/**
 * A rim of light around the silhouette, so a figure in shadow still reads against the street, and a soft fill from
 * over the camera's shoulder. Both are weighted by each surface's own color (the rim by `tint`), so under a deep
 * red dusk the skin, the hat, and the coat keep tones of their own.
 */
function addRim(material, c) {
  if (!(c.rimIntensity > 0) && !(c.fillIntensity > 0)) return;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uRim = { value: c.rim.clone().multiplyScalar(c.rimIntensity) };
    shader.uniforms.uRimTint = { value: c.rimTint };
    shader.uniforms.uFill = { value: c.fill.clone().multiplyScalar(c.fillIntensity) };
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 uRim;\nuniform float uRimTint;\nuniform vec3 uFill;")
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        float rimEdge = 1.0 - clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0);
        // faces seen exactly edge-on are slivers a pixel wide; they are left out so the rim stays smooth
        vec3 rimBody = mix(vec3(1.0), diffuseColor.rgb * 2.2, uRimTint);
        totalEmissiveRadiance += uRim * rimBody * pow(rimEdge, 3.0) * (1.0 - smoothstep(0.85, 0.97, rimEdge));
        float fillWrap = clamp(dot(normal, normalize(vec3(-0.35, 0.55, 0.75))) * 0.6 + 0.4, 0.0, 1.0);
        totalEmissiveRadiance += uFill * diffuseColor.rgb * fillWrap;`,
      );
  };
  material.customProgramCacheKey = () => "gunslinger-rim-fill";
}

function lathe(points, segments = 18, phiStart = 0, phiLength = Math.PI * 2) {
  return new THREE.LatheGeometry(points.map(([r, y]) => new THREE.Vector2(r, y)), segments, phiStart, phiLength);
}

function capsule(r, len) {
  return new THREE.CapsuleGeometry(r, len, 4, 10);
}

const PONCHO_ROWS = [
  // v, half width, half depth, height
  [0, 0.085, 0.08, 0.565],
  [0.1, 0.17, 0.135, 0.545],
  [0.2, 0.25, 0.178, 0.51],
  [0.3, 0.31, 0.208, 0.452],
  [0.4, 0.335, 0.218, 0.385],
];
const PONCHO_SPLIT = 0.3;

/**
 * The poncho's surface between rows v0 and v1 (0 at the collar, 1 at the hem), pushed out by `grow`. Open, the
 * yoke over the shoulders stays whole and the drape below parts over the gun arm, from ahead of the side to just
 * behind the shoulder, bunched where it is thrown back.
 */
function ponchoGeometry(g, v0, v1, grow, open) {
  const openA = g > 0 ? 0.6 : -1.95;
  const openB = g > 0 ? 1.95 : -0.6;
  const point = (phi, v) => {
    let rx;
    let rz;
    let y;
    let s = 0;
    if (v <= 0.4) {
      const i = Math.min(3, Math.floor(v / 0.1));
      const k = (v - PONCHO_ROWS[i][0]) / 0.1;
      rx = lerp(PONCHO_ROWS[i][1], PONCHO_ROWS[i + 1][1], k);
      rz = lerp(PONCHO_ROWS[i][2], PONCHO_ROWS[i + 1][2], k);
      y = lerp(PONCHO_ROWS[i][3], PONCHO_ROWS[i + 1][3], k);
    } else {
      s = (v - 0.4) / 0.6;
      const hem = 0.06 - 0.19 * Math.pow(Math.abs(Math.cos(phi)), 1.6);
      rx = lerp(0.335, 0.378, s);
      rz = lerp(0.218, 0.238, s);
      y = lerp(0.385, hem, s);
    }
    // folds deepen toward the hem; the fabric bunches where it is thrown back behind the gun shoulder
    const fold = 1 + 0.065 * s * (0.6 * Math.sin(phi * 7 + 0.4) + 0.4 * Math.sin(phi * 13 + 1.3));
    const d = Math.atan2(Math.sin(phi - openB), Math.cos(phi - openB));
    const bunch = !open ? 1 : 1 + 0.1 * Math.exp(-((d / 0.4) ** 2)) * Math.min(1, v / 0.35);
    const r = fold * bunch * grow;
    const sx = Math.sin(phi);
    const cz = Math.cos(phi);
    return [rx * r * Math.sign(sx) * Math.pow(Math.abs(sx), 0.8), y, rz * r * Math.sign(cz) * Math.pow(Math.abs(cz), 0.8)];
  };
  const grid = (p0, p1, a, b, nu, nv) => {
    const pos = [];
    const index = [];
    for (let j = 0; j <= nv; j += 1) {
      for (let i = 0; i <= nu; i += 1) pos.push(...point(lerp(p0, p1, i / nu), lerp(a, b, j / nv)));
    }
    for (let j = 0; j < nv; j += 1) {
      for (let i = 0; i < nu; i += 1) {
        const q = j * (nu + 1) + i;
        index.push(q, q + nu + 1, q + 1, q + 1, q + nu + 1, q + nu + 2);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setIndex(index);
    geo.computeVertexNormals();
    return geo;
  };
  if (!open) return grid(0, Math.PI * 2, v0, v1, 56, Math.max(4, Math.round((v1 - v0) * 26)));
  const parts = [];
  if (v0 < PONCHO_SPLIT) parts.push(grid(0, Math.PI * 2, v0, Math.min(v1, PONCHO_SPLIT), 56, 6));
  if (v1 > PONCHO_SPLIT) {
    const a = Math.max(v0, PONCHO_SPLIT);
    parts.push(grid(openB, openA + Math.PI * 2, a, v1, 48, Math.max(2, Math.round((v1 - a) * 22))));
  }
  return parts.length === 1 ? parts[0] : mergeGeometries(parts.map((p) => p.toNonIndexed()), false);
}

/** The revolver, barrel along -y from the grip, so it points where the forearm points. */
function revolver(piece, metal, grip, dark) {
  piece.add(box(0.026, 0.08, 0.034), grip, xf(0, 0.02, -0.006, 0.28, 0, 0));
  piece.add(box(0.03, 0.065, 0.05), metal, xf(0, -0.045, 0.012));
  piece.add(cylinder(0.024, 0.024, 0.05, 10), metal, xf(0, -0.08, 0.02));
  piece.add(cylinder(0.011, 0.011, 0.17, 8), metal, xf(0, -0.18, 0.024));
  piece.add(cylinder(0.006, 0.006, 0.15, 6), dark, xf(0, -0.17, 0.008));
  piece.add(box(0.006, 0.012, 0.01), metal, xf(0, -0.255, 0.036));
  piece.add(box(0.012, 0.02, 0.03), metal, xf(0, 0.0, 0.03, -0.4, 0, 0));
  return piece;
}

export class Gunslinger {
  /**
   * side: -1 stands on the left facing right, +1 on the right facing left. look: "duster" or "poncho".
   */
  constructor({ side, look, colors, x }) {
    this.side = side;
    this.look = look;
    this.g = side < 0 ? -1 : 1; // the gun hand's local x: both draw on the camera's side
    this.root = new THREE.Group();
    this.root.name = `gunslinger-${side < 0 ? "left" : "right"}`;
    this.home = new THREE.Vector3(x, 0, 0);
    this.root.position.copy(this.home);
    this.root.rotation.y = side < 0 ? Math.PI / 2 : -Math.PI / 2;
    this.material = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, side: THREE.DoubleSide, envMapIntensity: 0.7 });
    this.metalMaterial = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.32, metalness: 0.8, envMapIntensity: 1.3 });
    addRim(this.material, colors);
    this.build(colors);
    this.reset();
  }

  build(c) {
    const g = this.g;
    const M = this.material;
    const coat = c.coat;
    const shirt = c.shirt;
    const pants = c.pants;
    const leather = c.leather;
    const skin = c.skin;
    const accent = c.accent;
    const hatColor = c.hat;
    const metal = c.metal;
    const grip = c.grip;
    const dark = c.dark;

    this.hips = new THREE.Group();
    this.hips.position.y = 0.98;
    this.root.add(this.hips);

    const pelvis = new Piece()
      .add(cylinder(0.15, 0.16, 0.2, 14), pants, xf(0, -0.04, 0, 0, 0, 0, 1.05, 1, 0.8))
      .add(cylinder(0.168, 0.168, 0.065, 16), leather, xf(0, 0.05, 0, 0, 0, 0, 1.05, 1, 0.82))
      .add(box(0.06, 0.05, 0.02), metal, xf(0, 0.05, 0.14))
      .add(box(0.075, 0.22, 0.1), leather, xf(g * 0.2, -0.1, 0.03, 0, 0, g * -0.12))
      .add(cylinder(0.12, 0.12, 0.03, 12, true), leather, xf(0, 0.0, 0, 0.0, 0, g * -0.18, 1.32, 1, 1.05));
    for (let i = 0; i < 6; i += 1) pelvis.add(cylinder(0.009, 0.009, 0.03, 5), metal, xf(g * (0.06 + i * 0.022), 0.0 - i * 0.005, 0.145 - i * 0.015, Math.PI / 2, 0, 0));
    this.hips.add(pelvis.mesh(M, "pelvis"));

    this.holsterGun = new THREE.Group();
    this.holsterGun.position.set(g * 0.215, 0.02, 0.03);
    this.holsterGun.rotation.z = g * -0.12;
    this.holsterGun.add(revolver(new Piece(), metal, grip, dark).mesh(this.metalMaterial, "holstered"));
    this.hips.add(this.holsterGun);

    // legs
    this.legs = [];
    for (const lx of [-0.095, 0.095]) {
      const thigh = new THREE.Group();
      thigh.position.set(lx, -0.06, 0);
      thigh.rotation.z = Math.sign(lx) * 0.07;
      thigh.add(new Piece().add(capsule(0.07, 0.32), pants, xf(0, -0.21, 0)).mesh(M, "thigh"));
      const knee = new THREE.Group();
      knee.position.y = -0.44;
      const shin = new Piece()
        .add(capsule(0.058, 0.2), pants, xf(0, -0.13, 0))
        .add(cylinder(0.068, 0.064, 0.24, 12), leather, xf(0, -0.32, 0))
        .add(box(0.1, 0.11, 0.26), leather, xf(0, -0.415, 0.045))
        .add(box(0.105, 0.035, 0.27), dark, xf(0, -0.455, 0.045))
        .add(box(0.08, 0.06, 0.06), dark, xf(0, -0.44, -0.07))
        .add(new THREE.TorusGeometry(0.03, 0.006, 4, 10), metal, xf(0, -0.43, -0.1, 0, Math.PI / 2, 0));
      knee.add(shin.mesh(M, "shin"));
      thigh.add(knee);
      this.hips.add(thigh);
      this.legs.push({ thigh, knee });
    }

    // torso
    this.torso = new THREE.Group();
    this.torso.position.y = 0.06;
    this.hips.add(this.torso);
    const chest = new Piece().add(
      lathe([[0.001, 0], [0.15, 0], [0.165, 0.18], [0.185, 0.34], [0.18, 0.43], [0.09, 0.49], [0.001, 0.5]], 18),
      shirt,
      xf(0, 0, 0, 0, 0, 0, 1.12, 1, 0.74),
    );
    chest.add(cylinder(0.048, 0.052, 0.1, 10), skin, xf(0, 0.53, 0.0));
    if (this.look === "duster") {
      // vest, open duster, collar, and a red bandana
      chest.add(lathe([[0.168, 0.02], [0.18, 0.2], [0.19, 0.36], [0.17, 0.44]], 18, 0.5, Math.PI * 2 - 1.0), c.vest, xf(0, 0, 0, 0, 0, 0, 1.13, 1, 0.78));
      chest.add(
        lathe([[0.2, 0.45], [0.215, 0.36], [0.212, 0.12], [0.225, -0.08], [0.26, -0.34], [0.31, -0.62]], 22, 0.42, Math.PI * 2 - 0.84),
        coat,
        xf(0, 0, 0, 0, 0, 0, 1.12, 1, 0.84),
      );
      chest.add(new THREE.TorusGeometry(0.1, 0.03, 6, 16, Math.PI * 1.4), coat, xf(0, 0.47, -0.01, Math.PI / 2, 0, Math.PI * 0.8 + Math.PI));
      chest.add(new THREE.ConeGeometry(0.075, 0.12, 10), accent, xf(0, 0.44, 0.075, Math.PI, 0, 0, 1.4, 1, 0.5));
      chest.add(cylinder(0.062, 0.07, 0.05, 12), accent, xf(0, 0.5, 0.0));
    } else {
      // a poncho draped over both shoulders and arms, long at the front and back, short at the sides so the hands
      // show by the belt; drawing throws it open over the gun arm and a leather vest. A blue stripe and scarf
      chest.add(lathe([[0.168, 0.02], [0.18, 0.2], [0.19, 0.36], [0.17, 0.44]], 18, 0.5, Math.PI * 2 - 1.0), leather.clone().multiplyScalar(0.42), xf(0, 0, 0, 0, 0, 0, 1.13, 1, 0.78));
      chest.add(cylinder(0.086, 0.094, 0.05, 14), accent, xf(0, 0.57, 0.0));
      const poncho = (open) => new Piece()
        .add(ponchoGeometry(g, 0, 1, 1, open), coat)
        .add(ponchoGeometry(g, 0.86, 0.91, 1.008, open), accent)
        .mesh(M, open ? "poncho-open" : "poncho");
      this.ponchoClosed = poncho(false);
      this.ponchoOpen = poncho(true);
      this.ponchoOpen.visible = false;
      this.torso.add(this.ponchoClosed, this.ponchoOpen);
    }
    this.torso.add(chest.mesh(M, "chest"));

    // head
    this.head = new THREE.Group();
    this.head.position.y = 0.64;
    this.torso.add(this.head);
    const face = new Piece()
      .add(new THREE.SphereGeometry(0.1, 16, 12), skin, xf(0, 0, 0, 0, 0, 0, 0.92, 1.08, 1))
      .add(new THREE.SphereGeometry(0.085, 14, 10), skin, xf(0, -0.055, 0.018, 0, 0, 0, 0.95, 0.72, 0.95))
      .add(new THREE.SphereGeometry(0.104, 14, 10, 0, Math.PI * 2, 0, Math.PI * 0.55), hatColor.clone().lerp(dark, 0.5), xf(0, 0.012, -0.012, -0.5, 0, 0, 0.96, 0.9, 1.0))
      .add(box(0.028, 0.048, 0.04), skin.clone().multiplyScalar(0.92), xf(0, -0.005, 0.1))
      .add(new THREE.SphereGeometry(0.022, 6, 6), skin.clone().multiplyScalar(0.9), xf(0.094, 0, -0.005))
      .add(new THREE.SphereGeometry(0.022, 6, 6), skin.clone().multiplyScalar(0.9), xf(-0.094, 0, -0.005))
      .add(box(0.03, 0.01, 0.01), dark, xf(0.036, 0.02, 0.094))
      .add(box(0.03, 0.01, 0.01), dark, xf(-0.036, 0.02, 0.094))
      .add(box(0.12, 0.04, 0.03), hatColor.clone().multiplyScalar(0.6), xf(0, 0.055, -0.05));
    if (this.look === "duster") {
      face.add(new THREE.CapsuleGeometry(0.011, 0.07, 3, 6).rotateZ(Math.PI / 2), dark.clone().lerp(hatColor, 0.3), xf(0, -0.038, 0.098));
      face.add(new THREE.CapsuleGeometry(0.008, 0.03, 3, 6), dark.clone().lerp(hatColor, 0.3), xf(0.044, -0.056, 0.094, 0, 0, 0.3));
      face.add(new THREE.CapsuleGeometry(0.008, 0.03, 3, 6), dark.clone().lerp(hatColor, 0.3), xf(-0.044, -0.056, 0.094, 0, 0, -0.3));
    } else {
      face.add(new THREE.SphereGeometry(0.086, 12, 8, 0, Math.PI * 2, Math.PI * 0.45, Math.PI * 0.55), skin.clone().multiplyScalar(0.6), xf(0, -0.052, 0.02, 0, 0, 0, 0.96, 0.74, 0.97));
      face.add(box(0.012, 0.004, 0.012), dark, xf(0.05, -0.045, 0.1));
    }
    this.head.add(face.mesh(M, "face"));

    // hat
    this.hat = new THREE.Group();
    this.hat.position.set(0, 0.07, -0.004);
    this.hat.rotation.x = -0.04;
    this.head.add(this.hat);
    const hat = new Piece();
    const brimR = this.look === "duster" ? 0.245 : 0.262;
    const crown = this.look === "duster"
      ? [[0.001, 0.15], [0.03, 0.142], [0.07, 0.158], [0.098, 0.13], [0.106, 0.06], [0.11, 0.0]]
      : [[0.001, 0.105], [0.09, 0.108], [0.104, 0.09], [0.112, 0.0]];
    hat.add(lathe(crown, 20), hatColor, xf(0, 0.012, 0, 0, 0, 0, 1, 1, 1.08));
    hat.add(cylinder(0.113, 0.114, 0.026, 20), this.look === "duster" ? accent.clone().multiplyScalar(0.55) : dark, xf(0, 0.026, 0, 0, 0, 0, 1, 1, 1.08));
    const brim = new THREE.RingGeometry(0.095, brimR, 36, 3);
    brim.rotateX(-Math.PI / 2);
    const bp = brim.attributes.position;
    const curl = this.look === "duster" ? 1.15 : 0.75;
    for (let i = 0; i < bp.count; i += 1) {
      const x = bp.getX(i);
      const z = bp.getZ(i);
      const r = Math.hypot(x, z);
      const edge = Math.max(0, r - brimR * 0.72);
      bp.setY(i, curl * x * x + edge * edge * 6 - (this.look === "duster" ? 0.25 * z * z : 0));
      bp.setZ(i, z * 1.1);
    }
    brim.computeVertexNormals();
    hat.add(brim, hatColor, xf(0, 0.012, 0));
    hat.add(new THREE.RingGeometry(brimR - 0.012, brimR, 36, 1).rotateX(-Math.PI / 2), hatColor.clone().multiplyScalar(0.75), xf(0, 0.012 + (curl * brimR * brimR) * 0.5, 0, 0, 0, 0, 1, 1, 1.1));
    this.hatMesh = hat.mesh(M, "hat");
    this.hat.add(this.hatMesh);
    this.hatRest = { position: this.hat.position.clone(), quaternion: this.hat.quaternion.clone() };

    // arms
    this.arms = [];
    for (const sx of [g, -g]) {
      const shoulder = new THREE.Group();
      shoulder.position.set(sx * 0.215, 0.43, -0.005);
      const sleeve = this.look === "duster" ? coat : shirt;
      shoulder.add(new Piece()
        .add(new THREE.SphereGeometry(0.066, 10, 8), sleeve, xf(0, -0.01, 0))
        .add(capsule(0.054, 0.2), sleeve, xf(0, -0.15, 0))
        .mesh(M, "upper-arm"));
      const elbow = new THREE.Group();
      elbow.position.y = -0.3;
      const fore = new Piece()
        .add(capsule(0.047, 0.18, 0), sleeve, xf(0, -0.12, 0))
        .add(cylinder(0.056, 0.052, 0.05, 10), this.look === "duster" ? coat.clone().multiplyScalar(0.8) : shirt.clone().multiplyScalar(0.9), xf(0, -0.235, 0))
        .add(box(0.062, 0.1, 0.085), this.look === "duster" ? skin : leather, xf(0, -0.3, 0.008))
        .add(box(0.02, 0.06, 0.03), this.look === "duster" ? skin : leather, xf(-sx * 0.035, -0.29, 0.04, 0, 0, -sx * 0.4));
      elbow.add(fore.mesh(M, "forearm"));
      shoulder.add(elbow);
      this.torso.add(shoulder);
      this.arms.push({ shoulder, elbow, sx });
    }
    this.gunHand = new THREE.Group();
    this.gunHand.position.set(0, -0.3, 0.012);
    this.gunHand.add(revolver(new Piece(), metal, grip, dark).mesh(this.metalMaterial, "drawn"));
    this.gunHand.visible = false;
    this.arms[0].elbow.add(this.gunHand);
    this.muzzle = new THREE.Object3D();
    this.muzzle.position.set(0, -0.27, 0.024);
    this.gunHand.add(this.muzzle);
  }

  reset() {
    this.t = Math.random() * 10;
    this.phase = this.side < 0 ? 0 : 1.7;
    this.mode = "idle";
    this.drawAt = null;
    this.fireAt = null;
    this.hitAt = null;
    this.jamAt = null;
    this.twirlAt = null;
    this.holsterAt = null;
    this.stepBack = 0;
    this.hatOff = false;
    this.gunHand.visible = false;
    this.gunHand.rotation.set(0, 0, 0);
    this.holsterGun.visible = true;
    this.root.position.copy(this.home);
    this.cur = { armX: 0.06, armZ: this.g * 0.16, elbow: -0.2, leanX: 0, twist: 0, headX: 0, headY: 0, hipsY: 0.98, back: 0, offX: 0.04, offZ: -this.g * 0.1 };
  }

  restoreHat() {
    if (this.hat.parent !== this.head) this.head.add(this.hat);
    this.hat.position.copy(this.hatRest.position);
    this.hat.quaternion.copy(this.hatRest.quaternion);
    this.hat.scale.set(1, 1, 1);
    this.hatOff = false;
  }

  /** The hand drops to the grip during the wait. */
  ready(on) {
    if (this.mode === "idle" || this.mode === "ready") this.mode = on ? "ready" : "idle";
  }

  draw(now) {
    if (this.drawAt !== null) return;
    this.mode = "draw";
    this.drawAt = now;
  }

  fire(now) {
    this.fireAt = now;
  }

  jam(now) {
    this.mode = "draw";
    this.drawAt = now;
    this.jamAt = now + 0.16;
  }

  hit(now) {
    this.hitAt = now;
  }

  twirl(now) {
    this.twirlAt = now;
  }

  /** The muzzle's world position. */
  muzzleWorld(target) {
    this.root.updateMatrixWorld(true);
    return this.muzzle.getWorldPosition(target);
  }

  hatWorld(target) {
    this.root.updateMatrixWorld(true);
    return this.hat.getWorldPosition(target);
  }

  update(dt, now) {
    this.t += dt;
    const t = this.t;
    const g = this.g;
    const target = { armX: 0.06, armZ: g * 0.16, elbow: -0.2, leanX: 0.0, twist: 0, headX: -0.05 + Math.sin(t * 0.45 + this.phase) * 0.06, headY: Math.sin(t * 0.31 + this.phase) * 0.08, back: 0, offX: 0.04, offZ: -g * 0.1 };
    let snap = false;
    if (this.mode === "ready") {
      target.armX = 0.16;
      target.armZ = g * 0.24;
      target.elbow = -0.42 + Math.sin(t * 9 + this.phase) * 0.02;
      target.leanX = 0.06;
      target.headX = -0.12 + Math.sin(t * 0.6) * 0.02;
      target.headY = 0;
    }
    if (this.drawAt !== null) {
      const p = clamp01((now - this.drawAt) / 0.17);
      const e = easeOutBack(p);
      target.armX = lerp(0.18, -1.62, e);
      target.armZ = lerp(g * 0.24, g * 0.03, easeOutCubic(p));
      target.elbow = lerp(-0.45, -0.02, easeOutCubic(p));
      target.leanX = lerp(0.06, -0.02, p);
      target.twist = g * -0.22 * easeOutCubic(p);
      target.headX = -0.02;
      target.headY = g * 0.1 * p;
      snap = true;
      if (p > 0.28 && !this.gunHand.visible && this.holsterAt === null) {
        this.gunHand.visible = true;
        this.holsterGun.visible = false;
      }
      if (this.fireAt !== null) {
        const k = Math.exp(-(now - this.fireAt) * 11) * (now >= this.fireAt ? 1 : 0);
        target.armX -= 0.55 * k;
        target.elbow -= 0.35 * k;
        target.leanX -= 0.05 * k;
      }
      if (this.jamAt !== null && now > this.jamAt) {
        const j = now - this.jamAt;
        const shake = Math.exp(-j * 3.2) * Math.sin(j * 70);
        target.armX += shake * 0.12 + Math.min(1, j * 1.5) * 0.9;
        target.elbow += shake * 0.18 - Math.min(1, j * 1.5) * 0.5;
        target.headX = 0.2 * Math.min(1, j * 2);
        target.headY = g * -0.3 * Math.min(1, j * 2);
        this.gunHand.rotation.x = shake * 0.4 + Math.min(1, j * 1.5) * 0.6;
      }
      if (this.twirlAt !== null && now > this.twirlAt) {
        const w = now - this.twirlAt;
        const spin = clamp01(w / 0.7);
        this.gunHand.rotation.x = -easeOutCubic(spin) * Math.PI * 4;
        target.armX = lerp(-1.62, -0.7, clamp01(w / 0.35));
        target.elbow = lerp(-0.02, -1.3, clamp01(w / 0.35));
        if (w > 0.75) {
          const h = clamp01((w - 0.75) / 0.3);
          target.armX = lerp(-0.7, 0.16, easeOutCubic(h));
          target.elbow = lerp(-1.3, -0.4, easeOutCubic(h));
          target.twist = lerp(g * -0.22, 0, h);
          if (h > 0.7 && this.gunHand.visible) {
            this.gunHand.visible = false;
            this.holsterGun.visible = true;
            this.holsterAt = now;
          }
        }
      }
    }
    if (this.hitAt !== null && now >= this.hitAt) {
      const h = now - this.hitAt;
      const jolt = Math.exp(-h * 5) * Math.sin(Math.min(h * 9, Math.PI));
      target.leanX = -0.32 * jolt - 0.06 * clamp01(h * 2);
      target.headX = -0.45 * jolt;
      target.headY = g * 0.35 * jolt;
      target.back = 0.32 * easeOutCubic(clamp01(h / 0.5));
      target.offX = -0.4 * jolt + 0.1;
      target.offZ = g * 0.5 * jolt - g * 0.1;
      snap = true;
    }

    const c = this.cur;
    const k = snap ? 30 : 5;
    for (const key of Object.keys(target)) c[key] = damp(c[key], target[key], key === "back" ? 10 : k, dt);

    // idle breath and sway
    const breath = Math.sin(t * 1.6 + this.phase);
    this.hips.position.y = 0.98 + breath * 0.004 - c.back * 0.05;
    this.hips.rotation.z = Math.sin(t * 0.7 + this.phase) * 0.018;
    this.torso.rotation.set(c.leanX + breath * 0.01, c.twist, Math.sin(t * 0.7 + this.phase + 0.5) * -0.02);
    this.head.rotation.set(c.headX, c.headY, 0);
    const gun = this.arms[0];
    gun.shoulder.rotation.set(c.armX, 0, c.armZ);
    gun.elbow.rotation.x = c.elbow;
    const off = this.arms[1];
    off.shoulder.rotation.set(c.offX + breath * 0.02, 0, c.offZ);
    off.elbow.rotation.x = -0.25;
    // legs bend a touch with the breath, and step back with a hit
    for (const leg of this.legs) leg.knee.rotation.x = 0.04 + c.back * 0.25;
    this.legs[0].thigh.rotation.x = -c.back * 0.4;
    if (this.ponchoOpen) {
      this.ponchoOpen.visible = this.gunHand.visible;
      this.ponchoClosed.visible = !this.gunHand.visible;
    }
    const dir = this.side < 0 ? -1 : 1;
    this.root.position.x = this.home.x + dir * c.back * 0.6;
  }
}

/** The palette of each gunslinger, from the theme's tokens. */
export function figureColors(tokens, which) {
  const coat = which === 0 ? tokens.p1Coat : tokens.p2Coat;
  const accent = which === 0 ? tokens.p1Accent : tokens.p2Accent;
  const hat = which === 0 ? tokens.p1Hat : tokens.p2Hat;
  return {
    coat: coat.clone(),
    accent: accent.clone(),
    hat: hat.clone(),
    shirt: which === 0 ? new THREE.Color(0.56, 0.48, 0.38) : new THREE.Color(0.22, 0.16, 0.12),
    vest: coat.clone().multiplyScalar(0.55),
    pants: which === 0 ? new THREE.Color(0.24, 0.2, 0.17) : new THREE.Color(0.19, 0.15, 0.11),
    leather: new THREE.Color(0.28, 0.16, 0.09),
    skin: tokens.skin.clone().offsetHSL(0, 0, which === 0 ? 0 : -0.04),
    metal: new THREE.Color(0.55, 0.55, 0.57),
    grip: new THREE.Color(0.35, 0.18, 0.08),
    dark: new THREE.Color(0.06, 0.05, 0.05),
    rim: tokens.rim.clone(),
    rimIntensity: tokens.rimIntensity,
    rimTint: tokens.rimTint,
    fill: tokens.figureFill.clone(),
    fillIntensity: tokens.figureFillIntensity,
  };
}
