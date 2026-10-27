// The pad grid. The long side of the grid follows the long side of its space, so a phone holds it upright and a
// desktop lays it across: along the long side each pad is the next scale degree, across it each row is a fourth
// higher, the lowest note at the bottom left. Split gives each of two players a half with its own voice; on an
// upright screen the far half turns to face the person across the table.
import { keyIndex, midiOf, rowStep } from "../music/scales.js";

const KEY_ROWS = [
  ["KeyZ", "KeyX", "KeyC", "KeyV", "KeyB", "KeyN", "KeyM", "Comma", "Period", "Slash"],
  ["KeyA", "KeyS", "KeyD", "KeyF", "KeyG", "KeyH", "KeyJ", "KeyK", "KeyL", "Semicolon"],
  ["KeyQ", "KeyW", "KeyE", "KeyR", "KeyT", "KeyY", "KeyU", "KeyI", "KeyO", "KeyP"],
  ["Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Digit6", "Digit7", "Digit8", "Digit9", "Digit0"],
];
const KEY_AT = new Map();
KEY_ROWS.forEach((row, j) => row.forEach((code, i) => KEY_AT.set(code, { i, j })));

export class Grid {
  constructor(root, { onPress, onRelease, onHalfVoice }) {
    this.root = root;
    this.onPress = onPress;
    this.onRelease = onRelease;
    this.onHalfVoice = onHalfVoice;
    this.pads = [];
    this.settings = null;
    this.tall = null;
    this.pointers = new Map();
    this.lit = new Map();
    root.addEventListener("pointerdown", (event) => this.down(event));
    root.addEventListener("pointermove", (event) => this.move(event));
    root.addEventListener("pointerup", (event) => this.up(event));
    root.addEventListener("pointercancel", (event) => this.up(event));
    root.addEventListener("lostpointercapture", (event) => this.up(event));
    root.addEventListener("contextmenu", (event) => event.preventDefault());
  }

  /**
   * `size` "5x8" or "6x10"; `voices` one voice, or two when split; `labelFor(midi, voice)` names a pad;
   * `colorFor(midi)` colors it; `octaveFor(voice)` is the voice's own octave.
   */
  configure(settings) {
    this.settings = settings;
    this.tall = null;
    this.layout();
  }

  /** Lays the pads out again when the space changes shape; answers true when it did. */
  layout() {
    if (!this.settings) return false;
    const box = this.root.getBoundingClientRect();
    const tall = box.height > box.width * 1.02;
    if (tall === this.tall) return false;
    this.tall = tall;
    this.build();
    return true;
  }

