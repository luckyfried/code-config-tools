// The fallback when WebGL is not there: the same table drawn from above on a 2D canvas. Discs are ellipses whose width
// shrinks and grows through the flip, with the same stagger and ticks as the 3D table.
import { BLACK, WHITE } from "../game/reversi.js";
import { trayLayout, stackSpot } from "../scene/trays.js";

const R = 0.42;
const EDGE = 4.5;

export function createCanvasView({ host, tokens }) {
  const canvas = document.createElement("canvas");
  host.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  let size = { width: 1, height: 1 };
  let ratio = Math.min(devicePixelRatio || 1, 2);
  let layout = trayLayout("wide");
  let view = { scale: 40, ox: 0, oy: 0 };
  let from = view;
  let to = view;
  let start = 0;

  function box(mode) {
    if (mode === "wide") {
      const x = layout.centers[WHITE].x + layout.size.w / 2 + 0.1;
      const rim = Math.max(EDGE, layout.size.d / 2);
      if (layout.cardsAbove) return { x0: -x, x1: x, z0: layout.anchors[BLACK].z - 1.4, z1: rim };
      return { x0: -x, x1: x, z0: -rim, z1: Math.max(rim, layout.anchors[BLACK].z + 0.8) };
    }
    const z = layout.centers[BLACK].z + layout.size.d / 2 + 1.7;
    return { x0: -EDGE, x1: EDGE, z0: -z, z1: z };
  }

  function frame({ width, height, rect, mode, cardsAbove = false, now, immediate }) {
    const above = mode === "wide" && cardsAbove;
    if (mode !== layout.mode || above !== layout.cardsAbove) layout = trayLayout(mode, above);
    if (width !== size.width || height !== size.height) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      size = { width, height };
    }
    const b = box(mode);
    const scale = Math.min(rect.width / (b.x1 - b.x0), rect.height / (b.z1 - b.z0));
    const next = {
      scale,
      ox: rect.x + rect.width / 2 - ((b.x0 + b.x1) / 2) * scale,
      oy: rect.y + rect.height / 2 - ((b.z0 + b.z1) / 2) * scale,
    };
    from = immediate ? next : current(now);
    to = next;
    start = immediate ? now - 700 : now;
  }

  function current(now) {
    const p = Math.min(1, Math.max(0, (now - start) / 700));
    const e = 1 - Math.pow(1 - p, 3);
    return { scale: from.scale + (to.scale - from.scale) * e, ox: from.ox + (to.ox - from.ox) * e, oy: from.oy + (to.oy - from.oy) * e };
  }

  const sx = (x) => view.ox + x * view.scale;
  const sy = (z) => view.oy + z * view.scale;

  function disc(x, z, color, angle, ax, az, lift, scale, alpha = 1) {
    if (scale <= 0.01) return;
    const c = Math.cos(angle);
    const face = c >= 0 ? color : color === BLACK ? WHITE : BLACK;
    const rot = Math.atan2(az, ax);
    const r = R * view.scale * scale * (1 + lift * 0.35);
    ctx.save();
    ctx.globalAlpha = alpha * 0.35;
    ctx.fillStyle = "#000000";
    ctx.beginPath();
    ctx.ellipse(sx(x) + lift * view.scale * 0.35, sy(z) + lift * view.scale * 0.45, r, Math.max(1, r * Math.abs(c)), rot, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = face === BLACK ? tokens.discDark : tokens.discLight;
    ctx.beginPath();
    ctx.ellipse(sx(x), sy(z) - lift * view.scale * 0.2, r, Math.max(1, r * Math.abs(c)), rot, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = alpha * 0.25;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(1, r * 0.08);
    ctx.beginPath();
    ctx.ellipse(sx(x), sy(z) - lift * view.scale * 0.2, r * 0.82, Math.max(1, r * 0.82 * Math.abs(c)), rot, Math.PI * 1.1, Math.PI * 1.6);
    ctx.stroke();
    ctx.restore();
  }

  function glow(x, z, radius, alpha) {
    if (alpha <= 0.01) return;
    const g = ctx.createRadialGradient(sx(x), sy(z), 0, sx(x), sy(z), radius * view.scale);
    g.addColorStop(0, tokens.glow);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = alpha;
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(sx(x), sy(z), radius * view.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  const pose = {};
  const spot = {};
  function render(model, now) {
    view = current(now);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const bg = ctx.createRadialGradient(sx(0), sy(0), view.scale * 2, sx(0), sy(0), Math.max(size.width, size.height) * 0.8);
    bg.addColorStop(0, tokens.table);
    bg.addColorStop(1, tokens.tableEdge);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, size.width, size.height);

    for (const color of [BLACK, WHITE]) {
      const c = layout.centers[color];
      const shake = model.shakeOffset(color, now);
      const tx = c.x + layout.shakeAxis.x * shake;
      const tz = c.z + layout.shakeAxis.z * shake;
      ctx.fillStyle = tokens.tray;
      ctx.beginPath();
      ctx.roundRect(sx(tx - layout.size.w / 2), sy(tz - layout.size.d / 2), layout.size.w * view.scale, layout.size.d * view.scale, 0.22 * view.scale);
      ctx.fill();
      ctx.fillStyle = tokens.trayFloor;
      ctx.beginPath();
      ctx.roundRect(sx(tx - layout.size.w / 2 + 0.1), sy(tz - layout.size.d / 2 + 0.1), (layout.size.w - 0.2) * view.scale, (layout.size.d - 0.2) * view.scale, 0.14 * view.scale);
      ctx.fill();
      const stack = model.trays[color];
      let slot = 0;
      for (let j = 0; j < stack.length && slot < 64; j += 1) {
        model.trayPose(color, j, now, pose);
        if (!pose.visible) continue;
        stackSpot(layout, color, slot, spot);
        disc(tx + spot.x, tz + spot.z - spot.level * 0.05, color, 0, 1, 0, pose.lift, pose.scale * 0.9);
        slot += 1;
      }
    }

    ctx.fillStyle = tokens.rim;
    ctx.beginPath();
    ctx.roundRect(sx(-EDGE), sy(-EDGE), 9 * view.scale, 9 * view.scale, 0.32 * view.scale);
    ctx.fill();
    ctx.fillStyle = tokens.board;
    ctx.fillRect(sx(-4), sy(-4), 8 * view.scale, 8 * view.scale);
    ctx.strokeStyle = tokens.line;
    ctx.lineWidth = Math.max(1, view.scale * 0.03);
    ctx.beginPath();
    for (let k = 0; k <= 8; k += 1) {
      ctx.moveTo(sx(-4 + k), sy(-4));
      ctx.lineTo(sx(-4 + k), sy(4));
      ctx.moveTo(sx(-4), sy(-4 + k));
      ctx.lineTo(sx(4), sy(-4 + k));
    }
    ctx.stroke();

    const level = model.legalLevel(now);
    for (const square of model.legal) glow((square % 8) - 3.5, Math.floor(square / 8) - 3.5, 0.32 * level, 0.9);
    if (model.last.square >= 0) glow((model.last.square % 8) - 3.5, Math.floor(model.last.square / 8) - 3.5, 0.8, model.glowLevel(now));
    if (model.hint.square >= 0) glow((model.hint.square % 8) - 3.5, Math.floor(model.hint.square / 8) - 3.5, 0.7, model.hintLevel(now));

    for (let i = 0; i < 64; i += 1) {
      model.pose(i, now, pose);
      if (!pose.visible) continue;
      const x = (i % 8) - 3.5;
      const z = Math.floor(i / 8) - 3.5;
      disc(x, z, pose.show, pose.angle, pose.ax, pose.az, pose.lift, pose.scale);
      if (pose.fade > 0) disc(x, z, pose.to, 0, 1, 0, 0, pose.scale, pose.fade);
    }
    if (model.preview) {
      const p = model.preview;
      disc((p.square % 8) - 3.5, Math.floor(p.square / 8) - 3.5, p.color, 0, 1, 0, 0, 1, 0.5);
      for (const s of p.flips) disc((s % 8) - 3.5, Math.floor(s / 8) - 3.5, p.color, 0, 1, 0, 0, 0.8, 0.5);
    }
    if (model.cursor.visible) {
      ctx.strokeStyle = tokens.glow;
      ctx.lineWidth = Math.max(2, view.scale * 0.05);
      ctx.strokeRect(sx((model.cursor.square % 8) - 4 + 0.05), sy(Math.floor(model.cursor.square / 8) - 4 + 0.05), 0.9 * view.scale, 0.9 * view.scale);
    }
  }

  function pick(x, y) {
    const r = canvas.getBoundingClientRect();
    const wx = (x - r.left - view.ox) / view.scale;
    const wz = (y - r.top - view.oy) / view.scale;
    const col = Math.floor(wx + 4);
    const row = Math.floor(wz + 4);
    if (col < 0 || col > 7 || row < 0 || row > 7) return -1;
    return row * 8 + col;
  }

  function anchors() {
    const v = to;
    const p = (pt) => ({ x: v.ox + pt.x * v.scale, y: v.oy + pt.z * v.scale });
    return {
      [BLACK]: p(layout.anchors[BLACK]),
      [WHITE]: p(layout.anchors[WHITE]),
      below: layout.below,
      center: p({ x: 0, z: 0 }),
      top: p({ x: 0, z: -4 }),
      boardWidth: 8 * v.scale,
    };
  }

  return {
    kind: "2d",
    canvas,
    frame,
    render,
    pick,
    anchors,
    applyTokens: (next) => {
      tokens = next;
    },
    stepDown: () => {
      ratio = 1;
    },
    warm: async () => {},
    cameraMoving: (now) => now < start + 700,
  };
}
