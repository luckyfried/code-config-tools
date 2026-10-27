// The streak number in tabular figures: each digit a strip of 0 to 9 twice over, rolled up like an odometer.
const ROLL = "cubic-bezier(0.22, 1, 0.36, 1)";

export function createOdometer(root, reduced) {
  let shown = null;

  function strip() {
    const outer = document.createElement("span");
    outer.className = "digit";
    outer.setAttribute("aria-hidden", "true");
    const inner = document.createElement("span");
    inner.className = "digit-strip";
    for (let i = 0; i < 20; i += 1) {
      const d = document.createElement("span");
      d.textContent = String(i % 10);
      inner.append(d);
    }
    outer.append(inner);
    return { outer, inner };
  }

  function roll(inner, from, to, duration, delay) {
    inner.style.setProperty("--at", String(to));
    if (reduced() || from === to) return;
    inner.animate([{ transform: `translateY(${-from}em)` }, { transform: `translateY(${-to}em)` }], {
      duration,
      delay,
      easing: ROLL,
      fill: "backwards",
    });
  }

  /** Shows `value`; from nothing it rolls up from zero, after that it rolls from the number before. */
  function set(value) {
    const digits = String(Math.max(0, value)).split("").map(Number);
    root.setAttribute("aria-label", `${value} ${value === 1 ? "day" : "days"}`);
    const before = shown === null ? null : String(shown).split("").map(Number);
    if (before && before.length === digits.length) {
      [...root.children].forEach((outer, i) => {
        const inner = outer.firstChild;
        const from = before[i];
        const to = digits[i] >= from ? digits[i] : digits[i] + 10;
        roll(inner, from, to, 700, (digits.length - 1 - i) * 40);
        inner.style.setProperty("--at", String(digits[i]));
      });
      shown = value;
      return;
    }
    root.replaceChildren();
    digits.forEach((digit, i) => {
      const { outer, inner } = strip();
      root.append(outer);
      const last = i === digits.length - 1;
      const to = last ? digit + 10 : digit;
      roll(inner, 0, to, 1500, 140 + i * 90);
    });
    shown = value;
  }

  return { set };
}