  build() {
    const { size, scale, key, split, voices, labelFor, colorFor } = this.settings;
    const [short, long] = size.split("x").map(Number);
    const halves = split ? 2 : 1;
    const along = long / halves;
    const step = rowStep(scale);
    const tall = this.tall;
    this.release();
    this.root.replaceChildren();
    this.lit.clear();
    this.root.classList.toggle("tall", tall);
    this.root.classList.toggle("split", split);
    this.pads = [];
    this.along = along;
    this.short = short;

    for (let half = 0; half < halves; half += 1) {
      const voice = voices[half] || voices[0];
      const box = document.createElement("div");
      box.className = "half";
      if (tall && split && half === 1) box.classList.add("facing");
      const head = document.createElement("div");
      head.className = "half-head";
      const name = document.createElement("span");
      name.className = "half-name";
      name.textContent = half === 0 ? "Player one" : "Player two";
      const change = document.createElement("button");
      change.type = "button";
      change.className = "chip half-voice";
      change.dataset.voice = voice;
      change.textContent = this.settings.voiceLabel(voice);
      change.setAttribute("aria-label", `${name.textContent}: ${change.textContent}. Change voice`);
      change.addEventListener("click", () => this.onHalfVoice(half));
      head.append(name, change);

      const pads = document.createElement("div");
      pads.className = "pads";
      const cols = tall ? short : along;
      const rows = tall ? along : short;
      pads.style.setProperty("--cols", String(cols));
      pads.style.setProperty("--rows", String(rows));
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < cols; c += 1) {
          const i = tall ? along - 1 - r : c;
          const j = tall ? c : short - 1 - r;
          const degree = i + j * step;
          const midi = midiOf(degree, scale, key, 3);
          const el = document.createElement("div");
          el.className = "pad";
          if ((midi - keyIndex(key)) % 12 === 0) el.classList.add("root");
          el.dataset.index = String(this.pads.length);
          el.style.setProperty("--pad-color", colorFor(midi));
          const label = document.createElement("span");
          label.className = "pad-note";
          label.textContent = labelFor(midi, voice);
          el.append(label);
          pads.append(el);
          this.pads.push({ index: this.pads.length, half, i, j, degree, midi, voice, el });
        }
      }
      box.append(head, pads);
      this.root.append(box);
    }
  }

  padAt(x, y) {
    const hit = document.elementFromPoint(x, y);
    const el = hit && hit.closest(".pad");
    if (!el || !this.root.contains(el)) return null;
    return this.pads[Number(el.dataset.index)] || null;
  }

  velocity(event) {
    if (event.pointerType === "pen" && event.pressure > 0) return 0.4 + 0.6 * event.pressure;
    return 0.85;
  }

  down(event) {
    const pad = this.padAt(event.clientX, event.clientY);
    if (!pad) return;
    event.preventDefault();
    try {
      this.root.setPointerCapture(event.pointerId);
    } catch {
      // A pointer that is already gone has nothing to capture.
    }
    const key = `p${event.pointerId}`;
    this.pointers.set(event.pointerId, pad);
    this.onPress(pad, key, this.velocity(event));
  }

  move(event) {
    const was = this.pointers.get(event.pointerId);
    if (!was) return;
    const pad = this.padAt(event.clientX, event.clientY);
    if (!pad || pad === was) return;
    const key = `p${event.pointerId}`;
    this.onRelease(key);
    this.pointers.set(event.pointerId, pad);
    this.onPress(pad, key, this.velocity(event));
  }

  up(event) {
    if (!this.pointers.has(event.pointerId)) return;
    this.pointers.delete(event.pointerId);
    this.onRelease(`p${event.pointerId}`);
  }

  maps(code) {
    return KEY_AT.has(code);
  }

  /** A key of the typing map: the letter and number rows are the four lowest rows of the first half. */
  key(code, down) {
    const at = KEY_AT.get(code);
    if (!at) return false;
    const id = `k${code}`;
    if (!down) {
      this.onRelease(id);
      return true;
    }
    const pad = this.pads.find((p) => p.half === 0 && p.i === at.i && p.j === at.j);
    if (pad) this.onPress(pad, id, 0.85);
    return true;
  }

  release() {
    for (const id of this.pointers.keys()) this.onRelease(`p${id}`);
    this.pointers.clear();
  }

  /** The pad for a scale degree, nearest the middle of the first half when the degree is on several. */
  padFor(degree) {
    let best = null;
    let distance = Infinity;
    const ci = (this.along - 1) / 2;
    const cj = (this.short - 1) / 2;
    for (const pad of this.pads) {
      if (pad.half !== 0 || pad.degree !== degree) continue;
      const d = (pad.i - ci) ** 2 + ((pad.j - cj) * 1.4) ** 2;
      if (d < distance) {
        best = pad;
        distance = d;
      }
    }
    return best;
  }

  /** The middle of a pad as 0 to 1 across and down the window; null when the grid is out of sight. */
  centerOf(pad) {
    const rect = pad.el.getBoundingClientRect();
    if (rect.width === 0) return null;
    return { x: (rect.left + rect.width / 2) / window.innerWidth, y: (rect.top + rect.height / 2) / window.innerHeight };
  }

  /** Lights or dims a pad; a pad lit by two hands stays lit until both let go. */
  light(pad, on, look) {
    const count = (this.lit.get(pad.el) || 0) + (on ? 1 : -1);
    if (count <= 0) this.lit.delete(pad.el);
    else this.lit.set(pad.el, count);
    pad.el.style.setProperty("--attack", `${Math.max(10, Math.round(look.attack * 1000))}ms`);
    pad.el.style.setProperty("--release", `${Math.max(60, Math.round(look.release * 1000))}ms`);
    pad.el.classList.toggle("on", count > 0);
  }
}
