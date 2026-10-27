// The passage as one running line: one fixed-width cell per character, a caret that eases to each new position,
// and a track that slides left once the caret reaches its resting place a third of the way in.

export class Line {
  constructor(line, track, caret) {
    this.line = line;
    this.track = track;
    this.caret = caret;
    this.cells = [];
    this.index = 0;
    this.chWidth = 0;
    this.measure = this.measure.bind(this);
    if ("ResizeObserver" in window) new ResizeObserver(this.measure).observe(line);
    if (document.fonts) document.fonts.ready.then(this.measure);
  }

  setText(chars, mode) {
    this.line.classList.toggle("is-code", mode === "code");
    this.line.classList.remove("is-done", "is-typing");
    const frag = document.createDocumentFragment();
    this.cells = chars.map((ch) => {
      const cell = document.createElement("span");
      cell.className = "c";
      if (ch === "\n") {
        cell.textContent = "↵";
        cell.classList.add("is-nl");
      } else {
        cell.textContent = ch;
        if (ch === " " && mode === "code") cell.classList.add("is-ws");
      }
      frag.appendChild(cell);
      return cell;
    });
    this.track.replaceChildren(frag);
    this.index = 0;
    this.measure();
    this.place(0, true);
  }

  measure() {
    const probe = document.createElement("span");
    probe.textContent = "0000000000";
    probe.className = "c-probe";
    this.track.appendChild(probe);
    this.chWidth = probe.getBoundingClientRect().width / 10 || 0;
    probe.remove();
    this.place(this.index, true);
  }

  /** How many cells the caret may travel before the track starts to slide under it. */
  anchor() {
    if (!this.chWidth) return 8;
    const cells = this.line.clientWidth / this.chWidth;
    return Math.max(4, Math.floor(cells * 0.32));
  }

  place(index, instant) {
    this.index = index;
    const anchor = this.anchor();
    const cx = Math.min(index, anchor);
    const shift = Math.max(0, index - anchor);
    if (instant) {
      this.track.classList.add("is-instant");
      this.caret.classList.add("is-instant");
    }
    this.track.style.setProperty("--shift", String(shift));
    this.caret.style.setProperty("--cx", String(cx));
    this.cells.forEach((c, i) => c.classList.toggle("is-next", i === index));
    if (instant) {
      requestAnimationFrame(() => {
        this.track.classList.remove("is-instant");
        this.caret.classList.remove("is-instant");
      });
    }
  }

  advance(index, missed) {
    const cell = this.cells[index];
    if (cell) {
      cell.classList.remove("is-next", "is-bad");
      cell.classList.add("is-ok");
      if (missed) cell.classList.add("is-miss");
    }
    const next = this.cells[index + 1];
    if (next) next.classList.add("is-next");
    this.index = index + 1;
    const anchor = this.anchor();
    this.track.style.setProperty("--shift", String(Math.max(0, this.index - anchor)));
    this.caret.style.setProperty("--cx", String(Math.min(this.index, anchor)));
  }

  wrong(index) {
    const cell = this.cells[index];
    if (!cell) return;
    cell.classList.remove("is-bad");
    void cell.offsetWidth;
    cell.classList.add("is-bad");
  }

  typing(on) {
    this.line.classList.toggle("is-typing", on);
  }

  done() {
    this.line.classList.add("is-done");
  }
}
