// Glass pieces: geometry from profiles.js, one merged mesh per piece, clear glass for white and smoke glass
// for black. Each piece also carries a cheap stand-in material that the reflection pass draws, so the mirror image
// never pays for a second transmission render.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { profiles, rookMerlons, queenBeads, kingCross, knightHead, heights, footRadius } from "./profiles.js";

const TYPES = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };
const LATHE_SEGMENTS = 56;

const lathe = (points) => new THREE.LatheGeometry(points.map(([r, y]) => new THREE.Vector2(r, y)), LATHE_SEGMENTS);
const flat = (g) => (g.index ? g.toNonIndexed() : g);

function merlons() {
  const { count, spanDeg, inner, outer, bottom, top } = rookMerlons;
  const parts = [];
  for (let i = 0; i < count; i++) {
    const a0 = ((i * 360) / count) * (Math.PI / 180);
    const a1 = a0 + spanDeg * (Math.PI / 180);
    const shape = new THREE.Shape();
    shape.absarc(0, 0, outer, a0, a1, false);
    shape.absarc(0, 0, inner, a1, a0, true);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: top - bottom - 0.02, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2, curveSegments: 10,
    });
    g.rotateX(-Math.PI / 2);
    g.translate(0, bottom + 0.01, 0);
    parts.push(flat(g));
  }
  return parts;
}

function beads() {
  const { count, radius, ring, height } = queenBeads;
  const parts = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const g = new THREE.SphereGeometry(radius, 14, 10);
    g.translate(Math.cos(a) * ring, height, Math.sin(a) * ring);
    parts.push(flat(g));
  }
  return parts;
}

function cross() {
  const shape = new THREE.Shape(kingCross.outline.map(([x, y]) => new THREE.Vector2(x, y)));
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: kingCross.depth, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.01, bevelSegments: 2,
  });
  g.translate(0, kingCross.base, -kingCross.depth / 2);
  return flat(g);
}

export function knightShape() {
  const shape = new THREE.Shape();
  shape.moveTo(...knightHead.start);
  for (const [cx, cy, x, y] of knightHead.path) shape.quadraticCurveTo(cx, cy, x, y);
  return shape;
}

function head() {
  const { depth, bevel } = knightHead;
  const g = new THREE.ExtrudeGeometry(knightShape(), {
    depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 4, curveSegments: 16,
  });
  g.translate(0, 0, -depth / 2);
  g.computeVertexNormals();
  return flat(g);
}

const cache = new Map();
export function pieceGeometry(type) {
  if (cache.has(type)) return cache.get(type);
  const name = TYPES[type];
  const parts = [flat(lathe(profiles[name]))];
  if (type === "r") parts.push(...merlons());
  if (type === "q") parts.push(...beads());
  if (type === "k") parts.push(cross());
  if (type === "n") parts.push(head());
  for (const p of parts) { p.deleteAttribute("uv"); }
  const g = mergeGeometries(parts);
  g.computeBoundingSphere();
  cache.set(type, g);
  return g;
}

export const pieceHeight = (type) => heights[TYPES[type]];

// The two glasses, tinted by the theme's tokens.
// A bright edge where the glass turns away from the eye, in the key light's color: the glow along a piece's outline.
function withRim(material, color, strength) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uRim = { value: color.clone().multiplyScalar(strength) };
    shader.fragmentShader = shader.fragmentShader
      .replace("void main() {", "uniform vec3 uRim;\nvoid main() {")
      .replace(
        "#include <opaque_fragment>",
        "outgoingLight += uRim * pow(1.0 - clamp(dot(normalize(normal), normalize(vViewPosition)), 0.0, 1.0), 3.0);\n#include <opaque_fragment>",
      );
  };
  // Each material compiles its own program, so its rim uniform is always the one uploaded.
  material.customProgramCacheKey = () => material.uuid;
  return material;
}

export function glassMaterials(tokens, tier) {
  const rim = tokens.color("--key-light");
  const clear = withRim(new THREE.MeshPhysicalMaterial({
    color: tokens.color("--glass-white"),
    metalness: 0,
    roughness: 0.05,
    transmission: 1,
    ior: 1.7,
    thickness: 1.9,
    attenuationColor: tokens.color("--glass-white-tint"),
    attenuationDistance: 2.4,
    specularIntensity: 1,
    clearcoat: 0.3,
    clearcoatRoughness: 0.03,
    dispersion: tier === "desktop" ? 0.35 : 0,
    envMapIntensity: 0.95,
  }), rim, 0.75);
  // Smoke glass: clear enough that the squares show through dimly, dark where the glass is thick.
  const smoke = withRim(new THREE.MeshPhysicalMaterial({
    color: tokens.color("--glass-black"),
    metalness: 0,
    roughness: 0.06,
    transmission: 1,
    ior: 1.6,
    thickness: 0.8,
    attenuationColor: tokens.color("--glass-black-tint"),
    attenuationDistance: 0.95,
    specularIntensity: 1,
    clearcoat: 0.5,
    clearcoatRoughness: 0.04,
    envMapIntensity: 1,
  }), rim, 0.9);
  // What the mirror sees: the same tint, no transmission.
  const clearMirror = new THREE.MeshStandardMaterial({
    color: tokens.color("--glass-white-tint"), roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0.55,
  });
  const frostedMirror = new THREE.MeshStandardMaterial({
    color: tokens.color("--glass-black-tint"), roughness: 0.3, metalness: 0.2, transparent: true, opacity: 0.75,
  });
  return { w: clear, b: smoke, mirror: { w: clearMirror, b: frostedMirror } };
}

