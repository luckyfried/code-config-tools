// The stage: a glass tray with a socket etched for every cell and a light line inlaid round its edge, standing on a
// satin pedestal whose band glows up under the tray, on a floor with a pool of light around it. Nothing casts a
// shadow map: where the pedestal stands, a soft contact shade is painted on the floor instead.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { contactShade, floorStone, glassTray, lightLine, pedestalMetal, socketSheet } from "./materials.js";

export const PITCH = 1;
export const CUBE = 0.86;
const MARGIN = 0.22;
const SLAB = 0.36;
const PEDESTAL_H = 6;
const BAND_GAP = 0.08;

export function trayWidth(size) {
  return size * PITCH - (PITCH - CUBE) + MARGIN * 2;
}

/** Cell (r, c) to the tray's x and z; row 0 is the far side. */
export function cellX(c, size) {
  return (c - (size - 1) / 2) * PITCH;
}
export function cellZ(r, size) {
  return (r - (size - 1) / 2) * PITCH;
}

function roundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function socketTexture(size, tokens, anisotropy) {
  const W = trayWidth(size);
  const px = 1024;
  const k = px / W;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  const cell = 0.92 * k;
  const radius = 0.15 * k;
  for (let r = 0; r < size; r += 1) {
    for (let c = 0; c < size; c += 1) {
      const cx = (cellX(c, size) + W / 2) * k;
      const cy = (cellZ(r, size) + W / 2) * k;
      const x = cx - cell / 2;
      const y = cy - cell / 2;
      // The well: the socket color, shaded deeper at the far lip where the edge hides the light.
      roundedRect(ctx, x, y, cell, cell, radius);
      ctx.fillStyle = tokens.socketCss;
      ctx.fill();
      const shade = ctx.createLinearGradient(0, y, 0, y + cell);
      shade.addColorStop(0, "rgba(0, 0, 0, 0.32)");
      shade.addColorStop(0.35, "rgba(0, 0, 0, 0.06)");
      shade.addColorStop(1, "rgba(255, 255, 255, 0.05)");
      ctx.fillStyle = shade;
      ctx.fill();
      // The cut edge: a fine line all round, brightest on the near lip that faces the light.
      ctx.lineWidth = Math.max(2, k * 0.012);
      ctx.strokeStyle = tokens.socketEdgeCss;
      ctx.stroke();
      ctx.save();
      ctx.clip();
      ctx.beginPath();
      ctx.moveTo(x + radius, y + cell - 1.5);
      ctx.lineTo(x + cell - radius, y + cell - 1.5);
      ctx.lineWidth = Math.max(2, k * 0.01);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.16)";
      ctx.stroke();
      ctx.restore();
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = anisotropy;
  return tex;
}

function floorTexture(tokens) {
  const px = 1024;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  const c = px / 2;
  ctx.fillStyle = tokens.floorCss;
  ctx.fillRect(0, 0, px, px);
  if (tokens.floorPattern === "rings") {
    ctx.strokeStyle = tokens.dark ? "rgba(255, 220, 160, 0.05)" : "rgba(40, 30, 20, 0.05)";
    ctx.lineWidth = 2;
    for (let r = 60; r < c; r += 26) {
      ctx.beginPath();
      ctx.arc(c, c, r, 0, Math.PI * 2);
      ctx.stroke();
    }
  } else if (tokens.floorPattern === "grid") {
    ctx.strokeStyle = tokens.dark ? "rgba(63, 228, 255, 0.16)" : "rgba(11, 127, 154, 0.12)";
    ctx.lineWidth = 2;
    for (let x = c % 32; x < px; x += 32) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, px);
      ctx.moveTo(0, x);
      ctx.lineTo(px, x);
      ctx.stroke();
    }
  } else if (tokens.floorPattern === "dots") {
    ctx.fillStyle = tokens.dark ? "rgba(255, 190, 210, 0.08)" : "rgba(120, 60, 90, 0.07)";
    for (let y = 8; y < px; y += 22) for (let x = 8 + ((y / 22) % 2) * 11; x < px; x += 22) {
      ctx.beginPath();
      ctx.arc(x, y, 2.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  // The pool of light round the pedestal, and the falloff into the room.
  const pool = ctx.createRadialGradient(c, c, 0, c, c, c * 0.45);
  pool.addColorStop(0, tokens.floorGlowCss);
  pool.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.globalAlpha = tokens.dark ? 0.5 : 0.6;
  ctx.fillStyle = pool;
  ctx.fillRect(0, 0, px, px);
  ctx.globalAlpha = 1;
  const fall = ctx.createRadialGradient(c, c, c * 0.25, c, c, c);
  fall.addColorStop(0, "rgba(0, 0, 0, 0)");
  fall.addColorStop(1, tokens.bgCss);
  ctx.fillStyle = fall;
  ctx.fillRect(0, 0, px, px);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function bandGlowTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 4;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, "#ffffff");
  g.addColorStop(0.1, "#5a5a5a");
  g.addColorStop(0.35, "#000000");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(canvas);
  return tex;
}

/** A soft square shade, darkest under the pedestal's foot and gone a pedestal's width out. */
function shadeTexture(dark) {
  const px = 256;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.filter = `blur(${px * 0.07}px)`;
  ctx.fillStyle = dark ? "rgba(0, 0, 0, 0.6)" : "rgba(20, 18, 14, 0.34)";
  roundedRect(ctx, px * 0.3, px * 0.3, px * 0.4, px * 0.4, px * 0.06);
  ctx.fill();
  ctx.filter = `blur(${px * 0.02}px)`;
  ctx.fillStyle = dark ? "rgba(0, 0, 0, 0.5)" : "rgba(20, 18, 14, 0.28)";
  roundedRect(ctx, px * 0.33, px * 0.33, px * 0.34, px * 0.34, px * 0.04);
  ctx.fill();
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function ringGeometry(outer, inner, r1, r2) {
  const shape = new THREE.Shape();
  const rr = (s, x, y, w, h, r) => {
    s.moveTo(x + r, y);
    s.lineTo(x + w - r, y);
    s.quadraticCurveTo(x + w, y, x + w, y + r);
    s.lineTo(x + w, y + h - r);
    s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    s.lineTo(x + r, y + h);
    s.quadraticCurveTo(x, y + h, x, y + h - r);
    s.lineTo(x, y + r);
    s.quadraticCurveTo(x, y, x + r, y);
  };
  rr(shape, -outer / 2, -outer / 2, outer, outer, r1);
  const hole = new THREE.Path();
  rr(hole, -inner / 2, -inner / 2, inner, inner, r2);
  shape.holes.push(hole);
  const geo = new THREE.ShapeGeometry(shape, 12);
  geo.rotateX(-Math.PI / 2);
  return geo;
}

export function createTray({ size, tokens, renderer }) {
  const group = new THREE.Group();
  const W = trayWidth(size);
  const disposables = [];
  const keep = (x) => {
    disposables.push(x);
    return x;
  };
  const anisotropy = renderer.capabilities.getMaxAnisotropy();

  const slab = new THREE.Mesh(keep(new RoundedBoxGeometry(W, SLAB, W, 6, 0.2)), keep(glassTray(tokens)));
  slab.position.y = -SLAB / 2;
  group.add(slab);

  const sheetMap = keep(socketTexture(size, tokens, anisotropy));
  const sheet = new THREE.Mesh(keep(new THREE.PlaneGeometry(W, W)), keep(socketSheet(tokens, sheetMap)));
  sheet.rotation.x = -Math.PI / 2;
  sheet.position.y = 0.001;
  group.add(sheet);

  const inlay = new THREE.Mesh(keep(ringGeometry(W - 0.1, W - 0.15, 0.15, 0.13)), keep(lightLine(tokens.rim, tokens.rimGlow)));
  inlay.position.y = 0.003;
  group.add(inlay);

  const pw = W * 0.64;
  const glowMap = keep(bandGlowTexture());
  const pedestal = new THREE.Mesh(keep(new RoundedBoxGeometry(pw, PEDESTAL_H, pw, 4, 0.12)), keep(pedestalMetal(tokens, glowMap)));
  pedestal.position.y = -SLAB - BAND_GAP - PEDESTAL_H / 2;
  group.add(pedestal);

  const band = new THREE.Mesh(keep(new RoundedBoxGeometry(pw + 0.08, BAND_GAP, pw + 0.08, 2, 0.04)), keep(lightLine(tokens.band, tokens.bandGlow)));
  band.position.y = -SLAB - BAND_GAP / 2;
  group.add(band);

  const floorY = -SLAB - BAND_GAP - PEDESTAL_H;
  const floorMap = keep(floorTexture(tokens));
  const floor = new THREE.Mesh(keep(new THREE.PlaneGeometry(64, 64)), keep(floorStone(floorMap)));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = floorY;
  group.add(floor);

  const shadeMap = keep(shadeTexture(tokens.dark));
  const shade = new THREE.Mesh(keep(new THREE.PlaneGeometry(pw * 2.5, pw * 2.5)), keep(contactShade(shadeMap)));
  shade.rotation.x = -Math.PI / 2;
  shade.position.y = floorY + 0.002;
  group.add(shade);

  const inlayColor = inlay.material.color.clone();
  const bandColor = band.material.color.clone();
  const pedestalGlow = pedestal.material.emissiveIntensity;

  return {
    group,
    width: W,
    floorY,
    /** The box the camera frames: the tray and the cubes standing on it. */
    box: new THREE.Box3(new THREE.Vector3(-W / 2, -SLAB, -W / 2), new THREE.Vector3(W / 2, 0.8, W / 2)),
    /** Turns the light lines and the floor down for the 2048 moment; 0 is full light. */
    setDim(dim) {
      inlay.material.color.copy(inlayColor).multiplyScalar(1 - 0.6 * dim);
      band.material.color.copy(bandColor).multiplyScalar(1 - 0.6 * dim);
      pedestal.material.emissiveIntensity = pedestalGlow * (1 - 0.6 * dim);
      floor.material.color.setScalar(1 - 0.3 * dim);
    },
    dispose() {
      group.removeFromParent();
      for (const d of disposables) d.dispose();
    },
  };
}
