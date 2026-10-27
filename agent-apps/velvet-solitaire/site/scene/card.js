// The cards: one rounded, beveled slab 63 x 88 x 0.6, drawn 52 times in one instanced draw,
// with every face, the back, and the paper edge packed in one atlas drawn at twice the
// screen's pixel ratio. Lacquered: clearcoat 1.0 over a low-roughness paper.

import * as THREE from "three";
import { drawFace, drawBack, drawEdge } from "../faces.js";
import { CARD_THICK } from "../game/layout.js";

export const CARD_W = 63;
export const CARD_H = 88;
const RADIUS = 3.4;
const BEVEL = 0.16;
export const ATLAS_COLS = 8;
export const ATLAS_ROWS = 7;
export const BACK_CELL = 52;
export const EDGE_CELL = 53;

/** The card slab: front (side 0), back (side 1), and edge (side 2), centered on the origin. */
export function cardGeometry() {
  const w = CARD_W - BEVEL * 2;
  const h = CARD_H - BEVEL * 2;
  const r = RADIUS - BEVEL;
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
  const depth = CARD_THICK - BEVEL * 2;
  const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: true, bevelThickness: BEVEL, bevelSize: BEVEL, bevelSegments: 2, curveSegments: 6 });
  g.translate(0, 0, -depth / 2);
  const pos = g.getAttribute("position");
  const uv = g.getAttribute("uv");
  const side = new Float32Array(pos.count);
  const caps = g.groups.find((gr) => gr.materialIndex === 0);
  for (let i = 0; i < pos.count; i += 1) {
    const inCaps = caps && i >= caps.start && i < caps.start + caps.count;
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    let u = (x + CARD_W / 2) / CARD_W;
    const v = 1 - (y + CARD_H / 2) / CARD_H;
    if (inCaps) {
      const front = z > 0;
      side[i] = front ? 0 : 1;
      // The back is seen turned over, so its image is mirrored to read the right way round.
      if (!front) u = 1 - u;
      uv.setXY(i, u, v);
    } else {
      side[i] = 2;
      uv.setXY(i, 0.5, 0.5);
    }
  }
  g.setAttribute("aSide", new THREE.BufferAttribute(side, 1));
  g.clearGroups();
  g.computeVertexNormals();
  return g;
}

/** The atlas canvas, its cell size picked from the card's size on screen at twice the pixel ratio. */
export function createAtlas(cardCssWidth, pixelRatio) {
  const cellW = Math.max(160, Math.min(320, Math.ceil(cardCssWidth * pixelRatio * 2)));
  const cellH = Math.round((cellW * CARD_H) / CARD_W);
  const canvas = document.createElement("canvas");
  canvas.width = cellW * ATLAS_COLS;
  canvas.height = cellH * ATLAS_ROWS;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.flipY = false;
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return { canvas, texture, cellW, cellH, pad: 3 };
}

/** Draws all 52 faces, the back, and the edge into the atlas. */
export function paintAtlas(atlas, look, back) {
  const ctx = atlas.canvas.getContext("2d");
  const { cellW, cellH, pad } = atlas;
  ctx.clearRect(0, 0, atlas.canvas.width, atlas.canvas.height);
  for (let cell = 0; cell < ATLAS_COLS * ATLAS_ROWS; cell += 1) {
    const x = (cell % ATLAS_COLS) * cellW;
    const y = Math.floor(cell / ATLAS_COLS) * cellH;
    if (cell < 52) {
      // Bleed the paper color under the margin so mipmaps never pull in a neighbor.
      ctx.fillStyle = look.face;
      ctx.fillRect(x, y, cellW, cellH);
      drawFace(ctx, cell, x + pad, y + pad, cellW - pad * 2, cellH - pad * 2, look);
    } else if (cell === BACK_CELL) {
      ctx.fillStyle = look.backFrame;
      ctx.fillRect(x, y, cellW, cellH);
      drawBack(ctx, x + pad, y + pad, cellW - pad * 2, cellH - pad * 2, look, back.style, back.initials, back.image);
    } else if (cell === EDGE_CELL) {
      drawEdge(ctx, x, y, cellW, cellH, look);
    }
  }
  atlas.texture.needsUpdate = true;
}

