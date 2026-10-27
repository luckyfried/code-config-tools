// The photo: what the viewfinder frames, how many stars it earns, and the PNG written from the frame with its stamp.
// Stars: one for a creature in frame, two when it sits inside the middle 60% of the viewfinder at a readable size,
// three when it is also lit (its own glow, the sunlit zone, or the headlights).
import * as THREE from "three";
import { HEADLIGHT } from "../scene/lights.js";
import { SPECIES_BY_ID } from "./species.js";

const v = new THREE.Vector3();
const ndc = new THREE.Vector3();
const toT = new THREE.Vector3();

/** The photo's crop of a w×h frame: 3:2 when the screen is wide, 4:5 when it is tall. */
export function cropFor(w, h) {
  const aspect = w >= h ? 3 / 2 : 4 / 5;
  let cw = w, ch = Math.round(w / aspect);
  if (ch > h) {
    ch = h;
    cw = Math.round(h * aspect);
  }
  return { x: Math.round((w - cw) / 2), y: Math.round((h - ch) / 2), w: cw, h: ch, aspect };
}

/** The best-framed creature for the camera now, or null. */
export function evaluate(world, lampsOn) {
  const cam = world.camera;
  cam.updateMatrixWorld();
  const tanHalf = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2));
  const crop = cropFor(innerWidth, innerHeight);
  // The crop in NDC, so "inside the frame" means inside the photo, not the screen.
  const sx = crop.w / innerWidth, sy = crop.h / innerHeight;
  const density = world.scene.fog.density;
  const subPos = world.sub.position;
  const subFwd = new THREE.Vector3(0, 0, 1).applyQuaternion(world.sub.quaternion);
  let best = null;
  for (const c of world.creatures.list) {
    if (!c.active) continue;
    const sp = SPECIES_BY_ID[c.id];
    for (const tg of c.targets) {
      v.copy(tg.pos).applyMatrix4(cam.matrixWorldInverse);
      const dist = -v.z;
      if (dist < 0.6 || dist > sp.maxDist) continue;
      ndc.copy(tg.pos).project(cam);
      const fx = ndc.x / sx, fy = ndc.y / sy;
      const size = tg.radius / (dist * tanHalf) / sy;
      if (Math.abs(fx) > 1 + size * 0.5 || Math.abs(fy) > 1 + size * 0.5) continue;
      const f = density * dist;
      const visible = Math.exp(-f * f);
      if (visible < 0.22) continue;
      const inside = Math.abs(fx) <= 0.6 && Math.abs(fy) <= 0.6 && size >= 0.06;
      toT.copy(tg.pos).sub(subPos);
      const beamDist = toT.length();
      const inBeam = lampsOn && beamDist < HEADLIGHT.range * 0.85 && toT.normalize().dot(subFwd) > Math.cos(0.75);
      const lit = sp.selfLit || -tg.pos.y < 60 || inBeam;
      const stars = 1 + (inside ? 1 : 0) + (inside && lit ? 1 : 0);
      const score = stars * 10 + Math.min(size, 2) * 2 + visible;
      if (!best || score > best.score) best = { species: c.id, name: sp.name, stars, dist, size, lit, inside, score, depth: Math.round(-tg.pos.y) };
    }
  }
  return best;
}

/**
 * Renders the frame and draws it, cropped, onto a new canvas with the stamp. Must run in the same task as the render
 * so the drawing buffer still holds the frame. Answers the canvas; the PNG is made after.
 */
export function composeFrame(world, info, meta) {
  world.render(0);
  const src = world.renderer.domElement;
  const crop = cropFor(src.width, src.height);
  const landscape = crop.aspect > 1;
  const OW = landscape ? 1800 : 1080;
  const OH = landscape ? 1200 : 1350;
  const out = document.createElement("canvas");
  out.width = OW;
  out.height = OH;
  const g = out.getContext("2d");
  g.drawImage(src, crop.x, crop.y, crop.w, crop.h, 0, 0, OW, OH);
  stamp(g, OW, OH, info, meta);
  return out;
}

function stamp(g, W, H, info, meta) {
  const pad = Math.round(W * 0.04);
  const band = Math.round(H * 0.26);
  const grad = g.createLinearGradient(0, H - band, 0, H);
  grad.addColorStop(0, "rgba(0,0,0,0)");
  grad.addColorStop(1, "rgba(0,0,0,0.72)");
  g.fillStyle = grad;
  g.fillRect(0, H - band, W, band);
  g.textBaseline = "alphabetic";
  g.fillStyle = "#ffffff";
  const big = Math.round(W * (W > H ? 0.042 : 0.062));
  const small = Math.round(big * 0.46);
  g.font = `600 ${big}px Fraunces, Georgia, serif`;
  g.fillText(info ? info.name : "Open water", pad, H - pad - small * 2.3);
  g.font = `500 ${small}px Saira, system-ui, sans-serif`;
  g.globalAlpha = 0.9;
  g.fillText(`${meta.depth} m down, ${meta.dateText}`, pad, H - pad - small * 0.9);
  g.globalAlpha = 0.75;
  g.fillText(`Photo by ${meta.diver}`, pad, H - pad + small * 0.35);
  g.textAlign = "right";
  g.fillText(meta.title, W - pad, H - pad + small * 0.35);
  g.textAlign = "left";
  g.globalAlpha = 1;
  // Stars, top right.
  const n = info ? info.stars : 0;
  const r = Math.round(W * 0.016);
  for (let i = 0; i < 3; i++) {
    const cx = W - pad - r - (2 - i) * r * 2.6;
    const cy = pad + r;
    starPath(g, cx, cy, r);
    if (i < n) {
      g.fillStyle = meta.accent;
      g.fill();
    }
    g.lineWidth = Math.max(2, r * 0.18);
    g.strokeStyle = "#ffffff";
    g.stroke();
  }
}

function starPath(g, cx, cy, r) {
  g.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const rr = i % 2 ? r * 0.45 : r;
    g.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
  }
  g.closePath();
}

export function toPng(canvas) {
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("toBlob"))), "image/png"));
}

export function thumbnail(canvas, width = 240) {
  const t = document.createElement("canvas");
  t.width = width;
  t.height = Math.round((canvas.height / canvas.width) * width);
  t.getContext("2d").drawImage(canvas, 0, 0, t.width, t.height);
  return t.toDataURL("image/jpeg", 0.78);
}

/** Offers the PNG to the share sheet on a phone, or downloads it. */
export async function savePhoto(photo) {
  const file = new File([photo.blob], photo.filename, { type: "image/png" });
  const coarse = matchMedia("(pointer: coarse)").matches;
  if (coarse && navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: photo.name });
      return "shared";
    } catch (e) {
      if (e && e.name === "AbortError") return "cancelled";
    }
  }
  const a = document.createElement("a");
  a.href = photo.url;
  a.download = photo.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return "downloaded";
}
