// The face printed on each cube's top: the number (or the person's own label) drawn at 256 px into a CanvasTexture,
// pressed into the surface with a light lip below and the ink above, so it reads crisp at any size.
import * as THREE from "three";
import { stepOf } from "./tokens.js";

const SIZE = 256;
const MAX_W = 212;

/** The text for a value: the person's label for 2 through 4096 when they gave twelve, else the number. */
export function textFor(value, labels) {
  if (Array.isArray(labels)) {
    const i = Math.round(Math.log2(value)) - 1;
    if (i >= 0 && i < labels.length) return String(labels[i]);
  }
  return String(value);
}

function fit(ctx, text, family) {
  let px = text.length <= 2 ? 150 : text.length === 3 ? 124 : 104;
  for (; px > 34; px -= 4) {
    ctx.font = `760 ${px}px ${family}`;
    if (ctx.measureText(text).width <= MAX_W) return { lines: [text], px };
  }
  // A long label wraps onto two lines before it shrinks further.
  const words = text.split(/\s+/);
  if (words.length > 1) {
    let best = null;
    for (let cut = 1; cut < words.length; cut += 1) {
      const a = words.slice(0, cut).join(" ");
      const b = words.slice(cut).join(" ");
      for (let size = 96; size > 30; size -= 4) {
        ctx.font = `760 ${size}px ${family}`;
        if (ctx.measureText(a).width <= MAX_W && ctx.measureText(b).width <= MAX_W) {
          if (!best || size > best.px) best = { lines: [a, b], px: size };
          break;
        }
      }
    }
    if (best) return best;
  }
  return { lines: [text], px: 34 };
}

export function createLabels(renderer) {
  const cache = new Map();
  const anisotropy = renderer.capabilities.getMaxAnisotropy();
  let family = "sans-serif";
  let labels = "numbers";
  let inks = [];

  function draw(value) {
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext("2d");
    const text = textFor(value, labels);
    if ("fontStretch" in ctx) ctx.fontStretch = text.length >= 4 ? "semi-condensed" : "normal";
    const { lines, px } = fit(ctx, text, family);
    ctx.font = `760 ${px}px ${family}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const ink = inks[stepOf(value)] ?? "#222";
    const lineH = px * 0.96;
    const top = SIZE / 2 - ((lines.length - 1) * lineH) / 2 + px * 0.04;
    const light = isLight(ink);
    lines.forEach((line, i) => {
      const y = top + i * lineH;
      // The pressed lip: a soft highlight under dark ink, a soft shade under light ink.
      ctx.fillStyle = light ? "rgba(0, 0, 0, 0.28)" : "rgba(255, 255, 255, 0.42)";
      ctx.fillText(line, SIZE / 2, y + 3);
      if (light) {
        // Light ink on a bright cube gets a thin dark keyline, so it reads at arm's length on any color.
        ctx.lineJoin = "round";
        ctx.lineWidth = Math.max(4, px * 0.07);
        ctx.strokeStyle = "rgba(20, 12, 24, 0.55)";
        ctx.strokeText(line, SIZE / 2, y);
      }
      ctx.fillStyle = ink;
      ctx.fillText(line, SIZE / 2, y);
    });
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = anisotropy;
    return tex;
  }

  return {
    configure({ fontFamily, labelSet, inkList }) {
      family = fontFamily;
      labels = labelSet;
      inks = inkList;
      for (const tex of cache.values()) tex.dispose();
      cache.clear();
    },
    reset() {
      for (const tex of cache.values()) tex.dispose();
      cache.clear();
    },
    texture(value) {
      if (!cache.has(value)) cache.set(value, draw(value));
      return cache.get(value);
    },
  };
}

function isLight(css) {
  const c = new THREE.Color(css);
  return c.r * 0.3 + c.g * 0.59 + c.b * 0.11 > 0.5;
}