/** The lacquered card material, reading each instance's face, side, and opacity. */
export function cardMaterial(atlas, { reduced }) {
  const mat = new THREE.MeshPhysicalMaterial({
    map: atlas.texture,
    roughness: 0.42,
    metalness: 0,
    clearcoat: 1,
    clearcoatRoughness: 0.09,
    envMapIntensity: 0.9,
    alphaHash: reduced,
  });
  const inset = new THREE.Vector2(atlas.pad / atlas.cellW, atlas.pad / atlas.cellH);
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uInset = { value: inset };
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
attribute float aFace;
attribute float aSide;
attribute float aOpacity;
attribute vec2 aGloss;
uniform vec2 uInset;
varying float vCardOpacity;
varying vec2 vGloss;
varying vec2 vCardUv;
varying float vCardSide;`,
      )
      .replace(
        "#include <uv_vertex>",
        `#include <uv_vertex>
float cell = aSide < 0.5 ? aFace : (aSide < 1.5 ? ${BACK_CELL}.0 : ${EDGE_CELL}.0);
vec2 cellXY = vec2(mod(cell, ${ATLAS_COLS}.0), floor(cell / ${ATLAS_COLS}.0));
vec2 inCell = uInset + uv * (1.0 - 2.0 * uInset);
vMapUv = (cellXY + inCell) / vec2(${ATLAS_COLS}.0, ${ATLAS_ROWS}.0);
vCardOpacity = aOpacity;
vGloss = aGloss;
vCardUv = uv;
vCardSide = aSide;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\nvarying float vCardOpacity;\nvarying vec2 vGloss;\nvarying vec2 vCardUv;\nvarying float vCardSide;`)
      .replace("#include <map_fragment>", `#include <map_fragment>\ndiffuseColor.a *= vCardOpacity;`)
      .replace(
        "#include <opaque_fragment>",
        `// The clearcoat streak: the lamp's long reflection lying across a lifted or tilted card,
// sliding with the tilt and washing the ink under it, the rest of the face a shade darker.
if (vCardSide < 1.5 && vGloss.x > 0.001) {
  float along = dot(vCardUv - 0.5, vec2(0.53, 0.85)) - vGloss.y;
  float core = exp(-along * along / 0.0018);
  float second = exp(-(along - 0.17) * (along - 0.17) / 0.0005);
  float bloom = exp(-along * along / 0.026);
  float streak = clamp((core * 0.85 + second * 0.45 + bloom * 0.14) * vGloss.x, 0.0, 0.85);
  outgoingLight *= 1.0 - 0.17 * vGloss.x * (1.0 - bloom);
  outgoingLight = mix(outgoingLight, vec3(1.2, 1.26, 1.34), streak);
}
#include <opaque_fragment>`,
      );
  };
  mat.customProgramCacheKey = () => `velvet-card-${reduced ? 1 : 0}`;
  return mat;
}

/** The 52 cards as one instanced mesh, with per-card face and opacity attributes. */
export function createCards(atlas, opts) {
  const geometry = cardGeometry();
  const face = new THREE.InstancedBufferAttribute(new Float32Array(52), 1);
  const opacity = new THREE.InstancedBufferAttribute(new Float32Array(52).fill(1), 1);
  for (let i = 0; i < 52; i += 1) face.array[i] = i;
  geometry.setAttribute("aFace", face);
  geometry.setAttribute("aOpacity", opacity);
  opacity.setUsage(THREE.DynamicDrawUsage);
  // Per card: how strongly the clearcoat streak shows, and where it lies across the face.
  const gloss = new THREE.InstancedBufferAttribute(new Float32Array(104), 2);
  gloss.setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute("aGloss", gloss);
  const mesh = new THREE.InstancedMesh(geometry, cardMaterial(atlas, opts), 52);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  return { mesh, opacity, gloss };
}

/** A soft, blurred rounded-rectangle shadow, drawn once and shared by every card. */
export function shadowTexture() {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 160;
  const ctx = c.getContext("2d");
  // Drawn off the canvas with its shadow cast back in: a blur every browser's canvas supports.
  ctx.shadowColor = "#000";
  ctx.shadowBlur = 16;
  ctx.shadowOffsetX = 1000;
  ctx.fillStyle = "#000";
  ctx.beginPath();
  ctx.roundRect(28 - 1000, 30, 72, 100, 8);
  ctx.fill();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

/** One instanced quad per card for its contact shadow; opacity and spread per instance. */
export function createShadows() {
  const geometry = new THREE.PlaneGeometry(1, 1);
  const alpha = new THREE.InstancedBufferAttribute(new Float32Array(52), 1);
  alpha.setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute("aAlpha", alpha);
  const material = new THREE.ShaderMaterial({
    uniforms: { uMap: { value: shadowTexture() }, uColor: { value: new THREE.Color(0, 0, 0) }, uStrength: { value: 0.5 } },
    vertexShader: `
attribute float aAlpha;
varying vec2 vUv;
varying float vAlpha;
void main() {
  vUv = uv;
  vAlpha = aAlpha;
  gl_Position = projectionMatrix * viewMatrix * modelMatrix * instanceMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform sampler2D uMap;
uniform vec3 uColor;
uniform float uStrength;
varying vec2 vUv;
varying float vAlpha;
void main() {
  float a = texture2D(uMap, vUv).a * vAlpha * uStrength;
  gl_FragColor = vec4(uColor, a);
}`,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, 52);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.renderOrder = 1;
  return { mesh, alpha, material };
}

/** A glowing rounded-rectangle ring for hints, the keyboard cursor, and a held run. */
export function createHalo() {
  const material = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(1, 0.8, 0.4) }, uSize: { value: new THREE.Vector2(70, 95) }, uPower: { value: 0 }, uTime: { value: 0 } },
    vertexShader: `
varying vec2 vPos;
uniform vec2 uSize;
void main() {
  vPos = (uv - 0.5) * uSize;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform vec3 uColor;
uniform vec2 uSize;
uniform float uPower;
uniform float uTime;
varying vec2 vPos;
float box(vec2 p, vec2 b, float r) { vec2 q = abs(p) - b + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }
void main() {
  float d = box(vPos, vec2(${CARD_W / 2 + 1.2}, ${CARD_H / 2 + 1.2}), ${RADIUS + 1.2});
  float ring = smoothstep(2.4, 0.0, abs(d)) + step(0.0, d) * smoothstep(10.0, 0.0, d) * 0.5;
  float pulse = 0.78 + 0.22 * sin(uTime * 5.0);
  gl_FragColor = vec4(uColor, ring * uPower * pulse);
}`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(CARD_W + 22, CARD_H + 22), material);
  material.uniforms.uSize.value.set(CARD_W + 22, CARD_H + 22);
  mesh.renderOrder = 3;
  mesh.visible = false;
  return mesh;
}
