// The time scrubber: one dot per frame, the rain at the place drawn as a line across the loop, the future hatched,
// and the comet playhead with a tail as long as the loop is fast. Drag or use the arrow keys to move through time.
import { clockText, relText } from "./hud.js";

const $ = (id) => document.getElementById(id);
const TAIL = { slow: 120, normal: 180, fast: 260 };

export function createScrubber({ onSeek, onToggle }) {
  const el = $("scrubber");
  const comet = $("comet");
  const loopBox = document.querySelector(".loop");
  let frames = [];
  let nowIndex = 0;
  let width = el.clientWidth;
  let dragging = false;
  let lastShown = -1;

  new ResizeObserver(() => (width = el.clientWidth)).observe(el);

  const fromEvent = (e) => {
    const r = el.getBoundingClientRect();
    const t = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    return t * (frames.length - 1);
  };
  el.addEventListener("pointerdown", (e) => {
    if (!frames.length) return;
    dragging = true;
    el.setPointerCapture(e.pointerId);
    onSeek(fromEvent(e), true);
  });
  el.addEventListener("pointermove", (e) => dragging && onSeek(fromEvent(e), true));
  const end = (e) => {
    if (!dragging) return;
    dragging = false;
    onSeek(Math.round(fromEvent(e)), true);
  };
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
  el.addEventListener("keydown", (e) => {
    const keys = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1 };
    if (e.key in keys) onSeek(null, true, keys[e.key]);
    else if (e.key === "Home") onSeek(0, true);
    else if (e.key === "End") onSeek(frames.length - 1, true);
    else if (e.key === " " || e.key === "Enter") onToggle();
    else return;
    e.preventDefault();
  });

  return {
    setFrames(list, series) {
      frames = list;
      nowIndex = Math.max(0, list.findLastIndex((f) => !f.nowcast));
      const n = list.length;
      el.setAttribute("aria-valuemax", String(Math.max(0, n - 1)));
      el.style.setProperty("--from", n > 1 ? (nowIndex / (n - 1)).toFixed(4) : "1");
      $("future").hidden = nowIndex >= n - 1;

      const ticks = list.map((f, i) => {
        const t = document.createElement("span");
        t.className = i === nowIndex ? "tick is-now" : "tick";
        t.style.setProperty("--p", n > 1 ? (i / (n - 1)).toFixed(4) : "0");
        return t;
      });
      $("ticks").replaceChildren(...ticks);

      const labels = [];
      const add = (i, cls) => {
        if (i < 0 || labels.some((l) => Math.abs(l.i - i) < 2.5)) return;
        labels.push({ i, cls });
      };
      add(nowIndex, "is-now");
      add(0, "");
      add(n - 1, "");
      const hourBack = list.findIndex((f) => f.time >= list[nowIndex].time - 3600000);
      add(hourBack, "");
      labels.sort((p, q) => p.i - q.i);
      $("scale").replaceChildren(
        ...labels.map(({ i, cls }) => {
          const s = document.createElement("span");
          s.className = cls;
          s.style.setProperty("--p", n > 1 ? (i / (n - 1)).toFixed(4) : "0");
          s.textContent = i === nowIndex ? "Now" : relText((list[i].time - list[nowIndex].time) / 60000);
          return s;
        }),
      );

      // the rain at the place across the loop
      const pts = series.map((s, i) => [n > 1 ? (i / (n - 1)) * 100 : 0, 31 - Math.min(1, s.level / 1.4) * 27]);
      if (pts.length > 1) {
        const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
        $("sparkLine").setAttribute("d", line);
        $("sparkArea").setAttribute("d", `${line} L100 32 L0 32 Z`);
      }
      lastShown = -1;
    },
    update(view, playing, speed) {
      const n = frames.length;
      if (!n) return;
      comet.style.setProperty("--x", (view.head * width).toFixed(1));
      comet.style.setProperty("--o", view.fade.toFixed(3));
      comet.style.setProperty("--tail", `${Math.min(playing ? TAIL[speed] ?? TAIL.normal : 14, view.head * width).toFixed(1)}px`);
      loopBox.classList.toggle("is-paused", !playing);
      const shown = view.mix < 0.5 ? view.a : view.b;
      if (shown !== lastShown) {
        lastShown = shown;
        const f = frames[shown];
        $("frameClock").textContent = clockText(f.time);
        const rel = (f.time - frames[nowIndex].time) / 60000;
        $("frameRel").textContent = shown === nowIndex ? "Now" : relText(rel);
        el.setAttribute("aria-valuenow", String(shown));
        el.setAttribute("aria-valuetext", `${clockText(f.time)}, ${shown === nowIndex ? "now" : relText(rel)}`);
      }
    },
    get nowIndex() {
      return nowIndex;
    },
  };
}
