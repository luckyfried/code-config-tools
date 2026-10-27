// The Loops panel: one row per saved loop, with its shape, play and stop, its WAV and JSON files, and remove.

const PLAY = '<svg class="icon icon-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.4-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5Z" fill="currentColor"/></svg>';
const STOP = '<svg class="icon icon-stop" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor"/></svg>';
const REMOVE = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

export class LoopList {
  constructor(list, empty, handlers) {
    this.list = list;
    this.empty = empty;
    this.handlers = handlers;
    this.rows = new Map();
    this.tokens = null;
  }

  setTokens(tokens) {
    this.tokens = tokens;
    for (const row of this.rows.values()) this.paint(row);
  }

  render(loops) {
    this.list.replaceChildren();
    this.rows.clear();
    this.empty.hidden = loops.length > 0;
    for (const loop of loops) this.list.append(this.row(loop));
    for (const row of this.rows.values()) this.paint(row);
  }

  row(loop) {
    const item = document.createElement("li");
    item.className = "loop";

    const play = document.createElement("button");
    play.type = "button";
    play.className = "icon-button loop-play";
    play.setAttribute("aria-pressed", "false");
    play.setAttribute("aria-label", `Play ${loop.name}`);
    play.innerHTML = PLAY + STOP;
    play.addEventListener("click", () => {
      const on = play.getAttribute("aria-pressed") !== "true";
      if (on) this.handlers.onPlay(loop);
      else this.handlers.onStop(loop);
    });

    const name = document.createElement("p");
    name.className = "loop-name";
    name.textContent = loop.name;
    const meta = document.createElement("span");
    meta.className = "loop-meta";
    const bars = loop.bars === 1 ? "1 bar" : `${loop.bars} bars`;
    meta.textContent = `${bars} at ${loop.bpm} BPM, ${loop.key} ${loop.scaleLabel.toLowerCase()}`;
    name.append(meta);

    const shape = document.createElement("canvas");
    shape.className = "loop-shape";
    shape.setAttribute("aria-hidden", "true");

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button loop-remove";
    remove.setAttribute("aria-label", `Remove ${loop.name}`);
    remove.innerHTML = REMOVE;
    remove.addEventListener("click", () => this.handlers.onRemove(loop));

    const files = document.createElement("div");
    files.className = "loop-files";
    const wav = document.createElement("button");
    wav.type = "button";
    wav.className = "chip";
    wav.textContent = "Save WAV";
    wav.addEventListener("click", () => this.handlers.onWav(loop));
    const json = document.createElement("button");
    json.type = "button";
    json.className = "chip";
    json.textContent = "Save JSON";
    json.addEventListener("click", () => this.handlers.onJson(loop));
    files.append(wav, json);

    item.append(play, name, remove, shape, files);
    this.rows.set(loop.id, { loop, play, shape });
    return item;
  }

  paint({ loop, shape }) {
    if (!this.tokens || !loop.outline) return;
    const rect = shape.getBoundingClientRect();
    if (rect.width === 0) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    shape.width = Math.round(rect.width * ratio);
    shape.height = Math.round(rect.height * ratio);
    const ctx = shape.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const points = loop.outline;
    const step = rect.width / points.length;
    ctx.fillStyle = this.tokens.voices[loop.voice] || this.tokens.accent;
    for (let i = 0; i < points.length; i += 1) {
      const h = Math.max(1.5, points[i] * rect.height);
      ctx.fillRect(i * step, (rect.height - h) / 2, Math.max(1, step - 1), h);
    }
  }

  /** Repaints the shapes once the panel is in view and has a size. */
  refresh() {
    for (const row of this.rows.values()) this.paint(row);
  }

  setPlaying(id, on) {
    const row = this.rows.get(id);
    if (!row) return;
    row.play.setAttribute("aria-pressed", on ? "true" : "false");
    row.play.setAttribute("aria-label", `${on ? "Stop" : "Play"} ${row.loop.name}`);
  }
}