// Marble pieces for a machine that cannot hold the frame rate with transmission: a procedural vein texture.
export function marbleMaterials(tokens) {
  const veins = (base, vein) => {
    const c = document.createElement("canvas");
    c.width = c.height = 512;
    const g = c.getContext("2d");
    g.fillStyle = base;
    g.fillRect(0, 0, 512, 512);
    g.strokeStyle = vein;
    for (let i = 0; i < 26; i++) {
      g.globalAlpha = 0.08 + (i % 5) * 0.05;
      g.lineWidth = 0.6 + (i % 4);
      g.beginPath();
      let x = (i * 97) % 512, y = 0;
      g.moveTo(x, y);
      while (y < 512) { x += Math.sin(y * 0.03 + i) * 9; y += 12; g.lineTo(x, y); }
      g.stroke();
    }
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  };
  const make = (base, vein) => new THREE.MeshPhysicalMaterial({
    map: veins(base, vein), roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.08,
  });
  return {
    w: make(tokens.css("--marble-white"), tokens.css("--marble-white-vein")),
    b: make(tokens.css("--marble-black"), tokens.css("--marble-black-vein")),
  };
}

export class Piece {
  constructor(type, color, materials) {
    this.type = type;
    this.color = color;
    this.mesh = new THREE.Mesh(pieceGeometry(type), materials[color]);
    this.mesh.userData.piece = this;
    this.group = new THREE.Group();
    this.group.add(this.mesh);
    this.square = null;
    this.lift = 0;
    this.sinking = 0;
    this.tipped = 0;
    this.setMaterials(materials);
    this.setType(type);
  }

  setType(type) {
    this.type = type;
    this.height = pieceHeight(type);
    this.radius = footRadius[TYPES[type]];
    this.mesh.geometry = pieceGeometry(type);
    // Knights look across the board toward the other side, turned a little to face their player.
    this.mesh.rotation.y = type === "n" ? (this.color === "w" ? Math.PI - 0.45 : -0.45) : 0;
  }

  setMaterials(materials) {
    this.material = materials[this.color];
    this.mirrorMaterial = materials.mirror ? materials.mirror[this.color] : this.material;
    this.fadeMaterial = null;
    this.mesh.material = this.material;
  }

  // Opacity for the reduced-motion cross-fade; 1 puts the shared glass back.
  fade(v) {
    if (v >= 1) { this.mesh.material = this.material; return; }
    if (!this.fadeMaterial) {
      this.fadeMaterial = this.material.clone();
      this.fadeMaterial.transparent = true;
    }
    this.fadeMaterial.opacity = Math.max(0, v);
    this.mesh.material = this.fadeMaterial;
  }
}

// Renders one piece of each kind into small pictures for the promotion choice, the side picker, and the plates.
export function renderIcons(renderer, materials, environment, tokens) {
  const size = 192;
  const target = new THREE.WebGLRenderTarget(size, size);
  target.texture.colorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.environment = environment;
  // Small pictures need solid shapes: polished stand-ins in the two glass colors, on a clear background.
  const solid = {
    w: new THREE.MeshPhysicalMaterial({ color: tokens.color("--glass-white-tint"), roughness: 0.12, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.3 }),
    b: new THREE.MeshPhysicalMaterial({ color: tokens.color("--glass-black-tint"), roughness: 0.2, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 1.1 }),
  };
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(-2, 3, 3);
  scene.add(key);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
  const pixels = new Uint8Array(size * size * 4);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const icons = {};
  const prevTarget = renderer.getRenderTarget();
  for (const color of ["w", "b"]) {
    for (const type of ["p", "n", "b", "r", "q", "k"]) {
      const mesh = new THREE.Mesh(pieceGeometry(type), solid[color]);
      if (type === "n") mesh.rotation.y = Math.PI - 0.45;
      scene.add(mesh);
      const h = pieceHeight(type);
      camera.position.set(0, h * 0.62, 3.3);
      camera.lookAt(0, h * 0.47, 0);
      renderer.setRenderTarget(target);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.render(scene, camera);
      renderer.readRenderTargetPixels(target, 0, 0, size, size, pixels);
      const image = ctx.createImageData(size, size);
      for (let y = 0; y < size; y++) {
        image.data.set(pixels.subarray((size - 1 - y) * size * 4, (size - y) * size * 4), y * size * 4);
      }
      ctx.putImageData(image, 0, 0);
      icons[color + type] = canvas.toDataURL("image/png");
      scene.remove(mesh);
    }
  }
  renderer.setRenderTarget(prevTarget);
  target.dispose();
  solid.w.dispose();
  solid.b.dispose();
  return icons;
}
