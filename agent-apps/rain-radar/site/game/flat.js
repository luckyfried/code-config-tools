// The map drawn flat on a 2D canvas, for a browser with no WebGL: the same map and frames, crossfading, with the
// place marked.

function hex(text) {
  const m = /^#([0-9a-f]{6})$/i.exec((text || "").trim());
  const n = m ? parseInt(m[1], 16) : 0;
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// The procedural map's two fields turned into one colored picture.
function paintMap(land, roads) {
  const size = 512;
  const css = getComputedStyle(document.documentElement);
  const c = (name) => hex(css.getPropertyValue(`--map-${name}`));
  const [water, landC, town, street, road, shore] = ["water", "land", "town", "street", "road", "shore"].map(c);
  const out = document.createElement("canvas");
  out.width = out.height = size;
  const ctx = out.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(land, 0, 0, size, size);
  const L = ctx.getImageData(0, 0, size, size).data;
  ctx.drawImage(roads, 0, 0, size, size);
  const R = ctx.getImageData(0, 0, size, size).data;
  const img = ctx.createImageData(size, size);
  const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  for (let k = 0; k < L.length; k += 4) {
    const f = L[k] / 255;
    let col = f > 0.5 ? landC : water;
    if (f > 0.5) {
      col = mix(col, town, Math.min(1, (R[k + 2] / 255) * 1.3));
      col = mix(col, street, Math.min(1, (R[k] / 255) * 1.6));
      col = mix(col, road, Math.min(1, (R[k + 1] / 255) * 1.4));
    }
    if (Math.abs(f - 0.5) < 0.012) col = shore;
    img.data[k] = col[0];
    img.data[k + 1] = col[1];
    img.data[k + 2] = col[2];
    img.data[k + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return out;
}

export function createFlat(canvas) {
  const ctx = canvas.getContext("2d");
  let map = null;
  let frames = [];
  let w = 1;
  let h = 1;
  let ratio = 1;
  let top = 0;
  let bottom = 0;

  const square = () => {
    const free = h - top - bottom;
    const side = Math.max(w, free) * 1.15;
    return { x: (w - side) / 2, y: top + (free - side) / 2, side };
  };

  return {
    resize(nw, nh, nTop, nBottom) {
      ratio = Math.min(devicePixelRatio || 1, 2);
      w = nw;
      h = nh;
      top = nTop;
      bottom = nBottom;
      canvas.width = Math.round(w * ratio);
      canvas.height = Math.round(h * ratio);
    },
    setMap({ land, roads, base }) {
      map = base ?? (land && roads ? paintMap(land, roads) : null);
    },
    setFrames(list) {
      frames = list;
    },
    placeOnScreen() {
      const s = square();
      return { x: s.x + s.side / 2, y: s.y + s.side / 2 };
    },
    render(view) {
      const s = square();
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--map-edge").trim() || "black";
      ctx.fillRect(0, 0, w, h);
      if (map) ctx.drawImage(map, s.x, s.y, s.side, s.side);
      const a = frames[view.a];
      const b = frames[view.b];
      if (a?.ok) {
        ctx.globalAlpha = 1 - view.mix;
        ctx.drawImage(a.image, s.x, s.y, s.side, s.side);
      }
      if (b?.ok && view.mix > 0) {
        ctx.globalAlpha = view.mix;
        ctx.drawImage(b.image, s.x, s.y, s.side, s.side);
      }
      ctx.globalAlpha = 1;
      const p = this.placeOnScreen();
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--map-marker").trim() || "white";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fill();
    },
  };
}
