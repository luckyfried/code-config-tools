// A rolling-digit total: every digit is a column of 0 to 9 repeated three times, moved with transform only, so the
// roll runs on the compositor. The resting position lives in --row; the Web Animations API plays the move to it. A
// column at rest shows its digit as plain text (data-digit), so no edge of a neighboring row is ever drawn.

const CYCLES = 3;
const MIDDLE = 10;

function reduced() {
  return matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function currentRow(strip) {
  const cs = getComputedStyle(strip);
  const ty = new DOMMatrixReadOnly(cs.transform === "none" ? undefined : cs.transform).m42;
  return -ty / parseFloat(cs.fontSize);
}

function makeColumn() {
  const col = document.createElement("span");
  col.className = "odo-col";
  const strip = document.createElement("span");
  strip.className = "odo-strip";
  for (let i = 0; i < 10 * CYCLES; i += 1) {
    const d = document.createElement("span");
    d.textContent = String(i % 10);
    strip.append(d);
  }
  col.append(strip);
  return { col, strip };
}

function makeChar(ch) {
  const s = document.createElement("span");
  s.className = "odo-char";
  s.textContent = ch;
  return s;
}

export function createOdometer(root, format) {
  let text = "";
  let columns = [];

  function layout(next) {
    return next.replace(/\d/g, "0");
  }

  function build(next) {
    root.replaceChildren();
    columns = [];
    for (const ch of next) {
      if (/\d/.test(ch)) {
        const c = makeColumn();
        root.append(c.col);
        columns.push(c);
      } else {
        root.append(makeChar(ch));
      }
    }
  }

  function move(c, from, to, duration, delay) {
    const { col, strip } = c;
    strip.getAnimations().forEach((a) => a.cancel());
    strip.style.setProperty("--row", String(to));
    col.dataset.digit = String(to % 10);
    if (duration <= 0 || from === to) {
      col.classList.add("is-settled");
      return;
    }
    col.classList.remove("is-settled");
    const roll = strip.animate(
      [{ transform: `translateY(${-from}em)` }, { transform: `translateY(${-to}em)` }],
      { duration, delay, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
    );
    roll.finished.then(() => col.classList.add("is-settled"), () => {});
  }

  // Rolls up from zero: low places travel further than high ones, like a mechanical counter.
  function rollUp(cents, duration) {
    text = format(cents);
    build(text);
    const digits = text.replace(/\D/g, "");
    const n = digits.length;
    columns.forEach((c, i) => {
      const d = Number(digits[i]);
      const cycles = i === 0 ? 0 : i < n / 2 ? 1 : 2;
      const to = d + 10 * cycles;
      const dur = reduced() ? 0 : duration * (0.72 + 0.28 * (i / Math.max(1, n - 1)));
      move(c, 0, to, dur, 0);
    });
  }

  // Moves to a new figure from wherever the columns are now, matching places from the right.
  function to(cents, duration) {
    const next = format(cents);
    const oldDigits = text.replace(/\D/g, "");
    const rows = columns.map((c) => currentRow(c.strip));
    if (layout(next) !== layout(text)) build(next);
    text = next;
    const digits = next.replace(/\D/g, "");
    const n = digits.length;
    columns.forEach((c, i) => {
      const fromRight = n - 1 - i;
      const oldIndex = oldDigits.length - 1 - fromRight;
      let from = MIDDLE;
      if (oldIndex >= 0) {
        const r = rows.length === oldDigits.length ? rows[oldIndex] : Number(oldDigits[oldIndex]);
        from = MIDDLE + (((Math.round(r * 1000) / 1000) % 10) + 10) % 10;
      }
      const target = MIDDLE + Number(digits[i]);
      move(c, from, target, reduced() ? 0 : duration, (n - 1 - i) * 24);
    });
  }

  return { rollUp, to, get text() { return text; } };
}
